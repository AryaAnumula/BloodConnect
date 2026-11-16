"""Focused BB14 checks using actual config.urls and the shared route patch."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve

from inventory.acceptance.fixtures import SharedApplicationFixture
from inventory.api import StockView, UnitDetail, UnitDisposition
from inventory.models import BloodUnit, InventoryDisposition
from inventory.pages import StockPage


class SharedStockRouteChecks(SharedApplicationFixture,TestCase):
    def test_stock_disposition_and_report_reconcile_on_real_routes(self):
        event,units = self.historical_units()
        staff = self.session_client(self.staff)
        admin = self.session_client(self.admin)
        self.assertIs(resolve('/api/v1/stock').func.view_class,StockView)
        self.assertIs(resolve('/staff/inventory').func.view_class,StockPage)
        self.assertIs(resolve(f'/api/v1/blood-units/{units["RBC"].pk}').func.view_class,UnitDetail)
        self.assertIs(resolve(f'/api/v1/blood-units/{units["RBC"].pk}/dispositions').func.view_class,UnitDisposition)
        before = staff.get('/api/v1/stock')
        self.assertEqual(before.status_code,200,before.data)
        self.assertEqual(sum(row['available_quantity'] for row in before.data['results']),3)
        for component,status in [('RBC','DISCARDED'),('PLASMA','QUARANTINED')]:
            response = staff.post(f'/api/v1/blood-units/{units[component].pk}/dispositions',
                {'status':status,'reason':'Synthetic shared-route transition'},format='json')
            self.assertEqual(response.status_code,200,response.data)
            self.assertEqual(response.data['status'],status)
        stock = admin.get('/api/v1/stock')
        self.assertEqual(stock.status_code,200,stock.data)
        self.assertEqual(stock.data['results'],[
            {'blood_group':'A+','component_type':'PLATELETS','available_quantity':1}])
        self.assertEqual(BloodUnit.objects.count(),3)
        self.assertEqual(InventoryDisposition.objects.count(),2)
        report = admin.get('/api/v1/reports',{'from':event.collection_date.isoformat(),
            'to':self.today.isoformat()})
        self.assertEqual(report.status_code,200,report.data)
        self.assertEqual({key:report.data[key] for key in ('donation_event_count',
            'collected_unit_count','issued_unit_count','wasted_unit_count')},
            {'donation_event_count':1,'collected_unit_count':3,'issued_unit_count':0,'wasted_unit_count':1})

    def test_actual_issue_route_changes_units_stock_and_report_once(self):
        from blood_requests.models import IssueRecord
        event,units = self.historical_units()
        requester = get_user_model().objects.create_user(email='shared-requester@inventory.test',role='REQUESTER')
        request_client = self.session_client(requester)
        staff = self.session_client(self.staff)
        admin = self.session_client(self.admin)
        submitted = request_client.post('/api/v1/requests',{'blood_group':'A+','component_type':'RBC',
            'quantity':1,'urgency_level':'ROUTINE'},format='json')
        self.assertEqual(submitted.status_code,201,submitted.data)
        request_id = submitted.data['id']
        approved = staff.patch(f'/api/v1/requests/{request_id}/status',{'status':'APPROVED'},format='json')
        self.assertEqual(approved.status_code,200,approved.data)
        issued = staff.post(f'/api/v1/requests/{request_id}/issues',
            {'unit_ids':[str(units['RBC'].pk)]},format='json')
        self.assertEqual(issued.status_code,201,issued.data)
        self.assertEqual(IssueRecord.objects.filter(unit=units['RBC']).count(),1)
        self.assertEqual(staff.get(f'/api/v1/blood-units/{units["RBC"].pk}').data['status'],'ISSUED')
        stock = admin.get('/api/v1/stock')
        self.assertEqual(sum(row['available_quantity'] for row in stock.data['results']),2)
        again = staff.post(f'/api/v1/requests/{request_id}/issues',
            {'unit_ids':[str(units['RBC'].pk)]},format='json')
        self.assertEqual(again.status_code,422,again.data)
        self.assertEqual(IssueRecord.objects.count(),1)
        report = admin.get('/api/v1/reports',{'from':event.collection_date.isoformat(),
            'to':self.today.isoformat()})
        self.assertEqual(report.status_code,200,report.data)
        self.assertEqual(report.data['issued_unit_count'],1)
        self.assertEqual(report.data['wasted_unit_count'],0)

    def test_admin_real_route_read_access_does_not_grant_management(self):
        _event,units = self.historical_units()
        admin = self.session_client(self.admin)
        self.assertEqual(admin.get('/api/v1/stock').status_code,200)
        self.assertEqual(admin.get('/api/v1/blood-units').status_code,403)
        self.assertEqual(admin.post(f'/api/v1/blood-units/{units["RBC"].pk}/dispositions',
            {'status':'DISCARDED','reason':'Forbidden mutation'},format='json').status_code,403)
        page = admin.get('/staff/inventory')
        self.assertEqual(page.status_code,200)
        self.assertNotContains(page,'id="disposition"')
        self.assertFalse(InventoryDisposition.objects.exists())
