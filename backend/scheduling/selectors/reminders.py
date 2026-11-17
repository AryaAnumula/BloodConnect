"""Internal read-only appointment context for the reminder dispatcher."""
from rest_framework.exceptions import NotFound

from scheduling.models import Appointment


def reminder_context(*, appointment_id):
    appointment = (Appointment.objects.select_related('donor', 'slot__camp')
                   .filter(pk=appointment_id).first())
    if appointment is None:
        raise NotFound()
    return {
        'appointment_id': appointment.pk,
        'donor_user_id': appointment.donor.user_id,
        'starts_at': appointment.slot.starts_at,
        'appointment_status': appointment.status,
        'camp_status': appointment.slot.camp.status if appointment.slot.camp_id else None,
    }
