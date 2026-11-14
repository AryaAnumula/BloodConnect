"""BB-21 slot and appointment endpoint tests (real database, CSRF enforced)."""
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from scheduling.models import Appointment, Slot
from scheduling.tests.helpers import make_camp, make_donor, make_slot, make_user


def client_for(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    return client, client.get('/api/v1/auth/csrf').json()['csrf_token']


def send(client, token, method, url, payload=None, csrf=True):
    extra = {'HTTP_X_CSRFTOKEN': token} if csrf else {}
    return getattr(client, method)(url, payload, content_type='application/json', **extra)


class SlotApiTests(TestCase):
    URL = '/api/v1/appointment-slots'

    def setUp(self):
        self.camp = make_camp(capacity=5)
        self.staff = make_user('STAFF')
        self.client, self.token = client_for(self.staff)

    def payload(self, **overrides):
        data = {'camp_id': str(self.camp.id), 'location': 'Chennai',
                'starts_at': self.camp.starts_at.isoformat(),
                'ends_at': (self.camp.starts_at + timedelta(hours=2)).isoformat(), 'capacity': 2}
        data.update(overrides)
        return data

    def test_staff_creates_a_slot(self):
        r = send(self.client, self.token, 'post', self.URL, self.payload())
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['remaining_capacity'], 2)

    def test_donor_cannot_create_and_unauthenticated_is_refused(self):
        client, token = client_for(make_donor()[0])
        self.assertEqual(send(client, token, 'post', self.URL, self.payload()).status_code, 403)
        self.assertIn(Client().post(self.URL, self.payload(), content_type='application/json').status_code,
                      (401, 403))
        self.assertEqual(Slot.objects.count(), 0)

    def test_missing_csrf_is_refused(self):
        r = send(self.client, self.token, 'post', self.URL, self.payload(), csrf=False)
        self.assertEqual(r.status_code, 403)

    def test_bad_input_gets_the_error_envelope(self):
        for bad in (self.payload(capacity=0), self.payload(extra_field='x'),
                    self.payload(camp_id='nope'),
                    self.payload(ends_at=self.camp.starts_at.isoformat())):
            with self.subTest(bad=bad):
                r = send(self.client, self.token, 'post', self.URL, bad)
                self.assertEqual(r.status_code, 400)
                self.assertIn('error', r.json())

    def test_over_camp_capacity_is_409(self):
        r = send(self.client, self.token, 'post', self.URL, self.payload(capacity=6))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()['error']['code'], 'capacity_conflict')

    def test_donor_lists_only_open_slots_with_envelope(self):
        make_slot(self.camp, capacity=1)
        make_slot(self.camp, capacity=1, status='CANCELLED')
        client, _ = client_for(make_donor()[0])
        data = client.get(self.URL).json()
        self.assertEqual(set(data), {'count', 'page', 'page_size', 'results'})
        self.assertEqual(data['count'], 1)

    def test_requester_cannot_list(self):
        client, _ = client_for(make_user('REQUESTER'))
        self.assertEqual(client.get(self.URL).status_code, 403)


class AppointmentApiTests(TestCase):
    URL = '/api/v1/appointments'

    def setUp(self):
        self.slot = make_slot(make_camp(capacity=5), capacity=1)
        self.donor, self.profile = make_donor()
        self.client, self.token = client_for(self.donor)

    def book(self, **extra):
        return send(self.client, self.token, 'post', self.URL, {'slot_id': str(self.slot.id), **extra})

    def test_donor_books_for_themselves(self):
        r = self.book()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['donor_id'], str(self.profile.id))

    def test_client_cannot_choose_the_donor(self):
        r = self.book(donor_id=str(make_donor()[1].id))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_staff_cannot_book_and_csrf_required(self):
        client, token = client_for(make_user('STAFF'))
        self.assertEqual(send(client, token, 'post', self.URL, {'slot_id': str(self.slot.id)}).status_code, 403)
        r = send(self.client, self.token, 'post', self.URL, {'slot_id': str(self.slot.id)}, csrf=False)
        self.assertEqual(r.status_code, 403)

    def test_error_statuses(self):
        self.assertEqual(send(self.client, self.token, 'post', self.URL, {'slot_id': 'bad'}).status_code, 400)
        missing = '00000000-0000-4000-8000-000000000009'
        self.assertEqual(send(self.client, self.token, 'post', self.URL, {'slot_id': missing}).status_code, 404)
        ineligible, _ = make_donor(eligible=False)
        c2, t2 = client_for(ineligible)
        r = send(c2, t2, 'post', self.URL, {'slot_id': str(self.slot.id)})
        self.assertEqual((r.status_code, r.json()['error']['code']), (422, 'ineligible_donor'))
        self.assertEqual(self.book().status_code, 201)
        dup = self.book()
        self.assertEqual((dup.status_code, dup.json()['error']['code']), (409, 'duplicate_booking'))
        c3, t3 = client_for(make_donor()[0])
        full = send(c3, t3, 'post', self.URL, {'slot_id': str(self.slot.id)})
        self.assertEqual((full.status_code, full.json()['error']['code']), (409, 'capacity_conflict'))

    def test_donor_sees_only_own_appointments(self):
        self.book()
        other, _ = make_donor()
        Appointment.objects.create(donor=_, slot=make_slot(None), status='CONFIRMED')
        data = self.client.get(self.URL).json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['donor_id'], str(self.profile.id))
