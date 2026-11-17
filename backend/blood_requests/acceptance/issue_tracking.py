"""Explicit BB19 acceptance against REAL BB16/inventory; never auto-discovered.

Run: python backend/manage.py test blood_requests.acceptance.issue_tracking
Missing real providers/models FAIL readiness. No doubles and no manufactured ISSUED state.
Fixture insertion prepares valid source inventory; intake itself is tested by BB13.
"""
import json
from datetime import timedelta
from importlib import import_module

from django.apps import apps
from django.test import TestCase
from django.utils import timezone

from blood_requests.models import BloodRequest
from blood_requests.tests.helpers import make_user, signed_in
from donors.models import DonorProfile


class RealIssueTrackingAcceptance(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.Unit = apps.get_model('inventory', 'BloodUnit')
            cls.Event = apps.get_model('inventory', 'CollectionEvent')
            cls.Issue = apps.get_model('blood_requests', 'IssueRecord')
            provider = import_module('inventory.services.allocation').allocate_units
            issue = import_module('blood_requests.services.issue').issue_request
        except (LookupError, ImportError, AttributeError) as error:
            raise RuntimeError(
                'BB19 acceptance NOT READY: compose actual BB13 BloodUnit/CollectionEvent/'
                'allocation and BB16 IssueRecord/issue API first. Do not replace them with doubles.'
            ) from error
        if not callable(provider) or not callable(issue):
            raise RuntimeError('BB19 acceptance requires callable actual issue/allocation services.')
        super().setUpClass()

    def setUp(self):
        self.owner, self.staff, self.other = make_user(), make_user('STAFF'), make_user()
        self.owner_client, self.owner_token = signed_in(self.owner)
        self.staff_client, self.staff_token = signed_in(self.staff)
        self.other_client, self.other_token = signed_in(self.other)
        self.today = timezone.localdate()

    def unit(self, number, group='A+'):
        collected = self.today - timedelta(days=1)
        donor = DonorProfile.objects.create(
            user=make_user('DONOR'), full_name='Acceptance fixture donor',
            mobile=f'+9197000{number:05d}', blood_group=group, location='Demo City',
            last_confirmed_collection_date=collected,
        )
        event = self.Event.objects.create(
            donor=donor, collection_date=collected, blood_group=group,
            status='CONFIRMED', recorded_by=self.staff,
        )
        return self.Unit.objects.create(
            unit_code=f'BB19-ACCEPTANCE-{number}', donor=donor, collection_event=event,
            blood_group=group, component_type='RBC', collection_date=collected,
            expiry_date=collected + timedelta(days=42), quantity=1, status='AVAILABLE',
        )

    def approved_request(self):
        response = self.owner_client.post(
            '/api/v1/requests',
            data=json.dumps(dict(blood_group='A+', component_type='RBC',
                                 quantity=2, urgency_level='ROUTINE')),
            content_type='application/json', HTTP_X_CSRFTOKEN=self.owner_token,
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.route = '/api/v1/requests/' + response.json()['id']
        response = self.staff_client.patch(
            self.route + '/status', data=json.dumps({'status': 'APPROVED'}),
            content_type='application/json', HTTP_X_CSRFTOKEN=self.staff_token,
        )
        self.assertEqual(response.status_code, 200, response.content)
        return BloodRequest.objects.get(pk=response.json()['id'])

    def issue(self, *units):
        return self.staff_client.post(
            self.route + '/issues', data=json.dumps({'unit_ids': [str(u.pk) for u in units]}),
            content_type='application/json', HTTP_X_CSRFTOKEN=self.staff_token,
        )

    def close(self, client=None, token=None):
        return (client or self.owner_client).post(
            self.route + '/close', data=b'', content_type='application/json',
            HTTP_X_CSRFTOKEN=token or self.owner_token,
        )

    def assert_tracking(self, *, status, fulfilled):
        detail = self.owner_client.get(self.route)
        self.assertEqual(detail.status_code, 200, detail.content)
        data = detail.json()
        self.assertEqual((data['status'], data['fulfilled_quantity']), (status, fulfilled))
        listing = self.owner_client.get('/api/v1/requests')
        self.assertEqual(listing.status_code, 200, listing.content)
        self.assertEqual(listing.json()['count'], 1)
        self.assertEqual(listing.json()['results'], [data])
        return data

    def test_actual_partial_full_issue_tracking_close_and_replay(self):
        first, second = self.unit(1), self.unit(2)
        row = self.approved_request()
        response = self.issue(first)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.Issue.objects.filter(request=row).count(), 1)
        first.refresh_from_db()
        self.assertEqual(first.status, 'ISSUED')
        self.assert_tracking(status='APPROVED', fulfilled=1)
        self.assertEqual(self.close().status_code, 422)

        response = self.issue(second)
        self.assertEqual(response.status_code, 201, response.content)
        self.assert_tracking(status='ISSUED', fulfilled=2)
        issues_before = list(self.Issue.objects.order_by('id').values())
        units_before = list(self.Unit.objects.order_by('id').values())
        self.assertEqual(len(issues_before), 2)
        self.assertEqual(self.other_client.get(self.route).status_code, 404)
        self.assertEqual(self.close(self.other_client, self.other_token).status_code, 404)
        self.assertEqual(self.close(self.staff_client, self.staff_token).status_code, 403)
        self.assertEqual(self.owner_client.post(
            self.route + '/close', data=b'', content_type='application/json',
        ).status_code, 403)

        closed = self.close()
        self.assertEqual(closed.status_code, 200, closed.content)
        self.assert_tracking(status='CLOSED', fulfilled=2)
        row.refresh_from_db()
        timestamp = row.updated_at
        replay = self.close()
        self.assertEqual(replay.status_code, 200, replay.content)
        self.assertEqual(replay.json(), closed.json())
        row.refresh_from_db()
        self.assertEqual(row.updated_at, timestamp)
        self.assertEqual(list(self.Issue.objects.order_by('id').values()), issues_before)
        self.assertEqual(list(self.Unit.objects.order_by('id').values()), units_before)

    def test_actual_failed_issue_leaves_owner_tracking_and_all_inventory_unchanged(self):
        matching, wrong_group = self.unit(1), self.unit(2, 'B+')
        row = self.approved_request()
        before = self.assert_tracking(status='APPROVED', fulfilled=0)
        units_before = list(self.Unit.objects.order_by('id').values())
        response = self.issue(matching, wrong_group)
        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(response.json()['error']['code'], 'unsafe_unit')
        self.assertEqual(self.assert_tracking(status='APPROVED', fulfilled=0), before)
        self.assertFalse(self.Issue.objects.filter(request=row).exists())
        self.assertEqual(list(self.Unit.objects.order_by('id').values()), units_before)
