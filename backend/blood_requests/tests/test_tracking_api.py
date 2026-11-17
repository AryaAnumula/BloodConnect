"""Actual session/CSRF/API integration with BB17/18; no invented issue provider."""
import uuid

from django.test import Client, TestCase

from audit.models import SecurityEvent
from blood_requests.tests.helpers import (RESPONSE_KEYS, URL, VALID, make_request, make_user,
                                          patch_json, post_json, review_url, signed_in)


class TrackingApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user()
        cls.other = make_user()
        cls.staff = make_user('STAFF')

    def setUp(self):
        self.client, self.token = signed_in(self.owner)

    def test_requester_get_replaces_temporary_denial_with_private_list(self):
        mine = make_request(self.owner)
        make_request(self.other, urgency='CRITICAL')
        body = self.client.get(URL).json()
        self.assertEqual(body['count'], 1)
        self.assertEqual([r['id'] for r in body['results']], [str(mine.id)])
        self.assertEqual(set(body['results'][0]), RESPONSE_KEYS)

    def test_real_submission_review_and_requester_refresh(self):
        created = post_json(self.client, VALID, self.token)
        self.assertEqual(created.status_code, 201)
        request_id = created.json()['id']
        staff_client, staff_token = signed_in(self.staff)
        detail = f'{URL}/{request_id}'
        self.assertEqual(self.client.get(detail).json()['status'], 'SUBMITTED')
        reviewed = patch_json(staff_client, review_url(request_id),
                              {'status': 'REJECTED', 'rejection_reason': '  Duplicate request  '}, staff_token)
        self.assertEqual(reviewed.status_code, 200)
        refreshed = self.client.get(detail).json()
        self.assertEqual((refreshed['status'], refreshed['rejection_reason'], refreshed['fulfilled_quantity']),
                         ('REJECTED', 'Duplicate request', 0))
        self.assertEqual(self.client.get(URL).json()['results'][0], refreshed)
        self.assertEqual(self.client.get(URL + '?status=SUBMITTED').json()['count'], 0)

    def test_real_approval_visible_without_stock_and_staff_post_still_denied(self):
        row = post_json(self.client, VALID, self.token).json()
        staff_client, token = signed_in(self.staff)
        self.assertEqual(patch_json(staff_client, review_url(row['id']), {'status': 'APPROVED'}, token).status_code, 200)
        self.assertEqual(self.client.get(URL).json()['results'][0]['status'], 'APPROVED')
        self.assertEqual(staff_client.get(URL).json()['count'], 0)  # STAFF default unchanged
        self.assertEqual(staff_client.get(URL + '?status=APPROVED').json()['count'], 1)
        self.assertEqual(post_json(staff_client, VALID, token).status_code, 403)

    def test_strict_query_validation_on_both_roles(self):
        staff_client, _ = signed_in(self.staff)
        for client in (self.client, staff_client):
            for query in ('?status=', '?page=', '?page_size=', '?sort=newest', '?requester_id=x',
                          '?status=SUBMITTED&status=APPROVED', '?page=1&page=2', '?status=ALL',
                          '?page=1.1', '?page=0', '?page_size=101'):
                with self.subTest(query=query):
                    response = client.get(URL + query)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()['error']['code'], 'validation_error')

    def test_hidden_detail_and_minimized_staff_detail(self):
        foreign = make_request(self.other, status='REJECTED', rejection_reason='Other private reason')
        missing = self.client.get(f'{URL}/{uuid.uuid4()}')
        hidden = self.client.get(f'{URL}/{foreign.id}')
        self.assertEqual((missing.status_code, hidden.status_code), (404, 404))
        for key in ('code', 'message', 'fields'):
            self.assertEqual(missing.json()['error'][key], hidden.json()['error'][key])
        self.assertNotIn('private reason', hidden.content.decode())
        staff_client, _ = signed_in(self.staff)
        detail = staff_client.get(f'{URL}/{foreign.id}')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(set(detail.json()), RESPONSE_KEYS)
        self.assertEqual(self.client.get(f'{URL}/{foreign.id}?requester_id={self.owner.id}').status_code, 400)

    def test_partial_and_final_states_read_from_saved_records(self):
        # TEST-ONLY states, not actual BB16 issuance evidence.
        for status, fulfilled in (('APPROVED', 1), ('ISSUED', 2), ('CLOSED', 2)):
            row = make_request(self.owner, status=status, fulfilled_quantity=fulfilled)
            response = self.client.get(f'{URL}/{row.id}')
            self.assertEqual((response.json()['status'], response.json()['fulfilled_quantity']), (status, fulfilled))

    def test_wrong_roles_anonymous_and_superusers_denied_once(self):
        row = make_request(self.owner)
        for user in (make_user('DONOR'), make_user('ADMIN'), make_user(is_superuser=True),
                     make_user('STAFF', is_superuser=True)):
            client, _ = signed_in(user)
            for path in (URL, f'{URL}/{row.id}'):
                SecurityEvent.objects.all().delete()
                response = client.get(path)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()['error']['code'], 'forbidden')
                self.assertEqual(SecurityEvent.objects.filter(event_type='access_denied').count(), 1)
        self.assertEqual(Client().get(URL).json()['error']['code'], 'authentication_required')

    def test_deactivated_owner_loses_session_access(self):
        self.owner.is_active = False
        self.owner.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(URL).json()['error']['code'], 'authentication_required')

    def test_page_routes_do_not_shadow_submission_or_embed_private_records(self):
        row = make_request(self.owner, rejection_reason='Private fixture reason')
        for path in ('/requests', f'/requests/{row.id}', '/requests/new', '/staff/requests'):
            response = Client().get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('Private fixture reason', response.content.decode())
        self.assertEqual(Client().get('/requests/not-a-uuid').status_code, 404)
