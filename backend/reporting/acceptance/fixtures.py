"""Small actual-model fixtures for reporting acceptance, not intake/eligibility proof."""
from datetime import timedelta
from uuid import uuid4

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils import timezone

from donors.models import DonorProfile


def require_models(*labels):
    try:
        return [apps.get_model(label) for label in labels]
    except LookupError as error:
        raise RuntimeError(
            'Real reporting acceptance NOT READY: compose actual inventory/request/scheduling source first.'
        ) from error


def user(role='ADMIN', **fields):
    return get_user_model().objects.create_user(
        email=f'report-acceptance-{uuid4().hex}@example.test', role=role, **fields,
    )


def source_unit(*, actor, collected=None, group='A+', component='RBC',
                status='AVAILABLE', expiry=None, event=None):
    Event, Unit = require_models('inventory.CollectionEvent', 'inventory.BloodUnit')
    from inventory.configuration import shelf_life_policy
    if event is None:
        collected = collected or timezone.localdate()
        donor = DonorProfile.objects.create(
            user=user('DONOR'), full_name='Synthetic reporting fixture',
            mobile='+919' + str(uuid4().int % 1000000000).zfill(9),
            blood_group=group, location='Demo City', last_confirmed_collection_date=collected,
        )
        event = Event.objects.create(
            donor=donor, blood_group=group, collection_date=collected,
            recorded_by=actor, status='CONFIRMED',
        )
    else:
        collected, group = event.collection_date, event.blood_group
    return Unit.objects.create(
        unit_code='REPORT-' + uuid4().hex, donor_id=event.donor_id, collection_event=event,
        blood_group=group, component_type=component, collection_date=collected,
        expiry_date=expiry or collected + timedelta(days=shelf_life_policy()[component]),
        quantity=1, status=status,
    )
