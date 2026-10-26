"""Real baseline route plus isolated permission probes (not full BB-04 integration)."""
from uuid import UUID, uuid4
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from core.errors import LoginRejected
from audit.models import SecurityEvent


class RejectedLoginProbe(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        raise LoginRejected()


class DenialProbe(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        raise PermissionDenied()


class InvalidAuthProbe(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        raise AuthenticationFailed()


class ValidationProbe(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        raise ValidationError({'field': 'Invalid.'})


class DenialHookTests(TestCase):
    def test_real_anonymous_protected_route_records_exactly_once(self):
        correlation = str(uuid4())
        response = APIClient().get('/api/v1/donors', HTTP_X_REQUEST_ID=correlation)
        self.assertEqual(response.status_code, 403)
        event = SecurityEvent.objects.get()
        self.assertEqual((event.event_type, event.outcome), ('access_denied', 'denied'))
        self.assertIsNone(event.actor_id)
        self.assertEqual(str(event.request_id), correlation)
        self.assertEqual(response['X-Request-ID'], correlation)

    def test_invalid_client_correlation_is_replaced_safely(self):
        response = APIClient().get('/api/v1/donors', HTTP_X_REQUEST_ID='SYNTHETIC_SECRET_NOT_UUID')
        event = SecurityEvent.objects.get()
        self.assertEqual(str(event.request_id), response['X-Request-ID'])
        UUID(response['X-Request-ID'])
        self.assertNotIn('SYNTHETIC_SECRET', repr(response.json()))

    def test_known_actor_denial_uses_only_uuid(self):
        user = get_user_model().objects.create_user(email='denied@example.test', password='synthetic-only-password')
        request = APIRequestFactory().get('/probe')
        force_authenticate(request, user=user)
        response = DenialProbe.as_view()(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(SecurityEvent.objects.get().actor_id, user.pk)

    def test_shared_login_exception_records_failure_without_body(self):
        request = APIRequestFactory().post('/probe', {'password': 'SYNTHETIC_SECRET', 'health_data': 'SYNTHETIC_HEALTH'}, format='json')
        response = RejectedLoginProbe.as_view()(request)
        self.assertEqual(response.status_code, 401)
        event = SecurityEvent.objects.get()
        self.assertEqual((event.event_type, event.outcome), ('login', 'failure'))
        self.assertNotIn('SYNTHETIC_', repr(response.data))

    def test_invalid_authentication_is_access_denial_not_assumed_login(self):
        response = InvalidAuthProbe.as_view()(APIRequestFactory().get('/probe'))
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(SecurityEvent.objects.get().event_type, 'access_denied')

    def test_audit_failure_in_denial_returns_redacted_503(self):
        with patch('audit.events.SecurityEvent.objects.create', side_effect=OperationalError('PRIVATE_DB_DETAIL')):
            response = APIClient().get('/api/v1/donors')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'audit_unavailable')
        self.assertNotIn('PRIVATE_DB_DETAIL', response.content.decode())
        self.assertFalse(SecurityEvent.objects.exists())
        from pathlib import Path
        from django.conf import settings
        from jsonschema import Draft4Validator
        import yaml
        spec = yaml.safe_load((Path(settings.BASE_DIR) / 'docs/api/openapi.yaml').read_text())
        schema = dict(spec['paths']['/api/v1/donors']['get']['responses']['503']['content']['application/json']['schema'])
        schema['components'] = spec['components']
        Draft4Validator(schema).validate(response.json())

    def test_validation_error_is_not_a_security_denial(self):
        response = ValidationProbe.as_view()(APIRequestFactory().post('/probe', {}, format='json'))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SecurityEvent.objects.exists())

    def test_authenticated_unimplemented_route_not_recorded_as_denial(self):
        user = get_user_model().objects.create_user(email='stub@example.test', password='synthetic-only-password')
        client = APIClient()
        client.force_authenticate(user)
        response = client.get('/api/v1/donors')
        self.assertEqual(response.status_code, 501)
        self.assertFalse(SecurityEvent.objects.exists())

    def test_no_audit_listing_or_admin_endpoint_exposed(self):
        for path in ['/api/v1/audit/events', '/admin/audit/securityevent/']:
            self.assertEqual(APIClient().get(path).status_code, 404)
