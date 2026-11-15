"""BB-17 submit_request(*, actor, data) called directly, bypassing the HTTP layer."""
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.db import DatabaseError
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from blood_requests.models import BloodRequest
from blood_requests.services.submission import submit_request
from blood_requests.tests.helpers import VALID, make_clinical_staff, make_user
from core.errors import DecisionRequired


class SubmitRequestServiceTests(TestCase):
    def test_returns_contract_dto_for_the_actor(self):
        actor = make_user('REQUESTER')
        dto = submit_request(actor=actor, data=dict(VALID))
        saved = BloodRequest.objects.get(pk=dto['id'])
        self.assertEqual(saved.requester, actor)
        self.assertEqual(dto['status'], 'SUBMITTED')

    def test_service_applies_the_same_gate_when_called_directly(self):
        actors = [AnonymousUser(), None, make_user('DONOR'), make_user('STAFF'), make_user('ADMIN'),
                  make_clinical_staff(), make_user('REQUESTER', is_active=False),
                  make_user('REQUESTER', is_superuser=True)]
        for actor in actors:
            with self.subTest(actor=getattr(actor, 'role', actor)):
                with self.assertRaises(PermissionDenied):
                    submit_request(actor=actor, data=dict(VALID))
        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_owner_and_status_cannot_be_injected_at_the_service_boundary(self):
        actor, other = make_user('REQUESTER'), make_user('REQUESTER')
        for extra in ({'requester_id': str(other.pk)}, {'requester': other}, {'status': 'ISSUED'},
                      {'fulfilled_quantity': 5}):
            with self.subTest(extra=list(extra)):
                with self.assertRaises(ValidationError):
                    submit_request(actor=actor, data={**VALID, **extra})
        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_policy_problem_raises_decision_required_and_saves_nothing(self):
        with mock.patch('blood_requests.configuration.POLICY_PATH', '/nonexistent.json'):
            with self.assertRaises(DecisionRequired):
                submit_request(actor=make_user('REQUESTER'), data=dict(VALID))
        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_failure_after_insert_rolls_back_the_row(self):
        actor = make_user('REQUESTER')
        with mock.patch('blood_requests.services.submission.request_dto',
                        side_effect=DatabaseError('synthetic failure after insert')):
            with self.assertRaises(DatabaseError):
                submit_request(actor=actor, data=dict(VALID))
        self.assertEqual(BloodRequest.objects.count(), 0)
        # The service still works afterwards.
        submit_request(actor=actor, data=dict(VALID))
        self.assertEqual(BloodRequest.objects.count(), 1)
