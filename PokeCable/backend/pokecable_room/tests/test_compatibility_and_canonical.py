from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.canonical import CanonicalItem, CanonicalMove, CanonicalPokemon
from pokecable_room.compatibility import build_compatibility_report, get_trade_mode
from pokecable_room.compatibility.matrix import (
    FORWARD_TRANSFER_TO_GEN3,
    LEGACY_DOWNCONVERT_EXPERIMENTAL,
    SAME_GENERATION,
    TIME_CAPSULE_GEN1_GEN2,
)
from pokecable_room.parsers.gen1 import Gen1Parser, gen1_internal_to_national, national_to_gen1_internal
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser

from test_gen1_synthetic import synthetic_save as synthetic_gen1_save
from test_gen2_parser import synthetic_save as synthetic_gen2_save
from test_gen3_parser import synthetic_save as synthetic_gen3_save


def canonical_gen2(species_id: int = 152, held_item: bool = False) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=2,
        source_game="pokemon_crystal",
        species_national_id=species_id,
        species_name="Chikorita" if species_id == 152 else "Kadabra",
        nickname="TEST",
        level=20,
        ot_name="CHRIS",
        trainer_id=123,
        held_item=CanonicalItem(item_id=1, source_generation=2) if held_item else None,
    )


class CompatibilityAndCanonicalTests(unittest.TestCase):
    def test_compatibility_matrix_returns_expected_modes(self) -> None:
        self.assertEqual(get_trade_mode(1, 1), SAME_GENERATION)
        self.assertEqual(get_trade_mode(2, 2), SAME_GENERATION)
        self.assertEqual(get_trade_mode(3, 3), SAME_GENERATION)
        self.assertEqual(get_trade_mode(1, 2), TIME_CAPSULE_GEN1_GEN2)
        self.assertEqual(get_trade_mode(2, 1), TIME_CAPSULE_GEN1_GEN2)
        self.assertEqual(get_trade_mode(1, 3), FORWARD_TRANSFER_TO_GEN3)
        self.assertEqual(get_trade_mode(2, 3), FORWARD_TRANSFER_TO_GEN3)
        self.assertEqual(get_trade_mode(3, 1), LEGACY_DOWNCONVERT_EXPERIMENTAL)
        self.assertEqual(get_trade_mode(3, 2), LEGACY_DOWNCONVERT_EXPERIMENTAL)

    def test_gen1_internal_id_maps_to_national_dex(self) -> None:
        self.assertEqual(gen1_internal_to_national(38), 64)
        self.assertEqual(gen1_internal_to_national(149), 65)

    def test_national_dex_maps_to_gen1_internal_id(self) -> None:
        self.assertEqual(national_to_gen1_internal(64), 38)
        self.assertEqual(national_to_gen1_internal(65), 149)

    def test_canonical_export_from_gen1(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "Pokemon Red.sav"
            save.write_bytes(synthetic_gen1_save())
            parser = Gen1Parser()
            parser.load(save)
            canonical = parser.export_canonical("party:0")
            self.assertEqual(canonical.source_generation, 1)
            self.assertEqual(canonical.species_national_id, 64)
            self.assertEqual(canonical.species_name, "Kadabra")
            self.assertIsNotNone(canonical.original_data)

    def test_canonical_export_from_gen2(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "Pokemon Crystal.sav"
            save.write_bytes(synthetic_gen2_save())
            parser = Gen2Parser()
            parser.load(save)
            canonical = parser.export_canonical("party:0")
            self.assertEqual(canonical.source_generation, 2)
            self.assertEqual(canonical.species_national_id, 95)
            self.assertEqual(canonical.species_name, "Onix")
            self.assertIsNotNone(canonical.original_data)

    def test_canonical_export_from_gen3(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "Pokemon Emerald.sav"
            save.write_bytes(synthetic_gen3_save("rse"))
            parser = Gen3Parser()
            parser.load(save)
            canonical = parser.export_canonical("party:0")
            self.assertEqual(canonical.source_generation, 3)
            self.assertEqual(canonical.species_national_id, 64)
            self.assertEqual(canonical.species_name, "Kadabra")
            self.assertIsNotNone(canonical.original_data)

    def test_gen3_hoenn_internal_id_maps_to_real_national_dex(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "Pokemon Emerald.sav"
            save.write_bytes(synthetic_gen3_save("rse"))
            parser = Gen3Parser()
            parser.load(save)
            canonical = parser.export_canonical("party:1")
            self.assertEqual(canonical.species.source_species_id, 373)
            self.assertEqual(canonical.species.national_dex_id, 366)
            self.assertEqual(canonical.species_name, "Clamperl")

    def test_report_blocks_gen2_species_that_does_not_exist_in_gen1(self) -> None:
        report = build_compatibility_report(canonical_gen2(152), 1, cross_generation_enabled=False)
        self.assertFalse(report.compatible)
        self.assertIn("Chikorita", " ".join(report.blocking_reasons))

    def test_report_warns_held_item_loss_when_going_to_gen1(self) -> None:
        report = build_compatibility_report(canonical_gen2(64, held_item=True), 1, cross_generation_enabled=False)
        self.assertTrue(report.compatible)
        self.assertIn("held_item", report.data_loss)
        self.assertTrue(any("Held item" in warning for warning in report.warnings))

    def test_report_records_ability_and_nature_loss_when_downconverting(self) -> None:
        canonical = canonical_gen2(64)
        canonical.source_generation = 3
        canonical.source_game = "pokemon_emerald"
        canonical.ability = "Synchronize"
        canonical.nature = "Timid"
        report = build_compatibility_report(canonical, 2, cross_generation_enabled=True)
        self.assertTrue(report.compatible)
        self.assertIn("ability", report.data_loss)
        self.assertIn("nature", report.data_loss)
        self.assertTrue(report.requires_user_confirmation)

    def test_move_policy_blocks_or_removes_incompatible_move(self) -> None:
        canonical = canonical_gen2(64)
        canonical.moves = [CanonicalMove(move_id=200, name="Gen2Move", source_generation=2)]
        strict_report = build_compatibility_report(canonical, 1, cross_generation_enabled=True, policy="safe_default")
        self.assertFalse(strict_report.compatible)
        self.assertTrue(any("Gen2Move" in reason for reason in strict_report.blocking_reasons))

        permissive_report = build_compatibility_report(canonical, 1, cross_generation_enabled=True, policy="permissive")
        self.assertTrue(permissive_report.compatible)
        self.assertEqual(permissive_report.removed_moves, [{"move_id": 200, "name": "Gen2Move"}])
        self.assertIn("moves", permissive_report.data_loss)


if __name__ == "__main__":
    unittest.main()
