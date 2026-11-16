"""Runs only in the labelled reference composition containing Arya's consumers."""
from datetime import datetime, time, timedelta
from importlib.util import find_spec
from importlib import import_module
from unittest import skipUnless
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from inventory.models import BloodUnit
from inventory.services.dispositions import record_disposition
from inventory.tests.test_intake import InventoryFixture
from inventory.tests import test_stock_orm as stock_fixtures


def has_issue_provider():
    return callable(getattr(import_module('blood_requests.selectors.reporting'),
                            'request_issue_totals', None))


def without_provider(module_name):
    """Explicit missing-module negative fixture; other imports stay real."""
    def load(name):
        if name == module_name:
            raise ModuleNotFoundError(name=module_name)
        return import_module(name)
    return load


@skipUnless(find_spec('reporting') is not None, 'Requires separately labelled PR59/60/61/62 reference composition')
@override_settings(ROOT_URLCONF='inventory.tests.urls')
class DomainConsumerTests(InventoryFixture, TestCase):
    make_unit = stock_fixtures.StockORMTests.make_unit

    def test_real_dashboard_reads_stock_and_refreshes_after_discard(self):
        from reporting.providers.dashboard import current_stock
        admin = get_user_model().objects.create_user(email='admin@inventory.test', role='ADMIN')
        unit = self.make_unit('dashboard')
        first = current_stock(actor=admin)
        self.assertEqual(sum(row['available_quantity'] for row in first['results']),1)
        record_disposition(actor=self.staff, unit_id=unit.pk, data={'status':'DISCARDED','reason':'Synthetic fixture'})
        second = current_stock(actor=admin)
        self.assertEqual(second['results'],[])

    def test_explicit_missing_camp_provider_fails_503(self):
        from reporting.selectors.dashboard import dashboard_for_admin
        from reporting.exceptions import ReportingUnavailable
        admin = get_user_model().objects.create_user(email='admin-missing@inventory.test',role='ADMIN')
        client = APIClient()
        client.force_authenticate(admin)
        with patch('reporting.providers.import_module', without_provider('scheduling.selectors.summary')):
            with self.assertRaises(ReportingUnavailable):
                dashboard_for_admin(actor=admin,now=timezone.now())
            self.assertEqual(client.get('/api/v1/dashboard').status_code,503)

    def test_actual_dashboard_uses_real_stock_request_and_camp_sources(self):
        if find_spec('scheduling.selectors.summary') is None:
            self.skipTest('Actual camp summary provider is not composed; explicit503 coverage remains')
        from blood_requests.services.submission import submit_request
        from scheduling.services.camps import create_camp
        from reporting.selectors.dashboard import dashboard_for_admin
        admin = get_user_model().objects.create_user(email='admin-dashboard-real@inventory.test',role='ADMIN')
        requester = get_user_model().objects.create_user(email='requester-dashboard-real@inventory.test',role='REQUESTER')
        empty = dashboard_for_admin(actor=admin,now=timezone.now())
        self.assertEqual((empty['stock'],empty['pending_requests'],empty['upcoming_camps']),([],0,0))
        unit = self.make_unit('dashboard-all-real')
        submit_request(actor=requester,data={'blood_group':'A+','component_type':'RBC',
            'quantity':1,'urgency_level':'ROUTINE'})
        start = timezone.now()+timedelta(days=3)
        create_camp(actor=self.staff,data={'name':'Synthetic dashboard camp','location':'Synthetic hall',
            'starts_at':start,'ends_at':start+timedelta(hours=2),'capacity':2})
        live = dashboard_for_admin(actor=admin,now=timezone.now())
        self.assertEqual((live['pending_requests'],live['upcoming_camps']),(1,1))
        self.assertEqual(live['stock'],[{'blood_group':'A+','component_type':'RBC','available_quantity':1}])
        record_disposition(actor=self.staff,unit_id=unit.pk,data={'status':'DISCARDED','reason':'Synthetic dashboard change'})
        client = APIClient()
        client.force_authenticate(admin)
        response = client.get('/api/v1/dashboard')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual((response.data['stock'],response.data['pending_requests'],
            response.data['upcoming_camps']),([],1,1))

    def test_real_inventory_report_boundary(self):
        from reporting.providers.activity import collection_wastage
        unit = self.make_unit('report')
        start = datetime.combine(unit.collection_date,time.min,ZoneInfo('Asia/Kolkata'))
        self.assertEqual(collection_wastage(start=start,end=start+timedelta(days=1)),
            {'donation_event_count':1,'collected_unit_count':1,'wasted_unit_count':0})

    def test_explicit_missing_issue_provider_fails_503(self):
        from reporting.selectors.activity import activity_report
        from reporting.exceptions import ReportingUnavailable
        admin = get_user_model().objects.create_user(email='admin-missing@reports.test',role='ADMIN')
        client = APIClient()
        client.force_authenticate(admin)
        with patch('reporting.providers.import_module', without_provider('blood_requests.selectors.reporting')):
            with self.assertRaises(ReportingUnavailable):
                activity_report(actor=admin,from_date=self.today,to_date=self.today)
            self.assertEqual(client.get('/api/v1/reports',{'from':self.today.isoformat(),
                'to':self.today.isoformat()}).status_code,503)

    def test_actual_issue_provider_allows_successful_report(self):
        if not has_issue_provider():
            self.skipTest('Actual BB16 issue provider is not composed; missing-provider coverage remains explicit')
        from blood_requests.models import BloodRequest, IssueRecord
        from blood_requests.services.issue import issue_request
        from reporting.selectors.activity import activity_report
        admin = get_user_model().objects.create_user(email='admin-real@reports.test',role='ADMIN')
        requester = get_user_model().objects.create_user(email='requester-real@reports.test',role='REQUESTER')
        unit = self.make_unit('report-real-issue')
        request = BloodRequest.objects.create(requester=requester,blood_group='A+',component_type='RBC',
            quantity=1,urgency_level='ROUTINE',status='APPROVED')
        issue_request(actor=self.staff,request_id=request.pk,unit_ids=[str(unit.pk)])
        self.assertEqual(IssueRecord.objects.filter(unit=unit).count(),1)
        report = activity_report(actor=admin,from_date=unit.collection_date,to_date=self.today)
        self.assertEqual({key:report[key] for key in ('donation_event_count','collected_unit_count',
            'wasted_unit_count','issued_unit_count')},
            {'donation_event_count':1,'collected_unit_count':1,'wasted_unit_count':0,'issued_unit_count':1})
        client = APIClient()
        client.force_authenticate(admin)
        response = client.get('/api/v1/reports',{'from':unit.collection_date.isoformat(),
            'to':self.today.isoformat()})
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['issued_unit_count'],1)
