from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from donors.models import DonorProfile


class DemoSessionUiTests(TestCase):
    def setUp(self):
        self.donor = get_user_model().objects.create_user(
            email='demo-donor@example.test', password='local-test-password', role='DONOR')
        self.profile = DonorProfile.objects.create(
            user=self.donor, full_name='Demo Donor', mobile='+919876543210',
            blood_group='O+', location='Example')
        self.staff = get_user_model().objects.create_user(
            email='demo-staff@example.test', password='local-test-password', role='STAFF')

    def test_donor_pages_fill_only_the_signed_in_donors_profile(self):
        self.client.force_login(self.donor)
        for path in ['/screening', '/eligibility']:
            response = self.client.get(path)
            self.assertContains(response, f'value="{self.profile.pk}" readonly')
            self.assertContains(response, 'Your donor profile ID is filled in automatically.')
            self.assertContains(response, 'id="session-logout"')

    def test_staff_can_enter_profile_and_cannot_see_donor_id_automatically(self):
        self.client.force_login(self.staff)
        for path in ['/screening', '/eligibility']:
            response = self.client.get(path)
            self.assertNotContains(response, str(self.profile.pk))
            self.assertNotContains(response, 'readonly')
        for path in ['/staff/inventory/new', '/staff/inventory', '/staff/inventory/alerts']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'id="session-logout"')

    def test_unauthenticated_pages_do_not_reveal_profile_or_logout(self):
        for path in ['/screening', '/eligibility']:
            response = self.client.get(path)
            self.assertNotContains(response, str(self.profile.pk))
            self.assertNotContains(response, 'id="session-logout"')

    def test_logout_api_with_real_csrf_token_invalidates_session(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.donor)
        token = client.get('/api/v1/auth/csrf').json()['csrf_token']
        self.assertEqual(client.post('/api/v1/auth/logout', HTTP_X_CSRFTOKEN=token).status_code, 204)
        self.assertEqual(client.get('/api/v1/auth/me').status_code, 403)
        self.assertNotContains(client.get('/screening'), str(self.profile.pk))
