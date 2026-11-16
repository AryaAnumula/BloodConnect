"""Runs only in the labelled reference composition containing Arya's consumers."""
from datetime import datetime, time, timedelta
from importlib.util import find_spec
from unittest import skipUnless
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from inventory.models import BloodUnit
from inventory.services.dispositions import record_disposition
from inventory.tests.test_intake import InventoryFixture
from inventory.tests import test_stock_orm as stock_fixtures


@skipUnless(find_spec('reporting') is not None, 'Requires separately labelled PR59/60/61/62 reference composition')
class DomainConsumerTests(InventoryFixture, TestCase):
    make_unit = stock_fixtures.StockORMTests.make_unit

    def test_real_dashboard_reads_stock_and_refreshes_after_discard(self):
        from reporting.selectors.dashboard import dashboard_for_admin
        from reporting.providers.dashboard import current_stock
        from reporting.exceptions import ReportingUnavailable
        admin = get_user_model().objects.create_user(email='admin@inventory.test', role='ADMIN')
        unit = self.make_unit('dashboard')
        first = current_stock(actor=admin)
        self.assertEqual(sum(row['available_quantity'] for row in first['results']),1)
        record_disposition(actor=self.staff, unit_id=unit.pk, data={'status':'DISCARDED','reason':'Synthetic fixture'})
        second = current_stock(actor=admin)
        self.assertEqual(second['results'],[])
        # The supplied reference lacks the other owner's actual camp-count source.
        with self.assertRaises(ReportingUnavailable):
            dashboard_for_admin(actor=admin, now=timezone.now())
        client = APIClient()
        client.force_authenticate(admin)
        self.assertEqual(client.get('/api/v1/dashboard').status_code,503)

    def test_real_inventory_report_boundary_and_missing_issue_provider(self):
        from reporting.providers.activity import collection_wastage
        from reporting.selectors.activity import activity_report
        from reporting.exceptions import ReportingUnavailable
        admin = get_user_model().objects.create_user(email='admin@reports.test', role='ADMIN')
        unit = self.make_unit('report')
        start = datetime.combine(unit.collection_date,time.min,ZoneInfo('Asia/Kolkata'))
        self.assertEqual(collection_wastage(start=start,end=start+timedelta(days=1)),
            {'donation_event_count':1,'collected_unit_count':1,'wasted_unit_count':0})
        with self.assertRaises(ReportingUnavailable):
            activity_report(actor=admin,from_date=unit.collection_date,to_date=self.today)
