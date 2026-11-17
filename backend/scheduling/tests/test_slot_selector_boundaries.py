from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from scheduling.selectors.slots import list_slots
from scheduling.tests.helpers import make_camp, make_slot, make_user


class SlotSelectorBoundaryTests(TestCase):
    def test_kind_time_and_camp_filters_preserve_donor_visibility(self):
        staff, donor = make_user('STAFF'), make_user('DONOR')
        camp = make_camp()
        camp_slot = make_slot(camp=camp)
        walkin = make_slot()
        cancelled = make_camp(status='CANCELLED')
        make_slot(camp=cancelled)
        self.assertEqual(list_slots(actor=donor, filters={'kind': 'CAMP'})['count'], 1)
        self.assertEqual(list_slots(actor=donor, filters={'kind': 'WALK_IN'})['count'], 1)
        self.assertEqual(list_slots(actor=staff, filters={'camp_id': camp.id})['count'], 1)
        self.assertEqual(list_slots(actor=staff, filters={'from': camp_slot.starts_at + timedelta(days=2)})['count'], 0)
        self.assertEqual(list_slots(actor=staff, filters={'to': timezone.now()})['count'], 0)
        self.assertEqual(list_slots(actor=staff, filters={'kind': 'WALK_IN'})['results'][0]['id'], str(walkin.id))
