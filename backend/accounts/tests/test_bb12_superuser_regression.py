"""Actual BB12 policy + actual profile route, no mocked provider/permission success."""
from types import SimpleNamespace
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient
from audit.models import SecurityEvent
from accounts.permissions import IsDonorOrAuthorizedStaff, may_view_donor_health
from accounts.tests.test_donor_health_policy import FakeUser
from donors.tests.test_profile_api import make_donor


class SuperuserPolicyRegressionTests(SimpleTestCase):
    def test_all_superuser_roles_denied_by_object_policy_including_own_donor(self):
        for role in ['DONOR', 'STAFF', 'ADMIN', 'REQUESTER']:
            user = FakeUser(role=role, is_superuser=True)
            self.assertFalse(may_view_donor_health(user=user, donor_user_id=user.pk), role)
            self.assertEqual(user.has_perm_calls, [])

    def test_all_superuser_roles_denied_by_endpoint_gate(self):
        for role in ['DONOR', 'STAFF', 'ADMIN', 'REQUESTER']:
            user = FakeUser(role=role, is_superuser=True)
            self.assertFalse(IsDonorOrAuthorizedStaff().has_permission(SimpleNamespace(user=user), None), role)
            self.assertEqual(user.has_perm_calls, [])


class SuperuserProfileRouteRegressionTests(TestCase):
    def test_superuser_cannot_read_own_profile_and_denial_is_audited_once(self):
        for role in ['DONOR', 'STAFF', 'ADMIN', 'REQUESTER']:
            profile = make_donor()
            user = profile.user
            user.role = role
            user.is_superuser = True
            user.save(update_fields=['role', 'is_superuser'])
            client = APIClient()
            client.force_authenticate(user)
            before = SecurityEvent.objects.count()
            response = client.get(f'/api/v1/donors/{profile.pk}')
            self.assertEqual(response.status_code, 403, role)
            self.assertEqual(response.json()['error']['code'], 'forbidden')
            for private in [profile.full_name, profile.mobile, user.email]:
                self.assertNotIn(private, response.content.decode())
            self.assertEqual(SecurityEvent.objects.count(), before + 1)
