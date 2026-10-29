"""PROPOSED public interface. Owner: Arnav / BB-04, BB-12. Coordinate signature changes."""
import uuid

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


class IsDonorOrAuthorizedStaff(BasePermission):
    """Role-level gate for own-donor-or-authorized-staff routes.

    Rejects ADMIN, REQUESTER, plain STAFF and superusers BEFORE any record lookup
    (403 forbidden). It does NOT prove ownership; that is the object check
    may_view_donor_health, done after the lookup.
    """

    def has_permission(self, request, view):
        user = request.user
        if user is None or not getattr(user, 'is_authenticated', False):
            return False
        if not getattr(user, 'is_active', False):
            return False
        if getattr(user, 'is_superuser', False):
            return False
        return getattr(user, 'role', None) == 'DONOR' or is_authorized_staff(user=user)


def _same_user_id(a, b) -> bool:
    """Compare ids as UUIDs so str/UUID forms match; anything unparseable is a mismatch."""
    try:
        return uuid.UUID(str(a)) == uuid.UUID(str(b))
    except (ValueError, AttributeError, TypeError):
        return False


def may_view_donor_health(*, user, donor_user_id) -> bool:
    """Allow the owning DONOR or explicitly authorized staff (D-09).

    Pure and read-only: no database writes, no audit calls. Endpoint owners record
    denials themselves. ADMIN, REQUESTER and Django superusers get no automatic
    access, and a signed-in check alone is never enough.
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if not getattr(user, 'is_active', False):
        return False
    if getattr(user, 'is_superuser', False):
        return False
    if is_authorized_staff(user=user):
        return True
    return (
        getattr(user, 'role', None) == 'DONOR'
        and _same_user_id(getattr(user, 'pk', None), donor_user_id)
    )