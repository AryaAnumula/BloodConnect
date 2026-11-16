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
from reporting.selectors.dashboard import dashboard_for_admin
from scheduling.tests.helpers import make_camp


class ReportingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user('ADMIN')
        cls.requester = make_user('REQUESTER')
        cls.staff = make_user('STAFF')
        cls.donor = make_user('DONOR')
        cls.superuser = make_user('ADMIN', is_superuser=True)
        cls.inactive = make_user('ADMIN', is_active=False)

    def test_dashboard_reconciles_real_request_camp_states_and_boundary(self):
        now = timezone.now()
        make_request(self.requester)
        make_request(self.requester, status='APPROVED')
        make_request(self.requester, status='REJECTED')
        make_camp(starts_at=now, ends_at=now + timedelta(hours=1))
        make_camp(starts_at=now + timedelta(days=1), ends_at=now + timedelta(days=2))
        make_camp(starts_at=now - timedelta(days=2), ends_at=now - timedelta(days=1))
        make_camp(status='CANCELLED')
        stock = {'count': 1, 'results': [{'blood_group': 'O+', 'component_type': 'RBC', 'available_quantity': 3}]}
        with patch('reporting.providers.current_stock', return_value=stock):
            result = dashboard_for_admin(actor=self.admin, now=now)
        self.assertEqual((result['pending_requests'], result['upcoming_camps']), (1, 2))
        self.assertEqual(result['stock'], stock['results'])
        self.assertEqual(set(result), {'as_of', 'stock', 'pending_requests', 'upcoming_camps'})

    def test_empty_real_sources_and_explicit_empty_stock_are_valid_zeroes(self):
        with patch('reporting.providers.current_stock', return_value={'count': 0, 'results': []}):
            result = dashboard_for_admin(actor=self.admin, now=timezone.now())
        self.assertEqual((result['pending_requests'], result['upcoming_camps'], result['stock']), (0, 0, []))

    def test_missing_real_providers_are_unavailable_not_invented_success(self):
        with self.assertRaises(ReportingUnavailable):
            dashboard_for_admin(actor=self.admin, now=timezone.now())
        with self.assertRaises(ReportingUnavailable):
            activity_report(actor=self.admin, from_date=date(2026, 11, 15), to_date=date(2026, 11, 16))
        client, _ = signed_in(self.admin)
        for path in ('/api/v1/dashboard', '/api/v1/reports?from=2026-11-15&to=2026-11-16'):
            response = client.get(path)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()['error']['code'], 'reporting_unavailable')
            self.assertNotIn('pending_requests', response.json())

    def test_bad_or_incomplete_provider_dto_fails_closed(self):
        bad_pages = [{}, {'count': True, 'results': []}, {'count': 1, 'results': []},
                     {'count': 1, 'results': [{'blood_group': 'O+', 'component_type': 'RBC', 'available_quantity': -1}]},
                     {'count': 1, 'results': [{'blood_group': 'O+', 'component_type': 'RBC', 'available_units': 3}]}]
        for data in bad_pages:
            with self.subTest(data=data), patch('reporting.providers.current_stock', return_value=data):
                with self.assertRaises(ReportingUnavailable):
                    dashboard_for_admin(actor=self.admin, now=timezone.now())

    def test_date_range_is_inclusive_kolkata_and_half_open_utc(self):
        start, end = report_interval(from_date=date(2026, 11, 15), to_date=date(2026, 11, 15))
        self.assertEqual(start, datetime(2026, 11, 14, 18, 30, tzinfo=utc.utc))
        self.assertEqual(end, datetime(2026, 11, 15, 18, 30, tzinfo=utc.utc))
        self.assertEqual((end - start).total_seconds(), 86400)

    def test_real_pending_count_refreshes_after_underlying_review_change(self):
        row = make_request(self.requester)
        with patch('reporting.providers.current_stock', return_value={'count': 0, 'results': []}):
            first = dashboard_for_admin(actor=self.admin, now=timezone.now())
            from blood_requests.services.review import review_request
            review_request(actor=self.staff, request_id=row.id, status='APPROVED')
            second = dashboard_for_admin(actor=self.admin, now=timezone.now())
        self.assertEqual((first['pending_requests'], second['pending_requests']), (1, 0))

    def test_report_contract_uses_approved_counts_and_same_interval(self):
        inventory = {'donation_event_count': 2, 'collected_unit_count': 5, 'wasted_unit_count': 1,
                     'private_donor_email': 'must-not-leak@example.test'}
        with patch('reporting.providers.collection_wastage', return_value=inventory) as collection, \
                patch('reporting.providers.issue_totals', return_value={'issued_unit_count': 3}) as issues:
            result = activity_report(actor=self.admin, from_date=date(2026, 11, 15), to_date=date(2026, 11, 16))
        self.assertEqual(collection.call_args.kwargs, issues.call_args.kwargs)
        self.assertEqual((result['donation_event_count'], result['collected_unit_count'], result['issued_unit_count'], result['wasted_unit_count']), (2, 5, 3, 1))
        self.assertNotIn('private_donor_email', result)
        self.assertEqual(result['timezone'], 'Asia/Kolkata')

    def test_explicit_empty_report_from_real_contract_is_zero(self):
        with patch('reporting.providers.collection_wastage', return_value=dict(donation_event_count=0, collected_unit_count=0, wasted_unit_count=0)), \
                patch('reporting.providers.issue_totals', return_value={'issued_unit_count': 0}):
            result = activity_report(actor=self.admin, from_date=date(2026, 11, 15), to_date=date(2026, 11, 15))
        self.assertEqual(result['issued_unit_count'], 0)

    def test_invalid_range_fails_before_provider_calls(self):
        with patch('reporting.providers.collection_wastage') as source:
            for begin, end in [(date(2026, 11, 16), date(2026, 11, 15)), ('2026-11-15', date(2026, 11, 16)),
                               (date(2026, 11, 15), date.max)]:
                with self.assertRaises(ValidationError):
                    activity_report(actor=self.admin, from_date=begin, to_date=end)
        source.assert_not_called()

    def test_api_query_validation_precedes_missing_provider(self):
        client, _ = signed_in(self.admin)
        for suffix in ('', '?from=2026-11-16&to=2026-11-15', '?from=2026-02-30&to=2026-11-16',
                       '?from=2026-11-15&to=2026-11-16&to=2026-11-17', '?from=2026-11-15&to=2026-11-16&user=x'):
            self.assertEqual(client.get('/api/v1/reports' + suffix).status_code, 400)
        self.assertEqual(client.get('/api/v1/dashboard?status=SUBMITTED').status_code, 400)

    def test_all_role_boundaries_and_direct_service_guards(self):
        for actor in (None, AnonymousUser(), self.staff, self.requester, self.donor, self.superuser, self.inactive):
            with self.subTest(actor=getattr(actor, 'role', None)):
                with self.assertRaises(PermissionDenied):
                    dashboard_for_admin(actor=actor, now=timezone.now())
                with self.assertRaises(PermissionDenied):
                    activity_report(actor=actor, from_date=date(2026, 11, 15), to_date=date(2026, 11, 15))
        for actor in (self.staff, self.requester, self.donor, self.superuser):
            client, _ = signed_in(actor)
            self.assertEqual(client.get('/api/v1/dashboard').status_code, 403)
            self.assertEqual(client.get('/api/v1/reports').status_code, 403)
        self.assertEqual(Client().get('/api/v1/dashboard').json()['error']['code'], 'authentication_required')

    def test_provider_database_failure_is_redacted(self):
        from reporting.providers import invoke
        with patch('blood_requests.selectors.reporting.pending_request_count', side_effect=DatabaseError('private connection')):
            with self.assertRaises(ReportingUnavailable) as error:
                invoke('blood_requests.selectors.reporting', 'pending_request_count')
        self.assertNotIn('private', str(error.exception))

    def test_pages_are_public_shells_without_private_data(self):
        self.assertEqual(Client().get('/dashboard').status_code, 200)
        self.assertEqual(Client().get('/reports').status_code, 200)
