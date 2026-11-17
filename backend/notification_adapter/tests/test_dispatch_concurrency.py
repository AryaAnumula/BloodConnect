"""Real PostgreSQL leases/CAS; transport stand-in tests races, not actual delivery."""
import threading
import uuid
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from notification_adapter.models import DeliveryAttempt, OutboxIntent
from notification_adapter.services.dispatch import dispatch_due
from notification_adapter.services.intents import enqueue_intent
from notification_adapter.services.reminders import cancel_appointment_reminders


@skipUnless(connection.vendor == 'postgresql', 'requires real PostgreSQL row locks')
class DispatcherRaceTests(TransactionTestCase):
    def create_intent(self):
        self.record_id = uuid.uuid4()
        with transaction.atomic():
            data = enqueue_intent(event_id=uuid.uuid4(), recipient_id=uuid.uuid4(),
                                  event_type='APPOINTMENT_REMINDER', record_id=self.record_id,
                                  due_at=timezone.now() - timedelta(minutes=1), channels=['IN_APP'])
        return OutboxIntent.objects.get(pk=data['id'])

    def test_two_workers_claim_one_live_lease_and_send_once(self):
        row = self.create_intent()
        entered, release = threading.Event(), threading.Event()
        calls, failures, results = [], [], []
        def transport(*, event):
            self.assertFalse(connection.in_atomic_block)
            calls.append(event['event_id'])
            entered.set()
            if not release.wait(15):
                raise AssertionError('transport release timed out')
            return {}
        def worker():
            try:
                results.append(dispatch_due(now=timezone.now()))
            except BaseException as error:
                failures.append(repr(error))
            finally:
                connections.close_all()
        with patch('notification_adapter.services.dispatch._reminder_current', return_value=True), \
                patch('notification_adapter.services.dispatch.send_notification_intent', side_effect=transport):
            first = threading.Thread(target=worker, daemon=True)
            first.start()
            try:
                self.assertTrue(entered.wait(15))
                second = threading.Thread(target=worker, daemon=True)
                second.start(); second.join(15)
                self.assertFalse(second.is_alive())
            finally:
                release.set(); first.join(15)
        self.assertFalse(first.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(calls, [str(row.event_id)])
        row.refresh_from_db()
        self.assertEqual((row.state, row.attempts), ('DELIVERED', 1))
        self.assertEqual(DeliveryAttempt.objects.filter(intent=row).count(), 1)

    def test_cancellation_during_inflight_send_is_not_overwritten_by_completion(self):
        row = self.create_intent()
        entered, release = threading.Event(), threading.Event()
        outcomes, failures, accepted = [], [], []
        def transport(*, event):
            self.assertFalse(connection.in_atomic_block)
            entered.set()
            if not release.wait(15):
                raise AssertionError('transport release timed out')
            accepted.append(event['event_id'])  # stand-in may accept an already in-flight send
            return {}
        def worker():
            try:
                outcomes.append(dispatch_due(now=timezone.now()))
            except BaseException as error:
                failures.append(repr(error))
            finally:
                connections.close_all()
        with patch('notification_adapter.services.dispatch._reminder_current', return_value=True), \
                patch('notification_adapter.services.dispatch.send_notification_intent', side_effect=transport):
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            try:
                self.assertTrue(entered.wait(15))
                with transaction.atomic():
                    self.assertEqual(cancel_appointment_reminders(appointment_id=self.record_id), 1)
            finally:
                release.set(); thread.join(15)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        row.refresh_from_db()
        self.assertEqual((row.state, row.attempts), ('CANCELLED', 0))
        self.assertEqual(outcomes[0]['superseded'], 1)
        self.assertEqual(accepted, [str(row.event_id)])
        self.assertFalse(DeliveryAttempt.objects.filter(intent=row).exists())
        # This proves CAS preservation; it deliberately does NOT promise recall of the send.
