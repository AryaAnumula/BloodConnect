"""BB-16 reporting boundary for BB-24: request_issue_totals bounds and fail-closed behaviour.

Counts over real IssueRecord rows (interval boundaries) are in test_issue_integration.py.
"""
from datetime import date, datetime, timedelta, timezone as dt_timezone

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from blood_requests.selectors.reporting import pending_request_count, request_issue_totals
from blood_requests.tests.helpers import make_request, make_user

T0 = datetime(2026, 11, 16, 0, 0, tzinfo=dt_timezone.utc)


class IssueTotalsBoundsTests(TestCase):
    def test_invalid_bounds_are_rejected_without_an_all_time_fallback(self):
        naive = datetime(2026, 11, 16, 0, 0)
        cases = [dict(start=T0), dict(end=T0), dict(start=naive, end=naive + timedelta(days=1)),
                 dict(start=T0, end=naive), dict(start=T0, end=T0), dict(start=T0 + timedelta(days=1), end=T0),
                 dict(start=date(2026, 11, 16), end=date(2026, 11, 17)), dict(start='2026-11-16', end='2026-11-17')]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    request_issue_totals(**kwargs)

    def test_empty_history_is_a_real_zero(self):
        self.assertEqual(request_issue_totals(), {'issued_unit_count': 0})
        self.assertEqual(request_issue_totals(start=T0, end=T0 + timedelta(days=1)), {'issued_unit_count': 0})


class PendingCountTests(TestCase):
    def test_pending_request_count_counts_submitted_only(self):
        requester = make_user('REQUESTER')
        make_request(requester)
        make_request(requester, status='APPROVED')
        self.assertEqual(pending_request_count(), 1)
