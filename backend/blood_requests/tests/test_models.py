"""BB-17 database guards: the constraints hold even if application validation is bypassed."""
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from blood_requests.models import BloodRequest
from blood_requests.models.request import COMPONENT_TYPES, STATUS_VALUES, URGENCY_VALUES
from blood_requests.tests.helpers import make_user

ROW = dict(blood_group='A+', component_type='PLASMA', quantity=3, urgency_level='ROUTINE')


class ConstraintTests(TestCase):
    def setUp(self):
        self.requester = make_user('REQUESTER')

    def assert_db_rejects(self, **overrides):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BloodRequest.objects.create(requester=self.requester, **{**ROW, **overrides})

    def test_defaults_are_submitted_zero_fulfilled_and_null_reason(self):
        row = BloodRequest.objects.create(requester=self.requester, **ROW)
        row.refresh_from_db()
        self.assertEqual((row.status, row.fulfilled_quantity, row.rejection_reason), ('SUBMITTED', 0, None))

    def test_quantity_range_is_enforced_by_the_database(self):
        for bad in (0, 101):
            with self.subTest(quantity=bad):
                self.assert_db_rejects(quantity=bad)
        for good in (1, 100):
            BloodRequest.objects.create(requester=self.requester, **{**ROW, 'quantity': good})

    def test_fulfilled_quantity_cannot_exceed_requested(self):
        self.assert_db_rejects(quantity=2, fulfilled_quantity=3)

    def test_enum_values_are_enforced_by_the_database(self):
        for field, bad in [('blood_group', 'C+'), ('component_type', 'CRYO'),
                           ('urgency_level', 'HIGH'), ('status', 'PENDING')]:
            with self.subTest(field=field):
                self.assert_db_rejects(**{field: bad})

    def test_constraint_tuples_match_model_choices(self):
        self.assertEqual(tuple(BloodRequest.ComponentType.values), COMPONENT_TYPES)
        self.assertEqual(tuple(BloodRequest.Urgency.values), URGENCY_VALUES)
        self.assertEqual(tuple(BloodRequest.Status.values), STATUS_VALUES)

    def test_requester_with_request_history_cannot_be_deleted(self):
        BloodRequest.objects.create(requester=self.requester, **ROW)
        with self.assertRaises(ProtectedError):
            self.requester.delete()
        self.assertEqual(BloodRequest.objects.count(), 1)

    def test_str_does_not_expose_personal_data(self):
        row = BloodRequest.objects.create(requester=self.requester, **ROW)
        self.assertEqual(str(row), str(row.id))
