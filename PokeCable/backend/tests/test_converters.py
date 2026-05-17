from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical import CanonicalMove
from converters import get_converter
from data.species import national_to_native
from evolutions import apply_trade_evolution_to_parser
from parsers.gen1 import Gen1Parser, PARTY_MON_OFFSET as GEN1_PARTY_MON_OFFSET
from parsers.gen2 import CRYSTAL_LAYOUT, Gen2Parser
from parsers.gen3 import Gen3Parser

from test_gen1_synthetic import synthetic_save as synthetic_gen1_save
from test_gen1_synthetic import write_checksum as write_gen1_checksum
from test_gen2_parser import synthetic_save as synthetic_gen2_save
from test_gen2_parser import write_checksum as write_gen2_checksum
from test_gen3_parser import synthetic_save as synthetic_gen3_save


def _gen1_with_tackle_pp(pp: int = 35) -> bytes:
    data = bytearray(synthetic_gen1_save())
    start = GEN1_PARTY_MON_OFFSET
    data[start + 0x08] = 33
    data[start + 0x1D] = pp
    write_gen1_checksum(data)
    return bytes(data)


def _gen2_with_tackle_pp(pp: int = 35, shiny: bool = False) -> bytes:
    data = bytearray(synthetic_gen2_save())
    start = CRYSTAL_LAYOUT.party_data_offset
    data[start + 0x02] = 33
    data[start + 0x17] = pp
    if shiny:
        data[start + 0x15] = 0xAA
        data[start + 0x16] = 0xAA
    write_gen2_checksum(data)
    return bytes(data)


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
                    evolution = apply_trade_evolution_to_parser(target, "party:1")

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
            self.assertEqual(result.compatibility_report.removed_moves[0]["move_id"], 252)
            self.assertEqual(result.compatibility_report.removed_moves[0]["name"], "Fake Out")
            self.assertIn("valid_replacements", result.compatibility_report.removed_moves[0])
            self.assertIn("moves", result.data_loss)
            self.assertEqual(result.canonical_after.moves, [])
            self.assertTrue(target.validate())

    def test_gen1_to_gen3_writes_nonzero_pp(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen1Parser, root / "red.sav", _gen1_with_tackle_pp())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))

            get_converter(1, 3).apply_to_save(target, "party:1", source.export_canonical("party:0"))
            canonical = target.export_canonical("party:1")

            self.assertEqual(canonical.moves[0].move_id, 33)
            self.assertGreater(canonical.moves[0].pp or 0, 0)
            self.assertEqual(canonical.moves[0].max_pp, 35)

    def test_gen2_to_gen1_writes_nonzero_pp(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", _gen2_with_tackle_pp())
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())

            get_converter(2, 1).apply_to_save(target, "party:1", source.export_canonical("party:0"))
            canonical = target.export_canonical("party:1")

            self.assertEqual(canonical.moves[0].move_id, 33)
            self.assertGreater(canonical.moves[0].pp or 0, 0)

    def test_resolved_and_fallback_moves_get_valid_pp(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            canonical = source.export_canonical("party:0")
            canonical.moves = [CanonicalMove(move_id=252, source_generation=3)]

            get_converter(3, 2).apply_to_save(
                target,
                "party:1",
                canonical,
                policy="auto_retrocompat",
                resolved_moves={252: 33},
            )
            resolved = target.export_canonical("party:1")
            self.assertEqual(resolved.moves[0].move_id, 33)
            self.assertGreater(resolved.moves[0].pp or 0, 0)

            get_converter(3, 2).apply_to_save(target, "party:1", canonical, policy="auto_retrocompat")
            fallback = target.export_canonical("party:1")
            self.assertEqual(fallback.moves[0].move_id, 1)
            self.assertGreater(fallback.moves[0].pp or 0, 0)

    def test_gen2_shiny_exports_and_stays_shiny_in_gen3(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", _gen2_with_tackle_pp(shiny=True))
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            canonical = source.export_canonical("party:0")

            self.assertTrue(canonical.metadata["is_shiny"])
            get_converter(2, 3).apply_to_save(target, "party:1", canonical)

            self.assertTrue(target.export_canonical("party:1").metadata["is_shiny"])

    def test_gen3_shiny_import_to_gen2_writes_shiny_dvs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            target = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            canonical = source.export_canonical("party:0")
            canonical.metadata["is_shiny"] = True
            canonical.moves = [CanonicalMove(move_id=33, pp=35, max_pp=35, source_generation=3)]

            get_converter(3, 2).apply_to_save(target, "party:1", canonical)

            self.assertTrue(target.export_canonical("party:1").metadata["is_shiny"])
            mon = target._mon_bytes(1)
            self.assertEqual(mon[0x15], 0xAA)
            self.assertEqual(mon[0x16], 0xAA)

    def test_non_shiny_stays_non_shiny_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", _gen2_with_tackle_pp())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))

            self.assertFalse(source.export_canonical("party:0").metadata["is_shiny"])
            get_converter(2, 3).apply_to_save(target, "party:1", source.export_canonical("party:0"))

            self.assertFalse(target.export_canonical("party:1").metadata["is_shiny"])


if __name__ == "__main__":
    unittest.main()
