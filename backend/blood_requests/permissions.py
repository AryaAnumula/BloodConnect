"""Private blood_requests role gates (BC-D017–BC-D022 for BB-17, BC-D029-c for BB-18).

Pure predicates: no writes, no audit calls. The shared DRF exception handler records the
single access_denied event. Every superuser is denied, and clinical permissions
(view_donor_health) grant nothing here. The same predicates guard the API and the services.
"""
from rest_framework.permissions import BasePermission


def _active_non_superuser_with_role(user, role) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if not getattr(user, 'is_active', False):
        return False
    if getattr(user, 'is_superuser', False):
        return False
    return getattr(user, 'role', None) == role


def may_submit_request(*, user) -> bool:
    """BB-17: authenticated, active, non-superuser REQUESTER."""
    return _active_non_superuser_with_role(user, 'REQUESTER')


def may_review_requests(*, user) -> bool:
    """BB-18: authenticated, active, non-superuser STAFF; no clinical permission needed."""
    return _active_non_superuser_with_role(user, 'STAFF')


class IsRequester(BasePermission):
    """Use after IsAuthenticated so anonymous callers keep 403 authentication_required."""

    def has_permission(self, request, view):
        return may_submit_request(user=request.user)


class IsReviewStaff(BasePermission):
    """Use after IsAuthenticated so anonymous callers keep 403 authentication_required."""

    def has_permission(self, request, view):
        return may_review_requests(user=request.user)


def may_issue_requests(*, user) -> bool:
    """BB-16 (BC-D026): authenticated, active, non-superuser STAFF; no clinical permission needed."""
    return _active_non_superuser_with_role(user, 'STAFF')


class IsIssueStaff(BasePermission):
    """Use after IsAuthenticated so anonymous callers keep 403 authentication_required."""

    def has_permission(self, request, view):
        return may_issue_requests(user=request.user)
