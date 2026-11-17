"""Actual dataset-driven booking -> bounded worker -> private Node receipt demonstration."""
import argparse
import io
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--node', default=shutil.which('node'))
    args = parser.parse_args()
    if not args.node:
        raise SystemExit('Node is required for actual mock transport verification.')
    root = Path(__file__).resolve().parents[1]
    local = (root/'artifacts/local').resolve()
    local.mkdir(parents=True, exist_ok=True)
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings', DJANGO_SECRET_KEY=secrets.token_urlsafe(60),
                      DJANGO_DEBUG='1', DB_ENGINE='sqlite', ALLOW_SQLITE_SMOKE='1')
    sys.path.insert(0, str(root/'backend'))
    with tempfile.TemporaryDirectory(prefix='bb22-dataset-', dir=local) as directory:
        folder = Path(directory).resolve()
        if not folder.is_relative_to(local):
            raise RuntimeError('Unexpected demo directory.')
        from django.conf import settings
        settings.DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(folder/'demo.sqlite3')}
        import django
        django.setup()
        from django.core.management import call_command
        from django.db import connections
        from django.test import override_settings
        from notification_adapter.models import DeliveryAttempt, OutboxIntent
        token = secrets.token_urlsafe(40)
        receipts = folder/'receipts'
        script = ("import {createNotificationServer} from './notification-service/src/server.mjs';"
                  "const s=createNotificationServer({token:process.env.BB22_VERIFY_TOKEN,mockEnabled:true,receiptDir:process.env.BB22_VERIFY_DIR});"
                  "s.listen(0,'127.0.0.1',()=>console.log(s.address().port));")
        process = None
        try:
            call_command('migrate', interactive=False, verbosity=0, stdout=io.StringIO())
            process = subprocess.Popen([args.node, '--input-type=module', '-e', script], cwd=root,
                                       env={**os.environ, 'BB22_VERIFY_TOKEN': token, 'BB22_VERIFY_DIR': str(receipts)},
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            output = queue.Queue()
            threading.Thread(target=lambda: output.put(process.stdout.readline()), daemon=True).start()
            port = output.get(timeout=15).strip()
            if not port.isdigit():
                raise AssertionError('Local mock failed to start.')
            prepared = io.StringIO()
            call_command('queue_dataset_reminders', dataset=args.dataset.resolve(), stdout=prepared)
            demo = json.loads(prepared.getvalue())
            if OutboxIntent.objects.filter(state='DELIVERED').exists():
                raise AssertionError('Fictional receipt state was imported before transport.')
            with override_settings(NOTIFICATION_BASE_URL='http://127.0.0.1:'+port, NOTIFICATION_INTERNAL_TOKEN=token):
                observed = io.StringIO()
                call_command('dispatch_notifications', watch_seconds=14, interval_seconds=1, limit=100, stdout=observed)
            outcomes = {}
            for booking in demo['bookings']:
                intent = OutboxIntent.objects.get(pk=booking['intent_id'])
                if str(intent.recipient_id) != booking['donor_user_id']:
                    raise AssertionError('Recipient mismatch.')
                outcomes[booking['scenario']] = dict(state=intent.state, late_booking=intent.late_booking, timing_met=intent.timing_met)
            if outcomes['on_time_reminder'] != dict(state='DELIVERED', late_booking=False, timing_met=True):
                raise AssertionError('On-time actual receipt not established.')
            if outcomes['late_reminder'] != dict(state='DELIVERED', late_booking=True, timing_met=False):
                raise AssertionError('Late receipt incorrectly counted as on-time.')
            if outcomes['cancel_before_dispatch']['state'] != 'CANCELLED':
                raise AssertionError('Cancelled reminder was not invalidated.')
            persisted = list(receipts.glob('*.json'))
            if len(persisted) != 2 or DeliveryAttempt.objects.filter(outcome='DELIVERED').count() != 2:
                raise AssertionError('Actual receipt/attempt count mismatch.')
            for file in persisted:
                record = json.loads(file.read_text(encoding='utf-8'))
                if record['fingerprint_version'] != 2 or token in file.read_text(encoding='utf-8'):
                    raise AssertionError('Receipt persistence contract failed.')
            print(json.dumps(dict(story='BB-22', bookings='new actual services using PR62 actors', outcomes=outcomes,
                                  actual_private_node_receipts=2, actual_delivered_attempts=2,
                                  imported_fixture_receipts=0, network_under_business_lock=False,
                                  database='disposable SQLite; PostgreSQL suite separate', browser_walkthrough=False)))
        finally:
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                if process.stdout:
                    process.stdout.close()
            connections.close_all()


if __name__ == '__main__':
    main()
