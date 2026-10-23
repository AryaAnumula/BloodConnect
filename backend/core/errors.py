from django.http import JsonResponse
from rest_framework.exceptions import APIException, NotAuthenticated, AuthenticationFailed, PermissionDenied, ValidationError, ParseError
from rest_framework.views import exception_handler as drf_exception_handler

class FeatureNotImplemented(APIException):
    status_code = 501
    default_detail = 'This business feature is scaffolded but not implemented.'
    default_code = 'not_implemented'

class LoginRejected(APIException):
    # Dedicated APIException preserves the login contract's 401 with session auth.
    status_code = 401
    default_detail = 'Invalid email or password.'
    default_code = 'invalid_credentials'

class DecisionRequired(Exception):
    """An unapproved business rule must not be guessed."""

def envelope(request, code, message, fields=None):
    return {'error': {'code': code, 'message': message, 'fields': fields or {}, 'request_id': getattr(request, 'request_id', '')}}

def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # Unexpected failures remain failures, not fabricated success.
    request = context.get('request')
    fields = {}
    if isinstance(exc, NotAuthenticated):
        code, message = 'authentication_required', 'Sign in to use this endpoint.'
    elif isinstance(exc, AuthenticationFailed):
        code, message = 'invalid_authentication', 'Authentication is invalid.'
    elif isinstance(exc, PermissionDenied):
        code, message = 'forbidden', 'You are not permitted to perform this action.'
    elif isinstance(exc, ValidationError):
        code, message = 'validation_error', 'Request validation failed.'
        fields = response.data if isinstance(response.data, dict) else {'non_field_errors': response.data}
    elif isinstance(exc, ParseError):
        code, message = 'invalid_json', 'The JSON request could not be parsed.'
    else:
        code = getattr(exc, 'default_code', 'request_error')
        message = str(getattr(exc, 'detail', 'Request failed.'))
    response.data = envelope(request, code, message, fields)
    return response

def csrf_failure(request, reason=''):
    return JsonResponse(envelope(request, 'csrf_failed', 'CSRF verification failed.'), status=403)
