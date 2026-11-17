"""Real ORM component tests. Missing donor-v1.0 boundaries are explicitly doubled.

The doubles adapt the existing real projection writer and evaluator only in tests;
they are not application implementations or full donor integration evidence.
"""
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from inspect import signature
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from donors.models import DonorProfile, EligibilityResult
from donors.configuration import approved_screening_rules
from donors.services.collections import record_confirmed_collection as real_writer
from donors.services.evaluation import evaluate as old_evaluate
from inventory.exceptions import IneligibleDonor, InventoryUnavailable, UnitConflict, UnsafeUnit
from inventory.models import BloodUnit, CollectionEvent
from inventory.selectors.collection_history import latest_confirmed_collection_date
from inventory.services.allocation import allocate_units
from inventory.services.units import record_unit


def evaluator_boundary_double(*, age_years, weight_kg, last_donation_date,
                              confirmed_collection_date, today, rules):
    if 'confirmed_collection_date' in signature(old_evaluate).parameters:
        return old_evaluate(age_years=age_years,weight_kg=weight_kg,
            last_donation_date=last_donation_date,confirmed_collection_date=confirmed_collection_date,
            today=today,rules=rules)
    effective = max((d for d in (last_donation_date, confirmed_collection_date) if d is not None), default=None)
    return old_evaluate(age_years=age_years, weight_kg=weight_kg,
                        last_donation_date=effective, today=today, rules=rules)


def facade_boundary_double(*, donor_id, collection_date):
    return real_writer(donor_id=donor_id, collected_on=collection_date)


class InventoryFixture:
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.staff = get_user_model().objects.create_user(email='staff@inventory.test', role='STAFF')
        self.user = get_user_model().objects.create_user(email='donor@inventory.test', role='DONOR')
        self.donor = DonorProfile.objects.create(user=self.user, full_name='Synthetic Donor',
            mobile='+919999999991', blood_group='A+', location='Test')
        self.assessment = EligibilityResult.objects.create(donor=self.donor, age_years=25,
            weight_kg=Decimal('60'), last_donation_date=None, confirmed_collection_date=None,
            status='ELIGIBLE', rules_version=approved_screening_rules()['rules_version'])
        self.payload = dict(unit_code='BC-TEST-1', donor_id=str(self.donor.pk),
            blood_group='A+', component_type='RBC', collection_date=self.today.isoformat(), quantity=1)

    def intake(self, **changes):
        with patch('inventory.services.units.evaluate', evaluator_boundary_double), patch(
                'inventory.services.units.record_confirmed_collection', facade_boundary_double):
            return record_unit(actor=self.staff, data=self.payload | changes)


class IntakeTests(InventoryFixture, TestCase):
    def test_atomic_intake_and_additional_component(self):
        first = self.intake()
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.last_confirmed_collection_date, self.today)
        self.assertEqual(first['expiry_date'], (self.today + timedelta(days=42)).isoformat())
        self.assertEqual(latest_confirmed_collection_date(donor_id=self.donor.pk), self.today)
        # An extra component must not need the now-stale result or touch projection.
        with patch('inventory.services.units.record_confirmed_collection') as writer:
            second = record_unit(actor=self.staff, data=self.payload | dict(
                unit_code='BC-TEST-2', component_type='PLASMA', collection_event_id=first['collection_event_id']))
        writer.assert_not_called()
        self.assertEqual(second['collection_event_id'], first['collection_event_id'])
        self.assertEqual(CollectionEvent.objects.count(), 1)
        self.assertEqual(BloodUnit.objects.count(), 2)

    def test_component_exclusivity_both_orders_and_duplicate(self):
        for initial, extra in [('WHOLE_BLOOD', 'RBC'), ('RBC', 'WHOLE_BLOOD'), ('RBC', 'RBC')]:
            with self.subTest(initial=initial, extra=extra), transaction.atomic():
                first = self.intake(component_type=initial)
                with self.assertRaises(UnitConflict):
                    self.intake(unit_code='second', component_type=extra,
                                collection_event_id=first['collection_event_id'])
                self.assertEqual(BloodUnit.objects.count(), 1)
                transaction.set_rollback(True)

    def test_duplicate_identity_rolls_back_history_and_event(self):
        first = self.intake()
        with self.assertRaises(UnitConflict):
            self.intake()
        # A different donor can have a valid assessment but cannot reuse unit_code.
        BloodUnit.objects.filter(pk=first['id']).update(unit_code='taken')
        self.payload['unit_code'] = 'taken'
        self.donor.last_confirmed_collection_date = None
        self.donor.save(update_fields=['last_confirmed_collection_date'])
        # Remove authoritative history only inside rollback-isolated fixture setup.
        with patch('inventory.services.units.latest_confirmed_collection_date', return_value=None):
            with self.assertRaises(UnitConflict):
                self.intake()
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.last_confirmed_collection_date)
        self.assertEqual(CollectionEvent.objects.count(), 1)

    def test_later_failure_rolls_back_all_three_records(self):
        with patch('inventory.services.units.BloodUnit.objects.create', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):
                self.intake()
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.last_confirmed_collection_date)
        self.assertEqual(CollectionEvent.objects.count(), 0)
        self.assertEqual(BloodUnit.objects.count(), 0)

    def test_projection_failure_rolls_back(self):
        def failing_writer(**kwargs):
            facade_boundary_double(**kwargs)
            raise RuntimeError('test')
        with patch('inventory.services.units.evaluate', evaluator_boundary_double), patch(
                'inventory.services.units.record_confirmed_collection', failing_writer):
            with self.assertRaises(RuntimeError):
                record_unit(actor=self.staff, data=self.payload)
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.last_confirmed_collection_date)
        self.assertFalse(CollectionEvent.objects.exists())

    def test_explicit_missing_donor_facade_fails_closed(self):
        with patch('inventory.services.units.evaluate',evaluator_boundary_double), patch(
                'inventory.services.donor_boundary.find_spec',return_value=None):
            with self.assertRaises(InventoryUnavailable):
                record_unit(actor=self.staff, data=self.payload)
        self.assertFalse(CollectionEvent.objects.exists())

    def test_explicit_old_evaluator_signature_fails_closed(self):
        def old_shape(*,age_years,weight_kg,last_donation_date,today,rules):
            raise AssertionError('An incompatible evaluator must never run.')
        with patch('inventory.services.units.evaluate',old_shape):
            with self.assertRaises(InventoryUnavailable):
                record_unit(actor=self.staff,data=self.payload)
        self.assertFalse(CollectionEvent.objects.exists())

    def test_stale_missing_ineligible_and_history_mismatch(self):
        for change, error in [({'rules_version': 'old'}, IneligibleDonor),
                              ({'status': 'INELIGIBLE'}, IneligibleDonor),
                              ({'confirmed_collection_date': self.today}, IneligibleDonor)]:
            with self.subTest(change=change), transaction.atomic():
                EligibilityResult.objects.filter(pk=self.assessment.pk).update(**change)
                with self.assertRaises(error):
                    self.intake()
                transaction.set_rollback(True)
        self.donor.last_confirmed_collection_date = self.today
        self.donor.save(update_fields=['last_confirmed_collection_date'])
        with self.assertRaises(InventoryUnavailable):
            self.intake()
        self.assertFalse(CollectionEvent.objects.exists())

    def test_protected_user_donor_event_deletion_and_deactivation(self):
        first = self.intake()
        for obj in (self.user, self.donor, CollectionEvent.objects.get(pk=first['collection_event_id']), self.staff):
            with self.subTest(model=type(obj).__name__), self.assertRaises(ProtectedError):
                obj.delete()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(BloodUnit.objects.count(), 1)
        with self.assertRaises(ValidationError):
            self.intake(unit_code='second', component_type='PLASMA', collection_event_id=first['collection_event_id'])

    def test_input_access_and_database_constraints(self):
        for changes in ({'quantity': True}, {'quantity': 2}, {'expiry_date': '2027-01-01'},
                        {'donor_id': 'bad'}, {'blood_group': 'X'}, {'component_type': 'X'},
                        {'unit_code': ' '}, {'collection_date': (self.today + timedelta(days=1)).isoformat()}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.intake(**changes)
        for role in ('DONOR', 'ADMIN', 'REQUESTER'):
            self.staff.role = role
            with self.assertRaises(PermissionDenied):
                record_unit(actor=self.staff, data=self.payload)
        self.staff.role = 'STAFF'
        self.staff.is_superuser = True
        with self.assertRaises(PermissionDenied):
            record_unit(actor=self.staff, data=self.payload)
        self.staff.is_superuser = False
        first = self.intake()
        for changes in ({'quantity': 2}, {'status': 'EXPIRED'}, {'component_type': 'X'}, {'unit_code': ''}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                BloodUnit.objects.filter(pk=first['id']).update(**changes)

    def test_allocation_caller_rollback_and_unsafe_states(self):
        first = self.intake()
        with transaction.atomic():
            result = allocate_units(actor=self.staff, unit_ids=[first['id']], blood_group='A+',
                                    component_type='RBC', issued_at=timezone.now())
            self.assertEqual(result, [{'unit_id': first['id'], 'quantity': 1}])
            with self.assertRaises(UnitConflict):
                allocate_units(actor=self.staff, unit_ids=[first['id']], blood_group='A+',
                               component_type='RBC', issued_at=timezone.now())
            transaction.set_rollback(True)
        self.assertEqual(BloodUnit.objects.get(pk=first['id']).status, 'AVAILABLE')
        for status in ('DISCARDED', 'QUARANTINED'):
            BloodUnit.objects.filter(pk=first['id']).update(status=status)
            with self.assertRaises(UnsafeUnit):
                allocate_units(actor=self.staff, unit_ids=[first['id']], blood_group='A+',
                               component_type='RBC', issued_at=timezone.now())

    def test_reconciliation_dry_run_and_ahead_stop(self):
        self.intake()
        self.donor.last_confirmed_collection_date = None
        self.donor.save(update_fields=['last_confirmed_collection_date'])
        out = StringIO()
        call_command('reconcile_collection_history', stdout=out)
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.last_confirmed_collection_date)
        self.assertIn('advances=1', out.getvalue())
        with patch('inventory.management.commands.reconcile_collection_history.record_confirmed_collection', facade_boundary_double):
            call_command('reconcile_collection_history', apply=True, stdout=StringIO())
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.last_confirmed_collection_date, self.today)
        self.donor.last_confirmed_collection_date = self.today + timedelta(days=1)
        self.donor.save(update_fields=['last_confirmed_collection_date'])
        with self.assertRaises(CommandError):
            call_command('reconcile_collection_history', apply=True, stdout=StringIO())


@override_settings(ROOT_URLCONF='inventory.tests.urls')
class IntakeAPITests(InventoryFixture, TestCase):
    def test_permissions_csrf_and_strict_body(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/v1/blood-units', self.payload, format='json').status_code, 403)
        client.force_login(self.staff)
        self.assertEqual(client.post('/api/v1/blood-units', self.payload, format='json').status_code, 403)
        token = 'a' * 32
        client.cookies['csrftoken'] = token
        with patch('inventory.services.units.evaluate', evaluator_boundary_double), patch(
                'inventory.services.units.record_confirmed_collection', facade_boundary_double):
            response = client.post('/api/v1/blood-units', self.payload, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['quantity'], 1)
        response = client.post('/api/v1/blood-units', self.payload | {'status': 'ISSUED'},
                               format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        response = client.post('/api/v1/blood-units', '{"quantity":1,"quantity":2}',
                               content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(BloodUnit.objects.count(), 1)
