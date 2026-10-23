from django.db import connection, DatabaseError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def live(request):
    return Response({'status': 'ok', 'scope': 'process_only', 'business_features': 'not_implemented'})

@api_view(['GET'])
@permission_classes([AllowAny])
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except DatabaseError:
        return Response({'status': 'not_ready', 'checks': {'database': 'unavailable'}}, status=503)
    return Response({'status': 'ready', 'checks': {'database': 'ok'}})
