"""BB-17 runtime request policy loader (config/request-policy.json, version-controlled).

Any problem (missing file, bad JSON, unexpected keys, out-of-range values) raises
DecisionRequired. No default is ever substituted.
"""
import json
from pathlib import Path

from core.errors import DecisionRequired

from blood_requests.policy import RequestInputPolicy

POLICY_PATH = Path(__file__).resolve().parents[2] / 'config' / 'request-policy.json'
EXPECTED_KEYS = {'policy_version', 'demo_only', 'component_types', 'min_quantity',
                 'max_quantity', 'requires_current_stock', 'approval'}


def _reject(_):
    raise ValueError('Non-finite or non-integer JSON number.')


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def load_request_policy(path) -> RequestInputPolicy:
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle, parse_constant=_reject, parse_float=_reject)
    except (OSError, ValueError, RecursionError):
        raise DecisionRequired('Request policy configuration is missing or unreadable.') from None
    if not isinstance(data, dict) or set(data) != EXPECTED_KEYS:
        raise DecisionRequired('Request policy configuration has unexpected or missing keys.')
    version = data['policy_version']
    if not isinstance(version, str) or not version or version != version.strip() or len(version) > 64:
        raise DecisionRequired('Request policy configuration has an invalid policy_version.')
    if data['demo_only'] is not True:
        raise DecisionRequired('Request policy configuration must be marked demo_only.')
    if data['requires_current_stock'] is not False:
        # Approved: submission does not require current stock; any other value is unsupported.
        raise DecisionRequired('Request policy stock requirement is not supported.')
    if not _is_int(data['min_quantity']) or data['min_quantity'] != 1:
        raise DecisionRequired('Request policy minimum quantity must be 1.')
    components = data['component_types']
    if not isinstance(components, list):
        raise DecisionRequired('Request policy components must be a list.')
    return RequestInputPolicy(component_types=tuple(components), max_quantity=data['max_quantity'])


def approved_request_policy() -> RequestInputPolicy:
    return load_request_policy(POLICY_PATH)
