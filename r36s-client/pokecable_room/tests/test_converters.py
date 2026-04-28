from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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
            self.assertEqual(target.list_party()[1].species_id, 64)

    def test_gen2_to_gen1_creates_valid_gen1_struct_when_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())

            canonical = source.export_canonical("party:0")
            result = get_converter(2, 1).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            self.assertEqual(target.list_party()[1].species_name, "Onix")

    def test_gen1_to_gen3_creates_valid_gen3_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))

            canonical = source.export_canonical("party:0")
            result = get_converter(1, 3).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            self.assertEqual(target.list_party()[1].species_name, "Kadabra")

    def test_gen2_to_gen3_creates_valid_gen3_struct(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            target = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))

            canonical = source.export_canonical("party:0")
            result = get_converter(2, 3).apply_to_save(target, "party:1", canonical)

            self.assertTrue(result.wrote_to_save)
            self.assertTrue(target.validate())
            self.assertEqual(target.list_party()[1].species_name, "Onix")

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
            self.assertEqual(target.list_party()[1].species_name, "Kadabra")

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
            self.assertEqual(target.list_party()[1].species_name, "Kadabra")


if __name__ == "__main__":
    unittest.main()
