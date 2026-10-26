"""BB-01, Ankitha. POST /api/v1/auth/login. Sessions integration with Arnav (BB-02)."""
import uuid

from rest_framework.response import Response

from accounts.services.login import LoginRejected, authenticate_user
from accounts.services.sessions import establish_session  # BB-02 (Arnav)
from audit.events import record_security_event  # BB-05 (Arya)
from core.stubs import PublicPostStub


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
    # PublicPostStub already applies csrf_protect, so a bad CSRF token returns 403.
    def post(self, request, *args, **kwargs):
        request_id = _request_id(request)
        data = request.data if hasattr(request.data, 'get') else {}
        email, password = data.get('email'), data.get('password')

        fields = {}
        if not isinstance(email, str) or not email.strip():
            fields['email'] = 'This field is required.'
        if not isinstance(password, str) or not password:
            fields['password'] = 'This field is required.'
        if fields:
            return _error(request_id, 400, 'validation_error',
                          'Email and password are required.', fields)

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
