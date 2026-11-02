import uuid
from unittest.mock import Mock,patch
from django.test import SimpleTestCase,override_settings
from django.utils import timezone
from notification_adapter.client import send_notification_intent,NotificationTransportUnavailable

@override_settings(NOTIFICATION_BASE_URL='http://127.0.0.1:3000',NOTIFICATION_INTERNAL_TOKEN='synthetic-test-only-token-at-least-32-characters')
class ClientTests(SimpleTestCase):
    def setUp(self):self.event=dict(event_id=str(uuid.uuid4()),recipient_id=str(uuid.uuid4()),type='LOW_STOCK',record_id=str(uuid.uuid4()),due_at=timezone.now().isoformat(),channels=['IN_APP'])
    def test_receipt_validation_and_redirection_disabled(self):
        body=dict(event_id=self.event['event_id'],delivery_mode='mock',receipts=[dict(channel='IN_APP',status='DELIVERED')])
        with patch('notification_adapter.client.requests.post',return_value=Mock(status_code=202,json=lambda:body)) as send:
            self.assertEqual(send_notification_intent(event=self.event),body)
            self.assertFalse(send.call_args.kwargs['allow_redirects']);self.assertEqual(send.call_args.kwargs['timeout'],(2,3))
        for bad in [{}, {**body,'delivery_mode':'real'},{**body,'event_id':str(uuid.uuid4())},{**body,'receipts':[]},{**body,'receipts':[dict(channel='SMS_MOCK',status='DELIVERED')]}]:
            with patch('notification_adapter.client.requests.post',return_value=Mock(status_code=202,json=lambda:bad)):
                with self.assertRaises(NotificationTransportUnavailable):send_notification_intent(event=self.event)
    def test_non_success_never_accepted(self):
        for status in [200,301,400,401,409,501,503]:
            with patch('notification_adapter.client.requests.post',return_value=Mock(status_code=status)):
                with self.assertRaises(NotificationTransportUnavailable):send_notification_intent(event=self.event)
    def test_invalid_configuration_no_network(self):
        for base in ['https://user:pass@example.test','http://example.test','http://localhost:3000/path','http://localhost:3000?token=private']:
            with override_settings(NOTIFICATION_BASE_URL=base),patch('notification_adapter.client.requests.post') as send:
                with self.assertRaises(NotificationTransportUnavailable):send_notification_intent(event=self.event)
                send.assert_not_called()
