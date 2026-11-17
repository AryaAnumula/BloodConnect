"""Upgrade a disposable existing donor database, preserving its assessment history."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from donors.models import DonorProfile, EligibilityResult
from inventory.tests.test_intake import InventoryFixture


class ExistingDatabaseMigrationTests(InventoryFixture, TransactionTestCase):
    def test_inventory_upgrade_preserves_existing_donor_and_assessment(self):
        donor_id, result_id = self.donor.pk, self.assessment.pk
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([('inventory', None)])
            self.assertTrue(DonorProfile.objects.filter(pk=donor_id).exists())
            self.assertTrue(EligibilityResult.objects.filter(pk=result_id).exists())
        finally:
            MigrationExecutor(connection).migrate(targets)
        self.assertTrue(DonorProfile.objects.filter(pk=donor_id).exists())
        self.assertTrue(EligibilityResult.objects.filter(pk=result_id).exists())
