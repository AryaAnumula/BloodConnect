from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@never_cache
@api_view(['GET'])
@permission_classes([AllowAny])
def csrf(request):
    return Response({'csrf_token': get_token(request)})
