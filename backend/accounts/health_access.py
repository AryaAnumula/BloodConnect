"""BB-12: endpoint-boundary audit call. NOT used by may_view_donor_health (that stays pure)."""
from audit.events import record_security_event


def record_donor_health_denial(*, request) -> None:
    """Record exactly one access_denied/denied event for a denial returned as 404.

    Call once, at the endpoint/service boundary, BEFORE returning the 404, and outside any
    transaction that will be rolled back. Do not call for ordinary missing records.
    AuditUnavailable (503) must propagate: never swallow it or fake success.
    """
    user = getattr(request, 'user', None)
    actor_id = user.pk if user is not None and getattr(user, 'is_authenticated', False) else None
    record_security_event(event_type='access_denied', actor_id=actor_id,
                          request_id=getattr(request, 'request_id', None),
                          outcome='denied')