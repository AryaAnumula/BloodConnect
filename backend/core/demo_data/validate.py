"""Validate fixture source records, relationships and independently checked totals."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from .generate import COMPONENTS, GROUPS, LOCAL

TABLES = ('accounts', 'donors', 'screenings', 'collection_events', 'blood_units', 'inventory_dispositions',
          'blood_requests', 'issue_records', 'camps', 'slots', 'appointments', 'outbox_intents',
          'delivery_attempts', 'mock_receipts', 'stock_alerts')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ts(value):
    result = datetime.fromisoformat(value)
    require(result.tzinfo is not None and result.utcoffset() is not None, 'Naive timestamp.')
    return result


def validate(data):
    require(data['metadata']['demo_only'] is True, 'Not marked synthetic.')
    require(data['metadata']['timezone'] == 'Asia/Kolkata', 'Unexpected timezone.')
    now = ts(data['metadata']['as_of'])
    today = now.astimezone(LOCAL).date()
    tables, policy = data['tables'], data['policy']
    require(set(tables) == set(TABLES), 'Unexpected source tables.')
    indexes = {}
    for name in TABLES:
        rows = tables[name]
        require(isinstance(rows, list) and rows, 'Missing table records: '+name)
        for row in rows:
            UUID(row['id'])
        indexes[name] = {r['id']: r for r in rows}
        require(len(indexes[name]) == len(rows), 'Duplicate primary key: '+name)
    accounts, donors = indexes['accounts'], indexes['donors']
    require(len(donors) == 500 and len(indexes['blood_units']) == 500, 'Expected500 donors and500 units.')
    require(len({u['email'] for u in accounts.values()}) == len(accounts), 'Duplicate email.')
    require(len({d['mobile'] for d in donors.values()}) == len(donors), 'Duplicate mobile.')
    require(len({d['user_id'] for d in donors.values()}) == len(donors), 'Duplicate donor account.')
    for account in accounts.values():
        require(account['role'] in ('DONOR', 'REQUESTER', 'STAFF', 'ADMIN'), 'Unsupported role.')
        require(account['email'].endswith('@demo.example.test'), 'Non-example email.')
        require(not any(k in account for k in ('password', 'token', 'secret')), 'Credentials in dataset.')
    for donor in donors.values():
        require(accounts[donor['user_id']]['role'] == 'DONOR', 'Invalid donor account.')
        require(donor['blood_group'] in GROUPS, 'Invalid group.')
        require(donor['mobile'].startswith('+447700900') and len(donor['mobile']) == 13, 'Non-drama mobile.')

    def staff_actor(identifier):
        actor = accounts[identifier]
        require(actor['role'] == 'STAFF' and actor['is_active'] and not actor['is_superuser'], 'Invalid operational writer.')

    events_by_donor = defaultdict(list)
    for event in tables['collection_events']:
        donor = donors[event['donor_id']]
        require(event['status'] == 'CONFIRMED' and date.fromisoformat(event['collection_date']) <= today, 'Invalid collection.')
        require(ts(event['confirmed_at']).astimezone(LOCAL).date().isoformat() == event['collection_date'], 'Collection date/time mismatch.')
        require(ts(event['confirmed_at']) <= now and accounts[donor['user_id']]['is_active'], 'Invalid collection actor/time.')
        staff_actor(event['recorded_by_id'])
        events_by_donor[donor['id']].append(event)
    for donor in donors.values():
        dates = [e['collection_date'] for e in events_by_donor[donor['id']]]
        require(donor['last_confirmed_collection_date'] == max(dates, default=None), 'History projection mismatch.')
    screens = defaultdict(list)
    for screening in tables['screenings']:
        require(screening['donor_id'] in donors and ts(screening['assessed_at']) <= now, 'Invalid screening reference/time.')
        available_history = [e['collection_date'] for e in events_by_donor[screening['donor_id']] if ts(e['confirmed_at']) <= ts(screening['assessed_at'])]
        require(screening['confirmed_collection_date'] == max(available_history, default=None), 'Assessment history snapshot mismatch.')
        effective = max([d for d in (screening['last_donation_date'], screening['confirmed_collection_date']) if d], default=None)
        assessment_date = ts(screening['assessed_at']).astimezone(LOCAL).date()
        codes = []
        if screening['age_years'] < policy['min_age_years']:
            codes.append('AGE_BELOW_MINIMUM')
        if screening['age_years'] > policy['max_age_years']:
            codes.append('AGE_ABOVE_MAXIMUM')
        if Decimal(screening['weight_kg']) < policy['min_weight_kg']:
            codes.append('WEIGHT_BELOW_MINIMUM')
        if effective and (assessment_date-date.fromisoformat(effective)).days < policy['min_days_between_donations']:
            codes.append('DONATION_TOO_RECENT')
        require(screening['reason_codes'] == codes and screening['status'] == ('INELIGIBLE' if codes else 'ELIGIBLE'), 'Inconsistent screening result.')
        screens[screening['donor_id']].append(screening)
    for event in tables['collection_events']:
        previous = [s for s in screens[event['donor_id']] if ts(s['assessed_at']) <= ts(event['confirmed_at'])]
        require(previous and max(previous, key=lambda s: ts(s['assessed_at']))['status'] == 'ELIGIBLE', 'Collection lacks eligible assessment.')

    seen_components = defaultdict(set)
    require(len({u['unit_code'] for u in tables['blood_units']}) == 500, 'Duplicate unit code.')
    for unit in tables['blood_units']:
        event = indexes['collection_events'][unit['collection_event_id']]
        require(unit['donor_id'] == event['donor_id'] and unit['blood_group'] == donors[event['donor_id']]['blood_group'], 'Unit lineage mismatch.')
        require(unit['quantity'] == 1 and type(unit['quantity']) is int, 'Unit quantity must be1.')
        require(unit['status'] in ('AVAILABLE', 'ISSUED', 'DISCARDED', 'QUARANTINED'), 'Invalid unit status.')
        component = unit['component_type']
        require(component in COMPONENTS and component not in seen_components[event['id']], 'Duplicate/invalid component.')
        seen_components[event['id']].add(component)
        require(unit['collection_date'] == event['collection_date'], 'Unit collection date mismatch.')
        require(date.fromisoformat(unit['expiry_date']) == date.fromisoformat(unit['collection_date'])+timedelta(days=policy['shelf_life_days'][component]), 'Expiry policy mismatch.')
    for components in seen_components.values():
        require('WHOLE_BLOOD' not in components or len(components) == 1, 'Mixed whole blood/components.')
    require(len(seen_components) == len(indexes['collection_events']), 'Collection without units.')

    dispositions = {}
    for disposition in tables['inventory_dispositions']:
        unit = indexes['blood_units'][disposition['unit_id']]
        require(unit['id'] not in dispositions and disposition['to_status'] == unit['status'], 'Disposition mismatch/duplicate.')
        require(disposition['to_status'] in ('DISCARDED', 'QUARANTINED'), 'Invalid disposition.')
        require(ts(indexes['collection_events'][unit['collection_event_id']]['confirmed_at']) <= ts(disposition['occurred_at']) <= now, 'Disposition chronology.')
        staff_actor(disposition['actor_id'])
        dispositions[unit['id']] = disposition
    for unit in tables['blood_units']:
        require((unit['status'] in ('DISCARDED', 'QUARANTINED')) == (unit['id'] in dispositions), 'Missing/extra disposition history.')
    fulfilled, issued_units = Counter(), set()
    for issue in tables['issue_records']:
        unit = indexes['blood_units'][issue['unit_id']]
        request = indexes['blood_requests'][issue['request_id']]
        require(unit['id'] not in issued_units and unit['status'] == 'ISSUED', 'Unit double issue/status mismatch.')
        require((unit['blood_group'], unit['component_type']) == (request['blood_group'], request['component_type']), 'Issue/request mismatch.')
        require(issue['quantity'] == 1 and type(issue['quantity']) is int, 'Invalid issue quantity.')
        require(ts(indexes['collection_events'][unit['collection_event_id']]['confirmed_at']) <= ts(issue['issued_at']) <= now, 'Issue chronology.')
        require(ts(issue['issued_at']).astimezone(LOCAL).date().isoformat() < unit['expiry_date'], 'Issued expired unit.')
        require(ts(request['reviewed_at']) <= ts(issue['issued_at']), 'Issue before approval.')
        staff_actor(issue['issued_by_id'])
        issued_units.add(unit['id'])
        fulfilled[request['id']] += issue['quantity']
    require(issued_units == {u['id'] for u in tables['blood_units'] if u['status'] == 'ISSUED'}, 'Missing issue history.')
    for request in tables['blood_requests']:
        require(accounts[request['requester_id']]['role'] == 'REQUESTER', 'Request owner role.')
        require(request['blood_group'] in GROUPS and request['component_type'] in COMPONENTS, 'Invalid request component/group.')
        require(type(request['quantity']) is int and 1 <= request['quantity'] <= 100, 'Invalid request quantity.')
        require(request['urgency_level'] in ('CRITICAL', 'URGENT', 'ROUTINE'), 'Invalid urgency.')
        require(request['fulfilled_quantity'] == fulfilled[request['id']] <= request['quantity'], 'Fulfilment does not reconcile.')
        require(request['status'] in ('SUBMITTED', 'APPROVED', 'REJECTED', 'ISSUED', 'CLOSED'), 'Invalid request status.')
        require(ts(request['created_at']) <= ts(request['updated_at']) <= now, 'Request chronology.')
        if request['status'] in ('SUBMITTED', 'REJECTED'):
            require(request['fulfilled_quantity'] == 0, 'Unapproved request issued.')
        if request['status'] in ('ISSUED', 'CLOSED'):
            require(request['fulfilled_quantity'] == request['quantity'], 'Incomplete terminal request.')
        if request['status'] == 'APPROVED':
            require(request['fulfilled_quantity'] < request['quantity'], 'Full request still approved.')
        require(bool(request['rejection_reason']) == (request['status'] == 'REJECTED'), 'Rejection reason mismatch.')
        if request['status'] == 'SUBMITTED':
            require(request['reviewed_at'] is None and request['reviewed_by_id'] is None, 'Submitted already reviewed.')
        else:
            staff_actor(request['reviewed_by_id'])
            require(ts(request['created_at']) <= ts(request['reviewed_at']) <= ts(request['updated_at']), 'Review chronology.')

    slot_counts, camp_counts, donor_intervals = Counter(), Counter(), defaultdict(list)
    for slot in tables['slots']:
        require(ts(slot['starts_at']) < ts(slot['ends_at']) and slot['capacity'] > 0, 'Invalid slot interval/capacity.')
        if slot['camp_id']:
            camp = indexes['camps'][slot['camp_id']]
            require(ts(camp['starts_at']) <= ts(slot['starts_at']) < ts(slot['ends_at']) <= ts(camp['ends_at']), 'Slot outside camp.')
    for appointment in tables['appointments']:
        slot = indexes['slots'][appointment['slot_id']]
        donor = donors[appointment['donor_id']]
        require(ts(appointment['created_at']) < ts(slot['starts_at']), 'Appointment booked after start.')
        prior = [s for s in screens[donor['id']] if ts(s['assessed_at']) <= ts(appointment['created_at'])]
        require(prior and max(prior, key=lambda s: ts(s['assessed_at']))['status'] == 'ELIGIBLE', 'Booking lacks eligible assessment.')
        require(accounts[donor['user_id']]['is_active'], 'Inactive donor booking.')
        if appointment['status'] == 'CONFIRMED':
            require(slot['status'] == 'OPEN' and appointment['cancelled_at'] is None, 'Confirmed in unavailable slot.')
            if slot['camp_id']:
                require(indexes['camps'][slot['camp_id']]['status'] == 'ACTIVE', 'Confirmed in cancelled camp.')
            interval = ts(slot['starts_at']), ts(slot['ends_at'])
            require(all(interval[1] <= old[0] or interval[0] >= old[1] for old in donor_intervals[donor['id']]), 'Overlapping confirmed bookings.')
            donor_intervals[donor['id']].append(interval)
            slot_counts[slot['id']] += 1
            camp_counts[slot['camp_id']] += 1
        else:
            require(appointment['status'] == 'CANCELLED' and ts(appointment['created_at']) <= ts(appointment['cancelled_at']) <= now, 'Invalid cancellation chronology.')
    for slot in tables['slots']:
        require(slot_counts[slot['id']] <= slot['capacity'], 'Slot over capacity.')
    for camp in tables['camps']:
        require(camp_counts[camp['id']] <= camp['capacity'], 'Camp over capacity.')
        require((camp['cancelled_at'] is not None) == (camp['status'] == 'CANCELLED'), 'Camp cancellation mismatch.')

    events, delivered_ids = set(), set()
    for intent in tables['outbox_intents']:
        appointment = indexes['appointments'][intent['record_id']]
        slot = indexes['slots'][appointment['slot_id']]
        require(intent['recipient_id'] == donors[appointment['donor_id']]['user_id'], 'Wrong reminder recipient.')
        require(intent['event_id'] not in events, 'Duplicate event ID.')
        events.add(intent['event_id'])
        if intent['event_type'] == 'APPOINTMENT_REMINDER':
            late = ts(slot['starts_at'])-ts(appointment['created_at']) < timedelta(hours=25)
            due = ts(appointment['created_at']) if late else ts(slot['starts_at'])-timedelta(hours=25)
            require(intent['late_booking'] == late and ts(intent['due_at']) == due, 'Reminder timing policy mismatch.')
            if appointment['status'] == 'CANCELLED':
                require(intent['state'] in ('CANCELLED', 'DELIVERED'), 'Cancelled appointment has live reminder.')
        else:
            require(intent['event_type'] == 'APPOINTMENT_CANCELLED' and appointment['status'] == 'CANCELLED' and intent['due_at'] == appointment['cancelled_at'], 'Cancellation event mismatch.')
        if intent['state'] == 'DELIVERED':
            delivered_ids.add(intent['event_id'])
            require(ts(intent['due_at']) <= ts(intent['delivered_at']) <= now, 'Delivery chronology.')
            require(intent['timing_met'] == (ts(intent['delivered_at']) <= ts(slot['starts_at'])-timedelta(hours=24)), 'Incorrect timing outcome.')
        else:
            require(intent['delivered_at'] is None and intent['timing_met'] is None, 'Invented delivered state.')
    receipts = {r['event_id'] for r in tables['mock_receipts']}
    require(receipts == delivered_ids, 'Mock fixture receipt mismatch.')
    for row in tables['delivery_attempts']:
        intent = indexes['outbox_intents'][row['intent_id']]
        require(ts(intent['due_at']) <= ts(row['attempted_at']) <= now, 'Attempt before due/future.')
        require(bool(row['receipt_key']) == (row['outcome'] == 'DELIVERED'), 'Receipt on failed attempt.')
    usable = Counter((u['blood_group'], u['component_type']) for u in tables['blood_units'] if u['status'] == 'AVAILABLE' and u['expiry_date'] > today.isoformat())
    expected_low = {(g, c) for g in GROUPS for c in COMPONENTS if usable[(g, c)] < policy['low_stock_minimum_per_group_component']}
    expected_near = {u['id'] for u in tables['blood_units'] if u['status'] == 'AVAILABLE' and 0 < (date.fromisoformat(u['expiry_date'])-today).days <= policy['near_expiry_days']}
    low, near = set(), set()
    for alert in tables['stock_alerts']:
        require(ts(alert['observed_at']) == now, 'Alert reference clock mismatch.')
        if alert['alert_type'] == 'LOW_STOCK':
            key = alert['blood_group'], alert['component_type']
            require(key not in low and key in expected_low and alert['quantity'] == usable[key], 'Low-stock alert mismatch.')
            low.add(key)
        else:
            require(alert['alert_type'] == 'NEAR_EXPIRY' and alert['unit_id'] in expected_near and alert['unit_id'] not in near, 'Near-expiry alert mismatch.')
            near.add(alert['unit_id'])
    require(low == expected_low and near == expected_near, 'Missing source alert coverage.')
    return {'status': 'PASS', 'records': sum(len(rows) for rows in tables.values()), 'tables': len(TABLES)}
