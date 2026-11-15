"""S2-10 race tests on the donor profile lock (PostgreSQL only; skipped on SQLite).

Separate database connections in threads. Synthetic data only.
"""
import threading
import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from donors.eligibility_reader import read_saved_results
from donors.models import DonorProfile, EligibilityResult
from donors.services.collections import record_confirmed_collection
from donors.services.screening import screen_donor

PASSWORD = 'local-test-only-password'
RULES = {'rules_version': 'test-v1', 'min_age_years': 18, 'max_age_years': 65,
         'min_weight_kg': Decimal('50'), 'min_days_between_donations': 90}
COUNTER = {'n': 0}


def make_donor():
    COUNTER['n'] += 1
    user = get_user_model().objects.create_user(
        email=f'race{COUNTER["n"]}@example.test', password=PASSWORD)
    return user, DonorProfile.objects.create(
        user=user, full_name='Synthetic Donor', mobile=f'+9197000{COUNTER["n"]:05d}',
        blood_group='O+', location='Chennai')


def insert_fk_row(profile):
    """A stand-in for CollectionEvent/BloodUnit: any row with an FK to the profile takes
    FOR KEY SHARE on it, which is what makes FOR UPDATE upgrades deadlock-prone."""
    return EligibilityResult.objects.create(
        donor=profile, age_years=30, weight_kg=Decimal('60'), status='ELIGIBLE',
        reason_codes=[], reasons=[], rules_version='test-v1')


@unittest.skipUnless(connection.vendor == 'postgresql', 'needs PostgreSQL row locking')
class DonorLockRaceTests(TransactionTestCase):
    def run_two_collections(self, immediate_fk_checks):
        """Two transactions each insert an FK row to the profile, then record a collection.

        Django's PostgreSQL foreign keys are DEFERRABLE INITIALLY DEFERRED, so by default the
        FK check (FOR KEY SHARE on the profile) runs only at commit. With immediate_fk_checks the
        check runs at insert time, which is when a FOR UPDATE lock upgrade could deadlock.
        """
        _, profile = make_donor()
        today = timezone.localdate()
        dates = [today - timedelta(days=5), today - timedelta(days=2)]
        barrier = threading.Barrier(2)
        outcomes = [None, None]

        def collect(index):
            try:
                with transaction.atomic():
                    if immediate_fk_checks:
                        with connection.cursor() as cursor:
                            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                    insert_fk_row(profile)          # KEY SHARE on the profile row (if immediate)
                    barrier.wait(timeout=10)         # both have inserted before either locks
                    record_confirmed_collection(donor_id=profile.pk, collected_on=dates[index])
                outcomes[index] = 'ok'
            except Exception as exc:  # a deadlock would surface here
                outcomes[index] = repr(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=collect, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        self.assertFalse(any(t.is_alive() for t in threads), 'a collection thread hung')
        self.assertEqual(outcomes, ['ok', 'ok'])
        profile.refresh_from_db()
        self.assertEqual(profile.last_confirmed_collection_date, dates[1])

    def test_two_collections_with_deferred_fk_checks_do_not_deadlock(self):
        self.run_two_collections(immediate_fk_checks=False)

    def test_two_collections_with_immediate_fk_checks_do_not_deadlock(self):
        # Fails with FOR UPDATE (deadlock detected); passes with FOR NO KEY UPDATE.
        self.run_two_collections(immediate_fk_checks=True)

    @patch('donors.services.screening.approved_screening_rules', return_value=RULES)
    def test_screening_waits_for_a_collection_in_progress_and_then_sees_it(self, _rules):
        user, profile = make_donor()
        collected = timezone.localdate() - timedelta(days=10)
        saved = {}

        def screen():
            try:
                saved['result'] = screen_donor(
                    actor=user, donor_id=profile.pk,
                    answers={'age_years': 30, 'weight_kg': '60', 'last_donation_date': None})
            except Exception as exc:
                saved['error'] = repr(exc)
            finally:
                connections.close_all()

        with transaction.atomic():
            record_confirmed_collection(donor_id=profile.pk, collected_on=collected)
            thread = threading.Thread(target=screen)
            thread.start()
            thread.join(timeout=1.5)
            self.assertTrue(thread.is_alive(), 'screening must wait on the donor row lock')
        thread.join(timeout=30)
        self.assertFalse(thread.is_alive(), 'the screening thread hung')
        self.assertNotIn('error', saved)
        result = saved['result']
        self.assertEqual(result.confirmed_collection_date, collected)  # seen, not missed
        self.assertEqual(result.status, 'INELIGIBLE')
        self.assertFalse(read_saved_results(donor_ids=[profile.pk])[str(profile.pk)]['is_history_stale'])

    @patch('donors.services.screening.approved_screening_rules', return_value=RULES)
    def test_a_collection_committed_after_screening_makes_that_result_history_stale(self, _rules):
        user, profile = make_donor()
        screen_donor(actor=user, donor_id=profile.pk,
                     answers={'age_years': 30, 'weight_kg': '60', 'last_donation_date': None})
        with transaction.atomic():
            record_confirmed_collection(donor_id=profile.pk, collected_on=timezone.localdate())
        self.assertTrue(read_saved_results(donor_ids=[profile.pk])[str(profile.pk)]['is_history_stale'])
