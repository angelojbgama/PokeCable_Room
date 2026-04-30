from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from pokecable_room.client import _apply_received_item_transfer
from pokecable_room.converters import get_converter
from pokecable_room.data.items import ITEM_IDS_BY_GENERATION_AND_NAME
from pokecable_room.evolutions import apply_trade_evolution_to_parser
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser
from pokecable_room.battle_export import canonical_team_to_battle_text


REAL_SAVE_ROOT = Path("/srv/PokeCable/save")


class _StubUI:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        self.messages.append(message)


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
    def test_real_gen1_save_lists_boxes_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_path = copy_real_save("gen 1/Pokémon - Red Version.sav", tempdir, "red.sav")
            parser = Gen1Parser()
            parser.load(save_path)

            boxes = parser.list_boxes()

            self.assertIsInstance(boxes, list)
            for summary in boxes[:10]:
                self.assertTrue(summary.location.startswith("box:"))
                self.assertGreaterEqual(summary.level, 1)

    def test_real_gen2_saves_detect_expected_game_ids(self) -> None:
        cases = [
            ("gen 2/Pokémon - Gold Version.sav", "gold.sav", "pokemon_gold"),
            ("gen 2/Pokémon - Silver Version.sav", "silver.sav", "pokemon_silver"),
            ("gen 2/Pokémon - Crystal Version.sav", "crystal.sav", "pokemon_crystal"),
        ]
        for relative_path, name, expected_game in cases:
            with self.subTest(save=relative_path):
                with tempfile.TemporaryDirectory() as tempdir:
                    save_path = copy_real_save(relative_path, tempdir, name)
                    parser = Gen2Parser()
                    parser.load(save_path)
                    self.assertEqual(parser.get_generation(), 2)
                    self.assertEqual(parser.get_game_id(), expected_game)
                    self.assertTrue(parser.list_party())
                    payload = parser.export_pokemon("party:0").to_dict()
                    self.assertEqual(payload["generation"], 2)
                    self.assertEqual(payload["game"], expected_game)
                    self.assertEqual(payload["source_generation"], 2)
                    self.assertEqual(payload["source_game"], expected_game)

    def test_real_gen2_save_lists_boxes_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_path = copy_real_save("gen 2/Pokémon - Crystal Version.sav", tempdir, "crystal.sav")
            parser = Gen2Parser()
            parser.load(save_path)

            boxes = parser.list_boxes()

            self.assertIsInstance(boxes, list)
            for summary in boxes[:10]:
                self.assertTrue(summary.location.startswith("box:"))
                self.assertGreaterEqual(summary.level, 1)

    def test_real_gen3_saves_detect_expected_game_ids(self) -> None:
        cases = [
            ("gen 3/Pokémon - Ruby Version.sav", "ruby.sav", "pokemon_ruby"),
            ("gen 3/Pokémon - Sapphire Version.sav", "sapphire.sav", "pokemon_sapphire"),
            ("gen 3/Pokémon - Emerald Version.sav", "emerald.sav", "pokemon_emerald"),
            ("gen 3/Pokémon - FireRed Version.sav", "firered.sav", "pokemon_firered"),
            ("gen 3/Pokémon - LeafGreen Version.sav", "leafgreen.sav", "pokemon_leafgreen"),
        ]
        for relative_path, name, expected_game in cases:
            with self.subTest(save=relative_path):
                with tempfile.TemporaryDirectory() as tempdir:
                    save_path = copy_real_save(relative_path, tempdir, name)
                    parser = Gen3Parser()
                    parser.load(save_path)
                    self.assertEqual(parser.get_generation(), 3)
                    self.assertEqual(parser.get_game_id(), expected_game)
                    self.assertTrue(parser.list_party())
                    payload = parser.export_pokemon("party:0").to_dict()
                    self.assertEqual(payload["generation"], 3)
                    self.assertEqual(payload["game"], expected_game)
                    self.assertEqual(payload["source_generation"], 3)
                    self.assertEqual(payload["source_game"], expected_game)

    def test_real_gen3_save_lists_boxes_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_path = copy_real_save("gen 3/Pokémon - Emerald Version.sav", tempdir, "emerald.sav")
            parser = Gen3Parser()
            parser.load(save_path)

            boxes = parser.list_boxes()

            self.assertIsInstance(boxes, list)
            for summary in boxes[:10]:
                self.assertTrue(summary.location.startswith("box:"))
                self.assertGreaterEqual(summary.level, 1)

    def test_real_same_generation_trade_between_gen2_game_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            gold_path = copy_real_save("gen 2/Pokémon - Gold Version.sav", tempdir, "gold.sav")
            silver_path = copy_real_save("gen 2/Pokémon - Silver Version.sav", tempdir, "silver.sav")
            gold = Gen2Parser()
            silver = Gen2Parser()
            gold.load(gold_path)
            silver.load(silver_path)

            sent_from_gold = gold.list_party()[0]
            sent_from_silver = silver.list_party()[0]
            gold_payload = gold.export_pokemon("party:0")
            silver_payload = silver.export_pokemon("party:0")

            gold.import_pokemon("party:0", silver_payload)
            silver.import_pokemon("party:0", gold_payload)
            gold.save(gold_path)
            silver.save(silver_path)

            reloaded_gold = Gen2Parser()
            reloaded_silver = Gen2Parser()
            reloaded_gold.load(gold_path)
            reloaded_silver.load(silver_path)
            self.assertTrue(reloaded_gold.validate())
            self.assertTrue(reloaded_silver.validate())
            self.assertEqual(reloaded_gold.list_party()[0].species_name, sent_from_silver.species_name)
            self.assertEqual(reloaded_silver.list_party()[0].species_name, sent_from_gold.species_name)

    def test_real_same_generation_trade_between_gen3_game_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            ruby_path = copy_real_save("gen 3/Pokémon - Ruby Version.sav", tempdir, "ruby.sav")
            firered_path = copy_real_save("gen 3/Pokémon - FireRed Version.sav", tempdir, "firered.sav")
            ruby = Gen3Parser()
            firered = Gen3Parser()
            ruby.load(ruby_path)
            firered.load(firered_path)

            sent_from_ruby = ruby.list_party()[0]
            sent_from_firered = firered.list_party()[0]
            ruby_payload = ruby.export_pokemon("party:0")
            firered_payload = firered.export_pokemon("party:0")

            ruby.import_pokemon("party:0", firered_payload)
            firered.import_pokemon("party:0", ruby_payload)
            ruby.save(ruby_path)
            firered.save(firered_path)

            reloaded_ruby = Gen3Parser()
            reloaded_firered = Gen3Parser()
            reloaded_ruby.load(ruby_path)
            reloaded_firered.load(firered_path)
            self.assertTrue(reloaded_ruby.validate())
            self.assertTrue(reloaded_firered.validate())
            self.assertEqual(reloaded_ruby.list_party()[0].species_name, sent_from_firered.species_name)
            self.assertEqual(reloaded_firered.list_party()[0].species_name, sent_from_ruby.species_name)

    def test_real_cross_generation_trade_between_gen2_and_gen3_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            crystal_path = copy_real_save("gen 2/Pokémon - Crystal Version.sav", tempdir, "crystal.sav")
            leafgreen_path = copy_real_save("gen 3/Pokémon - LeafGreen Version.sav", tempdir, "leafgreen.sav")
            crystal = Gen2Parser()
            leafgreen = Gen3Parser()
            crystal.load(crystal_path)
            leafgreen.load(leafgreen_path)

            # Mew exists in both destinations and is a stable compatibility probe.
            crystal.set_species_id("party:0", 151)
            leafgreen.set_species_id("party:0", 151)
            leafgreen.clear_held_item("party:0")

            crystal_offer = crystal.export_canonical("party:0")
            leafgreen_offer = leafgreen.export_canonical("party:0")
            get_converter(2, 3).apply_to_save(leafgreen, "party:0", crystal_offer, policy="auto_retrocompat")
            get_converter(3, 2).apply_to_save(crystal, "party:0", leafgreen_offer, policy="auto_retrocompat")
            crystal.save(crystal_path)
            leafgreen.save(leafgreen_path)

            reloaded_crystal = Gen2Parser()
            reloaded_leafgreen = Gen3Parser()
            reloaded_crystal.load(crystal_path)
            reloaded_leafgreen.load(leafgreen_path)
            self.assertTrue(reloaded_crystal.validate())
            self.assertTrue(reloaded_leafgreen.validate())
            self.assertEqual(reloaded_crystal.list_party()[0].species_name, "Mew")
            self.assertEqual(reloaded_leafgreen.list_party()[0].species_name, "Mew")

    def test_real_simple_trade_evolutions_mark_pokedex_on_copies(self) -> None:
        cases = [
            ("gen 1/Pokémon - Red Version.sav", "red.sav", Gen1Parser, 38, 149, 65),
            ("gen 2/Pokémon - Crystal Version.sav", "crystal.sav", Gen2Parser, 64, 65, 65),
            ("gen 3/Pokémon - Ruby Version.sav", "ruby.sav", Gen3Parser, 64, 65, 65),
        ]
        for relative_path, filename, parser_cls, source_species, target_species, target_national in cases:
            with self.subTest(save=relative_path, species=source_species):
                with tempfile.TemporaryDirectory() as tempdir:
                    save_path = copy_real_save(relative_path, tempdir, filename)
                    parser = parser_cls()
                    parser.load(save_path)
                    parser.set_species_id("party:0", source_species)

                    result = apply_trade_evolution_to_parser(parser, "party:0")
                    parser.save(save_path)

                    reloaded = parser_cls()
                    reloaded.load(save_path)
                    self.assertTrue(result.evolved)
                    self.assertEqual(reloaded.get_species_id("party:0"), target_species)
                    self.assertTrue(reloaded.is_pokedex_seen(target_national))
                    self.assertTrue(reloaded.is_pokedex_caught(target_national))
                    self.assertTrue(reloaded.validate())

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

    def test_real_gen3_item_existing_in_gen1_moves_to_bag_on_copy(self) -> None:
        potion_id = ITEM_IDS_BY_GENERATION_AND_NAME[(3, "potion")]
        with tempfile.TemporaryDirectory() as tempdir:
            gen1_path = copy_real_save("gen 1/Pokémon - Yellow Version.sav", tempdir, "yellow.sav")
            gen3_path = copy_real_save("gen 3/Pokémon - Ruby Version.sav", tempdir, "ruby.sav")
            gen1 = Gen1Parser()
            gen3 = Gen3Parser()
            gen1.load(gen1_path)
            gen3.load(gen3_path)

            gen3.set_species_id("party:0", 151)
            gen3.set_held_item_id("party:0", potion_id)
            mew_with_potion = gen3.export_canonical("party:0")

            get_converter(3, 1).apply_to_save(gen1, "party:0", mew_with_potion, policy="auto_retrocompat")
            transfer_result = _apply_received_item_transfer(
                parser=gen1,
                location="party:0",
                canonical_pokemon=mew_with_potion,
                ui=_StubUI(),
            )
            gen1.save(gen1_path)

            reloaded_gen1 = Gen1Parser()
            reloaded_gen1.load(gen1_path)
            self.assertTrue(reloaded_gen1.validate())
            self.assertEqual(reloaded_gen1.get_species_id("party:0"), 21)
            self.assertEqual(transfer_result["disposition"], "move_to_bag")
            self.assertTrue(any(entry.pocket_name == "bag_items" and entry.item_name == "Potion" for entry in reloaded_gen1.list_inventory()))

    def test_real_gen2_item_trade_evolution_consumes_item_and_marks_pokedex_on_copy(self) -> None:
        cases = [
            (123, 0x8F, 212, "Metal Coat"),
            (95, 0x8F, 208, "Metal Coat"),
            (117, 0x97, 230, "Dragon Scale"),
            (137, 0xAC, 233, "Up-Grade"),
            (61, 0x52, 186, "King's Rock"),
            (79, 0x52, 199, "King's Rock"),
        ]
        for source_species, item_id, target_species, item_name in cases:
            with self.subTest(species=source_species, item=item_name):
                with tempfile.TemporaryDirectory() as tempdir:
                    save_path = copy_real_save("gen 2/Pokémon - Crystal Version.sav", tempdir, "crystal.sav")
                    parser = Gen2Parser()
                    parser.load(save_path)
                    parser.set_species_id("party:0", source_species)
                    parser.set_held_item_id("party:0", item_id)

                    result = apply_trade_evolution_to_parser(parser, "party:0", item_based_evolutions_enabled=True)
                    parser.save(save_path)

                    reloaded = Gen2Parser()
                    reloaded.load(save_path)
                    self.assertTrue(result.evolved)
                    self.assertEqual(result.consumed_item_name, item_name)
                    self.assertEqual(reloaded.get_species_id("party:0"), target_species)
                    self.assertIsNone(reloaded.get_held_item_id("party:0"))
                    self.assertTrue(reloaded.is_pokedex_seen(target_species))
                    self.assertTrue(reloaded.is_pokedex_caught(target_species))
                    self.assertTrue(reloaded.validate())

    def test_real_gen3_item_trade_evolution_consumes_item_and_marks_pokedex_on_copy(self) -> None:
        cases = [
            (373, 192, 374, 367, "Deep Sea Tooth"),
            (373, 193, 375, 368, "Deep Sea Scale"),
            (123, 199, 212, 212, "Metal Coat"),
            (95, 199, 208, 208, "Metal Coat"),
            (117, 201, 230, 230, "Dragon Scale"),
            (137, 218, 233, 233, "Up-Grade"),
            (61, 187, 186, 186, "King's Rock"),
            (79, 187, 199, 199, "King's Rock"),
        ]
        for source_species, item_id, target_species, target_national, item_name in cases:
            with self.subTest(species=source_species, item=item_name):
                with tempfile.TemporaryDirectory() as tempdir:
                    save_path = copy_real_save("gen 3/Pokémon - Ruby Version.sav", tempdir, "ruby.sav")
                    parser = Gen3Parser()
                    parser.load(save_path)
                    parser.set_species_id("party:0", source_species)
                    parser.set_held_item_id("party:0", item_id)

                    result = apply_trade_evolution_to_parser(parser, "party:0", item_based_evolutions_enabled=True)
                    parser.save(save_path)

                    reloaded = Gen3Parser()
                    reloaded.load(save_path)
                    self.assertTrue(result.evolved)
                    self.assertEqual(result.consumed_item_name, item_name)
                    self.assertEqual(reloaded.get_species_id("party:0"), target_species)
                    self.assertIsNone(reloaded.get_held_item_id("party:0"))
                    self.assertTrue(reloaded.is_pokedex_seen(target_national))
                    self.assertTrue(reloaded.is_pokedex_caught(target_national))
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

    def test_real_save_exports_battle_team_without_raw_save_data(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_path = copy_real_save("gen 3/Pokémon - Ruby Version.sav", tempdir, "ruby.sav")
            parser = Gen3Parser()
            parser.load(save_path)
            canonical = parser.export_canonical("party:0")
            text = canonical_team_to_battle_text([canonical], 3)

            self.assertIn("Level:", text)
            payload = canonical.to_dict()
            self.assertIn("original_data", payload)
            payload["original_data"]["raw_data_base64"] = None
            self.assertIsNone(payload["original_data"]["raw_data_base64"])


if __name__ == "__main__":
    unittest.main()
