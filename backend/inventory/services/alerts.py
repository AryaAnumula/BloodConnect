"""Durable condition episodes and the existing provider, in one transaction."""
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from collections import Counter
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.errors import DecisionRequired
from core.input_schemas import BLOOD_GROUPS
from inventory.exceptions import InventoryUnavailable
from inventory.models import AlertSweep, BloodUnit, InventoryAlert
from inventory.permissions import require_staff
from inventory.services.policy import SUPPORTED_COMPONENTS
from notification_adapter.services.intents import enqueue_intent


def alert_policy():
    try:
        path = Path(getattr(settings, 'INVENTORY_ALERT_POLICY_FILE',
                           Path(__file__).resolve().parents[1] / 'demo_alert_policy.json'))
        policy = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(policy, dict) or set(policy) != {'version', 'minimums', 'near_expiry_days', 'channels'}
                or not isinstance(policy['version'], str) or not policy['version'].strip()
                or type(policy['near_expiry_days']) is not int or policy['near_expiry_days'] <= 0):
            raise ValueError('Invalid alert policy')
        minimums = policy['minimums']
        if not isinstance(minimums, list) or len(minimums) != 32:
            raise ValueError('All configured pairs required')
        pairs = {}
        for row in minimums:
            if (set(row) != {'blood_group', 'component_type', 'minimum'}
                    or row['blood_group'] not in BLOOD_GROUPS or row['component_type'] not in SUPPORTED_COMPONENTS
                    or type(row['minimum']) is not int or row['minimum'] < 0):
                raise ValueError('Invalid minimum')
            key = (row['blood_group'], row['component_type'])
            if key in pairs:
                raise ValueError('Duplicate pair')
            pairs[key] = row['minimum']
        channels = policy['channels']
        if (not isinstance(channels, list) or not channels
                or any(type(c) is not str or c not in ('IN_APP', 'EMAIL_MOCK', 'SMS_MOCK') for c in channels)
                or len(channels) != len(set(channels))):
            raise ValueError('Invalid channels')
        recipient = UUID(str(getattr(settings, 'INVENTORY_ALERT_RECIPIENT_ID',
                                    os.environ.get('INVENTORY_ALERT_RECIPIENT_ID', ''))))
        user = get_user_model().objects.get(pk=recipient)
        if not user.is_active or user.is_superuser or user.role not in ('STAFF', 'ADMIN'):
            raise ValueError('Invalid operational recipient')
        canonical = policy | {'recipient_id': str(recipient)}
        fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
        return policy, pairs, recipient, fingerprint
    except (OSError, ValueError, KeyError, TypeError, AttributeError, get_user_model().DoesNotExist) as exc:
        raise InventoryUnavailable() from exc


def evaluate_alerts(*, actor, now) -> dict:
    require_staff(actor)
    if not isinstance(now, datetime) or timezone.is_naive(now):
        raise ValidationError({'now': ['An aware timestamp is required.']})
    try:
        with transaction.atomic():
            AlertSweep.objects.get_or_create(key='inventory')
            sweep = AlertSweep.objects.select_for_update().get(key='inventory')
            if sweep.evaluated_at is not None and now < sweep.evaluated_at:
                raise ValidationError({'now': ['Evaluation cannot move backwards.']})
            policy, pairs, recipient, fingerprint = alert_policy()
            today = timezone.localdate(now, ZoneInfo('Asia/Kolkata'))
            # One source snapshot for both conditions; no separately maintained counter.
            usable = list(BloodUnit.objects.filter(status='AVAILABLE', expiry_date__gt=today).order_by('id'))
            totals = Counter((unit.blood_group, unit.component_type) for unit in usable)
            conditions = {}
            for (group, component), minimum in sorted(pairs.items()):
                if totals.get((group, component), 0) < minimum:
                    conditions[f'LOW_STOCK:{group}:{component}'] = ('LOW_STOCK', group, component, None)
            for unit in usable:
                if unit.expiry_date <= today+timedelta(days=policy['near_expiry_days']):
                    conditions[f'NEAR_EXPIRY:{unit.pk}'] = ('NEAR_EXPIRY', unit.blood_group, unit.component_type, unit.pk)
            active = {row.condition_key: row for row in InventoryAlert.objects.filter(active=True)}
            resolved = created = 0
            for key, row in active.items():
                if key not in conditions or row.policy_fingerprint != fingerprint:
                    row.active = False
                    row.resolved_at = now
                    row.save(update_fields=['active', 'resolved_at'])
                    resolved += 1
            for key, (kind, group, component, unit_id) in conditions.items():
                previous = active.get(key)
                if previous is not None and previous.active:
                    continue
                alert_id, event_id = uuid4(), uuid4()
                intent = enqueue_intent(event_id=event_id, recipient_id=recipient,
                    event_type=kind, record_id=alert_id, due_at=now, channels=policy['channels'])
                InventoryAlert.objects.create(id=alert_id, condition_key=key, policy_fingerprint=fingerprint,
                    kind=kind, blood_group=group, component_type=component, unit_id=unit_id,
                    intent_id=intent['id'], created_at=now)
                created += 1
            sweep.evaluated_at = now
            sweep.save(update_fields=['evaluated_at'])
            return {'created': created, 'resolved': resolved, 'active': len(conditions)}
    except (DatabaseError, DecisionRequired) as exc:
        raise InventoryUnavailable() from exc
