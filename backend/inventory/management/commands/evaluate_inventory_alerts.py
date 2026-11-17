from uuid import UUID
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings
from django.utils import timezone

from inventory.services.alerts import evaluate_alerts


class Command(BaseCommand):
    help = 'Evaluate configured inventory alert episodes. Does not dispatch notifications.'

    def add_arguments(self, parser):
        parser.add_argument('--actor-id', required=True, type=UUID)
        parser.add_argument('--recipient-id', type=UUID)

    def handle(self, *args, **options):
        try:
            actor = get_user_model().objects.get(pk=options['actor_id'])
        except get_user_model().DoesNotExist:
            raise CommandError('Operational actor not found.') from None
        config = ({'INVENTORY_ALERT_RECIPIENT_ID': str(options['recipient_id'])}
                  if options['recipient_id'] else {})
        with override_settings(**config):
            self.stdout.write(str(evaluate_alerts(actor=actor, now=timezone.now())))
