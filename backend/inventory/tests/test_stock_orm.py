from datetime import datetime, time, timedelta
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from inventory.exceptions import InvalidTransition
from inventory.models import BloodUnit, CollectionEvent, InventoryDisposition
from inventory.selectors.reporting import collection_wastage_totals
from inventory.selectors.stock import stock_summary
from inventory.selectors.units import unit_list
from inventory.services.dispositions import record_disposition
from inventory.tests.test_intake import InventoryFixture


class StockORMTests(InventoryFixture, TestCase):
    def make_unit(self, code, component='RBC', status='AVAILABLE', expiry=None):
        # Historical model fixture, not evidence of new collection integration.
        collected = self.today - timedelta(days=10)
        event = CollectionEvent.objects.create(donor=self.donor, collection_date=collected,
                                               blood_group='A+', recorded_by=self.staff)
        return BloodUnit.objects.create(unit_code=code, donor=self.donor, collection_event=event,
            blood_group='A+', component_type=component, collection_date=collected,
            expiry_date=expiry or self.today + timedelta(days=1), status=status)

    def test_stock_reconciles_all_states_and_expiry_equality(self):
        self.make_unit('usable')
        self.make_unit('plasma', component='PLASMA')
        self.make_unit('expired', expiry=self.today)
        for status in ('ISSUED', 'DISCARDED', 'QUARANTINED'):
            self.make_unit(status, status=status)
        result = stock_summary(actor=self.staff, filters={}, page_size=100)
        self.assertEqual(result['count'], 2)
        self.assertEqual(sum(row['available_quantity'] for row in result['results']), 2)
        self.assertEqual(stock_summary(actor=self.staff, filters={'blood_group': 'O+'})['count'], 0)
        self.assertEqual(stock_summary(actor=self.staff, filters={}, page=2, page_size=1)['count'], 2)
        expired = unit_list(actor=self.staff, filters={'status': 'EXPIRED'})
        self.assertEqual(expired['count'], 1)
        self.assertEqual(expired['results'][0]['status'], 'EXPIRED')
        self.assertEqual(BloodUnit.objects.get(unit_code='expired').status, 'AVAILABLE')

    def test_disposition_updates_current_stock_once_and_reports_explicit_discard(self):
        discard, quarantine = self.make_unit('discard'), self.make_unit('quarantine')
        start = datetime.combine(self.today, time.min, ZoneInfo('Asia/Kolkata'))
        record_disposition(actor=self.staff, unit_id=discard.pk, data={'status': 'DISCARDED', 'reason': ' test reason '})
        record_disposition(actor=self.staff, unit_id=quarantine.pk, data={'status': 'QUARANTINED', 'reason': 'Hold'})
        self.assertEqual(stock_summary(actor=self.staff, filters={})['count'], 0)
        self.assertEqual(InventoryDisposition.objects.get(unit=discard).reason, 'test reason')
        for unit in (discard, quarantine):
            with self.assertRaises(InvalidTransition):
                record_disposition(actor=self.staff, unit_id=unit.pk, data={'status': 'DISCARDED', 'reason': 'again'})
        totals = collection_wastage_totals(start=start, end=start + timedelta(days=1))
        self.assertEqual(totals, {'donation_event_count': 0, 'collected_unit_count': 0, 'wasted_unit_count': 1})

    def test_disposition_later_failure_rolls_back_history_and_state(self):
        unit = self.make_unit('rollback')
        with patch.object(BloodUnit, 'save', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):
                record_disposition(actor=self.staff, unit_id=unit.pk, data={'status': 'DISCARDED', 'reason': 'Test'})
        unit.refresh_from_db()
        self.assertEqual(unit.status, 'AVAILABLE')
        self.assertFalse(InventoryDisposition.objects.exists())

    def test_reporting_counts_one_event_multiple_components_half_open(self):
        first = self.make_unit('first')
        BloodUnit.objects.create(unit_code='second', donor=self.donor,
            collection_event=first.collection_event, blood_group='A+', component_type='PLASMA',
            collection_date=first.collection_date, expiry_date=first.expiry_date)
        start = datetime.combine(first.collection_date, time.min, ZoneInfo('Asia/Kolkata'))
        totals = collection_wastage_totals(start=start, end=start+timedelta(days=1))
        self.assertEqual(totals, {'donation_event_count': 1, 'collected_unit_count': 2, 'wasted_unit_count': 0})
        self.assertEqual(collection_wastage_totals(start=start-timedelta(days=1), end=start)['collected_unit_count'], 0)
        with self.assertRaises(ValueError):
            collection_wastage_totals(start=start.replace(tzinfo=None), end=start)

    def test_admin_stock_only_strict_queries_and_page_access(self):
        self.staff.role = 'ADMIN'
        stock_summary(actor=self.staff, filters={}, page_size=100)
        with self.assertRaises(PermissionDenied):
            unit_list(actor=self.staff, filters={})
        for filters, page, size in [({'unknown': 1},1,20), ({},True,20), ({},1,101), ({'blood_group':'bad'},1,20)]:
            with self.assertRaises(ValidationError):
                stock_summary(actor=self.staff, filters=filters, page=page, page_size=size)
        client = APIClient()
        client.force_authenticate(self.staff)
        self.assertEqual(client.get('/api/v1/stock').status_code, 200)
        self.assertEqual(client.get('/api/v1/blood-units').status_code, 403)
        self.assertEqual(client.get('/api/v1/stock?blood_group=A%2B&blood_group=O%2B').status_code, 400)

    def test_all_32_pairs_and_dashboard_page100(self):
        from core.input_schemas import BLOOD_GROUPS
        for group in BLOOD_GROUPS:
            for component in BloodUnit.Component.values:
                unit = self.make_unit(group+component, component=component)
                BloodUnit.objects.filter(pk=unit.pk).update(blood_group=group)
        result = stock_summary(actor=self.staff, filters={}, page_size=100)
        self.assertEqual(result['count'], 32)
        self.assertEqual(len(result['results']), 32)

    def test_stock_page_hides_management_from_admin(self):
        from django.test import Client
        client = Client()
        client.force_login(self.staff)
        staff = client.get('/staff/inventory')
        self.assertContains(staff, 'id="disposition"')
        self.staff.role = 'ADMIN'
        self.staff.save(update_fields=['role'])
        admin = client.get('/staff/inventory')
        self.assertEqual(admin.status_code, 200)
        self.assertNotContains(admin, 'id="disposition"')
        self.assertNotContains(admin, 'id="units"')
        self.assertNotContains(admin, "read('/api/v1/blood-units")
