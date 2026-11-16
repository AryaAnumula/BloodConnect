"""Meaningful source mutations and independent SQL/export checks, no application doubles."""
from copy import deepcopy
from datetime import date
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from core.demo_data.generate import generate
from core.demo_data.reference import expected_results, reconcile_sql, reference_database
from core.demo_data.validate import validate

spec = importlib.util.spec_from_file_location('dataset_cli', ROOT/'scripts/generate_synthetic_dataset.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = generate()

    def mutation_rejected(self, mutate, message):
        changed = deepcopy(self.data)
        mutate(changed['tables'])
        with self.assertRaisesRegex((ValueError, KeyError), message):
            validate(changed)

    def test_complete_deterministic_connected_data(self):
        self.assertEqual(self.data, generate())
        result = validate(self.data)
        self.assertEqual(result['tables'], 15)
        self.assertEqual(len({(u['blood_group'], u['component_type']) for u in self.data['tables']['blood_units']}), 32)

    def test_independent_sql_stock_reports_and_empty_range(self):
        expected = expected_results(self.data)
        self.assertEqual(reconcile_sql(self.data, expected)['report_ranges'], 5)
        self.assertEqual(sum(s['available_quantity'] for s in expected['dashboard']['stock']), 316)
        self.assertEqual((expected['dashboard']['pending_requests'], expected['dashboard']['upcoming_camps']), (40, 6))
        reports = {r['name']: r for r in expected['reports']}
        self.assertEqual((reports['full_history']['donation_event_count'], reports['full_history']['collected_unit_count'], reports['full_history']['issued_unit_count'], reports['full_history']['wasted_unit_count']), (400, 500, 60, 25))
        self.assertEqual(reports['today']['issued_unit_count'], 59)
        self.assertEqual(reports['yesterday']['issued_unit_count'], 1)
        self.assertEqual(reports['empty_range']['donation_event_count'], 0)

    def test_regeneration_on_leap_day_keeps_relationships_and_totals(self):
        data = generate('2028-02-29')
        validate(data)
        reconcile_sql(data, expected_results(data))

    def test_export_roundtrip_checksum_and_repeated_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            cli.write_exports(self.data, target)
            snapshot = {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()}
            cli.check_exports(target)
            cli.write_exports(self.data, target)
            self.assertEqual(snapshot, {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()})
            with (target/'csv/accounts.csv').open('a', encoding='utf-8') as stream:
                stream.write('modified\n')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                cli.check_exports(target)

    def test_golden_totals_cannot_be_silently_invented(self):
        expected = expected_results(self.data)
        expected['dashboard']['pending_requests'] = 999
        with self.assertRaisesRegex(ValueError, 'dashboard'):
            reconcile_sql(self.data, expected)

    def test_donor_history_projection_mismatch_rejected(self):
        self.mutation_rejected(lambda t: t['donors'][0].update(last_confirmed_collection_date=None), 'projection')

    def test_historical_assessment_not_rewritten_to_new_history(self):
        self.mutation_rejected(lambda t: t['screenings'][0].update(confirmed_collection_date=t['collection_events'][0]['collection_date']), 'snapshot')

    def test_component_and_donation_lineage_rejected(self):
        self.mutation_rejected(lambda t: t['blood_units'][1].update(component_type=t['blood_units'][0]['component_type']), 'component')
        self.mutation_rejected(lambda t: t['blood_units'][0].update(donor_id=t['donors'][1]['id']), 'lineage')

    def test_missing_actual_issue_history_cannot_be_covered_by_fulfilled_total(self):
        self.mutation_rejected(lambda t: t['issue_records'].pop(), 'issue history')

    def test_zero_quantity_and_overfulfilled_requests_rejected(self):
        self.mutation_rejected(lambda t: t['blood_units'][0].update(quantity=0), 'quantity')
        self.mutation_rejected(lambda t: t['blood_requests'][0].update(fulfilled_quantity=1), 'Fulfilment')

    def test_expiry_alone_does_not_create_wastage(self):
        expected = expected_results(self.data)
        self.assertTrue(expected['expired_available_unit_codes'])
        self.assertEqual(expected['reports'][3]['wasted_unit_count'], 25)
        self.mutation_rejected(lambda t: t['inventory_dispositions'].pop(), 'disposition history')

    def test_capacity_and_cancelled_camp_guards(self):
        self.mutation_rejected(lambda t: t['slots'][0].update(capacity=0), 'capacity')
        self.mutation_rejected(lambda t: t['camps'][0].update(status='CANCELLED', cancelled_at=self.data['metadata']['as_of']), 'cancelled camp')

    def test_recipient_identity_and_late_timing_outcome(self):
        scenarios = self.data['scenarios']
        reminders = {r['record_id']: r for r in self.data['tables']['outbox_intents'] if r['event_type'] == 'APPOINTMENT_REMINDER'}
        early, late = reminders[scenarios['on_time_reminder']], reminders[scenarios['late_reminder']]
        self.assertEqual((early['late_booking'], early['timing_met']), (False, True))
        self.assertEqual((late['late_booking'], late['timing_met']), (True, False))
        self.mutation_rejected(lambda t: t['outbox_intents'][0].update(recipient_id=t['donors'][400]['id']), 'recipient')

    def test_reference_sqlite_is_separate_and_existing_database_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'reference.sqlite3'
            db = reference_database(self.data, path)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM blood_units').fetchone()[0], 500)
            db.close()
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'already exists'):
                reference_database(self.data, path)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
