"""TEST-ONLY doubles for BB-16 request-side tests. NOT an inventory provider, NOT integration.

FakeAllocator mimics the agreed allocate_units contract (one {"unit_id", "quantity": 1} per
selected unit in UUID order) without touching any database or unit rows. fake_issue_writer
returns issue-record-shaped dicts without a database table. Real-unit evidence (Yashwitha's
provider, BloodUnit rows and IssueRecord) is in test_issue_integration.py.
"""
import threading
import uuid
from contextlib import contextmanager
from unittest import mock

from rest_framework.exceptions import APIException


class FakeUnsafeUnit(APIException):  # stands in for whatever error the real provider raises
    status_code = 422
    default_code = 'unsafe_unit'
    default_detail = 'TEST-ONLY: a selected unit cannot be issued.'


_DEFAULT = object()


class FakeAllocator:
    def __init__(self, *, result=_DEFAULT, error=None):
        self.calls = []
        self.result = result
        self.error = error
        self._lock = threading.Lock()

    def __call__(self, *, actor, unit_ids, blood_group, component_type, issued_at):
        with self._lock:
            self.calls.append(dict(actor=actor, unit_ids=list(unit_ids), blood_group=blood_group,
                                   component_type=component_type, issued_at=issued_at))
        if self.error is not None:
            raise self.error
        if self.result is not _DEFAULT:
            return self.result
        return [{'unit_id': unit_id, 'quantity': 1} for unit_id in unit_ids]


def fake_issue_writer(*, blood_request, unit_ids, actor, issued_at):
    return [{'id': str(uuid.uuid4()), 'request_id': str(blood_request.id), 'unit_id': unit_id,
             'issued_by': str(actor.pk), 'issued_at': issued_at.isoformat(), 'issued_quantity': 1}
            for unit_id in unit_ids]


@contextmanager
def doubles(allocator=None, writer=fake_issue_writer):
    allocator = allocator or FakeAllocator()
    with mock.patch('blood_requests.services.issue.load_allocate_units', return_value=allocator), \
         mock.patch('blood_requests.services.issue._write_issue_records', side_effect=writer):
        yield allocator


def unit_ids(count):
    return sorted(str(uuid.uuid4()) for _ in range(count))
