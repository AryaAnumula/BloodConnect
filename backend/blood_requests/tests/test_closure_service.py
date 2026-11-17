"""Closure fixtures prove BB19 only; actual BB16 issue-to-close integration is pending."""
import uuid
from unittest import mock

from django.db import DatabaseError
from django.test import TestCase
from rest_framework.exceptions import NotFound, PermissionDenied

from blood_requests.exceptions import CloseInvalidTransition, StorageUnavailable
from blood_requests.services.closure import close_request
from blood_requests.tests.helpers import URL, make_request, make_user, signed_in


class ClosureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user()
        cls.other = make_user()
        cls.staff = make_user('STAFF')

    def setUp(self):
        self.row = make_request(self.owner, status='ISSUED', fulfilled_quantity=2,
                                reviewed_by=self.staff)
        self.client, self.token = signed_in(self.owner)
        self.url = f'{URL}/{self.row.id}/close'

    def post(self, *, client=None, token=True, data=b'', query=''):
        headers = {'HTTP_X_CSRFTOKEN': self.token} if token else {}
        return (client or self.client).post(self.url + query, data=data,
                                           content_type='application/json', **headers)

    def test_close_and_replay_are_atomic_and_preserve_history(self):
        original = {f.name: getattr(self.row, f.attname) for f in self.row._meta.fields
                    if f.name not in ('status', 'updated_at')}
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'CLOSED')
        self.row.refresh_from_db()
        self.assertEqual(original, {f.name: getattr(self.row, f.attname) for f in self.row._meta.fields
                                    if f.name not in ('status', 'updated_at')})
        updated_at = self.row.updated_at
        with mock.patch('blood_requests.models.BloodRequest.save', side_effect=AssertionError('replay saved')):
            repeated = self.post()
        self.assertEqual(repeated.json(), response.json())
        self.row.refresh_from_db()
        self.assertEqual(self.row.updated_at, updated_at)

    def test_only_fully_issued_can_close(self):
        for state, fulfilled in (('SUBMITTED', 0), ('APPROVED', 0), ('APPROVED', 1),
                                 ('REJECTED', 0), ('ISSUED', 1)):
            with self.subTest(state=state, fulfilled=fulfilled):
                self.row.status, self.row.fulfilled_quantity = state, fulfilled
                self.row.save()
                with self.assertRaises(CloseInvalidTransition):
                    close_request(actor=self.owner, request_id=self.row.id)
                self.assertEqual(self.post().status_code, 422)
                self.row.refresh_from_db()
                self.assertEqual((self.row.status, self.row.fulfilled_quantity), (state, fulfilled))

    def test_body_and_query_rejected_without_state_change(self):
        for body in (b'{}', b'null', b' ', b'{bad', b'{"status":"CLOSED"}'):
            with self.subTest(body=body):
                self.assertEqual(self.post(data=body).status_code, 400)
        for query in ('?status=CLOSED', '?requester_id=x', '?page=1'):
            self.assertEqual(self.post(query=query).status_code, 400)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, 'ISSUED')

    def test_form_body_is_rejected_even_if_csrf_middleware_consumes_it(self):
        response = self.client.post(self.url, {'status': 'CLOSED'}, HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 400)
        self.row.refresh_from_db()
        self.assertEqual(self.row.status, 'ISSUED')

    def test_missing_csrf_and_other_methods_denied(self):
        self.assertEqual(self.post(token=False).json()['error']['code'], 'csrf_failed')
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.client.patch(self.url, data=b'', content_type='application/json',
                                          HTTP_X_CSRFTOKEN=self.token).status_code, 405)

    def test_wrong_roles_direct_and_http_cannot_close(self):
        for actor in (self.staff, make_user('DONOR'), make_user('ADMIN'), make_user(is_superuser=True),
                      make_user(is_active=False), None):
            with self.subTest(actor=getattr(actor, 'role', None)):
                with self.assertRaises(PermissionDenied):
                    close_request(actor=actor, request_id=self.row.id)
        client, token = signed_in(self.staff)
        self.assertEqual(client.post(self.url, data=b'', content_type='application/json',
                                     HTTP_X_CSRFTOKEN=token).status_code, 403)

    def test_hidden_foreign_and_missing_have_same_response(self):
        client, token = signed_in(self.other)
        responses = [client.post(f'{URL}/{id_}/close', data=b'', content_type='application/json',
                                  HTTP_X_CSRFTOKEN=token) for id_ in (self.row.id, uuid.uuid4())]
        self.assertEqual([r.status_code for r in responses], [404, 404])
        for key in ('code', 'message', 'fields'):
            self.assertEqual(responses[0].json()['error'][key], responses[1].json()['error'][key])
        for id_ in (self.row.id, uuid.uuid4(), 'bad', None):
            with self.assertRaises(NotFound):
                close_request(actor=self.other, request_id=id_)

    def test_failure_after_save_rolls_back_and_redacts(self):
        before = self.row.updated_at
        with mock.patch('blood_requests.services.closure.request_dto', side_effect=DatabaseError('private detail')):
            with self.assertRaises(StorageUnavailable):
                close_request(actor=self.owner, request_id=self.row.id)
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private detail', response.content.decode())
        self.row.refresh_from_db()
        self.assertEqual((self.row.status, self.row.updated_at), ('ISSUED', before))
        self.assertEqual(self.post().status_code, 200)
