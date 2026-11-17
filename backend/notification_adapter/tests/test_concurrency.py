import json
import tempfile
import threading
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless

from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from notification_adapter.models import OutboxIntent
from notification_adapter.services.intents import enqueue_intent


@skipUnless(connection.vendor == 'postgresql', 'requires PostgreSQL concurrency')
class ConcurrentIntentTests(TransactionTestCase):
    def test_identical_concurrent_enqueues_create_one_intent(self):
        with tempfile.TemporaryDirectory() as folder:
            policy = Path(folder) / 'policy.json'
            policy.write_text(json.dumps({'decisions': [{'id': 'S2-06', 'status': 'APPROVED', 'approved_by': 'test only', 'approved_at': '2026-11-15', 'evidence': 'synthetic fixture'}]}))
            barrier = threading.Barrier(2, timeout=10)
            args = dict(event_id=uuid.uuid4(), recipient_id=uuid.uuid4(), event_type='LOW_STOCK', record_id=uuid.uuid4(), due_at=timezone.now(), channels=['IN_APP'])

            def worker():
                close_old_connections()
                try:
                    barrier.wait()
                    with transaction.atomic():
                        return enqueue_intent(**args)
                finally:
                    close_old_connections()

            with override_settings(NOTIFICATION_DECISIONS_FILE=policy):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda _: worker(), range(2)))
            self.assertEqual(results[0]['id'], results[1]['id'])
            self.assertEqual(OutboxIntent.objects.filter(event_id=args['event_id']).count(), 1)
