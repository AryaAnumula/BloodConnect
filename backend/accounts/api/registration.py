"""BB-06, Ankitha. POST /api/v1/auth/register. Creates donor accounts only."""
from rest_framework.response import Response

from accounts.services.registration import register_donor
from core.input_schemas import RegistrationInputSerializer
from core.parsers import StrictJSONParser
from core.stubs import PublicPostStub


class RegistrationView(PublicPostStub):
    # BB-11 shared validation: strict JSON (repeated keys rejected), strict string types,
    # unknown and privilege fields (role, is_staff, user_id, ...) rejected.
    parser_classes = [StrictJSONParser]
    # PublicPostStub applies csrf_protect, so a missing token returns 403.

    def post(self, request, *args, **kwargs):
        serializer = RegistrationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400 validation_error via core.errors
        profile = register_donor(validated_data=serializer.validated_data)
        user = profile.user
        return Response(
            {'donor_id': str(profile.id),
             'user': {'id': str(user.id), 'email': user.email, 'role': user.role}},
            status=201)