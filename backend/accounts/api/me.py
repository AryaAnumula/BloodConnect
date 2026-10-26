"""BB-04, Arnav. GET /api/v1/auth/me: current account metadata, never health data."""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


@method_decorator(csrf_protect, name='dispatch')
class MeView(APIView):
    # Same gates as the original stub. Anonymous, invalid and expired sessions
    # get the standard 403 authentication_required envelope.
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        # Exactly the AuthUser schema fields; nothing else is ever returned.
        return Response({'id': str(user.pk), 'email': user.email, 'role': user.role})