"""BB-21 domain exceptions. Status codes follow docs/sprint2/conventions.md:
409 concurrent/duplicate/capacity/policy_unresolved, 422 unsafe/ineligible/invalid transition.
Messages never include donor health answers."""
from rest_framework.exceptions import APIException


class CapacityConflict(APIException):
    status_code = 409
    default_code = 'capacity_conflict'
    default_detail = 'Capacity would be exceeded.'


class ScheduleConflict(APIException):
    status_code = 409
    default_code = 'slot_conflict'  # BC-D005
    default_detail = 'The change would leave a slot of this camp outside the camp times.'


class SlotUnavailable(APIException):
    status_code = 409
    default_code = 'slot_unavailable'
    default_detail = 'This slot is not available for booking.'


class DuplicateBooking(APIException):
    status_code = 409
    default_code = 'duplicate_booking'
    default_detail = 'You already have an active booking for this slot.'


class AppointmentConflict(APIException):
    status_code = 409
    default_code = 'appointment_conflict'
    default_detail = 'You already have a confirmed appointment during this time.'


class PolicyUnresolved(APIException):
    status_code = 409
    default_code = 'policy_unresolved'
    default_detail = 'A required policy is not configured.'


class IneligibleDonor(APIException):
    status_code = 422
    default_code = 'ineligible_donor'
    default_detail = 'A current eligible screening result is required to book.'


class CampNotActive(APIException):
    status_code = 422
    default_code = 'invalid_transition'
    default_detail = 'A cancelled camp cannot receive new slots.'


class AppointmentNotCancellable(APIException):
    # Arya (14 Nov): a donor may cancel only before the slot starts.
    status_code = 422
    default_code = 'invalid_transition'
    default_detail = 'An appointment cannot be cancelled once its slot has started.'
