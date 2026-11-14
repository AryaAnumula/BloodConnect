"""BB-21 slot setup service tests (real database)."""
from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from scheduling.exceptions import CampNotActive, CapacityConflict
from scheduling.models import Slot
from scheduling.services.slots import create_slot
from scheduling.tests.helpers import make_camp, make_slot, make_user


def slot_data(camp=None, **overrides):
    start = camp.starts_at if camp else timezone.now() + timedelta(days=10)
    data = {'camp_id': camp.id if camp else None, 'location': 'Chennai', 'starts_at': start,
            'ends_at': start + timedelta(hours=2), 'capacity': 3}
    data.update(overrides)
    return data


class CreateSlotTests(TestCase):
    def setUp(self):
        self.admin = make_user('ADMIN')
        self.camp = make_camp(capacity=5)

    def test_admin_and_staff_create_camp_slots(self):
        for person in (self.admin, make_user('STAFF')):
            with self.subTest(role=person.role):
                dto = create_slot(actor=person, data=slot_data(self.camp, capacity=1))
                self.assertEqual(dto['camp_id'], str(self.camp.id))
                self.assertEqual((dto['capacity'], dto['remaining_capacity'], dto['status']),
                                 (1, 1, 'OPEN'))

    def test_walk_in_slot_has_no_camp(self):
        dto = create_slot(actor=self.admin, data=slot_data(None))
        self.assertIsNone(dto['camp_id'])

    def test_other_roles_inactive_superuser_and_anonymous_denied(self):
        denied = [make_user('DONOR'), make_user('REQUESTER'), make_user('STAFF', is_active=False),
                  make_user('ADMIN', is_superuser=True), AnonymousUser(), None]
        for person in denied:
            with self.subTest(person=repr(person)):
                with self.assertRaises(PermissionDenied):
                    create_slot(actor=person, data=slot_data(self.camp, capacity=1))
        self.assertEqual(Slot.objects.count(), 0)

    def test_slot_must_be_inside_the_camp_times(self):
        early = slot_data(self.camp, starts_at=self.camp.starts_at - timedelta(minutes=1),
                          ends_at=self.camp.starts_at + timedelta(hours=1), capacity=1)
        late = slot_data(self.camp, starts_at=self.camp.ends_at - timedelta(hours=1),
                         ends_at=self.camp.ends_at + timedelta(minutes=1), capacity=1)
        for data in (early, late):
            with self.assertRaises(ValidationError):
                create_slot(actor=self.admin, data=data)
        edge = slot_data(self.camp, starts_at=self.camp.ends_at - timedelta(hours=1),
                         ends_at=self.camp.ends_at, capacity=1)
        self.assertEqual(create_slot(actor=self.admin, data=edge)['capacity'], 1)

    def test_slot_capacity_cannot_exceed_the_camp_total(self):
        create_slot(actor=self.admin, data=slot_data(self.camp, capacity=3))
        create_slot(actor=self.admin, data=slot_data(self.camp, capacity=2))  # exactly the total
        with self.assertRaises(CapacityConflict):
            create_slot(actor=self.admin, data=slot_data(self.camp, capacity=1))
        self.assertEqual(Slot.objects.count(), 2)

    def test_cancelled_slots_do_not_use_camp_capacity(self):
        first = make_slot(self.camp, capacity=5)
        Slot.objects.filter(pk=first.pk).update(status='CANCELLED')
        self.assertEqual(create_slot(actor=self.admin, data=slot_data(self.camp, capacity=5))['capacity'], 5)

    def test_walk_in_capacity_is_not_limited_by_any_camp(self):
        self.assertEqual(create_slot(actor=self.admin, data=slot_data(None, capacity=500))['capacity'], 500)

    def test_unknown_camp_not_found_and_cancelled_camp_refused(self):
        with self.assertRaises(NotFound):
            create_slot(actor=self.admin, data=slot_data(self.camp, camp_id='00000000-0000-4000-8000-000000000009'))
        self.camp.status = 'CANCELLED'
        self.camp.save()
        with self.assertRaises(CampNotActive):
            create_slot(actor=self.admin, data=slot_data(self.camp, capacity=1))

    def test_database_enforces_positive_capacity_and_ordered_times(self):
        start = timezone.now()
        for bad in ({'capacity': 0, 'ends_at': start + timedelta(hours=1)},
                    {'capacity': 1, 'ends_at': start}):
            with self.subTest(bad=bad):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Slot.objects.create(location='x', starts_at=start, **bad)
