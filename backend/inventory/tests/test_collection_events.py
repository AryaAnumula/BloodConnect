
from django.test import SimpleTestCase

from inventory.services.collection_events import validate_event_components


class CollectionEventComponentTests(SimpleTestCase):

    def test_accepts_whole_blood_alone(self):
        self.assertEqual(
            validate_event_components(components=["WHOLE_BLOOD"]),
            ("WHOLE_BLOOD",),
        )

    def test_accepts_single_separated_component(self):
        self.assertEqual(
            validate_event_components(components=["RBC"]),
            ("RBC",),
        )

    def test_accepts_multiple_separated_components(self):
        self.assertEqual(
            validate_event_components(
                components=["RBC", "PLASMA", "PLATELETS"],
            ),
            ("RBC", "PLASMA", "PLATELETS"),
        )

    def test_rejects_empty_components(self):
        with self.assertRaises(ValueError):
            validate_event_components(components=[])

    def test_rejects_duplicate_components(self):
        with self.assertRaises(ValueError):
            validate_event_components(components=["RBC", "RBC"])

    def test_rejects_whole_blood_mixed_with_other_components(self):
        with self.assertRaises(ValueError):
            validate_event_components(
                components=["WHOLE_BLOOD", "RBC"],
            )

    def test_rejects_unsupported_component(self):
        with self.assertRaises(ValueError):
            validate_event_components(components=["RBC", "UNKNOWN"])

    def test_rejects_string_instead_of_component_list(self):
        with self.assertRaises(ValueError):
            validate_event_components(components="RBC")
