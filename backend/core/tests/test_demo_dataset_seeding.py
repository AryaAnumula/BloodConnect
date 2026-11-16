"""Real local import, transaction rollback, replay and no invented domain history."""
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from blood_requests.models import BloodRequest
from core.demo_data.generate import generate
from donors.models import DonorProfile, EligibilityResult


@override_settings(DEBUG=True)
class DemoSeederTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = tempfile.TemporaryDirectory()
        cls.data = generate()
        cls.path = Path(cls.folder.name)/'dataset.json'
        cls.path.write_text(json.dumps(cls.data), encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()
        super().tearDownClass()

    def seed(self, **kwargs):
        output = StringIO()
        call_command('seed_project_demo', dataset=self.path, stdout=output, **kwargs)
        return json.loads(output.getvalue())

    @override_settings(DEBUG=False)
    def test_not_enabled_outside_local_debug(self):
        with self.assertRaisesRegex(CommandError, 'DEBUG'):
            self.seed()
        self.assertFalse(get_user_model().objects.exists())

    def test_dry_run_has_no_writes_and_declares_partial_import_scope(self):
        result = self.seed(dry_run=True)
        self.assertEqual(result['planned'], {'accounts': 515, 'donors': 500, 'screenings': 100, 'blood_requests': 80})
        self.assertFalse(get_user_model().objects.exists())

    def test_actual_import_replay_and_source_linked_states_not_invented(self):
        result = self.seed()
        self.assertEqual(result['created'], result['planned'])
        self.assertEqual(get_user_model().objects.count(), 515)
        self.assertFalse(get_user_model().objects.filter(is_superuser=True).exists())
        self.assertEqual((DonorProfile.objects.count(), EligibilityResult.objects.count(), BloodRequest.objects.count()), (500, 100, 80))
        self.assertFalse(BloodRequest.objects.exclude(fulfilled_quantity=0).exists())
        self.assertFalse(BloodRequest.objects.filter(status__in=['ISSUED', 'CLOSED']).exists())
        before = list(BloodRequest.objects.values_list('id', 'updated_at'))
        self.assertTrue(all(not n for n in self.seed()['created'].values()))
        self.assertEqual(before, list(BloodRequest.objects.values_list('id', 'updated_at')))
        self.assertFalse(get_user_model().objects.first().has_usable_password())

    def test_late_mobile_collision_rolls_back_every_new_account_and_profile(self):
        user = get_user_model().objects.create_user(email='existing@demo.example.test', role='DONOR')
        donor = DonorProfile.objects.create(user=user, full_name='Existing demo', mobile=self.data['tables']['donors'][-1]['mobile'], blood_group='A+', location='Existing demo')
        with self.assertRaisesRegex(CommandError, 'rolled back'):
            self.seed()
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(list(DonorProfile.objects.values_list('pk', flat=True)), [donor.pk])
        self.assertFalse(BloodRequest.objects.exists())

    def test_existing_modified_demo_record_is_preserved(self):
        self.seed()
        row = BloodRequest.objects.filter(status='SUBMITTED').first()
        BloodRequest.objects.filter(pk=row.pk).update(quantity=99)
        with self.assertRaisesRegex(CommandError, 'preserved'):
            self.seed()
        row.refresh_from_db()
        self.assertEqual(row.quantity, 99)

    def test_modified_assessment_timestamp_rejects_replay_and_rolls_back_new_records(self):
        self.seed()
        row = EligibilityResult.objects.order_by('id').first()
        changed = row.assessed_at + timedelta(microseconds=1)
        EligibilityResult.objects.filter(pk=row.pk).update(assessed_at=changed)
        # The next import recreates this missing account before reaching the mismatch.
        User = get_user_model()
        victim = User.objects.filter(role='ADMIN').first()
        victim_id = victim.pk
        victim.delete()
        before = (User.objects.count(), DonorProfile.objects.count(), EligibilityResult.objects.count(), BloodRequest.objects.count())
        with self.assertRaisesRegex(CommandError, 'preserved'):
            self.seed()
        self.assertFalse(User.objects.filter(pk=victim_id).exists())
        self.assertEqual(before, (User.objects.count(), DonorProfile.objects.count(), EligibilityResult.objects.count(), BloodRequest.objects.count()))
        row.refresh_from_db()
        self.assertEqual(row.assessed_at, changed)

    def test_explicit_password_enables_only_four_demo_logins_and_is_never_printed(self):
        secret = 'synthetic-test-credential-only'
        with patch.dict(os.environ, {'DEMO_USER_PASSWORD': secret}):
            result = self.seed(password_env='DEMO_USER_PASSWORD')
        users = list(get_user_model().objects.all())
        self.assertEqual(sum(u.has_usable_password() for u in users), 4)
        self.assertNotIn(secret, json.dumps(result))
        admin = get_user_model().objects.get(email='admin-000@demo.example.test')
        self.assertTrue(admin.check_password(secret))
        self.assertFalse(admin.is_superuser)
        self.assertFalse(admin.is_staff)
        self.assertFalse(admin.user_permissions.exists())

    def test_missing_password_env_is_not_silently_used(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(CommandError, 'missing'):
                self.seed(password_env='DEMO_USER_PASSWORD')
        self.assertFalse(get_user_model().objects.exists())
