"""BB-16 request-side issue logic (BC-D026). Inventory is a TEST-ONLY double here (see
issue_doubles.py); these tests prove request locking/state/rollback rules, not real units."""
import uuid
from datetime import timezone as dt_timezone
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.db import DatabaseError, IntegrityError
from django.test import TestCase
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from blood_requests.exceptions import (InventoryUnavailable, IssueInvalidTransition, Oversupply,
                                       StorageUnavailable, UnitConflict)
from blood_requests.integrations.inventory import InventoryContractError
from blood_requests.services.issue import issue_request
from blood_requests.tests.helpers import make_request, make_user
from blood_requests.tests.issue_doubles import FakeAllocator, FakeUnsafeUnit, doubles, unit_ids


class IssueServiceTests(TestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.row = make_request(make_user('REQUESTER'), status='APPROVED', quantity=3,
                                blood_group='O-', component_type='PLATELETS')

    def snapshot(self):
        self.row.refresh_from_db()
        return (self.row.status, self.row.fulfilled_quantity)

    def test_partial_batch_stays_approved_then_exact_completion_becomes_issued(self):
        with doubles() as allocator:
            first = issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(2))
            self.assertEqual((first['fulfilled_quantity'], first['request_status'], len(first['issues'])),
                             (2, 'APPROVED', 2))
            second = issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(1))
        self.assertEqual((second['fulfilled_quantity'], second['request_status']), (3, 'ISSUED'))
        self.assertEqual(self.snapshot(), ('ISSUED', 3))
        call = allocator.calls[0]
        self.assertEqual((call['blood_group'], call['component_type'], call['actor']), ('O-', 'PLATELETS', self.staff))
        self.assertEqual(call['unit_ids'], sorted(call['unit_ids']))  # stable UUID order
        self.assertIsNotNone(call['issued_at'].tzinfo)

    def test_response_shape_matches_issue_response(self):
        ids = unit_ids(1)
        with doubles():
            body = issue_request(actor=self.staff, request_id=self.row.id, unit_ids=ids)
        self.assertEqual(set(body), {'issues', 'fulfilled_quantity', 'request_status'})
        self.assertEqual(set(body['issues'][0]),
                         {'id', 'request_id', 'unit_id', 'issued_by', 'issued_at', 'issued_quantity'})
        self.assertEqual((body['issues'][0]['unit_id'], body['issues'][0]['issued_quantity']), (ids[0], 1))

    def test_ids_are_canonicalised_and_sorted_before_the_provider(self):
        ids = unit_ids(2)
        with doubles() as allocator:
            issue_request(actor=self.staff, request_id=self.row.id, unit_ids=[ids[1].upper(), ids[0]])
        self.assertEqual(allocator.calls[0]['unit_ids'], ids)

    def test_only_approved_requests_can_issue(self):
        for status in ('SUBMITTED', 'REJECTED', 'ISSUED', 'CLOSED'):
            with self.subTest(status=status):
                row = make_request(make_user('REQUESTER'), status=status, quantity=2,
                                   fulfilled_quantity=2 if status in ('ISSUED', 'CLOSED') else 0)
                with doubles() as allocator, self.assertRaises(IssueInvalidTransition):
                    issue_request(actor=self.staff, request_id=row.id, unit_ids=unit_ids(1))
                self.assertEqual(allocator.calls, [])  # inventory never touched

    def test_oversupply_is_rejected_before_inventory(self):
        with doubles() as allocator, self.assertRaises(Oversupply):
            issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(4))
        self.assertEqual(allocator.calls, [])
        with doubles():
            issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(2))
        with doubles(), self.assertRaises(Oversupply):
            issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(2))
        self.assertEqual(self.snapshot(), ('APPROVED', 2))

    def test_gate_applies_to_direct_calls(self):
        for actor in (None, AnonymousUser(), make_user('REQUESTER'), make_user('ADMIN'), make_user('DONOR'),
                      make_user('STAFF', is_active=False), make_user('STAFF', is_superuser=True)):
            with self.subTest(actor=getattr(actor, 'role', actor)):
                with doubles() as allocator, self.assertRaises(PermissionDenied):
                    issue_request(actor=actor, request_id=self.row.id, unit_ids=unit_ids(1))
                self.assertEqual(allocator.calls, [])

    def test_unit_id_validation_at_the_service_boundary(self):
        one = unit_ids(1)[0]
        for bad in ([], [one, one], [one, one.upper()], ['not-a-uuid'], [1], 'x', None, unit_ids(101)):
            with self.subTest(bad=str(bad)[:40]):
                with doubles(), self.assertRaises(ValidationError):
                    issue_request(actor=self.staff, request_id=self.row.id, unit_ids=bad)

    def test_unknown_request_is_not_found(self):
        for request_id in (uuid.uuid4(), 'not-a-uuid', None):
            with doubles(), self.assertRaises(NotFound):
                issue_request(actor=self.staff, request_id=request_id, unit_ids=unit_ids(1))

    def test_provider_errors_propagate_and_roll_back(self):
        for error in (FakeUnsafeUnit(), UnitConflict()):
            with self.subTest(error=type(error).__name__):
                with doubles(FakeAllocator(error=error)), self.assertRaises(type(error)):
                    issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(1))
                self.assertEqual(self.snapshot(), ('APPROVED', 0))

    def test_provider_contract_mismatch_rolls_back(self):
        ids = unit_ids(2)
        for result in ([{'unit_id': ids[0], 'quantity': 1}],
                       [{'unit_id': ids[1], 'quantity': 1}, {'unit_id': ids[0], 'quantity': 1}],
                       [{'unit_id': ids[0], 'quantity': 2}, {'unit_id': ids[1], 'quantity': 1}],
                       [{'unit_id': ids[0], 'quantity': True}, {'unit_id': ids[1], 'quantity': 1}],
                       [{'unit_id': ids[0], 'quantity': 1, 'x': 1}, {'unit_id': ids[1], 'quantity': 1}],
                       [{'unit_id': str(uuid.uuid4()), 'quantity': 1}, {'unit_id': ids[1], 'quantity': 1}],
                       None, 'oops'):
            with self.subTest(result=str(result)[:50]):
                with doubles(FakeAllocator(result=result)), self.assertRaises(InventoryContractError):
                    issue_request(actor=self.staff, request_id=self.row.id, unit_ids=ids)
                self.assertEqual(self.snapshot(), ('APPROVED', 0))

    def test_write_failures_roll_back_and_are_mapped(self):
        def boom(error):
            def writer(**kwargs):
                raise error
            return writer
        for error, expected in ((IntegrityError('dup unit'), UnitConflict), (DatabaseError('x'), StorageUnavailable)):
            with self.subTest(error=type(error).__name__):
                with doubles(writer=boom(error)), self.assertRaises(expected):
                    issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(1))
                self.assertEqual(self.snapshot(), ('APPROVED', 0))


class FailClosedWithoutRealInventoryTests(TestCase):
    """No doubles: the actual runtime state of this branch."""

    def setUp(self):
        self.staff = make_user('STAFF')
        self.row = make_request(make_user('REQUESTER'), status='APPROVED', quantity=2)

    def test_missing_provider_fails_closed(self):
        with self.assertRaises(InventoryUnavailable):
            issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(1))
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.fulfilled_quantity), ('APPROVED', 0))

    def test_missing_issue_record_model_fails_closed_even_with_a_provider(self):
        allocator = FakeAllocator()
        with mock.patch('blood_requests.services.issue.load_allocate_units', return_value=allocator):
            with self.assertRaises(InventoryUnavailable):
                issue_request(actor=self.staff, request_id=self.row.id, unit_ids=unit_ids(1))
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.fulfilled_quantity), ('APPROVED', 0))

    def test_real_import_errors_inside_a_provider_are_not_hidden(self):
        from blood_requests.integrations import inventory
        error = ModuleNotFoundError("No module named 'some_dependency'", name='some_dependency')
        with mock.patch.object(inventory.importlib, 'import_module', side_effect=error):
            with self.assertRaises(ModuleNotFoundError):
                inventory.load_allocate_units()
