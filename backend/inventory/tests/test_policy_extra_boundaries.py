from datetime import date, datetime
from unittest import TestCase

from inventory.services.policy import DecisionRequired, calculate_expiry_date, get_shelf_life_days, is_unit_usable
from inventory.selectors.stock import summarize_usable_stock, usable_units


class PolicyExtraBoundaryTests(TestCase):
    def test_unsupported_and_invalid_shelf_life_fail_closed(self):
        for component, policy in [('UNKNOWN', {}), ('RBC', None), ('RBC', {'RBC': True}), ('RBC', {'RBC': 0})]:
            with self.subTest(component=component, policy=policy), self.assertRaises(DecisionRequired):
                get_shelf_life_days(component_type=component, policy=policy)

    def test_expiry_rejects_datetime_and_future_collection(self):
        today = date(2026, 11, 17)
        for collected, current in [(datetime(2026, 11, 16), today), (today, datetime(2026, 11, 17)), (date(2026, 11, 18), today)]:
            with self.subTest(collected=collected, current=current), self.assertRaises(ValueError):
                calculate_expiry_date(collection_date=collected, component_type='RBC', policy={'RBC': 42}, today=current)

    def test_usability_rejects_non_dates_and_non_available_units(self):
        today = date(2026, 11, 17)
        for expiry, current in [(datetime(2026, 11, 18), today), (today, datetime(2026, 11, 17))]:
            with self.subTest(expiry=expiry, current=current), self.assertRaises(ValueError):
                is_unit_usable(status='AVAILABLE', expiry_date=expiry, today=current)
        self.assertFalse(is_unit_usable(status='QUARANTINED', expiry_date=date(2026, 12, 1), today=today))

    def test_stock_summary_rejects_invalid_data_without_fabricating_stock(self):
        today = date(2026, 11, 17)
        valid = {'blood_group': 'A+', 'component_type': 'RBC', 'status': 'AVAILABLE',
                 'expiry_date': date(2026, 12, 1), 'quantity': 1}
        for unit in [None, dict(valid, blood_group=''), dict(valid, component_type='BAD'),
                     dict(valid, status='BAD'), dict(valid, expiry_date=datetime(2026, 12, 1)),
                     dict(valid, quantity=True)]:
            with self.subTest(unit=unit), self.assertRaises(ValueError):
                summarize_usable_stock(units=[unit], today=today)
        with self.assertRaises(ValueError): summarize_usable_stock(units=[], today=datetime(2026, 11, 17))
        self.assertEqual(summarize_usable_stock(units=[valid], today=today)[0]['available_units'], 1)

    def test_orm_stock_rejects_naive_datetime_as_a_local_date(self):
        with self.assertRaisesRegex(ValueError, 'local date'):
            usable_units(today=datetime(2026, 11, 17))
