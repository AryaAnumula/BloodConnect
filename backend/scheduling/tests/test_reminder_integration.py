"""Booking, cancellation and the real dispatcher selector across the provider boundary."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TransactionTestCase
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
