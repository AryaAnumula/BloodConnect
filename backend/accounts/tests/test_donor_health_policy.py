"""Component evidence for BB-12 (stand-in users, no database).

These tests prove the pure policy only. They are NOT endpoint integration or
privacy-acceptance evidence.
"""
import uuid

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase

from accounts.permissions import VIEW_DONOR_HEALTH, may_view_donor_health


class FakeUser:
    """Mimics Django: has_perm() is True for every active superuser."""

    is_authenticated = True

    def __init__(self, *, role, pk=None, is_active=True, is_superuser=False, perms=()):
        self.role = role
        self.pk = pk or uuid.uuid4()
        self.is_active = is_active
        self.is_superuser = is_superuser
        self._perms = set(perms)
        self.has_perm_calls = []

    def has_perm(self, perm):
        self.has_perm_calls.append(perm)
        return self.is_superuser or perm in self._perms


class DonorHealthPolicyTests(SimpleTestCase):
    def setUp(self):
        self.donor_id = uuid.uuid4()

    def test_owner_donor_allowed_for_uuid_and_string_ids(self):
        donor = FakeUser(role='DONOR', pk=self.donor_id)
        self.assertTrue(may_view_donor_health(user=donor, donor_user_id=self.donor_id))
        self.assertTrue(may_view_donor_health(user=donor, donor_user_id=str(self.donor_id)))
        self.assertEqual(donor.has_perm_calls, [])

    def test_other_donor_denied(self):
        donor = FakeUser(role='DONOR')
        self.assertFalse(may_view_donor_health(user=donor, donor_user_id=self.donor_id))

    def test_inactive_donor_denied(self):
        donor = FakeUser(role='DONOR', pk=self.donor_id, is_active=False)
        self.assertFalse(may_view_donor_health(user=donor, donor_user_id=self.donor_id))

    def test_donor_with_missing_or_invalid_id_denied(self):
        donor = FakeUser(role='DONOR', pk=self.donor_id)
        for bad in (None, '', 'not-a-uuid'):
            self.assertFalse(may_view_donor_health(user=donor, donor_user_id=bad))

    def test_staff_with_permission_allowed(self):
        staff = FakeUser(role='STAFF', perms=[VIEW_DONOR_HEALTH])
        self.assertTrue(may_view_donor_health(user=staff, donor_user_id=self.donor_id))

    def test_staff_without_permission_denied(self):
        staff = FakeUser(role='STAFF')
        self.assertFalse(may_view_donor_health(user=staff, donor_user_id=self.donor_id))

    def test_inactive_staff_with_permission_denied(self):
        staff = FakeUser(role='STAFF', perms=[VIEW_DONOR_HEALTH], is_active=False)
        self.assertFalse(may_view_donor_health(user=staff, donor_user_id=self.donor_id))

    def test_superuser_denied_before_has_perm_is_consulted(self):
        for role in ('STAFF', 'ADMIN', 'REQUESTER'):
            su = FakeUser(role=role, is_superuser=True)
            self.assertFalse(may_view_donor_health(user=su, donor_user_id=self.donor_id))
            self.assertEqual(su.has_perm_calls, [])

    def test_admin_denied_even_with_permission_granted(self):
        admin = FakeUser(role='ADMIN', perms=[VIEW_DONOR_HEALTH])
        self.assertFalse(may_view_donor_health(user=admin, donor_user_id=self.donor_id))

    def test_requester_denied_even_when_ids_match(self):
        req = FakeUser(role='REQUESTER', pk=self.donor_id)
        self.assertFalse(may_view_donor_health(user=req, donor_user_id=self.donor_id))

    def test_anonymous_and_none_denied(self):
        self.assertFalse(may_view_donor_health(user=AnonymousUser(), donor_user_id=self.donor_id))
        self.assertFalse(may_view_donor_health(user=None, donor_user_id=self.donor_id))