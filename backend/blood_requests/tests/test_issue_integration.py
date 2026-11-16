"""BB-16 real-unit integration: NO doubles. Yashwitha's actual inventory.models.BloodUnit,
inventory.services.allocation.allocate_units and inventory.selectors.stock.stock_summary, with
this app's IssueRecord, in the caller-owned issue transaction.

Unit rows are inserted through the real BloodUnit/CollectionEvent ORM models as historical test
fixtures (synthetic example.test identities). They are not evidence of BB-13 intake, which
needs the donor facade from another owner.
"""
import itertools
import json
import threading
import unittest
from datetime import timedelta
from importlib.util import find_spec
from unittest import mock
from zoneinfo import ZoneInfo

from django.db import DatabaseError, connection, connections
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import APIException

from blood_requests.models import BloodRequest, IssueRecord
from blood_requests.selectors.reporting import request_issue_totals
from blood_requests.services.issue import issue_request
from blood_requests.tests.helpers import make_request, make_user, signed_in
from donors.models import DonorProfile
from inventory.models import BloodUnit, CollectionEvent
from inventory.selectors.stock import stock_summary

KOLKATA = ZoneInfo('Asia/Kolkata')
_seq = itertools.count(1)
WAIT = 20


def today():
    return timezone.localdate(timezone=KOLKATA)  # the provider's own clock basis


class UnitFactory:
    """Real BloodUnit rows for one synthetic donor per blood group."""

    def __init__(self, recorder):
        self.recorder = recorder
        self.donors = {}

    def donor(self, group):
        if group not in self.donors:
            n = next(_seq)
            user = make_user('DONOR')
            self.donors[group] = DonorProfile.objects.create(
                user=user, full_name=f'Synthetic Donor {n}', mobile=f'+9190000{n:05d}',
                blood_group=group, location='Test')
        return self.donors[group]

    def unit(self, *, group='A+', component='RBC', status='AVAILABLE', expiry=None):
        n = next(_seq)
        donor = self.donor(group)
        collected = today() - timedelta(days=10)
        event = CollectionEvent.objects.create(donor=donor, collection_date=collected, blood_group=group,
                                               recorded_by=self.recorder)
        return BloodUnit.objects.create(
            unit_code=f'BB16-TEST-{n}', donor=donor, collection_event=event, blood_group=group,
            component_type=component, collection_date=collected,
            expiry_date=expiry or today() + timedelta(days=5), status=status)


def usable(staff, group='A+', component='RBC'):
    rows = stock_summary(actor=staff, filters={'blood_group': group, 'component_type': component})['results']
    return rows[0]['available_quantity'] if rows else 0


def issue_url(request_id):
    return f'/api/v1/requests/{request_id}/issues'


class RealIssueTests(TestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.requester = make_user('REQUESTER')
        self.units = UnitFactory(self.staff)
        self.row = make_request(self.requester, status='APPROVED', quantity=2, blood_group='A+',
                                component_type='RBC')

    def state(self):
        self.row.refresh_from_db()
        return self.row.status, self.row.fulfilled_quantity

    def test_partial_then_full_issue_through_the_api_reduces_stock_exactly_once(self):
        u1, u2, spare = (self.units.unit() for _ in range(3))
        client, token = signed_in(self.staff)
        self.assertEqual(usable(self.staff), 3)

        response = client.post(issue_url(self.row.id), json.dumps({'unit_ids': [str(u1.id)]}),
                               content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body['request_status'], body['fulfilled_quantity']), ('APPROVED', 1))
        self.assertEqual([i['unit_id'] for i in body['issues']], [str(u1.id)])
        self.assertEqual(usable(self.staff), 2)

        response = client.post(issue_url(self.row.id), json.dumps({'unit_ids': [str(u2.id)]}),
                               content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.state(), ('ISSUED', 2))
        self.assertEqual(usable(self.staff), 1)

        statuses = dict(BloodUnit.objects.values_list('id', 'status'))
        self.assertEqual((statuses[u1.id], statuses[u2.id], statuses[spare.id]), ('ISSUED', 'ISSUED', 'AVAILABLE'))
        records = list(IssueRecord.objects.order_by('issued_at'))
        self.assertEqual([(r.unit_id, r.request_id, r.issued_by_id, r.issued_quantity) for r in records],
                         [(u1.id, self.row.id, self.staff.id, 1), (u2.id, self.row.id, self.staff.id, 1)])

        # A further issue against the now-ISSUED request changes nothing.
        response = client.post(issue_url(self.row.id), json.dumps({'unit_ids': [str(spare.id)]}),
                               content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual((response.status_code, response.json()['error']['code']), (422, 'invalid_transition'))
        self.assertEqual((usable(self.staff), IssueRecord.objects.count()), (1, 2))

    def test_one_batch_can_complete_the_request(self):
        ids = sorted(str(self.units.unit().id) for _ in range(2))
        result = issue_request(actor=self.staff, request_id=self.row.id, unit_ids=list(reversed(ids)))
        self.assertEqual([i['unit_id'] for i in result['issues']], ids)
        self.assertEqual(self.state(), ('ISSUED', 2))
        self.assertEqual(usable(self.staff), 0)

    def assert_nothing_changed(self, unit, unit_status, available):
        unit.refresh_from_db()
        self.assertEqual(unit.status, unit_status)
        self.assertEqual(self.state(), ('APPROVED', 0))
        self.assertFalse(IssueRecord.objects.exists())
        self.assertEqual(usable(self.staff), available)

    def test_unsafe_units_are_rejected_without_mutation(self):
        good = self.units.unit()
        cases = {
            'expires today (equality)': dict(expiry=today()),
            'expired yesterday': dict(expiry=today() - timedelta(days=1)),
            'discarded': dict(status='DISCARDED'),
            'quarantined': dict(status='QUARANTINED'),
            'wrong blood group': dict(group='O-'),
            'wrong component': dict(component='PLASMA'),
        }
        client, token = signed_in(self.staff)
        for label, kwargs in cases.items():
            with self.subTest(label):
                bad = self.units.unit(**kwargs)
                with self.assertRaises(APIException) as caught:
                    issue_request(actor=self.staff, request_id=self.row.id, unit_ids=[str(bad.id)])
                self.assertEqual((caught.exception.status_code, caught.exception.default_code), (422, 'unsafe_unit'))
                # A mixed batch is all-or-nothing: the good unit stays available.
                response = client.post(issue_url(self.row.id),
                                       json.dumps({'unit_ids': [str(good.id), str(bad.id)]}),
                                       content_type='application/json', HTTP_X_CSRFTOKEN=token)
                self.assertEqual((response.status_code, response.json()['error']['code']), (422, 'unsafe_unit'))
                self.assert_nothing_changed(bad, kwargs.get('status', 'AVAILABLE'), 1)
                self.assert_nothing_changed(good, 'AVAILABLE', 1)

    def test_already_issued_and_unknown_units(self):
        other = make_request(self.requester, status='APPROVED', quantity=1, blood_group='A+', component_type='RBC')
        unit = self.units.unit()
        issue_request(actor=self.staff, request_id=other.id, unit_ids=[str(unit.id)])
        with self.assertRaises(APIException) as caught:
            issue_request(actor=self.staff, request_id=self.row.id, unit_ids=[str(unit.id)])
        self.assertEqual((caught.exception.status_code, caught.exception.default_code), (409, 'unit_conflict'))
        client, token = signed_in(self.staff)
        response = client.post(issue_url(self.row.id),
                               json.dumps({'unit_ids': ['00000000-0000-4000-8000-000000000001']}),
                               content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.state(), ('APPROVED', 0))
        self.assertEqual(IssueRecord.objects.filter(request=self.row).count(), 0)

    def test_failure_after_allocation_rolls_back_units_records_and_request(self):
        u1, u2 = self.units.unit(), self.units.unit()
        ids = [str(u1.id), str(u2.id)]
        create = IssueRecord.objects.create
        calls = []

        def second_record_fails(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise RuntimeError('forced failure after allocation and one issue record')
            return create(**kwargs)

        with mock.patch.object(IssueRecord.objects, 'create', side_effect=second_record_fails):
            with self.assertRaises(RuntimeError):
                issue_request(actor=self.staff, request_id=self.row.id, unit_ids=ids)
        self.assertEqual(len(calls), 2)
        for unit in (u1, u2):
            self.assert_nothing_changed(unit, 'AVAILABLE', 2)

        with mock.patch.object(BloodRequest, 'save', side_effect=DatabaseError('forced')):
            with self.assertRaises(APIException) as caught:
                issue_request(actor=self.staff, request_id=self.row.id, unit_ids=ids)
        self.assertEqual(caught.exception.default_code, 'storage_unavailable')
        for unit in (u1, u2):
            self.assert_nothing_changed(unit, 'AVAILABLE', 2)

    def test_issue_history_is_protected(self):
        unit = self.units.unit()
        issue_request(actor=self.staff, request_id=self.row.id, unit_ids=[str(unit.id)])
        for obj in (unit, self.row, self.staff):
            with self.subTest(model=type(obj).__name__), self.assertRaises(ProtectedError):
                obj.delete()
        self.assertEqual(IssueRecord.objects.count(), 1)


class RealIssueTotalsTests(TestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.requester = make_user('REQUESTER')
        self.units = UnitFactory(self.staff)
        self.start = timezone.now().replace(microsecond=0) - timedelta(days=2)
        self.end = self.start + timedelta(days=1)

    def issue_at(self, when, request=None):
        request = request or make_request(self.requester, status='APPROVED', quantity=1,
                                          blood_group='A+', component_type='RBC')
        unit = self.units.unit()
        issue_request(actor=self.staff, request_id=request.id, unit_ids=[str(unit.id)])
        # Test setup only: place the real record at a controlled instant to probe boundaries.
        IssueRecord.objects.filter(unit=unit).update(issued_at=when)
        return request

    def test_half_open_interval_counts_actual_records(self):
        for when in (self.start - timedelta(microseconds=1), self.start,
                     self.end - timedelta(microseconds=1), self.end):
            self.issue_at(when)
        self.assertEqual(request_issue_totals(start=self.start, end=self.end), {'issued_unit_count': 2})
        self.assertEqual(request_issue_totals(), {'issued_unit_count': 4})
        self.assertEqual(request_issue_totals(start=self.end, end=self.end + timedelta(days=1)),
                         {'issued_unit_count': 1})

    @unittest.skipUnless(find_spec('blood_requests.services.closure'), 'BB-19 close service not on this base')
    def test_closing_a_request_does_not_change_totals(self):
        from blood_requests.services.closure import close_request
        request = self.issue_at(self.start)
        self.assertEqual(request_issue_totals(start=self.start, end=self.end), {'issued_unit_count': 1})
        close_request(actor=self.requester, request_id=request.id)
        self.assertEqual(BloodRequest.objects.get(pk=request.id).status, 'CLOSED')
        self.assertEqual(request_issue_totals(start=self.start, end=self.end), {'issued_unit_count': 1})

    @unittest.skipUnless(find_spec('reporting'), 'BB-24 reporting consumer not on this base')
    def test_reporting_provider_reads_real_totals(self):
        from reporting.providers.activity import issue_totals
        self.issue_at(self.start)
        self.assertEqual(issue_totals(start=self.start, end=self.end), {'issued_unit_count': 1})


@unittest.skipUnless(connection.vendor == 'postgresql', 'needs PostgreSQL row locks; SQLite is not evidence')
class RealSameUnitRaceTests(TransactionTestCase):
    """Separate connections: two staff issue the SAME real unit to two approved requests."""

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

    def setUp(self):
        self.staff = [make_user('STAFF'), make_user('STAFF')]
        self.units = UnitFactory(self.staff[0])
        requester = make_user('REQUESTER')
        self.requests = [make_request(requester, status='APPROVED', quantity=2, blood_group='A+',
                                      component_type='RBC') for _ in range(2)]

    def test_same_unit_to_two_requests_has_exactly_one_winner(self):
        unit = self.units.unit()
        results = self.run_parallel([
            (lambda s=s, r=r: issue_request(actor=s, request_id=r.id, unit_ids=[str(unit.id)]))
            for s, r in zip(self.staff, self.requests)])
        self.assertEqual(sorted(results, key=str)[0], ('error', 'unit_conflict'), results)
        self.assertEqual(sum(r[0] == 'ok' for r in results), 1, results)
        self.assertEqual(IssueRecord.objects.filter(unit=unit).count(), 1)
        unit.refresh_from_db()
        self.assertEqual(unit.status, 'ISSUED')
        fulfilled = sorted(BloodRequest.objects.filter(pk__in=[r.id for r in self.requests])
                           .values_list('fulfilled_quantity', flat=True))
        self.assertEqual(fulfilled, [0, 1])
        self.assertEqual(usable(self.staff[0]), 0)

    def test_overlapping_batches_in_opposite_order_do_not_deadlock(self):
        u1, u2 = self.units.unit(), self.units.unit()
        batches = [[str(u1.id), str(u2.id)], [str(u2.id), str(u1.id)]]
        results = self.run_parallel([
            (lambda s=s, r=r, b=b: issue_request(actor=s, request_id=r.id, unit_ids=b))
            for s, r, b in zip(self.staff, self.requests, batches)])
        self.assertEqual(sorted(r[0] for r in results), ['error', 'ok'], results)
        self.assertEqual([r[1] for r in results if r[0] == 'error'], ['unit_conflict'])
        self.assertEqual(IssueRecord.objects.count(), 2)
        self.assertEqual(set(IssueRecord.objects.values_list('request_id', flat=True)) & {r.id for r in self.requests},
                         {next(r.id for r, res in zip(self.requests, results) if res[0] == 'ok')})
        self.assertEqual(usable(self.staff[0]), 0)
