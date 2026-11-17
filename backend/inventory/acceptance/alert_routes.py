"""Affected alert composition checks; deliberately no repeat Node/browser/load run."""
from django.test import TestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from rest_framework.test import APIClient

from inventory.acceptance.fixtures import SharedApplicationFixture
from inventory.api import AlertView
from inventory.exceptions import InventoryUnavailable
from inventory.models import InventoryAlert
from inventory.pages import AlertPage
from inventory.services.alerts import evaluate_alerts
from notification_adapter.models import OutboxIntent


class SharedAlertRouteChecks(SharedApplicationFixture,TestCase):
    def test_actual_fresh_intakes_resolve_low_stock_without_duplicate_intents(self):
        from django.contrib.auth import get_user_model
        from donors.models import DonorProfile
        from donors.services.screening import screen_donor
        from donors.eligibility_reader import read_saved_results
        staff=self.session_client(self.staff)
        with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(self.staff.pk)):
            first=evaluate_alerts(actor=self.staff,now=timezone.now())
            self.assertEqual(first,{'created':32,'resolved':0,'active':32})
            for index in range(2):
                user=get_user_model().objects.create_user(email=f'fresh-alert-{index}@inventory.test',role='DONOR')
                donor=DonorProfile.objects.create(user=user,full_name='Synthetic fresh alert donor',
                    mobile=f'+91909999995{index}',blood_group='A+',location='Synthetic integration')
                screen_donor(actor=user,donor_id=donor.pk,
                    answers={'age_years':25,'weight_kg':'60.00','last_donation_date':None})
                response=staff.post('/api/v1/blood-units',{'unit_code':f'FRESH-ALERT-{index}',
                    'donor_id':str(donor.pk),'blood_group':'A+','component_type':'RBC',
                    'collection_date':self.today.isoformat(),'quantity':1},format='json')
                self.assertEqual(response.status_code,201,response.data)
                donor.refresh_from_db()
                self.assertEqual(donor.last_confirmed_collection_date,self.today)
                self.assertTrue(read_saved_results(donor_ids=[donor.pk])[str(donor.pk)]['is_history_stale'])
            self.assertEqual(evaluate_alerts(actor=self.staff,now=timezone.now()),
                {'created':0,'resolved':1,'active':31})
            self.assertEqual(evaluate_alerts(actor=self.staff,now=timezone.now())['created'],0)
        low=InventoryAlert.objects.get(kind='LOW_STOCK',blood_group='A+',component_type='RBC')
        self.assertFalse(low.active)
        self.assertIsNotNone(low.resolved_at)
        self.assertEqual(OutboxIntent.objects.count(),32)
        self.assertEqual(InventoryAlert.objects.count(),32)

    def test_actual_alert_route_retains_deduplication_and_resolution_history(self):
        _event,units = self.historical_units()
        self.assertIs(resolve('/api/v1/stock/alerts').func.view_class,AlertView)
        self.assertIs(resolve('/staff/inventory/alerts').func.view_class,AlertPage)
        staff = self.session_client(self.staff)
        with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(self.staff.pk)):
            now = timezone.now()
            first = evaluate_alerts(actor=self.staff,now=now)
            self.assertEqual(first,{'created':33,'resolved':0,'active':33})
            self.assertEqual(evaluate_alerts(actor=self.staff,now=now)['created'],0)
            response = staff.get('/api/v1/stock/alerts',{'page_size':100})
            self.assertEqual(response.status_code,200,response.data)
            self.assertEqual(response.data['count'],33)
            self.assertEqual({row['notification_state'] for row in response.data['results']},{'PENDING'})
            changed = staff.post(f'/api/v1/blood-units/{units["PLATELETS"].pk}/dispositions',
                {'status':'QUARANTINED','reason':'Synthetic condition resolution'},format='json')
            self.assertEqual(changed.status_code,200,changed.data)
            resolved = evaluate_alerts(actor=self.staff,now=timezone.now())
            self.assertEqual(resolved,{'created':0,'resolved':1,'active':32})
        self.assertEqual(InventoryAlert.objects.count(),33)
        self.assertEqual(OutboxIntent.objects.count(),33)
        near = InventoryAlert.objects.get(kind='NEAR_EXPIRY')
        self.assertFalse(near.active)
        self.assertIsNotNone(near.resolved_at)
        retained = staff.get('/api/v1/stock/alerts',{'page_size':100})
        self.assertEqual(retained.data['count'],33)
        # This test proves queued state and real route projection, not repeated delivery.
        self.assertEqual(OutboxIntent.objects.filter(state='DELIVERED').count(),0)

    def test_actual_shared_composition_preserves_reader_and_recipient_gates(self):
        self.historical_units()
        self.assertEqual(APIClient().get('/api/v1/stock/alerts').status_code,403)
        self.assertEqual(self.session_client(self.admin).get('/api/v1/stock/alerts').status_code,403)
        with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(self.admin.pk)):
            with self.assertRaises(InventoryUnavailable):
                evaluate_alerts(actor=self.staff,now=timezone.now())
        self.assertFalse(InventoryAlert.objects.exists())
        self.assertFalse(OutboxIntent.objects.exists())
