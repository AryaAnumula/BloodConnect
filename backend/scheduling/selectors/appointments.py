"""BB-21 own appointments only; there is no donor_id parameter, so no override is possible."""
from donors.models import DonorProfile
from scheduling.dto import appointment_dto
from scheduling.models import Appointment
from scheduling.permissions import require_camp_role


def list_own_appointments(*, actor, page: int = 1, page_size: int = 20) -> dict:
    require_camp_role(user=actor, action='own_appointments')
    profile = DonorProfile.objects.filter(user_id=actor.pk).first()
    queryset = (Appointment.objects.filter(donor=profile).select_related('slot')
                if profile else Appointment.objects.none())
    count = queryset.count()
    offset = (page - 1) * page_size
    rows = list(queryset.order_by('slot__starts_at', 'id')[offset:offset + page_size])
    return {'count': count, 'page': page, 'page_size': page_size,
            'results': [appointment_dto(row) for row in rows]}
