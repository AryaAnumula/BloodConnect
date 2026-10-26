"""BB-02, Arnav. POST /api/v1/auth/logout: invalidate the current session."""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.sessions import end_session


@method_decorator(csrf_protect, name='dispatch')
class LogoutView(APIView):
    # Same gates as the original stub: CSRF first, then a signed-in session.
    # Missing, invalid or expired sessions get the standard 403 envelope.
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        end_session(request=request._request)
        return Response(status=204)