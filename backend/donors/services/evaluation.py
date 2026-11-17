"""BB-07, Ankitha. Pure screening evaluation. Demonstration rules only; not medical advice."""
from datetime import date, datetime
from decimal import Decimal

REASONS = {
    'AGE_BELOW_MINIMUM': 'Age is below the minimum for this demonstration screening.',
    'AGE_ABOVE_MAXIMUM': 'Age is above the maximum for this demonstration screening.',
    'WEIGHT_BELOW_MINIMUM': 'Weight is below the minimum for this demonstration screening.',
    'DONATION_TOO_RECENT': 'The last donation was too recent for this demonstration screening.',
}


def _checked_date(name, value, today):
    if value is None:
        return None
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValueError(f'{name} must be a date or None.')
    if value > today:
        raise ValueError(f'{name} cannot be in the future.')
    return value


def evaluate(*, age_years, weight_kg, last_donation_date, confirmed_collection_date, today, rules):
    """Pure demonstration screening. No database, transaction or inventory access.

    `confirmed_collection_date` is REQUIRED (pass None explicitly when there is none). The
    effective last donation is the later non-null of the self-reported and confirmed dates;
    both absent skips only the gap check. Invalid or future dates raise ValueError.
    """
    if isinstance(today, datetime) or not isinstance(today, date):
        raise ValueError('today must be a date.')
    reported = _checked_date('last_donation_date', last_donation_date, today)
    confirmed = _checked_date('confirmed_collection_date', confirmed_collection_date, today)
    effective_last = max((d for d in (reported, confirmed) if d is not None), default=None)

    codes = []
    if age_years < rules['min_age_years']:
        codes.append('AGE_BELOW_MINIMUM')
    if age_years > rules['max_age_years']:
        codes.append('AGE_ABOVE_MAXIMUM')
    if weight_kg < rules['min_weight_kg']:
        codes.append('WEIGHT_BELOW_MINIMUM')
    if effective_last is not None:
        if (today - effective_last).days < rules['min_days_between_donations']:
            codes.append('DONATION_TOO_RECENT')
    status = 'INELIGIBLE' if codes else 'ELIGIBLE'
    return status, codes, [REASONS[c] for c in codes]
