"""BB08 latest persisted result; consumes BB12 policy, never duplicates eligibility rules."""
from uuid import UUID
from rest_framework.exceptions import NotFound, PermissionDenied
from accounts.permissions import is_authorized_staff, may_view_donor_health
from core.errors import FeatureNotImplemented
from donors.models.profile import DonorProfile
from donors.eligibility_reader import read_saved_results


class ResultAccessDenied(NotFound):
    """Disguised object denial; endpoint records once and returns ordinary 404."""


def latest_eligibility_result(*, actor, donor_id: UUID):
    if (actor is None or not getattr(actor, 'is_authenticated', False)
            or not getattr(actor, 'is_active', False) or getattr(actor, 'is_superuser', False)):
        raise PermissionDenied()
    if getattr(actor, 'role', None) != 'DONOR' and not is_authorized_staff(user=actor):
        raise PermissionDenied()
    try:
        profile = DonorProfile.objects.get(pk=donor_id)
    except DonorProfile.DoesNotExist:
        raise NotFound() from None
    try:
        allowed = may_view_donor_health(user=actor, donor_user_id=profile.user_id)
    except NotImplementedError:
        raise FeatureNotImplemented('BB12 ownership provider is not integrated yet.') from None
    if not allowed:
        raise ResultAccessDenied()
    result = read_saved_results(donor_ids=[profile.pk]).get(str(profile.pk))
    if result is None:
        raise NotFound()
    return result
