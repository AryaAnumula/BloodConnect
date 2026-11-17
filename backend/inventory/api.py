from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.parsers import StrictJSONParser
from inventory.permissions import IsInventoryStaff
from inventory.services.units import record_unit


class BloodUnitIntake(APIView):
    permission_classes = [IsAuthenticated, IsInventoryStaff]
    parser_classes = [StrictJSONParser]

    def post(self, request):
        return Response(record_unit(actor=request.user, data=request.data), status=201)
