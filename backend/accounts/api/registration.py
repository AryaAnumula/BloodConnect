"""BB-06, Ankitha. POST /api/v1/auth/register. Creates donor accounts only."""
from rest_framework import serializers
from rest_framework.response import Response

from accounts.services.registration import register_donor
from core.stubs import PublicPostStub
from donors.models import DonorProfile


class RegistrationSerializer(serializers.Serializer):
    # PROPOSED rules per docs/api/openapi.yaml; D-04 and D-05 approval pending.
    email = serializers.EmailField(max_length=254)
    mobile = serializers.RegexField(
        r'^\+[1-9][0-9]{7,14}$', max_length=16,
        error_messages={'invalid': 'Use international format, for example +919876543210.'})
    password = serializers.CharField(min_length=12, write_only=True, trim_whitespace=False)
    full_name = serializers.CharField(min_length=1, max_length=120)
    blood_group = serializers.ChoiceField(choices=DonorProfile.BloodGroup.values)
    location = serializers.CharField(min_length=1, max_length=120)

    def validate_email(self, value):
        return value.strip().lower()

    def to_internal_value(self, data):
        # Reject unknown fields (role, is_staff, user_id, ...) instead of silently ignoring them.
        if hasattr(data, 'keys'):
            unknown = set(data.keys()) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {name: ['This field is not allowed.'] for name in sorted(unknown)})
        return super().to_internal_value(data)


class RegistrationView(PublicPostStub):
    # PublicPostStub applies csrf_protect, so a missing token returns 403.
    def post(self, request, *args, **kwargs):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400 validation_error via core.errors
        profile = register_donor(validated_data=serializer.validated_data)
        user = profile.user
        return Response(
            {'donor_id': str(profile.id),
             'user': {'id': str(user.id), 'email': user.email, 'role': user.role}},
            status=201)