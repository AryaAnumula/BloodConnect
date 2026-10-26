"""Test-only write probe: demonstrates validation ordering, NOT donor registration.

Only enabled by ROOT_URLCONF override in this test class. No production route.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView
from core.input_schemas import LoginInputSerializer
from core.parsers import StrictJSONParser
from core.validation import StrictInputSerializer, StrictStringField


class NameInput(StrictInputSerializer):
    full_name = StrictStringField(max_length=120, allow_blank=False)


class ValidationWriteProbe(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [StrictJSONParser]
    def post(self, request):
        serializer = NameInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.first_name = serializer.validated_data['full_name']
        request.user.save(update_fields=['first_name'])
        return Response({'full_name': request.user.first_name})


urlpatterns = [path('__tests__/bb11/name', ValidationWriteProbe.as_view())]


@override_settings(ROOT_URLCONF=__name__)
class DirectApiValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email='input-only@example.test', password='synthetic-valid-password', first_name='Original')
        self.client = APIClient()
        # Bypass auth ONLY in this isolated validation probe, not the real login tests.
        self.client.force_authenticate(self.user)

    def assert_unchanged(self):
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Original')
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_direct_invalid_request_cannot_commit_change(self):
        for payload in [{'full_name': 'x' * 121}, {'full_name': False},
                        {'full_name': 'Valid', 'role': 'ADMIN'}, [], {'full_name': ''}]:
            response = self.client.post('/__tests__/bb11/name', payload, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error']['code'], 'validation_error')
            self.assert_unchanged()

    def test_bad_duplicate_and_nonfinite_json_rejected_before_write(self):
        for raw in ['{"full_name":"SYNTHETIC_SECRET",', '{"full_name":"One","full_name":"Two"}', '{"full_name":NaN}']:
            response = self.client.post('/__tests__/bb11/name', raw, content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error']['code'], 'invalid_json')
            self.assertNotIn('SYNTHETIC_SECRET', response.content.decode())
            self.assert_unchanged()

    def test_parameterized_orm_keeps_sql_like_name_as_literal(self):
        literal = "Synthetic'); DROP TABLE accounts_user; --"
        response = self.client.post('/__tests__/bb11/name', {'full_name': literal}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, literal)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertFalse(get_user_model().objects.filter(first_name="' OR 1=1 --").exists())

    def test_script_like_name_is_returned_as_json_data_not_html(self):
        literal = '<img src=x onerror="window.__bb11_script_ran__=true">'
        response = self.client.post('/__tests__/bb11/name', {'full_name': literal}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('application/json'))
        self.assertEqual(response.json()['full_name'], literal)

    def test_validation_error_does_not_echo_submitted_values(self):
        response = self.client.post('/__tests__/bb11/name', {'full_name': {'secret': 'SYNTHETIC_SECRET'}}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('SYNTHETIC_SECRET', response.content.decode())
        self.assert_unchanged()
