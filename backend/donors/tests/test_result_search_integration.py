"""BB08/09 real HTTP/ORM screening consumers. No mocked runtime providers.
Registration, login, CSRF, permissions, screening config/history, result reader,
search and audit are actual merged implementations. Synthetic example.test only.
"""
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import OperationalError
from django.test import Client, TestCase
from django.utils import timezone
from audit.models import SecurityEvent
from donors.models import DonorProfile, EligibilityResult

PASSWORD='Synthetic-Only-Password-123'
class RealResultSearchTests(TestCase):
    def csrf(self,c): return c.get('/api/v1/auth/csrf').json()['csrf_token']
    def post(self,c,path,data): return c.post(path,data,content_type='application/json',HTTP_X_CSRFTOKEN=self.csrf(c))
    def account(self,email,mobile,group='O+',location='Bengaluru'):
        c=Client(enforce_csrf_checks=True)
        response=self.post(c,'/api/v1/auth/register',{'email':email,'mobile':mobile,'password':PASSWORD,'full_name':'Synthetic Donor','blood_group':group,'location':location})
        self.assertEqual(response.status_code,201)
        response=self.post(c,'/api/v1/auth/login',{'email':email,'password':PASSWORD});self.assertEqual(response.status_code,200)
        return c,DonorProfile.objects.get(user__email=email)
    def staff_client(self):
        user=get_user_model().objects.create_user(email='real-staff@example.test',password=PASSWORD,role='STAFF')
        user.user_permissions.add(Permission.objects.get(content_type__app_label='accounts',codename='view_donor_health'))
        c=Client(enforce_csrf_checks=True)
        self.assertEqual(self.post(c,'/api/v1/auth/login',{'email':user.email,'password':PASSWORD}).status_code,200)
        return c
    def setUp(self):
        self.owner,self.a=self.account('real-owner@example.test','+919876543210')
        self.other,self.b=self.account('real-other@example.test','+919876543211','A+','Hyderabad')
        self.staff=self.staff_client()
        self.path=f'/api/v1/donors/{self.a.pk}/eligibility'
        self.result_path=self.path+'/result'
        SecurityEvent.objects.all().delete()  # isolate test evidence only, never runtime cleanup
    def screen(self,c=None,path=None,age=25,weight='60.00',last=None):
        return self.post(c or self.owner,path or self.path,{'age_years':age,'weight_kg':weight,'last_donation_date':last})
    def test_real_registration_login_screen_result_and_combined_search(self):
        response=self.screen();self.assertEqual(response.status_code,200)
        result=self.owner.get(self.result_path);self.assertEqual(result.status_code,200)
        from django.utils.dateparse import parse_datetime
        saved=dict(result.json());created=dict(response.json())
        self.assertEqual(parse_datetime(saved.pop('assessed_at')),parse_datetime(created.pop('assessed_at')))
        self.assertEqual(saved,created)
        self.assertEqual(set(result.json()),{'id','donor_id','status','reason_codes','reasons','assessed_at','rules_version','is_stale'})
        response=self.staff.get('/api/v1/donors?blood_group=O%2B&location=beng&eligibility_status=ELIGIBLE')
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['count'],1)
        row=response.json()['results'][0];self.assertEqual(row['id'],str(self.a.pk))
        self.assertEqual(set(row),{'id','blood_group','location','eligibility_status'})
        self.assertFalse(SecurityEvent.objects.exists())
    def test_ineligible_reason_and_latest_history(self):
        self.assertEqual(self.screen(age=17).status_code,200)
        value=self.owner.get(self.result_path).json();self.assertEqual(value['status'],'INELIGIBLE');self.assertIn('AGE_BELOW_MINIMUM',value['reason_codes'])
        self.assertTrue(value['reasons'])
        self.assertEqual(self.screen().status_code,200)
        value=self.owner.get(self.result_path).json();self.assertEqual(value['status'],'ELIGIBLE');self.assertEqual(value['reasons'],[])
        self.assertEqual(EligibilityResult.objects.filter(donor=self.a).count(),2)
    def test_missing_result_and_unknown_profile_are_safe_404(self):
        for path in [self.result_path,f'/api/v1/donors/{uuid4()}/eligibility/result']:
            response=self.owner.get(path);self.assertEqual(response.status_code,404)
            self.assertNotIn(self.a.mobile,response.content.decode())
        self.assertFalse(SecurityEvent.objects.exists())
    def test_other_donor_result_denial_matches_missing_and_records_once(self):
        self.screen();a=self.other.get(self.result_path);b=self.other.get(f'/api/v1/donors/{uuid4()}/eligibility/result')
        self.assertEqual((a.status_code,b.status_code),(404,404))
        for key in ['code','message','fields']:self.assertEqual(a.json()['error'][key],b.json()['error'][key])
        event=SecurityEvent.objects.get();self.assertEqual((event.event_type,event.actor_id),('access_denied',self.b.user_id))
    def test_staff_can_read_and_ordinary_donor_cannot_search(self):
        self.screen();self.assertEqual(self.staff.get(self.result_path).status_code,200)
        self.assertEqual(self.owner.get('/api/v1/donors').status_code,403)
        self.assertEqual(SecurityEvent.objects.filter(event_type='access_denied').count(),1)
    def test_not_screened_empty_and_pagination(self):
        response=self.staff.get('/api/v1/donors?eligibility_status=NOT_SCREENED');self.assertEqual(response.json()['count'],2)
        first=self.staff.get('/api/v1/donors?page_size=1&page=1').json();second=self.staff.get('/api/v1/donors?page_size=1&page=2').json()
        self.assertNotEqual(first['results'][0]['id'],second['results'][0]['id'])
        self.assertEqual(self.staff.get('/api/v1/donors?page=999').json()['results'],[])
        self.assertEqual(self.staff.get('/api/v1/donors?location=nonexistent').json()['results'],[])
    def test_changed_rule_version_marks_real_saved_result_stale(self):
        from donors.configuration import approved_screening_rules
        self.screen();rules=approved_screening_rules();rules['rules_version']='changed-demo-version'
        with patch('donors.eligibility_reader.approved_screening_rules',return_value=rules):
            self.assertTrue(self.owner.get(self.result_path).json()['is_stale'])
            value=self.staff.get('/api/v1/donors?eligibility_status=STALE').json();self.assertEqual(value['count'],1)
        self.assertFalse(self.owner.get(self.result_path).json()['is_stale'])
    def test_old_assessment_is_not_used_over_latest_timestamp(self):
        self.screen(age=17);old=EligibilityResult.objects.get(donor=self.a)
        self.screen();EligibilityResult.objects.filter(pk=old.pk).update(assessed_at=timezone.now()-timedelta(days=1))
        self.assertEqual(self.owner.get(self.result_path).json()['status'],'ELIGIBLE')
    def test_invalid_filters_and_duplicates_reject_without_domain_writes(self):
        for query in ['page=0','page_size=101','page=1.5','page=1&page=2','blood_group=XX','eligibility_status=XX','role=ADMIN','location='+('x'*121)]:
            r=self.staff.get('/api/v1/donors?'+query);self.assertEqual(r.status_code,400,query)
        self.assertFalse(EligibilityResult.objects.exists());self.assertEqual(DonorProfile.objects.count(),2)
    def test_literal_injection_like_location_does_not_bypass_query(self):
        for query in ["x' OR 1=1 --",'<script>alert(1)</script>','%','_']:
            response=self.staff.get('/api/v1/donors',{'location':query})
            self.assertEqual(response.status_code,200);self.assertEqual(response.json()['results'],[])
        self.assertEqual(DonorProfile.objects.count(),2)
    def test_result_denial_audit_failure_is_redacted_503(self):
        self.screen()
        with patch('audit.events.SecurityEvent.objects.create',side_effect=OperationalError('PRIVATE_STORAGE_DETAIL')):
            response=self.other.get(self.result_path)
        self.assertEqual(response.status_code,503);self.assertNotIn('PRIVATE_STORAGE_DETAIL',response.content.decode())
    def test_superusers_all_roles_denied_on_real_result_and_search(self):
        self.screen()
        for role in ['DONOR','STAFF','ADMIN','REQUESTER']:
            self.a.user.role=role;self.a.user.is_superuser=True;self.a.user.save(update_fields=['role','is_superuser'])
            for path in [self.result_path,'/api/v1/donors']:
                r=self.owner.get(path);self.assertEqual(r.status_code,403,role)
                self.assertNotIn(self.a.mobile,r.content.decode())
        self.assertEqual(SecurityEvent.objects.filter(event_type='access_denied').count(),8)
