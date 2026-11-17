"""Explicit BB22 acceptance: actual camp cancellation -> durable mock receipts.

Run: python backend/manage.py test notification_adapter.acceptance.camp_cancellation
Missing cancellation route or Node FAILS readiness; this module is not auto-discovered.
"""
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import subprocess
import tempfile
import threading
import uuid
from datetime import timedelta

from django.conf import settings
from django.test import TransactionTestCase, override_settings
from django.urls import Resolver404, resolve
from django.utils import timezone

from notification_adapter.models import OutboxIntent
from notification_adapter.services.dispatch import dispatch_due
from scheduling.models import Appointment
from scheduling.services.appointments import book_appointment
from scheduling.tests.helpers import make_camp, make_donor, make_slot, make_user
from scheduling.tests.test_camp_api import client_for


class RealCampCancellationAcceptance(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        try:
            resolve('/api/v1/camps/' + str(uuid.uuid4()) + '/cancel')
        except Resolver404 as error:
            raise RuntimeError(
                'BB22 acceptance NOT READY: Ankitha must deliver the actual BB20 '
                'camp cancellation API/service into this composed source first.'
            ) from error
        if not shutil.which('node'):
            raise RuntimeError('BB22 acceptance requires Node24 and actual mock receipts; no skip.')
        super().setUpClass()

    def test_camp_cancel_invalidates_all_pending_states_and_delivers_once(self):
        now = timezone.now()
        camp = make_camp(starts_at=now + timedelta(hours=27),
                         ends_at=now + timedelta(hours=30), capacity=3)
        slot = make_slot(camp=camp, starts_at=camp.starts_at,
                         ends_at=camp.ends_at, capacity=3)
        people = [make_donor() for _ in range(3)]
        bookings = [book_appointment(actor=user, slot_id=slot.pk)
                    for user, profile in people]
        ids = [row['id'] for row in bookings]
        # Controlled queue-state fixtures represent real persisted PENDING/BLOCKED/LEASED
        # reminders. Every booking and every intent itself came from the real service.
        for booking, state in zip(bookings, ('PENDING', 'BLOCKED', 'LEASED')):
            OutboxIntent.objects.filter(record_id=booking['id']).update(
                state=state, lease_token=uuid.uuid4() if state == 'LEASED' else None,
                lease_until=now + timedelta(minutes=5) if state == 'LEASED' else None,
            )
        client, token = client_for(make_user('STAFF'))
        route = f'/api/v1/camps/{camp.pk}/cancel'
        result = client.post(route, data=json.dumps({'reason': 'Synthetic acceptance cancellation'}),
                             content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(result.status_code, 200, result.content)
        camp.refresh_from_db()
        self.assertEqual(camp.status, 'CANCELLED')
        self.assertIsNotNone(camp.cancelled_at)
        appointments = list(Appointment.objects.filter(pk__in=ids).order_by('id').values())
        self.assertEqual(len(appointments), 3)
        self.assertTrue(all(row['status'] == 'CANCELLED' and row['cancelled_at'] is not None
                            for row in appointments))
        reminders = OutboxIntent.objects.filter(record_id__in=ids, event_type='APPOINTMENT_REMINDER')
        self.assertEqual(reminders.count(), 3)
        self.assertEqual(set(reminders.values_list('state', flat=True)), {'CANCELLED'})
        self.assertTrue(all(r.lease_token is None and r.lease_until is None for r in reminders))
        cancellations = OutboxIntent.objects.filter(record_id__in=ids, event_type='APPOINTMENT_CANCELLED')
        self.assertEqual(cancellations.count(), 3)
        expected_recipients = {str(b['id']): user.pk for b, (user, profile) in zip(bookings, people)}
        for row in cancellations:
            self.assertEqual(row.recipient_id, expected_recipients[str(row.record_id)])
            self.assertEqual(row.due_at, camp.cancelled_at)
        intent_count = OutboxIntent.objects.count()
        cancelled_at = camp.cancelled_at
        replay = client.post(route, data=json.dumps({'reason': 'Synthetic acceptance cancellation'}),
                             content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(replay.status_code, 200, replay.content)
        camp.refresh_from_db()
        self.assertEqual(camp.cancelled_at, cancelled_at)
        self.assertEqual(OutboxIntent.objects.count(), intent_count)
        self.assertEqual(list(Appointment.objects.filter(pk__in=ids).order_by('id').values()), appointments)

        key = secrets.token_urlsafe(40)
        script = (
            "import {createNotificationServer} from './notification-service/src/server.mjs';"
            "const server=createNotificationServer({token:process.env.BB22_ACCEPTANCE_TOKEN,"
            "mockEnabled:true,receiptDir:process.env.BB22_ACCEPTANCE_RECEIPTS});"
            "server.listen(0,'127.0.0.1',()=>console.log(server.address().port));"
        )
        with tempfile.TemporaryDirectory(prefix='bb22-cancellation-receipts-') as directory:
            process = subprocess.Popen(
                ['node', '--input-type=module', '-e', script], cwd=settings.BASE_DIR,
                env={**os.environ, 'BB22_ACCEPTANCE_TOKEN': key,
                     'BB22_ACCEPTANCE_RECEIPTS': directory},
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            try:
                output = queue.Queue()
                threading.Thread(target=lambda: output.put(process.stdout.readline()), daemon=True).start()
                port = output.get(timeout=15).strip()
                self.assertTrue(port.isdigit())
                with override_settings(NOTIFICATION_BASE_URL='http://127.0.0.1:' + port,
                                       NOTIFICATION_INTERNAL_TOKEN=key):
                    sent = dispatch_due(now=timezone.now())
                    again = dispatch_due(now=timezone.now())
                self.assertEqual(sent['delivered'], 3)
                self.assertEqual(again['delivered'], 0)
                self.assertEqual(set(cancellations.values_list('state', flat=True)), {'DELIVERED'})
                files = list(Path(directory).glob('*.json'))
                self.assertEqual(len(files), 3)
                self.assertEqual(
                    {p.stem for p in files},
                    {str(value) for value in cancellations.values_list('event_id', flat=True)},
                )
                for path in files:
                    saved = json.loads(path.read_text(encoding='utf-8'))
                    self.assertEqual(saved['fingerprint_version'], 2)
                    self.assertEqual(saved['receipt']['delivery_mode'], 'mock')
                    self.assertEqual(saved['receipt']['receipts'],
                                     [{'channel': 'IN_APP', 'status': 'DELIVERED'}])
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                process.stdout.close()
