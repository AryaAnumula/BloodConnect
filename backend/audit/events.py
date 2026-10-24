"""BB-05 public writer. Compatible with Ankitha PR #30's exact call shape.

Policy values/failure handling are D-10 proposals, not team approval.
Only allowlisted metadata; callers must never pass request bodies or credentials.
"""
from uuid import UUID
from django.db import DatabaseError, transaction
from rest_framework.exceptions import APIException
from .models import SecurityEvent


class AuditUnavailable(APIException):
    status_code = 503
    default_code = 'audit_unavailable'
    default_detail = 'Security audit storage is temporarily unavailable.'


ALLOWED_PAIRS = frozenset({('login', 'failure'), ('login', 'success'), ('access_denied', 'denied')})


def record_security_event(*, event_type: str, actor_id: UUID | None, request_id: str, outcome: str) -> None:
    """Persist one event, return None; ValueError for bad metadata, AuditUnavailable on DB failure.

    Owns an atomic write/savepoint, NOT an independent connection/outer commit.
    Do not call inside an outer transaction that will be rolled back: the event
    would roll back too. No payload/logging/network side effects. No retry here.
    Login success is supported for compatibility; its session compensation is
    the login owner's integration responsibility (docs/audit.md).
    """
    if not isinstance(event_type, str) or not isinstance(outcome, str) or (event_type, outcome) not in ALLOWED_PAIRS:
        raise ValueError('Unsupported security event metadata.')
    try:
        correlation = UUID(str(request_id))
        actor = None if actor_id is None else UUID(str(actor_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Security event identifiers must be UUIDs.') from None
    if event_type == 'login' and outcome == 'success' and actor is None:
        raise ValueError('Successful login requires an actor UUID.')
    try:
        with transaction.atomic():
            SecurityEvent.objects.create(event_type=event_type, actor_id=actor,
                                         request_id=correlation, outcome=outcome)
    except DatabaseError:
        # No raw DB details, fallback file, sensitive payload or fabricated success.
        raise AuditUnavailable() from None
