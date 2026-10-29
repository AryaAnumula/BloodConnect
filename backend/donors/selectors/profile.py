"""BB-12, Arnav. Object policy: accounts.permissions.may_view_donor_health (D-09)."""
from uuid import UUID

from rest_framework.exceptions import NotFound

from accounts.permissions import may_view_donor_health
from donors.models.profile import DonorProfile


class ProfileAccessDenied(NotFound):
    """Profile exists but this caller may not see it.

    Renders as the SAME 404 as a missing profile. The endpoint catches it only to
    record one audit event; it never gets its own response.
    """


def donor_profile_for_actor(*, actor, donor_id: UUID) -> dict:
    """Return the OpenAPI DonorProfile projection, or raise NotFound / ProfileAccessDenied."""
    try:
        profile = DonorProfile.objects.select_related('user').get(pk=donor_id)
    except DonorProfile.DoesNotExist:
        raise NotFound() from None
    if not may_view_donor_health(user=actor, donor_user_id=profile.user_id):
        raise ProfileAccessDenied()
    # Explicit allowlist (docs/api/openapi.yaml DonorProfile). Never dump model fields.
    return {
        'id': str(profile.pk),
        'user_id': str(profile.user_id),
        'full_name': profile.full_name,
        'email': profile.user.email,
        'mobile': profile.mobile,
        'blood_group': profile.blood_group,
        'location': profile.location,
    }