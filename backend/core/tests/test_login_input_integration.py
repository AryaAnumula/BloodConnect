"""Actual merged BB-01/02/05 reference integration; no runtime auth/audit mocks.

BB-11 refresh wires the strict parser/serializer into the existing login endpoint.
These tests remain conditional for isolated provider consumers; the integrated
refresh must run them without skips.
"""
from unittest import skipUnless
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from accounts.api import login as login_api
from accounts.services import sessions as sessions_provider
from audit import events as audit_provider


def provider_implemented(function):
    # No service calls or database side effects during test discovery.
    import inspect
    return 'raise NotImplementedError' not in inspect.getsource(function)


LOGIN_WIRED = hasattr(login_api, 'LoginInputSerializer') and hasattr(login_api, 'StrictJSONParser')
ALL_PROVIDERS = (LOGIN_WIRED and provider_implemented(sessions_provider.establish_session)
                 and provider_implemented(audit_provider.record_security_event))


@skipUnless(LOGIN_WIRED, 'BB-01 owner-reviewed BB-11 login validation patch is not integrated.')
class ActualLoginInputTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email='input-donor@example.test', password='  ExactSyntheticPassword!  ')
        self.original_hash = self.user.password
        self.client = Client(enforce_csrf_checks=True)
        self.csrf = self.client.get('/api/v1/auth/csrf').json()['csrf_token']

    def post(self, payload, raw=False, csrf=True):
        import json
        body = payload if raw else json.dumps(payload)
        return self.client.post('/api/v1/auth/login', body, content_type='application/json',
                                **({'HTTP_X_CSRFTOKEN': self.csrf} if csrf else {}))

    def assert_no_auth_or_account_change(self):
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, self.original_hash)
        self.assertEqual(self.user.role, 'DONOR')
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_real_endpoint_rejects_wrong_types_unknown_fields_and_shapes(self):
        for payload in [[], None, {'email': True, 'password': 'x'},
                        {'email': self.user.email, 'password': 123},
                        {'email': self.user.email, 'password': 'x', 'role': 'ADMIN'},
                        {'email': self.user.email}, {'email': 'not-email', 'password': 'x'},
                        {'email': 'x' * 255, 'password': 'x'}]:
            response = self.post(payload)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error']['code'], 'validation_error')
            self.assert_no_auth_or_account_change()

    def test_real_endpoint_rejects_malformed_and_duplicate_json(self):
        for raw in ['{"email":"SYNTHETIC_SECRET",', '{"email":"one@example.test","email":"two@example.test","password":"x"}', '{"email":NaN,"password":"x"}', '{"email":1e999,"password":"x"}']:
            response = self.post(raw, raw=True)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error']['code'], 'invalid_json')
            self.assertNotIn('SYNTHETIC_SECRET', response.content.decode())
            self.assert_no_auth_or_account_change()

    def test_real_endpoint_injection_like_email_rejected_without_record_change(self):
        for email in ["' OR 1=1 --", '<script>window.__bb11_script_ran__=true</script>']:
            response = self.post({'email': email, 'password': 'SYNTHETIC_SECRET_PASSWORD'})
            self.assertEqual(response.status_code, 400)
            self.assertNotIn('SYNTHETIC_SECRET_PASSWORD', response.content.decode())
            self.assertNotIn('window.__bb11', response.content.decode())
            self.assert_no_auth_or_account_change()

    def test_real_endpoint_csrf_still_precedes_input_validation(self):
        self.assertEqual(self.post({'email': self.user.email, 'password': 'x'}, csrf=False).status_code, 403)
        self.assert_no_auth_or_account_change()

    @skipUnless(ALL_PROVIDERS, 'Actual BB02 session and BB05 audit providers are not integrated.')
    def test_real_valid_login_preserves_password_and_normalizes_email(self):
        response = self.post({'email': '  INPUT-DONOR@EXAMPLE.TEST  ', 'password': '  ExactSyntheticPassword!  '})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertNotIn('ExactSyntheticPassword', response.content.decode())
        from audit.models import SecurityEvent
        self.assertEqual(SecurityEvent.objects.filter(event_type='login', outcome='success', actor_id=self.user.pk).count(), 1)
