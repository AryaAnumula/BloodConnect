"""BB19 ownership is applied before filters/count/slicing; direct boundaries stay guarded."""
import uuid
from datetime import datetime, timezone

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from blood_requests.selectors.tracking import own_requests, request_detail
from blood_requests.tests.helpers import RESPONSE_KEYS, make_request, make_user


class TrackingSelectorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user()
        cls.other = make_user()
        cls.staff = make_user('STAFF')
        cls.denied = [make_user('DONOR'), make_user('ADMIN'), make_user(is_active=False),
                      make_user(is_superuser=True), make_user('STAFF', is_superuser=True)]

    def test_owner_filter_precedes_count_order_and_pagination(self):
        when = datetime(2026, 11, 1, tzinfo=timezone.utc)
        routine = make_request(self.owner, urgency='ROUTINE', created_at=when)
        later = make_request(self.owner, urgency='CRITICAL', created_at=when,
                             id=uuid.UUID('00000000-0000-4000-8000-00000000000b'))
        first = make_request(self.owner, urgency='CRITICAL', created_at=when,
                             id=uuid.UUID('00000000-0000-4000-8000-00000000000a'))
        make_request(self.other, urgency='CRITICAL', created_at=when)
        pages = [own_requests(actor=self.owner, page=n, page_size=1) for n in (1, 2, 3)]
        self.assertEqual([p['count'] for p in pages], [3, 3, 3])
        self.assertEqual([p['results'][0]['id'] for p in pages], [str(r.id) for r in (first, later, routine)])
        self.assertEqual(own_requests(actor=self.owner, page=4, page_size=1)['results'], [])
        self.assertEqual(own_requests(actor=self.owner, page=10**100)['results'], [])

    def test_all_own_statuses_by_default_and_explicit_filter(self):
        for state in ('SUBMITTED', 'APPROVED', 'REJECTED', 'ISSUED', 'CLOSED'):
            make_request(self.owner, status=state)
            make_request(self.other, status=state)
        page = own_requests(actor=self.owner)
        self.assertEqual(page['count'], 5)
        self.assertEqual(set(page), {'count', 'page', 'page_size', 'results'})
        for state in ('SUBMITTED', 'APPROVED', 'REJECTED', 'ISSUED', 'CLOSED'):
            filtered = own_requests(actor=self.owner, status=state)
            self.assertEqual((filtered['count'], filtered['results'][0]['status']), (1, state))

    def test_empty_owner_and_page_size_boundaries(self):
        self.assertEqual(own_requests(actor=self.owner)['results'], [])
        self.assertEqual(own_requests(actor=self.owner, page_size=100)['page_size'], 100)

    def test_direct_query_argument_validation(self):
        for params in ({'status': ''}, {'status': 1}, {'status': 'PENDING'}, {'page': True},
                       {'page': '1'}, {'page': 0}, {'page': 1.5}, {'page_size': False},
                       {'page_size': 0}, {'page_size': 101}, {'page_size': None}):
            with self.subTest(params=params), self.assertRaises(ValidationError):
                own_requests(actor=self.owner, **params)

    def test_direct_role_gates(self):
        row = make_request(self.owner)
        for actor in [None, AnonymousUser(), *self.denied]:
            with self.subTest(role=getattr(actor, 'role', None)):
                with self.assertRaises(PermissionDenied):
                    own_requests(actor=actor)
                with self.assertRaises(PermissionDenied):
                    request_detail(actor=actor, request_id=row.id)
        with self.assertRaises(PermissionDenied):
            own_requests(actor=self.staff)

    def test_detail_own_staff_and_hidden_foreign(self):
        row = make_request(self.owner, status='REJECTED', rejection_reason='<b>Duplicate</b>')
        own = request_detail(actor=self.owner, request_id=row.id)
        self.assertEqual(set(own), RESPONSE_KEYS)
        self.assertEqual(own['rejection_reason'], '<b>Duplicate</b>')
        self.assertEqual(request_detail(actor=self.staff, request_id=row.id), own)
        for request_id in (row.id, uuid.uuid4()):
            with self.assertRaises(NotFound):
                request_detail(actor=self.other, request_id=request_id)
        for invalid in ('bad', None, 12):
            with self.assertRaises(NotFound):
                request_detail(actor=self.owner, request_id=invalid)
