"""BB05 real merged login/profile/screening audit paths. Synthetic data only.
No auth/session/audit/permission provider is mocked on successful paths.
Only explicit storage-failure tests inject failures.
"""
import json
from unittest.mock import patch
from uuid import UUID, uuid4
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import OperationalError
from django.test import Client, TestCase
from audit.models import SecurityEvent
from donors.models import DonorProfile, EligibilityResult

PASSWORD = 'Synthetic-Only-Password-123'

class MergedEndpointAuditTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.owner=User.objects.create_user(email='audit-owner@example.test',password=PASSWORD)
        self.other=User.objects.create_user(email='audit-other@example.test',password=PASSWORD)
        self.profile=DonorProfile.objects.create(user=self.owner,full_name='Synthetic Audit Donor',mobile='+919876543210',blood_group='O+',location='Demo City')
        self.profile_path=f'/api/v1/donors/{self.profile.pk}'
        self.screen_path=self.profile_path+'/eligibility'
        self.body={'age_years':25,'weight_kg':'60.00','last_donation_date':None}

    def signed_client(self, actor):
        c=Client(enforce_csrf_checks=True)
        token=c.get('/api/v1/auth/csrf').json()['csrf_token']
        response=c.post('/api/v1/auth/login',{'email':actor.email,'password':PASSWORD},content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,200)
        SecurityEvent.objects.all().delete()  # test isolation only; never a production operation
        token=c.get('/api/v1/auth/csrf').json()['csrf_token']
        return c,token

    def assert_one_denial(self, actor):
        event=SecurityEvent.objects.get()
        self.assertEqual((event.event_type,event.outcome,event.actor_id),('access_denied','denied',actor.pk))
        self.assertIsInstance(event.request_id,UUID)
        self.assertIsNotNone(event.occurred_at.tzinfo)
        self.assertEqual(set(event.__dict__)-{'_state'}, {'id','occurred_at','event_type','actor_id','request_id','outcome'})
        encoded=json.dumps(list(SecurityEvent.objects.values()),default=str)
        for sensitive in [PASSWORD,self.owner.email,self.profile.mobile,self.profile.full_name,'weight_kg','last_donation_date']:
            self.assertNotIn(sensitive,encoded)

    def test_real_failed_login_has_exactly_one_allowlisted_entry(self):
        c=Client(enforce_csrf_checks=True);token=c.get('/api/v1/auth/csrf').json()['csrf_token']
        response=c.post('/api/v1/auth/login',{'email':self.owner.email,'password':'Synthetic-Wrong-Password'},content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,401)
        e=SecurityEvent.objects.get();self.assertEqual((e.event_type,e.outcome,e.actor_id),('login','failure',None))
        self.assertNotIn('Synthetic-Wrong',str(list(SecurityEvent.objects.values())))

    def test_real_successful_login_records_once(self):
        c=Client(enforce_csrf_checks=True);token=c.get('/api/v1/auth/csrf').json()['csrf_token']
        response=c.post('/api/v1/auth/login',{'email':self.owner.email,'password':PASSWORD},content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,200)
        self.assertEqual(SecurityEvent.objects.filter(event_type='login',outcome='success',actor_id=self.owner.pk).count(),1)
        self.assertEqual(c.get('/api/v1/auth/me').status_code,200)
        self.assertEqual(SecurityEvent.objects.count(),1)

    def test_profile_hidden_denial_records_exactly_once(self):
        c,_=self.signed_client(self.other)
        self.assertEqual(c.get(self.profile_path).status_code,404)
        self.assert_one_denial(self.other)

    def test_screening_hidden_denial_records_exactly_once_without_answers(self):
        c,token=self.signed_client(self.other)
        self.assertEqual(c.post(self.screen_path,self.body,content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,404)
        self.assert_one_denial(self.other)
        self.assertFalse(EligibilityResult.objects.exists())

    def test_role_denial_and_superuser_are_logged_once_each(self):
        for i,attrs in enumerate([{'role':'ADMIN'}, {'role':'REQUESTER'}, {'role':'STAFF'}, {'role':'DONOR','is_superuser':True}]):
            actor=get_user_model().objects.create_user(email=f'audit-role-{i}@example.test',password=PASSWORD,**attrs)
            c,token=self.signed_client(actor)
            self.assertEqual(c.post(self.screen_path,self.body,content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,403)
            self.assert_one_denial(actor)

    def test_nonexistent_profile_is_not_a_false_security_denial(self):
        c,token=self.signed_client(self.owner)
        path=f'/api/v1/donors/{uuid4()}'
        self.assertEqual(c.get(path).status_code,404)
        self.assertEqual(c.post(path+'/eligibility',self.body,content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,404)
        self.assertFalse(SecurityEvent.objects.exists())

    def test_authorized_owner_and_staff_success_are_not_denials(self):
        staff=get_user_model().objects.create_user(email='audit-staff@example.test',password=PASSWORD,role='STAFF')
        staff.user_permissions.add(Permission.objects.get(content_type__app_label='accounts',codename='view_donor_health'))
        for actor in [self.owner,staff]:
            c,token=self.signed_client(actor)
            self.assertEqual(c.get(self.profile_path).status_code,200)
            self.assertEqual(c.post(self.screen_path,self.body,content_type='application/json',HTTP_X_CSRFTOKEN=token).status_code,200)
            self.assertFalse(SecurityEvent.objects.exists())

    def test_invalid_screening_has_no_domain_write_or_denial(self):
        c,token=self.signed_client(self.owner)
        response=c.post(self.screen_path,{},content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,400)
        self.assertFalse(EligibilityResult.objects.exists());self.assertFalse(SecurityEvent.objects.exists())

    def test_screening_denial_audit_failure_is_redacted_503(self):
        c,token=self.signed_client(self.other)
        with patch('audit.events.SecurityEvent.objects.create',side_effect=OperationalError('PRIVATE_AUDIT_STORAGE')):
            response=c.post(self.screen_path,self.body,content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()['error']['code'],'audit_unavailable')
        self.assertNotIn('PRIVATE_AUDIT_STORAGE',response.content.decode())
        self.assertFalse(EligibilityResult.objects.exists())
