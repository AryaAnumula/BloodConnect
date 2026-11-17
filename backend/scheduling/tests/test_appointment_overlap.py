"""Half-open appointment overlap policy, including cancelled history."""
from datetime import timedelta

from django.test import TestCase

from scheduling.exceptions import AppointmentConflict
from scheduling.models import Appointment
from scheduling.services.appointments import book_appointment, cancel_appointment
from scheduling.tests.helpers import make_donor, make_slot


class AppointmentOverlapTests(TestCase):
    def test_overlap_rejected_but_adjacent_and_cancelled_are_allowed(self):
        donor, _ = make_donor()
        first = make_slot()
        overlap = make_slot(starts_at=first.starts_at + timedelta(minutes=30),
                            ends_at=first.ends_at + timedelta(minutes=30))
        adjacent = make_slot(starts_at=first.ends_at, ends_at=first.ends_at + timedelta(hours=1))
        booked = book_appointment(actor=donor, slot_id=first.pk)
        with self.assertRaises(AppointmentConflict):
            book_appointment(actor=donor, slot_id=overlap.pk)
        book_appointment(actor=donor, slot_id=adjacent.pk)
        cancel_appointment(actor=donor, appointment_id=booked['id'])
        # The existing adjacent booking starts later than this slot ends.
        prior = make_slot(starts_at=first.starts_at, ends_at=first.ends_at)
        book_appointment(actor=donor, slot_id=prior.pk)
        self.assertEqual(Appointment.objects.filter(donor__user=donor, status='CONFIRMED').count(), 2)
