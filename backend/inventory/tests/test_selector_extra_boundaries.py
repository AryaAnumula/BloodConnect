from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.db import DatabaseError
from django.test import TestCase
from rest_framework.exceptions import NotFound

from inventory.exceptions import InventoryUnavailable
from inventory.models import BloodUnit, CollectionEvent
from inventory.selectors.units import unit_detail, unit_list
from inventory.tests.test_intake import InventoryFixture


class UnitSelectorExtraBoundaryTests(InventoryFixture, TestCase):
    def make_unit(self, code, status='AVAILABLE', expiry=None):
        collected = self.today - timedelta(days=10)
        event = CollectionEvent.objects.create(donor=self.donor, collection_date=collected,
                                               blood_group='A+', recorded_by=self.staff)
        return BloodUnit.objects.create(unit_code=code, donor=self.donor, collection_event=event,
                                        blood_group='A+', component_type='RBC', collection_date=collected,
                                        expiry_date=expiry or self.today + timedelta(days=2), status=status)

    def test_status_filters_and_detail_preserve_derived_expiry(self):
        good = self.make_unit('good')
        self.make_unit('expired', expiry=self.today)
        self.make_unit('held', status='QUARANTINED')
        for status, code in [('AVAILABLE', 'good'), ('EXPIRED', 'expired'), ('QUARANTINED', 'held')]:
            with self.subTest(status=status):
                self.assertEqual(unit_list(actor=self.staff, filters={'status': status})['results'][0]['unit_code'], code)
        self.assertEqual(unit_detail(actor=self.staff, unit_id=good.pk)['unit_code'], 'good')
        with self.assertRaises(NotFound): unit_detail(actor=self.staff, unit_id=uuid4())

    def test_database_failures_are_unavailable(self):
        with patch('inventory.selectors.units.BloodUnit.objects.get', side_effect=DatabaseError):
            with self.assertRaises(InventoryUnavailable): unit_detail(actor=self.staff, unit_id=uuid4())
        with patch('django.db.models.query.QuerySet.count', side_effect=DatabaseError):
            with self.assertRaises(InventoryUnavailable): unit_list(actor=self.staff, filters={})
