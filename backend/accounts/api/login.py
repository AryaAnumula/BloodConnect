"""BB-01, Ankitha. POST /api/v1/auth/login. Session: BB-02 (Arnav). Audit: BB-05 (Arya)."""
import uuid

from rest_framework.response import Response

from accounts.services.login import LoginRejected, authenticate_user
from accounts.services.sessions import end_session, establish_session
from audit.events import record_security_event
from core.stubs import PublicPostStub
from core.input_schemas import LoginInputSerializer
from core.parsers import StrictJSONParser


def _request_id(request):
    # The request-id middleware always sets a valid UUID; uuid4 is only a safety net.
    return str(getattr(request, 'request_id', None) or uuid.uuid4())


def _error(request_id, status, code, message, fields=None):
    return Response(
        {'error': {'code': code, 'message': message,
                   'fields': fields or {}, 'request_id': request_id}},
        status=status)


class LoginView(PublicPostStub):
    # BB-11 reference integration. Preserve BB-01 CSRF/auth, BB-02 session and BB-05 audit.
    parser_classes = [StrictJSONParser]
    # PublicPostStub applies csrf_protect, so a bad CSRF token returns 403 before anything else.

    def post(self, request, *args, **kwargs):
        request_id = _request_id(request)
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = authenticate_user(email=email, password=password)
        except LoginRejected:
            # The one login-failure audit hook (BB-05). AuditUnavailable propagates as 503.
            record_security_event(event_type='login', actor_id=None,
                                  request_id=request_id, outcome='failure')
            return _error(request_id, 401, 'invalid_credentials',
                          'Invalid email or password.')

        try:
            establish_session(request=request, user=user)
            # Success is recorded only AFTER the session exists.
            record_security_event(event_type='login', actor_id=user.id,
                                  request_id=request_id, outcome='success')
        except Exception:
            # Session or audit failed: leave no usable session, never fake success.
            end_session(request=request)
            raise

        return Response({
            'user': {'id': str(user.id), 'email': user.email, 'role': user.role},
            'session_expires_at': request.session.get_expiry_date().isoformat(),
        })
