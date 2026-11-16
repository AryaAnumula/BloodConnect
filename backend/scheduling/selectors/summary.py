"""Read-only scheduling summary consumed by the BB-23 dashboard provider.

Contract (COMMON/INTEGRATION_CONTRACTS): upcoming_camp_count(*, now) -> int, the number of real
ACTIVE camps whose start is at or after the aware `now`. CANCELLED camps are never counted, so a
camp cancellation lowers the count. No writes, no network, no personal data, no reporting-owned
camp model.
"""
from datetime import datetime

from django.utils import timezone

from scheduling.models import Camp


def upcoming_camp_count(*, now) -> int:
    if not isinstance(now, datetime) or timezone.is_naive(now):
        raise ValueError('An aware timestamp is required.')
    return Camp.objects.filter(status=Camp.Status.ACTIVE, starts_at__gte=now).count()
