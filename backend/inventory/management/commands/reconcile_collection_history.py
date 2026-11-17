"""Controlled history initialization. Defaults to dry run; never lowers projection."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from donors.models import DonorProfile
from inventory.selectors.collection_history import latest_confirmed_collection_date
from inventory.services.donor_boundary import record_confirmed_collection


class Command(BaseCommand):
    help = 'Validate authoritative inventory history; --apply advances absent/lagging projections.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        checked = advanced = 0
        with transaction.atomic():
            for donor in DonorProfile.objects.select_for_update(no_key=True).order_by('id').iterator():
                checked += 1
                source = latest_confirmed_collection_date(donor_id=donor.pk)
                current = donor.last_confirmed_collection_date
                if current is not None and (source is None or current > source):
                    raise CommandError('Projection ahead of authoritative history; controlled review required.')
                if source is not None and (current is None or current < source):
                    advanced += 1
                    if options['apply']:
                        stored = record_confirmed_collection(donor_id=donor.pk, collection_date=source)
                        if stored != source:
                            raise CommandError('Projection writer returned inconsistent history.')
        self.stdout.write(f"Successful history check: checked={checked}, advances={advanced}, apply={options['apply']}")
