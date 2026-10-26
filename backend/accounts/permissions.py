"""PROPOSED public interface. Owner: Arnav / BB-04, BB-12. Coordinate signature changes."""
from rest_framework.permissions import BasePermission

VIEW_DONOR_HEALTH = 'accounts.view_donor_health'


def is_authorized_staff(*, user) -> bool:
    """Require active authenticated staff and the approved clinical-data permission."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if not getattr(user, 'is_active', False):
        return False
    # D-09 (approved): STAFF role AND an explicitly granted permission.
    # Django's has_perm() returns True for EVERY active superuser, which would be a
    # silent bypass, so superusers are refused before has_perm() is consulted.
    if getattr(user, 'is_superuser', False):
        return False
    if getattr(user, 'role', None) != 'STAFF':
        return False
    return user.has_perm(VIEW_DONOR_HEALTH)


class IsAuthorizedStaff(BasePermission):
    """DRF gate for STAFF-ONLY routes (for example donor search).

    Do NOT use this alone on own-donor-or-staff routes (profile, screening,
    eligibility result): it would block legitimate donors. See
    docs/permissions-usage.md.

    Anonymous callers get the standard 403 authentication_required envelope;
    signed-in callers without staff authorization get 403 forbidden.
    """

    def has_permission(self, request, view):
        return is_authorized_staff(user=request.user)


def may_view_donor_health(*, user, donor_user_id) -> bool:
    """Allow own donor or explicitly authorized staff; ADMIN is not automatic access."""
    raise NotImplementedError('BB-12: object policy is unfinished.')