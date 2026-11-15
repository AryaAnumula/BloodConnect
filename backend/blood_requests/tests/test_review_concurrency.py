"""BB-18 review races on REAL PostgreSQL 16 with separate database connections (BC-D029-d).

Each worker thread gets its own Django connection. On SQLite these tests are SKIPPED and
therefore are not evidence. A connection/timeout error is a FAILURE, never a valid loser.
"""
import threading
import unittest

from django.db import connection, connections, transaction
from django.test import TransactionTestCase

from blood_requests.exceptions import InvalidTransition
from blood_requests.models import BloodRequest
from blood_requests.services.review import review_request
from blood_requests.tests.helpers import make_request, make_user

WAIT = 20  # seconds; bounded so a deadlock fails the test instead of hanging


def run_parallel(jobs):
    barrier = threading.Barrier(len(jobs))
    results = [None] * len(jobs)

    def worker(index, job):
        try:
            barrier.wait(timeout=WAIT)
            results[index] = ('ok', job())
        except InvalidTransition:
            results[index] = ('invalid_transition', None)
        except BaseException as exc:  # surfaced by the assertions below
            results[index] = ('crash', repr(exc))
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(i, job)) for i, job in enumerate(jobs)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=WAIT)
    return threads, results


@unittest.skipUnless(connection.vendor == 'postgresql', 'needs PostgreSQL row locks; SQLite is not evidence')
class ReviewRaceTests(TransactionTestCase):
    def test_simultaneous_approve_and_reject_have_exactly_one_winner(self):
        requester = make_user('REQUESTER')
        approver, rejecter = make_user('STAFF'), make_user('STAFF')
        for attempt in range(5):
            with self.subTest(attempt=attempt):
                row = make_request(requester)
                threads, results = run_parallel([
                    lambda: review_request(actor=approver, request_id=row.id, status='APPROVED'),
                    lambda: review_request(actor=rejecter, request_id=row.id, status='REJECTED',
                                           rejection_reason='Race loser reason'),
                ])
                self.assertFalse(any(t.is_alive() for t in threads), 'a worker did not finish')
                self.assertEqual([r for r in results if r is None or r[0] == 'crash'], [], results)
                outcomes = sorted(r[0] for r in results)
                self.assertEqual(outcomes, ['invalid_transition', 'ok'], results)
                winner_index = [r[0] for r in results].index('ok')
                winner_dto = results[winner_index][1]
                row.refresh_from_db()
                self.assertEqual(row.status, winner_dto['status'])
                if row.status == 'APPROVED':
                    self.assertEqual((row.reviewed_by_id, row.rejection_reason), (approver.pk, None))
                else:
                    self.assertEqual((row.reviewed_by_id, row.rejection_reason), (rejecter.pk, 'Race loser reason'))
                self.assertIsNotNone(row.reviewed_at)

    def test_second_reviewer_waits_for_the_lock_then_sees_the_decided_state(self):
        row = make_request(make_user('REQUESTER'))
        reviewer = make_user('STAFF')
        locked, release = threading.Event(), threading.Event()
        holder_error = []

        def hold_lock_and_decide():
            # Another transaction (on its own connection) holds the row lock and decides first.
            try:
                with transaction.atomic():
                    held = BloodRequest.objects.select_for_update().get(pk=row.pk)
                    held.status = 'APPROVED'
                    held.save(update_fields=['status'])
                    locked.set()
                    if not release.wait(timeout=WAIT):
                        raise TimeoutError('release not signalled')
            except BaseException as exc:
                holder_error.append(repr(exc))
            finally:
                connections.close_all()

        outcome = []

        def contender():
            try:
                review_request(actor=reviewer, request_id=row.id, status='REJECTED', rejection_reason='Too late')
                outcome.append('ok')
            except InvalidTransition:
                outcome.append('invalid_transition')
            except BaseException as exc:
                outcome.append(repr(exc))
            finally:
                connections.close_all()

        holder = threading.Thread(target=hold_lock_and_decide)
        holder.start()
        self.assertTrue(locked.wait(timeout=WAIT))
        second = threading.Thread(target=contender)
        second.start()
        second.join(timeout=1.0)
        self.assertTrue(second.is_alive(), 'the contender should be blocked on the row lock')
        release.set()
        holder.join(timeout=WAIT)
        second.join(timeout=WAIT)
        self.assertFalse(holder.is_alive() or second.is_alive())
        self.assertEqual(holder_error, [])
        self.assertEqual(outcome, ['invalid_transition'])
        row.refresh_from_db()
        self.assertEqual((row.status, row.rejection_reason, row.reviewed_by_id), ('APPROVED', None, None))
