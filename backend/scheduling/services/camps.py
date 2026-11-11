"""BB-20 camp services. Return JSON-ready DTOs, never ORM instances.

Role checks go through scheduling.permissions (PENDING S2-04).
Not implemented yet and waiting on approvals / BB-21:
  - cancel_camp (S2-05 / S2-06: cancels appointments and creates notification intents)
  - refusing a capacity reduction below active bookings, or a time change that strands
    appointments (needs the BB-21 appointment model)
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import APIException, NotFound, ValidationError

from scheduling.dto import camp_dto
from scheduling.models import Camp
from scheduling.permissions import require_camp_role

EDITABLE_FIELDS = ('name', 'location', 'starts_at', 'ends_at', 'capacity')


class CampNotEditable(APIException):
    # ASSUMPTION to confirm with Arya: a cancelled camp cannot be edited.
    status_code = 422
    default_code = 'invalid_transition'
    default_detail = 'A cancelled camp cannot be changed.'


def _check_interval(starts_at, ends_at) -> None:
    if starts_at >= ends_at:
        raise ValidationError({'ends_at': ['End must be after start.']})


def create_camp(*, actor, data: dict) -> dict:
    """Create an ACTIVE camp from already shape-validated data."""
    require_camp_role(user=actor, action='create')
    _check_interval(data['starts_at'], data['ends_at'])
    with transaction.atomic():
        camp = Camp.objects.create(
            name=data['name'], location=data['location'],
            starts_at=data['starts_at'], ends_at=data['ends_at'],
            capacity=data['capacity'])
    return camp_dto(camp)


def update_camp(*, actor, camp_id, data: dict) -> dict:
    """Apply a partial update under a row lock."""
    require_camp_role(user=actor, action='update')
    changes = {name: data[name] for name in EDITABLE_FIELDS if name in data}
    if not changes:
        raise ValidationError({'non_field_errors': ['Provide at least one field to change.']})
    with transaction.atomic():
        try:
            camp = Camp.objects.select_for_update().get(pk=camp_id)
        except (Camp.DoesNotExist, DjangoValidationError, ValueError):
            raise NotFound() from None
        if camp.status != Camp.Status.ACTIVE:
            raise CampNotEditable()
        _check_interval(changes.get('starts_at', camp.starts_at),
                        changes.get('ends_at', camp.ends_at))
        for field, value in changes.items():
            setattr(camp, field, value)
        camp.save(update_fields=[*changes, 'updated_at'])
    return camp_dto(camp)
