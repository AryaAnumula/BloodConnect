"""BB-07, Ankitha. Loads the version-controlled screening rules (demonstration rules only).

Missing or invalid configuration raises DecisionRequired; no defaults are ever substituted.
These are simplified demonstration rules, not a statement of medical fitness to donate.
"""
import json
from decimal import Decimal
from pathlib import Path

from core.errors import DecisionRequired

RULES_PATH = Path(__file__).resolve().parent / 'screening_rules.json'
EXPECTED_KEYS = {'rules_version', 'min_age_years', 'max_age_years',
                 'min_weight_kg', 'min_days_between_donations'}


def _reject_constant(name):
    raise ValueError('Non-finite JSON number.')


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def load_rules(path) -> dict:
    """Read and validate a rules file. Raises DecisionRequired on any problem."""
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle, parse_float=Decimal, parse_constant=_reject_constant)
    except (OSError, ValueError, RecursionError):
        raise DecisionRequired('Screening configuration is missing or unreadable.') from None

    if not isinstance(data, dict) or set(data) != EXPECTED_KEYS:
        raise DecisionRequired('Screening configuration has unexpected or missing keys.')

    version = data['rules_version']
    min_age, max_age = data['min_age_years'], data['max_age_years']
    weight = data['min_weight_kg']
    days = data['min_days_between_donations']

    if not isinstance(version, str) or not version or version != version.strip() or len(version) > 64:
        raise DecisionRequired('Screening configuration has an invalid rules_version.')
    if not (_is_int(min_age) and _is_int(max_age) and _is_int(days)):
        raise DecisionRequired('Screening configuration ages and days must be whole numbers.')
    if isinstance(weight, bool) or not isinstance(weight, (int, Decimal)):
        raise DecisionRequired('Screening configuration weight must be a number.')
    if min_age < 0 or max_age < min_age or days < 0 or weight <= 0:
        raise DecisionRequired('Screening configuration values are out of range.')

    return {
        'rules_version': version,
        'min_age_years': min_age,
        'max_age_years': max_age,
        'min_weight_kg': Decimal(weight),
        'min_days_between_donations': days,
    }


def approved_screening_rules() -> dict:
    """Return the approved, versioned rules; DecisionRequired if unavailable or invalid."""
    return load_rules(RULES_PATH)
