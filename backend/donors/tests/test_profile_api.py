"""BB-12 integration: real DonorProfile rows, real route, real audit writes.
Synthetic @example.test data only. Covers the profile route ONLY; result, screening
and search endpoints are other owners' stubs and are not covered here."""
import itertools
from pathlib import Path
from unittest.mock import patch

import yaml
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import OperationalError
from django.test import TestCase
from jsonschema import Draft4Validator
from rest_framework.test import APIClient

from audit.models import SecurityEvent
from donors.models.profile import DonorProfile

PASSWORD = 'local-test-only-password'
_counter = itertools.count(1)


def make_user(role, **extra):
    n = next(_counter)
    return get_user_model().objects.create_user(
        email=f'bb12-{role.lower()}-{n}@example.test', password=PASSWORD, role=role, **extra)


def make_donor():
    user = make_user('DONOR')
    n = next(_counter)
    return DonorProfile.objects.create(
        user=user, full_name='Synthetic Donor', mobile=f'+9198765{n:05d}',
        blood_group='O+', location='Synthetic City')


def grant(user):
    perm = Permission.objects.get(content_type__app_label='accounts', codename='view_donor_health')
    user.user_permissions.add(perm)
    return get_user_model().objects.get(pk=user.pk)  # fresh: no cached permissions


def fetch(user, donor_id):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client.get(f'/api/v1/donors/{donor_id}')


def error_core(response):
    err = response.json()['error']
    return response.status_code, err['code'], err['message'], err['fields']


def assert_matches_openapi(testcase, response, status):
    spec = yaml.safe_load((Path(settings.BASE_DIR) / 'docs/api/openapi.yaml').read_text())
    op = spec['paths']['/api/v1/donors/{donor_id}']['get']
    schema = dict(op['responses'][status]['content']['application/json']['schema'])
    schema['components'] = spec['components']
    Draft4Validator(schema).validate(response.json())


class DonorProfileAccessTests(TestCase):
    def setUp(self):
        self.profile = make_donor()
        self.owner = self.profile.user

    def test_owner_reads_own_profile_with_exact_allowlisted_fields(self):
        response = fetch(self.owner, self.profile.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'id': str(self.profile.pk), 'user_id': str(self.owner.pk),
            'full_name': 'Synthetic Donor', 'email': self.owner.email,
            'mobile': self.profile.mobile, 'blood_group': 'O+', 'location': 'Synthetic City'})
        assert_matches_openapi(self, response, '200')
        self.assertFalse(SecurityEvent.objects.exists())

    def test_account_uuid_is_not_a_donor_id(self):
        response = fetch(self.owner, self.owner.pk)
        self.assertEqual(response.status_code, 404)

    def test_other_donor_gets_404_identical_to_unknown_id(self):
        other = make_donor().user
        denied = fetch(other, self.profile.pk)
        missing = fetch(other, '00000000-0000-4000-8000-000000000000')
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(error_core(denied), error_core(missing))
        self.assertEqual(error_core(denied)[1], 'not_found')
        assert_matches_openapi(self, denied, '404')
        self.assertNotIn('Synthetic Donor', denied.content.decode())

    def test_other_donor_denial_records_one_event_but_unknown_id_records_none(self):
        other = make_donor().user
        fetch(other, '00000000-0000-4000-8000-000000000000')
        self.assertFalse(SecurityEvent.objects.exists())
        fetch(other, self.profile.pk)
        event = SecurityEvent.objects.get()
        self.assertEqual((event.event_type, event.outcome), ('access_denied', 'denied'))
        self.assertEqual(event.actor_id, other.pk)

    def test_authorized_staff_reads_profile(self):
        staff = grant(make_user('STAFF'))
        response = fetch(staff, self.profile.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {
            'id', 'user_id', 'full_name', 'email', 'mobile', 'blood_group', 'location'})

    def test_staff_with_permission_unknown_id_is_404_without_event(self):
        staff = grant(make_user('STAFF'))
        response = fetch(staff, '00000000-0000-4000-8000-000000000000')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(SecurityEvent.objects.exists())

    def test_staff_without_permission_is_403_forbidden_and_logged_once(self):
        staff = make_user('STAFF')
        response = fetch(staff, self.profile.pk)
        self.assertEqual(error_core(response)[:2], (403, 'forbidden'))
        self.assertEqual(SecurityEvent.objects.get().actor_id, staff.pk)

    def test_admin_requester_and_superusers_are_403_forbidden(self):
        users = [
            make_user('ADMIN'),
            make_user('REQUESTER'),
            get_user_model().objects.create_superuser(email='bb12-su1@example.test', password=PASSWORD),
            get_user_model().objects.create_superuser(
                email='bb12-su2@example.test', password=PASSWORD, role='STAFF'),
        ]
        for user in users:
            response = fetch(user, self.profile.pk)
            self.assertEqual(error_core(response)[:2], (403, 'forbidden'), user.email)
            self.assertNotIn('Synthetic Donor', response.content.decode())

    def test_anonymous_is_403_authentication_required_and_logged_once(self):
        response = fetch(None, self.profile.pk)
        self.assertEqual(error_core(response)[:2], (403, 'authentication_required'))
        self.assertIsNone(SecurityEvent.objects.get().actor_id)

    def test_audit_failure_on_disguised_denial_is_503_without_profile_data(self):
        other = make_donor().user
        with patch('audit.events.SecurityEvent.objects.create', side_effect=OperationalError('PRIVATE')):
            response = fetch(other, self.profile.pk)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'audit_unavailable')
        body = response.content.decode()
        for secret in ('Synthetic Donor', self.profile.mobile, 'PRIVATE'):
            self.assertNotIn(secret, body)