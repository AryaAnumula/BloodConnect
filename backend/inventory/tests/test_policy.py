
from datetime import date

from django.test import SimpleTestCase

from inventory.services.policy import (
    DecisionRequired,
    calculate_expiry_date,
    get_shelf_life_days,
    is_unit_usable,
)


# Synthetic test data only. Never use as production configuration.
TEST_SHELF_LIFE_POLICY = {
    "WHOLE_BLOOD": 10,
    "RBC": 11,
    "PLASMA": 12,
    "PLATELETS": 13,
}


class ShelfLifePolicyTests(SimpleTestCase):

    def test_reads_explicit_component_value(self):
        self.assertEqual(
            get_shelf_life_days(
                component_type="RBC",
                policy=TEST_SHELF_LIFE_POLICY,
            ),
            11,
        )

    def test_missing_component_fails_closed(self):
        with self.assertRaises(DecisionRequired):
            get_shelf_life_days(
                component_type="RBC",
                policy={"PLASMA": 12},
            )

    def test_zero_value_fails_closed(self):
        with self.assertRaises(DecisionRequired):
            get_shelf_life_days(
                component_type="RBC",
                policy={"RBC": 0},
            )

    def test_negative_value_fails_closed(self):
        with self.assertRaises(DecisionRequired):
            get_shelf_life_days(
                component_type="RBC",
                policy={"RBC": -5},
            )

    def test_boolean_value_fails_closed(self):
        with self.assertRaises(DecisionRequired):
            get_shelf_life_days(
                component_type="RBC",
                policy={"RBC": True},
            )

    def test_fractional_value_fails_closed(self):
        with self.assertRaises(DecisionRequired):
            get_shelf_life_days(
                component_type="RBC",
                policy={"RBC": 11.5},
            )

    def test_unsupported_component_fails_closed(self):
        with self.assertRaises(DecisionRequired):
            get_shelf_life_days(
                component_type="UNKNOWN",
                policy=TEST_SHELF_LIFE_POLICY,
            )

    def test_expiry_date_uses_configured_value(self):
        result = calculate_expiry_date(
            collection_date=date(2026, 11, 1),
            component_type="RBC",
            policy=TEST_SHELF_LIFE_POLICY,
            today=date(2026, 11, 15),
        )
        self.assertEqual(result, date(2026, 11, 12))

    def test_future_collection_date_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_expiry_date(
                collection_date=date(2026, 11, 16),
                component_type="RBC",
                policy=TEST_SHELF_LIFE_POLICY,
                today=date(2026, 11, 15),
            )

    def test_available_unit_before_expiry_is_usable(self):
        self.assertTrue(
            is_unit_usable(
                status="AVAILABLE",
                expiry_date=date(2026, 11, 20),
                today=date(2026, 11, 19),
            )
        )

    def test_unit_is_not_usable_on_expiry_date(self):
        self.assertFalse(
            is_unit_usable(
                status="AVAILABLE",
                expiry_date=date(2026, 11, 20),
                today=date(2026, 11, 20),
            )
        )

    def test_unit_is_not_usable_after_expiry(self):
        self.assertFalse(
            is_unit_usable(
                status="AVAILABLE",
                expiry_date=date(2026, 11, 20),
                today=date(2026, 11, 21),
            )
        )

    def test_non_available_unit_is_not_usable(self):
        for status in ("ISSUED", "DISCARDED", "QUARANTINED"):
            with self.subTest(status=status):
                self.assertFalse(
                    is_unit_usable(
                        status=status,
                        expiry_date=date(2026, 11, 20),
                        today=date(2026, 11, 19),
                    )
                )
