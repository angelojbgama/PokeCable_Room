from __future__ import annotations

import unittest

from pokecable_room.data.items import (
    GEN1_ITEMS_BY_ID,
    GEN2_ITEMS_BY_ID,
    GEN3_ITEMS_BY_ID,
    equivalent_item_id,
    generation_items,
    item_category,
    item_exists,
    item_name,
)


class ItemCatalogTests(unittest.TestCase):
    def test_generation_catalogs_have_expected_sizes(self) -> None:
        self.assertEqual(len(GEN1_ITEMS_BY_ID), 152)
        self.assertEqual(len(GEN2_ITEMS_BY_ID), 250)
        self.assertEqual(len(GEN3_ITEMS_BY_ID), 376)

    def test_generation_items_returns_full_copy(self) -> None:
        self.assertEqual(len(generation_items(1)), 152)
        self.assertEqual(len(generation_items(2)), 250)
        self.assertEqual(len(generation_items(3)), 376)

    def test_known_items_exist_in_each_generation(self) -> None:
        self.assertTrue(item_exists(1, 1))
        self.assertTrue(item_exists(0x52, 2))
        self.assertTrue(item_exists(199, 3))
        self.assertFalse(item_exists(999, 1))
        self.assertFalse(item_exists(999, 2))
        self.assertFalse(item_exists(999, 3))

    def test_known_item_names_resolve(self) -> None:
        self.assertEqual(item_name(1, 1), "Master Ball")
        self.assertEqual(item_name(0x52, 2), "King's Rock")
        self.assertEqual(item_name(199, 3), "Metal Coat")
        self.assertEqual(item_name(192, 3), "Deep Sea Tooth")

    def test_item_categories_cover_expected_classes(self) -> None:
        self.assertEqual(item_category(0xC9, 1), "tm")
        self.assertEqual(item_category(0xC4, 1), "hm")
        self.assertEqual(item_category(21, 1), "badge")
        self.assertEqual(item_category(0xBF, 2), "tm")
        self.assertEqual(item_category(0xF3, 2), "hm")
        self.assertEqual(item_category(121, 3), "mail")
        self.assertEqual(item_category(133, 3), "berry")
        self.assertEqual(item_category(187, 3), "hold_item")
        self.assertEqual(item_category(289, 3), "tm")
        self.assertEqual(item_category(339, 3), "hm")

    def test_explicit_cross_generation_equivalents_stay_stable(self) -> None:
        self.assertEqual(equivalent_item_id(0x52, 2, 3), 187)
        self.assertEqual(equivalent_item_id(0x8F, 2, 3), 199)
        self.assertEqual(equivalent_item_id(0x97, 2, 3), 201)
        self.assertEqual(equivalent_item_id(0xAC, 2, 3), 218)
        self.assertEqual(equivalent_item_id(187, 3, 2), 0x52)
        self.assertEqual(equivalent_item_id(199, 3, 2), 0x8F)
        self.assertEqual(equivalent_item_id(201, 3, 2), 0x97)
        self.assertEqual(equivalent_item_id(218, 3, 2), 0xAC)

    def test_non_equivalent_items_do_not_gain_implicit_mapping(self) -> None:
        self.assertIsNone(equivalent_item_id(192, 3, 2))
        self.assertIsNone(equivalent_item_id(193, 3, 2))
        self.assertIsNone(equivalent_item_id(1, 1, 2))
        self.assertIsNone(equivalent_item_id(1, 1, 3))


if __name__ == "__main__":
    unittest.main()
