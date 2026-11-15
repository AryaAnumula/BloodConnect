"""Booking, cancellation and the real dispatcher selector across the provider boundary."""
from datetime import timedelta
import os
import queue
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from notification_adapter.models import OutboxIntent
from notification_adapter.services.dispatch import dispatch_due
from scheduling.models import Appointment
from scheduling.services.appointments import book_appointment, cancel_appointment
from scheduling.tests.helpers import make_donor, make_slot


class ReminderIntegrationTests(TransactionTestCase):
    def setUp(self):
        self.user, self.profile = make_donor()
        self.now = timezone.now()
        self.slot = make_slot(starts_at=self.now + timedelta(hours=23),
                              ends_at=self.now + timedelta(hours=24))

    def test_booking_persists_real_intent_and_dispatch_uses_real_selector(self):
        booking = book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
        intent = OutboxIntent.objects.get(record_id=booking['id'])
        self.assertEqual(intent.recipient_id, self.user.pk)
        self.assertEqual(intent.state, 'PENDING')
        with patch('notification_adapter.services.dispatch.send_notification_intent', return_value={}) as send:
            result = dispatch_due(now=timezone.now())
        self.assertEqual(result['delivered'], 1)
        self.assertEqual(send.call_count, 1)
        intent.refresh_from_db()
        self.assertEqual(intent.state, 'DELIVERED')
        self.assertFalse(intent.timing_met)

    def test_enqueue_failure_rolls_back_booking(self):
        with patch('scheduling.services.appointments.schedule_appointment_reminder', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(OutboxIntent.objects.exists())

    def test_cancellation_invalidates_intent_and_replay_is_idempotent(self):
        booking = book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
        cancel_appointment(actor=self.user, appointment_id=booking['id'], now=self.now)
        cancel_appointment(actor=self.user, appointment_id=booking['id'], now=self.now)
        self.assertEqual(OutboxIntent.objects.get(record_id=booking['id']).state, 'CANCELLED')
        with patch('notification_adapter.services.dispatch.send_notification_intent') as send:
            dispatch_due(now=timezone.now())
        send.assert_not_called()

    def test_invalidation_failure_rolls_back_cancellation(self):
        booking = book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
        with patch('scheduling.services.appointments.cancel_appointment_reminders', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                cancel_appointment(actor=self.user, appointment_id=booking['id'], now=self.now)
        self.assertEqual(Appointment.objects.get(pk=booking['id']).status, 'CONFIRMED')
        self.assertEqual(OutboxIntent.objects.get(record_id=booking['id']).state, 'PENDING')

    def test_booking_dispatches_to_real_local_mock_receipt(self):
        if not shutil.which('node'):
            self.skipTest('Node unavailable; end-to-end mock delivery not verified')
        token = 'synthetic-test-only-dedicated-internal-token'
        script = ("import {createNotificationServer} from './notification-service/src/server.mjs';"
                  "const s=createNotificationServer({token:process.env.BB22_TEST_TOKEN,"
                  "mockEnabled:true,receiptDir:process.env.BB22_TEST_DIR});"
                  "s.listen(0,'127.0.0.1',()=>console.log(s.address().port));")
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.Popen(
                ['node', '--input-type=module', '-e', script], cwd=settings.BASE_DIR,
                env={**os.environ, 'BB22_TEST_TOKEN': token, 'BB22_TEST_DIR': directory},
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                output = queue.Queue()
                threading.Thread(target=lambda: output.put(process.stdout.readline()), daemon=True).start()
                port = output.get(timeout=15).strip()
                self.assertTrue(port.isdigit())
                booking = book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
                with override_settings(NOTIFICATION_BASE_URL='http://127.0.0.1:' + port,
                                       NOTIFICATION_INTERNAL_TOKEN=token):
                    result = dispatch_due(now=timezone.now())
                self.assertEqual(result['delivered'], 1)
                self.assertEqual(OutboxIntent.objects.get(record_id=booking['id']).state, 'DELIVERED')
                self.assertEqual(len(list(Path(directory).glob('*.json'))), 1)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                process.stdout.close()
