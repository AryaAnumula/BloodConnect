"""Fail-closed routing placeholders; no story is complete because a route exists."""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from .errors import FeatureNotImplemented

@method_decorator(csrf_protect, name='dispatch')
class PublicPostStub(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        raise FeatureNotImplemented()

@method_decorator(csrf_protect, name='dispatch')
class AuthenticatedGetStub(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        raise FeatureNotImplemented()

@method_decorator(csrf_protect, name='dispatch')
class AuthenticatedPostStub(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        raise FeatureNotImplemented()
