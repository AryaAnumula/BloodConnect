"""Independent Python expectations and SQLite reconciliation; never an application provider."""
import json
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from .generate import LOCAL, stamp


def expected_results(data):
    tables = data['tables']
    now = datetime.fromisoformat(data['metadata']['as_of'])
    day = now.astimezone(LOCAL).date()
    counts = Counter((u['blood_group'], u['component_type']) for u in tables['blood_units']
                     if u['status'] == 'AVAILABLE' and u['expiry_date'] > day.isoformat())
    stock = [dict(blood_group=g, component_type=c, available_quantity=n) for (g, c), n in sorted(counts.items())]
    dashboard = dict(as_of=stamp(now), stock=stock,
                     pending_requests=sum(r['status'] == 'SUBMITTED' for r in tables['blood_requests']),
                     upcoming_camps=sum(c['status'] == 'ACTIVE' and datetime.fromisoformat(c['starts_at']) >= now for c in tables['camps']))
    reports = []
    ranges = [('today', day, day), ('yesterday', day-timedelta(days=1), day-timedelta(days=1)),
              ('last_30_days', day-timedelta(days=29), day), ('full_history', day-timedelta(days=500), day),
              ('empty_range', day-timedelta(days=1000), day-timedelta(days=999))]
    for name, begin, end in ranges:
        start_time = datetime.combine(begin, datetime.min.time(), LOCAL).astimezone(timezone.utc)
        end_time = datetime.combine(end+timedelta(days=1), datetime.min.time(), LOCAL).astimezone(timezone.utc)
        reports.append(dict(name=name, **{'from': begin.isoformat(), 'to': end.isoformat()}, timezone='Asia/Kolkata',
                            donation_event_count=sum(begin.isoformat() <= e['collection_date'] <= end.isoformat() for e in tables['collection_events'] if e['status'] == 'CONFIRMED'),
                            collected_unit_count=sum(begin.isoformat() <= u['collection_date'] <= end.isoformat() for u in tables['blood_units']),
                            issued_unit_count=sum(i['quantity'] for i in tables['issue_records'] if start_time <= datetime.fromisoformat(i['issued_at']) < end_time),
                            wasted_unit_count=sum(1 for d in tables['inventory_dispositions'] if d['to_status'] == 'DISCARDED' and start_time <= datetime.fromisoformat(d['occurred_at']) < end_time),
                            definitions_version='college-demo-events-v1'))
    return dict(row_counts={name: len(rows) for name, rows in tables.items()}, dashboard=dashboard, reports=reports,
                expired_available_unit_codes=sorted(u['unit_code'] for u in tables['blood_units'] if u['status'] == 'AVAILABLE' and u['expiry_date'] <= day.isoformat()),
                low_stock_alert_count=sum(a['alert_type'] == 'LOW_STOCK' for a in tables['stock_alerts']),
                near_expiry_alert_count=sum(a['alert_type'] == 'NEAR_EXPIRY' for a in tables['stock_alerts']))


def reference_database(data, path=':memory:'):
    """New standalone reference schema; refuses existing on-disk database files."""
    from pathlib import Path
    if str(path) != ':memory:' and Path(path).exists():
        raise ValueError('Reference database already exists; choose a new output path.')
    connection = sqlite3.connect(str(path))
    try:
        for name, rows in data['tables'].items():
            # Names come only from the fixed generator table definitions, checked below.
            if not name.replace('_', '').isalpha() or not rows:
                raise ValueError('Invalid reference table.')
            keys = list(rows[0])
            if any(not key.replace('_', '').isalpha() for key in keys):
                raise ValueError('Invalid reference column.')
            columns = ','.join('"'+key+'"' for key in keys)
            connection.execute(f'CREATE TABLE "{name}" ({columns}, PRIMARY KEY(id))')
            values = [tuple(json.dumps(row[key], sort_keys=True) if isinstance(row[key], (list, dict)) else row[key] for key in keys) for row in rows]
            connection.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in keys)})', values)
        connection.commit()
        return connection
    except BaseException:
        connection.close()
        raise


def reconcile_sql(data, expected):
    db = reference_database(data)
    try:
        day = datetime.fromisoformat(data['metadata']['as_of']).astimezone(LOCAL).date().isoformat()
        rows = db.execute("SELECT blood_group,component_type,SUM(quantity) FROM blood_units WHERE status='AVAILABLE' AND expiry_date>? GROUP BY blood_group,component_type ORDER BY blood_group,component_type", (day,)).fetchall()
        stock = [dict(blood_group=g, component_type=c, available_quantity=q) for g, c, q in rows]
        if stock != expected['dashboard']['stock']:
            raise ValueError('SQL stock reconciliation failed.')
        pending = db.execute("SELECT COUNT(*) FROM blood_requests WHERE status='SUBMITTED'").fetchone()[0]
        upcoming = db.execute("SELECT COUNT(*) FROM camps WHERE status='ACTIVE' AND starts_at>=?", (data['metadata']['as_of'],)).fetchone()[0]
        if (pending, upcoming) != (expected['dashboard']['pending_requests'], expected['dashboard']['upcoming_camps']):
            raise ValueError('SQL dashboard reconciliation failed.')
        for report in expected['reports']:
            begin, end = report['from'], report['to']
            start_time = stamp(datetime.combine(date.fromisoformat(begin), datetime.min.time(), LOCAL))
            end_time = stamp(datetime.combine(date.fromisoformat(end)+timedelta(days=1), datetime.min.time(), LOCAL))
            sql_values = (
                db.execute("SELECT COUNT(*) FROM collection_events WHERE status='CONFIRMED' AND collection_date>=? AND collection_date<=?", (begin, end)).fetchone()[0],
                db.execute('SELECT COUNT(*) FROM blood_units WHERE collection_date>=? AND collection_date<=?', (begin, end)).fetchone()[0],
                db.execute('SELECT COALESCE(SUM(quantity),0) FROM issue_records WHERE issued_at>=? AND issued_at<?', (start_time, end_time)).fetchone()[0],
                db.execute("SELECT COUNT(*) FROM inventory_dispositions WHERE to_status='DISCARDED' AND occurred_at>=? AND occurred_at<?", (start_time, end_time)).fetchone()[0])
            if sql_values != tuple(report[key] for key in ('donation_event_count', 'collected_unit_count', 'issued_unit_count', 'wasted_unit_count')):
                raise ValueError('SQL report reconciliation failed: '+report['name'])
        return {'stock_and_dashboard': 'PASS', 'report_ranges': len(expected['reports'])}
    finally:
        db.close()
