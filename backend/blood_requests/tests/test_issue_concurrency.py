"""BB-16 request-side race on REAL PostgreSQL 16 with separate connections.

Proves the REQUEST row lock: concurrent batches can never push fulfilled_quantity past the
requested quantity. Inventory is a TEST-ONLY double, so this is NOT the same-unit double-issue
proof; that test needs Yashwitha's real BloodUnit rows and is pending integration.
"""
import threading
import unittest

from django.db import connection, connections
from django.test import TransactionTestCase
from rest_framework.exceptions import APIException

from blood_requests.services.issue import issue_request
from blood_requests.tests.helpers import make_request, make_user
from blood_requests.tests.issue_doubles import doubles, unit_ids

WAIT = 20


@unittest.skipUnless(connection.vendor == 'postgresql', 'needs PostgreSQL row locks; SQLite is not evidence')
class IssueRequestLockRaceTests(TransactionTestCase):
    def run_parallel(self, jobs):
        barrier = threading.Barrier(len(jobs))
        results = [None] * len(jobs)

        def worker(index, job):
            try:
                barrier.wait(timeout=WAIT)
                results[index] = ('ok', job())
            except APIException as exc:
                results[index] = ('error', exc.default_code)
            except BaseException as exc:
                results[index] = ('crash', repr(exc))
            finally:
                connections.close_all()

        threads = [threading.Thread(target=worker, args=(i, job)) for i, job in enumerate(jobs)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=WAIT)
        self.assertFalse(any(t.is_alive() for t in threads), 'a worker hung')
        self.assertEqual([r for r in results if r is None or r[0] == 'crash'], [], results)
        return results

    def test_concurrent_batches_never_oversupply_one_request(self):
        row = make_request(make_user('REQUESTER'), status='APPROVED', quantity=2)
        staff = [make_user('STAFF') for _ in range(3)]
        with doubles():
            results = self.run_parallel([
                (lambda s=s: issue_request(actor=s, request_id=row.id, unit_ids=unit_ids(1))) for s in staff])
        self.assertEqual(sorted(r[0] for r in results), ['error', 'ok', 'ok'], results)
        # The last caller rereads after the lock: the request is already ISSUED, so the state
        # check (422 invalid_transition) fires before any oversupply check. Nothing is issued.
        self.assertEqual([r[1] for r in results if r[0] == 'error'], ['invalid_transition'])
        row.refresh_from_db()
        self.assertEqual((row.fulfilled_quantity, row.status), (2, 'ISSUED'))

    def test_two_full_batches_for_the_last_units_have_one_winner(self):
        row = make_request(make_user('REQUESTER'), status='APPROVED', quantity=3)
        with doubles():
            results = self.run_parallel([
                lambda: issue_request(actor=make_user('STAFF'), request_id=row.id, unit_ids=unit_ids(3)),
                lambda: issue_request(actor=make_user('STAFF'), request_id=row.id, unit_ids=unit_ids(3)),
            ])
        self.assertEqual(sorted(r[0] for r in results), ['error', 'ok'], results)
        loser = [r[1] for r in results if r[0] == 'error'][0]
        self.assertIn(loser, ('oversupply', 'invalid_transition'))  # ISSUED after the winner commits
        row.refresh_from_db()
        self.assertEqual((row.fulfilled_quantity, row.status), (3, 'ISSUED'))
