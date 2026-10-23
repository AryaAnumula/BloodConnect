"""BB-03 health-contract checks; no operational availability claim."""
from unittest.mock import patch
from django.db import OperationalError
from rest_framework.test import APITestCase


class HealthMonitoringTests(APITestCase):
    def test_readiness_is_public_and_matches_contract(self):
        response = self.client.get('/api/v1/health/ready')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),{'status':'ready','checks':{'database':'ok'}})

    def test_database_failure_is_redacted_503(self):
        with patch('core.health.connection.cursor',side_effect=OperationalError('PRIVATE_SYNTHETIC_DATABASE_DETAIL')):
            response=self.client.get('/api/v1/health/ready')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json(),{'status':'not_ready','checks':{'database':'unavailable'}})
        self.assertNotIn('PRIVATE_SYNTHETIC',response.content.decode())

    def test_liveness_does_not_depend_on_database(self):
        with patch('core.health.connection.cursor',side_effect=OperationalError('PRIVATE_SYNTHETIC_DATABASE_DETAIL')) as cursor:
            response=self.client.get('/api/v1/health/live')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['scope'],'process_only')
        cursor.assert_not_called()

    def test_health_endpoints_reject_mutation(self):
        for endpoint in ['/api/v1/health/live','/api/v1/health/ready']:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.post(endpoint,{},format='json').status_code,405)
