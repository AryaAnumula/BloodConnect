from copy import deepcopy
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings

from blood_requests.tests.helpers import make_user, signed_in
from reporting.tests.synthetic_fixture import fixture, write_snapshot
from reporting.exceptions import ReportingUnavailable


@override_settings(DEBUG=True, BLOODCONNECT_REPORT_SOURCE='synthetic')
class SyntheticDashboardTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data = fixture()
        self.path = write_snapshot(self.directory.name, self.data)
        self.override = override_settings(BLOODCONNECT_DEMO_DATASET_PATH=str(self.path))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.client, _ = signed_in(make_user('ADMIN'))

    def test_file_records_reconcile_through_actual_admin_api(self):
        response = self.client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-BloodConnect-Data-Source'], 'synthetic')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.json(), {'as_of': self.data['metadata']['as_of'], 'pending_requests': 1, 'upcoming_camps': 2,
                                          'stock': [{'blood_group': 'O+', 'component_type': 'RBC', 'available_quantity': 1}]})

    def test_refresh_reloads_changed_source_records_without_caching_totals(self):
        self.assertEqual(self.client.get('/api/v1/dashboard').json()['pending_requests'], 1)
        self.data['tables']['blood_requests'][0]['status'] = 'APPROVED'
        self.data['tables']['camps'][0]['status'] = 'CANCELLED'
        write_snapshot(self.directory.name, self.data)
        result = self.client.get('/api/v1/dashboard').json()
        self.assertEqual((result['pending_requests'], result['upcoming_camps']), (0, 1))

    def test_empty_available_snapshot_returns_genuine_zeroes(self):
        self.data['tables'] = {name: [] for name in self.data['tables']}
        write_snapshot(self.directory.name, self.data)
        response = self.client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['stock'], response.json()['pending_requests']), ([], 0))

    def test_missing_corrupt_unverified_source_never_falls_back_or_leaks_path(self):
        self.path.write_text('{}', encoding='utf-8')
        for path in (self.path, Path(self.directory.name)/'missing.json'):
            with override_settings(BLOODCONNECT_DEMO_DATASET_PATH=str(path)):
                response = self.client.get('/api/v1/dashboard')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(self.directory.name, response.content.decode())

    def test_malformed_or_duplicate_source_rows_fail_closed(self):
        for mutate in (lambda d: d['tables']['blood_units'][0].update(quantity=True),
                       lambda d: d['tables']['blood_units'].append(deepcopy(d['tables']['blood_units'][0])),
                       lambda d: d['tables']['camps'][0].update(starts_at='invalid')):
            changed = fixture()
            mutate(changed)
            write_snapshot(self.directory.name, changed)
            self.assertEqual(self.client.get('/api/v1/dashboard').status_code, 503)

    def test_source_mode_needs_explicit_local_setting_and_keeps_domain_failure(self):
        for settings in ({'DEBUG': False}, {'BLOODCONNECT_REPORT_SOURCE': 'unknown'}):
            with override_settings(**settings):
                self.assertEqual(self.client.get('/api/v1/dashboard').status_code, 503)

    def test_domain_failure_is_explicit_and_never_falls_back_to_snapshot(self):
        with override_settings(BLOODCONNECT_REPORT_SOURCE='domain'), patch(
            'reporting.providers.dashboard.current_stock', side_effect=ReportingUnavailable,
        ):
            response = self.client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'reporting_unavailable')

    def test_domain_mode_uses_its_providers_when_a_valid_snapshot_also_exists(self):
        # Orchestration boundary test; real providers are reconciled in explicit acceptance.
        with override_settings(BLOODCONNECT_REPORT_SOURCE='domain'), patch(
            'reporting.providers.dashboard.current_stock', return_value={'count': 0, 'results': []},
        ), patch('reporting.providers.dashboard.pending_requests', return_value=7), patch(
            'reporting.providers.dashboard.upcoming_camps', return_value=4,
        ):
            response = self.client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-BloodConnect-Data-Source'], 'domain')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual((response.json()['stock'], response.json()['pending_requests'],
                          response.json()['upcoming_camps']), ([], 7, 4))

    def test_invalid_collection_links_status_and_dates_fail_closed(self):
        mutations = (
            lambda d: d['tables']['blood_units'][0].update(collection_event_id='missing'),
            lambda d: d['tables']['collection_events'][0].update(status='UNCONFIRMED'),
            lambda d: d['tables']['collection_events'][0].update(collection_date='2026-11-14'),
            lambda d: d['tables']['collection_events'].append(deepcopy(d['tables']['collection_events'][0])),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                changed = fixture()
                mutate(changed)
                write_snapshot(self.directory.name, changed)
                response = self.client.get('/api/v1/dashboard')
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()['error']['code'], 'reporting_unavailable')
                self.assertNotIn(self.directory.name, response.content.decode())

    def test_invalid_request_group_and_component_fail_closed(self):
        for field, value in (('blood_group', 'INVALID'), ('component_type', 'INVALID')):
            with self.subTest(field=field):
                changed = fixture()
                changed['tables']['blood_requests'][0][field] = value
                write_snapshot(self.directory.name, changed)
                response = self.client.get('/api/v1/dashboard')
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()['error']['code'], 'reporting_unavailable')

    def test_permission_check_precedes_dataset_read(self):
        client, _ = signed_in(make_user('STAFF'))
        with override_settings(BLOODCONNECT_DEMO_DATASET_PATH='missing'):
            self.assertEqual(client.get('/api/v1/dashboard').status_code, 403)

    def test_shell_labels_snapshot_and_does_not_publish_source_rows(self):
        response = self.client.get('/dashboard')
        self.assertContains(response, 'Read-only synthetic snapshot')
        self.assertNotContains(response, self.directory.name)
        self.assertNotContains(response, 'demo.example.test')
