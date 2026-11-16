"""Approved inclusive local dates -> half-open UTC range and minimized source counts."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from rest_framework.exceptions import ValidationError

from reporting import providers
from reporting.exceptions import ReportingUnavailable
from reporting.permissions import require_admin
from reporting.selectors.dashboard import nonnegative

DEFINITIONS_VERSION = 'college-demo-events-v1'


def report_interval(*, from_date, to_date):
    if type(from_date) is not date or type(to_date) is not date or from_date > to_date:
        raise ValidationError({'to': ['Use valid dates with from no later than to.']})
    try:
        local = ZoneInfo('Asia/Kolkata')
        start = datetime.combine(from_date, time.min, local).astimezone(timezone.utc)
        end = datetime.combine(to_date + timedelta(days=1), time.min, local).astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise ValidationError({'to': ['Date range cannot be represented.']}) from None
    return start, end


def activity_report(*, actor, from_date, to_date) -> dict:
    require_admin(actor=actor)
    start, end = report_interval(from_date=from_date, to_date=to_date)
    inventory = providers.collection_wastage(start=start, end=end)
    issues = providers.issue_totals(start=start, end=end)
    if not isinstance(inventory, dict) or not isinstance(issues, dict):
        raise ReportingUnavailable()
    return {'from': from_date.isoformat(), 'to': to_date.isoformat(), 'timezone': 'Asia/Kolkata',
            'donation_event_count': nonnegative(inventory.get('donation_event_count')),
            'collected_unit_count': nonnegative(inventory.get('collected_unit_count')),
            'issued_unit_count': nonnegative(issues.get('issued_unit_count')),
            'wasted_unit_count': nonnegative(inventory.get('wasted_unit_count')),
            'definitions_version': DEFINITIONS_VERSION}
