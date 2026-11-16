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
from reporting.selectors.dashboard import dashboard_for_admin


class BB23Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user('ADMIN')
        cls.requester = make_user('REQUESTER')
        cls.staff = make_user('STAFF')
        cls.donor = make_user('DONOR')
        cls.superuser = make_user('ADMIN', is_superuser=True)
        cls.inactive = make_user('ADMIN', is_active=False)


    def test_bad_or_incomplete_provider_dto_fails_closed(self):
        bad_pages = [{}, {'count': True, 'results': []}, {'count': 1, 'results': []},
                     {'count': 1, 'results': [{'blood_group': 'O+', 'component_type': 'RBC', 'available_quantity': -1}]},
                     {'count': 1, 'results': [{'blood_group': 'O+', 'component_type': 'RBC', 'available_units': 3}]}]
        for data in bad_pages:
            with self.subTest(data=data), patch('reporting.providers.dashboard.current_stock', return_value=data):
                with self.assertRaises(ReportingUnavailable):
                    dashboard_for_admin(actor=self.admin, now=timezone.now())


    def test_real_pending_count_refreshes_after_underlying_review_change(self):
        row = make_request(self.requester)
        with patch('reporting.providers.dashboard.current_stock', return_value={'count': 0, 'results': []}), patch('reporting.providers.dashboard.upcoming_camps', return_value=0):
            first = dashboard_for_admin(actor=self.admin, now=timezone.now())
            from blood_requests.services.review import review_request
            review_request(actor=self.staff, request_id=row.id, status='APPROVED')
            second = dashboard_for_admin(actor=self.admin, now=timezone.now())
        self.assertEqual((first['pending_requests'], second['pending_requests']), (1, 0))


    def test_actual_requests_and_camp_boundary_are_aggregated_without_private_fields(self):
        make_request(self.requester)
        make_request(self.requester, status='APPROVED')
        stock = {'count': 1, 'results': [{'blood_group': 'O+', 'component_type': 'RBC', 'available_quantity': 3, 'private': 'hidden'}]}
        now = timezone.now()
        with patch('reporting.providers.dashboard.current_stock', return_value=stock), patch('reporting.providers.dashboard.upcoming_camps', return_value=2) as camps:
            result = dashboard_for_admin(actor=self.admin, now=now)
        self.assertEqual((result['pending_requests'], result['upcoming_camps']), (1, 2))
        self.assertEqual(camps.call_args.kwargs, {'now': now})
        self.assertNotIn('private', result['stock'][0])

    def test_available_empty_sources_return_zero_and_missing_camp_provider_is_503(self):
        with patch('reporting.providers.dashboard.current_stock', return_value={'count': 0, 'results': []}):
            with patch('reporting.providers.dashboard.upcoming_camps', side_effect=ReportingUnavailable):
                with self.assertRaises(ReportingUnavailable):
                    dashboard_for_admin(actor=self.admin, now=timezone.now())
            with patch('reporting.providers.dashboard.upcoming_camps', return_value=0):
                result = dashboard_for_admin(actor=self.admin, now=timezone.now())
        self.assertEqual((result['pending_requests'], result['upcoming_camps'], result['stock']), (0, 0, []))

    def test_admin_api_success_and_query_validation(self):
        client, _ = signed_in(self.admin)
        with patch('reporting.providers.dashboard.current_stock', return_value={'count': 0, 'results': []}), patch('reporting.providers.dashboard.upcoming_camps', return_value=0):
            response = client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['pending_requests'], 0)
        self.assertEqual(client.get('/api/v1/dashboard?status=SUBMITTED').status_code, 400)

    def test_server_timestamp_must_be_aware(self):
        with self.assertRaises(ValidationError):
            dashboard_for_admin(actor=self.admin, now=datetime(2026, 11, 16))

    def test_missing_real_provider_is_redacted503(self):
        client, _ = signed_in(self.admin)
        with patch('reporting.providers.import_module', side_effect=ModuleNotFoundError):
            response = client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'reporting_unavailable')

    def test_role_boundaries_at_api_and_service(self):
        for actor in (None, AnonymousUser(), self.staff, self.requester, self.donor, self.superuser, self.inactive):
            with self.assertRaises(PermissionDenied):
                dashboard_for_admin(actor=actor, now=timezone.now())
        for actor in (self.staff, self.requester, self.donor, self.superuser):
            client, _ = signed_in(actor)
            self.assertEqual(client.get('/api/v1/dashboard').status_code, 403)
        self.assertEqual(Client().get('/api/v1/dashboard').json()['error']['code'], 'authentication_required')

    def test_provider_database_failure_is_redacted(self):
        from reporting.providers import invoke
        with patch('reporting.providers.import_module') as module:
            module.return_value.read.side_effect = DatabaseError('private connection')
            with self.assertRaises(ReportingUnavailable) as error:
                invoke('constant.test.provider', 'read')
        self.assertNotIn('private', str(error.exception))

    def test_story_page_shell_does_not_require_source_data(self):
        client, _ = signed_in(self.admin)
        self.assertEqual(client.get('/dashboard').status_code, 200)

    def test_dashboard_page_rejects_anonymous_and_non_operational_admins(self):
        self.assertEqual(Client().get('/dashboard').status_code, 403)
        for actor in (self.staff, self.requester, self.donor, self.superuser, self.inactive):
            with self.subTest(role=actor.role, active=actor.is_active, superuser=actor.is_superuser):
                client = Client()
                client.force_login(actor)
                response = client.get('/dashboard')
                self.assertEqual(response.status_code, 403)
                self.assertNotContains(response, 'Read-only synthetic snapshot', status_code=403)
