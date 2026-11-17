"""Real PostgreSQL close serialization on TEST-ONLY fully issued fixtures, not BB16 evidence."""
import threading
import unittest

from django.db import connection, connections
from django.test import TransactionTestCase

from blood_requests.models import BloodRequest
from blood_requests.services.closure import close_request
from blood_requests.tests.helpers import make_request, make_user


@unittest.skipUnless(connection.vendor == 'postgresql', 'requires actual PostgreSQL row locks')
class ClosureRaceTests(TransactionTestCase):
    def test_simultaneous_close_returns_one_transition_and_one_read_only_replay(self):
        owner = make_user()
        row = make_request(owner, status='ISSUED', fulfilled_quantity=2)
        barrier = threading.Barrier(2)
        results, failures, saves = [], [], []
        # Count actual UPDATEs through a DB wrapper on EACH separate worker connection.
        def observe(execute, sql, params, many, context):
            if sql.lstrip().upper().startswith('UPDATE "BLOOD_REQUESTS_BLOODREQUEST"'):
                saves.append(sql)
            return execute(sql, params, many, context)

        def worker():
            try:
                barrier.wait(timeout=15)
                with connections['default'].execute_wrapper(observe):
                    results.append(close_request(actor=owner, request_id=row.id))
            except BaseException as error:
                failures.append(repr(error))
            finally:
                connections.close_all()
        workers = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
        for worker_thread in workers:
            worker_thread.start()
        for worker_thread in workers:
            worker_thread.join(timeout=20)
        self.assertFalse(any(worker_thread.is_alive() for worker_thread in workers))
        self.assertEqual(failures, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(saves), 1, saves)
        row.refresh_from_db()
        self.assertEqual((row.status, row.fulfilled_quantity), ('CLOSED', 2))
        saved_time = row.updated_at
        close_request(actor=owner, request_id=row.id)
        self.assertEqual(BloodRequest.objects.get(pk=row.id).updated_at, saved_time)
