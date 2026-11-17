from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class SeederGuardBoundaryTests(SimpleTestCase):
    @override_settings(DEBUG=False)
    def test_seeders_refuse_non_debug(self):
        for command in ('seed_project_demo', 'import_inventory_demo'):
            kwargs = {'dataset': Path('missing.json')} if command == 'import_inventory_demo' else {}
            with self.subTest(command=command), self.assertRaises(CommandError):
                call_command(command, stdout=StringIO(), **kwargs)

    @override_settings(DEBUG=True)
    def test_seeders_reject_missing_or_invalid_dataset(self):
        with TemporaryDirectory() as directory:
            bad = Path(directory) / 'bad.json'
            bad.write_text('not-json')
            for command in ('seed_project_demo', 'import_inventory_demo'):
                for path in (bad, Path(directory) / 'missing.json'):
                    with self.subTest(command=command, path=path), self.assertRaises(CommandError):
                        call_command(command, dataset=path, stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_project_seeder_rejects_invalid_password_and_policy_mismatch(self):
        data = {'policy': {'rules_version': 'fixture', 'min_age_years': 1, 'max_age_years': 2,
                           'min_weight_kg': 3, 'min_days_between_donations': 4}}
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.json'
            import json
            path.write_text(json.dumps(data))
            with patch('core.management.commands.seed_project_demo.validate'), patch.dict('os.environ', {'BAD_DEMO_PASSWORD': 'short'}):
                with self.assertRaises(CommandError):
                    call_command('seed_project_demo', dataset=path, password_env='BAD_DEMO_PASSWORD', stdout=StringIO())
            mismatched = dict(data['policy'], min_age_years=99)
            with patch('core.management.commands.seed_project_demo.validate'), patch('core.management.commands.seed_project_demo.approved_screening_rules', return_value=mismatched):
                with self.assertRaises(CommandError):
                    call_command('seed_project_demo', dataset=path, stdout=StringIO())
