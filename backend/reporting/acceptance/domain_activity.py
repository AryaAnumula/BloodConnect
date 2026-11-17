"""Explicit BB24 actual collection/unit/issue/discard reconciliation, not synthetic fallback.

python backend/manage.py test reporting.acceptance.domain_activity --noinput
Source-unit setup is a controlled fixture; actual issue/disposition services create history.
"""
from datetime import datetime, time, timedelta, timezone as utc
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from blood_requests.tests.helpers import make_request, signed_in
from reporting.acceptance.fixtures import require_models, source_unit, user


@override_settings(BLOODCONNECT_REPORT_SOURCE='domain')
class RealDomainActivityAcceptance(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.Event, cls.Unit, cls.Disposition, cls.Issue = require_models(
            'inventory.CollectionEvent', 'inventory.BloodUnit',
            'inventory.InventoryDisposition', 'blood_requests.IssueRecord',
        )
        from blood_requests.services.issue import issue_request
        from inventory.services.dispositions import record_disposition
        from inventory.selectors.reporting import collection_wastage_totals
        if not all(map(callable, (issue_request, record_disposition, collection_wastage_totals))):
            raise RuntimeError('Actual source write/read services required.')
        super().setUpClass()

    def setUp(self):
        self.admin, self.staff, self.owner = user(), user('STAFF'), user('REQUESTER')
        self.client, _ = signed_in(self.admin)

    def route(self, day, until=None):
        return f'/api/v1/reports?from={day.isoformat()}&to={(until or day).isoformat()}'

    def assert_counts(self, response, expected):
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response['X-BloodConnect-Data-Source'], 'domain')
        self.assertEqual(response['Cache-Control'], 'no-store')
        data = response.json()
        self.assertEqual({k: data[k] for k in expected}, expected)
        self.assertEqual(data['timezone'], 'Asia/Kolkata')
        self.assertEqual(data['definitions_version'], 'college-demo-events-v1')
        self.assertEqual(set(data), {'from', 'to', 'timezone', 'definitions_version',
                                    'donation_event_count', 'collected_unit_count',
                                    'issued_unit_count', 'wasted_unit_count'})
        return data

    def test_actual_date_boundaries_count_events_units_issues_and_explicit_discards(self):
        day = timezone.localdate()-timedelta(days=2)
        units = [source_unit(actor=self.staff, collected=day+timedelta(days=offset))
                 for offset in (-1, 0, 1)]
        middle_event = units[1].collection_event
        plasma = source_unit(actor=self.staff, component='PLASMA', event=middle_event)
        platelets = source_unit(actor=self.staff, component='PLATELETS', event=middle_event)
        # An expired AVAILABLE unit is not wastage and stays outside this collection day.
        expired = source_unit(actor=self.staff, collected=day-timedelta(days=50))
        self.assertLess(expired.expiry_date, day)
        request = make_request(self.owner, status='APPROVED', quantity=3, blood_group='A+', component_type='RBC')
        from blood_requests.services.issue import issue_request
        issue_request(actor=self.staff, request_id=request.pk, unit_ids=[str(u.pk) for u in units])
        start = datetime.combine(day, time.min, ZoneInfo('Asia/Kolkata')).astimezone(utc.utc)
        end = start+timedelta(days=1)
        # Controlled timestamp fixtures probe exact boundaries on REAL service-created history.
        for unit, instant in zip(units, (start, end-timedelta(microseconds=1), end)):
            self.Issue.objects.filter(unit=unit).update(issued_at=instant)
        from inventory.services.dispositions import record_disposition
        record_disposition(actor=self.staff, unit_id=plasma.pk,
                           data={'status': 'DISCARDED', 'reason': 'Synthetic acceptance discard'})
        self.Disposition.objects.filter(unit=plasma).update(occurred_at=start+timedelta(hours=1))
        record_disposition(actor=self.staff, unit_id=platelets.pk,
                           data={'status': 'QUARANTINED', 'reason': 'Synthetic acceptance quarantine'})
        self.Disposition.objects.filter(unit=platelets).update(occurred_at=start+timedelta(hours=2))
        self.assert_counts(self.client.get(self.route(day)), dict(
            donation_event_count=1, collected_unit_count=3, issued_unit_count=2, wasted_unit_count=1))
        self.assert_counts(self.client.get(self.route(day+timedelta(days=1))), dict(
            donation_event_count=1, collected_unit_count=1, issued_unit_count=1, wasted_unit_count=0))
        expired.refresh_from_db()
        self.assertEqual(expired.status, 'AVAILABLE')

    def test_http_refresh_reads_actual_issue_and_disposition_writes(self):
        day = timezone.localdate()
        unit = source_unit(actor=self.staff)
        extra = source_unit(actor=self.staff, component='PLASMA', event=unit.collection_event)
        self.assert_counts(self.client.get(self.route(day)), dict(
            donation_event_count=1, collected_unit_count=2, issued_unit_count=0, wasted_unit_count=0))
        request = make_request(self.owner, status='APPROVED', quantity=1, blood_group='A+', component_type='RBC')
        from blood_requests.services.issue import issue_request
        issue_request(actor=self.staff, request_id=request.pk, unit_ids=[str(unit.pk)])
        from inventory.services.dispositions import record_disposition
        record_disposition(actor=self.staff, unit_id=extra.pk,
                           data={'status': 'DISCARDED', 'reason': 'Synthetic refresh disposition'})
        self.assert_counts(self.client.get(self.route(day)), dict(
            donation_event_count=1, collected_unit_count=2, issued_unit_count=1, wasted_unit_count=1))

    def test_empty_real_report_validation_and_failure_do_not_fabricate_data(self):
        day = timezone.localdate()
        self.assert_counts(self.client.get(self.route(day)), dict(
            donation_event_count=0, collected_unit_count=0, issued_unit_count=0, wasted_unit_count=0))
        self.assertEqual(self.client.get(self.route(day, day-timedelta(days=1))).status_code, 400)
        self.assertEqual(self.client.get('/api/v1/reports?from=bad&to=bad').status_code, 400)
        with patch('inventory.selectors.reporting.CollectionEvent.objects.filter',
                   side_effect=DatabaseError('private reporting fixture')):
            response = self.client.get(self.route(day))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private reporting', response.content.decode())
        self.assertNotIn('donation_event_count', response.json())

    def test_actual_sources_keep_admin_api_and_page_access(self):
        day = timezone.localdate()
        source_unit(actor=self.staff)
        self.assertEqual(self.client.get('/reports').status_code, 200)
        self.assertEqual(Client().get(self.route(day)).status_code, 403)
        for actor in (self.staff, self.owner, user('DONOR'), user(is_superuser=True), user(is_active=False)):
            client, _ = signed_in(actor)
            self.assertEqual(client.get(self.route(day)).status_code, 403)
            self.assertEqual(client.get('/reports').status_code, 403)
