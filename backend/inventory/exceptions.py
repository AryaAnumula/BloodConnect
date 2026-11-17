"""Stable domain errors for inventory and request allocation callers."""
from rest_framework.exceptions import APIException


class UnitConflict(APIException):
    status_code = 409
    default_code = 'unit_conflict'
    default_detail = 'Inventory identity or state conflicts with this operation.'


class UnsafeUnit(APIException):
    status_code = 422
    default_code = 'unsafe_unit'
    default_detail = 'The selected unit is not safe for this allocation.'


class IneligibleDonor(APIException):
    status_code = 422
    default_code = 'ineligible_donor'
    default_detail = 'A current eligible assessment is required.'


class InventoryUnavailable(APIException):
    status_code = 503
    default_code = 'inventory_unavailable'
    default_detail = 'Inventory is temporarily unavailable.'


class TransactionRequired(RuntimeError):
    """Allocation requires its caller's transaction."""
