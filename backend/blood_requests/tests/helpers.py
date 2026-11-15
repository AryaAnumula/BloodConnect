"""Synthetic BB-17 fixtures: example.test identities only, no real data or secrets."""
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

PASSWORD = 'local-test-only-password-17'
URL = '/api/v1/requests'
VALID = {'blood_group': 'O-', 'component_type': 'RBC', 'quantity': 2, 'urgency_level': 'URGENT'}
RESPONSE_KEYS = {'id', 'requester_id', 'blood_group', 'component_type', 'quantity',
                 'fulfilled_quantity', 'urgency_level', 'status', 'rejection_reason', 'created_at'}
_counter = {'n': 0}


def make_user(role='REQUESTER', **extra):
    _counter['n'] += 1
    return get_user_model().objects.create_user(
        email=f'{role.lower()}-bb17-{_counter["n"]}@example.test', password=PASSWORD,
        role=role, **extra)


def make_clinical_staff():
    user = make_user('STAFF')
    user.user_permissions.add(Permission.objects.get(
        content_type__app_label='accounts', codename='view_donor_health'))
    return user


def signed_in(user):
    """Session login + real CSRF token from the existing bootstrap endpoint."""
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    token = client.get('/api/v1/auth/csrf').json()['csrf_token']
    return client, token


def post_json(client, body, token=None, raw=None):
    headers = {} if token is None else {'HTTP_X_CSRFTOKEN': token}
    data = raw if raw is not None else json.dumps(body)
    return client.post(URL, data=data, content_type='application/json', **headers)
