"""Small, synthetic reference checks: no full-size account dataset is created."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from core.demo_data.reference import expected_results, reconcile_sql, reference_database


def fixture():
    return {
        'metadata': {'as_of': '2026-11-16T12:00:00+00:00'},
        'tables': {
            'accounts': [{'id': 'a1'}],
            'blood_units': [
                {'id': 'u1', 'blood_group': 'A+', 'component_type': 'RBC', 'quantity': 1,
                 'status': 'AVAILABLE', 'expiry_date': '2026-11-17', 'collection_date': '2026-11-16', 'unit_code': 'good'},
                {'id': 'u2', 'blood_group': 'A+', 'component_type': 'RBC', 'quantity': 1,
                 'status': 'AVAILABLE', 'expiry_date': '2026-11-16', 'collection_date': '2026-11-15', 'unit_code': 'expired'},
                {'id': 'u3', 'blood_group': 'O-', 'component_type': 'PLASMA', 'quantity': 1,
                 'status': 'QUARANTINED', 'expiry_date': '2026-11-18', 'collection_date': '2026-11-16', 'unit_code': 'held'},
            ],
            'blood_requests': [{'id': 'r1', 'status': 'SUBMITTED'}, {'id': 'r2', 'status': 'APPROVED'}],
            'camps': [{'id': 'c1', 'status': 'ACTIVE', 'starts_at': '2026-11-16T12:00:00.000000+00:00'},
                      {'id': 'c2', 'status': 'CANCELLED', 'starts_at': '2026-11-17T12:00:00.000000+00:00'}],
            'collection_events': [{'id': 'e1', 'status': 'CONFIRMED', 'collection_date': '2026-11-16'},
                                  {'id': 'e2', 'status': 'OTHER', 'collection_date': '2026-11-16'}],
            'issue_records': [{'id': 'i1', 'quantity': 1, 'issued_at': '2026-11-16T12:00:00.000000+00:00'}],
            'inventory_dispositions': [{'id': 'd1', 'to_status': 'DISCARDED', 'occurred_at': '2026-11-16T12:00:00.000000+00:00'},
                                       {'id': 'd2', 'to_status': 'QUARANTINED', 'occurred_at': '2026-11-16T12:00:00.000000+00:00'}],
            'stock_alerts': [{'id': 's1', 'alert_type': 'LOW_STOCK'}, {'id': 's2', 'alert_type': 'NEAR_EXPIRY'}],
        },
    }


class ReferenceBoundaryTests(TestCase):
    def test_results_and_sql_reconcile_with_boundary_and_status_cases(self):
        data = fixture()
        expected = expected_results(data)
        self.assertEqual(expected['dashboard']['stock'][0]['available_quantity'], 1)
        self.assertEqual(expected['dashboard']['pending_requests'], 1)
        self.assertEqual(expected['dashboard']['upcoming_camps'], 1)
        self.assertEqual(expected['expired_available_unit_codes'], ['expired'])
        self.assertEqual((expected['low_stock_alert_count'], expected['near_expiry_alert_count']), (1, 1))
        self.assertEqual(reconcile_sql(data, expected), {'stock_and_dashboard': 'PASS', 'report_ranges': 5})

    def test_reconciliation_rejects_wrong_stock_dashboard_and_report(self):
        data = fixture()
        for change, message in [('stock', 'stock'), ('dashboard', 'dashboard'), ('report', 'report')]:
            expected = deepcopy(expected_results(data))
            if change == 'stock': expected['dashboard']['stock'] = []
            elif change == 'dashboard': expected['dashboard']['pending_requests'] += 1
            else: expected['reports'][0]['issued_unit_count'] += 1
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                reconcile_sql(data, expected)

    def test_reference_rejects_existing_path_and_invalid_schema(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'existing.db'
            path.write_text('preserved')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                reference_database(fixture(), path)
            self.assertEqual(path.read_text(), 'preserved')
        for table, rows in [('bad-name', [{'id': '1'}]), ('empty', []), ('valid', [{'bad key': '1'}])]:
            with self.subTest(table=table), self.assertRaises(ValueError):
                reference_database({'tables': {table: rows}})

    def test_nested_values_are_serialized_in_reference_store(self):
        db = reference_database({'tables': {'items': [{'id': 'one', 'data': ['x']}]}})
        try:
            self.assertEqual(db.execute('select data from items').fetchone()[0], '["x"]')
        finally:
            db.close()
