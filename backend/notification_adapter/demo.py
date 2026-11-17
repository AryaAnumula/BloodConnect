"""Queue NEW domain operations from dataset identities; never import fictional deliveries."""
import hashlib
import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from donors.models import DonorProfile
from donors.services.screening import screen_donor
from notification_adapter.models import OutboxIntent
from notification_adapter.policy import require_policy
from scheduling.models import Appointment
from scheduling.services.appointments import book_appointment, cancel_appointment
from scheduling.services.camps import create_camp
from scheduling.services.slots import create_slot


def source_records(path):
    try:
        path = Path(path)
        with path.open('rb') as handle:
            payload = handle.read(16*1024*1024+1)
        if len(payload) > 16*1024*1024:
            raise ValueError()
        manifest = json.loads((path.parent/'manifest.json').read_text(encoding='utf-8'))
        if manifest['files'][path.name] != hashlib.sha256(payload).hexdigest():
            raise ValueError()
        data = json.loads(payload)
        if data['metadata']['demo_only'] is not True or data['metadata']['dataset_version'] != 'bloodconnect-synthetic-v1':
            raise ValueError()
        result = {}
        for table in ('accounts', 'donors', 'screenings', 'appointments', 'slots', 'camps'):
            rows = data['tables'][table]
            result[table] = {r['id']: r for r in rows}
            if len(result[table]) != len(rows):
                raise ValueError()
        return data, result
    except (OSError, ValueError, TypeError, KeyError):
        raise CommandError('Synthetic dataset/manifest is invalid or unavailable; no demo writes performed.') from None


def queue_dataset_reminders(*, dataset):
    if not settings.DEBUG:
        raise CommandError('Dataset booking demo requires local DEBUG mode.')
    require_policy('S2-06', 'S2-07')
    data, source = source_records(dataset)
    try:
        staff_source = next(a for a in source['accounts'].values() if a['role'] == 'STAFF' and a['is_active'] and not a['is_superuser'])
        selected = []
        for scenario in ('on_time_reminder', 'late_reminder'):
            appointment = source['appointments'][data['scenarios'][scenario]]
            donor = source['donors'][appointment['donor_id']]
            user = source['accounts'][donor['user_id']]
            slot = source['slots'][appointment['slot_id']]
            camp = source['camps'][slot['camp_id']]
            screen = max((s for s in source['screenings'].values() if s['donor_id'] == donor['id']), key=lambda s: s['assessed_at'])
            if donor['last_confirmed_collection_date'] is not None or screen['status'] != 'ELIGIBLE':
                raise ValueError()
            selected.append((scenario, donor, user, camp, screen))
    except (KeyError, ValueError, TypeError, StopIteration):
        raise CommandError('Dataset reminder scenarios are incomplete or not eligible.') from None

    def actor(row, role):
        if row['role'] != role or row['is_active'] is not True or row['is_superuser'] is not False or row['is_staff'] is not False or not row['email'].endswith('@demo.example.test'):
            raise CommandError('Only normal active synthetic actors are allowed.')
        User = get_user_model()
        existing = User.objects.filter(pk=row['id']).first()
        if existing:
            if existing.email != row['email'] or existing.role != role or not existing.is_active or existing.is_superuser or existing.is_staff:
                raise CommandError('Existing actor differs; preserved. Use a separate fresh demo database.')
            return existing
        return User.objects.create_user(id=row['id'], email=row['email'], role=role)

    bookings = []
    with transaction.atomic():
        staff = actor(staff_source, 'STAFF')
        donors = []
        for scenario, row, user_row, camp_row, assessment in selected:
            user = actor(user_row, 'DONOR')
            defaults = {k: row[k] for k in ('user_id', 'full_name', 'mobile', 'blood_group', 'location')}
            profile, _ = DonorProfile.objects.get_or_create(id=row['id'], defaults=defaults)
            if any(str(getattr(profile, k)) != str(v) for k, v in defaults.items()) or profile.last_confirmed_collection_date is not None:
                raise CommandError('Existing donor differs or has collection history; preserved.')
            if Appointment.objects.filter(donor=profile, status='CONFIRMED').exists():
                raise CommandError('Demo donor already has a confirmed booking; use a fresh demo DB or normal cancellation.')
            result = screen_donor(actor=user, donor_id=profile.pk, answers=dict(age_years=assessment['age_years'], weight_kg=assessment['weight_kg'], last_donation_date=None))
            if result.status != 'ELIGIBLE':
                raise CommandError('Current configured screening did not permit the demo booking.')
            start = timezone.now()+timedelta(hours=25, seconds=10) if scenario == 'on_time_reminder' else timezone.now()+timedelta(hours=23)
            camp = create_camp(actor=staff, data=dict(name=camp_row['name']+' reminder demo', location=camp_row['location'], starts_at=start, ends_at=start+timedelta(hours=1), capacity=1))
            slot = create_slot(actor=staff, data=dict(camp_id=camp['id'], location=camp_row['location'], starts_at=start, ends_at=start+timedelta(hours=1), capacity=1))
            booking = book_appointment(actor=user, slot_id=slot['id'])
            intent = OutboxIntent.objects.get(record_id=booking['id'])
            if intent.late_booking != (scenario == 'late_reminder'):
                raise CommandError('Demo setup exceeded timing margin; rolled back, retry on a fresh demo database.')
            bookings.append(dict(scenario=scenario, appointment_id=booking['id'], intent_id=str(intent.pk), donor_user_id=str(user.pk)))
            donors.append((user, profile))
        user, profile = donors[0]
        start = timezone.now()+timedelta(days=3)
        slot = create_slot(actor=staff, data=dict(camp_id=None, location=profile.location, starts_at=start, ends_at=start+timedelta(hours=1), capacity=1))
        booking = book_appointment(actor=user, slot_id=slot['id'])
        cancelled = cancel_appointment(actor=user, appointment_id=booking['id'])
        bookings.append(dict(scenario='cancel_before_dispatch', appointment_id=booking['id'],
                             intent_id=str(OutboxIntent.objects.get(record_id=booking['id']).pk), donor_user_id=str(user.pk)))
    return dict(source='PR62 identities; new actual bookings/intents, not imported mock history', bookings=bookings,
                cancelled_reminder_state=cancelled['reminder_state'])
