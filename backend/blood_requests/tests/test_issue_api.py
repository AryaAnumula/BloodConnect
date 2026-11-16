"""BB-16 POST /api/v1/requests/{id}/issues through the full stack. Inventory is a TEST-ONLY
double where noted; real-unit API evidence is in test_issue_integration.py."""
import json
import uuid

from django.test import Client, TestCase

from audit.models import SecurityEvent
from blood_requests.tests.helpers import make_clinical_staff, make_request, make_user, signed_in
from blood_requests.tests.issue_doubles import doubles, unit_ids


def issue_url(request_id):
    return f'/api/v1/requests/{request_id}/issues'


def post(client, url, body, token=None, raw=None):
    headers = {} if token is None else {'HTTP_X_CSRFTOKEN': token}
    return client.post(url, data=raw if raw is not None else json.dumps(body),
                       content_type='application/json', **headers)


class IssueApiTests(TestCase):
    def setUp(self):
        self.client, self.token = signed_in(make_user('STAFF'))
        self.row = make_request(make_user('REQUESTER'), status='APPROVED', quantity=2)

    def test_staff_issue_returns_201_issue_response(self):
        with doubles():
            response = post(self.client, issue_url(self.row.id), {'unit_ids': unit_ids(2)}, self.token)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body['fulfilled_quantity'], body['request_status'], len(body['issues'])), (2, 'ISSUED', 2))

    def test_clinical_staff_may_issue_too(self):
        client, token = signed_in(make_clinical_staff())
        with doubles():
            self.assertEqual(post(client, issue_url(self.row.id), {'unit_ids': unit_ids(1)}, token).status_code, 201)

    def test_absent_inventory_module_fails_closed_with_503(self):
        from blood_requests.tests.test_issue_service import missing_module
        with missing_module('inventory'):
            response = post(self.client, issue_url(self.row.id), {'unit_ids': unit_ids(1)}, self.token)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'inventory_unavailable')
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.fulfilled_quantity), ('APPROVED', 0))

    def test_strict_payloads_are_rejected(self):
        one = unit_ids(1)[0]
        cases = [{}, {'unit_ids': []}, {'unit_ids': [one, one]}, {'unit_ids': ['x']}, {'unit_ids': one},
                 {'unit_ids': [1]}, {'unit_ids': unit_ids(101)}, {'unit_ids': [one], 'quantity': 1},
                 {'unit_ids': [one], 'status': 'ISSUED'}, {'unit_ids': [one], 'issued_by': str(uuid.uuid4())}]
        for body in cases:
            with self.subTest(body=str(body)[:60]):
                with doubles() as allocator:
                    response = post(self.client, issue_url(self.row.id), body, self.token)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()['error']['code'], 'validation_error')
                self.assertEqual(allocator.calls, [])
        for raw in ('{"unit_ids": [', '{"unit_ids":[],"unit_ids":[]}', '[]'):
            with self.subTest(raw=raw):
                self.assertEqual(post(self.client, issue_url(self.row.id), None, self.token, raw=raw).status_code, 400)

    def test_state_errors_use_422_codes(self):
        submitted = make_request(make_user('REQUESTER'), status='SUBMITTED')
        with doubles():
            r1 = post(self.client, issue_url(submitted.id), {'unit_ids': unit_ids(1)}, self.token)
            r2 = post(self.client, issue_url(self.row.id), {'unit_ids': unit_ids(3)}, self.token)
        self.assertEqual((r1.status_code, r1.json()['error']['code']), (422, 'invalid_transition'))
        self.assertEqual((r2.status_code, r2.json()['error']['code']), (422, 'oversupply'))

    def test_unknown_request_404(self):
        with doubles():
            response = post(self.client, issue_url(uuid.uuid4()), {'unit_ids': unit_ids(1)}, self.token)
        self.assertEqual(response.status_code, 404)

    def test_wrong_method(self):
        self.assertEqual(self.client.get(issue_url(self.row.id)).status_code, 405)


class IssueAccessTests(TestCase):
    def setUp(self):
        self.row = make_request(make_user('REQUESTER'), status='APPROVED', quantity=2)

    def assert_denied(self, client, token, code, actor=None):
        SecurityEvent.objects.all().delete()  # test isolation only
        with doubles() as allocator:
            response = post(client, issue_url(self.row.id), {'unit_ids': unit_ids(1)}, token)
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.json()['error']['code'], code)
        self.assertEqual(allocator.calls, [])
        if code != 'csrf_failed':
            event = SecurityEvent.objects.get()  # exactly one denial event
            self.assertEqual((event.event_type, event.actor_id), ('access_denied', getattr(actor, 'pk', None)))

    def test_anonymous(self):
        client = Client(enforce_csrf_checks=True)
        self.assert_denied(client, client.get('/api/v1/auth/csrf').json()['csrf_token'], 'authentication_required')

    def test_wrong_roles_and_every_superuser(self):
        for user in (self.row.requester, make_user('REQUESTER'), make_user('DONOR'), make_user('ADMIN'),
                     make_user('STAFF', is_superuser=True, is_staff=True),
                     make_user('ADMIN', is_superuser=True, is_staff=True)):
            with self.subTest(role=user.role, superuser=user.is_superuser):
                self.assert_denied(*signed_in(user), 'forbidden', user)

    def test_csrf_required(self):
        client, _ = signed_in(make_user('STAFF'))
        self.assert_denied(client, None, 'csrf_failed')
