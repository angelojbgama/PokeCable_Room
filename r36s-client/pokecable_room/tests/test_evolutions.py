from __future__ import annotations

import unittest

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.evolutions import EvolutionContext, apply_trade_evolution, trade_evolution_target
from pokecable_room.evolutions.rules import SIMPLE_TRADE_EVOLUTIONS


def pokemon(species_id: int, generation: int) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=generation,
        source_game=f"gen{generation}",
        species_national_id=species_id,
        species_name=f"Species #{species_id}",
        nickname="TEST",
        level=30,
        ot_name="OT",
        trainer_id=1,
    )


class EvolutionEngineTests(unittest.TestCase):
    def test_simple_trade_evolution_gen1_uses_internal_ids(self) -> None:
        context = EvolutionContext(source_generation=1, target_generation=1, trade_mode="same_generation")
        self.assertEqual(trade_evolution_target(38, context), 149)
        self.assertEqual(trade_evolution_target(41, context), 126)
        self.assertEqual(trade_evolution_target(39, context), 49)
        self.assertEqual(trade_evolution_target(147, context), 14)

    def test_simple_trade_evolution_gen2_and_gen3_use_generation_ids(self) -> None:
        for generation in (2, 3):
            context = EvolutionContext(source_generation=generation, target_generation=generation, trade_mode="same_generation")
            self.assertEqual(trade_evolution_target(64, context), 65)
            self.assertEqual(trade_evolution_target(67, context), 68)
            self.assertEqual(trade_evolution_target(75, context), 76)
            self.assertEqual(trade_evolution_target(93, context), 94)

    def test_apply_trade_evolution_updates_canonical_species(self) -> None:
        context = EvolutionContext(source_generation=2, target_generation=2, trade_mode="same_generation")
        evolved = apply_trade_evolution(pokemon(64, 2), context)
        self.assertEqual(evolved.species_national_id, 65)
        self.assertTrue(evolved.metadata["trade_evolution_applied"])

    def test_evolution_does_not_apply_when_target_species_does_not_exist(self) -> None:
        original = SIMPLE_TRADE_EVOLUTIONS[1][38]
        SIMPLE_TRADE_EVOLUTIONS[1][38] = 999
        try:
            context = EvolutionContext(source_generation=1, target_generation=1, trade_mode="same_generation")
            self.assertIsNone(trade_evolution_target(38, context))
        finally:
            SIMPLE_TRADE_EVOLUTIONS[1][38] = original


if __name__ == "__main__":
    unittest.main()
