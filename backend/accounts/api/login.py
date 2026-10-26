"""BB-01, Ankitha. POST /api/v1/auth/login. Sessions integration with Arnav (BB-02)."""
import uuid

from rest_framework.response import Response

from accounts.services.login import LoginRejected, authenticate_user
from accounts.services.sessions import establish_session  # BB-02 (Arnav)
from audit.events import record_security_event  # BB-05 (Arya)
from core.stubs import PublicPostStub
from core.input_schemas import LoginInputSerializer
from core.parsers import StrictJSONParser


def _request_id(request):
    return str(getattr(request, 'request_id', None)
               or request.META.get('HTTP_X_REQUEST_ID')
               or uuid.uuid4())


def _error(request_id, status, code, message, fields=None):
    return Response(
        {'error': {'code': code, 'message': message,
                   'fields': fields or {}, 'request_id': request_id}},
        status=status)


class LoginView(PublicPostStub):
    # BB-11 reference integration. Preserve BB-01 CSRF/auth, BB-02 session and BB-05 audit.
    parser_classes = [StrictJSONParser]
    # PublicPostStub already applies csrf_protect, so a bad CSRF token returns 403.
    def post(self, request, *args, **kwargs):
        request_id = _request_id(request)
        serializer = LoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = authenticate_user(email=email, password=password)
        except LoginRejected:
            record_security_event(event_type='login', actor_id=None,
                                  request_id=request_id, outcome='failure')
            return _error(request_id, 401, 'invalid_credentials',
                          'Invalid email or password.')

        establish_session(request=request, user=user)
        record_security_event(event_type='login', actor_id=user.id,
                              request_id=request_id, outcome='success')
        return Response({
            'user': {'id': str(user.id), 'email': user.email, 'role': user.role},
            'session_expires_at': request.session.get_expiry_date().isoformat(),
        })
