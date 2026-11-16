"""Real request/camp summaries; stock/event boundary doubles are not provider integration."""
from datetime import date, datetime, timedelta, timezone as utc
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.db import DatabaseError
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from blood_requests.tests.helpers import make_request, make_user, signed_in
from reporting.exceptions import ReportingUnavailable
from reporting.selectors.activity import activity_report, report_interval


class BB24Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user('ADMIN')
        cls.requester = make_user('REQUESTER')
        cls.staff = make_user('STAFF')
        cls.donor = make_user('DONOR')
        cls.superuser = make_user('ADMIN', is_superuser=True)
        cls.inactive = make_user('ADMIN', is_active=False)


    def test_date_range_is_inclusive_kolkata_and_half_open_utc(self):
        start, end = report_interval(from_date=date(2026, 11, 15), to_date=date(2026, 11, 15))
        self.assertEqual(start, datetime(2026, 11, 14, 18, 30, tzinfo=utc.utc))
        self.assertEqual(end, datetime(2026, 11, 15, 18, 30, tzinfo=utc.utc))
        self.assertEqual((end - start).total_seconds(), 86400)


    def test_report_contract_uses_approved_counts_and_same_interval(self):
        inventory = {'donation_event_count': 2, 'collected_unit_count': 5, 'wasted_unit_count': 1,
                     'private_donor_email': 'must-not-leak@example.test'}
        with patch('reporting.providers.activity.collection_wastage', return_value=inventory) as collection, \
                patch('reporting.providers.activity.issue_totals', return_value={'issued_unit_count': 3}) as issues:
            result = activity_report(actor=self.admin, from_date=date(2026, 11, 15), to_date=date(2026, 11, 16))
        self.assertEqual(collection.call_args.kwargs, issues.call_args.kwargs)
        self.assertEqual((result['donation_event_count'], result['collected_unit_count'], result['issued_unit_count'], result['wasted_unit_count']), (2, 5, 3, 1))
        self.assertNotIn('private_donor_email', result)
        self.assertEqual(result['timezone'], 'Asia/Kolkata')


    def test_explicit_empty_report_from_real_contract_is_zero(self):
        with patch('reporting.providers.activity.collection_wastage', return_value=dict(donation_event_count=0, collected_unit_count=0, wasted_unit_count=0)), \
                patch('reporting.providers.activity.issue_totals', return_value={'issued_unit_count': 0}):
            result = activity_report(actor=self.admin, from_date=date(2026, 11, 15), to_date=date(2026, 11, 15))
        self.assertEqual(result['issued_unit_count'], 0)


    def test_invalid_range_fails_before_provider_calls(self):
        with patch('reporting.providers.activity.collection_wastage') as source:
            for begin, end in [(date(2026, 11, 16), date(2026, 11, 15)), ('2026-11-15', date(2026, 11, 16)),
                               (date(2026, 11, 15), date.max)]:
                with self.assertRaises(ValidationError):
                    activity_report(actor=self.admin, from_date=begin, to_date=end)
        source.assert_not_called()


    def test_api_query_validation_precedes_missing_provider(self):
        client, _ = signed_in(self.admin)
        for suffix in ('', '?from=2026-11-16&to=2026-11-15', '?from=2026-02-30&to=2026-11-16', '?from=2026-11-15&to=2026-11-16&to=2026-11-17', '?from=2026-11-15&to=2026-11-16&user=x'):
            self.assertEqual(client.get('/api/v1/reports' + suffix).status_code, 400)

    def test_admin_api_returns_minimized_success_only_from_available_providers(self):
        client, _ = signed_in(self.admin)
        with patch('reporting.providers.activity.collection_wastage', return_value=dict(donation_event_count=1, collected_unit_count=2, wasted_unit_count=0)), patch('reporting.providers.activity.issue_totals', return_value={'issued_unit_count': 1}):
            response = client.get('/api/v1/reports?from=2026-11-15&to=2026-11-16')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['donation_event_count'], 1)

    def test_malformed_source_is_not_fabricated_success(self):
        with patch('reporting.providers.activity.collection_wastage', return_value={}), patch('reporting.providers.activity.issue_totals', return_value={'issued_unit_count': 0}):
            with self.assertRaises(ReportingUnavailable):
                activity_report(actor=self.admin, from_date=date(2026, 11, 15), to_date=date(2026, 11, 16))

    def test_missing_real_provider_is_redacted503(self):
        client, _ = signed_in(self.admin)
        with patch('reporting.providers.import_module', side_effect=ModuleNotFoundError):
            response = client.get('/api/v1/reports?from=2026-11-15&to=2026-11-16')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'reporting_unavailable')

    def test_role_boundaries_at_api_and_service(self):
        for actor in (None, AnonymousUser(), self.staff, self.requester, self.donor, self.superuser, self.inactive):
            with self.assertRaises(PermissionDenied):
                activity_report(actor=actor, from_date=date(2026, 11, 15), to_date=date(2026, 11, 16))
        for actor in (self.staff, self.requester, self.donor, self.superuser):
            client, _ = signed_in(actor)
            self.assertEqual(client.get('/api/v1/reports?from=2026-11-15&to=2026-11-16').status_code, 403)
        self.assertEqual(Client().get('/api/v1/reports?from=2026-11-15&to=2026-11-16').json()['error']['code'], 'authentication_required')

    def test_provider_database_failure_is_redacted(self):
        from reporting.providers import invoke
        with patch('reporting.providers.import_module') as module:
            module.return_value.read.side_effect = DatabaseError('private connection')
            with self.assertRaises(ReportingUnavailable) as error:
                invoke('constant.test.provider', 'read')
        self.assertNotIn('private', str(error.exception))

    def test_story_page_shell_does_not_require_source_data(self):
        client, _ = signed_in(self.admin)
        self.assertEqual(client.get('/reports').status_code, 200)

    def test_reports_page_rejects_anonymous_and_non_operational_admins(self):
        self.assertEqual(Client().get('/reports').status_code, 403)
        for actor in (self.staff, self.requester, self.donor, self.superuser, self.inactive):
            with self.subTest(role=actor.role, active=actor.is_active, superuser=actor.is_superuser):
                client = Client()
                client.force_login(actor)
                response = client.get('/reports')
                self.assertEqual(response.status_code, 403)
                self.assertNotContains(response, 'Read-only synthetic snapshot', status_code=403)
