"""Fail closed until REAL Sprint2 decision approval is recorded; no fabricated approvals."""
import json
from pathlib import Path
from django.conf import settings
from core.errors import DecisionRequired

def require_policy(*decision_ids):
    path = Path(getattr(settings, 'NOTIFICATION_DECISIONS_FILE', settings.BASE_DIR / 'config/sprint2-decisions.json'))
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        records = {d['id']: d for d in data['decisions']}
        for key in decision_ids:
            d = records[key]
            scope = d.get('notification_provider_scope', d)
            if scope['status'] != 'APPROVED' or not all(scope.get(k) for k in ('approved_by','approved_at','evidence')):
                raise ValueError('Unapproved')
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise DecisionRequired('Notification policy approval is required.') from None
