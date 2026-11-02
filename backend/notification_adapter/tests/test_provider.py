import json,tempfile,uuid
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from django.test import TransactionTestCase,override_settings
from django.db import transaction,connection
from django.utils import timezone
from core.errors import DecisionRequired
from notification_adapter.models import OutboxIntent,DeliveryAttempt
from notification_adapter.services.intents import enqueue_intent,EventConflict
from notification_adapter.services.reminders import schedule_appointment_reminder,cancel_appointment_reminders
from notification_adapter.services.dispatch import dispatch_due
from notification_adapter.client import NotificationTransportUnavailable

class ProviderTests(TransactionTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        path=Path(self.temp.name)/'policy.json'
        path.write_text(json.dumps({'decisions':[{'id':x,'status':'APPROVED','approved_by':'synthetic test only','approved_at':'2026-01-01','evidence':'TEST FIXTURE ONLY'} for x in ['S2-06','S2-07']]}))
        self.override=override_settings(NOTIFICATION_DECISIONS_FILE=path);self.override.enable();self.addCleanup(self.override.disable)
        self.now=timezone.now();self.kw=dict(event_id=uuid.uuid4(),recipient_id=uuid.uuid4(),event_type='LOW_STOCK',record_id=uuid.uuid4(),due_at=self.now,channels=['IN_APP'])
    def enqueue(self):
        with transaction.atomic(): return enqueue_intent(**self.kw)
    def reminder(self,**extra):
        kw=dict(appointment_id=uuid.uuid4(),donor_user_id=uuid.uuid4(),starts_at=self.now+timedelta(days=2),booked_at=self.now)
        kw.update(extra)
        with transaction.atomic(): return schedule_appointment_reminder(**kw)
    def test_unapproved_policy_has_no_writes(self):
        with override_settings(NOTIFICATION_DECISIONS_FILE=Path(self.temp.name)/'missing'):
            with self.assertRaises(DecisionRequired):self.enqueue()
        self.assertEqual(OutboxIntent.objects.count(),0)
    def test_atomic_required(self):
        with self.assertRaises(RuntimeError):enqueue_intent(**self.kw)
    def test_rollback_removes_intent(self):
        with self.assertRaises(ValueError):
            with transaction.atomic():
                enqueue_intent(**self.kw);raise ValueError()
        self.assertEqual(OutboxIntent.objects.count(),0)
    def test_idempotence_and_conflict(self):
        self.assertEqual(self.enqueue(),self.enqueue())
        self.kw['recipient_id']=uuid.uuid4()
        with self.assertRaises(EventConflict):self.enqueue()
    def test_validation(self):
        for key,value in [('channels',[]),('channels',['IN_APP','IN_APP']),('recipient_id','bad'),('due_at',self.now.replace(tzinfo=None)),('event_type','BAD')]:
            kw={**self.kw,key:value}
            with self.assertRaises(ValueError):
                with transaction.atomic():enqueue_intent(**kw)
    def test_timing_boundaries(self):
        for hours,late in [(48,False),(24,False),(23,True)]:
            result=self.reminder(starts_at=self.now+timedelta(hours=hours))
            row=OutboxIntent.objects.get(pk=result['id']);self.assertEqual(row.late_booking,late)
            self.assertEqual(row.due_at,self.now if late else row.scheduled_for-timedelta(hours=24))
    def test_past_appointment_rejected(self):
        with self.assertRaises(ValueError):self.reminder(starts_at=self.now)
    def test_cancel_atomic(self):
        result=self.reminder();row=OutboxIntent.objects.get(pk=result['id'])
        with transaction.atomic():self.assertEqual(cancel_appointment_reminders(appointment_id=row.record_id),1)
        row.refresh_from_db();self.assertEqual(row.state,'CANCELLED')
    def test_send_outside_transaction_and_delivery_record(self):
        self.enqueue()
        def send(**kw):
            self.assertFalse(connection.in_atomic_block);self.assertEqual(set(kw['event']),{'event_id','recipient_id','type','record_id','due_at','channels'});return {}
        with patch('notification_adapter.services.dispatch.send_notification_intent',side_effect=send):result=dispatch_due(now=self.now)
        self.assertEqual(result['delivered'],1);self.assertEqual(DeliveryAttempt.objects.count(),1)
        self.assertEqual(dispatch_due(now=self.now)['delivered'],0)
    def test_retry_exhaustion(self):
        self.enqueue()
        with patch('notification_adapter.services.dispatch.send_notification_intent',side_effect=NotificationTransportUnavailable()):
            for seconds in [0,61,182]:
                current=self.now+timedelta(seconds=seconds)
                with patch('notification_adapter.services.dispatch.timezone.now',return_value=current):
                    dispatch_due(now=current)
        row=OutboxIntent.objects.get();self.assertEqual(row.state,'FAILED');self.assertEqual(row.attempts,3)
    def test_missing_real_appointment_reader_blocks(self):
        self.reminder(starts_at=self.now+timedelta(hours=24))
        with patch('notification_adapter.services.dispatch.send_notification_intent') as send:
            result=dispatch_due(now=self.now);send.assert_not_called()
        self.assertEqual(result['blocked'],1);self.assertEqual(DeliveryAttempt.objects.count(),0)
    def test_changed_appointment_cancels(self):
        self.reminder(starts_at=self.now+timedelta(hours=24))
        with patch('notification_adapter.services.dispatch._reminder_current',return_value=False),patch('notification_adapter.services.dispatch.send_notification_intent') as send:
            self.assertEqual(dispatch_due(now=self.now)['cancelled'],1);send.assert_not_called()
    def test_expired_lease_recovered(self):
        self.enqueue();OutboxIntent.objects.update(state='LEASED',lease_token=uuid.uuid4(),lease_until=self.now-timedelta(seconds=1))
        with patch('notification_adapter.services.dispatch.send_notification_intent',return_value={}):self.assertEqual(dispatch_due(now=self.now)['delivered'],1)
    def test_cancel_during_send_not_overwritten(self):
        self.enqueue()
        def send(**kw):OutboxIntent.objects.update(state='CANCELLED');return {}
        with patch('notification_adapter.services.dispatch.send_notification_intent',side_effect=send):self.assertEqual(dispatch_due(now=self.now)['superseded'],1)
        self.assertEqual(OutboxIntent.objects.get().state,'CANCELLED')
    def test_late_receipt_not_counted_as_24h_success(self):
        self.reminder(starts_at=self.now+timedelta(hours=23))
        with patch('notification_adapter.services.dispatch._reminder_current',return_value=True),patch('notification_adapter.services.dispatch.send_notification_intent',return_value={}):dispatch_due(now=self.now)
        self.assertFalse(OutboxIntent.objects.get().timing_met)
    def test_on_time_receipt_sets_timing_true_with_controlled_clock(self):
        self.reminder(starts_at=self.now+timedelta(hours=24))
        with patch('notification_adapter.services.dispatch._reminder_current',return_value=True),patch('notification_adapter.services.dispatch.send_notification_intent',return_value={}),patch('notification_adapter.services.dispatch.timezone.now',return_value=self.now):
            dispatch_due(now=self.now)
        self.assertTrue(OutboxIntent.objects.get().timing_met)
    def test_dispatch_inside_outer_transaction_rejected(self):
        with transaction.atomic():
            with self.assertRaises(RuntimeError):dispatch_due(now=self.now)

    def test_slow_batch_claims_each_lease_from_current_time(self):
        self.enqueue()
        self.kw.update(event_id=uuid.uuid4(), record_id=uuid.uuid4(), due_at=self.now+timedelta(microseconds=1))
        self.enqueue()
        start=self.now+timedelta(seconds=1); clock=[start]; leases=[]
        def send(*, event):
            row=OutboxIntent.objects.get(event_id=event['event_id'])
            leases.append((row.lease_until, clock[0]))
            if len(leases)==1: clock[0]+=timedelta(seconds=31)
            return {}
        with patch('notification_adapter.services.dispatch.timezone.now',side_effect=lambda:clock[0]), patch('notification_adapter.services.dispatch.send_notification_intent',side_effect=send):
            result=dispatch_due(now=start)
        self.assertEqual(result['delivered'],2)
        self.assertEqual(len(leases),2)
        self.assertEqual(leases[1][0],leases[1][1]+timedelta(seconds=30))

    def test_retry_delay_starts_after_transport_finishes(self):
        self.enqueue(); clock=[self.now]
        def send(*, event):
            clock[0]+=timedelta(seconds=90)
            raise NotificationTransportUnavailable()
        with patch('notification_adapter.services.dispatch.timezone.now',side_effect=lambda:clock[0]), patch('notification_adapter.services.dispatch.send_notification_intent',side_effect=send):
            result=dispatch_due(now=self.now)
        self.assertEqual(result['retry'],1)
        self.assertEqual(OutboxIntent.objects.get().next_attempt_at,clock[0]+timedelta(seconds=60))

    def test_multi_channel_attempts_record_channel_and_acknowledgement_identity(self):
        self.kw['channels']=['IN_APP','EMAIL_MOCK'];self.enqueue()
        with patch('notification_adapter.services.dispatch.send_notification_intent',return_value={}):
            self.assertEqual(dispatch_due(now=self.now)['delivered'],1)
        rows=list(DeliveryAttempt.objects.order_by('channel'))
        self.assertEqual(len(rows),2)
        self.assertEqual({r.channel for r in rows},{'IN_APP','EMAIL_MOCK'})
        for row in rows:
            self.assertEqual(row.outcome,'DELIVERED')
            self.assertEqual(row.receipt_key,f'{self.kw["event_id"]}:{row.channel}')

    def test_multi_channel_failure_does_not_claim_receipts(self):
        self.kw['channels']=['IN_APP','EMAIL_MOCK'];self.enqueue()
        with patch('notification_adapter.services.dispatch.send_notification_intent',side_effect=NotificationTransportUnavailable()):
            self.assertEqual(dispatch_due(now=self.now)['retry'],1)
        rows=list(DeliveryAttempt.objects.all());self.assertEqual(len(rows),2)
        for row in rows:
            self.assertEqual(row.outcome,'FAILED');self.assertIsNone(row.receipt_key)
