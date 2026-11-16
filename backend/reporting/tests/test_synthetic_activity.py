from copy import deepcopy
from pathlib import Path
import tempfile

from django.test import TestCase, override_settings

from blood_requests.tests.helpers import make_user, signed_in
from reporting.tests.synthetic_fixture import fixture, write_snapshot


@override_settings(DEBUG=True, BLOODCONNECT_REPORT_SOURCE='synthetic')
class SyntheticActivityTests(TestCase):
    path = '/api/v1/reports?from=2026-11-16&to=2026-11-16'

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data = fixture()
        self.source = write_snapshot(self.directory.name, self.data)
        self.override = override_settings(BLOODCONNECT_DEMO_DATASET_PATH=str(self.source))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.client, _ = signed_in(make_user('ADMIN'))

    def test_actual_api_counts_events_units_and_midnight_issue_separately(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-BloodConnect-Data-Source'], 'synthetic')
        self.assertEqual(response['Cache-Control'], 'no-store')
        body = response.json()
        self.assertEqual((body['donation_event_count'], body['collected_unit_count'], body['issued_unit_count'], body['wasted_unit_count']), (0, 0, 1, 0))
        yesterday = self.client.get('/api/v1/reports?from=2026-11-15&to=2026-11-15').json()
        self.assertEqual((yesterday['donation_event_count'], yesterday['collected_unit_count'], yesterday['issued_unit_count'], yesterday['wasted_unit_count']), (3, 4, 0, 1))

    def test_expired_available_and_quarantine_do_not_become_wastage(self):
        result = self.client.get('/api/v1/reports?from=2026-11-01&to=2026-11-30').json()
        self.assertEqual((result['donation_event_count'], result['collected_unit_count'], result['wasted_unit_count']), (4, 5, 1))

    def test_empty_available_range_is_valid_zero(self):
        response = self.client.get('/api/v1/reports?from=2025-01-01&to=2025-01-02')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['issued_unit_count'], 0)

    def test_incomplete_issue_or_disposition_history_rejected(self):
        for table in ('issue_records', 'inventory_dispositions'):
            changed = fixture()
            changed['tables'][table].pop()
            write_snapshot(self.directory.name, changed)
            self.assertEqual(self.client.get(self.path).status_code, 503)

    def test_refresh_reloads_updated_explicit_source_timestamp(self):
        self.assertEqual(self.client.get(self.path).json()['wasted_unit_count'], 0)
        self.data['tables']['inventory_dispositions'][0]['occurred_at'] = '2026-11-15T18:30:00Z'
        write_snapshot(self.directory.name, self.data)
        self.assertEqual(self.client.get(self.path).json()['wasted_unit_count'], 1)

    def test_unknown_unit_status_fails_closed_even_outside_the_report_range(self):
        self.data['tables']['blood_units'][0]['status'] = 'NOT_A_UNIT_STATE'
        write_snapshot(self.directory.name, self.data)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'reporting_unavailable')
        self.assertNotIn(self.directory.name, response.content.decode())

    def test_source_errors_are_redacted_and_invalid_query_is_checked_first(self):
        self.source.write_text('{}', encoding='utf-8')
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(self.directory.name, response.content.decode())
        self.assertEqual(self.client.get('/api/v1/reports?from=bad&to=bad').status_code, 400)

    def test_non_local_unknown_mode_and_wrong_role_stay_denied(self):
        for settings in ({'DEBUG': False}, {'BLOODCONNECT_REPORT_SOURCE': 'unknown'}, {'BLOODCONNECT_REPORT_SOURCE': 'domain'}):
            with override_settings(**settings):
                self.assertEqual(self.client.get(self.path).status_code, 503)
        client, _ = signed_in(make_user('REQUESTER'))
        self.assertEqual(client.get(self.path).status_code, 403)

    def test_report_page_labels_the_snapshot_without_raw_records(self):
        response = self.client.get('/reports')
        self.assertContains(response, 'Read-only synthetic snapshot')
        self.assertNotContains(response, self.directory.name)
