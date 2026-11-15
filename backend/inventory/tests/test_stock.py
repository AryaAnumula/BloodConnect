from datetime import date

from django.test import SimpleTestCase

from inventory.selectors.stock import summarize_usable_stock


TODAY = date(2026, 11, 15)


def make_unit(
    *,
    blood_group="O+",
    component_type="RBC",
    status="AVAILABLE",
    expiry_date=date(2026, 11, 20),
    quantity=1,
):
    return {
        "blood_group": blood_group,
        "component_type": component_type,
        "status": status,
        "expiry_date": expiry_date,
        "quantity": quantity,
    }


class StockSummaryTests(SimpleTestCase):

    def test_empty_inventory_returns_empty_summary(self):
        self.assertEqual(
            summarize_usable_stock(units=[], today=TODAY),
            [],
        )

    def test_counts_available_unexpired_units(self):
        units = [
            make_unit(),
            make_unit(),
            make_unit(component_type="PLASMA"),
        ]

        result = summarize_usable_stock(units=units, today=TODAY)

        self.assertEqual(
            result,
            [
                {
                    "blood_group": "O+",
                    "component_type": "PLASMA",
                    "available_units": 1,
                },
                {
                    "blood_group": "O+",
                    "component_type": "RBC",
                    "available_units": 2,
                },
            ],
        )

    def test_excludes_expired_units(self):
        units = [
            make_unit(expiry_date=date(2026, 11, 14)),
            make_unit(expiry_date=date(2026, 11, 20)),
        ]

        result = summarize_usable_stock(units=units, today=TODAY)

        self.assertEqual(result[0]["available_units"], 1)

    def test_excludes_units_on_expiry_date(self):
        units = [
            make_unit(expiry_date=TODAY),
        ]

        self.assertEqual(
            summarize_usable_stock(units=units, today=TODAY),
            [],
        )

    def test_excludes_non_available_units(self):
        units = [
            make_unit(status="ISSUED"),
            make_unit(status="DISCARDED"),
            make_unit(status="QUARANTINED"),
            make_unit(status="AVAILABLE"),
        ]

        result = summarize_usable_stock(units=units, today=TODAY)

        self.assertEqual(result[0]["available_units"], 1)

    def test_groups_different_blood_groups_separately(self):
        units = [
            make_unit(blood_group="O+"),
            make_unit(blood_group="A+"),
        ]

        result = summarize_usable_stock(units=units, today=TODAY)

        self.assertEqual(len(result), 2)
        self.assertEqual(
            {row["blood_group"] for row in result},
            {"O+", "A+"},
        )

    def test_rejects_quantity_other_than_one(self):
        with self.assertRaises(ValueError):
            summarize_usable_stock(
                units=[make_unit(quantity=2)],
                today=TODAY,
            )

    def test_rejects_invalid_unit_status(self):
        with self.assertRaises(ValueError):
            summarize_usable_stock(
                units=[make_unit(status="EXPIRED")],
                today=TODAY,
            )

    def test_rejects_invalid_expiry_date(self):
        with self.assertRaises(ValueError):
            summarize_usable_stock(
                units=[make_unit(expiry_date="2026-11-20")],
                today=TODAY,
            )