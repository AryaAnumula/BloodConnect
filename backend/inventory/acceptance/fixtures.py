"""Synthetic historical fixtures, not fresh-donation acceptance or donor adapters."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from donors.models import DonorProfile
from inventory.configuration import shelf_life_policy
from inventory.models import BloodUnit, CollectionEvent


class SharedApplicationFixture:
    def setUp(self):
        super().setUp()
        self.assertEqual(settings.ROOT_URLCONF,'config.urls',
            'Use the actual shared application routes, not an inventory test URL override.')
        User = get_user_model()
        self.staff = User.objects.create_user(email='shared-staff@inventory.test',role='STAFF')
        self.admin = User.objects.create_user(email='shared-admin@inventory.test',role='ADMIN')
        user = User.objects.create_user(email='shared-donor@inventory.test',role='DONOR')
        self.donor = DonorProfile.objects.create(user=user,full_name='Synthetic shared-route donor',
            mobile='+919099999941',blood_group='A+',location='Synthetic shared application')
        self.today = timezone.localdate()

    def session_client(self,actor):
        """Real persisted session + actual CSRF endpoint; login browser evidence is separate."""
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(actor)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        client.credentials(HTTP_X_CSRFTOKEN=token)
        return client

    def historical_units(self):
        """A labelled coherent historical event with three separated components."""
        collected = self.today-timedelta(days=4)
        policy = shelf_life_policy()
        with transaction.atomic():
            donor = DonorProfile.objects.select_for_update(no_key=True).get(pk=self.donor.pk)
            donor.last_confirmed_collection_date = collected
            donor.save(update_fields=['last_confirmed_collection_date'])
            event = CollectionEvent.objects.create(donor=donor,collection_date=collected,
                blood_group='A+',recorded_by=self.staff)
            units = {component:BloodUnit.objects.create(unit_code='SHARED-'+component,
                donor=donor,collection_event=event,blood_group='A+',component_type=component,
                collection_date=collected,expiry_date=collected+timedelta(days=policy[component]))
                for component in ('RBC','PLASMA','PLATELETS')}
        return event,units
