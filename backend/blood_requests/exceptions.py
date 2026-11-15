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


class CloseInvalidTransition(APIException):
    status_code = 422
    default_code = 'invalid_transition'
    default_detail = 'Only a fully issued request can be closed.'
