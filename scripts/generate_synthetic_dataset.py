"""Generate, validate, or inspect the complete BloodConnect mini-project dataset."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from core.demo_data.generate import generate
from core.demo_data.reference import expected_results, reconcile_sql, reference_database
from core.demo_data.validate import validate

DEFAULT = ROOT / 'datasets/synthetic/bloodconnect-demo-v1'
TARGETS = {
    'accounts': ('accounts.User', 'All owners'), 'donors': ('donors.DonorProfile', 'Ankitha'),
    'screenings': ('donors.EligibilityResult', 'Ankitha'),
    'collection_events': ('inventory.CollectionEvent', 'Yashwitha'),
    'blood_units': ('inventory.BloodUnit', 'Yashwitha'),
    'inventory_dispositions': ('inventory.InventoryDisposition', 'Yashwitha'),
    'blood_requests': ('blood_requests.BloodRequest', 'Arnav17/18; Arya19'),
    'issue_records': ('blood_requests.IssueRecord', 'Arnav16'),
    'camps': ('scheduling.Camp', 'Ankitha20'), 'slots': ('scheduling.Slot', 'Ankitha21'),
    'appointments': ('scheduling.Appointment', 'Ankitha21'),
    'outbox_intents': ('notification_adapter.OutboxIntent', 'Arya22'),
    'delivery_attempts': ('notification_adapter.DeliveryAttempt', 'Arya22'),
    'mock_receipts': ('Fictional reference history only; never seed Node receipt store', 'Arya22'),
    'stock_alerts': ('inventory.StockAlert source-condition examples', 'Yashwitha15'),
}
REFERENCES = {
    'donors': {'user_id': 'accounts.id'}, 'screenings': {'donor_id': 'donors.id'},
    'collection_events': {'donor_id': 'donors.id', 'recorded_by_id': 'accounts.id'},
    'blood_units': {'collection_event_id': 'collection_events.id', 'donor_id': 'donors.id'},
    'inventory_dispositions': {'unit_id': 'blood_units.id', 'actor_id': 'accounts.id'},
    'blood_requests': {'requester_id': 'accounts.id', 'reviewed_by_id': 'accounts.id'},
    'issue_records': {'request_id': 'blood_requests.id', 'unit_id': 'blood_units.id', 'issued_by_id': 'accounts.id'},
    'slots': {'camp_id': 'camps.id'}, 'appointments': {'donor_id': 'donors.id', 'slot_id': 'slots.id'},
    'outbox_intents': {'recipient_id': 'accounts.id', 'record_id': 'appointments.id'},
    'delivery_attempts': {'intent_id': 'outbox_intents.id'},
    'mock_receipts': {'event_id': 'outbox_intents.event_id'}, 'stock_alerts': {'unit_id': 'blood_units.id'},
}


def encoded(value):
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)+'\n'


def write_exports(data, target):
    target.mkdir(parents=True, exist_ok=True)
    (target/'csv').mkdir(exist_ok=True)
    expected = expected_results(data)
    (target/'dataset.json').write_text(encoded(data), encoding='utf-8', newline='\n')
    (target/'expected.json').write_text(encoded(expected), encoding='utf-8', newline='\n')
    dictionary = {}
    for table, rows in data['tables'].items():
        fields = {}
        for field in rows[0]:
            values = [r[field] for r in rows]
            fields[field] = dict(types=sorted({type(v).__name__ for v in values if v is not None}),
                                 nullable=any(v is None for v in values))
            if field in REFERENCES.get(table, {}):
                fields[field]['references'] = REFERENCES[table][field]
            if field == 'id' or field.endswith('_id'):
                fields[field]['format'] = 'UUID'
            elif field.endswith('_at') or field in ('as_of', 'scheduled_for', 'assessed_at'):
                fields[field]['format'] = 'aware ISO8601 UTC timestamp'
            elif field.endswith('_date'):
                fields[field]['format'] = 'ISO8601 calendar date'
            if field in ('role', 'blood_group', 'component_type', 'status', 'event_type', 'urgency_level', 'alert_type', 'evidence_kind'):
                fields[field]['observed_values'] = sorted({v for v in values if v is not None})
        dictionary[table] = dict(target_model=TARGETS[table][0], owner=TARGETS[table][1], fields=fields)
        with (target/'csv'/f'{table}.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader()
            for row in rows:
                writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (list, dict, bool)) else v for k, v in row.items()})
    (target/'data_dictionary.json').write_text(encoded(dictionary), encoding='utf-8', newline='\n')
    files = [target/'dataset.json', target/'expected.json', target/'data_dictionary.json', *sorted((target/'csv').glob('*.csv'))]
    manifest = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (target/'manifest.json').write_text(encoded(dict(algorithm='sha256', files=manifest)), encoding='utf-8', newline='\n')


def check_exports(target):
    data = json.loads((target/'dataset.json').read_text(encoding='utf-8'))
    result = validate(data)
    expected = json.loads((target/'expected.json').read_text(encoding='utf-8'))
    if expected != expected_results(data):
        raise ValueError('Golden expectations differ from source records.')
    result['independent_sql'] = reconcile_sql(data, expected)
    manifest = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        path = (target/name).resolve()
        if not path.is_relative_to(target.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Export checksum mismatch.')
    for table, rows in data['tables'].items():
        with (target/'csv'/f'{table}.csv').open(newline='', encoding='utf-8') as stream:
            exported = list(csv.DictReader(stream))
        expected_rows = [{k: '' if v is None else json.dumps(v, sort_keys=True) if isinstance(v, (list, dict, bool)) else str(v) for k, v in row.items()} for row in rows]
        if exported != expected_rows:
            raise ValueError('CSV/JSON discrepancy: '+table)
    return data, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', default='2026-11-16', help='Reference local date; deterministic default, not wall-clock time.')
    parser.add_argument('--output', type=Path, default=DEFAULT)
    parser.add_argument('--check', action='store_true', help='Validate existing exports without rewriting.')
    parser.add_argument('--sqlite', type=Path, help='Optional NEW local reference database; never the Django DB.')
    args = parser.parse_args()
    if args.check:
        data, result = check_exports(args.output)
    else:
        data = generate(args.as_of)
        result = validate(data)
        result['independent_sql'] = reconcile_sql(data, expected_results(data))
        write_exports(data, args.output)
        check_exports(args.output)
    if args.sqlite:
        args.sqlite.parent.mkdir(parents=True, exist_ok=True)
        reference_database(data, args.sqlite).close()
    print(encoded(dict(**result, row_counts={t: len(r) for t, r in data['tables'].items()}, output=str(args.output))))


if __name__ == '__main__':
    main()
