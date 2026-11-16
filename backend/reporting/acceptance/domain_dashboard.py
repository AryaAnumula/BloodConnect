"""Explicit BB23 real-domain acceptance. Missing real dependencies FAIL readiness.

python backend/manage.py test reporting.acceptance.domain_dashboard --noinput
No actual success provider is mocked. Fixture inventory states are source reconciliation setup.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from blood_requests.models import BloodRequest
from blood_requests.services.review import review_request
from blood_requests.tests.helpers import make_request, signed_in
from reporting.acceptance.fixtures import require_models, source_unit, user
from reporting.selectors.dashboard import dashboard_for_admin


@override_settings(BLOODCONNECT_REPORT_SOURCE='domain')
class RealDomainDashboardAcceptance(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.Event, cls.Unit, cls.Disposition, cls.Camp = require_models(
            'inventory.CollectionEvent', 'inventory.BloodUnit',
            'inventory.InventoryDisposition', 'scheduling.Camp',
        )
        from inventory.selectors.stock import stock_summary
        from scheduling.selectors.summary import upcoming_camp_count
        if not callable(stock_summary) or not callable(upcoming_camp_count):
            raise RuntimeError('Actual stock and camp summary providers are required.')
        super().setUpClass()

    def setUp(self):
        self.admin, self.staff, self.owner = user(), user('STAFF'), user('REQUESTER')
        self.client, _ = signed_in(self.admin)

    def camp(self, starts, status='ACTIVE'):
        return self.Camp.objects.create(
            name='Synthetic report camp', location='Demo City', starts_at=starts,
            ends_at=starts + timedelta(hours=2), capacity=10, status=status,
        )

    def test_real_sources_reconcile_and_camp_boundary_is_inclusive(self):
        now = timezone.now()
        source_unit(actor=self.staff)
        source_unit(actor=self.staff, status='ISSUED')
        source_unit(actor=self.staff, status='DISCARDED')
        source_unit(actor=self.staff, status='QUARANTINED')
        source_unit(actor=self.staff, collected=timezone.localdate()-timedelta(days=42),
                    expiry=timezone.localdate())
        make_request(self.owner)
        make_request(self.owner, status='APPROVED')
        self.camp(now-timedelta(microseconds=1))
        self.camp(now)
        self.camp(now+timedelta(days=1))
        self.camp(now+timedelta(days=2), 'CANCELLED')
        result = dashboard_for_admin(actor=self.admin, now=now)
        self.assertEqual(result, {
            'as_of': now.isoformat(), 'pending_requests': 1, 'upcoming_camps': 2,
            'stock': [{'blood_group': 'A+', 'component_type': 'RBC', 'available_quantity': 1}],
        })
        from scheduling.selectors.summary import upcoming_camp_count
        self.assertEqual(upcoming_camp_count(now=now), 2)
        with self.assertRaises(ValidationError):
            upcoming_camp_count(now=datetime(2026, 11, 16))
        with self.assertRaises(ValidationError):
            upcoming_camp_count(now='2026-11-16')

    def test_http_refresh_uses_actual_review_disposition_and_camp_creation(self):
        unit = source_unit(actor=self.staff)
        request = make_request(self.owner)
        first = self.client.get('/api/v1/dashboard')
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(first['X-BloodConnect-Data-Source'], 'domain')
        self.assertEqual(first['Cache-Control'], 'no-store')
        self.assertEqual((first.json()['pending_requests'], first.json()['upcoming_camps']), (1, 0))
        review_request(actor=self.staff, request_id=request.pk, status='APPROVED')
        from inventory.services.dispositions import record_disposition
        record_disposition(actor=self.staff, unit_id=unit.pk,
                           data={'status': 'DISCARDED', 'reason': 'Synthetic acceptance disposition'})
        from scheduling.services.camps import create_camp
        start = timezone.now()+timedelta(days=2)
        create_camp(actor=self.staff, data=dict(name='New synthetic camp', location='Demo City',
                    starts_at=start, ends_at=start+timedelta(hours=2), capacity=10))
        second = self.client.get('/api/v1/dashboard')
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual((second.json()['stock'], second.json()['pending_requests'],
                          second.json()['upcoming_camps']), ([], 0, 1))
        self.assertEqual(BloodRequest.objects.get(pk=request.pk).status, 'APPROVED')

    def test_real_empty_sources_are_zero_and_actual_source_failure_is_unavailable(self):
        result = self.client.get('/api/v1/dashboard')
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual((result.json()['stock'], result.json()['pending_requests'],
                          result.json()['upcoming_camps']), ([], 0, 0))
        with patch('inventory.selectors.stock.usable_units',
                   side_effect=DatabaseError('private connection fixture')):
            failed = self.client.get('/api/v1/dashboard')
        self.assertEqual(failed.status_code, 503)
        self.assertNotIn('private connection', failed.content.decode())
        self.assertNotIn('stock', failed.json())

    def test_actual_data_does_not_bypass_admin_or_page_access(self):
        source_unit(actor=self.staff)
        self.assertEqual(self.client.get('/dashboard').status_code, 200)
        self.assertEqual(Client().get('/api/v1/dashboard').status_code, 403)
        for actor in (self.staff, self.owner, user('DONOR'), user(is_superuser=True), user(is_active=False)):
            client, _ = signed_in(actor)
            self.assertEqual(client.get('/api/v1/dashboard').status_code, 403)
            self.assertEqual(client.get('/dashboard').status_code, 403)
