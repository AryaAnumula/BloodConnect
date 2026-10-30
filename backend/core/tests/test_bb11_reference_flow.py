""""Real session/audit/me/logout reference; SQLite does not prove PostgreSQL concurrency."""
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.sessions.models import Session
from django.db import OperationalError
from django.test import Client, TestCase
from audit.models import SecurityEvent


class ReferenceFlowTests(TestCase):
    PASSWORD = 'SyntheticReferencePassword!'

    def setUp(self):
        self.user = get_user_model().objects.create_user(email='reference@example.test', password=self.PASSWORD)
        self.client = Client(enforce_csrf_checks=True)
        self.token = self.client.get('/api/v1/auth/csrf').json()['csrf_token']

    def assert_contract(self, path, method, response):
        from pathlib import Path
        import yaml
        from jsonschema import Draft4Validator, FormatChecker
        spec = yaml.safe_load((Path(settings.BASE_DIR) / 'docs/api/openapi.yaml').read_text())
        operation = spec['paths'][path][method]
        response_spec = operation['responses'][str(response.status_code)]
        if response.status_code == 204:
            self.assertEqual(response.content, b'')
            self.assertNotIn('content', response_spec)
            return
        schema = dict(response_spec['content']['application/json']['schema'])
        schema['components'] = spec['components']
        Draft4Validator(schema, format_checker=FormatChecker()).validate(response.json())

    def login(self, password=None):
        return self.client.post('/api/v1/auth/login',
            {'email': self.user.email, 'password': password or self.PASSWORD},
            content_type='application/json', HTTP_X_CSRFTOKEN=self.token)

    def test_real_login_me_logout_and_old_cookie_replay(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assert_contract('/api/v1/auth/login', 'post', response)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertEqual(SecurityEvent.objects.filter(event_type='login', outcome='success', actor_id=self.user.pk).count(), 1)
        me = self.client.get('/api/v1/auth/me')
        self.assertEqual(me.status_code, 200)
        self.assert_contract('/api/v1/auth/me', 'get', me)
        self.assertEqual(me.json(), {'id': str(self.user.pk), 'email': self.user.email, 'role': 'DONOR'})
        self.assertNotIn(self.PASSWORD, response.content.decode())
        old_cookie = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        csrf = self.client.get('/api/v1/auth/csrf').json()['csrf_token']
        logout = self.client.post('/api/v1/auth/logout', content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(logout.status_code, 204)
        self.assert_contract('/api/v1/auth/logout', 'post', logout)
        self.assertEqual(logout.content, b'')
        replay = Client()
        replay.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
        self.assertEqual(replay.get('/api/v1/auth/me').status_code, 403)

    def test_real_unknown_and_wrong_credentials_are_indistinguishable(self):
        first = self.login(password='SyntheticWrong!')
        second = self.client.post('/api/v1/auth/login',
            {'email': 'absent@example.test', 'password': 'SyntheticWrong!'},
            content_type='application/json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual((first.status_code, second.status_code), (401, 401))
        for field in ('code', 'message', 'fields'):
            self.assertEqual(first.json()['error'][field], second.json()['error'][field])
        self.assertEqual(SecurityEvent.objects.filter(event_type='login', outcome='failure').count(), 2)

    def test_success_audit_storage_failure_does_not_persist_authenticated_session(self):
        # Deliberate failure injection only; normal reference flow above uses real providers.
        # Cover both fresh and previously initialized anonymous session cookies.
        for initialized in (False, True):
            with self.subTest(initialized=initialized):
                self.client = Client(enforce_csrf_checks=True)
                self.token = self.client.get('/api/v1/auth/csrf').json()['csrf_token']
                if initialized:
                    session = self.client.session
                    session['synthetic_marker'] = True
                    session.save()
                with patch('audit.events.SecurityEvent.objects.create', side_effect=OperationalError('PRIVATE_DB_DETAIL')):
                    response = self.login()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()['error']['code'], 'audit_unavailable')
                self.assertNotIn('PRIVATE_DB_DETAIL', response.content.decode())
                self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 403)
                for session in Session.objects.all():
                    self.assertNotIn(SESSION_KEY, session.get_decoded())

    def test_invalid_body_does_not_create_session_or_credential_event(self):
        response = self.client.post('/api/v1/auth/login',
            '{"email":"reference@example.test","password":"SyntheticReferencePassword!","role":"ADMIN"}',
            content_type='application/json', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'validation_error')
        self.assertFalse(SecurityEvent.objects.exists())
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_rejects_unsupported_media_type_with_documented_schema(self):
        response = self.client.post('/api/v1/auth/login', 'email=reference@example.test',
            content_type='application/x-www-form-urlencoded', HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 415)
        self.assert_contract('/api/v1/auth/login', 'post', response)
        self.assertFalse(SecurityEvent.objects.exists())

    def test_implemented_donor_routes_reject_invalid_or_unauthorized_requests(self):
        self.assertEqual(self.login().status_code, 200)
        token = self.client.get('/api/v1/auth/csrf').json()['csrf_token']
        donor = '00000000-0000-4000-8000-000000000001'
        # BB08/09 now use real data/policy providers; no fabricated stub success.
        response = self.client.get('/api/v1/donors')
        self.assertEqual(response.status_code,403)  # ordinary donor cannot staff-search
        self.assertEqual(response.json()['error']['code'],'forbidden')
        response = self.client.get(f'/api/v1/donors/{donor}/eligibility/result')
        self.assertEqual(response.status_code,404)
        self.assertEqual(response.json()['error']['code'],'not_found')
        # BB-06: registration is implemented, so it is no longer in the stub list.
        # An empty body is rejected by validation and creates no account.
        response = self.client.post('/api/v1/auth/register', {}, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'validation_error')
        # BB-07: screening is implemented, so it is no longer in the stub list.
        # An empty body is rejected by validation and saves no result.
        response = self.client.post(f'/api/v1/donors/{donor}/eligibility', {}, content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'validation_error')
        self.assertEqual(get_user_model().objects.count(), 1)