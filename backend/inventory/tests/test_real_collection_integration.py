"""Real PR51 boundary only: no donor evaluator/facade development adapters.

Absent donor tranche is an explicit skip, never a passing integration claim.
Inventory write/storage fault injection below exercises real donor writes first.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib.util import find_spec
from inspect import signature
from io import StringIO
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from donors.configuration import approved_screening_rules
from donors.eligibility_reader import read_saved_results
from donors.models import DonorProfile, EligibilityResult
from donors.services.evaluation import evaluate
from donors.services.screening import screen_donor
from inventory.configuration import shelf_life_policy
from inventory.exceptions import IneligibleDonor, InventoryUnavailable
from inventory.models import BloodUnit, CollectionEvent
from inventory.services.units import record_unit


def real_donor_tranche_available():
    return (find_spec('donors.services.collection_history') is not None
            and 'confirmed_collection_date' in signature(evaluate).parameters)


class RealCollectionFixture:
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.rules = approved_screening_rules()
        self.staff = get_user_model().objects.create_user(email='real-staff@inventory.test',role='STAFF')
        self.user = get_user_model().objects.create_user(email='real-donor@inventory.test',role='DONOR')
        self.donor = DonorProfile.objects.create(user=self.user,full_name='Synthetic real-boundary donor',
            mobile='+919099999931',blood_group='A+',location='Synthetic integration')
        self.assessment = screen_donor(actor=self.user,donor_id=self.donor.pk,
            answers={'age_years':25,'weight_kg':'60.00','last_donation_date':None})
        self.payload = {'unit_code':'REAL-INTAKE-1','donor_id':str(self.donor.pk),
            'blood_group':'A+','component_type':'RBC','collection_date':self.today.isoformat(),'quantity':1}

    def old_assessment(self):
        return EligibilityResult.objects.filter(pk=self.assessment.pk).values().get()


@skipUnless(real_donor_tranche_available(),
            'Published PR51 facade and required-argument evaluator not composed; no donor adapters permitted')
class RealCollectionIntegrationTests(RealCollectionFixture, TestCase):
    def test_actual_intake_projection_and_additional_component(self):
        before = self.old_assessment()
        first = record_unit(actor=self.staff,data=self.payload)
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.last_confirmed_collection_date,self.today)
        event = CollectionEvent.objects.get(pk=first['collection_event_id'])
        unit = BloodUnit.objects.get(pk=first['id'])
        self.assertEqual((event.donor_id,event.blood_group,event.collection_date),
            (unit.donor_id,unit.blood_group,unit.collection_date))
        self.assertEqual(event.recorded_by_id,self.staff.pk)
        second = record_unit(actor=self.staff,data=self.payload|{'unit_code':'REAL-INTAKE-2',
            'component_type':'PLASMA','collection_event_id':str(event.pk)})
        self.assertEqual(second['collection_event_id'],str(event.pk))
        self.assertEqual(CollectionEvent.objects.count(),1)
        self.assertEqual(BloodUnit.objects.count(),2)
        self.assertEqual(self.old_assessment(),before)

    def test_later_unit_failure_rolls_back_actual_projection_event_and_unit(self):
        before = self.old_assessment()
        # The real facade/evaluator execute; only the final inventory insert fails.
        with patch('inventory.services.units.BloodUnit.objects.create',side_effect=RuntimeError('synthetic write failure')):
            with self.assertRaises(RuntimeError):
                record_unit(actor=self.staff,data=self.payload)
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.last_confirmed_collection_date)
        self.assertFalse(CollectionEvent.objects.exists())
        self.assertFalse(BloodUnit.objects.exists())
        self.assertEqual(self.old_assessment(),before)

    def test_actual_booking_rejects_history_stale_eligibility(self):
        from scheduling.exceptions import IneligibleDonor as BookingIneligible
        from scheduling.models import Appointment
        from scheduling.services.appointments import book_appointment
        from scheduling.services.camps import create_camp
        from scheduling.services.slots import create_slot
        record_unit(actor=self.staff,data=self.payload)
        saved = read_saved_results(donor_ids=[self.donor.pk])[str(self.donor.pk)]
        self.assertTrue(saved['is_history_stale'])
        start = timezone.now()+timedelta(days=7)
        camp = create_camp(actor=self.staff,data={'name':'Synthetic history camp','location':'Synthetic hall',
            'starts_at':start,'ends_at':start+timedelta(hours=2),'capacity':1})
        slot = create_slot(actor=self.staff,data={'camp_id':camp['id'],'location':'Synthetic hall',
            'starts_at':start,'ends_at':start+timedelta(hours=1),'capacity':1})
        with self.assertRaises(BookingIneligible):
            book_appointment(actor=self.user,slot_id=slot['id'])
        self.assertFalse(Appointment.objects.exists())

    def test_actual_reconciliation_preserves_assessment_and_resumes_intake(self):
        before = self.old_assessment()
        collected = self.today-timedelta(days=self.rules['min_days_between_donations']+1)
        # Labelled historical ORM fixture: genuine lagging projection, not new intake.
        with transaction.atomic():
            DonorProfile.objects.select_for_update(no_key=True).get(pk=self.donor.pk)
            event = CollectionEvent.objects.create(donor=self.donor,blood_group='A+',
                collection_date=collected,recorded_by=self.staff)
            BloodUnit.objects.create(unit_code='REAL-HISTORICAL',donor=self.donor,
                collection_event=event,blood_group='A+',component_type='RBC',collection_date=collected,
                expiry_date=collected+timedelta(days=shelf_life_policy()['RBC']))
        with self.assertRaises(InventoryUnavailable):
            record_unit(actor=self.staff,data=self.payload)
        call_command('reconcile_collection_history',stdout=StringIO())
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.last_confirmed_collection_date)
        call_command('reconcile_collection_history',apply=True,stdout=StringIO())
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.last_confirmed_collection_date,collected)
        self.assertEqual(self.old_assessment(),before)
        call_command('reconcile_collection_history',apply=True,stdout=StringIO())
        self.assertEqual(self.old_assessment(),before)
        current = screen_donor(actor=self.user,donor_id=self.donor.pk,
            answers={'age_years':25,'weight_kg':'60.00','last_donation_date':None})
        self.assertEqual(current.confirmed_collection_date,collected)
        record_unit(actor=self.staff,data=self.payload)
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.last_confirmed_collection_date,self.today)
        self.assertEqual(CollectionEvent.objects.count(),2)
        self.assertEqual(BloodUnit.objects.count(),2)
        self.assertEqual(self.old_assessment(),before)

    def test_ahead_projection_without_source_is_never_lowered(self):
        before = self.old_assessment()
        DonorProfile.objects.filter(pk=self.donor.pk).update(last_confirmed_collection_date=self.today)
        with self.assertRaises(CommandError):
            call_command('reconcile_collection_history',apply=True,stdout=StringIO())
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.last_confirmed_collection_date,self.today)
        self.assertEqual(self.old_assessment(),before)
        self.assertFalse(CollectionEvent.objects.exists())

    def test_failed_authoritative_read_is_not_empty_history(self):
        with patch('inventory.services.units.latest_confirmed_collection_date',
                   side_effect=DatabaseError('synthetic source unavailable')):
            with self.assertRaises(InventoryUnavailable):
                record_unit(actor=self.staff,data=self.payload)
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.last_confirmed_collection_date)
        self.assertFalse(CollectionEvent.objects.exists())
        self.assertFalse(BloodUnit.objects.exists())


@skipUnless(real_donor_tranche_available() and connection.vendor=='postgresql',
            'Needs actual published donor tranche and PostgreSQL; no donor adapters permitted')
class RealCollectionConcurrencyTests(RealCollectionFixture, TransactionTestCase):
    def test_two_actual_collections_have_one_winner(self):
        barrier = Barrier(2)
        def worker(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return record_unit(actor=self.staff,data=self.payload|{'unit_code':f'REAL-RACE-{index}'})
            except IneligibleDonor:
                return 'ineligible'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(worker,range(2)))
        self.assertEqual(sum(isinstance(result,dict) for result in results),1)
        self.assertIn('ineligible',results)
        self.assertEqual(CollectionEvent.objects.count(),1)
        self.assertEqual(BloodUnit.objects.count(),1)
