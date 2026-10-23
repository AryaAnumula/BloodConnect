#!/usr/bin/env python
"""BB-03: protocol-bound readiness sampling; never certifies story completion."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

UTC = timezone.utc
MAX_SAMPLES = 100_000


def utc_now():
    return datetime.now(UTC)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('An offset-aware ISO timestamp is required.')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Naive timestamps are not accepted.')
    return result.astimezone(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat()


def fingerprint(protocol):
    canonical = json.dumps(protocol, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def validate_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname
            or parsed.path != '/api/v1/health/ready' or parsed.query or parsed.fragment
            or parsed.username is not None or parsed.password is not None):
        raise ValueError('Use an HTTP(S) readiness URL without credentials, query or fragment.')
    parsed.port  # Validate port syntax as well.
    return url


def validate_protocol(raw):
    if not isinstance(raw, dict):
        raise ValueError('Protocol must be a JSON object.')
    start, end = timestamp(raw['start']), timestamp(raw['end'])
    interval, timeout = raw['interval_seconds'], raw['timeout_seconds']
    if (type(interval) is not int or interval < 1
            or type(timeout) not in (int, float) or not 0 < timeout <= interval):
        raise ValueError('Use an integer interval >=1 and 0<timeout<=interval.')
    if end <= start or (end - start).total_seconds() / interval > MAX_SAMPLES:
        raise ValueError('Invalid or excessively large observation window.')
    if not isinstance(raw.get('maintenance', []), list):
        raise ValueError('Maintenance must be an array.')
    maintenance = []
    for item in raw.get('maintenance', []):
        a, b = timestamp(item['start']), timestamp(item['end'])
        if b <= a:
            raise ValueError('Maintenance end must follow start.')
        a, b = max(a, start), min(b, end)
        if b > a:
            maintenance.append((a, b))
    merged = []
    for a, b in sorted(maintenance):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    fingerprint(raw)  # Reject non-finite JSON values.
    return start, end, interval, float(timeout), merged


def approval_record_present(protocol, *, now):
    fields = ['protocol_id', 'environment_name', 'approved_by', 'approval_reference']
    if not all(isinstance(protocol.get(k), str) and protocol[k].strip()
               and len(protocol[k]) <= 240
               and not protocol[k].startswith(('REPLACE_', 'CHANGE_ME')) for k in fields):
        return False
    if not re.fullmatch(r'[0-9a-fA-F]{40}', str(protocol.get('source_revision', ''))):
        return False
    if not protocol.get('approved_at'):
        return False
    approved = timestamp(protocol['approved_at'])
    return approved <= timestamp(protocol['start']) and approved <= now


def eligible_seconds(a, b, maintenance):
    excluded = sum(max(0, (min(b, y) - max(a, x)).total_seconds()) for x, y in maintenance)
    return max(0, (b - a).total_seconds() - excluded)


def summarize(protocol, observations, *, now=None):
    start, end, interval, timeout, maintenance = validate_protocol(protocol)
    now = now or utc_now()
    if now.tzinfo is None:
        raise ValueError('Summary time must have an offset.')
    by_schedule = {}
    for row in observations:
        scheduled, observed = timestamp(row['scheduled_at']), timestamp(row['observed_at'])
        if scheduled in by_schedule:
            raise ValueError('Duplicate scheduled sample; reconcile evidence before reporting.')
        if type(row.get('ready')) is not bool:
            raise ValueError('Observation ready must be a boolean.')
        if not start <= scheduled < end or (scheduled - start).total_seconds() % interval != 0:
            raise ValueError('Observation is outside the approved sample schedule.')
        if not scheduled <= observed <= min(scheduled + timedelta(seconds=timeout), end):
            raise ValueError('Observation timestamp is outside sampling tolerance.')
        if observed > now:
            raise ValueError('Future observations cannot establish availability.')
        if type(row.get('http_status')) is not int or not 0 <= row['http_status'] <= 599:
            raise ValueError('Observation requires a numeric HTTP status, or 0 for transport/format failure.')
        if row['ready'] and row['http_status'] != 200:
            raise ValueError('Ready observation must have HTTP status 200.')
        by_schedule[scheduled] = row
    available = unavailable = unknown = eligible = 0.0
    current = start
    while current < end:
        stop = min(current + timedelta(seconds=interval), end)
        weight = eligible_seconds(current, stop, maintenance)
        eligible += weight
        row = by_schedule.get(current)
        if row is None or stop > now:
            unknown += weight
        elif row['ready']:
            available += weight
        else:
            unavailable += weight
        current = stop
    complete = now >= end and eligible > 0 and unknown == 0
    approval_claimed = approval_record_present(protocol, now=now)
    percentage = None if eligible == 0 else available / eligible * 100
    return {
        'protocol_id': protocol.get('protocol_id'),
        'protocol_sha256': fingerprint(protocol),
        'environment_name': protocol.get('environment_name'),
        'source_revision': protocol.get('source_revision'),
        'measurement': 'sampled readiness estimate, NOT continuous user-journey availability',
        'window_start': iso(start), 'window_end': iso(end),
        'eligible_seconds': eligible, 'sampled_available_seconds': available,
        'sampled_unavailable_seconds': unavailable, 'unknown_seconds': unknown,
        'sampled_availability_percent': percentage,
        'coverage_percent': None if eligible == 0 else (eligible - unknown) / eligible * 100,
        'window_elapsed': now >= end, 'observation_complete': complete,
        'protocol_approval_claimed': approval_claimed,
        'approval_external_verification': 'not performed; reviewer must verify actual approval and deployed revision',
        'sampled_threshold_met': bool(complete and approval_claimed and percentage is not None and percentage >= 99),
        'story_complete': False,
        'acceptance_status': 'requires independent protocol, evidence, deployment and story-criteria review',
        'generated_at': iso(now),
    }


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(url, timeout):
    """Read-only bounded response; do not follow redirects or save response bodies."""
    try:
        with build_opener(NoRedirect()).open(url, timeout=timeout) as response:
            payload = json.loads(response.read(16_384))
            ready = (response.status == 200 and payload.get('status') == 'ready'
                     and payload.get('checks', {}).get('database') == 'ok')
            return bool(ready), response.status
    except HTTPError as exc:
        status = exc.code
        exc.close()
        return False, status
    except (URLError, TimeoutError, OSError, ValueError, AttributeError):
        return False, 0


def read_observations(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@contextmanager
def evidence_lock(output):
    """One writer/reporter at a time. A crashed process's lock requires manual review."""
    lock = output / 'collector.lock'
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError('Evidence directory is locked; check for another collector or a reviewed stale lock.') from None
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def bind_evidence(output, protocol, url):
    expected = {'protocol_sha256': fingerprint(protocol), 'probe_url': url,
                'environment_name': protocol.get('environment_name'), 'source_revision': protocol.get('source_revision')}
    path = output / 'session.json'
    if path.exists():
        actual = json.loads(path.read_text())
        if any(actual.get(k) != v for k, v in expected.items()):
            raise ValueError('Evidence protocol/URL/environment/revision mismatch. Use a separate output directory.')
        return actual
    if (output / 'observations.jsonl').exists() or (output / 'report.json').exists():
        raise ValueError('Unbound evidence exists; do not silently adopt or overwrite it.')
    record = {**expected, 'collector_started_at': iso(utc_now())}
    with path.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return record


def collect(protocol, url, observations_path, observations, max_samples=None):
    start, end, interval, timeout, maintenance = validate_protocol(protocol)
    seen = {timestamp(row['scheduled_at']) for row in observations}
    scheduled, collected = start, 0
    while scheduled < end:
        stop = min(scheduled + timedelta(seconds=interval), end)
        if scheduled in seen or eligible_seconds(scheduled, stop, maintenance) == 0:
            scheduled += timedelta(seconds=interval)
            continue
        now = utc_now()
        if now < scheduled:
            time.sleep((scheduled - now).total_seconds())
        began = utc_now()
        if began > min(scheduled + timedelta(seconds=timeout), end):
            scheduled += timedelta(seconds=interval)
            continue  # Missing past samples stay unknown, never retrospectively invented.
        ready, status = probe(url, timeout)
        row = {'scheduled_at': iso(scheduled), 'observed_at': iso(began), 'ready': ready, 'http_status': status}
        with observations_path.open('a') as stream:
            stream.write(json.dumps(row) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        observations.append(row)
        collected += 1
        scheduled += timedelta(seconds=interval)
        if max_samples and collected >= max_samples:
            break
    if not max_samples:
        time.sleep(max(0, (end - utc_now()).total_seconds()))


def run(args):
    protocol = json.loads(args.protocol.read_text())
    validate_protocol(protocol)
    url = validate_url(args.url)
    if args.max_samples is not None and (args.max_samples < 1 or args.summarize_only or args.dry_run):
        raise ValueError('Use a positive max-samples only for collection, not dry-run or summary.')
    if args.dry_run:
        print(json.dumps({'valid_protocol_shape': True,
                          'approval_claimed': approval_record_present(protocol, now=utc_now()),
                          'observation_complete': False, 'story_complete': False}, indent=2))
        return 0
    if not args.summarize_only and not approval_record_present(protocol, now=utc_now()):
        raise ValueError('Record actual pre-window approval, environment, deployment revision and reference first. Do not fabricate approval.')
    args.output.mkdir(parents=True, exist_ok=True)
    with evidence_lock(args.output):
        if args.summarize_only and not (args.output / 'session.json').exists():
            raise ValueError('No bound evidence session exists to summarize.')
        session = bind_evidence(args.output, protocol, url)
        if args.max_samples:
            session['tooling_or_interrupted_history'] = True
            temp_session = args.output / 'session.json.tmp'
            temp_session.write_text(json.dumps(session, indent=2) + '\n')
            temp_session.replace(args.output / 'session.json')
        path = args.output / 'observations.jsonl'
        observations = read_observations(path)
        summarize(protocol, observations)  # Validate existing evidence before resume.
        interrupted = False
        if not args.summarize_only:
            try:
                collect(protocol, url, path, observations, args.max_samples)
            except KeyboardInterrupt:
                interrupted = True
        if interrupted:
            session['tooling_or_interrupted_history'] = True
            temp_session = args.output / 'session.json.tmp'
            temp_session.write_text(json.dumps(session, indent=2) + '\n')
            temp_session.replace(args.output / 'session.json')
        report = summarize(protocol, observations)
        report.update(probe_url=url, collector_started_at=session['collector_started_at'],
                      limited_run=bool(args.max_samples), interrupted=interrupted,
                      tooling_or_interrupted_history=bool(session.get('tooling_or_interrupted_history')))
        if report['tooling_or_interrupted_history']:
            report['sampled_threshold_met'] = False
        temp = args.output / 'report.json.tmp'
        temp.write_text(json.dumps(report, indent=2) + '\n')
        temp.replace(args.output / 'report.json')
        print(json.dumps(report, indent=2))
        return 130 if interrupted else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--url', default='http://localhost:8000/api/v1/health/ready')
    parser.add_argument('--output', type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--summarize-only', action='store_true')
    modes.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max-samples', type=int, help='Tooling smoke limit; cannot certify a full observation window.')
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        # No remote response bodies or local environment values are included.
        print(f'Availability collection stopped: {type(exc).__name__}. Check protocol, evidence and local file permissions; evidence was not certified.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
