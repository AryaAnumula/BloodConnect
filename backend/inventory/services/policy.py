
"""Fail-closed inventory policy validation and expiry calculations."""

from datetime import date, datetime, timedelta


class DecisionRequired(Exception):
    """Raised when an approved inventory policy is unavailable or invalid."""


SUPPORTED_COMPONENTS = (
    "WHOLE_BLOOD",
    "RBC",
    "PLASMA",
    "PLATELETS",
)


def get_shelf_life_days(*, component_type: str, policy: dict) -> int:
    """Return an explicitly configured positive shelf-life value."""
    if component_type not in SUPPORTED_COMPONENTS:
        raise DecisionRequired("Unsupported inventory component.")

    if not isinstance(policy, dict):
        raise DecisionRequired("Shelf-life policy is unavailable.")

    value = policy.get(component_type)

    if type(value) is not int or value <= 0:
        raise DecisionRequired(
            f"Approved shelf-life policy is missing or invalid for {component_type}."
        )

    return value


def calculate_expiry_date(
    *,
    collection_date: date,
    component_type: str,
    policy: dict,
    today: date,
) -> date:
    """Calculate expiry using an explicitly configured shelf life."""
    if (
        not isinstance(collection_date, date)
        or isinstance(collection_date, datetime)
    ):
        raise ValueError("Collection date must be a date.")

    if not isinstance(today, date) or isinstance(today, datetime):
        raise ValueError("Today must be a date.")

    if collection_date > today:
        raise ValueError("Collection date cannot be in the future.")

    shelf_life_days = get_shelf_life_days(
        component_type=component_type,
        policy=policy,
    )

    return collection_date + timedelta(days=shelf_life_days)


def is_unit_usable(
    *,
    status: str,
    expiry_date: date,
    today: date,
) -> bool:
    """Return whether a unit is available and not expired."""
    if (
        not isinstance(expiry_date, date)
        or isinstance(expiry_date, datetime)
    ):
        raise ValueError("Expiry date must be a date.")

    if not isinstance(today, date) or isinstance(today, datetime):
        raise ValueError("Today must be a date.")

    if status != "AVAILABLE":
        return False

    return today < expiry_date
