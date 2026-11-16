"""Complete connected demo records; all constants are educational fixture settings."""
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

GROUPS = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')
COMPONENTS = ('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELETS')
LOCAL = ZoneInfo('Asia/Kolkata')
LIFE = dict(WHOLE_BLOOD=35, RBC=42, PLASMA=365, PLATELETS=5)
REASONS = {
    'AGE_BELOW_MINIMUM': 'Age is below the minimum for this demonstration screening.',
    'AGE_ABOVE_MAXIMUM': 'Age is above the maximum for this demonstration screening.',
    'WEIGHT_BELOW_MINIMUM': 'Weight is below the minimum for this demonstration screening.',
    'DONATION_TOO_RECENT': 'The last donation was too recent for this demonstration screening.',
}


def uid(kind, index):
    return str(uuid5(NAMESPACE_URL, f'bloodconnect/synthetic-demo-v1/{kind}/{index}'))


def stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds')


def instant(day, hour=9):
    return datetime.combine(day, time(hour), LOCAL)


def generate(as_of_date='2026-11-16'):
    day = date.fromisoformat(as_of_date)
    now = instant(day, 12)
    tables = {name: [] for name in (
        'accounts', 'donors', 'screenings', 'collection_events', 'blood_units',
        'inventory_dispositions', 'blood_requests', 'issue_records', 'camps', 'slots',
        'appointments', 'outbox_intents', 'delivery_attempts', 'mock_receipts', 'stock_alerts')}

    def account(kind, index, **flags):
        number = len(tables['accounts'])
        row = dict(id=uid('account', number), email=f'{kind.lower()}-{index:03d}@demo.example.test',
                   role=kind, is_active=True, is_superuser=False, is_staff=False,
                   demo_login=(kind != 'DONOR' and index == 0) or (kind == 'DONOR' and index == 450))
        row.update(flags)
        tables['accounts'].append(row)
        return row

    admins = [account('ADMIN', i) for i in range(2)]
    staff = [account('STAFF', i) for i in range(4)]
    requesters = [account('REQUESTER', i) for i in range(8)]
    forbidden_superuser = account('ADMIN', 2, is_superuser=True, is_staff=True, demo_login=False)
    inactive_admin = account('ADMIN', 3, is_active=False, demo_login=False)
    for i in range(500):
        user = account('DONOR', i, is_active=i < 490)
        tables['donors'].append(dict(id=uid('donor', i), user_id=user['id'], full_name=f'Demo Donor {i+1:04d}',
                                    mobile=f'+447700900{i:03d}', blood_group=GROUPS[i % 8],
                                    location=f'Demo Bengaluru Zone {i % 12 + 1:02d}',
                                    last_confirmed_collection_date=None))

    for i in range(400):
        donor = tables['donors'][i]
        age_days = (1, 2, 3, 4, 5, 10, 20, 45, 400)[(i // 32) % 9]
        collected = day - timedelta(days=age_days)
        event = dict(id=uid('collection', i), donor_id=donor['id'], collection_date=collected.isoformat(),
                     status='CONFIRMED', confirmed_at=stamp(instant(collected)), recorded_by_id=staff[i % 4]['id'])
        tables['collection_events'].append(event)
        donor['last_confirmed_collection_date'] = collected.isoformat()
        components = ('RBC', 'PLASMA' if i % 2 else 'PLATELETS') if i < 100 else (COMPONENTS[(i // 8) % 4],)
        for component in components:
            n = len(tables['blood_units'])
            expiry = collected + timedelta(days=LIFE[component])
            status = 'DISCARDED' if n % 20 == 0 else 'QUARANTINED' if n % 20 == 1 else 'AVAILABLE'
            unit = dict(id=uid('unit', n), unit_code=f'DEMO-UNIT-{n+1:05d}', collection_event_id=event['id'],
                        donor_id=donor['id'], blood_group=donor['blood_group'], component_type=component,
                        collection_date=collected.isoformat(), expiry_date=expiry.isoformat(), quantity=1, status=status)
            tables['blood_units'].append(unit)
            if status != 'AVAILABLE':
                expired_discard = status == 'DISCARDED' and expiry < day
                when = instant(expiry, 10) if expired_discard else instant(collected, 11)
                tables['inventory_dispositions'].append(dict(
                    id=uid('disposition', n), unit_id=unit['id'], from_status='AVAILABLE', to_status=status,
                    occurred_at=stamp(when), actor_id=staff[n % 4]['id'],
                    reason_code='EXPIRED' if expired_discard else 'DEMO_DAMAGED_PACK' if status == 'DISCARDED' else 'DEMO_PENDING_REVIEW'))

    # Preserve a historical eligible assessment and a new history-aware assessment.
    for i, donor in enumerate(tables['donors']):
        confirmed = date.fromisoformat(donor['last_confirmed_collection_date']) if donor['last_confirmed_collection_date'] else None
        if confirmed:
            historical = dict(id=uid('screening-before', i), donor_id=donor['id'], age_years=30,
                              weight_kg='65.00', last_donation_date=None, confirmed_collection_date=None,
                              status='ELIGIBLE', reason_codes=[], reasons=[],
                              assessed_at=stamp(instant(confirmed, 8)), rules_version='demo-2026-10-v1')
            tables['screenings'].append(historical)
        codes = []
        age = 17 if 475 <= i < 480 else 22 + i % 39
        weight = '45.00' if 480 <= i < 490 else f'{55 + i % 30}.00'
        self_reported = day - timedelta(days=120) if i % 3 == 0 else None
        effective = max([d for d in (confirmed, self_reported) if d is not None], default=None)
        if age < 18:
            codes.append('AGE_BELOW_MINIMUM')
        if Decimal(weight) < 50:
            codes.append('WEIGHT_BELOW_MINIMUM')
        if effective is not None and (day - effective).days < 90:
            codes.append('DONATION_TOO_RECENT')
        tables['screenings'].append(dict(
            id=uid('screening-current', i), donor_id=donor['id'], age_years=age, weight_kg=weight,
            last_donation_date=self_reported.isoformat() if self_reported else None,
            confirmed_collection_date=confirmed.isoformat() if confirmed else None,
            status='INELIGIBLE' if codes else 'ELIGIBLE', reason_codes=codes, reasons=[REASONS[c] for c in codes],
            assessed_at=stamp(now - timedelta(minutes=30)), rules_version='demo-2026-11-history-v2'))

    def request_row(index, status, group, component, quantity, fulfilled=0, issued_at=None):
        created = (issued_at - timedelta(days=2)) if issued_at else now - timedelta(days=1 + index % 30)
        reviewed = created + timedelta(hours=1) if status != 'SUBMITTED' else None
        row = dict(id=uid('request', index), requester_id=requesters[index % 8]['id'], blood_group=group,
                   component_type=component, quantity=quantity, fulfilled_quantity=fulfilled,
                   urgency_level=('CRITICAL', 'URGENT', 'ROUTINE')[index % 3], status=status,
                   rejection_reason='Demo request rejected for an incomplete supporting reference.' if status == 'REJECTED' else None,
                   reviewed_by_id=staff[index % 4]['id'] if reviewed else None,
                   reviewed_at=stamp(reviewed) if reviewed else None,
                   created_at=stamp(created), updated_at=stamp(issued_at or reviewed or created))
        tables['blood_requests'].append(row)
        return row

    for i in range(80):
        status = 'SUBMITTED' if i < 40 else 'APPROVED' if i < 60 else 'REJECTED'
        request_row(i, status, GROUPS[i % 8], COMPONENTS[(i // 8) % 4], 100 if i == 0 else 1 + i % 5)
    candidates = [u for u in tables['blood_units'] if u['status'] == 'AVAILABLE' and u['expiry_date'] > day.isoformat()]
    for n, unit in enumerate(candidates[:60]):
        if n == 0:
            issued_at = instant(day, 0)
        elif n == 1:
            issued_at = instant(day, 0) - timedelta(microseconds=1)
        else:
            issued_at = now - timedelta(hours=2, minutes=n)
        status = 'APPROVED' if n < 20 else 'ISSUED' if n < 40 else 'CLOSED'
        req = request_row(80 + n, status, unit['blood_group'], unit['component_type'], 2 if n < 20 else 1, 1, issued_at)
        unit['status'] = 'ISSUED'
        tables['issue_records'].append(dict(id=uid('issue', n), request_id=req['id'], unit_id=unit['id'],
                                           issued_by_id=staff[n % 4]['id'], issued_at=stamp(issued_at), quantity=1))

    offsets = [timedelta(hours=25), timedelta(hours=23), *[timedelta(days=d) for d in (2, 7, 14, 30, -1, -7, -30, 3, 8, -2)]]
    for i, offset in enumerate(offsets):
        start = now + offset
        cancelled = i >= 9
        tables['camps'].append(dict(id=uid('camp', i), name=f'Demo Donation Camp {i+1:02d}',
                                    location=f'Demo Campus Hall {i+1:02d}', starts_at=stamp(start),
                                    ends_at=stamp(start+timedelta(hours=4)), capacity=25 if i == 0 else 32,
                                    status='CANCELLED' if cancelled else 'ACTIVE',
                                    cancel_reason='Synthetic organiser cancellation.' if cancelled else '',
                                    cancelled_at=stamp(min(now-timedelta(hours=1), start-timedelta(days=1))) if cancelled else None))
        for j in range(4):
            s = start + timedelta(hours=j)
            tables['slots'].append(dict(id=uid('slot', len(tables['slots'])), camp_id=uid('camp', i),
                                        location=f'Demo Campus Hall {i+1:02d}', starts_at=stamp(s),
                                        ends_at=stamp(s+timedelta(hours=1)), capacity=1 if i == 0 and j == 0 else 8, status='OPEN'))
    for i in range(8):
        s = now + timedelta(days=2+i, hours=i % 3)
        tables['slots'].append(dict(id=uid('slot', 48+i), camp_id=None, location=f'Demo Walk-in Desk {i+1}',
                                    starts_at=stamp(s), ends_at=stamp(s+timedelta(hours=1)), capacity=4,
                                    status='CANCELLED' if i == 7 else 'OPEN'))
    camp_index = {c['id']: c for c in tables['camps']}
    for i, slot in enumerate(tables['slots']):
        donor = tables['donors'][400+i]
        start = datetime.fromisoformat(slot['starts_at'])
        camp = camp_index.get(slot['camp_id'])
        cancelled = slot['status'] == 'CANCELLED' or (camp and camp['status'] == 'CANCELLED') or i == 10
        booked = now if i in (0, 4) else min(now-timedelta(hours=2), start-timedelta(hours=30))
        cancelled_at = datetime.fromisoformat(camp['cancelled_at']) if camp and camp['status'] == 'CANCELLED' else min(now-timedelta(minutes=15), start-timedelta(hours=1))
        if cancelled:
            booked = min(booked, cancelled_at-timedelta(hours=1))
        appt = dict(id=uid('appointment', i), donor_id=donor['id'], slot_id=slot['id'],
                    status='CANCELLED' if cancelled else 'CONFIRMED', created_at=stamp(booked),
                    cancelled_at=stamp(cancelled_at) if cancelled else None)
        tables['appointments'].append(appt)
        late = start-booked < timedelta(hours=25)
        due = booked if late else start-timedelta(hours=25)
        state = 'CANCELLED' if cancelled else 'FAILED' if i == 24 else 'BLOCKED' if i == 25 else 'DELIVERED' if i in (0, 4) or start < now else 'PENDING'
        delivered = due+timedelta(minutes=5) if state == 'DELIVERED' and due < now else now if state == 'DELIVERED' else None
        reminder_event = str(uuid5(NAMESPACE_URL, f"bloodconnect:reminder:{appt['id']}:{start.astimezone(timezone.utc).isoformat()}"))
        intent = dict(id=uid('intent', i), event_id=reminder_event, recipient_id=donor['user_id'],
                      event_type='APPOINTMENT_REMINDER', record_id=appt['id'], due_at=stamp(due),
                      scheduled_for=stamp(start), channels=['IN_APP'], state=state, late_booking=late,
                      delivered_at=stamp(delivered) if delivered else None,
                      timing_met=delivered <= start-timedelta(hours=24) if delivered else None,
                      evidence_kind='SYNTHETIC_FIXTURE_NOT_OBSERVED_DELIVERY')
        tables['outbox_intents'].append(intent)
        tables['screenings'].append(dict(
            id=uid('screening-booking', i), donor_id=donor['id'], age_years=30, weight_kg='65.00',
            last_donation_date=None, confirmed_collection_date=None, status='ELIGIBLE', reason_codes=[], reasons=[],
            assessed_at=stamp(booked-timedelta(hours=1)), rules_version='demo-2026-11-history-v2'))
        if delivered:
            tables['delivery_attempts'].append(dict(id=uid('attempt', i), intent_id=intent['id'], channel='IN_APP',
                                                   attempted_at=stamp(delivered), outcome='DELIVERED',
                                                   receipt_key=f"{intent['event_id']}:IN_APP", error_code=''))
            tables['mock_receipts'].append(dict(id=uid('fixture-receipt', i), event_id=intent['event_id'],
                                               channel='IN_APP', status='DELIVERED', recorded_at=stamp(delivered),
                                               evidence_kind='SYNTHETIC_FIXTURE_NOT_OBSERVED_DELIVERY'))
        elif state == 'FAILED':
            for retry in range(3):
                tables['delivery_attempts'].append(dict(id=uid('failed-attempt', retry), intent_id=intent['id'],
                                                       channel='IN_APP', attempted_at=stamp(now-timedelta(minutes=3-retry)),
                                                       outcome='FAILED', receipt_key=None, error_code='transport_unavailable'))
        if cancelled and camp and camp['status'] == 'CANCELLED':
            tables['outbox_intents'].append(dict(id=uid('cancel-intent', i), event_id=str(uuid5(NAMESPACE_URL, f"bloodconnect:camp-cancel:{appt['id']}")),
                                                recipient_id=donor['user_id'], event_type='APPOINTMENT_CANCELLED',
                                                record_id=appt['id'], due_at=appt['cancelled_at'], scheduled_for=None,
                                                channels=['IN_APP'], state='PENDING', late_booking=False,
                                                delivered_at=None, timing_met=None,
                                                evidence_kind='SYNTHETIC_FIXTURE_NOT_OBSERVED_DELIVERY'))

    usable = Counter((u['blood_group'], u['component_type']) for u in tables['blood_units'] if u['status'] == 'AVAILABLE' and u['expiry_date'] > day.isoformat())
    for group in GROUPS:
        for component in COMPONENTS:
            quantity = usable[(group, component)]
            if quantity < 2:
                tables['stock_alerts'].append(dict(id=uid('low-stock', group+component), alert_type='LOW_STOCK',
                                                  blood_group=group, component_type=component, unit_id=None,
                                                  quantity=quantity, threshold=2, observed_at=stamp(now)))
    for unit in tables['blood_units']:
        days = (date.fromisoformat(unit['expiry_date'])-day).days
        if unit['status'] == 'AVAILABLE' and 0 < days <= 3:
            tables['stock_alerts'].append(dict(id=uid('near-expiry', unit['id']), alert_type='NEAR_EXPIRY',
                                              blood_group=unit['blood_group'], component_type=unit['component_type'],
                                              unit_id=unit['id'], quantity=1, threshold=3, observed_at=stamp(now)))
    return dict(metadata=dict(dataset_version='bloodconnect-synthetic-v1', demo_only=True, as_of=stamp(now),
                              timezone='Asia/Kolkata', seed='UUIDv5/bloodconnect/synthetic-demo-v1',
                              distribution='Balanced coverage fixtures, not population statistics.',
                              contacts='IANA example.test emails; Ofcom +44 7700 900000-900999 drama mobiles.',
                              fixture_note='Generated history is fictional; mock receipt rows are not transport-test evidence.'),
                policy=dict(shelf_life_days=dict(LIFE), near_expiry_days=3, low_stock_minimum_per_group_component=2,
                            min_age_years=18, max_age_years=65, min_weight_kg=50, min_days_between_donations=90,
                            screening_rules_version='demo-2026-11-history-v2', foundation_screening_rules_version='demo-2026-10-v1',
                            policy_note='Explicit existing educational fixture values; no runtime clinical defaults.'),
                tables=tables,
                scenarios=dict(on_time_reminder=uid('appointment', 0), late_reminder=uid('appointment', 4),
                               full_slot=uid('slot', 0), cancelled_camp=uid('camp', 9),
                               partial_request=uid('request', 80), issued_request=uid('request', 100),
                               closed_request=uid('request', 120), max_quantity_request=uid('request', 0),
                               forbidden_superuser=forbidden_superuser['id'], inactive_admin=inactive_admin['id']),
                invalid_input_cases=[dict(name='quantity_zero', endpoint='POST /api/v1/requests',
                                          body=dict(blood_group='O+', component_type='RBC', quantity=0, urgency_level='URGENT'), expected_status=400),
                                     dict(name='quantity_over_demo_limit', endpoint='POST /api/v1/requests',
                                          body=dict(blood_group='O+', component_type='RBC', quantity=101, urgency_level='URGENT'), expected_status=400),
                                     dict(name='reversed_report_dates', endpoint='GET /api/v1/reports',
                                          query={'from': day.isoformat(), 'to': (day-timedelta(days=1)).isoformat()}, expected_status=400)])
