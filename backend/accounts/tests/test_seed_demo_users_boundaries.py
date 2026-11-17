from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings


class DemoUserCommandBoundaryTests(TestCase):
    @override_settings(DEBUG=False)
    def test_refuses_non_debug_environment(self):
        with self.assertRaisesRegex(CommandError, 'DEBUG'):
            call_command('seed_demo_users', stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_refuses_missing_short_and_placeholder_passwords(self):
        for value in ('', 'short', 'CHANGE_ME_123456789'):
            with self.subTest(value=value), patch.dict('os.environ', {'DEMO_USER_PASSWORD': value}):
                with self.assertRaises(CommandError):
                    call_command('seed_demo_users', stdout=StringIO())
        self.assertEqual(get_user_model().objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_creates_four_roles_and_replays_without_resetting_accounts(self):
        with patch.dict('os.environ', {'DEMO_USER_PASSWORD': 'synthetic-demo-only-123'}):
            call_command('seed_demo_users', stdout=StringIO())
            ids = list(get_user_model().objects.order_by('email').values_list('id', flat=True))
            call_command('seed_demo_users', stdout=StringIO())
        self.assertEqual(len(ids), 4)
        self.assertEqual(ids, list(get_user_model().objects.order_by('email').values_list('id', flat=True)))
