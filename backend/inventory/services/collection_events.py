
"""Collection-event component validation.

This module contains pure validation only. Database uniqueness and
cross-transaction event locking belong in the inventory write service.
"""

from collections.abc import Sequence


WHOLE_BLOOD = "WHOLE_BLOOD"

COMPONENT_TYPES = frozenset({
    "RBC",
    "PLASMA",
    "PLATELETS",
})

SUPPORTED_EVENT_COMPONENTS = COMPONENT_TYPES | {WHOLE_BLOOD}


def validate_event_components(
    *,
    components: Sequence[str],
) -> tuple[str, ...]:
    """Validate and return the components belonging to one collection event.

    A collection event must contain either WHOLE_BLOOD alone or a
    non-empty combination of distinct separated components.
    """
    if not isinstance(components, (list, tuple)):
        raise ValueError("Components must be supplied as a list or tuple.")

    if not components:
        raise ValueError("A collection event must contain at least one component.")

    if any(
        not isinstance(component, str)
        or component not in SUPPORTED_EVENT_COMPONENTS
        for component in components
    ):
        raise ValueError("Collection event contains an unsupported component.")

    if len(components) != len(set(components)):
        raise ValueError("A component may appear only once in a collection event.")

    if WHOLE_BLOOD in components and len(components) != 1:
        raise ValueError("WHOLE_BLOOD must be the only component in its event.")

    return tuple(components)
