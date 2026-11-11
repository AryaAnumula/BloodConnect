"""BB-20 camp endpoints. Role gates are the PROPOSED S2-04 matrix (see scheduling.permissions).

POST/GET /api/v1/camps and PATCH /api/v1/camps/{camp_id}. Cancel (POST .../cancel) is NOT built:
it waits for S2-05/S2-06 approval and the BB-21 appointment model.
"""
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.parsers import StrictJSONParser
from scheduling.camp_inputs import (CampCreateInputSerializer, CampListInputSerializer,
                                    CampUpdateInputSerializer)
from scheduling.permissions import require_camp_role
from scheduling.selectors.camps import list_camps
from scheduling.services.camps import create_camp, update_camp


@method_decorator(csrf_protect, name='dispatch')
class CampCollectionView(APIView):
    # Anonymous: 403 authentication_required. Wrong role: 403 forbidden, checked BEFORE validation.
    permission_classes = [IsAuthenticated]
    parser_classes = [StrictJSONParser]

    def get(self, request, *args, **kwargs):
        require_camp_role(user=request.user, action='list')
        query = CampListInputSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        return Response(list_camps(
            actor=request.user, filters={'status': params.get('status')},
            page=params['page'], page_size=params['page_size']))

    def post(self, request, *args, **kwargs):
        require_camp_role(user=request.user, action='create')
        serializer = CampCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(create_camp(actor=request.user, data=serializer.validated_data),
                        status=201)


@method_decorator(csrf_protect, name='dispatch')
class CampDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [StrictJSONParser]

    def patch(self, request, camp_id, *args, **kwargs):
        require_camp_role(user=request.user, action='update')
        serializer = CampUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(update_camp(actor=request.user, camp_id=camp_id,
                                    data=serializer.validated_data))
