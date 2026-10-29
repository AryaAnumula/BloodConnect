"""D-09 provisioning: maintainer-operated only. No HTTP endpoint, no public assignment."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Grant or revoke accounts.view_donor_health for one active STAFF account (by UUID).'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', required=True)
        parser.add_argument('--revoke', action='store_true')

    def handle(self, *args, user_id, revoke, **options):
        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
            perm = Permission.objects.get(content_type__app_label='accounts',
                                          codename='view_donor_health')
        except (User.DoesNotExist, ValueError, ValidationError):
            raise CommandError('No such account.') from None
        except Permission.DoesNotExist:
            raise CommandError('Permission missing; run migrations first.') from None
        if revoke:
            user.user_permissions.remove(perm)
            self.stdout.write(f'Revoked view_donor_health from {user.pk}.')
            return
        if user.role != User.Role.STAFF or not user.is_active or user.is_superuser:
            raise CommandError('Only an active, non-superuser STAFF account may be granted this.')
        user.user_permissions.add(perm)
        self.stdout.write(f'Granted view_donor_health to {user.pk}.')