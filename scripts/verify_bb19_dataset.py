"""Dataset -> actual BB17 submit/BB18 review/BB19 tracking, without fabricated BB16 issues."""
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    args = parser.parse_args()
    source_path = args.dataset.resolve()
    payload = source_path.read_bytes()
    manifest = json.loads((source_path.parent/'manifest.json').read_text(encoding='utf-8'))
    if manifest['files'][source_path.name] != hashlib.sha256(payload).hexdigest():
        raise SystemExit('Dataset manifest mismatch.')
    data = json.loads(payload)
    if data['metadata']['demo_only'] is not True:
        raise SystemExit('Use the explicitly synthetic dataset.')
    source = [r for r in data['tables']['blood_requests'] if r['fulfilled_quantity'] == 0 and r['status'] in ('SUBMITTED', 'APPROVED', 'REJECTED')]
    if not source:
        raise SystemExit('No supported request source records.')
    needed = {r['requester_id'] for r in source} | {r['reviewed_by_id'] for r in source if r['reviewed_by_id']}
    root = Path(__file__).resolve().parents[1]
    local = (root/'artifacts/local').resolve()
    local.mkdir(parents=True, exist_ok=True)
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings', DJANGO_SECRET_KEY=secrets.token_urlsafe(60),
                      DJANGO_DEBUG='1', DB_ENGINE='sqlite', ALLOW_SQLITE_SMOKE='1',
                      DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,testserver')
    sys.path.insert(0, str(root/'backend'))
    with tempfile.TemporaryDirectory(prefix='bb19-dataset-', dir=local) as directory:
        if not Path(directory).resolve().is_relative_to(local):
            raise RuntimeError('Unexpected verification directory.')
        from django.conf import settings
        settings.DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(Path(directory)/'demo.sqlite3')}
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        from django.core.management import call_command
        from django.db import connections
        from django.test import Client
        try:
            call_command('migrate', interactive=False, verbosity=0, stdout=io.StringIO())
            sessions = {}
            password = secrets.token_urlsafe(32)
            for account in data['tables']['accounts']:
                if account['id'] not in needed:
                    continue
                if account['role'] not in ('REQUESTER', 'STAFF') or not account['is_active'] or account['is_superuser'] or account['is_staff'] or not account['email'].endswith('@demo.example.test'):
                    raise AssertionError('Invalid source actor.')
                user = get_user_model().objects.create_user(id=account['id'], email=account['email'], role=account['role'], password=password)
                client = Client(enforce_csrf_checks=True)
                csrf = client.get('/api/v1/auth/csrf').json()['csrf_token']
                response = client.post('/api/v1/auth/login', data=json.dumps({'email': user.email, 'password': password}), content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
                if response.status_code != 200:
                    raise AssertionError('Actual source-actor session login failed.')
                csrf = client.get('/api/v1/auth/csrf').json()['csrf_token']
                sessions[account['id']] = client, csrf
            created = {}
            for row in source:
                client, csrf = sessions[row['requester_id']]
                body = {k: row[k] for k in ('blood_group', 'component_type', 'quantity', 'urgency_level')}
                response = client.post('/api/v1/requests', data=json.dumps(body), content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
                if response.status_code != 201 or response.json()['requester_id'] != row['requester_id']:
                    raise AssertionError('Actual source submission failed.')
                created[row['id']] = response.json()['id']
                if row['status'] != 'SUBMITTED':
                    reviewer, token = sessions[row['reviewed_by_id']]
                    decision = {'status': row['status']}
                    if row['status'] == 'REJECTED':
                        decision['rejection_reason'] = row['rejection_reason']
                    response = reviewer.patch(f"/api/v1/requests/{created[row['id']]}/status", data=json.dumps(decision), content_type='application/json', HTTP_X_CSRFTOKEN=token)
                    if response.status_code != 200:
                        raise AssertionError('Actual source review failed.')
            for requester in {r['requester_id'] for r in source}:
                client, _ = sessions[requester]
                result = client.get('/api/v1/requests').json()
                wanted = {created[r['id']]: r for r in source if r['requester_id'] == requester}
                if result['count'] != len(wanted) or {r['id'] for r in result['results']} != set(wanted):
                    raise AssertionError('Owner list/count mismatch.')
                for actual in result['results']:
                    row = wanted[actual['id']]
                    for field in ('status', 'quantity', 'fulfilled_quantity', 'rejection_reason'):
                        if actual[field] != row[field]:
                            raise AssertionError('Tracking does not reflect source lifecycle.')
                    detail = client.get('/api/v1/requests/'+actual['id'])
                    if detail.status_code != 200 or detail.json() != actual:
                        raise AssertionError('Owner detail differs from list.')
            sample = next(r for r in source if r['status'] == 'SUBMITTED')
            owner, token = sessions[sample['requester_id']]
            route = '/api/v1/requests/'+created[sample['id']]
            other_id = next(r['requester_id'] for r in source if r['requester_id'] != sample['requester_id'])
            other, _ = sessions[other_id]
            if other.get(route).status_code != 404 or other.get('/api/v1/requests/'+str(uuid.uuid4())).status_code != 404:
                raise AssertionError('Foreign/missing ownership boundary differs.')
            staff_source = next(a for a in data['tables']['accounts'] if a['id'] in sessions and a['role'] == 'STAFF')
            staff, staff_token = sessions[staff_source['id']]
            reviewed = staff.patch(route+'/status', data=json.dumps({'status': 'APPROVED'}), content_type='application/json', HTTP_X_CSRFTOKEN=staff_token)
            if reviewed.status_code != 200 or owner.get(route).json()['status'] != 'APPROVED':
                raise AssertionError('Real review change did not refresh.')
            if owner.post(route+'/close', data=b'', content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code != 422:
                raise AssertionError('Unissued request was permitted to close.')
            if owner.post(route+'/close', data=b'', content_type='application/json').status_code != 403:
                raise AssertionError('Close CSRF guard failed.')
            if Client().get(route).status_code != 403 or owner.get(route+'?extra=1').status_code != 400:
                raise AssertionError('Session/query guard failed.')
            print(json.dumps(dict(story='BB-19', actual_submissions=len(source), source_reviews=sum(r['status'] != 'SUBMITTED' for r in source), additional_refresh_review=1,
                                  requester_sessions=len({r['requester_id'] for r in source}),
                                  source_states_verified=dict(Counter(r['status'] for r in source)),
                                  owner_list_detail='PASS', live_review_refresh='PASS', ownership_csrf_close_guard='PASS',
                                  deferred_issue_linked_requests=len(data['tables']['blood_requests'])-len(source),
                                  actual_issue_to_close='PENDING_BB16; no fabricated issue/status writes',
                                  database='disposable SQLite; PostgreSQL regression separate', browser_walkthrough=False)))
        finally:
            connections.close_all()


if __name__ == '__main__':
    main()
