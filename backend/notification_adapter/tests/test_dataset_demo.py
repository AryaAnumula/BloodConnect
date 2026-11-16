from io import StringIO
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from donors.models import DonorProfile
from notification_adapter.models import OutboxIntent
from scheduling.models import Appointment, Camp


def dataset_fixture():
    def identifier():
        return str(uuid.uuid4())
    staff = dict(id=identifier(), email='staff-demo@demo.example.test', role='STAFF', is_active=True, is_staff=False, is_superuser=False)
    users, donors, screens, appointments, slots, camps = [], [], [], [], [], []
    for i in range(2):
        user = dict(id=identifier(), email=f'donor-demo{i}@demo.example.test', role='DONOR', is_active=True, is_staff=False, is_superuser=False)
        donor = dict(id=identifier(), user_id=user['id'], full_name='Demo Donor', mobile=f'+44770090000{i}', blood_group='O+', location='Demo Hall', last_confirmed_collection_date=None)
        camp = dict(id=identifier(), name='Demo Camp', location='Demo Hall')
        slot = dict(id=identifier(), camp_id=camp['id'])
        users.append(user); donors.append(donor); camps.append(camp); slots.append(slot)
        screens.append(dict(id=identifier(), donor_id=donor['id'], age_years=30, weight_kg='65.00', status='ELIGIBLE', assessed_at='2026-11-16T00:00:00Z'))
        appointments.append(dict(id=identifier(), donor_id=donor['id'], slot_id=slot['id']))
    return dict(metadata=dict(demo_only=True, dataset_version='bloodconnect-synthetic-v1'),
                tables=dict(accounts=[staff, *users], donors=donors, screenings=screens, appointments=appointments, slots=slots, camps=camps),
                scenarios=dict(on_time_reminder=appointments[0]['id'], late_reminder=appointments[1]['id']))


@override_settings(DEBUG=True)
class DatasetReminderDemoTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data = dataset_fixture()
        self.path = Path(self.directory.name)/'dataset.json'
        payload = json.dumps(self.data).encode()
        self.path.write_bytes(payload)
        (self.path.parent/'manifest.json').write_text(json.dumps({'files': {'dataset.json': hashlib.sha256(payload).hexdigest()}}), encoding='utf-8')

    def queue(self):
        output = StringIO()
        call_command('queue_dataset_reminders', dataset=self.path, stdout=output)
        return json.loads(output.getvalue())

    def test_source_identities_create_actual_screening_bookings_and_cancellation(self):
        result = self.queue()
        self.assertEqual((get_user_model().objects.count(), DonorProfile.objects.count(), Appointment.objects.count()), (3, 2, 3))
        self.assertEqual((OutboxIntent.objects.filter(state='PENDING').count(), OutboxIntent.objects.filter(state='CANCELLED').count()), (2, 1))
        self.assertFalse(OutboxIntent.objects.filter(state='DELIVERED').exists())
        self.assertEqual(result['cancelled_reminder_state'], 'CANCELLED')
        rows = {r['scenario']: OutboxIntent.objects.get(pk=r['intent_id']) for r in result['bookings']}
        self.assertFalse(rows['on_time_reminder'].late_booking)
        self.assertTrue(rows['late_reminder'].late_booking)
        for row in result['bookings']:
            self.assertEqual(str(OutboxIntent.objects.get(pk=row['intent_id']).recipient_id), row['donor_user_id'])

    def test_repeat_does_not_overwrite_or_duplicate_confirmed_demo(self):
        self.queue()
        with self.assertRaisesRegex(CommandError, 'already has'):
            self.queue()
        self.assertEqual((Appointment.objects.count(), OutboxIntent.objects.count(), Camp.objects.count()), (3, 3, 2))

    def test_bad_manifest_is_rejected_before_any_domain_write(self):
        self.path.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(CommandError, 'invalid'):
            self.queue()
        self.assertFalse(get_user_model().objects.exists())

    @override_settings(DEBUG=False)
    def test_non_local_demo_is_rejected(self):
        with self.assertRaisesRegex(CommandError, 'DEBUG'):
            self.queue()
        self.assertFalse(Appointment.objects.exists())

    def test_second_booking_failure_rolls_entire_preparation_back(self):
        from notification_adapter import demo
        actual = demo.book_appointment
        calls = []
        def failing(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise RuntimeError('Synthetic failure')
            return actual(**kwargs)
        with patch('notification_adapter.demo.book_appointment', side_effect=failing):
            with self.assertRaises(RuntimeError):
                self.queue()
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(Camp.objects.exists())
        self.assertFalse(OutboxIntent.objects.exists())
