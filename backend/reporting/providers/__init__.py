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
        source = import_module(module)
    except ModuleNotFoundError as error:
        # An absent agreed provider (or parent package) is an integration gap.
        # A missing dependency INSIDE an installed provider is a programming error.
        missing = error.name
        if missing and (module == missing or module.startswith(missing + '.')):
            raise ReportingUnavailable() from None
        raise
    provider = getattr(source, function, None)
    if not callable(provider):
        raise ReportingUnavailable()
    try:
        return provider(**kwargs)
    except (DatabaseError, DecisionRequired):
        raise ReportingUnavailable() from None

