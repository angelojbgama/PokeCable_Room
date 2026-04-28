from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.canonical import CanonicalMove
from pokecable_room.converters import get_converter
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
