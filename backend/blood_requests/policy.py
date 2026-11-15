"""BB-17 request input policy. Approved values: BC-D017–BC-D022 (15 Nov 2026).

The runtime policy is loaded from config/request-policy.json by blood_requests.configuration.
A missing or malformed policy fails closed with DecisionRequired (API: 409 policy_unresolved).
A policy can only narrow what the database accepts: components must be model choices and
the maximum cannot exceed the database constraint.
"""
from dataclasses import dataclass

from core.errors import DecisionRequired

from blood_requests.models import MAX_REQUEST_QUANTITY, BloodRequest

URGENCY_LEVELS = tuple(BloodRequest.Urgency.values)  # CRITICAL, URGENT, ROUTINE
SUPPORTED_COMPONENTS = frozenset(BloodRequest.ComponentType.values)


@dataclass(frozen=True)
class RequestInputPolicy:
    component_types: tuple
    max_quantity: int

    def __post_init__(self):
        components = self.component_types
        if (not isinstance(components, tuple) or not components
                or any(not isinstance(c, str) or c not in SUPPORTED_COMPONENTS for c in components)
                or len(set(components)) != len(components)):
            raise DecisionRequired('Supported request components are not configured.')
        limit = self.max_quantity
        if (isinstance(limit, bool) or not isinstance(limit, int)
                or not 1 <= limit <= MAX_REQUEST_QUANTITY):
            raise DecisionRequired('The maximum request quantity is not configured.')


def require_policy(policy) -> RequestInputPolicy:
    if not isinstance(policy, RequestInputPolicy):
        raise DecisionRequired('Request input policy is not configured.')
    return policy
