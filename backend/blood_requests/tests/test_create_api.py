"""BB-17 POST /api/v1/requests through Django's full stack (session, CSRF, parser, DB).

Runs against the configured database; PostgreSQL 16 in Docker is the evidence target.
"""
import json
import uuid
from datetime import datetime
from unittest import mock

from django.test import Client, TestCase

from audit.models import SecurityEvent
from blood_requests.models import BloodRequest
from blood_requests.tests.helpers import (PASSWORD, RESPONSE_KEYS, URL, VALID, make_clinical_staff,
                                          make_user, post_json, signed_in)


class SubmitSuccessTests(TestCase):
    def setUp(self):
        self.requester = make_user('REQUESTER')
        self.client, self.token = signed_in(self.requester)

    def test_valid_request_is_saved_submitted_and_owned_by_the_session_user(self):
        response = post_json(self.client, VALID, self.token)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(set(body), RESPONSE_KEYS)
        saved = BloodRequest.objects.get()
        self.assertEqual(body['id'], str(saved.id))
        self.assertEqual(body['requester_id'], str(self.requester.pk))
        self.assertEqual(saved.requester_id, self.requester.pk)
        self.assertEqual((body['status'], body['fulfilled_quantity'], body['rejection_reason']),
                         ('SUBMITTED', 0, None))
        self.assertEqual((saved.status, saved.fulfilled_quantity, saved.rejection_reason),
                         ('SUBMITTED', 0, None))
        for key, value in VALID.items():
            self.assertEqual(body[key], value)
            self.assertEqual(getattr(saved, key), value)
        created = datetime.fromisoformat(body['created_at'])
        self.assertIsNotNone(created.tzinfo)
        self.assertEqual(created.utcoffset().total_seconds(), 0)
        uuid.UUID(body['id'])

    def test_response_discloses_no_account_details(self):
        text = post_json(self.client, VALID, self.token).content.decode()
        for secret in (self.requester.email, PASSWORD, 'email', 'password', 'role'):
            self.assertNotIn(secret, text)

    def test_each_request_gets_its_own_id(self):
        first = post_json(self.client, VALID, self.token).json()['id']
        second = post_json(self.client, {**VALID, 'urgency_level': 'CRITICAL'}, self.token).json()['id']
        self.assertNotEqual(first, second)
        self.assertEqual(BloodRequest.objects.filter(requester=self.requester).count(), 2)

    def test_all_four_components_and_quantity_boundaries_are_accepted(self):
        for component in ('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELETS'):
            for quantity in (1, 100):
                with self.subTest(component=component, quantity=quantity):
                    r = post_json(self.client, {**VALID, 'component_type': component, 'quantity': quantity}, self.token)
                    self.assertEqual(r.status_code, 201, r.content)
                    self.assertEqual(r.json()['quantity'], quantity)  # never clamped

    def test_submission_does_not_require_stock(self):
        # No inventory exists in this database at all; submission must still succeed.
        self.assertEqual(post_json(self.client, {**VALID, 'quantity': 100}, self.token).status_code, 201)

    def test_real_password_login_then_submit(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        login = client.post('/api/v1/auth/login', {'email': self.requester.email, 'password': PASSWORD},
                            content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(login.status_code, 200)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']  # rotated on login
        self.assertEqual(post_json(client, VALID, token).status_code, 201)


class ValidationRejectionTests(TestCase):
    def setUp(self):
        self.client, self.token = signed_in(make_user('REQUESTER'))

    def assert_rejected(self, body=None, raw=None, code='validation_error', field=None):
        response = post_json(self.client, body, self.token, raw=raw)
        self.assertEqual(response.status_code, 400, response.content)
        error = response.json()['error']
        self.assertEqual(error['code'], code)
        self.assertEqual(set(error), {'code', 'message', 'fields', 'request_id'})
        if field:
            self.assertIn(field, error['fields'])
        self.assertEqual(BloodRequest.objects.count(), 0)  # no partial write
        return error

    def test_quantity_out_of_range_or_wrong_type_is_rejected_not_clamped(self):
        for bad in (0, -1, 101, 1000, 10 ** 12, 1.5, 2.0, '2', '100', True, False, None, [1], {'n': 1}):
            with self.subTest(quantity=bad):
                self.assert_rejected({**VALID, 'quantity': bad}, field='quantity')

    def test_quantity_messages_are_clear(self):
        self.assertEqual(self.assert_rejected({**VALID, 'quantity': 101})['fields']['quantity'],
                         ['Quantity cannot be more than 100 units.'])
        self.assertEqual(self.assert_rejected({**VALID, 'quantity': 0})['fields']['quantity'],
                         ['Quantity must be at least 1 unit.'])
        self.assertEqual(self.assert_rejected({**VALID, 'quantity': 1.5})['fields']['quantity'],
                         ['Enter a whole number of units.'])

    def test_missing_and_empty_fields_are_rejected(self):
        for name in VALID:
            with self.subTest(missing=name):
                self.assert_rejected({k: v for k, v in VALID.items() if k != name}, field=name)
            with self.subTest(empty=name):
                self.assert_rejected({**VALID, name: ''}, field=name)
        self.assertEqual(set(self.assert_rejected({})['fields']), set(VALID))

    def test_unsupported_values_are_rejected(self):
        for name, bad in [('blood_group', 'C+'), ('blood_group', 'o-'), ('component_type', 'CRYO'),
                          ('component_type', 'rbc'), ('urgency_level', 'EMERGENCY'),
                          ('urgency_level', 'critical')]:
            with self.subTest(field=name, value=bad):
                error = self.assert_rejected({**VALID, name: bad}, field=name)
                self.assertNotIn(bad, json.dumps(error))

    def test_client_supplied_owner_status_and_server_fields_are_rejected(self):
        other = make_user('REQUESTER')
        for name, value in [('requester_id', str(other.pk)), ('requester', str(other.pk)),
                            ('status', 'APPROVED'), ('status', 'SUBMITTED'), ('fulfilled_quantity', 0),
                            ('rejection_reason', None), ('id', str(uuid.uuid4())),
                            ('created_at', '2026-01-01T00:00:00Z'), ('role', 'STAFF')]:
            with self.subTest(field=name):
                error = self.assert_rejected({**VALID, name: value})
                self.assertEqual(error['fields'], {'non_field_errors': ['Unexpected input field.']})
        self.assertFalse(BloodRequest.objects.filter(requester=other).exists())

    def test_malformed_duplicate_key_and_non_object_json_are_rejected(self):
        self.assert_rejected(raw='{"quantity": 2', code='invalid_json')
        self.assert_rejected(raw='{"blood_group":"O-","component_type":"RBC","quantity":2,'
                                 '"urgency_level":"URGENT","quantity":3}', code='invalid_json')
        self.assert_rejected(raw='{"blood_group":"O-","component_type":"RBC","quantity":NaN,'
                                 '"urgency_level":"URGENT"}', code='invalid_json')
        for raw in ('[]', '"RBC"', '5', 'null'):
            with self.subTest(raw=raw):
                self.assert_rejected(raw=raw)

    def test_form_encoded_body_is_not_accepted(self):
        # Only JSON is parsed. A multipart form yields no fields (CSRF middleware has
        # already consumed the form), so it fails validation and nothing is saved.
        response = self.client.post(URL, VALID, HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'validation_error')
        self.assertEqual(BloodRequest.objects.count(), 0)


class AccessDenialTests(TestCase):
    def assert_denied(self, client, token, code, actor=None):
        SecurityEvent.objects.all().delete()  # test isolation only
        response = post_json(client, VALID, token)
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.json()['error']['code'], code)
        self.assertEqual(BloodRequest.objects.count(), 0)
        if code != 'csrf_failed':
            event = SecurityEvent.objects.get()  # exactly one denial event
            self.assertEqual((event.event_type, event.outcome, event.actor_id),
                             ('access_denied', 'denied', getattr(actor, 'pk', None)))
        return response

    def test_anonymous_is_authentication_required(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        self.assert_denied(client, token, 'authentication_required')

    def test_wrong_roles_are_forbidden(self):
        for role in ('DONOR', 'STAFF', 'ADMIN'):
            with self.subTest(role=role):
                user = make_user(role)
                self.assert_denied(*signed_in(user), 'forbidden', user)

    def test_clinical_staff_permission_grants_no_submission(self):
        user = make_clinical_staff()
        self.assert_denied(*signed_in(user), 'forbidden', user)

    def test_every_superuser_is_forbidden_including_role_requester(self):
        for role in ('REQUESTER', 'ADMIN', 'STAFF'):
            with self.subTest(role=role):
                user = make_user(role, is_superuser=True, is_staff=True)
                self.assert_denied(*signed_in(user), 'forbidden', user)

    def test_session_of_a_deactivated_requester_is_rejected(self):
        user = make_user('REQUESTER')
        client, token = signed_in(user)
        user.is_active = False
        user.save(update_fields=['is_active'])
        # Django's backend refuses inactive users, so the request is anonymous.
        self.assert_denied(client, token, 'authentication_required')

    def test_missing_and_wrong_csrf_token_are_rejected(self):
        client, _ = signed_in(make_user('REQUESTER'))
        self.assert_denied(client, None, 'csrf_failed')
        self.assert_denied(client, 'b' * 32, 'csrf_failed')

    def test_requester_get_reads_only_own_records_under_bb19(self):
        # BB19 replaces temporary403 with a private list, never the staff queue.
        from blood_requests.tests.helpers import make_request
        make_request(make_user('REQUESTER'))
        client, _ = signed_in(make_user('REQUESTER'))
        response = client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 0)
        self.assertEqual(response.json()['results'], [])

    def test_other_methods_are_not_allowed(self):
        client, token = signed_in(make_user('REQUESTER'))
        self.assertEqual(client.put(URL, data='{}', content_type='application/json',
                                    HTTP_X_CSRFTOKEN=token).status_code, 405)

    def test_denial_happens_before_body_validation(self):
        client, token = signed_in(make_user('DONOR'))
        response = post_json(client, {'requester_id': 'x'}, token)
        self.assertEqual(response.json()['error']['code'], 'forbidden')
        self.assertEqual(response.json()['error']['fields'], {})


class PolicyFailClosedApiTests(TestCase):
    def test_missing_or_invalid_policy_returns_409_policy_unresolved_and_saves_nothing(self):
        client, token = signed_in(make_user('REQUESTER'))
        for path in ('/nonexistent/request-policy.json', __file__):  # missing, then not JSON
            with self.subTest(path=path):
                with mock.patch('blood_requests.configuration.POLICY_PATH', path):
                    response = post_json(client, VALID, token)
                self.assertEqual(response.status_code, 409)
                error = response.json()['error']
                self.assertEqual(error['code'], 'policy_unresolved')
                self.assertEqual(error['fields'], {})
                self.assertEqual(BloodRequest.objects.count(), 0)


class NoPublicRequesterElevationTests(TestCase):
    def test_public_registration_cannot_create_a_requester(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        body = {'email': 'self-elevate@example.test', 'mobile': '+919800000171',
                'password': PASSWORD, 'full_name': 'Synthetic Person', 'blood_group': 'O+',
                'location': 'Demo City', 'role': 'REQUESTER'}
        response = client.post('/api/v1/auth/register', body, content_type='application/json',
                               HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        from django.contrib.auth import get_user_model
        self.assertFalse(get_user_model().objects.filter(role='REQUESTER').exists())
