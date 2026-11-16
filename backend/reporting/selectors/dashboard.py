"""ADMIN summaries from real domain providers; no partial/fabricated success response."""
from datetime import datetime
from django.db import DatabaseError
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.input_schemas import BLOOD_GROUPS
from reporting.providers import dashboard as providers
from reporting.selectors.common import nonnegative
from reporting.exceptions import ReportingUnavailable
from reporting.permissions import require_admin



def dashboard_for_admin(*, actor, now) -> dict:
    require_admin(actor=actor)
    if not isinstance(now, datetime) or timezone.is_naive(now):
        raise ValidationError({'now': ['An aware server timestamp is required.']})
    try:
        page = providers.current_stock(actor=actor)
        if not isinstance(page, dict) or not isinstance(page.get('results'), list):
            raise ReportingUnavailable()
        rows = page['results']
        if nonnegative(page.get('count')) != len(rows) or len(rows) > 32:
            raise ReportingUnavailable()
        stock, seen = [], set()
        for row in rows:
            if not isinstance(row, dict):
                raise ReportingUnavailable()
            group, component = row.get('blood_group'), row.get('component_type')
            if group not in BLOOD_GROUPS or component not in ('WHOLE_BLOOD', 'RBC', 'PLASMA', 'PLATELETS'):
                raise ReportingUnavailable()
            key = (group, component)
            if key in seen:
                raise ReportingUnavailable()
            seen.add(key)
            stock.append({'blood_group': group, 'component_type': component,
                          'available_quantity': nonnegative(row.get('available_quantity'))})
        return {'as_of': now.isoformat(), 'stock': sorted(stock, key=lambda x: (x['blood_group'], x['component_type'])),
                'pending_requests': nonnegative(providers.pending_requests()),
                'upcoming_camps': nonnegative(providers.upcoming_camps(now=now))}
    except DatabaseError:
        raise ReportingUnavailable() from None
