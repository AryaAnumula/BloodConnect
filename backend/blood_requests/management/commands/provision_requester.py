"""BB-17 restricted local REQUESTER provisioning (BC-D017–BC-D022). No HTTP endpoint exists.

Create: requires DEBUG/local development and REQUESTER_PASSWORD in the environment (never
printed). Only a NEW account is created; an existing account's role is never changed.
Deactivate: --deactivate turns off an existing REQUESTER account. Accounts with request
history are deactivated, never deleted (requests PROTECT their requester).
"""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.validation import normalize_email


class Command(BaseCommand):
    help = 'Create (local DEBUG only) or deactivate one hospital/requester account by email.'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--deactivate', action='store_true')

    def handle(self, *args, email, deactivate, **options):
        try:
            email = normalize_email(email)
        except ValidationError:
            raise CommandError('Enter a valid email address.') from None
        User = get_user_model()
        if deactivate:
            user = User.objects.filter(email=email, role=User.Role.REQUESTER).first()
            if user is None:
                raise CommandError('No requester account with that email.')
            user.is_active = False
            user.save(update_fields=['is_active'])
            self.stdout.write(f'Deactivated requester {user.pk}.')
            return
        if not settings.DEBUG:
            raise CommandError('Requester provisioning is restricted to DEBUG/local development.')
        password = os.environ.get('REQUESTER_PASSWORD', '')
        if not password or password.startswith('CHANGE_ME'):
            raise CommandError('Set REQUESTER_PASSWORD in the environment; it will not be printed.')
        candidate = User(email=email, role=User.Role.REQUESTER)
        try:
            validate_password(password, user=candidate)
        except DjangoValidationError:
            raise CommandError('REQUESTER_PASSWORD does not meet the password policy.') from None
        with transaction.atomic():
            if User.objects.filter(email=email).exists():
                raise CommandError('An account with that email already exists; roles are never changed here.')
            user = User.objects.create_user(email=email, password=password, role=User.Role.REQUESTER)
        self.stdout.write(f'Created requester {user.pk}. Password omitted.')
