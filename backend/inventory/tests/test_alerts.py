from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from inventory.exceptions import InventoryUnavailable
from inventory.models import BloodUnit, InventoryAlert
from inventory.selectors.alerts import alert_list
from inventory.services.alerts import evaluate_alerts
from inventory.tests import test_stock_orm as stock_fixtures
from inventory.tests.test_intake import InventoryFixture
from notification_adapter.models import OutboxIntent


class AlertTests(InventoryFixture, TestCase):
    make_unit = stock_fixtures.StockORMTests.make_unit

    def sweep(self, now=None):
        with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(self.staff.pk)):
            return evaluate_alerts(actor=self.staff, now=now or timezone.now())

    def test_low_stock_zero_equality_recovery_and_recurrence(self):
        first = self.make_unit('one')
        second = self.make_unit('two')
        now = timezone.now()
        result = self.sweep(now)
        self.assertEqual(result['created'], 33)  # 31 low pairs, two near-expiry units
        self.assertFalse(InventoryAlert.objects.filter(kind='LOW_STOCK', blood_group='A+', component_type='RBC').exists())
        self.assertEqual(self.sweep(now)['created'], 0)
        BloodUnit.objects.filter(pk=second.pk).update(status='ISSUED')
        self.assertEqual(self.sweep(now+timedelta(seconds=1))['created'], 1)
        self.assertEqual(InventoryAlert.objects.filter(kind='LOW_STOCK', blood_group='A+', component_type='RBC', active=True).count(), 1)
        BloodUnit.objects.filter(pk=second.pk).update(status='AVAILABLE')
        self.sweep(now+timedelta(seconds=2))
        self.assertFalse(InventoryAlert.objects.filter(kind='LOW_STOCK', blood_group='A+', component_type='RBC', active=True).exists())
        BloodUnit.objects.filter(pk=second.pk).update(status='ISSUED')
        self.sweep(now+timedelta(seconds=3))
        self.assertEqual(InventoryAlert.objects.filter(kind='LOW_STOCK', blood_group='A+', component_type='RBC').count(), 2)

    def test_near_expiry_boundaries_and_excluded_states(self):
        for days in (0, 1, 3, 4):
            self.make_unit('days'+str(days), expiry=self.today+timedelta(days=days))
        for state in ('ISSUED', 'DISCARDED', 'QUARANTINED'):
            self.make_unit(state, status=state)
        self.sweep()
        self.assertEqual(InventoryAlert.objects.filter(kind='NEAR_EXPIRY').count(), 2)

    def test_missing_recipient_config_fails_closed(self):
        with override_settings(INVENTORY_ALERT_RECIPIENT_ID=''):
            with self.assertRaises(InventoryUnavailable):
                evaluate_alerts(actor=self.staff, now=timezone.now())
        self.assertFalse(InventoryAlert.objects.exists())
        self.assertFalse(OutboxIntent.objects.exists())

    def test_recipient_must_be_active_non_superuser_staff(self):
        from django.contrib.auth import get_user_model
        recipient = get_user_model().objects.create_user(email='recipient@inventory.test',role='STAFF')
        for role, active, superuser in [('ADMIN',True,False), ('DONOR',True,False),
                ('REQUESTER',True,False), ('STAFF',False,False), ('STAFF',True,True)]:
            with self.subTest(role=role,active=active,superuser=superuser):
                recipient.role, recipient.is_active, recipient.is_superuser = role,active,superuser
                recipient.save(update_fields=['role','is_active','is_superuser'])
                with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(recipient.pk)):
                    with self.assertRaises(InventoryUnavailable):
                        evaluate_alerts(actor=self.staff,now=timezone.now())
                self.assertFalse(InventoryAlert.objects.exists())
                self.assertFalse(OutboxIntent.objects.exists())
        recipient.role, recipient.is_active, recipient.is_superuser = 'STAFF',True,False
        recipient.save(update_fields=['role','is_active','is_superuser'])
        with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(recipient.pk)):
            self.assertEqual(evaluate_alerts(actor=self.staff,now=timezone.now())['created'],32)

    def test_provider_failure_rolls_back_alerts_and_previous_intents(self):
        from notification_adapter.services.intents import enqueue_intent
        calls = 0
        def fails_second(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError('test')
            return enqueue_intent(**kwargs)
        with patch('inventory.services.alerts.enqueue_intent', fails_second):
            with self.assertRaises(RuntimeError):
                self.sweep()
        self.assertFalse(InventoryAlert.objects.exists())
        self.assertFalse(OutboxIntent.objects.exists())

    def test_truthful_provider_state(self):
        self.sweep()
        row = InventoryAlert.objects.first()
        for raw, public in [('BLOCKED','PENDING'), ('LEASED','PENDING'), ('DELIVERED','DELIVERED'), ('FAILED','FAILED')]:
            OutboxIntent.objects.filter(pk=row.intent_id).update(state=raw)
            result = alert_list(actor=self.staff, filters={'page_size':100})
            self.assertEqual(next(r for r in result['results'] if r['id']==str(row.pk))['notification_state'], public)
        OutboxIntent.objects.filter(pk=row.intent_id).update(state='CANCELLED')
        with self.assertRaises(InventoryUnavailable):
            alert_list(actor=self.staff, filters={'page_size':100})

    def test_threshold_version_change_resolves_and_reopens(self):
        from inventory.services.alerts import alert_policy
        self.sweep()
        with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(self.staff.pk)):
            policy, pairs, recipient, fingerprint = alert_policy()
        with patch('inventory.services.alerts.alert_policy', return_value=(policy,pairs,recipient,'f'*64)):
            result = self.sweep()
        self.assertEqual(result['created'],32)
        self.assertEqual(result['resolved'],32)
        self.assertEqual(OutboxIntent.objects.count(),64)


@skipUnless(connection.vendor == 'postgresql', 'Requires real PostgreSQL locks')
class AlertConcurrencyTests(InventoryFixture, TransactionTestCase):
    def test_two_sweeps_create_one_episode_per_condition(self):
        barrier = Barrier(2)
        now = timezone.now()
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return evaluate_alerts(actor=self.staff, now=now)
            finally:
                close_old_connections()
        with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(self.staff.pk)):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(worker) for _ in range(2)]
                results = [f.result(timeout=20) for f in futures]
        self.assertEqual(sorted(r['created'] for r in results), [0,32])
        self.assertEqual(InventoryAlert.objects.count(),32)
        self.assertEqual(OutboxIntent.objects.count(),32)
