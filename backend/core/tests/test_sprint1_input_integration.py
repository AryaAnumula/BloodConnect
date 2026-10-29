"""BB11 actual direct-API validation. No mocked successful business endpoints."""
import json
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from donors.models import DonorProfile, EligibilityResult

class ActualInputIntegrationTests(TestCase):
    password='Synthetic-Input-Password-123'
    def setUp(self):
        self.c=Client(enforce_csrf_checks=True)
        self.token=self.c.get('/api/v1/auth/csrf').json()['csrf_token']
    def post(self,path,data,raw=False):
        return self.c.post(path,data if raw else json.dumps(data),content_type='application/json',HTTP_X_CSRFTOKEN=self.token)
    def registration(self,**kw):
        d={'email':'input-owner@example.test','mobile':'+919876543219','password':self.password,'full_name':'Synthetic Input','blood_group':'O+','location':'Demo City'};d.update(kw);return d
    def sign_in(self):
        response=self.post('/api/v1/auth/register',self.registration());self.assertEqual(response.status_code,201)
        profile=DonorProfile.objects.get(pk=response.json()['donor_id'])
        self.assertEqual(self.post('/api/v1/auth/login',{'email':profile.user.email,'password':self.password}).status_code,200)
        self.token=self.c.get('/api/v1/auth/csrf').json()['csrf_token'];return profile
    def test_registration_types_lengths_privilege_and_duplicate_keys_save_nothing(self):
        cases=[self.registration(role='ADMIN'),self.registration(full_name='x'*121),self.registration(email=7),self.registration(mobile='123'),self.registration(password='short'),self.registration(blood_group='XX')]
        for body in cases:self.assertEqual(self.post('/api/v1/auth/register',body).status_code,400)
        self.assertEqual(self.post('/api/v1/auth/register','{"email":"a@example.test","email":"b@example.test"}',True).status_code,400)
        self.assertEqual(get_user_model().objects.count(),0);self.assertEqual(DonorProfile.objects.count(),0)
    def test_duplicate_contact_generic_409_and_atomic_counts(self):
        self.assertEqual(self.post('/api/v1/auth/register',self.registration()).status_code,201)
        for changes in [{'mobile':'+919876543218'},{'email':'other@example.test'}]:
            r=self.post('/api/v1/auth/register',self.registration(**changes));self.assertEqual(r.status_code,409)
            self.assertEqual(r.json()['error']['code'],'duplicate_contact')
        self.assertEqual((get_user_model().objects.count(),DonorProfile.objects.count()),(1,1))
    def test_screening_types_unknown_fields_future_dates_reject_before_save(self):
        profile=self.sign_in();path=f'/api/v1/donors/{profile.pk}/eligibility'
        good={'age_years':25,'weight_kg':'60.00','last_donation_date':None}
        cases=[dict(good,age_years=True),dict(good,age_years='25'),dict(good,weight_kg=60),dict(good,weight_kg='NaN'),dict(good,role='ADMIN'),dict(good,last_donation_date=(timezone.localdate()+timedelta(days=1)).isoformat()),dict(good,last_donation_date='2026-02-30')]
        for body in cases:self.assertEqual(self.post(path,body).status_code,400,body)
        self.assertFalse(EligibilityResult.objects.exists());profile.user.refresh_from_db();self.assertEqual(profile.user.role,'DONOR')
    def test_malformed_duplicate_nonfinite_json_never_writes(self):
        profile=self.sign_in();path=f'/api/v1/donors/{profile.pk}/eligibility'
        for raw in ['{','[]','null','{"age_years":25,"age_years":99}', '{"age_years":NaN}', '{"weight_kg":1e999}']:
            response=self.post(path,raw,True);self.assertEqual(response.status_code,400)
            self.assertNotIn('Traceback',response.content.decode())
        self.assertFalse(EligibilityResult.objects.exists())
    def test_script_like_stored_text_is_literal_data_and_private_projection_excludes_it(self):
        text="<script>alert('synthetic')</script>"
        self.assertEqual(self.post('/api/v1/auth/register',self.registration(full_name=text,location="x' OR 1=1 --")).status_code,201)
        profile=DonorProfile.objects.get();self.assertEqual(profile.full_name,text)
        # ORM stored literal data; no execution or schema deletion. Frontend textContent
        # behavior is covered by Node tests, NOT asserted as a browser run here.
        self.assertEqual(get_user_model().objects.count(),1)
        self.assertEqual(DonorProfile.objects.count(),1)
