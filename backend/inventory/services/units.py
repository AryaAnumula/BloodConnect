"""Atomic intake. Profile lock precedes event/unit FK inserts (BC-D047)."""
from inspect import signature
from zoneinfo import ZoneInfo

from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from core.errors import DecisionRequired
from donors.configuration import approved_screening_rules
from donors.models import DonorProfile
from donors.services.evaluation import evaluate
from inventory.configuration import shelf_life_policy
from inventory.exceptions import IneligibleDonor, InventoryUnavailable, UnitConflict
from inventory.models import BloodUnit, CollectionEvent
from inventory.permissions import require_staff
from inventory.selectors.collection_history import latest_confirmed_collection_date
from inventory.serializers import BloodUnitCreate
from inventory.services.collection_events import validate_event_components
from inventory.services.donor_boundary import record_confirmed_collection
from inventory.services.policy import calculate_expiry_date

KOLKATA = ZoneInfo('Asia/Kolkata')


def unit_dto(unit):
    return {name: str(getattr(unit, name)) for name in
            ('id', 'unit_code', 'donor_id', 'collection_event_id', 'blood_group',
             'component_type', 'collection_date', 'expiry_date', 'status')} | {'quantity': unit.quantity}


def _authorize_collection(donor, collection_date, today):
    latest = latest_confirmed_collection_date(donor_id=donor.pk)
    if latest != donor.last_confirmed_collection_date:
        raise InventoryUnavailable()
    if latest is not None and collection_date < latest:
        raise ValidationError({'collection_date': ['Date precedes confirmed history.']})
    rules = approved_screening_rules()
    result = donor.eligibility_results.order_by('-assessed_at', '-id').first()
    if (result is None or result.status != 'ELIGIBLE'
            or result.rules_version != rules['rules_version']
            or result.confirmed_collection_date != latest
            or result.assessed_at > timezone.now()
            or timezone.localdate(result.assessed_at, KOLKATA) > collection_date):
        raise IneligibleDonor()
    if 'confirmed_collection_date' not in signature(evaluate).parameters:
        raise InventoryUnavailable()
    status, _, _ = evaluate(age_years=result.age_years, weight_kg=result.weight_kg,
                            last_donation_date=result.last_donation_date,
                            confirmed_collection_date=latest,
                            today=collection_date, rules=rules)
    if status != 'ELIGIBLE':
        raise IneligibleDonor()


def record_unit(*, actor, data: dict) -> dict:
    require_staff(actor)
    serializer = BloodUnitCreate(data=data)
    serializer.is_valid(raise_exception=True)
    values = dict(serializer.validated_data)
    event_id = values.pop('collection_event_id', None)
    policy = shelf_life_policy()
    try:
        with transaction.atomic():
            try:
                donor = DonorProfile.objects.select_for_update(no_key=True).get(pk=values['donor_id'])
            except DonorProfile.DoesNotExist:
                raise NotFound() from None
            today = timezone.localdate(timezone=KOLKATA)
            if values['collection_date'] > today:
                raise ValidationError({'collection_date': ['Date cannot be in the future.']})
            if not donor.user.is_active or donor.user.role != 'DONOR':
                raise ValidationError({'donor_id': ['An active donor is required.']})
            if values['blood_group'] != donor.blood_group:
                raise ValidationError({'blood_group': ['Group does not match donor.']})
            expiry = calculate_expiry_date(collection_date=values['collection_date'],
                                          component_type=values['component_type'], policy=policy, today=today)
            if event_id is None:
                _authorize_collection(donor, values['collection_date'], today)
                stored = record_confirmed_collection(donor_id=donor.pk,
                                                      collection_date=values['collection_date'])
                if stored != values['collection_date']:
                    raise InventoryUnavailable()
                event = CollectionEvent.objects.create(donor=donor,
                    collection_date=values['collection_date'], blood_group=values['blood_group'],
                    recorded_by=actor)
            else:
                try:
                    event = CollectionEvent.objects.select_for_update().get(pk=event_id)
                except CollectionEvent.DoesNotExist:
                    raise NotFound() from None
                if (event.donor_id != donor.pk or event.collection_date != values['collection_date']
                        or event.blood_group != values['blood_group'] or event.status != 'CONFIRMED'):
                    raise ValidationError({'collection_event_id': ['Event identity does not match unit.']})
            components = list(event.units.values_list('component_type', flat=True))
            try:
                validate_event_components(components=components + [values['component_type']])
            except ValueError as exc:
                raise UnitConflict() from exc
            unit = BloodUnit.objects.create(collection_event=event, expiry_date=expiry, **values)
            return unit_dto(unit)
    except IntegrityError as exc:
        # Only actual identity duplicates are 409; other integrity failures stay unavailable.
        if (BloodUnit.objects.filter(unit_code=values['unit_code']).exists()
                or (event_id and BloodUnit.objects.filter(collection_event_id=event_id,
                                                          component_type=values['component_type']).exists())):
            raise UnitConflict() from exc
        raise InventoryUnavailable() from exc
    except (DatabaseError, DecisionRequired) as exc:
        raise InventoryUnavailable() from exc
