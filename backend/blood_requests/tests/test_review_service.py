"""BB-18 review_request(*, actor, request_id, status, rejection_reason=None) called directly."""
import uuid
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.db import DatabaseError
from django.db.models import ProtectedError
from django.test import TestCase
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from blood_requests.exceptions import InvalidTransition, StorageUnavailable
from blood_requests.services.review import review_request
from blood_requests.tests.helpers import make_request, make_user


class ReviewServiceTests(TestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.row = make_request(make_user('REQUESTER'))

    def test_direct_call_applies_the_staff_gate(self):
        for actor in (None, AnonymousUser(), make_user('REQUESTER'), make_user('ADMIN'), make_user('DONOR'),
                      make_user('STAFF', is_active=False), make_user('STAFF', is_superuser=True)):
            with self.subTest(actor=getattr(actor, 'role', actor)):
                with self.assertRaises(PermissionDenied):
                    review_request(actor=actor, request_id=self.row.id, status='APPROVED')
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, 'SUBMITTED')

    def test_direct_call_validates_target_and_reason(self):
        bad_calls = [dict(status='SUBMITTED'), dict(status='approved'), dict(status=None),
                     dict(status='APPROVED', rejection_reason='no'), dict(status='APPROVED', rejection_reason=''),
                     dict(status='REJECTED'), dict(status='REJECTED', rejection_reason='  '),
                     dict(status='REJECTED', rejection_reason=7), dict(status='REJECTED', rejection_reason='x' * 241)]
        for kwargs in bad_calls:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    review_request(actor=self.staff, request_id=self.row.id, **kwargs)

    def test_unknown_or_malformed_id_is_not_found(self):
        for request_id in (uuid.uuid4(), 'not-a-uuid', None, 12):
            with self.subTest(request_id=request_id):
                with self.assertRaises(NotFound):
                    review_request(actor=self.staff, request_id=request_id, status='APPROVED')

    def test_service_trims_and_saves_metadata(self):
        dto = review_request(actor=self.staff, request_id=str(self.row.id), status='REJECTED',
                             rejection_reason='  Out of scope  ')
        self.assertEqual(dto['rejection_reason'], 'Out of scope')
        self.row.refresh_from_db()
        self.assertEqual((self.row.reviewed_by, self.row.status), (self.staff, 'REJECTED'))

    def test_second_review_raises_invalid_transition(self):
        review_request(actor=self.staff, request_id=self.row.id, status='APPROVED')
        with self.assertRaises(InvalidTransition):
            review_request(actor=make_user('STAFF'), request_id=self.row.id, status='APPROVED')

    def test_failure_after_save_rolls_back_every_decision_field(self):
        with mock.patch('blood_requests.services.review.request_dto', side_effect=DatabaseError('x')):
            with self.assertRaises(StorageUnavailable):
                review_request(actor=self.staff, request_id=self.row.id, status='REJECTED', rejection_reason='r')
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.rejection_reason, self.row.reviewed_by_id, self.row.reviewed_at),
                         ('SUBMITTED', None, None, None))
        review_request(actor=self.staff, request_id=self.row.id, status='APPROVED')  # still works afterwards

    def test_reviewer_with_review_history_cannot_be_deleted(self):
        review_request(actor=self.staff, request_id=self.row.id, status='APPROVED')
        with self.assertRaises(ProtectedError):
            self.staff.delete()
