import os,shutil,subprocess,tempfile,uuid,json
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase,override_settings
from django.utils import timezone
from notification_adapter.client import send_notification_intent,NotificationTransportUnavailable

class RealNodeTransportTests(SimpleTestCase):
    def test_real_http_receipt_and_durable_replay(self):
        if not shutil.which('node'):self.skipTest('Node unavailable: real transport NOT verified.')
        token='synthetic-test-only-dedicated-internal-token'
        with tempfile.TemporaryDirectory() as directory:
            script="""import {createNotificationServer} from './notification-service/src/server.mjs';const s=createNotificationServer({token:process.env.BB22_TEST_TOKEN,mockEnabled:true,receiptDir:process.env.BB22_TEST_DIR});s.listen(0,'127.0.0.1',()=>console.log(s.address().port));"""
            process=subprocess.Popen(['node','--input-type=module','-e',script],cwd=settings.BASE_DIR,env={**os.environ,'BB22_TEST_TOKEN':token,'BB22_TEST_DIR':directory},stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
            try:
                # Node starts one local test server, never real email/SMS. Process always terminated.
                import threading,queue
                q=queue.Queue();threading.Thread(target=lambda:q.put(process.stdout.readline()),daemon=True).start()
                port=q.get(timeout=15).strip();self.assertTrue(port.isdigit())
                event=dict(event_id=str(uuid.uuid4()),recipient_id=str(uuid.uuid4()),type='LOW_STOCK',record_id=str(uuid.uuid4()),due_at=timezone.now().isoformat(),channels=['IN_APP'])
                with override_settings(NOTIFICATION_BASE_URL='http://127.0.0.1:'+port,NOTIFICATION_INTERNAL_TOKEN=token):
                    receipt=send_notification_intent(event=event)
                    self.assertEqual(receipt['delivery_mode'],'mock');self.assertEqual(send_notification_intent(event=event),receipt)
                    with self.assertRaises(NotificationTransportUnavailable):send_notification_intent(event={**event,'record_id':str(uuid.uuid4())})
                self.assertEqual(len(list(Path(directory).glob('*.json'))),1)
            finally:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
                process.stdout.close()
