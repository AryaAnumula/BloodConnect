"""BB-07, Ankitha. Pure screening evaluation. Demonstration rules only; not medical advice."""
from datetime import date
from decimal import Decimal

REASONS = {
    'AGE_BELOW_MINIMUM': 'Age is below the minimum for this demonstration screening.',
    'AGE_ABOVE_MAXIMUM': 'Age is above the maximum for this demonstration screening.',
    'WEIGHT_BELOW_MINIMUM': 'Weight is below the minimum for this demonstration screening.',
    'DONATION_TOO_RECENT': 'The last donation was too recent for this demonstration screening.',
}


def evaluate(*, age_years, weight_kg, last_donation_date, today, rules):
    codes = []
    if age_years < rules['min_age_years']:
        codes.append('AGE_BELOW_MINIMUM')
    if age_years > rules['max_age_years']:
        codes.append('AGE_ABOVE_MAXIMUM')
    if weight_kg < rules['min_weight_kg']:
        codes.append('WEIGHT_BELOW_MINIMUM')
    if last_donation_date is not None:
        if (today - last_donation_date).days < rules['min_days_between_donations']:
            codes.append('DONATION_TOO_RECENT')
    status = 'INELIGIBLE' if codes else 'ELIGIBLE'
    return status, codes, [REASONS[c] for c in codes]
