"""Authenticated file-to-API check in a disposable local database; no browser claim."""
import argparse
import io
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile


def verify(cases, *, page, invalid_paths, story):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, type=Path)
    args = parser.parse_args()
    path = args.dataset.resolve()
    expected = json.loads((path.parent/'expected.json').read_text(encoding='utf-8'))
    root = Path(__file__).resolve().parents[1]
    local = (root/'artifacts/local').resolve()
    local.mkdir(parents=True, exist_ok=True)
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings', DJANGO_SECRET_KEY=secrets.token_urlsafe(60),
                      DJANGO_DEBUG='1', DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,testserver',
                      DB_ENGINE='sqlite', ALLOW_SQLITE_SMOKE='1', BLOODCONNECT_REPORT_SOURCE='synthetic',
                      BLOODCONNECT_DEMO_DATASET_PATH=str(path))
    sys.path.insert(0, str(root/'backend'))
    with tempfile.TemporaryDirectory(prefix='dataset-api-', dir=local) as directory:
        if not Path(directory).resolve().is_relative_to(local):
            raise RuntimeError('Unexpected verification directory.')
        from django.conf import settings
        settings.DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(Path(directory)/'verification.sqlite3')}
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        from django.core.management import call_command
        from django.db import connections
        from django.test import Client
        try:
            call_command('migrate', interactive=False, verbosity=0, stdout=io.StringIO())
            password = secrets.token_urlsafe(32)
            admin = get_user_model().objects.create_user(email='dataset-verifier@demo.example.test', password=password, role='ADMIN')
            client = Client(enforce_csrf_checks=True)
            csrf = client.get('/api/v1/auth/csrf').json()['csrf_token']
            login = client.post('/api/v1/auth/login', data=json.dumps({'email': admin.email, 'password': password}),
                                content_type='application/json', HTTP_X_CSRFTOKEN=csrf)
            if login.status_code != 200:
                raise AssertionError('Actual session login failed.')
            checked = []
            for route, wanted in cases(expected):
                response = client.get(route)
                if response.status_code != 200 or response.json() != wanted or response['X-BloodConnect-Data-Source'] != 'synthetic':
                    raise AssertionError('Dataset API reconciliation failed: '+route)
                checked.append(route)
            for route in invalid_paths:
                if client.get(route).status_code != 400:
                    raise AssertionError('Query validation failed.')
            shell = client.get(page)
            if shell.status_code != 200 or b'Read-only synthetic snapshot' not in shell.content:
                raise AssertionError('Page source label missing.')
            other = get_user_model().objects.create_user(email='dataset-denied@demo.example.test', role='STAFF')
            client.force_login(other)
            if client.get(checked[0]).status_code != 403 or Client().get(checked[0]).status_code != 403:
                raise AssertionError('Role/session guard failed.')
            print(json.dumps(dict(story=story, source='canonical PR62 synthetic dataset', source_rows=expected['row_counts'],
                                  reconciled_api_cases=len(checked), session_csrf='PASS', access='PASS',
                                  query_validation='PASS', page_label='PASS', database='disposable SQLite; PostgreSQL suite separate')))
        finally:
            connections.close_all()
