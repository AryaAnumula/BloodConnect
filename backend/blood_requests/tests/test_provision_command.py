"""BB-17 restricted provisioning: management command only, password never printed."""
import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from blood_requests.tests.helpers import make_user

PASSWORD = 'synthetic-requester-password-17'


def run(*args):
    out = StringIO()
    call_command('provision_requester', *args, stdout=out)
    return out.getvalue()


@override_settings(DEBUG=True)
class ProvisionTests(TestCase):
    def test_creates_an_active_non_superuser_requester_without_printing_the_password(self):
        with mock.patch.dict(os.environ, {'REQUESTER_PASSWORD': PASSWORD}):
            output = run('--email', ' Hospital.One@Example.TEST ')
        user = get_user_model().objects.get(email='hospital.one@example.test')
        self.assertEqual((user.role, user.is_active, user.is_superuser, user.is_staff),
                         ('REQUESTER', True, False, False))
        self.assertFalse(user.user_permissions.exists())
        self.assertTrue(user.check_password(PASSWORD))
        self.assertIn(str(user.pk), output)
        self.assertNotIn(PASSWORD, output)

    def test_never_changes_the_role_of_an_existing_account(self):
        donor = make_user('DONOR')
        with mock.patch.dict(os.environ, {'REQUESTER_PASSWORD': PASSWORD}):
            with self.assertRaises(CommandError):
                run('--email', donor.email)
        donor.refresh_from_db()
        self.assertEqual(donor.role, 'DONOR')

    def test_password_must_be_set_and_meet_policy(self):
        for value in ('', 'CHANGE_ME_please_123', 'short'):
            with self.subTest(value=value):
                with mock.patch.dict(os.environ, {'REQUESTER_PASSWORD': value}):
                    with self.assertRaises(CommandError):
                        run('--email', 'nopass@example.test')
        self.assertFalse(get_user_model().objects.filter(email='nopass@example.test').exists())

    def test_invalid_email_is_rejected(self):
        with mock.patch.dict(os.environ, {'REQUESTER_PASSWORD': PASSWORD}):
            with self.assertRaises(CommandError):
                run('--email', 'not-an-email')

    def test_deactivate_turns_off_only_requester_accounts(self):
        requester, donor = make_user('REQUESTER'), make_user('DONOR')
        self.assertIn(str(requester.pk), run('--email', requester.email, '--deactivate'))
        requester.refresh_from_db()
        self.assertFalse(requester.is_active)
        with self.assertRaises(CommandError):
            run('--email', donor.email, '--deactivate')
        donor.refresh_from_db()
        self.assertTrue(donor.is_active)


@override_settings(DEBUG=False)
class ProvisionRestrictedTests(TestCase):
    def test_creation_is_refused_outside_debug(self):
        with mock.patch.dict(os.environ, {'REQUESTER_PASSWORD': PASSWORD}):
            with self.assertRaises(CommandError):
                run('--email', 'prod@example.test')
        self.assertFalse(get_user_model().objects.filter(email='prod@example.test').exists())
