"""BB09: authorized safe-summary search, approved query contract; no clinical calculation."""
from rest_framework.exceptions import PermissionDenied, ValidationError
from accounts.permissions import is_authorized_staff
from core.input_schemas import SearchInputSerializer
from donors.models.profile import DonorProfile
from donors.eligibility_reader import read_saved_results


def search_donors(*, actor, blood_group=None, location=None, eligibility_status=None, page=1, page_size=20):
    if not is_authorized_staff(user=actor):
        raise PermissionDenied()
    raw = {'page': page, 'page_size': page_size}
    for key, value in [('blood_group', blood_group), ('location', location), ('eligibility_status', eligibility_status)]:
        if value is not None:
            raw[key] = value
    validator = SearchInputSerializer(data=raw)
    validator.is_valid(raise_exception=True)
    data = validator.validated_data
    query = DonorProfile.objects.filter(user__is_active=True).order_by('pk')
    if data.get('blood_group'):
        query = query.filter(blood_group=data['blood_group'])
    if data.get('location'):
        query = query.filter(location__icontains=data['location'])
    profiles = list(query)
    # Read persisted results once; NOT_SCREENED is used only after a successful reader call.
    saved = read_saved_results(donor_ids=[profile.pk for profile in profiles])
    summaries = []
    for profile in profiles:
        assessment = saved.get(str(profile.pk))
        state = 'NOT_SCREENED' if assessment is None else ('STALE' if assessment['is_stale'] else assessment['status'])
        if state not in ('ELIGIBLE', 'INELIGIBLE', 'NOT_SCREENED', 'STALE'):
            raise ValidationError({'non_field_errors': ['Invalid saved assessment state.']})
        if data.get('eligibility_status') and state != data['eligibility_status']:
            continue
        summaries.append({'id': str(profile.pk), 'blood_group': profile.blood_group,
                          'location': profile.location, 'eligibility_status': state})
    start = (data['page'] - 1) * data['page_size']
    return {'count': len(summaries), 'page': data['page'], 'page_size': data['page_size'],
            'results': summaries[start:start + data['page_size']]}
