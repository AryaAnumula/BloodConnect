"""Local synthetic accounts only. No passwords in the repository or command output."""
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Create local synthetic role fixtures; requires DEBUG and DEMO_USER_PASSWORD.'
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Synthetic seeding is restricted to DEBUG/local development.')
        password = os.environ.get('DEMO_USER_PASSWORD', '')
        if len(password) < 12 or password.startswith('CHANGE_ME'):
            raise CommandError('Set a generated local DEMO_USER_PASSWORD; it will not be printed.')
        User = get_user_model()
        for role in User.Role.values:
            email = f'{role.lower()}@example.test'
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(email=email, password=password, role=role)
        self.stdout.write('Synthetic role accounts exist. Password omitted. No clinical permissions granted automatically.')
