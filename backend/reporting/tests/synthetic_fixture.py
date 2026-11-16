"""Small connected source records for file-to-API tests, not aggregate-provider mocks."""
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


def key(value):
    return str(uuid5(NAMESPACE_URL, 'reporting-source-test/'+value))


def fixture():
    events = [dict(id=key(f'event{i}'), status='CONFIRMED', collection_date='2026-11-11' if i == 1 else '2026-11-15') for i in range(4)]
    units = []
    for i, component, state, expiry, event in [(0, 'RBC', 'AVAILABLE', '2026-12-27', 0),
                                              (1, 'PLASMA', 'ISSUED', '2027-11-15', 0),
                                              (2, 'PLATELETS', 'AVAILABLE', '2026-11-16', 1),
                                              (3, 'WHOLE_BLOOD', 'DISCARDED', '2026-12-20', 2),
                                              (4, 'RBC', 'QUARANTINED', '2026-12-27', 3)]:
        units.append(dict(id=key(f'unit{i}'), collection_event_id=events[event]['id'], blood_group='O+',
                          component_type=component, quantity=1, status=state, expiry_date=expiry,
                          collection_date=events[event]['collection_date']))
    requests = [dict(id=key('request0'), status='SUBMITTED', blood_group='O+', component_type='RBC', quantity=2, fulfilled_quantity=0),
                dict(id=key('request1'), status='ISSUED', blood_group='O+', component_type='PLASMA', quantity=1, fulfilled_quantity=1)]
    camps = [dict(id=key('camp0'), status='ACTIVE', capacity=2, starts_at='2026-11-17T06:30:00Z', ends_at='2026-11-17T07:30:00Z'),
             dict(id=key('camp1'), status='CANCELLED', capacity=2, starts_at='2026-11-17T06:30:00Z', ends_at='2026-11-17T07:30:00Z'),
             dict(id=key('camp2'), status='ACTIVE', capacity=2, starts_at='2026-11-16T06:30:00Z', ends_at='2026-11-16T07:30:00Z'),
             dict(id=key('camp3'), status='ACTIVE', capacity=2, starts_at='2026-11-15T06:30:00Z', ends_at='2026-11-15T07:30:00Z')]
    issues = [dict(id=key('issue'), unit_id=units[1]['id'], request_id=requests[1]['id'], quantity=1, issued_at='2026-11-15T18:30:00Z')]
    dispositions = [dict(id=key('discard'), unit_id=units[3]['id'], to_status='DISCARDED', occurred_at='2026-11-15T18:29:59.999999Z'),
                    dict(id=key('quarantine'), unit_id=units[4]['id'], to_status='QUARANTINED', occurred_at='2026-11-15T22:00:00Z')]
    return dict(metadata=dict(demo_only=True, dataset_version='bloodconnect-synthetic-v1', timezone='Asia/Kolkata', as_of='2026-11-16T06:30:00.000000+00:00'),
                tables=dict(collection_events=events, blood_units=units, blood_requests=requests, camps=camps,
                            issue_records=issues, inventory_dispositions=dispositions))


def write_snapshot(directory, data):
    path = Path(directory)/'dataset.json'
    payload = json.dumps(data, sort_keys=True).encode()
    path.write_bytes(payload)
    (path.parent/'manifest.json').write_text(json.dumps(dict(algorithm='sha256', files={'dataset.json': hashlib.sha256(payload).hexdigest()})), encoding='utf-8')
    return path
