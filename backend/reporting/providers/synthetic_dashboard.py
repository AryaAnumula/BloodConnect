"""Compute BB23 from canonical source rows, never expected.json or hard-coded totals."""
from collections import Counter
from zoneinfo import ZoneInfo

from core.input_schemas import BLOOD_GROUPS
from reporting.dataset import calendar_date, check, rows, timestamp, whole
from reporting.exceptions import ReportingUnavailable


def dashboard_snapshot(data):
    try:
        now = timestamp(data['metadata']['as_of'])
        today = now.astimezone(ZoneInfo('Asia/Kolkata')).date()
        events = {event['id']: event for event in rows(data, 'collection_events')}
        for event in events.values():
            check(event['status'] == 'CONFIRMED')
            calendar_date(event['collection_date'])
        stock = Counter()
        for unit in rows(data, 'blood_units'):
            check(unit['blood_group'] in BLOOD_GROUPS and unit['component_type'] in ('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELETS'))
            check(whole(unit['quantity'], 1) == 1 and unit['status'] in ('AVAILABLE', 'ISSUED', 'DISCARDED', 'QUARANTINED'))
            expiry = calendar_date(unit['expiry_date'])
            check(unit['collection_event_id'] in events)
            check(unit['collection_date'] == events[unit['collection_event_id']]['collection_date'])
            check(calendar_date(unit['collection_date']) < expiry)
            if unit['status'] == 'AVAILABLE' and today < expiry:
                stock[(unit['blood_group'], unit['component_type'])] += unit['quantity']
        pending = 0
        for request in rows(data, 'blood_requests'):
            check(request['blood_group'] in BLOOD_GROUPS and request['component_type'] in ('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELETS'))
            check(request['status'] in ('SUBMITTED', 'APPROVED', 'REJECTED', 'ISSUED', 'CLOSED'))
            check(whole(request['fulfilled_quantity']) <= whole(request['quantity'], 1) <= 100)
            pending += request['status'] == 'SUBMITTED'
        upcoming = 0
        for camp in rows(data, 'camps'):
            check(camp['status'] in ('ACTIVE', 'CANCELLED') and whole(camp['capacity'], 1) > 0)
            start = timestamp(camp['starts_at'])
            check(start < timestamp(camp['ends_at']))
            upcoming += camp['status'] == 'ACTIVE' and start >= now
        return {'as_of': data['metadata']['as_of'],
                'stock': [dict(blood_group=g, component_type=c, available_quantity=q) for (g, c), q in sorted(stock.items())],
                'pending_requests': pending, 'upcoming_camps': upcoming}
    except (KeyError, TypeError, ValueError):
        raise ReportingUnavailable() from None
