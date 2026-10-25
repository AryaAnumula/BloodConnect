"""BB-04 tests. Synthetic example.test users only. Policy per approved D-09."""
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from accounts.permissions import IsAuthorizedStaff, is_authorized_staff

PASSWORD = 'local-test-only-password'


def make_user(role, name, **extra):
    return get_user_model().objects.create_user(
        email=f'{name}@example.test', password=PASSWORD, role=role, **extra)


def with_clinical_permission(user):
    perm = Permission.objects.get(content_type__app_label='accounts', codename='view_donor_health')
    user.user_permissions.add(perm)
    return get_user_model().objects.get(pk=user.pk)  # fresh object: no cached permissions


class StaffOnlyView(APIView):
    permission_classes = [IsAuthorizedStaff]

    def get(self, request):
        return Response({'ok': True})


class RoleFixtureTests(TestCase):
    def test_all_four_synthetic_roles_can_be_created(self):
        roles = {
            make_user('DONOR', 'donor1').role,
            make_user('STAFF', 'staff1').role,
            make_user('REQUESTER', 'requester1').role,
            make_user('ADMIN', 'admin1').role,
        }
        self.assertEqual(roles, {'DONOR', 'STAFF', 'REQUESTER', 'ADMIN'})
        self.assertEqual(set(get_user_model().Role.values), roles)


class IsAuthorizedStaffTests(TestCase):
    def test_staff_with_clinical_permission_is_authorized(self):
        user = with_clinical_permission(make_user('STAFF', 'staff2'))
        self.assertTrue(is_authorized_staff(user=user))

    def test_staff_without_clinical_permission_is_denied(self):
        self.assertFalse(is_authorized_staff(user=make_user('STAFF', 'staff3')))

    def test_admin_role_alone_is_denied(self):
        self.assertFalse(is_authorized_staff(user=make_user('ADMIN', 'admin2')))

    def test_admin_with_clinical_permission_is_still_denied(self):
        user = with_clinical_permission(make_user('ADMIN', 'admin3'))
        self.assertFalse(is_authorized_staff(user=user))

    def test_superuser_with_admin_role_is_denied(self):
        user = get_user_model().objects.create_superuser(
            email='super1@example.test', password=PASSWORD)
        self.assertEqual(user.role, 'ADMIN')
        self.assertFalse(is_authorized_staff(user=user))

    def test_donor_and_requester_are_denied_even_with_permission(self):
        for role, name in (('DONOR', 'donor2'), ('REQUESTER', 'requester2')):
            user = with_clinical_permission(make_user(role, name))
            self.assertFalse(is_authorized_staff(user=user), role)

    def test_inactive_staff_with_permission_is_denied(self):
        user = with_clinical_permission(make_user('STAFF', 'staff4', is_active=False))
        self.assertFalse(is_authorized_staff(user=user))

    def test_anonymous_and_none_are_denied(self):
        self.assertFalse(is_authorized_staff(user=AnonymousUser()))
        self.assertFalse(is_authorized_staff(user=None))


class IsAuthorizedStaffPermissionClassTests(TestCase):
    def call(self, user=None):
        request = APIRequestFactory().get('/synthetic-staff-only')
        if user is not None:
            force_authenticate(request, user=user)
        return StaffOnlyView.as_view()(request)

    def test_authorized_staff_gets_200(self):
        user = with_clinical_permission(make_user('STAFF', 'staff5'))
        self.assertEqual(self.call(user).status_code, 200)

    def test_donor_requester_admin_and_plain_staff_get_403_forbidden(self):
        users = [
            make_user('DONOR', 'donor3'),
            make_user('REQUESTER', 'requester3'),
            make_user('ADMIN', 'admin4'),
            make_user('STAFF', 'staff6'),
        ]
        for user in users:
            response = self.call(user)
            self.assertEqual(response.status_code, 403, user.role)
            self.assertEqual(response.data['error']['code'], 'forbidden', user.role)

    def test_anonymous_gets_403_authentication_required(self):
        response = self.call(None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['error']['code'], 'authentication_required')

    def test_permission_class_reads_the_request_user(self):
        user = with_clinical_permission(make_user('STAFF', 'staff7'))
        request = SimpleNamespace(user=user)
        self.assertTrue(IsAuthorizedStaff().has_permission(request, None))


class SuperuserBypassTests(TestCase):
    def make_superuser_with_staff_role(self):
        return get_user_model().objects.create_superuser(
            email='super2@example.test', password=PASSWORD, role='STAFF')

    def test_superuser_with_staff_role_is_denied_despite_django_bypass(self):
        user = self.make_superuser_with_staff_role()
        self.assertTrue(user.has_perm('accounts.view_donor_health'))  # Django's automatic bypass
        self.assertFalse(is_authorized_staff(user=user))

    def test_superuser_with_staff_role_gets_403_from_staff_only_route(self):
        request = APIRequestFactory().get('/synthetic-staff-only')
        force_authenticate(request, user=self.make_superuser_with_staff_role())
        response = StaffOnlyView.as_view()(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['error']['code'], 'forbidden')

    def test_django_is_staff_flag_alone_grants_nothing(self):
        user = make_user('STAFF', 'staff8', is_staff=True)
        self.assertFalse(is_authorized_staff(user=user))