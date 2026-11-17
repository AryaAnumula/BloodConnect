# Synthetic example.test walkthrough data (local lane only). Password comes from env, never printed.
import json, os
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.utils import timezone
from donors.models import DonorProfile
from inventory.models import BloodUnit, CollectionEvent

pw = os.environ['WALK_PW']
U = get_user_model()
def user(email, role):
    u, _ = U.objects.get_or_create(email=email, defaults={'role': role})
    u.role = role; u.is_active = True; u.set_password(pw); u.save(); return u
staff = user('bb16-walk-staff@example.test', 'STAFF')
user('bb16-walk-requester@example.test', 'REQUESTER')
donor_user = user('bb16-walk-donor@example.test', 'DONOR')
donor, _ = DonorProfile.objects.get_or_create(user=donor_user, defaults=dict(
    full_name='Synthetic Walk Donor', mobile='+919000099001', blood_group='A+', location='Test'))
today = timezone.now().astimezone(ZoneInfo('Asia/Kolkata')).date()
out = {}
for code, status, expiry in [('BB16-WALK-GOOD-1', 'AVAILABLE', today + timedelta(days=5)),
                             ('BB16-WALK-GOOD-2', 'AVAILABLE', today + timedelta(days=6)),
                             ('BB16-WALK-EXPIRES-TODAY', 'AVAILABLE', today),
                             ('BB16-WALK-QUARANTINED', 'QUARANTINED', today + timedelta(days=5))]:
    unit = BloodUnit.objects.filter(unit_code=code).first()
    if unit is None:
        collected = today - timedelta(days=10)
        event = CollectionEvent.objects.create(donor=donor, collection_date=collected, blood_group='A+', recorded_by=staff)
        unit = BloodUnit.objects.create(unit_code=code, donor=donor, collection_event=event, blood_group='A+',
                                        component_type='RBC', collection_date=collected, expiry_date=expiry, status=status)
    out[code] = str(unit.id)
print(json.dumps(out))
