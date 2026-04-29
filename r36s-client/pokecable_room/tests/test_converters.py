from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.canonical import CanonicalMove
from pokecable_room.converters import get_converter
from pokecable_room.data.species import national_to_native
from pokecable_room.evolutions import apply_trade_evolution_to_parser
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser

from test_gen1_synthetic import synthetic_save as synthetic_gen1_save
from test_gen2_parser import synthetic_save as synthetic_gen2_save
from test_gen3_parser import synthetic_save as synthetic_gen3_save


class ConverterTests(unittest.TestCase):
    def _parser(self, parser_cls, path: Path, data: bytes):
        path.write_bytes(data)
        parser = parser_cls()
        parser.load(path)
        return parser

    def _mew_canonical(self, parser, location: str = "party:0"):
        generation = parser.get_generation()
        parser.set_species_id(location, {1: 21, 2: 151, 3: 151}[generation])
        if generation in {2, 3}:
            parser.clear_held_item(location)
        canonical = parser.export_canonical(location)
        canonical.moves = [CanonicalMove(33)]
        return canonical

    def test_gen1_to_gen2_creates_valid_gen2_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            target = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())

            canonical = source.export_canonical("party:0")
            result = get_converter(1, 2).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            updated = target.list_party()[1]
            self.assertEqual(updated.species_id, 64)
            self.assertEqual(updated.nickname, "KADABRA")
            self.assertEqual(updated.ot_name, "ASH")
            self.assertEqual(updated.trainer_id, 12345)

    def test_gen2_to_gen1_creates_valid_gen1_struct_when_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())

            canonical = source.export_canonical("party:0")
            result = get_converter(2, 1).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            updated = target.list_party()[1]
            self.assertEqual(updated.species_name, "Onix")
            self.assertEqual(updated.nickname, "ROCKY")
            self.assertEqual(updated.ot_name, "CHRIS")
            self.assertEqual(updated.trainer_id, 12345)

    def test_gen2_to_gen1_blocks_species_above_151(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            source.set_species_id("party:0", 152)
            converter = get_converter(2, 1)
            report = converter.can_convert(source.export_canonical("party:0"))

            self.assertFalse(report.compatible)
            self.assertTrue(any("National Dex #152" in item for item in report.blocking_reasons))
            with self.assertRaises(ValueError):
                converter.apply_to_save(target, "party:1", source.export_canonical("party:0"))

    def test_gen1_to_gen3_creates_valid_gen3_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))

            canonical = source.export_canonical("party:0")
            result = get_converter(1, 3).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            updated = target.list_party()[1]
            self.assertEqual(updated.species_name, "Kadabra")
            self.assertEqual(updated.nickname, "KADABRA")
            self.assertEqual(updated.ot_name, "ASH")
            self.assertEqual(updated.trainer_id, 12345)

    def test_mew_gen1_to_gen3_creates_valid_gen3_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))

            result = get_converter(1, 3).apply_to_save(target, "party:1", self._mew_canonical(source))

            self.assertTrue(result.wrote_to_save)
            self.assertEqual(target.get_species_id("party:1"), 151)
            self.assertEqual(target.list_party()[1].species_name, "Mew")
            self.assertTrue(target.validate())

    def test_gen2_to_gen3_creates_valid_gen3_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))

            canonical = source.export_canonical("party:0")
            result = get_converter(2, 3).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            updated = target.list_party()[1]
            self.assertEqual(updated.species_name, "Onix")
            self.assertEqual(updated.nickname, "ROCKY")
            self.assertEqual(updated.ot_name, "CHRIS")
            self.assertEqual(updated.trainer_id, 12345)

    def test_mew_gen2_to_gen3_creates_valid_gen3_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))

            result = get_converter(2, 3).apply_to_save(target, "party:1", self._mew_canonical(source))

            self.assertTrue(result.wrote_to_save)
            self.assertEqual(target.get_species_id("party:1"), 151)
            self.assertEqual(target.list_party()[1].species_name, "Mew")
            self.assertTrue(target.validate())

    def test_mew_gen2_to_gen1_creates_valid_gen1_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())

            result = get_converter(2, 1).apply_to_save(target, "party:1", self._mew_canonical(source))

            self.assertTrue(result.wrote_to_save)
            self.assertEqual(target.get_species_id("party:1"), 21)
            self.assertEqual(target.list_party()[1].species_name, "Mew")
            self.assertTrue(target.validate())

    def test_gen3_to_gen2_blocks_incompatible_and_converts_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            converter = get_converter(3, 2)

            incompatible = converter.can_convert(source.export_canonical("party:1"))
            self.assertFalse(incompatible.compatible)
            self.assertTrue(any("National Dex #366" in item for item in incompatible.blocking_reasons))

            result = converter.apply_to_save(target, "party:1", source.export_canonical("party:0"))
            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            updated = target.list_party()[1]
            self.assertEqual(updated.species_name, "Kadabra")
            self.assertEqual(updated.nickname, "KADABRA")
            self.assertEqual(updated.ot_name, "BRENDAN")
            self.assertEqual(updated.trainer_id, 0x5678)
            self.assertIn("trainer_id_high_bits", result.data_loss)

    def test_mew_gen3_to_gen2_creates_valid_gen2_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())

            result = get_converter(3, 2).apply_to_save(target, "party:1", self._mew_canonical(source))

            self.assertTrue(result.wrote_to_save)
            self.assertEqual(target.get_species_id("party:1"), 151)
            self.assertEqual(target.list_party()[1].species_name, "Mew")
            self.assertTrue(target.validate())

    def test_gen3_to_gen1_blocks_incompatible_and_converts_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            converter = get_converter(3, 1)

            incompatible = converter.can_convert(source.export_canonical("party:1"))
            self.assertFalse(incompatible.compatible)
            self.assertTrue(any("National Dex #366" in item for item in incompatible.blocking_reasons))

            result = converter.apply_to_save(target, "party:1", source.export_canonical("party:0"))
            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            updated = target.list_party()[1]
            self.assertEqual(updated.species_name, "Kadabra")
            self.assertEqual(updated.nickname, "KADABRA")
            self.assertEqual(updated.ot_name, "BRENDAN")
            self.assertEqual(updated.trainer_id, 0x5678)
            self.assertIn("trainer_id_high_bits", result.data_loss)

    def test_mew_gen3_to_gen1_creates_valid_gen1_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())

            result = get_converter(3, 1).apply_to_save(target, "party:1", self._mew_canonical(source))

            self.assertTrue(result.wrote_to_save)
            self.assertEqual(target.get_species_id("party:1"), 21)
            self.assertEqual(target.list_party()[1].species_name, "Mew")
            self.assertTrue(target.validate())

    def test_gen2_to_gen3_converts_held_item_when_equivalent_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            source.set_held_item_id("party:0", 0x8F)

            result = get_converter(2, 3).apply_to_save(target, "party:1", source.export_canonical("party:0"))

            self.assertTrue(result.wrote_to_save)
            self.assertEqual(target.get_held_item_id("party:1"), 199)
            self.assertEqual(result.canonical_after.held_item.item_id, 199)
            self.assertTrue(any("ID 199" in item for item in result.transformations))
            self.assertTrue(target.validate())

    def test_gen3_to_gen2_converts_held_item_when_equivalent_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            source.set_held_item_id("party:0", 199)

            result = get_converter(3, 2).apply_to_save(target, "party:1", source.export_canonical("party:0"))

            self.assertTrue(result.wrote_to_save)
            self.assertEqual(target.get_held_item_id("party:1"), 0x8F)
            self.assertEqual(result.canonical_after.held_item.item_id, 0x8F)
            self.assertTrue(target.validate())

    def test_gen3_to_gen1_removes_held_item_and_modern_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            source.set_held_item_id("party:0", 199)
            canonical = source.export_canonical("party:0")
            canonical.ability = "Synchronize"
            canonical.nature = "Timid"

            result = get_converter(3, 1).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertIsNone(result.canonical_after.held_item)
            self.assertIsNone(result.canonical_after.ability)
            self.assertIsNone(result.canonical_after.nature)
            self.assertIn("held_item", result.data_loss)
            self.assertIn("ability", result.data_loss)
            self.assertIn("nature", result.data_loss)
            self.assertTrue(target.validate())

    def test_gen2_to_gen1_removes_held_item_and_reports_data_loss(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            source.set_held_item_id("party:0", 0x52)

            result = get_converter(2, 1).apply_to_save(target, "party:1", source.export_canonical("party:0"))

            self.assertTrue(result.wrote_to_save)
            self.assertIn("held_item", result.data_loss)
            self.assertIsNone(result.canonical_after.held_item)
            self.assertTrue(target.validate())

    def test_gen2_item_trade_species_arrive_in_gen1_without_evolving(self) -> None:
        cases = [
            (61, 0x52, 61, "Poliwhirl"),
            (79, 0x52, 79, "Slowpoke"),
            (95, 0x8F, 95, "Onix"),
            (123, 0x8F, 123, "Scyther"),
            (117, 0x97, 117, "Seadra"),
            (137, 0xAC, 137, "Porygon"),
        ]
        for source_species, item_id, expected_national, expected_name in cases:
            with self.subTest(source=expected_name):
                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
                    target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
                    source.set_species_id("party:0", source_species)
                    source.set_held_item_id("party:0", item_id)

                    conversion = get_converter(2, 1).apply_to_save(
                        target,
                        "party:1",
                        source.export_canonical("party:0"),
                        policy="auto_retrocompat",
                    )
                    evolution = apply_trade_evolution_to_parser(
                        target,
                        "party:1",
                        item_based_evolutions_enabled=True,
                    )

                    self.assertTrue(conversion.wrote_to_save)
                    self.assertIn("held_item", conversion.data_loss)
                    self.assertIsNone(conversion.canonical_after.held_item)
                    self.assertFalse(evolution.evolved)
                    self.assertEqual(target.get_species_id("party:1"), national_to_native(1, expected_national))
                    self.assertEqual(target.list_party()[1].species_name, expected_name)
                    self.assertIsNone(target.get_held_item_id("party:1"))
                    self.assertTrue(target.is_pokedex_caught(expected_national))
                    self.assertTrue(target.validate())

    def test_downconvert_removes_ability_nature_and_reports_data_loss(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            canonical = source.export_canonical("party:0")
            canonical.ability = "Synchronize"
            canonical.nature = "Timid"

            result = get_converter(3, 2).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertIsNone(result.canonical_after.ability)
            self.assertIsNone(result.canonical_after.nature)
            self.assertIn("ability", result.data_loss)
            self.assertIn("nature", result.data_loss)
            self.assertTrue(target.validate())

    def test_incompatible_moves_block_or_are_removed_by_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            canonical = source.export_canonical("party:0")
            canonical.moves = [CanonicalMove(252)]
            converter = get_converter(3, 2)

            strict = converter.can_convert(canonical)
            self.assertFalse(strict.compatible)
            self.assertTrue(any("Fake Out" in reason for reason in strict.blocking_reasons))

            result = converter.apply_to_save(target, "party:1", canonical, policy="permissive")
            self.assertTrue(result.wrote_to_save)
            self.assertEqual(result.compatibility_report.removed_moves, [{"move_id": 252, "name": "Fake Out"}])
            self.assertIn("moves", result.data_loss)
            self.assertEqual(result.canonical_after.moves, [])
            self.assertTrue(target.validate())


if __name__ == "__main__":
    unittest.main()
