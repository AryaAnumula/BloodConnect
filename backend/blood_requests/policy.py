"""BB-17 request input policy, injected into validation. PENDING S2-01 / S2-03.

No runtime default lives here on purpose. The supported components (S2-01: three in the
current register, four in the SRS/shared context) and the maximum units per request are
not recorded as approved, so callers must pass an explicit policy. A missing or malformed
policy fails closed with DecisionRequired (mapped later to 409 policy_unresolved).

Urgency values CRITICAL/URGENT/ROUTINE are identical in every source and in the proposed
OpenAPI, so they are a fixed contract enum. Their ORDERING is S2-03 and belongs to BB-18.
"""
from dataclasses import dataclass

from core.errors import DecisionRequired

URGENCY_LEVELS = ('CRITICAL', 'URGENT', 'ROUTINE')


@dataclass(frozen=True)
class RequestInputPolicy:
    component_types: tuple
    max_quantity: int

    def __post_init__(self):
        components = self.component_types
        if (not isinstance(components, tuple) or not components
                or any(not isinstance(c, str) or not c or c != c.strip() for c in components)
                or len(set(components)) != len(components)):
            raise DecisionRequired('Supported request components are not configured.')
        limit = self.max_quantity
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise DecisionRequired('The maximum request quantity is not configured.')


def require_policy(policy) -> RequestInputPolicy:
    if not isinstance(policy, RequestInputPolicy):
        raise DecisionRequired('Request input policy is not configured.')
    return policy
