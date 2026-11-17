"""BB24 counts from explicit source events, with no dashboard dependency."""
from collections import Counter
from zoneinfo import ZoneInfo

from reporting.dataset import calendar_date, check, rows, timestamp, whole
from reporting.exceptions import ReportingUnavailable


def activity_snapshot(data, *, start, end):
    try:
        local = ZoneInfo('Asia/Kolkata')
        first, after = start.astimezone(local).date(), end.astimezone(local).date()
        events = {e['id']: e for e in rows(data, 'collection_events')}
        units = {u['id']: u for u in rows(data, 'blood_units')}
        requests = {r['id']: r for r in rows(data, 'blood_requests')}
        donations, collected, issued, wasted = 0, 0, 0, 0
        for event in events.values():
            check(event['status'] == 'CONFIRMED')
            when = calendar_date(event['collection_date'])
            donations += first <= when < after
        for unit in units.values():
            check(unit['status'] in ('AVAILABLE', 'ISSUED', 'DISCARDED', 'QUARANTINED'))
            check(unit['collection_event_id'] in events and whole(unit['quantity'], 1) == 1)
            check(unit['collection_date'] == events[unit['collection_event_id']]['collection_date'])
            check(calendar_date(unit['collection_date']) < calendar_date(unit['expiry_date']))
            collected += first <= calendar_date(unit['collection_date']) < after
        issued_ids, fulfilled = set(), Counter()
        for issue in rows(data, 'issue_records'):
            check(issue['unit_id'] in units and issue['request_id'] in requests and issue['unit_id'] not in issued_ids)
            issued_ids.add(issue['unit_id'])
            unit = units[issue['unit_id']]
            request = requests[issue['request_id']]
            check(unit['status'] == 'ISSUED' and whole(issue['quantity'], 1) == 1)
            check((unit['blood_group'], unit['component_type']) == (request['blood_group'], request['component_type']))
            fulfilled[request['id']] += issue['quantity']
            when = timestamp(issue['issued_at'])
            check(calendar_date(unit['collection_date']) <= when.astimezone(local).date() < calendar_date(unit['expiry_date']))
            if start <= when < end:
                issued += issue['quantity']
        check(issued_ids == {u['id'] for u in units.values() if u['status'] == 'ISSUED'})
        for request in requests.values():
            check(whole(request['fulfilled_quantity']) == fulfilled[request['id']] <= whole(request['quantity'], 1))
        disposed = set()
        for disposition in rows(data, 'inventory_dispositions'):
            check(disposition['unit_id'] in units and disposition['unit_id'] not in disposed)
            disposed.add(disposition['unit_id'])
            unit = units[disposition['unit_id']]
            check(disposition['to_status'] in ('DISCARDED', 'QUARANTINED') and disposition['to_status'] == unit['status'])
            when = timestamp(disposition['occurred_at'])
            check(calendar_date(unit['collection_date']) <= when.astimezone(local).date())
            wasted += disposition['to_status'] == 'DISCARDED' and start <= when < end
        check(disposed == {u['id'] for u in units.values() if u['status'] in ('DISCARDED', 'QUARANTINED')})
        return {'donation_event_count': donations, 'collected_unit_count': collected,
                'issued_unit_count': issued, 'wasted_unit_count': wasted}
    except (KeyError, TypeError, ValueError):
        raise ReportingUnavailable() from None
