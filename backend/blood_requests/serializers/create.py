"""BB-17 RequestCreate input shape (docs/sprint2/openapi.proposed.yaml, PROPOSED).

Accepts exactly blood_group, component_type, quantity and urgency_level. Owner, status,
fulfilled quantity, IDs and timestamps are server-controlled: any extra key is rejected
by StrictInputSerializer, so a client can never choose the requester or the status.
Shape validation only; it does not authorize the caller or save anything.
"""
from core.input_schemas import BLOOD_GROUPS
from core.validation import StrictChoiceField, StrictInputSerializer, StrictIntegerField

from blood_requests.policy import URGENCY_LEVELS, require_policy


class RequestCreateSerializer(StrictInputSerializer):
    blood_group = StrictChoiceField(choices=BLOOD_GROUPS)
    component_type = StrictChoiceField(choices=())  # replaced from the injected policy
    quantity = StrictIntegerField(min_value=1)  # replaced from the injected policy
    urgency_level = StrictChoiceField(choices=URGENCY_LEVELS)

    def __init__(self, *args, policy=None, **kwargs):
        policy = require_policy(policy)  # fail closed before any input is read
        super().__init__(*args, **kwargs)
        self.fields['component_type'] = StrictChoiceField(choices=policy.component_types)
        self.fields['quantity'] = StrictIntegerField(
            min_value=1, max_value=policy.max_quantity, error_messages={
                'invalid': 'Enter a whole number of units.',
                'min_value': 'Quantity must be at least 1 unit.',
                'max_value': f'Quantity cannot be more than {policy.max_quantity} units.',
            })
