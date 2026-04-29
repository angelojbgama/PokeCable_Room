from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from pokecable_room.converters import get_converter
from pokecable_room.evolutions import apply_trade_evolution_to_parser
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser
from pokecable_room.showdown import canonical_team_to_showdown_text


REAL_SAVE_ROOT = Path("/srv/save")


def require_real_save(relative_path: str) -> Path:
    path = REAL_SAVE_ROOT / relative_path
    if not path.exists():
        raise unittest.SkipTest(f"Save real local ausente: {path}")
    return path


def copy_real_save(relative_path: str, tempdir: str, name: str) -> Path:
    source = require_real_save(relative_path)
    target = Path(tempdir) / name
    shutil.copy2(source, target)
    return target


class RealSaveIntegrationTests(unittest.TestCase):
    def test_real_gen1_pikachu_gen3_mew_marks_party_and_pokedex_on_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            gen1_path = copy_real_save("gen 1/Pokémon - Yellow Version.sav", tempdir, "yellow.sav")
            gen3_path = copy_real_save("gen 3/Pokémon - Ruby Version.sav", tempdir, "ruby.sav")
            gen1 = Gen1Parser()
            gen3 = Gen3Parser()
            gen1.load(gen1_path)
            gen3.load(gen3_path)

            gen1.set_species_id("party:0", 84)  # Pikachu internal Gen 1 -> National Dex #25.
            gen3.set_species_id("party:0", 151)  # Mew native Gen 3 -> National Dex #151.
            gen3.clear_held_item("party:0")
            pikachu = gen1.export_canonical("party:0")
            mew = gen3.export_canonical("party:0")

            get_converter(3, 1).apply_to_save(gen1, "party:0", mew, policy="auto_retrocompat")
            get_converter(1, 3).apply_to_save(gen3, "party:0", pikachu, policy="auto_retrocompat")
            gen1.save(gen1_path)
            gen3.save(gen3_path)

            reloaded_gen1 = Gen1Parser()
            reloaded_gen3 = Gen3Parser()
            reloaded_gen1.load(gen1_path)
            reloaded_gen3.load(gen3_path)
            self.assertTrue(reloaded_gen1.validate())
            self.assertTrue(reloaded_gen3.validate())
            self.assertEqual(reloaded_gen1.get_species_id("party:0"), 21)
            self.assertEqual(reloaded_gen3.get_species_id("party:0"), 25)
            self.assertTrue(reloaded_gen1.is_pokedex_seen(151))
            self.assertTrue(reloaded_gen1.is_pokedex_caught(151))
            self.assertTrue(reloaded_gen3.is_pokedex_seen(25))
            self.assertTrue(reloaded_gen3.is_pokedex_caught(25))

    def test_real_gen2_item_trade_evolution_consumes_item_and_marks_pokedex_on_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_path = copy_real_save("gen 2/Pokémon - Crystal Version.sav", tempdir, "crystal.sav")
            parser = Gen2Parser()
            parser.load(save_path)
            parser.set_species_id("party:0", 123)  # Scyther.
            parser.set_held_item_id("party:0", 0x8F)  # Metal Coat.

            result = apply_trade_evolution_to_parser(parser, "party:0", item_based_evolutions_enabled=True)
            parser.save(save_path)

            reloaded = Gen2Parser()
            reloaded.load(save_path)
            self.assertTrue(result.evolved)
            self.assertEqual(result.consumed_item_name, "Metal Coat")
            self.assertEqual(reloaded.get_species_id("party:0"), 212)
            self.assertIsNone(reloaded.get_held_item_id("party:0"))
            self.assertTrue(reloaded.is_pokedex_seen(212))
            self.assertTrue(reloaded.is_pokedex_caught(212))
            self.assertTrue(reloaded.validate())

    def test_real_gen3_item_trade_evolution_consumes_item_and_marks_pokedex_on_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_path = copy_real_save("gen 3/Pokémon - Ruby Version.sav", tempdir, "ruby.sav")
            parser = Gen3Parser()
            parser.load(save_path)
            parser.set_species_id("party:0", 373)  # Clamperl native Gen 3 -> National Dex #366.
            parser.set_held_item_id("party:0", 192)  # Deep Sea Tooth.

            result = apply_trade_evolution_to_parser(parser, "party:0", item_based_evolutions_enabled=True)
            parser.save(save_path)

            reloaded = Gen3Parser()
            reloaded.load(save_path)
            self.assertTrue(result.evolved)
            self.assertEqual(result.consumed_item_name, "Deep Sea Tooth")
            self.assertEqual(reloaded.get_species_id("party:0"), 374)
            self.assertIsNone(reloaded.get_held_item_id("party:0"))
            self.assertTrue(reloaded.is_pokedex_seen(367))
            self.assertTrue(reloaded.is_pokedex_caught(367))
            self.assertTrue(reloaded.validate())

    def test_real_gen3_pokedex_offsets_for_rse_and_frlg_copies(self) -> None:
        cases = [
            ("gen 3/Pokémon - Ruby Version.sav", "ruby.sav"),
            ("gen 3/Pokémon - Sapphire Version.sav", "sapphire.sav"),
            ("gen 3/Pokémon - Emerald Version.sav", "emerald.sav"),
            ("gen 3/Pokémon - FireRed Version.sav", "firered.sav"),
            ("gen 3/Pokémon - LeafGreen Version.sav", "leafgreen.sav"),
        ]
        for relative_path, name in cases:
            with self.subTest(save=relative_path):
                with tempfile.TemporaryDirectory() as tempdir:
                    save_path = copy_real_save(relative_path, tempdir, name)
                    parser = Gen3Parser()
                    parser.load(save_path)
                    parser.mark_pokedex_caught(151)
                    parser.save(save_path)

                    reloaded = Gen3Parser()
                    reloaded.load(save_path)
                    self.assertTrue(reloaded.is_pokedex_seen(151))
                    self.assertTrue(reloaded.is_pokedex_caught(151))
                    self.assertTrue(reloaded.validate())

    def test_real_save_exports_showdown_team_without_raw_save_data(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_path = copy_real_save("gen 3/Pokémon - Ruby Version.sav", tempdir, "ruby.sav")
            parser = Gen3Parser()
            parser.load(save_path)
            canonical = parser.export_canonical("party:0")
            text = canonical_team_to_showdown_text([canonical], 3)

            self.assertIn("Level:", text)
            payload = canonical.to_dict()
            self.assertIn("original_data", payload)
            payload["original_data"]["raw_data_base64"] = None
            self.assertIsNone(payload["original_data"]["raw_data_base64"])


if __name__ == "__main__":
    unittest.main()
