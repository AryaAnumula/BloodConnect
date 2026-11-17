"""BB-19 reuses strict staff query fields; defaults are applied by the actor's selector."""
from core.validation import StrictInputSerializer
from blood_requests.serializers.review import StaffQueueQuerySerializer


class TrackingQuerySerializer(StaffQueueQuerySerializer):
    """Omitted status stays omitted: requester all-own, staff SUBMITTED."""


class EmptyQuerySerializer(StrictInputSerializer):
    """Detail/close accept no query fields, including owner/status overrides."""
