from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.evolutions import apply_trade_evolution_to_parser, preview_trade_evolution_for_parser
from pokecable_room.evolutions import engine
from pokecable_room.evolutions.rules import TradeEvolutionRule
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser

from test_gen1_synthetic import synthetic_save as synthetic_gen1_save
from test_gen2_parser import synthetic_save as synthetic_gen2_save
from test_gen3_parser import synthetic_save as synthetic_gen3_save


class FakeParser:
    def __init__(self, generation: int, species_id: int, held_item_id: int | None = None) -> None:
        self.generation = generation
        self.species_id = species_id
        self.held_item_id = held_item_id
        self.clear_calls = 0
        self.set_calls: list[int] = []

    def get_generation(self) -> int:
        return self.generation

    def get_species_id(self, location: str) -> int:
        return self.species_id

    def set_species_id(self, location: str, species_id: int) -> None:
        self.species_id = species_id
        self.set_calls.append(species_id)

    def get_held_item_id(self, location: str) -> int | None:
        return self.held_item_id

    def clear_held_item(self, location: str) -> None:
        self.clear_calls += 1
        self.held_item_id = None


class TradeEvolutionParserTests(unittest.TestCase):
    def test_gen1_kadabra_evolves_to_alakazam(self) -> None:
        self._assert_gen1_evolution(38, 149)

    def test_gen1_machoke_evolves_to_machamp(self) -> None:
        self._assert_gen1_evolution(41, 126)

    def test_gen1_graveler_evolves_to_golem(self) -> None:
        self._assert_gen1_evolution(39, 49)

    def test_gen1_haunter_evolves_to_gengar(self) -> None:
        self._assert_gen1_evolution(147, 14)

    def test_gen2_kadabra_evolves_to_alakazam(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "Pokemon Crystal.sav"
            save.write_bytes(synthetic_gen2_save())
            parser = Gen2Parser()
            parser.load(save)
            parser.set_species_id("party:0", 64)
            result = apply_trade_evolution_to_parser(parser, "party:0")
            self.assertTrue(result.evolved)
            self.assertEqual(parser.get_species_id("party:0"), 65)
            self.assertTrue(parser.validate())

    def test_gen3_kadabra_evolves_to_alakazam(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "Pokemon Emerald.sav"
            save.write_bytes(synthetic_gen3_save("rse"))
            parser = Gen3Parser()
            parser.load(save)
            result = apply_trade_evolution_to_parser(parser, "party:0")
            self.assertTrue(result.evolved)
            self.assertEqual(parser.get_species_id("party:0"), 65)
            self.assertTrue(parser.validate())

    def test_preview_when_auto_trade_evolution_is_false_does_not_mutate_parser(self) -> None:
        parser = FakeParser(2, 64)
        result = preview_trade_evolution_for_parser(parser, "party:0")
        self.assertTrue(result.evolved)
        self.assertEqual(parser.get_species_id("party:0"), 64)
        self.assertEqual(parser.set_calls, [])

    def test_species_without_trade_evolution_does_not_change(self) -> None:
        parser = FakeParser(2, 1)
        result = apply_trade_evolution_to_parser(parser, "party:0")
        self.assertFalse(result.evolved)
        self.assertEqual(parser.get_species_id("party:0"), 1)
        self.assertEqual(parser.set_calls, [])

    def test_item_evolution_does_not_run_when_feature_flag_is_false(self) -> None:
        parser = FakeParser(2, 95, held_item_id=999)
        result = apply_trade_evolution_to_parser(parser, "party:0", item_based_evolutions_enabled=False)
        self.assertFalse(result.evolved)
        self.assertEqual(parser.get_species_id("party:0"), 95)
        self.assertEqual(parser.clear_calls, 0)

    def test_clear_held_item_only_when_item_rule_is_enabled_and_consumed(self) -> None:
        original = engine.item_trade_rules_for_generation
        try:
            engine.item_trade_rules_for_generation = lambda generation: (
                TradeEvolutionRule(
                    generation=2,
                    source_species_id=95,
                    target_species_id=208,
                    source_name="Onix",
                    target_name="Steelix",
                    required_item_id=999,
                    required_item_name="Metal Coat",
                ),
            )
            disabled_parser = FakeParser(2, 95, held_item_id=999)
            disabled = apply_trade_evolution_to_parser(
                disabled_parser,
                "party:0",
                item_based_evolutions_enabled=False,
            )
            self.assertFalse(disabled.evolved)
            self.assertEqual(disabled_parser.clear_calls, 0)

            enabled_parser = FakeParser(2, 95, held_item_id=999)
            enabled = apply_trade_evolution_to_parser(
                enabled_parser,
                "party:0",
                item_based_evolutions_enabled=True,
            )
            self.assertTrue(enabled.evolved)
            self.assertEqual(enabled_parser.get_species_id("party:0"), 208)
            self.assertEqual(enabled_parser.clear_calls, 1)
        finally:
            engine.item_trade_rules_for_generation = original

    def test_gen2_item_rule_without_validated_item_id_does_not_evolve_when_enabled(self) -> None:
        parser = FakeParser(2, 95, held_item_id=999)
        result = apply_trade_evolution_to_parser(parser, "party:0", item_based_evolutions_enabled=True)
        self.assertFalse(result.evolved)
        self.assertEqual(parser.clear_calls, 0)

    def test_gen2_item_evolutions_use_validated_ids_and_consume_item(self) -> None:
        cases = [
            (61, 0x52, 186, "King's Rock"),
            (79, 0x52, 199, "King's Rock"),
            (95, 0x8F, 208, "Metal Coat"),
            (123, 0x8F, 212, "Metal Coat"),
            (117, 0x97, 230, "Dragon Scale"),
            (137, 0xAC, 233, "Up-Grade"),
        ]
        for source, item_id, target, item_name in cases:
            with self.subTest(source=source, item=item_name):
                parser = FakeParser(2, source, held_item_id=item_id)
                result = apply_trade_evolution_to_parser(
                    parser,
                    "party:0",
                    item_based_evolutions_enabled=True,
                )
                self.assertTrue(result.evolved)
                self.assertEqual(parser.get_species_id("party:0"), target)
                self.assertEqual(result.consumed_item_id, item_id)
                self.assertEqual(result.consumed_item_name, item_name)
                self.assertEqual(parser.clear_calls, 1)

    def test_gen3_clamperl_item_evolutions_use_validated_ids_and_consume_item(self) -> None:
        cases = [
            (192, 374, "Deep Sea Tooth"),
            (193, 375, "Deep Sea Scale"),
        ]
        for item_id, target, item_name in cases:
            with self.subTest(item=item_name):
                parser = FakeParser(3, 373, held_item_id=item_id)
                result = apply_trade_evolution_to_parser(
                    parser,
                    "party:0",
                    item_based_evolutions_enabled=True,
                )
                self.assertTrue(result.evolved)
                self.assertEqual(parser.get_species_id("party:0"), target)
                self.assertEqual(result.consumed_item_name, item_name)
                self.assertEqual(parser.clear_calls, 1)

    def test_evolution_does_not_run_when_target_species_does_not_exist(self) -> None:
        original = engine.simple_trade_rules_for_generation
        try:
            engine.simple_trade_rules_for_generation = lambda generation: (
                TradeEvolutionRule(
                    generation=2,
                    source_species_id=64,
                    target_species_id=999,
                    source_name="Kadabra",
                    target_name="Invalid",
                ),
            )
            parser = FakeParser(2, 64)
            result = apply_trade_evolution_to_parser(parser, "party:0")
            self.assertFalse(result.evolved)
            self.assertEqual(parser.get_species_id("party:0"), 64)
        finally:
            engine.simple_trade_rules_for_generation = original

    def _assert_gen1_evolution(self, source_species_id: int, target_species_id: int) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "Pokemon Red.sav"
            save.write_bytes(synthetic_gen1_save())
            parser = Gen1Parser()
            parser.load(save)
            parser.set_species_id("party:0", source_species_id)
            result = apply_trade_evolution_to_parser(parser, "party:0")
            self.assertTrue(result.evolved)
            self.assertEqual(parser.get_species_id("party:0"), target_species_id)
            self.assertTrue(parser.validate())


if __name__ == "__main__":
    unittest.main()
