"""BB-06, Ankitha. Atomic donor registration. Never log validated_data (contains a password)."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException

from donors.models import DonorProfile


class DuplicateContact(APIException):
    status_code = 409
    default_detail = 'An account with this email or mobile number already exists.'
    default_code = 'duplicate_contact'


def _contact_exists(email, mobile):
    User = get_user_model()
    return (User.objects.filter(email__iexact=email).exists()
            or DonorProfile.objects.filter(mobile=mobile).exists())


def register_donor(*, validated_data: dict):
    """Atomically create donor User + DonorProfile; return profile.

    Raises DuplicateContact (409) only for a confirmed email or mobile uniqueness conflict.
    Any other database error propagates and is never reported as a duplicate.
    """
    User = get_user_model()
    email = validated_data['email']
    mobile = validated_data['mobile']

    if _contact_exists(email, mobile):
        raise DuplicateContact()

    try:
        with transaction.atomic():
            # Role is forced to DONOR here; nothing from the request can change it.
            user = User.objects.create_user(
                email=email, password=validated_data['password'], role=User.Role.DONOR)
            profile = DonorProfile.objects.create(
                user=user,
                full_name=validated_data['full_name'],
                mobile=mobile,
                blood_group=validated_data['blood_group'],
                location=validated_data['location'],
            )
    except IntegrityError:
        # The failed block was rolled back, so nothing partial exists. Only call this a
        # duplicate if a conflicting email or mobile is now confirmed to exist; a race
        # with a concurrent registration shows up this way. Otherwise re-raise the real error.
        if _contact_exists(email, mobile):
            raise DuplicateContact() from None
        raise
    return profile