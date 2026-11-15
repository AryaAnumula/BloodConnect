"""BB-18 PATCH /api/v1/requests/{request_id}/status (BC-D029-b/c/d) through the full stack."""
import json
import uuid
from unittest import mock

from django.db import DatabaseError
from django.test import Client, TestCase

from audit.models import SecurityEvent
from blood_requests.models import BloodRequest
from blood_requests.tests.helpers import (RESPONSE_KEYS, URL, VALID, make_clinical_staff, make_request,
                                          make_user, patch_json, post_json, review_url, signed_in)

REASON = 'Missing required request information'


class ReviewSuccessTests(TestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.client, self.token = signed_in(self.staff)
        self.requester = make_user('REQUESTER')
        self.row = make_request(self.requester, urgency='CRITICAL', quantity=7, blood_group='AB-',
                                component_type='PLASMA')

    def assert_contents_unchanged(self, row):
        self.assertEqual((row.requester_id, row.blood_group, row.component_type, row.quantity,
                          row.urgency_level, row.fulfilled_quantity),
                         (self.requester.pk, 'AB-', 'PLASMA', 7, 'CRITICAL', 0))

    def test_approve_saves_status_reviewer_and_time_and_returns_the_dto(self):
        response = patch_json(self.client, review_url(self.row.id), {'status': 'APPROVED'}, self.token)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(set(body), RESPONSE_KEYS)
        self.assertEqual((body['id'], body['status'], body['rejection_reason'], body['fulfilled_quantity']),
                         (str(self.row.id), 'APPROVED', None, 0))
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.rejection_reason, self.row.reviewed_by_id),
                         ('APPROVED', None, self.staff.pk))
        self.assertIsNotNone(self.row.reviewed_at.tzinfo)
        self.assert_contents_unchanged(self.row)

    def test_reject_saves_the_trimmed_reason_with_the_decision(self):
        response = patch_json(self.client, review_url(self.row.id),
                              {'status': 'REJECTED', 'rejection_reason': f'  {REASON}\n'}, self.token)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()['status'], response.json()['rejection_reason']), ('REJECTED', REASON))
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.rejection_reason, self.row.reviewed_by_id),
                         ('REJECTED', REASON, self.staff.pk))
        self.assert_contents_unchanged(self.row)

    def test_reason_of_exactly_240_characters_is_accepted(self):
        reason = 'r' * 240
        response = patch_json(self.client, review_url(self.row.id),
                              {'status': 'REJECTED', 'rejection_reason': f' {reason} '}, self.token)
        self.assertEqual(response.status_code, 200)
        self.row.refresh_from_db()
        self.assertEqual(self.row.rejection_reason, reason)

    def test_markup_in_a_reason_is_stored_as_plain_text(self):
        reason = '<script>alert(1)</script> & "quotes"'
        patch_json(self.client, review_url(self.row.id), {'status': 'REJECTED', 'rejection_reason': reason}, self.token)
        self.row.refresh_from_db()
        self.assertEqual(self.row.rejection_reason, reason)  # no storage escaping; UI uses textContent

    def test_clinical_staff_can_review_too(self):
        client, token = signed_in(make_clinical_staff())
        self.assertEqual(patch_json(client, review_url(self.row.id), {'status': 'APPROVED'}, token).status_code, 200)

    def test_approved_request_appears_in_the_approved_queue_not_the_pending_one(self):
        patch_json(self.client, review_url(self.row.id), {'status': 'APPROVED'}, self.token)
        self.assertEqual(self.client.get(URL).json()['count'], 0)
        self.assertEqual([r['id'] for r in self.client.get(URL + '?status=APPROVED').json()['results']],
                         [str(self.row.id)])


class ReviewValidationTests(TestCase):
    def setUp(self):
        self.client, self.token = signed_in(make_user('STAFF'))
        self.row = make_request(make_user('REQUESTER'))

    def assert_rejected(self, body=None, raw=None, code='validation_error', field=None):
        response = patch_json(self.client, review_url(self.row.id), body, self.token, raw=raw)
        self.assertEqual(response.status_code, 400, response.content)
        error = response.json()['error']
        self.assertEqual(error['code'], code)
        if field:
            self.assertIn(field, error['fields'])
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.rejection_reason, self.row.reviewed_by_id, self.row.reviewed_at),
                         ('SUBMITTED', None, None, None))
        return error

    def test_rejection_reason_is_required_and_bounded(self):
        for bad in ({}, {'rejection_reason': None}, {'rejection_reason': ''}, {'rejection_reason': '   \t\n'},
                    {'rejection_reason': 5}, {'rejection_reason': ['x']}, {'rejection_reason': True},
                    {'rejection_reason': 'x' * 241}):
            with self.subTest(body=bad):
                self.assert_rejected({'status': 'REJECTED', **bad}, field='rejection_reason')

    def test_approval_must_not_carry_a_reason_key_even_null(self):
        for value in (None, '', 'reason', 5):
            with self.subTest(value=value):
                self.assert_rejected({'status': 'APPROVED', 'rejection_reason': value}, field='rejection_reason')

    def test_only_approved_or_rejected_targets(self):
        for target in ('SUBMITTED', 'ISSUED', 'CLOSED', 'approved', '', None, 1, ['APPROVED']):
            with self.subTest(target=target):
                self.assert_rejected({'status': target}, field='status')
        self.assert_rejected({}, field='status')

    def test_unknown_and_server_controlled_keys_are_rejected(self):
        for extra in ({'reviewed_by': str(uuid.uuid4())}, {'reviewed_at': '2026-01-01T00:00:00Z'},
                      {'requester_id': str(uuid.uuid4())}, {'fulfilled_quantity': 1}, {'quantity': 9},
                      {'urgency_level': 'CRITICAL'}, {'id': str(uuid.uuid4())}):
            with self.subTest(extra=list(extra)):
                error = self.assert_rejected({'status': 'APPROVED', **extra})
                self.assertEqual(error['fields'], {'non_field_errors': ['Unexpected input field.']})

    def test_malformed_and_duplicate_key_json(self):
        self.assert_rejected(raw='{"status": "APPROVED"', code='invalid_json')
        self.assert_rejected(raw='{"status":"REJECTED","rejection_reason":"a","rejection_reason":"b"}',
                             code='invalid_json')
        self.assert_rejected(raw='{"status":"APPROVED","x":NaN}', code='invalid_json')
        for raw in ('[]', '"APPROVED"', 'null'):
            with self.subTest(raw=raw):
                self.assert_rejected(raw=raw)


class ReviewStateTests(TestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.client, self.token = signed_in(self.staff)
        self.requester = make_user('REQUESTER')

    def test_decided_requests_cannot_be_reviewed_again_and_history_is_kept(self):
        for first, second in [('APPROVED', 'APPROVED'), ('APPROVED', 'REJECTED'),
                              ('REJECTED', 'REJECTED'), ('REJECTED', 'APPROVED')]:
            with self.subTest(first=first, second=second):
                row = make_request(self.requester)
                body = lambda s: {'status': s, **({'rejection_reason': 'First reason'} if s == 'REJECTED' else {})}
                self.assertEqual(patch_json(self.client, review_url(row.id), body(first), self.token).status_code, 200)
                row.refresh_from_db()
                saved = (row.status, row.rejection_reason, row.reviewed_by_id, row.reviewed_at)
                other_client, other_token = signed_in(make_user('STAFF'))
                replay = body(second)
                if second == 'REJECTED':
                    replay['rejection_reason'] = 'Second reason'
                response = patch_json(other_client, review_url(row.id), replay, other_token)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()['error']['code'], 'invalid_transition')
                row.refresh_from_db()
                self.assertEqual((row.status, row.rejection_reason, row.reviewed_by_id, row.reviewed_at), saved)

    def test_issued_and_closed_requests_cannot_be_reviewed(self):
        for status in ('ISSUED', 'CLOSED'):
            with self.subTest(status=status):
                row = make_request(self.requester, status=status)
                response = patch_json(self.client, review_url(row.id), {'status': 'APPROVED'}, self.token)
                self.assertEqual(response.status_code, 422)
                row.refresh_from_db()
                self.assertEqual((row.status, row.reviewed_by_id), (status, None))

    def test_missing_request_is_404_and_malformed_id_is_404(self):
        response = patch_json(self.client, review_url(uuid.uuid4()), {'status': 'APPROVED'}, self.token)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error']['code'], 'not_found')
        # Malformed ids never match the <uuid:request_id> route (current repository convention).
        self.assertEqual(patch_json(self.client, review_url('not-a-uuid'), {'status': 'APPROVED'},
                                    self.token).status_code, 404)

    def test_storage_failure_returns_redacted_503_and_rolls_back(self):
        row = make_request(self.requester)
        with mock.patch('blood_requests.services.review.request_dto',
                        side_effect=DatabaseError('synthetic secret detail')):
            response = patch_json(self.client, review_url(row.id), {'status': 'APPROVED'}, self.token)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'storage_unavailable')
        self.assertNotIn('synthetic secret detail', response.content.decode())
        row.refresh_from_db()
        self.assertEqual((row.status, row.reviewed_by_id, row.reviewed_at), ('SUBMITTED', None, None))

    def test_wrong_methods(self):
        row = make_request(self.requester)
        self.assertEqual(self.client.get(review_url(row.id)).status_code, 405)
        self.assertEqual(self.client.post(review_url(row.id), data='{"status":"APPROVED"}',
                                          content_type='application/json', HTTP_X_CSRFTOKEN=self.token).status_code, 405)


class ReviewAccessTests(TestCase):
    def setUp(self):
        self.row = make_request(make_user('REQUESTER'))

    def assert_denied(self, client, token, code, actor=None):
        SecurityEvent.objects.all().delete()  # test isolation only
        response = patch_json(client, review_url(self.row.id), {'status': 'APPROVED'}, token)
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(response.json()['error']['code'], code)
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.reviewed_by_id), ('SUBMITTED', None))
        if code != 'csrf_failed':
            event = SecurityEvent.objects.get()  # exactly one denial event
            self.assertEqual((event.event_type, event.actor_id), ('access_denied', getattr(actor, 'pk', None)))

    def test_anonymous(self):
        client = Client(enforce_csrf_checks=True)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        self.assert_denied(client, token, 'authentication_required')

    def test_wrong_roles_and_every_superuser(self):
        for user in (make_user('REQUESTER'), make_user('DONOR'), make_user('ADMIN'),
                     make_user('STAFF', is_superuser=True, is_staff=True),
                     make_user('ADMIN', is_superuser=True, is_staff=True),
                     make_user('REQUESTER', is_superuser=True, is_staff=True)):
            with self.subTest(role=user.role, superuser=user.is_superuser):
                self.assert_denied(*signed_in(user), 'forbidden', user)

    def test_owner_requester_cannot_decide_their_own_request(self):
        self.assert_denied(*signed_in(self.row.requester), 'forbidden', self.row.requester)

    def test_deactivated_staff(self):
        staff = make_user('STAFF')
        client, token = signed_in(staff)
        staff.is_active = False
        staff.save(update_fields=['is_active'])
        self.assert_denied(client, token, 'authentication_required')

    def test_csrf_is_required(self):
        client, _ = signed_in(make_user('STAFF'))
        self.assert_denied(client, None, 'csrf_failed')
        self.assert_denied(client, 'c' * 32, 'csrf_failed')

    def test_denial_happens_before_body_validation(self):
        client, token = signed_in(make_user('DONOR'))
        response = patch_json(client, review_url(self.row.id), {'evil': 1}, token)
        self.assertEqual((response.status_code, response.json()['error']['code']), (403, 'forbidden'))


class Bb17RegressionTests(TestCase):
    def test_requester_post_still_works_and_lands_in_the_staff_queue(self):
        requester_client, token = signed_in(make_user('REQUESTER'))
        created = post_json(requester_client, VALID, token)
        self.assertEqual(created.status_code, 201)
        staff_client, _ = signed_in(make_user('STAFF'))
        self.assertEqual(staff_client.get(URL).json()['results'][0]['id'], created.json()['id'])
        self.assertEqual(BloodRequest.objects.get().reviewed_by, None)
        self.assertEqual(json.loads(created.content)['status'], 'SUBMITTED')
