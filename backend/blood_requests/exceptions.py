"""blood_requests domain errors, rendered by the shared core.errors handler.

Codes follow docs/sprint2/conventions.md: 422 invalid business transition, 503 redacted
storage unavailability. Messages never include request contents.
"""
from rest_framework.exceptions import APIException


class InvalidTransition(APIException):
    status_code = 422
    default_code = 'invalid_transition'
    default_detail = 'This request has already been decided and cannot be changed.'


class StorageUnavailable(APIException):
    status_code = 503
    default_code = 'storage_unavailable'
    default_detail = 'Request storage is temporarily unavailable. Nothing was changed.'


class IssueInvalidTransition(APIException):
    status_code = 422
    default_code = 'invalid_transition'
    default_detail = 'Only an approved request can have blood issued against it.'


class Oversupply(APIException):
    status_code = 422
    default_code = 'oversupply'
    default_detail = 'More units were selected than the request still needs. Nothing was issued.'


class UnitConflict(APIException):
    status_code = 409
    default_code = 'unit_conflict'
    default_detail = 'A selected unit has already been issued. Nothing was issued.'


class InventoryUnavailable(APIException):
    """Fail-closed while the real inventory provider / issue-record model is not integrated."""
    status_code = 503
    default_code = 'inventory_unavailable'
    default_detail = 'Issuing is not available: inventory is not connected. Nothing was issued.'


class UnsafeUnit(APIException):
    """Shared contract v1.1: a selected unit is not usable (expired, quarantined, discarded,
    already used, or not an exact group/component match)."""
    status_code = 422
    default_code = 'unsafe_unit'
    default_detail = 'A selected unit cannot be issued for this request. Nothing was issued.'
