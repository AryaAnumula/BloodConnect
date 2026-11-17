"""BB23 read-only camp summary; existing scheduling models remain authoritative.

Internal trusted selector consumed after reporting's ADMIN gate. No write service,
inventory dependency or duplicate camp model. A missing app is unavailable, not zero.
"""
from datetime import datetime

from django.apps import apps
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.errors import DecisionRequired


def upcoming_camp_count(*, now) -> int:
    if not isinstance(now, datetime) or timezone.is_naive(now):
        raise ValidationError({'now': ['An aware server timestamp is required.']})
    try:
        Camp = apps.get_model('scheduling', 'Camp')
    except LookupError:
        raise DecisionRequired('Camp summary requires the actual scheduling application.') from None
    # BC-D036 dashboard definition: ACTIVE camps starting at/after the snapshot instant.
    # Database/storage errors propagate to the reporting provider's redacted boundary.
    return Camp.objects.filter(status='ACTIVE', starts_at__gte=now).count()
