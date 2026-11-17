"""DEBUG-only historical fixture loader, never an intake/issue/delivery workflow."""
from collections import defaultdict
from datetime import date, datetime
import json
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from donors.models import DonorProfile
from inventory.models import BloodUnit, CollectionEvent, InventoryDisposition
from inventory.selectors.collection_history import latest_confirmed_collection_date
from inventory.services.collection_events import validate_event_components
from inventory.services.donor_boundary import record_confirmed_collection


class Command(BaseCommand):
    help = 'Plan/import complete non-issued historical events only; accounts/profiles must already exist.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', type=Path, required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Historical demo import requires local DEBUG mode.')
        # Reuse the shared canonical validator; no expected.json or new data export.
        try:
            from core.demo_data.validate import validate
        except ModuleNotFoundError as exc:
            if exc.name not in ('core.demo_data', 'core.demo_data.validate'):
                raise
            raise CommandError('The shared dataset baseline is required.') from exc
        try:
            data = json.loads(options['dataset'].read_text(encoding='utf-8'))
            validate(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError('Invalid canonical demo dataset.') from exc
        tables = data['tables']
        units_by_event = defaultdict(list)
        for unit in tables['blood_units']:
            units_by_event[unit['collection_event_id']].append(unit)
        # Never copy fictional ISSUED state or fabricate its missing IssueRecord.
        events = [event for event in tables['collection_events'] if units_by_event[event['id']]
                  and all(unit['status'] != 'ISSUED' for unit in units_by_event[event['id']])]
        selected_units = {unit['id'] for event in events for unit in units_by_event[event['id']]}
        dispositions = {row['unit_id']: row for row in tables['inventory_dispositions'] if row['unit_id'] in selected_units}
        planned = {'events':len(events), 'units':len(selected_units), 'dispositions':len(dispositions),
                   'excluded_issued_events':len(tables['collection_events'])-len(events)}
        if not options['apply']:
            self.stdout.write(json.dumps({'mode':'historical_plan_no_writes',**planned}))
            return

        def save_new(model, identifier, defaults):
            existing = model.objects.filter(pk=identifier).first()
            if existing is not None:
                if any(getattr(existing, key) != value for key, value in defaults.items()):
                    raise CommandError('Existing inventory fixture differs; all changes rolled back.')
                return existing
            return model.objects.create(id=identifier, **defaults)

        grouped = defaultdict(list)
        for event in events:
            grouped[event['donor_id']].append(event)
        with transaction.atomic():
            for donor_id in sorted(grouped):
                try:
                    donor = DonorProfile.objects.select_for_update(no_key=True).get(pk=donor_id)
                except DonorProfile.DoesNotExist as exc:
                    raise CommandError('Seed the shared account/profile foundation first.') from exc
                source_before = latest_confirmed_collection_date(donor_id=donor.pk)
                if source_before != donor.last_confirmed_collection_date:
                    raise CommandError('Existing history projection requires reconciliation first.')
                for event_source in sorted(grouped[donor_id],key=lambda row:(row['collection_date'],row['id'])):
                    unit_sources = units_by_event[event_source['id']]
                    group = unit_sources[0]['blood_group']
                    collected = date.fromisoformat(event_source['collection_date'])
                    validate_event_components(components=[row['component_type'] for row in unit_sources])
                    if any(row['blood_group'] != group or row['donor_id'] != donor_id
                           or date.fromisoformat(row['collection_date']) != collected for row in unit_sources):
                        raise CommandError('Inconsistent event identities.')
                    if collected > timezone.localdate():
                        raise CommandError('Historical fixture is in the future; use its documented snapshot clock.')
                    event = save_new(CollectionEvent, UUID(event_source['id']), dict(donor_id=donor.pk,
                        collection_date=collected,blood_group=group,status='CONFIRMED',
                        recorded_by_id=UUID(event_source['recorded_by_id']),
                        confirmed_at=datetime.fromisoformat(event_source['confirmed_at'])))
                    for unit_source in unit_sources:
                        unit = save_new(BloodUnit, UUID(unit_source['id']), dict(
                            donor_id=donor.pk,collection_event_id=event.pk,unit_code=unit_source['unit_code'],
                            blood_group=group,component_type=unit_source['component_type'],collection_date=collected,
                            expiry_date=date.fromisoformat(unit_source['expiry_date']),quantity=1,status=unit_source['status']))
                        if unit.status in ('DISCARDED','QUARANTINED'):
                            history = dispositions.get(unit_source['id'])
                            if history is None:
                                raise CommandError('Terminal historical fixture requires explicit disposition.')
                            save_new(InventoryDisposition, UUID(history['id']), dict(unit_id=unit.pk,
                                actor_id=UUID(history['actor_id']),from_status='AVAILABLE',to_status=history['to_status'],
                                reason=history['reason_code'],occurred_at=datetime.fromisoformat(history['occurred_at'])))
                latest = latest_confirmed_collection_date(donor_id=donor.pk)
                if latest is not None and record_confirmed_collection(donor_id=donor.pk,collection_date=latest) != latest:
                    raise CommandError('Projection writer returned inconsistent history.')
        self.stdout.write(json.dumps({'mode':'historical_fixture_not_workflow_evidence',**planned,
            'identity_mapping':'source UUIDs retained; event group derived from validated linked units'}))
