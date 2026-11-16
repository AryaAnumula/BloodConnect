import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from core.errors import DecisionRequired
from notification_adapter.demo import queue_dataset_reminders


class Command(BaseCommand):
    help = 'Queue fresh on-time/late reminders and donor cancellation from PR62 identities in a local demo DB.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', type=Path, required=True)

    def handle(self, *args, **options):
        try:
            result = queue_dataset_reminders(dataset=options['dataset'])
        except (DecisionRequired, IntegrityError) as error:
            raise CommandError('Demo policy/data collision; no partial import or delivery was performed.') from error
        self.stdout.write(json.dumps(result))
