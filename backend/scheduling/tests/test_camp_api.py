"""BB-20 camp endpoint tests on the real database. Roles are the PROPOSED S2-04 matrix.

Needs the root urls include for scheduling (shared file, pending Arya).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from scheduling.models import Camp

PASSWORD = 'local-test-only-password'
COUNTER = {'n': 0}


def make_user(role, **extra):
    COUNTER['n'] += 1
    return get_user_model().objects.create_user(
        email=f'{role.lower()}{COUNTER["n"]}@example.test', password=PASSWORD, role=role, **extra)


def client_for(user):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    return client, client.get('/api/v1/auth/csrf').json()['csrf_token']


def body(**overrides):
    start = timezone.now() + timedelta(days=10)
    data = {'name': 'City Hall Camp', 'location': 'Chennai',
            'starts_at': start.isoformat(), 'ends_at': (start + timedelta(hours=6)).isoformat(),
            'capacity': 40}
    data.update(overrides)
    return data


class CampApiTests(TestCase):
    URL = '/api/v1/camps'

    def setUp(self):
        self.admin = make_user('ADMIN')
        self.client, self.token = client_for(self.admin)

    def send(self, method, url, payload=None, client=None, token=None, csrf=True):
        who = client or self.client
        extra = {'HTTP_X_CSRFTOKEN': token or self.token} if csrf else {}
        return getattr(who, method)(url, payload, content_type='application/json', **extra)

    def create(self, **overrides):
        return self.send('post', self.URL, body(**overrides))

    def test_admin_creates_a_camp_with_the_contract_fields(self):
        r = self.create()
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertEqual(set(data), {'id', 'name', 'location', 'starts_at', 'ends_at',
                                     'capacity', 'status'})
        self.assertEqual(data['status'], 'ACTIVE')
        self.assertEqual(Camp.objects.count(), 1)

    def test_other_roles_get_403_forbidden_and_nothing_saved(self):
        for role in ('DONOR', 'REQUESTER'):
            with self.subTest(role=role):
                client, token = client_for(make_user(role))
                r = self.send('post', self.URL, body(), client=client, token=token)
                self.assertEqual(r.status_code, 403)
                self.assertEqual(r.json()['error']['code'], 'forbidden')
        self.assertEqual(Camp.objects.count(), 0)

    def test_staff_can_create_a_camp_over_http(self):
        client, token = client_for(make_user('STAFF'))
        r = self.send('post', self.URL, body(), client=client, token=token)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Camp.objects.count(), 1)

    def test_inactive_staff_and_superuser_cannot_create_over_http(self):
        people = [
            make_user('STAFF', is_active=False),
            get_user_model().objects.create_superuser(email='root-camps@example.test',
                                                      password=PASSWORD),
        ]
        for person in people:
            with self.subTest(person=person.email):
                client = Client(enforce_csrf_checks=True)
                client.force_login(person)
                token = client.get('/api/v1/auth/csrf').json()['csrf_token']
                r = self.send('post', self.URL, body(), client=client, token=token)
                self.assertEqual(r.status_code, 403)
        self.assertEqual(Camp.objects.count(), 0)

    def test_wrong_role_gets_403_even_with_an_invalid_body(self):
        client, token = client_for(make_user('DONOR'))
        r = self.send('post', self.URL, {}, client=client, token=token)
        self.assertEqual(r.status_code, 403)

    def test_anonymous_is_blocked(self):
        anon = Client(enforce_csrf_checks=True)
        token = anon.get('/api/v1/auth/csrf').json()['csrf_token']
        r = self.send('post', self.URL, body(), client=anon, token=token)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()['error']['code'], 'authentication_required')
        self.assertEqual(Camp.objects.count(), 0)

    def test_missing_csrf_token_403_and_nothing_saved(self):
        self.assertEqual(self.send('post', self.URL, body(), csrf=False).status_code, 403)
        self.assertEqual(Camp.objects.count(), 0)

    def test_invalid_input_400_and_nothing_saved(self):
        start = timezone.now() + timedelta(days=10)
        bad = [
            {}, body(name=''), body(location=''), body(capacity=0), body(capacity='5'),
            body(starts_at='2026-12-01T10:00:00'),            # naive datetime
            body(starts_at='not-a-date'),
            body(ends_at=start.isoformat(), starts_at=start.isoformat()),  # start == end
            dict(body(), status='CANCELLED'),                 # unknown field
            dict(body(), role='ADMIN'),
        ]
        for payload in bad:
            with self.subTest(payload=payload):
                r = self.send('post', self.URL, payload)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()['error']['code'], 'validation_error')
        self.assertEqual(Camp.objects.count(), 0)

    def test_repeated_json_keys_rejected(self):
        raw = ('{"name": "A", "name": "B", "location": "Chennai", '
               '"starts_at": "2030-01-01T10:00:00Z", "ends_at": "2030-01-01T12:00:00Z", '
               '"capacity": 5}')
        r = self.client.post(self.URL, raw, content_type='application/json',
                             HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Camp.objects.count(), 0)

    def test_list_for_allowed_roles_and_forbidden_for_requester(self):
        self.create()
        for role in ('ADMIN', 'STAFF', 'DONOR'):
            with self.subTest(role=role):
                client, _ = client_for(make_user(role))
                r = client.get(self.URL)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()['count'], 1)
        client, _ = client_for(make_user('REQUESTER'))
        self.assertEqual(client.get(self.URL).status_code, 403)

    def test_list_query_validation(self):
        for query in ('?status=OPEN', '?page=0', '?page=abc', '?page_size=101', '?unknown=1',
                      '?status=ACTIVE&status=CANCELLED'):
            with self.subTest(query=query):
                r = self.client.get(self.URL + query)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()['error']['code'], 'validation_error')

    def test_list_filter_and_empty_page(self):
        self.create()
        self.assertEqual(self.client.get(self.URL + '?status=CANCELLED').json(),
                         {'count': 0, 'page': 1, 'page_size': 20, 'results': []})

    def test_admin_and_staff_can_patch(self):
        camp_id = self.create().json()['id']
        url = f'{self.URL}/{camp_id}'
        r = self.send('patch', url, {'capacity': 55})
        self.assertEqual((r.status_code, r.json()['capacity']), (200, 55))
        client, token = client_for(make_user('STAFF'))
        r = self.send('patch', url, {'location': 'Bengaluru'}, client=client, token=token)
        self.assertEqual((r.status_code, r.json()['location']), (200, 'Bengaluru'))

    def test_donor_and_requester_cannot_patch(self):
        camp_id = self.create().json()['id']
        for role in ('DONOR', 'REQUESTER'):
            with self.subTest(role=role):
                client, token = client_for(make_user(role))
                r = self.send('patch', f'{self.URL}/{camp_id}', {'capacity': 1},
                              client=client, token=token)
                self.assertEqual(r.status_code, 403)
        self.assertEqual(Camp.objects.get(pk=camp_id).capacity, 40)

    def test_patch_validation_and_unknown_camp(self):
        camp_id = self.create().json()['id']
        url = f'{self.URL}/{camp_id}'
        for payload in ({}, {'capacity': 0}, {'status': 'CANCELLED'}, {'name': ''}):
            with self.subTest(payload=payload):
                self.assertEqual(self.send('patch', url, payload).status_code, 400)
        missing = f'{self.URL}/00000000-0000-4000-8000-000000000009'
        self.assertEqual(self.send('patch', missing, {'capacity': 5}).status_code, 404)

    def test_cancelled_camp_cannot_be_patched(self):
        camp_id = self.create().json()['id']
        Camp.objects.filter(pk=camp_id).update(status='CANCELLED')
        r = self.send('patch', f'{self.URL}/{camp_id}', {'capacity': 5})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()['error']['code'], 'invalid_transition')
