"""BB-20 atomic camp cancellation: service, API, rollback and PostgreSQL races.

Uses the REAL notification provider (no doubles) except where a failure is injected to prove
rollback. Mock delivery only; an already in-flight send cannot be recalled.
"""
import unittest
from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.test import Client, TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from notification_adapter.models import OutboxIntent
from scheduling.exceptions import ReminderUnavailable
from scheduling.models import Appointment, Camp, Slot
from scheduling.services.appointments import book_appointment
from scheduling.services.camps import cancel_camp
from scheduling.tests.helpers import PASSWORD, make_camp, make_donor, make_slot, make_user
from scheduling.tests.test_booking_concurrency import error_codes, run_parallel


def started_confirmed(camp, donor_profile):
    """A CONFIRMED appointment whose slot has already started (inside a camp that began)."""
    start = timezone.now() - timedelta(hours=1)
    slot = make_slot(camp, starts_at=start, ends_at=start + timedelta(hours=2))
    return Appointment.objects.create(donor=donor_profile, slot=slot)


class CancelCampServiceTests(TransactionTestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.camp = make_camp(capacity=20)
        self.slot_a = make_slot(self.camp, capacity=5)
        self.slot_b = make_slot(self.camp, capacity=5,
                                starts_at=self.camp.starts_at + timedelta(hours=3),
                                ends_at=self.camp.starts_at + timedelta(hours=5))
        self.donors = [make_donor() for _ in range(3)]
        self.bookings = [book_appointment(actor=self.donors[0][0], slot_id=self.slot_a.pk),
                         book_appointment(actor=self.donors[1][0], slot_id=self.slot_a.pk),
                         book_appointment(actor=self.donors[2][0], slot_id=self.slot_b.pk)]

    def cancel(self, reason='Venue unavailable', **kw):
        return cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason=reason, **kw)

    def intents(self):
        return OutboxIntent.objects.filter(event_type='APPOINTMENT_CANCELLED')

    def test_cancels_camp_and_every_confirmed_appointment_with_one_intent_each(self):
        when = timezone.now()
        payload = self.cancel(now=when)
        self.assertEqual(payload['status'], 'CANCELLED')
        self.camp.refresh_from_db()
        self.assertEqual((self.camp.status, self.camp.cancel_reason, self.camp.cancelled_at),
                         ('CANCELLED', 'Venue unavailable', when))
        rows = Appointment.objects.filter(slot__camp=self.camp)
        self.assertEqual({a.status for a in rows}, {'CANCELLED'})
        self.assertEqual({a.cancelled_at for a in rows}, {when})
        self.assertEqual(self.intents().count(), 3)
        accounts = {user.pk for user, _ in self.donors}
        self.assertEqual({i.recipient_id for i in self.intents()}, accounts)  # account, not profile
        self.assertEqual({i.due_at for i in self.intents()}, {when})
        self.assertEqual({str(i.record_id) for i in self.intents()},
                         {b['id'] for b in self.bookings})
        self.assertEqual(Slot.objects.filter(camp=self.camp).count(), 2)  # history kept

    def test_pending_reminders_are_invalidated(self):
        self.cancel()
        states = set(OutboxIntent.objects.filter(event_type='APPOINTMENT_REMINDER')
                     .values_list('state', flat=True))
        self.assertEqual(states, {'CANCELLED'})

    def test_started_confirmed_appointments_are_cancelled_too(self):
        camp = make_camp(starts_at=timezone.now() - timedelta(hours=2),
                         ends_at=timezone.now() + timedelta(hours=6))
        _, profile = make_donor()
        appointment = started_confirmed(camp, profile)
        cancel_camp(actor=self.staff, camp_id=camp.pk, reason='Emergency closure')
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'CANCELLED')
        self.assertTrue(self.intents().filter(record_id=appointment.pk).exists())

    def test_already_cancelled_appointment_is_untouched_and_gets_no_intent(self):
        from scheduling.services.appointments import cancel_appointment
        earlier = timezone.now() - timedelta(minutes=5)
        cancel_appointment(actor=self.donors[0][0], appointment_id=self.bookings[0]['id'],
                           now=earlier)
        self.cancel()
        kept = Appointment.objects.get(pk=self.bookings[0]['id'])
        self.assertEqual(kept.cancelled_at, earlier)
        self.assertEqual(self.intents().count(), 2)

    def test_replay_with_a_different_reason_changes_nothing(self):
        first = self.cancel('First reason')
        before = (self.intents().count(), Appointment.objects.filter(
            status='CANCELLED').count(), Camp.objects.get(pk=self.camp.pk).cancelled_at)
        replay = self.cancel('A different reason')
        self.assertEqual(replay, first)
        self.camp.refresh_from_db()
        self.assertEqual(self.camp.cancel_reason, 'First reason')
        self.assertEqual((self.intents().count(), Appointment.objects.filter(
            status='CANCELLED').count(), self.camp.cancelled_at), before)

    def test_empty_camp_cancels_without_effects(self):
        empty = make_camp()
        self.assertEqual(cancel_camp(actor=self.staff, camp_id=empty.pk,
                                     reason='No longer needed')['status'], 'CANCELLED')
        self.assertEqual(self.intents().count(), 0)

    def test_failure_on_a_later_intent_rolls_back_everything(self):
        from notification_adapter.services import reminders as provider
        real, calls = provider.enqueue_camp_cancellation, []

        def flaky(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise RuntimeError('storage failed')
            return real(**kwargs)

        with patch('scheduling.services.camps.enqueue_camp_cancellation', side_effect=flaky):
            with self.assertRaises(RuntimeError):
                self.cancel()
        self.assertEqual(len(calls), 2)
        self.camp.refresh_from_db()
        self.assertEqual((self.camp.status, self.camp.cancel_reason, self.camp.cancelled_at),
                         ('ACTIVE', '', None))
        self.assertEqual({a.status for a in Appointment.objects.filter(slot__camp=self.camp)},
                         {'CONFIRMED'})
        self.assertEqual(self.intents().count(), 0)
        self.assertEqual(set(OutboxIntent.objects.filter(event_type='APPOINTMENT_REMINDER')
                             .values_list('state', flat=True)), {'PENDING'})

    def test_failure_on_the_first_invalidation_rolls_back_everything(self):
        with patch('scheduling.services.camps.cancel_appointment_reminders',
                   side_effect=RuntimeError('invalidate failed')):
            with self.assertRaises(RuntimeError):
                self.cancel()
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).status, 'ACTIVE')
        self.assertEqual(Appointment.objects.filter(status='CANCELLED').count(), 0)
        self.assertEqual(self.intents().count(), 0)

    def test_missing_notification_policy_is_503_and_rolls_back(self):
        from core.errors import DecisionRequired
        with patch('scheduling.services.camps.enqueue_camp_cancellation',
                   side_effect=DecisionRequired('missing')):
            with self.assertRaises(ReminderUnavailable) as caught:
                self.cancel()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).status, 'ACTIVE')
        self.assertEqual(Appointment.objects.filter(status='CANCELLED').count(), 0)

    def test_roles_reason_and_missing_camp(self):
        for who in (make_donor()[0], make_user('REQUESTER'), make_user('STAFF', is_active=False),
                    make_user('ADMIN', is_superuser=True)):
            with self.subTest(who=who.role, active=who.is_active), self.assertRaises(PermissionDenied):
                cancel_camp(actor=who, camp_id=self.camp.pk, reason='x')
        for reason in ('', '   ', 'x' * 241, None, 5):
            with self.subTest(reason=reason), self.assertRaises(ValidationError):
                self.cancel(reason)
        with self.assertRaises(NotFound):
            cancel_camp(actor=self.staff, camp_id='11111111-1111-1111-1111-111111111111', reason='x')
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).status, 'ACTIVE')

    def test_after_cancelling_nothing_can_be_booked_and_donors_cannot_see_the_camp(self):
        from scheduling.exceptions import SlotUnavailable
        from scheduling.selectors.camps import list_camps
        self.cancel()
        with self.assertRaises(SlotUnavailable):
            book_appointment(actor=make_donor()[0], slot_id=self.slot_a.pk)
        donor = make_donor()[0]
        self.assertEqual(list_camps(actor=donor, filters={'status': None}, page=1,
                                    page_size=20)['count'], 0)

    def test_camp_cannot_be_edited_after_cancellation(self):
        from scheduling.services.camps import CampNotEditable, update_camp
        self.cancel()
        with self.assertRaises(CampNotEditable):
            update_camp(actor=self.staff, camp_id=self.camp.pk, data={'name': 'New'})


class CancelCampApiTests(TransactionTestCase):
    def setUp(self):
        self.staff = make_user('STAFF')
        self.camp = make_camp()
        self.url = f'/api/v1/camps/{self.camp.pk}/cancel'

    def make_client(self, user):
        client = Client(enforce_csrf_checks=True)
        if user:
            client.force_login(user)
        return client, client.get('/api/v1/auth/csrf').json()['csrf_token']

    def post(self, user, payload, csrf=True, url=None):
        client, token = self.make_client(user)
        extra = {'HTTP_X_CSRFTOKEN': token} if csrf else {}
        return client.post(url or self.url, payload, content_type='application/json', **extra)

    def test_staff_cancels_and_replay_returns_the_same_representation(self):
        first = self.post(self.staff, {'reason': '  Venue closed  '})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['status'], 'CANCELLED')
        again = self.post(make_user('ADMIN'), {'reason': 'Another reason'})
        self.assertEqual((again.status_code, again.json()), (200, first.json()))
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).cancel_reason, 'Venue closed')

    def test_csrf_is_required(self):
        self.assertEqual(self.post(self.staff, {'reason': 'x'}, csrf=False).status_code, 403)
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).status, 'ACTIVE')

    def test_wrong_roles_and_anonymous_are_denied_before_validation(self):
        for user in (make_donor()[0], make_user('REQUESTER'), None):
            r = self.post(user, {'bogus': 1})
            self.assertEqual(r.status_code, 403)
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).status, 'ACTIVE')

    def test_strict_body(self):
        for payload in ({}, {'reason': ''}, {'reason': '   '}, {'reason': 'x' * 241},
                        {'reason': 5}, {'reason': True}, {'reason': None},
                        {'reason': 'ok', 'extra': 1}, ['reason']):
            with self.subTest(payload=payload):
                self.assertEqual(self.post(self.staff, payload).status_code, 400)
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).status, 'ACTIVE')
        self.assertEqual(self.post(self.staff, {'reason': 'x' * 240}).status_code, 200)

    def test_unknown_camp_is_404(self):
        r = self.post(self.staff, {'reason': 'x'},
                      url='/api/v1/camps/11111111-1111-1111-1111-111111111111/cancel')
        self.assertEqual(r.status_code, 404)


@unittest.skipUnless(connection.vendor == 'postgresql', 'needs PostgreSQL row locking')
class CancelCampRaceTests(TransactionTestCase):
    """Separate connections, real locks. Run only on PostgreSQL."""

    def setUp(self):
        self.staff = make_user('STAFF')
        self.camp = make_camp(capacity=40)
        self.slot = make_slot(self.camp, capacity=30)

    def test_two_camp_cancellations_create_effects_once(self):
        for _ in range(3):
            book_appointment(actor=make_donor()[0], slot_id=self.slot.pk)
        results = run_parallel([lambda: cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason='A'),
                                lambda: cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason='B')])
        self.assertEqual([r[0] for r in results], ['ok', 'ok'], results)
        self.assertEqual(OutboxIntent.objects.filter(event_type='APPOINTMENT_CANCELLED').count(), 3)
        self.assertEqual(Appointment.objects.filter(status='CONFIRMED').count(), 0)
        self.assertIn(Camp.objects.get(pk=self.camp.pk).cancel_reason, {'A', 'B'})

    def test_booking_racing_cancellation_is_all_or_nothing(self):
        donors = [make_donor()[0] for _ in range(8)]
        jobs = [lambda d=d: book_appointment(actor=d, slot_id=self.slot.pk) for d in donors]
        jobs.append(lambda: cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason='Closed'))
        results = run_parallel(jobs)
        self.assertEqual([r for r in results if r[0] == 'crash'], [])
        self.assertEqual(set(error_codes(results)) - {'slot_unavailable'}, set())
        self.assertEqual(results[-1][0], 'ok')
        # No donor is left CONFIRMED in a cancelled camp, and every appointment that won the
        # race to book before the cancellation received exactly one cancellation intent.
        self.assertEqual(Appointment.objects.filter(status='CONFIRMED').count(), 0)
        cancelled = Appointment.objects.filter(status='CANCELLED').count()
        self.assertEqual(OutboxIntent.objects.filter(event_type='APPOINTMENT_CANCELLED').count(),
                         cancelled)
        self.assertEqual(cancelled, [r[0] for r in results[:-1]].count('ok'))

    def test_slot_creation_racing_cancellation_never_adds_a_slot_to_a_cancelled_camp(self):
        from scheduling.services.slots import create_slot
        start = self.camp.starts_at + timedelta(hours=4)
        data = {'camp_id': self.camp.pk, 'location': 'Chennai', 'starts_at': start,
                'ends_at': start + timedelta(hours=1), 'capacity': 2}
        results = run_parallel([
            lambda: create_slot(actor=self.staff, data=data),
            lambda: cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason='Closed')])
        self.assertEqual(results[1][0], 'ok', results)
        self.assertEqual(set(error_codes(results)) - {'invalid_transition'}, set())
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).status, 'CANCELLED')
        self.assertEqual(Slot.objects.filter(camp=self.camp).count(),
                         2 if results[0][0] == 'ok' else 1)

    def test_capacity_edit_racing_cancellation(self):
        from scheduling.services.camps import update_camp
        book_appointment(actor=make_donor()[0], slot_id=self.slot.pk)
        results = run_parallel([
            lambda: update_camp(actor=self.staff, camp_id=self.camp.pk, data={'capacity': 35}),
            lambda: cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason='Closed')])
        self.assertEqual(results[1][0], 'ok', results)
        self.assertEqual(set(error_codes(results)) - {'invalid_transition'}, set())
        self.assertEqual(Camp.objects.get(pk=self.camp.pk).status, 'CANCELLED')
        self.assertEqual(Appointment.objects.filter(status='CONFIRMED').count(), 0)


class CancelCampDeliveryTests(TransactionTestCase):
    """Camp cancellation through the REAL private Node mock transport (mock delivery only).

    Skipped, and so NOT evidence, where Node is unavailable. A send already in flight when a
    camp is cancelled cannot be recalled; these tests cover the before-send and after-send cases.
    """

    TOKEN = 'synthetic-test-only-dedicated-internal-token'

    def setUp(self):
        import shutil
        if not shutil.which('node'):
            self.skipTest('Node unavailable; real mock delivery after camp cancel NOT verified')
        self.staff = make_user('STAFF')
        self.now = timezone.now()
        self.camp = make_camp(starts_at=self.now + timedelta(hours=23),
                              ends_at=self.now + timedelta(hours=30), capacity=10)
        self.slot = make_slot(self.camp, capacity=5, starts_at=self.now + timedelta(hours=23),
                              ends_at=self.now + timedelta(hours=24))
        self.donors = [make_donor()[0] for _ in range(2)]
        for donor in self.donors:  # lead < 25h, so each reminder is queued as due immediately
            book_appointment(actor=donor, slot_id=self.slot.pk, now=self.now)

    def run_dispatch(self, directory, port):
        from django.test import override_settings
        from notification_adapter.services.dispatch import dispatch_due
        with override_settings(NOTIFICATION_BASE_URL='http://127.0.0.1:' + port,
                               NOTIFICATION_INTERNAL_TOKEN=self.TOKEN):
            return dispatch_due(now=timezone.now())

    def with_node(self, scenario):
        import os
        import queue
        import subprocess
        import tempfile
        import threading
        from django.conf import settings
        script = ("import {createNotificationServer} from './notification-service/src/server.mjs';"
                  "const s=createNotificationServer({token:process.env.BB22_TEST_TOKEN,"
                  "mockEnabled:true,receiptDir:process.env.BB22_TEST_DIR});"
                  "s.listen(0,'127.0.0.1',()=>console.log(s.address().port));")
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.Popen(
                ['node', '--input-type=module', '-e', script], cwd=settings.BASE_DIR,
                env={**os.environ, 'BB22_TEST_TOKEN': self.TOKEN, 'BB22_TEST_DIR': directory},
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                output = queue.Queue()
                threading.Thread(target=lambda: output.put(process.stdout.readline()),
                                 daemon=True).start()
                port = output.get(timeout=15).strip()
                self.assertTrue(port.isdigit())
                scenario(directory, port)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                process.stdout.close()

    def test_cancelled_before_dispatch_sends_only_cancellation_receipts(self):
        from pathlib import Path

        def scenario(directory, port):
            cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason='Venue closed')
            result = self.run_dispatch(directory, port)
            self.assertEqual(result['delivered'], 2, result)  # one cancellation per donor
            reminders = OutboxIntent.objects.filter(event_type='APPOINTMENT_REMINDER')
            self.assertEqual(set(reminders.values_list('state', flat=True)), {'CANCELLED'})
            self.assertFalse(reminders.filter(delivery_attempts__outcome='DELIVERED').exists())
            cancellations = OutboxIntent.objects.filter(event_type='APPOINTMENT_CANCELLED')
            self.assertEqual(set(cancellations.values_list('state', flat=True)), {'DELIVERED'})
            self.assertEqual(len(list(Path(directory).glob('*.json'))), 2)  # no reminder receipt

        self.with_node(scenario)

    def test_reminder_already_delivered_stays_historical_and_replay_adds_nothing(self):
        from pathlib import Path

        def scenario(directory, port):
            first = self.run_dispatch(directory, port)  # reminders are due now and deliver
            self.assertEqual(first['delivered'], 2, first)
            cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason='Venue closed')
            second = self.run_dispatch(directory, port)
            self.assertEqual(second['delivered'], 2, second)
            reminders = OutboxIntent.objects.filter(event_type='APPOINTMENT_REMINDER')
            self.assertEqual(set(reminders.values_list('state', flat=True)), {'DELIVERED'})
            self.assertEqual(len(list(Path(directory).glob('*.json'))), 4)
            # Replaying the cancel and dispatching again creates no new receipt.
            cancel_camp(actor=self.staff, camp_id=self.camp.pk, reason='Different reason')
            third = self.run_dispatch(directory, port)
            self.assertEqual(third['delivered'], 0, third)
            self.assertEqual(len(list(Path(directory).glob('*.json'))), 4)

        self.with_node(scenario)


class CancelCampSideEffectTests(TransactionTestCase):
    def setUp(self):
        self.staff = make_user('STAFF')

    def test_no_network_call_is_made_while_cancelling(self):
        camp = make_camp()
        slot = make_slot(camp, capacity=3)
        book_appointment(actor=make_donor()[0], slot_id=slot.pk)
        with patch('requests.sessions.Session.request',
                   side_effect=AssertionError('network call during cancellation')) as network, \
                patch('notification_adapter.services.dispatch.send_notification_intent',
                      side_effect=AssertionError('dispatch during cancellation')):
            cancel_camp(actor=self.staff, camp_id=camp.pk, reason='Closed')
        network.assert_not_called()
        self.assertEqual(OutboxIntent.objects.get(event_type='APPOINTMENT_CANCELLED').state,
                         'PENDING')  # queued only; delivery is a separate step after commit

    def test_upcoming_camp_count_follows_real_create_and_cancel(self):
        from scheduling.selectors.summary import upcoming_camp_count
        now = timezone.now()
        before = upcoming_camp_count(now=now)
        camp = make_camp()
        make_camp(starts_at=now - timedelta(days=1), ends_at=now + timedelta(hours=1))  # started
        self.assertEqual(upcoming_camp_count(now=now), before + 1)
        cancel_camp(actor=self.staff, camp_id=camp.pk, reason='Closed')
        self.assertEqual(upcoming_camp_count(now=now), before)
        self.assertEqual(upcoming_camp_count(now=camp.starts_at), before)  # boundary: >= now

    def test_upcoming_camp_count_requires_an_aware_datetime(self):
        from datetime import datetime
        from scheduling.selectors.summary import upcoming_camp_count
        for bad in (datetime(2026, 1, 1), '2026-01-01T00:00:00Z', None):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                upcoming_camp_count(now=bad)

    def test_upcoming_camp_count_missing_scheduling_app_is_unavailable_not_zero(self):
        from core.errors import DecisionRequired
        from scheduling.selectors.summary import upcoming_camp_count
        with patch('scheduling.selectors.summary.apps.get_model', side_effect=LookupError):
            with self.assertRaises(DecisionRequired):
                upcoming_camp_count(now=timezone.now())

    def test_reminder_context_reports_cancelled_camp_so_dispatch_blocks_nothing_new(self):
        from scheduling.selectors.reminders import reminder_context
        camp = make_camp()
        slot = make_slot(camp, capacity=3)
        booking = book_appointment(actor=make_donor()[0], slot_id=slot.pk)
        cancel_camp(actor=self.staff, camp_id=camp.pk, reason='Closed')
        context = reminder_context(appointment_id=booking['id'])
        self.assertEqual((context['appointment_status'], context['camp_status']),
                         ('CANCELLED', 'CANCELLED'))
