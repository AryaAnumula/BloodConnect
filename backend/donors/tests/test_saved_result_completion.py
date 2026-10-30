"""BB08 actual saved results and real BB12 policy/audit,not fixture endpoint success."""
from unittest.mock import patch
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient
from audit.models import SecurityEvent
from donors.models import DonorProfile,EligibilityResult
from donors.configuration import approved_screening_rules
class SavedResultCompletionTests(TestCase):
    def setUp(self):
        U=get_user_model();self.owner=U.objects.create_user(email='saved-owner@example.test',password='Synthetic-Password-123')
        self.other=U.objects.create_user(email='saved-other@example.test',password='Synthetic-Password-123')
        self.profile=DonorProfile.objects.create(user=self.owner,full_name='Synthetic Donor',mobile='+919876543210',blood_group='O+',location='Demo City')
        self.path=f'/api/v1/donors/{self.profile.pk}/eligibility/result'
    def api_client(self,user):
        c=APIClient();c.force_authenticate(user);return c
    def save_result(self,status='ELIGIBLE'):
        return EligibilityResult.objects.create(donor=self.profile,age_years=25,weight_kg='60.00',status=status,reason_codes=[] if status=='ELIGIBLE' else ['AGE_BELOW_MINIMUM'],reasons=[] if status=='ELIGIBLE' else ['Demo rule failed.'],rules_version=approved_screening_rules()['rules_version'])
    def test_owner_reads_actual_exact_public_result(self):
        row=self.save_result();r=self.api_client(self.owner).get(self.path)
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['id'],str(row.pk))
        self.assertEqual(set(r.json()),{'id','donor_id','status','reason_codes','reasons','assessed_at','rules_version','is_stale'})
        self.assertNotIn('weight_kg',r.json())
    def test_authorized_staff_reads_ineligible_reasons(self):
        self.save_result('INELIGIBLE');staff=get_user_model().objects.create_user(email='saved-staff@example.test',password='Synthetic-Password-123',role='STAFF')
        staff.user_permissions.add(Permission.objects.get(content_type__app_label='accounts',codename='view_donor_health'))
        r=self.api_client(staff).get(self.path);self.assertEqual(r.status_code,200);self.assertTrue(r.json()['reasons'])
    def test_missing_and_other_donor_404_with_only_denial_audited(self):
        c=self.api_client(self.other);a=c.get(self.path);b=c.get(f'/api/v1/donors/{uuid4()}/eligibility/result')
        self.assertEqual((a.status_code,b.status_code),(404,404))
        for key in ['code','message','fields']:self.assertEqual(a.json()['error'][key],b.json()['error'][key])
        self.assertEqual(SecurityEvent.objects.count(),1)
    def test_no_saved_assessment_returns_404_without_audit(self):
        self.assertEqual(self.api_client(self.owner).get(self.path).status_code,404);self.assertFalse(SecurityEvent.objects.exists())
    def test_superuser_owner_is_denied(self):
        self.save_result();self.owner.is_superuser=True;self.owner.save(update_fields=['is_superuser'])
        self.assertEqual(self.api_client(self.owner).get(self.path).status_code,403);self.assertEqual(SecurityEvent.objects.count(),1)
    def test_changed_config_version_marks_saved_result_stale(self):
        self.save_result();rules=approved_screening_rules();rules['rules_version']='new-demo-v2'
        with patch('donors.eligibility_reader.approved_screening_rules',return_value=rules):self.assertTrue(self.api_client(self.owner).get(self.path).json()['is_stale'])
