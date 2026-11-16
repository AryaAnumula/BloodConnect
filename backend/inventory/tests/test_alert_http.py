"""Executed private Node acknowledgement, never a generated/mock Python receipt."""
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
from unittest import skipUnless
from urllib.request import urlopen

from django.conf import settings
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from inventory.models import InventoryAlert
from inventory.services.alerts import evaluate_alerts
from inventory.tests.test_intake import InventoryFixture
from notification_adapter.models import DeliveryAttempt, OutboxIntent
from notification_adapter.services.dispatch import dispatch_due


@skipUnless(shutil.which('node'), 'Node is required for actual private mock HTTP receipt evidence')
class InventoryAlertHTTPTests(InventoryFixture, TransactionTestCase):
    def test_alert_to_actual_node_receipt_and_failure_retry(self):
        token = secrets.token_urlsafe(40)
        server = (Path(settings.BASE_DIR) / 'notification-service/src/server.mjs').as_uri()
        with socket.socket() as candidate:
            candidate.bind(('127.0.0.1', 0))
            port = candidate.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        with tempfile.TemporaryDirectory(prefix='inventory-receipts-') as directory:
            code = (f'import {{createNotificationServer}} from {json.dumps(server)};'
                    'createNotificationServer({token:process.env.NOTIFICATION_INTERNAL_TOKEN,'
                    'mockEnabled:true,receiptDir:process.env.NOTIFICATION_MOCK_RECEIPT_DIR})'
                    f'.listen({port},"127.0.0.1");')
            environment = os.environ | {'NOTIFICATION_INTERNAL_TOKEN': token,
                                        'NOTIFICATION_MOCK_RECEIPT_DIR': directory}
            process = subprocess.Popen([shutil.which('node'), '--input-type=module', '-e', code],
                env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            try:
                for _ in range(50):
                    try:
                        with urlopen(base+'/health/live', timeout=.2) as response:
                            self.assertEqual(response.status, 200)
                        break
                    except OSError:
                        if process.poll() is not None:
                            self.fail('Private Node test service failed to start.')
                        time.sleep(.1)
                else:
                    self.fail('Private Node test service did not become ready.')
                with override_settings(INVENTORY_ALERT_RECIPIENT_ID=str(self.staff.pk),
                                       NOTIFICATION_INTERNAL_TOKEN=token):
                    summary = evaluate_alerts(actor=self.staff, now=timezone.now())
                    self.assertEqual(summary['created'], 32)
                    with override_settings(NOTIFICATION_BASE_URL='http://127.0.0.1:1'):
                        failed = dispatch_due(now=timezone.now(), limit=1)
                    self.assertEqual(failed['retry'], 1)
                    self.assertEqual(DeliveryAttempt.objects.filter(outcome='FAILED').count(), 1)
                    # Controlled retry fixture, not a fabricated acknowledgement.
                    OutboxIntent.objects.update(next_attempt_at=timezone.now())
                    with override_settings(NOTIFICATION_BASE_URL=base):
                        delivered = dispatch_due(now=timezone.now(), limit=100)
                    self.assertEqual(delivered['delivered'],32)
                    self.assertEqual(OutboxIntent.objects.filter(state='DELIVERED').count(),32)
                    self.assertEqual(DeliveryAttempt.objects.filter(outcome='DELIVERED',receipt_key__isnull=False).count(),32)
                    self.assertEqual(len(list(Path(directory).glob('*.json'))),32)
                    row = InventoryAlert.objects.select_related('intent').first()
                    receipt = json.loads((Path(directory)/(str(row.intent.event_id)+'.json')).read_text())
                    self.assertEqual(receipt['fingerprint_version'],2)
                    self.assertEqual(receipt['receipt']['delivery_mode'],'mock')
                    self.assertEqual(receipt['receipt']['event_id'],str(row.intent.event_id))
            finally:
                process.terminate()
                process.communicate(timeout=10)
