"""Versioned educational policy; never a clinical default."""
import json
from pathlib import Path

from inventory.exceptions import InventoryUnavailable
from inventory.services.policy import SUPPORTED_COMPONENTS


def shelf_life_policy():
    try:
        data = json.loads(Path(__file__).with_name('demo_policy.json').read_text(encoding='utf-8'))
        policy = data['shelf_life_days']
        if (data['version'] != 'bloodconnect-demo-v1' or set(policy) != set(SUPPORTED_COMPONENTS)
                or any(type(v) is not int or v <= 0 for v in policy.values())):
            raise ValueError('Invalid policy')
        return policy
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise InventoryUnavailable() from exc
