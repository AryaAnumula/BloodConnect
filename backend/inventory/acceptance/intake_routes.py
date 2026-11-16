"""Run explicitly in the shared composition; no donor adapters or test URLconf."""
from django.test import TestCase
from django.urls import resolve
from rest_framework.test import APIClient

from inventory.acceptance.fixtures import SharedApplicationFixture
from inventory.api import BloodUnitIntake
from inventory.models import BloodUnit, CollectionEvent
from inventory.pages import IntakePage


class SharedIntakeRouteChecks(SharedApplicationFixture,TestCase):
    def test_shared_routes_resolve_to_real_intake_views(self):
        self.assertIs(resolve('/api/v1/blood-units').func.view_class,BloodUnitIntake)
        self.assertIs(resolve('/staff/inventory/new').func.view_class,IntakePage)

    def test_actual_route_permissions_csrf_and_strict_shape(self):
        payload = {'unit_code':'SHARED-NEW','donor_id':str(self.donor.pk),'blood_group':'A+',
            'component_type':'RBC','collection_date':self.today.isoformat(),'quantity':1}
        anonymous = APIClient(enforce_csrf_checks=True)
        self.assertEqual(anonymous.post('/api/v1/blood-units',payload,format='json').status_code,403)
        unprotected = APIClient(enforce_csrf_checks=True)
        unprotected.force_login(self.staff)
        self.assertEqual(unprotected.post('/api/v1/blood-units',payload,format='json').status_code,403)
        staff = self.session_client(self.staff)
        self.assertEqual(staff.post('/api/v1/blood-units',payload|{'status':'ISSUED'},format='json').status_code,400)
        admin = self.session_client(self.admin)
        self.assertEqual(admin.post('/api/v1/blood-units',payload,format='json').status_code,403)
        self.assertFalse(CollectionEvent.objects.exists())
        self.assertFalse(BloodUnit.objects.exists())
        self.donor.refresh_from_db()
        self.assertIsNone(self.donor.last_confirmed_collection_date)
