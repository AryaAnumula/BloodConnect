"""BB-21 slot endpoints: POST/GET /api/v1/appointment-slots. Role check precedes validation."""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.parsers import StrictJSONParser
from scheduling.permissions import require_camp_role
from scheduling.selectors.slots import list_slots
from scheduling.services.slots import create_slot
from scheduling.slot_inputs import SlotCreateInputSerializer, SlotListInputSerializer


@method_decorator(csrf_protect, name='dispatch')
class SlotCollectionView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [StrictJSONParser]

    def get(self, request, *args, **kwargs):
        require_camp_role(user=request.user, action='slot_list')
        query = SlotListInputSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = dict(query.validated_data)
        page, page_size = params.pop('page'), params.pop('page_size')
        return Response(list_slots(actor=request.user, filters=params, page=page,
                                   page_size=page_size))

    def post(self, request, *args, **kwargs):
        require_camp_role(user=request.user, action='slot_create')
        serializer = SlotCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(create_slot(actor=request.user, data=serializer.validated_data),
                        status=201)
