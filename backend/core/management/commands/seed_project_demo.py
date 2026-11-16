"""Explicit local fixture import for existing models; no fabricated missing app history."""
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from blood_requests.models import BloodRequest
from core.demo_data.generate import LOCAL, uid
from core.demo_data.validate import validate
from donors.configuration import approved_screening_rules
from donors.models import DonorProfile, EligibilityResult
from donors.services.evaluation import evaluate


class Command(BaseCommand):
    help = 'Seed a local demo foundation: accounts, profiles, uncollected screenings and non-issued requests.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset', type=Path, default=Path(settings.BASE_DIR)/'datasets/synthetic/bloodconnect-demo-v1/dataset.json')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--password-env', help='Optional env var for the four demo_login accounts only; other new passwords unusable.')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Synthetic seeding requires local DEBUG mode.')
        try:
            data = json.loads(Path(options['dataset']).read_text(encoding='utf-8'))
            validate(data)
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise CommandError('Dataset is invalid or unavailable; run the standalone validator.') from error
        password = os.environ.get(options['password_env'], '') if options['password_env'] else None
        if password is not None and (len(password) < 12 or password.startswith('CHANGE_ME')):
            raise CommandError('Configured local demo password is missing or too short; value omitted.')
        rules = approved_screening_rules()
        for field in ('min_age_years', 'max_age_years', 'min_weight_kg', 'min_days_between_donations'):
            if rules[field] != data['policy'][field]:
                raise CommandError('Fixture screening settings differ from live demo rules; no import performed.')
        tables = data['tables']
        accounts = [u for u in tables['accounts'] if not u['is_superuser']]
        donors = tables['donors']
        uncollected = {d['id'] for d in donors if d['last_confirmed_collection_date'] is None}
        screens = {s['donor_id']: s for s in sorted(tables['screenings'], key=lambda r: r['assessed_at']) if s['donor_id'] in uncollected}
        requests = [r for r in tables['blood_requests'] if r['fulfilled_quantity'] == 0 and r['status'] in ('SUBMITTED', 'APPROVED', 'REJECTED')]
        planned = dict(accounts=len(accounts), donors=len(donors), screenings=len(screens), blood_requests=len(requests))
        if options['dry_run']:
            self.stdout.write(json.dumps(dict(mode='foundation_plan_no_writes', planned=planned,
                                             deferred='All collection/unit/issue/scheduling/notification/alert history; issued or partially fulfilled requests.')))
            return
        created = dict.fromkeys(planned, 0)

        def save_new(model, identifier, defaults):
            existing = model.objects.filter(pk=identifier).first()
            if existing is not None:
                for key, value in defaults.items():
                    if str(getattr(existing, key)) != str(value):
                        raise CommandError('Existing demo record differs; preserved. Use a separate fresh demo database.')
                return existing, False
            return model.objects.create(id=identifier, **defaults), True

        try:
            with transaction.atomic():
                User = get_user_model()
                for source in accounts:
                    defaults = {k: source[k] for k in ('email', 'role', 'is_active', 'is_superuser', 'is_staff')}
                    existing = User.objects.filter(pk=source['id']).first()
                    if existing is not None:
                        save_new(User, source['id'], defaults)
                        continue  # Never reset an existing password or identity.
                    user = User(id=source['id'], **defaults)
                    if password and source['demo_login']:
                        user.set_password(password)
                    else:
                        user.set_unusable_password()
                    user.save(force_insert=True)
                    created['accounts'] += 1
                for source in donors:
                    defaults = {k: source[k] for k in ('user_id', 'full_name', 'mobile', 'blood_group', 'location')}
                    _, fresh = save_new(DonorProfile, source['id'], defaults)
                    created['donors'] += fresh
                for donor_id, source in screens.items():
                    last_date = datetime.fromisoformat(source['last_donation_date']).date() if source['last_donation_date'] else None
                    assessment_date = datetime.fromisoformat(source['assessed_at']).astimezone(LOCAL).date()
                    status, codes, reasons = evaluate(age_years=source['age_years'], weight_kg=Decimal(source['weight_kg']),
                                                      last_donation_date=last_date, today=assessment_date, rules=rules)
                    defaults = dict(donor_id=donor_id, age_years=source['age_years'], weight_kg=Decimal(source['weight_kg']),
                                    last_donation_date=last_date, status=status, reason_codes=codes, reasons=reasons,
                                    rules_version=rules['rules_version'])
                    row, fresh = save_new(EligibilityResult, uid('foundation-screening', donor_id), defaults)
                    assessed_at = datetime.fromisoformat(source['assessed_at'])
                    if fresh:
                        EligibilityResult.objects.filter(pk=row.pk).update(assessed_at=assessed_at)
                    elif row.assessed_at != assessed_at:
                        raise CommandError('Existing demo record differs; preserved. Use a separate fresh demo database.')
                    created['screenings'] += fresh
                for source in requests:
                    defaults = {k: source[k] for k in ('requester_id', 'blood_group', 'component_type', 'quantity',
                                                       'fulfilled_quantity', 'urgency_level', 'status', 'rejection_reason', 'reviewed_by_id')}
                    defaults['reviewed_at'] = datetime.fromisoformat(source['reviewed_at']) if source['reviewed_at'] else None
                    row, fresh = save_new(BloodRequest, source['id'], defaults)
                    if fresh:
                        BloodRequest.objects.filter(pk=row.pk).update(created_at=source['created_at'], updated_at=source['updated_at'])
                    created['blood_requests'] += fresh
        except IntegrityError as error:
            raise CommandError('Demo identity/data collision; entire import rolled back, no existing records overwritten.') from error
        self.stdout.write(json.dumps(dict(mode='foundation_only', planned=planned, created=created,
                                         password='omitted; only four new demo_login accounts may be enabled',
                                         deferred='Full source history remains in dataset.json/CSV; no missing app models were invented.')))
