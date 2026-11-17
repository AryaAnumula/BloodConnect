"""Explicit read-only synthetic source; never a silent fallback for missing domain code."""
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from django.conf import settings

from reporting.exceptions import ReportingUnavailable


def source_mode():
    mode = getattr(settings, 'BLOODCONNECT_REPORT_SOURCE', 'domain')
    if mode not in ('domain', 'synthetic') or (mode == 'synthetic' and not settings.DEBUG):
        raise ReportingUnavailable()
    return mode


def response_headers():
    return {'X-BloodConnect-Data-Source': source_mode(), 'Cache-Control': 'no-store'}


def check(condition):
    if not condition:
        raise ReportingUnavailable()


def timestamp(value):
    try:
        check(isinstance(value, str))
        result = datetime.fromisoformat(value)
        check(result.tzinfo is not None and result.utcoffset() is not None)
        return result
    except (ValueError, TypeError):
        raise ReportingUnavailable() from None


def calendar_date(value):
    try:
        check(isinstance(value, str) and len(value) == 10)
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ReportingUnavailable() from None


def whole(value, minimum=0):
    check(type(value) is int and value >= minimum)
    return value


def rows(data, table):
    try:
        values = data['tables'][table]
        check(isinstance(values, list))
        seen = set()
        for row in values:
            check(isinstance(row, dict) and isinstance(row['id'], str))
            UUID(row['id'])
            check(row['id'] not in seen)
            seen.add(row['id'])
        return values
    except (KeyError, ValueError, TypeError):
        raise ReportingUnavailable() from None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate key.')
        result[key] = value
    return result


def read_snapshot():
    check(source_mode() == 'synthetic')
    try:
        location = getattr(settings, 'BLOODCONNECT_DEMO_DATASET_PATH', '')
        check(bool(location))
        path = Path(location)
        with path.open('rb') as handle:
            payload = handle.read(16 * 1024 * 1024 + 1)
        check(len(payload) <= 16 * 1024 * 1024)
        with (path.parent/'manifest.json').open('rb') as handle:
            manifest_bytes = handle.read(65537)
        check(len(manifest_bytes) <= 65536)
        manifest = json.loads(manifest_bytes, object_pairs_hook=unique_object)
        check(manifest['algorithm'] == 'sha256')
        check(manifest['files'][path.name] == hashlib.sha256(payload).hexdigest())
        data = json.loads(payload, object_pairs_hook=unique_object)
        metadata = data['metadata']
        check(metadata['demo_only'] is True and metadata['dataset_version'] == 'bloodconnect-synthetic-v1')
        check(metadata['timezone'] == 'Asia/Kolkata' and isinstance(data['tables'], dict))
        timestamp(metadata['as_of'])
        return data
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        raise ReportingUnavailable() from None
