from unittest.mock import patch
from django.db import OperationalError
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient

class StarterSmokeTests(APITestCase):
    def test_liveness_is_honest_about_scope(self):
        response = self.client.get('/api/v1/health/live')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['business_features'], 'not_implemented')
        self.assertIn('X-Request-ID', response)

    def test_readiness_checks_database(self):
        self.assertEqual(self.client.get('/api/v1/health/ready').status_code, 200)

    def test_readiness_returns_503_when_database_fails(self):
        with patch('core.health.connection.cursor', side_effect=OperationalError('private connection detail')):
            response = self.client.get('/api/v1/health/ready')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private connection detail', response.content.decode())

    def test_browser_login_requires_csrf_and_validates_input(self):
        # BB-01: login is implemented, so the old 501 stub assertion was replaced.
        # The CSRF requirement is still verified.
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/v1/auth/login', {}, format='json').status_code, 403)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        response = client.post('/api/v1/auth/login', {}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'validation_error')

    def test_registration_is_not_fabricated_success(self):
        response = self.client.post('/api/v1/auth/register', {}, format='json')
        self.assertEqual(response.status_code, 501)

    def test_protected_stubs_expose_no_anonymous_data(self):
        for path in ['/api/v1/auth/me', '/api/v1/donors']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()['error']['code'], 'authentication_required')

    def test_authenticated_stub_remains_unimplemented(self):
        User = get_user_model()
        user = User.objects.create_user(email='synthetic@example.test', password='local-test-only-password')
        self.client.force_authenticate(user=user)
        self.assertEqual(self.client.get('/api/v1/donors').status_code, 501)

    def test_static_shells_load_without_claiming_business_completion(self):
        for path in ['/', '/login', '/register', '/screening', '/eligibility', '/staff/donors']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Starter only')