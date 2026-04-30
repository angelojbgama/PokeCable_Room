from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Callable, Type

from pokecable_room.evolutions import apply_trade_evolution_to_parser
from pokecable_room.parsers.base import SaveParser
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser

from test_gen1_synthetic import synthetic_save as synthetic_gen1_save
from test_gen2_parser import synthetic_save as synthetic_gen2_save
from test_gen3_parser import synthetic_save as synthetic_gen3_save


class SameGenerationTradeFlowTests(unittest.TestCase):
    def test_gen1_raw_trade_applies_simple_evolution_after_write(self) -> None:
        self._assert_same_generation_trade(
            parser_cls=Gen1Parser,
            save_factory=synthetic_gen1_save,
            save_suffix=".sav",
            species_a=38,
            species_b=41,
            expected_a=126,
            expected_b=149,
        )

    def test_gen2_raw_trade_applies_simple_evolution_after_write(self) -> None:
        self._assert_same_generation_trade(
            parser_cls=Gen2Parser,
            save_factory=synthetic_gen2_save,
            save_suffix=".sav",
            species_a=64,
            species_b=67,
            expected_a=68,
            expected_b=65,
        )

    def test_gen3_raw_trade_applies_simple_evolution_after_write(self) -> None:
        self._assert_same_generation_trade(
            parser_cls=Gen3Parser,
            save_factory=lambda: synthetic_gen3_save("rse"),
            save_suffix=".sav",
            species_a=64,
            species_b=67,
            expected_a=68,
            expected_b=65,
        )

    def _assert_same_generation_trade(
        self,
        *,
        parser_cls: Type[SaveParser],
        save_factory: Callable[[], bytes],
        save_suffix: str,
        species_a: int,
        species_b: int,
        expected_a: int,
        expected_b: int,
    ) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_a = Path(tempdir) / f"a{save_suffix}"
            save_b = Path(tempdir) / f"b{save_suffix}"
            save_a.write_bytes(save_factory())
            save_b.write_bytes(save_factory())

            parser_a = parser_cls()
            parser_b = parser_cls()
            parser_a.load(save_a)
            parser_b.load(save_b)
            parser_a.set_species_id("party:0", species_a)
            parser_b.set_species_id("party:0", species_b)

            payload_a = parser_a.export_pokemon("party:0")
            payload_b = parser_b.export_pokemon("party:0")

            self.assertEqual(payload_a.generation, parser_a.get_generation())
            self.assertEqual(payload_b.generation, parser_b.get_generation())

            parser_a.remove_or_replace_sent_pokemon("party:0", payload_b)
            parser_b.remove_or_replace_sent_pokemon("party:0", payload_a)
            apply_trade_evolution_to_parser(parser_a, "party:0")
            apply_trade_evolution_to_parser(parser_b, "party:0")

            parser_a.save(save_a)
            parser_b.save(save_b)

            reloaded_a = parser_cls()
            reloaded_b = parser_cls()
            reloaded_a.load(save_a)
            reloaded_b.load(save_b)

            self.assertTrue(reloaded_a.validate())
            self.assertTrue(reloaded_b.validate())
            self.assertEqual(reloaded_a.get_species_id("party:0"), expected_a)
            self.assertEqual(reloaded_b.get_species_id("party:0"), expected_b)


if __name__ == "__main__":
    unittest.main()
