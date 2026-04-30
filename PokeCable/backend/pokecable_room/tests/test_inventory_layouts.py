from __future__ import annotations

import unittest

from pokecable_room.data.inventory_layouts import (
    GEN1_RBY_LAYOUT,
    GEN2_CRYSTAL_LAYOUT,
    GEN2_GS_LAYOUT,
    GEN3_EMERALD_LAYOUT,
    GEN3_FRLG_LAYOUT,
    GEN3_RS_LAYOUT,
    inventory_layout_for_game,
    inventory_pocket_for_game,
)


class InventoryLayoutTests(unittest.TestCase):
    def test_gen1_layout_has_bag_and_pc(self) -> None:
        self.assertEqual(GEN1_RBY_LAYOUT.pocket("bag_items").offset, 0x25C9)
        self.assertEqual(GEN1_RBY_LAYOUT.pocket("bag_items").capacity, 20)
        self.assertEqual(GEN1_RBY_LAYOUT.pocket("pc_items").offset, 0x27E6)
        self.assertEqual(GEN1_RBY_LAYOUT.pocket("pc_items").capacity, 50)

    def test_gen2_gold_silver_layout_matches_known_offsets(self) -> None:
        self.assertEqual(GEN2_GS_LAYOUT.pocket("tm_hm").offset, 0x23E6)
        self.assertEqual(GEN2_GS_LAYOUT.pocket("items").offset, 0x241F)
        self.assertEqual(GEN2_GS_LAYOUT.pocket("key_items").offset, 0x2449)
        self.assertEqual(GEN2_GS_LAYOUT.pocket("balls").capacity, 12)
        self.assertEqual(GEN2_GS_LAYOUT.pocket("pc_items").capacity, 50)

    def test_gen2_crystal_layout_matches_shifted_offsets(self) -> None:
        self.assertEqual(GEN2_CRYSTAL_LAYOUT.pocket("tm_hm").offset, 0x23E7)
        self.assertEqual(GEN2_CRYSTAL_LAYOUT.pocket("items").offset, 0x2420)
        self.assertEqual(GEN2_CRYSTAL_LAYOUT.pocket("key_items").offset, 0x244A)
        self.assertEqual(GEN2_CRYSTAL_LAYOUT.pocket("balls").offset, 0x2465)
        self.assertEqual(GEN2_CRYSTAL_LAYOUT.pocket("pc_items").offset, 0x247F)

    def test_gen3_layouts_capture_rse_emerald_and_frlg_differences(self) -> None:
        self.assertEqual(GEN3_RS_LAYOUT.pocket("items").capacity, 20)
        self.assertEqual(GEN3_EMERALD_LAYOUT.pocket("items").capacity, 30)
        self.assertEqual(GEN3_FRLG_LAYOUT.pocket("items").capacity, 42)
        self.assertEqual(GEN3_RS_LAYOUT.pocket("key_items").offset, 0x05B0)
        self.assertEqual(GEN3_EMERALD_LAYOUT.pocket("key_items").offset, 0x05D8)
        self.assertEqual(GEN3_FRLG_LAYOUT.pocket("berries").offset, 0x054C)

    def test_inventory_layout_lookup_by_game_id(self) -> None:
        self.assertEqual(inventory_layout_for_game("pokemon_blue").game_family, "gen1_rby")
        self.assertEqual(inventory_layout_for_game("pokemon_crystal").game_family, "gen2_crystal")
        self.assertEqual(inventory_layout_for_game("pokemon_emerald").game_family, "gen3_emerald")
        self.assertEqual(inventory_layout_for_game("pokemon_leafgreen").game_family, "gen3_frlg")

    def test_inventory_pocket_lookup_by_game_id(self) -> None:
        pocket = inventory_pocket_for_game("pokemon_silver", "items")
        self.assertEqual(pocket.offset, 0x241F)
        self.assertEqual(pocket.encoding, "counted_item_pairs_u8")


if __name__ == "__main__":
    unittest.main()
