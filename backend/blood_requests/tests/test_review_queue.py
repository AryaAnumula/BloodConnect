"""BB-18 staff queue (BC-D029-a/c/e): GET /api/v1/requests and staff_queue selector."""
import uuid
from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth.models import AnonymousUser
from django.test import Client, TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.models import SecurityEvent
from blood_requests.selectors.review_queue import staff_queue
from blood_requests.tests.helpers import (RESPONSE_KEYS, URL, VALID, make_clinical_staff, make_request,
                                          make_user, post_json, signed_in)

T0 = datetime(2026, 11, 1, 8, 0, tzinfo=dt_timezone.utc)


def ids(page):
    return [row['id'] for row in page['results']]


class QueueOrderingTests(TestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.requester = make_user('REQUESTER')

    def test_interleaved_urgencies_sort_by_rank_then_oldest_then_id(self):
        r = self.requester
        routine_old = make_request(r, urgency='ROUTINE', created_at=T0)
        critical_new = make_request(r, urgency='CRITICAL', created_at=T0 + timedelta(hours=3))
        urgent_mid = make_request(r, urgency='URGENT', created_at=T0 + timedelta(hours=1))
        critical_old = make_request(r, urgency='CRITICAL', created_at=T0 + timedelta(hours=2))
        routine_new = make_request(r, urgency='ROUTINE', created_at=T0 + timedelta(hours=4))
        tie_b = make_request(r, urgency='URGENT', created_at=T0 + timedelta(hours=5),
                             id=uuid.UUID('00000000-0000-4000-8000-00000000000b'))
        tie_a = make_request(r, urgency='URGENT', created_at=T0 + timedelta(hours=5),
                             id=uuid.UUID('00000000-0000-4000-8000-00000000000a'))
        page = staff_queue(actor=self.staff)
        self.assertEqual(ids(page), [str(x.id) for x in (
            critical_old, critical_new, urgent_mid, tie_a, tie_b, routine_old, routine_new)])

    def test_pagination_spans_ranks_and_count_is_the_filtered_total(self):
        r = self.requester
        made = [make_request(r, urgency=u, created_at=T0 + timedelta(minutes=i))
                for i, u in enumerate(['ROUTINE', 'CRITICAL', 'URGENT', 'CRITICAL', 'ROUTINE'])]
        make_request(r, urgency='CRITICAL', status='APPROVED', created_at=T0)  # filtered out
        expected = [str(made[i].id) for i in (1, 3, 2, 0, 4)]
        pages = [staff_queue(actor=self.staff, page=p, page_size=2) for p in (1, 2, 3)]
        self.assertEqual(sum((ids(p) for p in pages), []), expected)
        self.assertEqual([p['count'] for p in pages], [5, 5, 5])
        self.assertEqual([len(p['results']) for p in pages], [2, 2, 1])
        beyond = staff_queue(actor=self.staff, page=4, page_size=2)
        self.assertEqual(beyond, {'count': 5, 'page': 4, 'page_size': 2, 'results': []})

    def test_default_is_submitted_and_explicit_status_filters(self):
        r = self.requester
        submitted = make_request(r)
        approved = make_request(r, status='APPROVED')
        rejected = make_request(r, status='REJECTED', rejection_reason='Synthetic reason')
        self.assertEqual(ids(staff_queue(actor=self.staff)), [str(submitted.id)])
        self.assertEqual(ids(staff_queue(actor=self.staff, status='APPROVED')), [str(approved.id)])
        self.assertEqual(ids(staff_queue(actor=self.staff, status='REJECTED')), [str(rejected.id)])
        for empty in ('ISSUED', 'CLOSED'):
            self.assertEqual(staff_queue(actor=self.staff, status=empty)['count'], 0)

    def test_empty_queue(self):
        self.assertEqual(staff_queue(actor=self.staff), {'count': 0, 'page': 1, 'page_size': 20, 'results': []})


class SelectorBoundaryTests(TestCase):
    def test_selector_denies_non_staff_directly(self):
        for actor in (None, AnonymousUser(), make_user('REQUESTER'), make_user('ADMIN'), make_user('DONOR'),
                      make_user('STAFF', is_active=False), make_user('STAFF', is_superuser=True)):
            with self.subTest(actor=getattr(actor, 'role', actor)):
                with self.assertRaises(PermissionDenied):
                    staff_queue(actor=actor)

    def test_selector_rejects_invalid_direct_arguments(self):
        staff = make_user('STAFF')
        for kwargs in ({'status': 'PENDING'}, {'status': 'submitted'}, {'status': 1}, {'page': 0},
                       {'page': True}, {'page': '1'}, {'page': 1.0}, {'page_size': 0}, {'page_size': 101},
                       {'page_size': False}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    staff_queue(actor=staff, **kwargs)

    def test_clinical_permission_is_not_needed_and_does_not_hurt(self):
        self.assertEqual(staff_queue(actor=make_clinical_staff())['count'], 0)


class QueueApiTests(TestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.client, self.token = signed_in(self.staff)

    def test_newly_submitted_request_appears_in_the_staff_queue(self):
        requester_client, token = signed_in(make_user('REQUESTER'))
        created = post_json(requester_client, VALID, token).json()
        body = self.client.get(URL).json()
        self.assertEqual(body['count'], 1)
        self.assertEqual(body['results'][0], created)  # same BB-17 DTO, nothing extra
        self.assertEqual(set(body['results'][0]), RESPONSE_KEYS)
        self.assertEqual(set(body), {'count', 'page', 'page_size', 'results'})

    def test_query_parameters_are_strict(self):
        for query in ('?status=PENDING', '?status=submitted', '?status=', '?page=', '?page_size=', '?page=0', '?page=-1', '?page=1.0',
                      '?page=abc', '?page_size=0', '?page_size=101', '?page_size=1e1', '?sort=created_at',
                      '?requester_id=x', '?status=SUBMITTED&status=APPROVED', '?page=1&page=2'):
            with self.subTest(query=query):
                response = self.client.get(URL + query)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()['error']['code'], 'validation_error')

    def test_valid_query_parameters(self):
        make_request(make_user('REQUESTER'), status='APPROVED')
        body = self.client.get(URL + '?status=APPROVED&page=1&page_size=100').json()
        self.assertEqual((body['count'], body['page'], body['page_size']), (1, 1, 100))
        self.assertEqual(self.client.get(URL + '?page=9').json()['results'], [])

    def test_response_has_no_review_metadata_or_account_details(self):
        requester = make_user('REQUESTER')
        make_request(requester)
        text = self.client.get(URL).content.decode()
        for hidden in ('reviewed_by', 'reviewed_at', requester.email, 'email', 'password'):
            self.assertNotIn(hidden, text)


class QueueAccessTests(TestCase):
    def assert_denied(self, client, code, actor=None):
        SecurityEvent.objects.all().delete()  # test isolation only
        response = client.get(URL)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], code)
        self.assertNotIn('results', response.json())
        event = SecurityEvent.objects.get()
        self.assertEqual((event.event_type, event.actor_id), ('access_denied', getattr(actor, 'pk', None)))

    def test_anonymous_and_wrong_roles_cannot_read_the_queue(self):
        make_request(make_user('REQUESTER'))
        self.assert_denied(Client(), 'authentication_required')
        for user in (make_user('DONOR'), make_user('ADMIN'),
                     make_user('STAFF', is_superuser=True, is_staff=True),
                     make_user('ADMIN', is_superuser=True, is_staff=True)):
            with self.subTest(role=user.role, superuser=user.is_superuser):
                self.assert_denied(signed_in(user)[0], 'forbidden', user)

    def test_deactivated_staff_session_is_rejected(self):
        staff = make_user('STAFF')
        client, _ = signed_in(staff)
        staff.is_active = False
        staff.save(update_fields=['is_active'])
        self.assert_denied(client, 'authentication_required')

    def test_staff_still_cannot_submit_requests(self):
        client, token = signed_in(make_user('STAFF'))
        response = post_json(client, VALID, token)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'forbidden')
