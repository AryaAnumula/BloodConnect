"""PostgreSQL separate-connection tests; donor boundary doubles are test-only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from inventory.exceptions import IneligibleDonor, TransactionRequired, UnitConflict, UnsafeUnit
from inventory.models import BloodUnit
from inventory.services.allocation import allocate_units
from inventory.tests.test_intake import InventoryFixture, evaluator_boundary_double, facade_boundary_double
from inventory.services.units import record_unit


@skipUnless(connection.vendor == 'postgresql', 'Requires real PostgreSQL locks')
class InventoryConcurrencyTests(InventoryFixture, TransactionTestCase):
    def race(self, operation):
        barrier = Barrier(2)
        def worker(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation(index)
            except (IneligibleDonor, UnitConflict) as exc:
                return type(exc).__name__
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, i) for i in range(2)]
            return [future.result(timeout=20) for future in futures]

    def test_concurrent_collections_serialize_on_profile(self):
        with patch('inventory.services.units.evaluate', evaluator_boundary_double), patch(
                'inventory.services.units.record_confirmed_collection', facade_boundary_double):
            results = self.race(lambda i: record_unit(actor=self.staff,
                data=self.payload | {'unit_code': f'concurrent-{i}'}))
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertIn('IneligibleDonor', results)
        self.assertEqual(BloodUnit.objects.count(), 1)

    def test_allocation_competition_has_one_winner(self):
        first = self.intake()
        def allocate(index):
            with transaction.atomic():
                return allocate_units(actor=self.staff, unit_ids=[first['id']], blood_group='A+',
                                      component_type='RBC', issued_at=timezone.now())
        results = self.race(allocate)
        self.assertEqual(sum(isinstance(result, list) for result in results), 1)
        self.assertIn('UnitConflict', results)

    def test_allocation_requires_outer_transaction(self):
        with self.assertRaises(TransactionRequired):
            allocate_units(actor=self.staff, unit_ids=[], blood_group='A+', component_type='RBC', issued_at=timezone.now())

    def test_disposition_competition_preserves_one_terminal_history(self):
        from inventory.exceptions import InvalidTransition
        from inventory.models import InventoryDisposition
        from inventory.services.dispositions import record_disposition
        first = self.intake()
        def dispose(index):
            try:
                return record_disposition(actor=self.staff, unit_id=first['id'],
                    data={'status': ('DISCARDED','QUARANTINED')[index], 'reason':'Synthetic race'})
            except InvalidTransition:
                return 'invalid_transition'
        results = self.race(dispose)
        self.assertEqual(sum(isinstance(result,dict) for result in results),1)
        self.assertIn('invalid_transition',results)
        self.assertEqual(InventoryDisposition.objects.count(),1)

    def test_waiting_allocator_checks_clock_after_lock(self):
        first = self.intake()
        expiry = self.today + timedelta(days=1)
        BloodUnit.objects.filter(pk=first['id']).update(expiry_date=expiry)
        entered = Event()
        def waiting_allocator():
            close_old_connections()
            try:
                with transaction.atomic():
                    entered.set()
                    allocate_units(actor=self.staff, unit_ids=[first['id']], blood_group='A+',
                                   component_type='RBC', issued_at=timezone.now())
            except UnsafeUnit:
                return 'unsafe'
            finally:
                close_old_connections()
        # Hold the actual row lock while advancing a controlled date clock.
        with ThreadPoolExecutor(max_workers=1) as executor:
            with patch('inventory.services.allocation.timezone.localdate', return_value=self.today) as clock:
                with transaction.atomic():
                    BloodUnit.objects.select_for_update().get(pk=first['id'])
                    future = executor.submit(waiting_allocator)
                    self.assertTrue(entered.wait(timeout=5))
                    clock.return_value = expiry
                self.assertEqual(future.result(timeout=10), 'unsafe')
        self.assertEqual(BloodUnit.objects.get(pk=first['id']).status, 'AVAILABLE')
