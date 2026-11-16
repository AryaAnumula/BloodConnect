"""Call domain-owned public selectors only. Missing real providers never become zeroes.

No inventory/issue models are invented here. Test replacements are boundary doubles,
not proof of actual source integration. No user-supplied module/import path.
"""
from importlib import import_module

from django.db import DatabaseError
from core.errors import DecisionRequired
from reporting.exceptions import ReportingUnavailable


def invoke(module, function, **kwargs):
    try:
        provider = getattr(import_module(module), function)
    except (ImportError, AttributeError):
        raise ReportingUnavailable() from None
    try:
        return provider(**kwargs)
    except (DatabaseError, DecisionRequired):
        raise ReportingUnavailable() from None

