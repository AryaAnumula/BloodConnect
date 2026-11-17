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
from scheduling.selectors.appointments import list_own_appointments
from scheduling.exceptions import ReminderUnavailable
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

    def test_actual_provider_states_map_to_the_public_appointment_contract(self):
        booking = book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
        for state, expected in [('PENDING', 'PENDING'), ('LEASED', 'PENDING'), ('BLOCKED', 'PENDING'),
                                ('DELIVERED', 'DELIVERED'), ('FAILED', 'FAILED'), ('CANCELLED', 'CANCELLED')]:
            with self.subTest(state=state):
                OutboxIntent.objects.filter(record_id=booking['id']).update(state=state)
                result = list_own_appointments(actor=self.user)
                self.assertEqual(result['results'][0]['reminder_state'], expected)

    def test_missing_intent_is_unavailable_instead_of_fabricated_pending(self):
        booking = book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
        OutboxIntent.objects.filter(record_id=booking['id']).delete()
        with self.assertRaises(ReminderUnavailable):
            list_own_appointments(actor=self.user)

    def test_unavailable_response_projection_rolls_back_new_booking(self):
        with patch('notification_adapter.services.reminders.public_reminder_state', side_effect=LookupError):
            with self.assertRaises(ReminderUnavailable):
                book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(OutboxIntent.objects.exists())

    def test_unavailable_response_projection_rolls_back_cancellation(self):
        booking = book_appointment(actor=self.user, slot_id=self.slot.pk, now=self.now)
        with patch('notification_adapter.services.reminders.public_reminder_state', side_effect=LookupError):
            with self.assertRaises(ReminderUnavailable):
                cancel_appointment(actor=self.user, appointment_id=booking['id'], now=self.now)
        self.assertEqual(Appointment.objects.get(pk=booking['id']).status, 'CONFIRMED')
        self.assertEqual(OutboxIntent.objects.get(record_id=booking['id']).state, 'PENDING')

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
                # Both lead-time cases use the actual private HTTP adapter and durable
                # Node mock receipt. At exactly25h the reminder is due immediately and
                # its actual completion is still at least24h before the appointment.
                for lead, expected_timing in [(23, False), (25, True)]:
                    with self.subTest(lead_hours=lead):
                        slot = make_slot(starts_at=self.now + timedelta(hours=lead),
                                         ends_at=self.now + timedelta(hours=lead + 1))
                        booking = book_appointment(actor=self.user, slot_id=slot.pk, now=self.now)
                        with override_settings(NOTIFICATION_BASE_URL='http://127.0.0.1:' + port,
                                               NOTIFICATION_INTERNAL_TOKEN=token):
                            result = dispatch_due(now=timezone.now())
                        self.assertEqual(result['delivered'], 1)
                        intent = OutboxIntent.objects.get(record_id=booking['id'])
                        self.assertEqual(intent.state, 'DELIVERED')
                        self.assertEqual(intent.timing_met, expected_timing)
                        self.assertEqual(intent.late_booking, not expected_timing)
                        self.assertEqual(list_own_appointments(actor=self.user)['results'][-1]['reminder_state'], 'DELIVERED')
                self.assertEqual(len(list(Path(directory).glob('*.json'))), 2)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                process.stdout.close()
