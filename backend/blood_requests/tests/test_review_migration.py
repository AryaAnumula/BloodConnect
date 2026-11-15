"""BB-18 migration 0002 upgrades existing BB-17 rows without inventing reviewers."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [('blood_requests', '0001_initial')]
AFTER = [('blood_requests', '0002_bloodrequest_reviewed_at_bloodrequest_reviewed_by')]


class ReviewMigrationUpgradeTests(TransactionTestCase):
    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())  # leave the schema fully migrated

    def test_existing_bb17_rows_keep_null_review_metadata(self):
        executor = MigrationExecutor(connection)
        executor.migrate(BEFORE)
        old_apps = executor.loader.project_state(BEFORE).apps
        User = old_apps.get_model('accounts', 'User')
        OldRequest = old_apps.get_model('blood_requests', 'BloodRequest')
        requester = User.objects.create(email='migration-requester@example.test', role='REQUESTER')
        old = OldRequest.objects.create(requester=requester, blood_group='B+', component_type='PLATELETS',
                                        quantity=4, urgency_level='URGENT', status='SUBMITTED')
        decided = OldRequest.objects.create(requester=requester, blood_group='B+', component_type='RBC',
                                            quantity=1, urgency_level='ROUTINE', status='APPROVED')

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(AFTER)
        new_apps = executor.loader.project_state(AFTER).apps
        NewRequest = new_apps.get_model('blood_requests', 'BloodRequest')
        for row_id, status in ((old.pk, 'SUBMITTED'), (decided.pk, 'APPROVED')):
            row = NewRequest.objects.get(pk=row_id)
            self.assertEqual((row.status, row.reviewed_by_id, row.reviewed_at, row.requester_id),
                             (status, None, None, requester.pk))
