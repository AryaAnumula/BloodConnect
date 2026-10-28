from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.permissions import is_authorized_staff


def make(role, **kw):
    n = get_user_model().objects.count()
    return get_user_model().objects.create_user(
        email=f'u{n}-{role.lower()}@example.test', password='synthetic-only-password',
        role=role, **kw)


def run(*args):
    call_command('grant_donor_health_access', *args, stdout=StringIO())


class GrantCommandTests(TestCase):
    def fresh(self, user):
        return get_user_model().objects.get(pk=user.pk)

    def test_grant_then_revoke_for_staff(self):
        staff = make('STAFF')
        self.assertFalse(is_authorized_staff(user=staff))
        run('--user-id', str(staff.pk))
        self.assertTrue(is_authorized_staff(user=self.fresh(staff)))
        run('--user-id', str(staff.pk), '--revoke')
        self.assertFalse(is_authorized_staff(user=self.fresh(staff)))

    def test_refuses_non_staff_inactive_and_superuser(self):
        for user in (make('DONOR'), make('ADMIN'), make('REQUESTER'),
                     make('STAFF', is_active=False), make('STAFF', is_superuser=True)):
            with self.assertRaises(CommandError):
                run('--user-id', str(user.pk))
            self.assertEqual(user.user_permissions.count(), 0)

    def test_unknown_or_malformed_id_errors(self):
        for bad in ('not-a-uuid', '00000000-0000-0000-0000-000000000000'):
            with self.assertRaises(CommandError):
                run('--user-id', bad)