"""BB-16 boundary to Yashwitha's allocation provider (docs/sprint2/services.md, BC-D026).

Contract: inventory.services.allocation.allocate_units(*, actor, unit_ids, blood_group,
component_type, issued_at) -> list[dict], run inside OUR transaction; it locks the units in
UUID order, rechecks them, marks them ISSUED and returns one {"unit_id", "quantity": 1} per
unit in UUID order. Its own exceptions (conflict/unsafe unit) propagate unchanged.

INTEGRATION_PENDING: the provider is not on any shared branch yet. Until it exists,
load_allocate_units() raises InventoryUnavailable (503), so nothing can be issued and no
success is ever manufactured. blood_requests never defines a competing provider.
"""
import importlib
import uuid

from blood_requests.exceptions import InventoryUnavailable

PROVIDER_MODULE = 'inventory.services.allocation'
_MISSING_MODULES = {'inventory', 'inventory.services', PROVIDER_MODULE}


def load_allocate_units():
    try:
        module = importlib.import_module(PROVIDER_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name in _MISSING_MODULES:
            raise InventoryUnavailable() from None
        raise  # a real import error inside the provider must surface, not be hidden
    allocate_units = getattr(module, 'allocate_units', None)
    if not callable(allocate_units):
        raise InventoryUnavailable()
    return allocate_units


class InventoryContractError(InventoryUnavailable):
    default_detail = 'Inventory returned an unexpected allocation. Nothing was issued.'


def checked_allocation(result, expected_unit_ids: list[str]) -> list[str]:
    """Verify the provider's DTOs exactly match the requested units; any mismatch rolls back."""
    if not isinstance(result, list) or len(result) != len(expected_unit_ids):
        raise InventoryContractError()
    allocated = []
    for item in result:
        if not isinstance(item, dict) or set(item) != {'unit_id', 'quantity'}:
            raise InventoryContractError()
        quantity = item['quantity']
        if isinstance(quantity, bool) or quantity != 1 or not isinstance(quantity, int):
            raise InventoryContractError()
        try:
            allocated.append(str(uuid.UUID(str(item['unit_id']))))
        except (ValueError, TypeError, AttributeError):
            raise InventoryContractError() from None
    if allocated != expected_unit_ids:  # same units, stable UUID order
        raise InventoryContractError()
    return allocated


def translate_provider_error(exc):
    """Map the provider's shared contract errors to our API errors; anything else is untouched.

    Contract v1.1: inventory.exceptions.UnitConflict -> 409 unit_conflict and UnsafeUnit ->
    422 unsafe_unit. If the provider already raises DRF APIExceptions they pass through as-is.
    Returns the exception to raise, or None to re-raise the original (never swallowed).
    """
    from rest_framework.exceptions import APIException

    from blood_requests.exceptions import UnitConflict, UnsafeUnit
    if isinstance(exc, APIException):
        return None
    if not type(exc).__module__.startswith('inventory.'):
        return None
    return {'UnitConflict': UnitConflict, 'UnsafeUnit': UnsafeUnit}.get(type(exc).__name__, lambda: None)()
