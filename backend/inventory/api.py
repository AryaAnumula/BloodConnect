from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.parsers import StrictJSONParser
from inventory.permissions import IsInventoryStaff, IsStockReader
from inventory.serializers import StockQuery
from inventory.selectors.units import unit_list, unit_detail
from inventory.selectors.stock import stock_summary
from inventory.services.dispositions import record_disposition
from inventory.services.units import record_unit


class BloodUnitIntake(APIView):
    permission_classes = [IsAuthenticated, IsInventoryStaff]
    parser_classes = [StrictJSONParser]

    def post(self, request):
        return Response(record_unit(actor=request.user, data=request.data), status=201)

    def get(self, request):
        return Response(unit_list(actor=request.user, filters=request.query_params))


class UnitDetail(APIView):
    permission_classes = [IsAuthenticated, IsInventoryStaff]

    def get(self, request, unit_id):
        return Response(unit_detail(actor=request.user, unit_id=unit_id))


class UnitDisposition(APIView):
    permission_classes = [IsAuthenticated, IsInventoryStaff]
    parser_classes = [StrictJSONParser]

    def post(self, request, unit_id):
        return Response(record_disposition(actor=request.user, unit_id=unit_id, data=request.data))


class StockView(APIView):
    permission_classes = [IsAuthenticated, IsStockReader]

    def get(self, request):
        query = StockQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = dict(query.validated_data)
        page, size = values.pop('page'), values.pop('page_size')
        return Response(stock_summary(actor=request.user, filters=values, page=page, page_size=size))
