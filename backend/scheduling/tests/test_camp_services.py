"""BB-20 camp service tests on the real database. Role matrix is the PROPOSED S2-04 one."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from scheduling.models import Camp
from scheduling.selectors.camps import list_camps
from scheduling.services.camps import CampNotEditable, create_camp, update_camp

PASSWORD = 'local-test-only-password'


def make_user(role, **extra):
    return get_user_model().objects.create_user(
        email=f'{role.lower()}{len(extra)}@example.test', password=PASSWORD, role=role, **extra)


def camp_data(**overrides):
    start = timezone.now() + timedelta(days=10)
    data = {'name': 'City Hall Camp', 'location': 'Chennai', 'starts_at': start,
            'ends_at': start + timedelta(hours=6), 'capacity': 40}
    data.update(overrides)
    return data


class CreateCampTests(TestCase):
    def setUp(self):
        self.admin = make_user('ADMIN')

    def test_admin_creates_an_active_camp(self):
        dto = create_camp(actor=self.admin, data=camp_data())
        self.assertEqual(set(dto), {'id', 'name', 'location', 'starts_at', 'ends_at',
                                    'capacity', 'status'})
        self.assertEqual(dto['status'], 'ACTIVE')
        self.assertEqual(Camp.objects.get(pk=dto['id']).capacity, 40)

    def test_staff_can_create_a_camp(self):
        self.assertEqual(create_camp(actor=make_user('STAFF'), data=camp_data())['status'],
                         'ACTIVE')

    def test_other_roles_inactive_superuser_and_anonymous_cannot_create(self):
        people = [
            make_user('DONOR'), make_user('REQUESTER'),
            make_user('STAFF', is_active=False), make_user('ADMIN', is_active=False),
            get_user_model().objects.create_superuser(email='root@example.test',
                                                      password=PASSWORD),
            AnonymousUser(), None,
        ]
        for person in people:
            with self.subTest(person=repr(person)):
                with self.assertRaises(PermissionDenied):
                    create_camp(actor=person, data=camp_data())
        self.assertEqual(Camp.objects.count(), 0)

    def test_start_not_before_end_rejected_and_nothing_saved(self):
        start = timezone.now() + timedelta(days=10)
        for ends in (start, start - timedelta(hours=1)):
            with self.subTest(ends=ends):
                with self.assertRaises(ValidationError):
                    create_camp(actor=self.admin, data=camp_data(starts_at=start, ends_at=ends))
        self.assertEqual(Camp.objects.count(), 0)

    def test_new_camp_must_start_in_the_future(self):
        now = timezone.now()
        for start in (now - timedelta(days=1), now - timedelta(seconds=1)):
            with self.subTest(start=start):
                with self.assertRaises(ValidationError) as caught:
                    create_camp(actor=self.admin, data=camp_data(
                        starts_at=start, ends_at=start + timedelta(hours=6)))
                self.assertIn('starts_at', caught.exception.detail)
        self.assertEqual(Camp.objects.count(), 0)

    def test_database_enforces_positive_capacity_and_ordered_times(self):
        start = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Camp.objects.create(name='x', location='y', starts_at=start,
                                ends_at=start + timedelta(hours=1), capacity=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Camp.objects.create(name='x', location='y', starts_at=start,
                                ends_at=start, capacity=5)


class UpdateCampTests(TestCase):
    def setUp(self):
        self.admin = make_user('ADMIN')
        self.staff = make_user('STAFF')
        self.camp = create_camp(actor=self.admin, data=camp_data())

    def update(self, actor=None, **data):
        return update_camp(actor=actor or self.admin, camp_id=self.camp['id'], data=data)

    def test_admin_and_staff_can_update(self):
        self.assertEqual(self.update(capacity=55)['capacity'], 55)
        self.assertEqual(self.update(actor=self.staff, location='Bengaluru')['location'],
                         'Bengaluru')

    def test_partial_update_changes_only_given_fields(self):
        dto = self.update(name='Renamed')
        self.assertEqual(dto['name'], 'Renamed')
        self.assertEqual(dto['capacity'], 40)
        self.assertEqual(dto['location'], 'Chennai')

    def test_donor_requester_and_anonymous_cannot_update(self):
        for person in (make_user('DONOR'), make_user('REQUESTER'), AnonymousUser()):
            with self.subTest(person=repr(person)):
                with self.assertRaises(PermissionDenied):
                    self.update(actor=person, capacity=1)
        self.assertEqual(Camp.objects.get(pk=self.camp['id']).capacity, 40)

    def test_update_uses_existing_values_for_the_interval_check(self):
        later = timezone.now() + timedelta(days=60)
        with self.assertRaises(ValidationError):
            self.update(starts_at=later)  # new start is after the existing end
        self.assertEqual(Camp.objects.get(pk=self.camp['id']).capacity, 40)

    def test_unrelated_edit_of_an_already_started_camp_is_allowed(self):
        started = timezone.now() - timedelta(hours=1)
        camp = Camp.objects.create(name='Old', location='Chennai', starts_at=started,
                                   ends_at=started + timedelta(hours=6), capacity=10)
        dto = update_camp(actor=self.admin, camp_id=camp.id, data={'name': 'Renamed'})
        self.assertEqual(dto['name'], 'Renamed')

    def test_changing_starts_at_to_a_past_time_is_currently_allowed(self):
        # PENDING DECISION: documents current behaviour only; this rule is not agreed.
        past = timezone.now() - timedelta(days=1)
        dto = self.update(starts_at=past)
        self.assertEqual(dto['starts_at'], past.isoformat())

    def test_empty_update_rejected(self):
        with self.assertRaises(ValidationError):
            self.update()

    def test_unknown_camp_is_not_found(self):
        with self.assertRaises(NotFound):
            update_camp(actor=self.admin, camp_id='00000000-0000-4000-8000-000000000009',
                        data={'capacity': 5})
        with self.assertRaises(NotFound):
            update_camp(actor=self.admin, camp_id='not-a-uuid', data={'capacity': 5})

    def test_cancelled_camp_cannot_be_edited(self):
        Camp.objects.filter(pk=self.camp['id']).update(status='CANCELLED')
        with self.assertRaises(CampNotEditable):
            self.update(capacity=5)


class ListCampsTests(TestCase):
    def setUp(self):
        self.admin = make_user('ADMIN')
        base = timezone.now() + timedelta(days=5)
        for index in range(3):
            create_camp(actor=self.admin, data=camp_data(
                name=f'Camp {index}', starts_at=base + timedelta(days=index),
                ends_at=base + timedelta(days=index, hours=4)))

    def test_all_allowed_roles_can_list_in_start_order(self):
        for person in (self.admin, make_user('STAFF'), make_user('DONOR')):
            with self.subTest(role=person.role):
                page = list_camps(actor=person, filters={})
                self.assertEqual(page['count'], 3)
                self.assertEqual([c['name'] for c in page['results']],
                                 ['Camp 0', 'Camp 1', 'Camp 2'])

    def test_requester_and_anonymous_cannot_list(self):
        for person in (make_user('REQUESTER'), AnonymousUser()):
            with self.subTest(person=repr(person)):
                with self.assertRaises(PermissionDenied):
                    list_camps(actor=person, filters={})

    def test_status_filter(self):
        Camp.objects.filter(name='Camp 1').update(status='CANCELLED')
        self.assertEqual(list_camps(actor=self.admin, filters={'status': 'CANCELLED'})['count'], 1)
        self.assertEqual(list_camps(actor=self.admin, filters={'status': 'ACTIVE'})['count'], 2)

    def test_default_list_hides_cancelled_camps_from_donors_only(self):
        Camp.objects.filter(name='Camp 1').update(status='CANCELLED')
        donor_page = list_camps(actor=make_user('DONOR'), filters={})
        self.assertEqual(donor_page['count'], 2)
        self.assertEqual([c['name'] for c in donor_page['results']], ['Camp 0', 'Camp 2'])
        for person in (self.admin, make_user('STAFF')):
            with self.subTest(role=person.role):
                page = list_camps(actor=person, filters={})
                self.assertEqual(page['count'], 3)
                self.assertIn('CANCELLED', [c['status'] for c in page['results']])

    def test_donor_pagination_counts_only_visible_camps(self):
        Camp.objects.filter(name='Camp 0').update(status='CANCELLED')
        donor = make_user('DONOR')
        first = list_camps(actor=donor, filters={}, page=1, page_size=1)
        second = list_camps(actor=donor, filters={}, page=2, page_size=1)
        third = list_camps(actor=donor, filters={}, page=3, page_size=1)
        self.assertEqual((first['count'], second['count']), (2, 2))
        self.assertEqual([first['results'][0]['name'], second['results'][0]['name']],
                         ['Camp 1', 'Camp 2'])
        self.assertEqual(third['results'], [])

    def test_explicit_status_filter_is_applied_as_given_for_donors(self):
        # PENDING DECISION: documents current behaviour, not an agreed rule.
        Camp.objects.filter(name='Camp 1').update(status='CANCELLED')
        donor = make_user('DONOR')
        self.assertEqual(list_camps(actor=donor, filters={'status': 'CANCELLED'})['count'], 1)
        self.assertEqual(list_camps(actor=donor, filters={'status': 'ACTIVE'})['count'], 2)

    def test_pagination(self):
        first = list_camps(actor=self.admin, filters={}, page=1, page_size=2)
        second = list_camps(actor=self.admin, filters={}, page=2, page_size=2)
        self.assertEqual((first['count'], len(first['results'])), (3, 2))
        self.assertEqual(len(second['results']), 1)
        self.assertEqual(second['results'][0]['name'], 'Camp 2')

    def test_empty_result_is_a_valid_empty_page(self):
        Camp.objects.all().delete()
        page = list_camps(actor=self.admin, filters={})
        self.assertEqual(page, {'count': 0, 'page': 1, 'page_size': 20, 'results': []})
