"""Historical fixture evidence; explicitly not intake, issue or delivery workflows."""
from importlib.util import find_spec
from io import StringIO
import json
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from inventory.exceptions import InventoryUnavailable
from inventory.models import BloodUnit, CollectionEvent
from inventory.selectors.collection_history import latest_confirmed_collection_date
from inventory.tests.test_intake import facade_boundary_double
from donors.models import DonorProfile


@skipUnless(find_spec('core.demo_data') is not None, 'Requires shared merged dataset baseline')
@override_settings(DEBUG=True)
class HistoricalInventoryImportTests(TestCase):
    def test_dry_run_atomic_import_replay_and_conflict(self):
        dataset = Path(settings.BASE_DIR)/'datasets/synthetic/bloodconnect-demo-v1/dataset.json'
        if not dataset.exists():
            self.skipTest('Canonical shared dataset unavailable')
        out = StringIO()
        call_command('import_inventory_demo',dataset=dataset,stdout=out)
        plan = json.loads(out.getvalue())
        self.assertFalse(CollectionEvent.objects.exists())
        call_command('seed_project_demo',dataset=dataset,stdout=StringIO())
        # Missing actual donor facade must roll back the entire historical fixture import.
        with self.assertRaises(InventoryUnavailable):
            call_command('import_inventory_demo',dataset=dataset,apply=True,stdout=StringIO())
        self.assertFalse(CollectionEvent.objects.exists())
        with patch('inventory.management.commands.import_inventory_demo.record_confirmed_collection',facade_boundary_double):
            call_command('import_inventory_demo',dataset=dataset,apply=True,stdout=StringIO())
            self.assertEqual(CollectionEvent.objects.count(),plan['events'])
            self.assertEqual(BloodUnit.objects.count(),plan['units'])
            self.assertFalse(BloodUnit.objects.filter(status='ISSUED').exists())
            for donor in DonorProfile.objects.all():
                self.assertEqual(donor.last_confirmed_collection_date,
                                 latest_confirmed_collection_date(donor_id=donor.pk))
            call_command('import_inventory_demo',dataset=dataset,apply=True,stdout=StringIO())
            self.assertEqual(BloodUnit.objects.count(),plan['units'])
            unit = BloodUnit.objects.first()
            BloodUnit.objects.filter(pk=unit.pk).update(unit_code='modified-preserve')
            with self.assertRaises(CommandError):
                call_command('import_inventory_demo',dataset=dataset,apply=True,stdout=StringIO())
            unit.refresh_from_db()
            self.assertEqual(unit.unit_code,'modified-preserve')
