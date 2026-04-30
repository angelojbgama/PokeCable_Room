from __future__ import annotations

import unittest

from pokecable_room.data.item_transfer_policy import resolve_item_transfer_decision


class ItemTransferPolicyTests(unittest.TestCase):
    def test_no_item_is_noop(self) -> None:
        decision = resolve_item_transfer_decision(
            None,
            source_generation=3,
            target_generation=1,
            target_supports_held_items=False,
        )
        self.assertEqual(decision.disposition, "remove")
        self.assertEqual(decision.reason, "no_item")

    def test_cross_generation_item_that_exists_but_target_cannot_hold_moves_to_bag(self) -> None:
        decision = resolve_item_transfer_decision(
            13,  # Potion in Gen 3
            source_generation=3,
            target_generation=1,
            target_supports_held_items=False,
        )
        self.assertEqual(decision.resolved_item_name, "Potion")
        self.assertEqual(decision.disposition, "move_to_bag")
        self.assertEqual(decision.fallback_disposition, "move_to_pc")
        self.assertEqual(decision.preferred_pocket_name, "bag_items")
        self.assertEqual(decision.fallback_pocket_name, "pc_items")
        self.assertEqual(decision.reason, "item_exists_but_target_cannot_hold")

    def test_equivalent_held_item_stays_held_when_target_supports_it(self) -> None:
        decision = resolve_item_transfer_decision(
            201,  # Dragon Scale in Gen 3
            source_generation=3,
            target_generation=2,
            target_supports_held_items=True,
        )
        self.assertEqual(decision.resolved_item_name, "Dragon Scale")
        self.assertEqual(decision.disposition, "keep_held")
        self.assertEqual(decision.reason, "equivalent_held_item_available")

    def test_non_holdable_existing_item_moves_to_bag_even_when_target_supports_held_items(self) -> None:
        decision = resolve_item_transfer_decision(
            289,  # TM01 in Gen 3
            source_generation=3,
            target_generation=3,
            target_supports_held_items=True,
        )
        self.assertEqual(decision.disposition, "move_to_bag")
        self.assertEqual(decision.fallback_disposition, "move_to_pc")
        self.assertEqual(decision.preferred_pocket_name, "tm_hm")
        self.assertEqual(decision.reason, "item_exists_but_category_not_holdable")

    def test_ball_and_berry_route_to_special_pockets(self) -> None:
        master_ball = resolve_item_transfer_decision(
            1,
            source_generation=3,
            target_generation=3,
            target_supports_held_items=False,
        )
        cheri_berry = resolve_item_transfer_decision(
            133,
            source_generation=3,
            target_generation=3,
            target_supports_held_items=False,
        )
        self.assertEqual(master_ball.preferred_pocket_name, "balls")
        self.assertEqual(cheri_berry.preferred_pocket_name, "berries")

    def test_item_absent_in_target_generation_is_removed(self) -> None:
        decision = resolve_item_transfer_decision(
            192,  # Deep Sea Tooth in Gen 3
            source_generation=3,
            target_generation=2,
            target_supports_held_items=True,
        )
        self.assertEqual(decision.disposition, "remove")
        self.assertEqual(decision.reason, "item_absent_in_target_generation")
        self.assertIsNone(decision.resolved_item_id)


if __name__ == "__main__":
    unittest.main()
