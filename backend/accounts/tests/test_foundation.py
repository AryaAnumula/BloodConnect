from django.contrib.auth import get_user_model
from django.test import TestCase

class AccountFoundationTests(TestCase):
    def test_foundational_user_uses_django_hashing(self):
        user = get_user_model().objects.create_user(email='SYNTHETIC@EXAMPLE.TEST', password='local-test-only-password')
        self.assertNotEqual(user.password, 'local-test-only-password')
        self.assertTrue(user.check_password('local-test-only-password'))
        self.assertEqual(user.email, 'synthetic@example.test')
        self.assertFalse(user.is_superuser)

    def test_admin_role_does_not_automatically_grant_clinical_permission(self):
        user = get_user_model().objects.create_user(email='admin@example.test', role='ADMIN', password='local-test-only-password')
        self.assertFalse(user.has_perm('accounts.view_donor_health'))
