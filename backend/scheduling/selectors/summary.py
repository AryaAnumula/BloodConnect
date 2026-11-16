"""Read-only approved ACTIVE/future camp definition for reporting consumers."""
from datetime import datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from scheduling.models import Camp


def upcoming_camp_count(*, now) -> int:
    if not isinstance(now, datetime) or timezone.is_naive(now):
        raise ValidationError({'now': ['An aware timestamp is required.']})
    return Camp.objects.filter(status=Camp.Status.ACTIVE, starts_at__gte=now).count()
