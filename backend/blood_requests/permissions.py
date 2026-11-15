"""BB-17 private requester gate (approved BC-D017–BC-D022: interim helper in this app).

Submission requires an authenticated, active, non-superuser account whose role is
REQUESTER. Every superuser is denied, including one with role REQUESTER, and clinical
permissions (view_donor_health) grant nothing here. The same predicate is used by the
API permission class and the submission service. Pure: no writes, no audit calls; the
shared DRF exception handler records the single access_denied event.
"""
from rest_framework.permissions import BasePermission


def may_submit_request(*, user) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if not getattr(user, 'is_active', False):
        return False
    if getattr(user, 'is_superuser', False):
        return False
    return getattr(user, 'role', None) == 'REQUESTER'


class IsRequester(BasePermission):
    """Use after IsAuthenticated so anonymous callers keep 403 authentication_required."""

    def has_permission(self, request, view):
        return may_submit_request(user=request.user)
