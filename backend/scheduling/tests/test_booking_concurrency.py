"""BB-21 race tests: separate database connections, real row locks. PostgreSQL only.

On SQLite (no row locks) these are skipped, so they only count as evidence from a PostgreSQL run.
"""
import threading
import unittest

from django.db import connection, connections, transaction
from django.utils import timezone
from django.test import TransactionTestCase
from rest_framework.exceptions import APIException

from scheduling.models import Appointment
from scheduling.services.appointments import book_appointment
from scheduling.tests.helpers import make_camp, make_donor, make_slot


def run_parallel(jobs):
    barrier = threading.Barrier(len(jobs))
    results = [None] * len(jobs)

    def worker(i, job):
        try:
            barrier.wait(timeout=10)
            results[i] = ('ok', job())
        except APIException as exc:
            results[i] = ('error', exc.default_code)
        except Exception as exc:  # surfaced in the assertion below
            results[i] = ('crash', repr(exc))
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(i, j)) for i, j in enumerate(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    hung = [i for i, t in enumerate(threads) if t.is_alive()]
    if hung:  # a hang must fail clearly, not leave a None result behind
        raise AssertionError(f'threads {hung} did not finish within 30 seconds')
    return results


def error_codes(results):
    return [r[1] for r in results if r[0] == 'error']


@unittest.skipUnless(connection.vendor == 'postgresql', 'needs PostgreSQL row locking')
class BookingRaceTests(TransactionTestCase):
    def test_same_donor_overlapping_camp_and_walkin_slots_serialize(self):
        camp_slot = make_slot(make_camp(capacity=10))
        walkin = make_slot(None, starts_at=camp_slot.starts_at, ends_at=camp_slot.ends_at)
        donor = make_donor()[0]
        results = run_parallel([lambda: book_appointment(actor=donor, slot_id=camp_slot.id),
                                lambda: book_appointment(actor=donor, slot_id=walkin.id)])
        self.assertEqual([r[0] for r in results].count('ok'), 1, results)
        self.assertEqual(error_codes(results), ['appointment_conflict'])
        self.assertEqual(Appointment.objects.filter(status='CONFIRMED').count(), 1)
    def test_last_place_goes_to_exactly_one_donor(self):
        slot = make_slot(make_camp(capacity=10), capacity=1)
        donors = [make_donor()[0] for _ in range(6)]
        results = run_parallel([lambda d=d: book_appointment(actor=d, slot_id=slot.id) for d in donors])
        self.assertEqual([r[0] for r in results].count('ok'), 1, results)
        self.assertEqual([r for r in results if r[0] == 'crash'], [])
        self.assertEqual(error_codes(results), ['capacity_conflict'] * 5)  # losers lost on capacity
        self.assertEqual(Appointment.objects.filter(status='CONFIRMED').count(), 1)

    def test_walk_in_slot_last_place_goes_to_exactly_one_donor(self):
        slot = make_slot(None, capacity=1)  # no camp: only the slot lock protects it
        donors = [make_donor()[0] for _ in range(6)]
        results = run_parallel([lambda d=d: book_appointment(actor=d, slot_id=slot.id) for d in donors])
        self.assertEqual([r[0] for r in results].count('ok'), 1, results)
        self.assertEqual(error_codes(results), ['capacity_conflict'] * 5)
        self.assertEqual(Appointment.objects.filter(status='CONFIRMED').count(), 1)

    def test_camp_total_is_never_exceeded_across_slots(self):
        camp = make_camp(capacity=2)
        slots = [make_slot(camp, capacity=2) for _ in range(3)]
        donors = [make_donor()[0] for _ in range(6)]
        results = run_parallel([lambda d=d, s=slots[i % 3]: book_appointment(actor=d, slot_id=s.id)
                                for i, d in enumerate(donors)])
        self.assertEqual([r for r in results if r[0] == 'crash'], [])
        self.assertEqual(error_codes(results), ['capacity_conflict'] * 4)
        self.assertEqual(Appointment.objects.filter(status='CONFIRMED').count(), 2)

    def test_same_donor_double_click_books_once(self):
        slot = make_slot(make_camp(capacity=10), capacity=5)
        donor = make_donor()[0]
        results = run_parallel([lambda: book_appointment(actor=donor, slot_id=slot.id)] * 4)
        self.assertEqual([r[0] for r in results].count('ok'), 1, results)
        self.assertEqual([r for r in results if r[0] == 'crash'], [])
        self.assertEqual(error_codes(results), ['duplicate_booking'] * 3)  # losers are duplicates
        self.assertEqual(Appointment.objects.count(), 1)

    def test_booking_and_a_capacity_reduction_never_leave_the_camp_overbooked(self):
        from scheduling.models import Camp
        from scheduling.services.camps import update_camp
        from scheduling.tests.helpers import make_user
        camp = make_camp(capacity=3)
        slot = make_slot(camp, capacity=3)
        for _ in range(2):
            book_appointment(actor=make_donor()[0], slot_id=slot.id)  # 2 of 3 confirmed
        newcomer, admin = make_donor()[0], make_user('ADMIN')
        results = run_parallel([
            lambda: book_appointment(actor=newcomer, slot_id=slot.id),             # 3rd booking
            lambda: update_camp(actor=admin, camp_id=camp.id, data={'capacity': 2})])  # lower to 2
        self.assertEqual([r for r in results if r[0] == 'crash'], [])
        # Exactly one side wins: both lock the camp first, so they run one after the other.
        self.assertEqual(error_codes(results), ['capacity_conflict'], results)
        confirmed = Appointment.objects.filter(status='CONFIRMED').count()
        self.assertLessEqual(confirmed, Camp.objects.get(pk=camp.pk).capacity)


@unittest.skipUnless(connection.vendor == 'postgresql', 'needs PostgreSQL row locking')
class CancelRaceTests(TransactionTestCase):
    def test_double_cancel_and_a_booking_race_never_overbook(self):
        from scheduling.services.appointments import cancel_appointment
        slot = make_slot(make_camp(capacity=10), capacity=1)
        owner = make_donor()[0]
        appt = book_appointment(actor=owner, slot_id=slot.id)
        waiting = [make_donor()[0] for _ in range(4)]
        jobs = [lambda: cancel_appointment(actor=owner, appointment_id=appt['id'])] * 3
        jobs += [lambda d=d: book_appointment(actor=d, slot_id=slot.id) for d in waiting]
        results = run_parallel(jobs)
        self.assertEqual([r for r in results if r[0] == 'crash'], [])
        self.assertEqual([r[0] for r in results[:3]], ['ok'] * 3)  # every cancel call succeeds
        self.assertLessEqual([r[0] for r in results[3:]].count('ok'), 1)
        self.assertEqual(set(error_codes(results[3:])) - {'capacity_conflict'}, set())
        self.assertLessEqual(Appointment.objects.filter(status='CONFIRMED').count(), 1)
        self.assertEqual(Appointment.objects.get(pk=appt['id']).status, 'CANCELLED')


@unittest.skipUnless(connection.vendor == 'postgresql', 'needs PostgreSQL row locking')
class CollectionBookingRaceTests(TransactionTestCase):
    def test_booking_waits_for_a_collection_in_progress_then_rejects_the_stale_result(self):
        from donors.services.collections import record_confirmed_collection
        slot = make_slot(make_camp(capacity=10), capacity=3)
        donor, profile = make_donor()  # has a current ELIGIBLE result with no confirmed date
        outcome = []

        def booking():
            try:
                outcome.append(('ok', book_appointment(actor=donor, slot_id=slot.id)))
            except APIException as exc:
                outcome.append(('error', exc.default_code))
            except Exception as exc:  # surfaced in the assertion below
                outcome.append(('crash', repr(exc)))
            finally:
                connections.close_all()

        with transaction.atomic():
            record_confirmed_collection(donor_id=profile.pk, collected_on=timezone.localdate())
            thread = threading.Thread(target=booking)
            thread.start()
            thread.join(timeout=1.5)
            self.assertTrue(thread.is_alive(), 'booking must wait on the donor row lock')
        thread.join(timeout=30)
        self.assertFalse(thread.is_alive(), 'the booking thread hung')
        self.assertEqual(outcome, [('error', 'ineligible_donor')])
        self.assertEqual(Appointment.objects.count(), 0)
