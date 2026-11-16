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
