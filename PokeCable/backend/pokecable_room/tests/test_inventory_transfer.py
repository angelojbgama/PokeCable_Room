from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.canonical import CanonicalItem, CanonicalPokemon, CanonicalSpecies
from pokecable_room.client import _apply_received_item_transfer
from pokecable_room.data.items import ITEM_IDS_BY_GENERATION_AND_NAME
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser
from pokecable_room.tests.test_gen1_synthetic import synthetic_save as synthetic_gen1_save
from pokecable_room.tests.test_gen2_parser import synthetic_save as synthetic_gen2_save
from pokecable_room.tests.test_gen3_parser import synthetic_save as synthetic_gen3_save


class _StubUI:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        self.messages.append(message)


def _canonical_with_item(*, generation: int, game: str, national_id: int, species_name: str, item_id: int, item_name: str) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=generation,
        source_game=game,
        species_national_id=national_id,
        species_name=species_name,
        nickname=species_name.upper()[:10],
        level=30,
        ot_name="ASH",
        trainer_id=12345,
        held_item=CanonicalItem(item_id=item_id, name=item_name, source_generation=generation),
        species=CanonicalSpecies(
            national_dex_id=national_id,
            source_species_id=national_id,
            source_species_id_space="national_dex",
            name=species_name,
        ),
    )


class InventoryTransferTests(unittest.TestCase):
    def test_gen1_inventory_store_item_in_bag_and_pc(self) -> None:
        potion_id = ITEM_IDS_BY_GENERATION_AND_NAME[(1, "potion")]
        max_potion_id = ITEM_IDS_BY_GENERATION_AND_NAME[(1, "max potion")]
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "red.sav"
            save.write_bytes(synthetic_gen1_save())
            parser = Gen1Parser()
            parser.load(save)

            bag_result = parser.store_item_in_bag(potion_id, 1)
            pc_result = parser.store_item_in_pc(max_potion_id, 1)
            inventory = parser.list_inventory()

            self.assertEqual(bag_result.pocket_name, "bag_items")
            self.assertEqual(pc_result.pocket_name, "pc_items")
            self.assertTrue(any(entry.pocket_name == "bag_items" and entry.item_id == potion_id for entry in inventory))
            self.assertTrue(any(entry.pocket_name == "pc_items" and entry.item_id == max_potion_id for entry in inventory))

    def test_gen2_inventory_routes_items_to_expected_pockets(self) -> None:
        metal_coat_id = ITEM_IDS_BY_GENERATION_AND_NAME[(2, "metal coat")]
        master_ball_id = ITEM_IDS_BY_GENERATION_AND_NAME[(2, "master ball")]
        tm01_id = ITEM_IDS_BY_GENERATION_AND_NAME[(2, "tm01")]
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "crystal.sav"
            save.write_bytes(synthetic_gen2_save())
            parser = Gen2Parser()
            parser.load(save)

            parser.store_item_in_bag(metal_coat_id, 1)
            parser.store_item_in_bag(master_ball_id, 1)
            parser.store_item_in_bag(tm01_id, 2)
            inventory = parser.list_inventory()

            self.assertTrue(any(entry.pocket_name == "items" and entry.item_id == metal_coat_id for entry in inventory))
            self.assertTrue(any(entry.pocket_name == "balls" and entry.item_id == master_ball_id for entry in inventory))
            self.assertTrue(any(entry.pocket_name == "tm_hm" and entry.item_id == tm01_id and entry.quantity == 2 for entry in inventory))

    def test_gen3_inventory_routes_items_to_expected_pockets(self) -> None:
        potion_id = ITEM_IDS_BY_GENERATION_AND_NAME[(3, "potion")]
        master_ball_id = ITEM_IDS_BY_GENERATION_AND_NAME[(3, "master ball")]
        cheri_berry_id = ITEM_IDS_BY_GENERATION_AND_NAME[(3, "cheri berry")]
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "emerald.sav"
            save.write_bytes(synthetic_gen3_save("rse"))
            parser = Gen3Parser()
            parser.load(save)

            parser.store_item_in_bag(potion_id, 1)
            parser.store_item_in_bag(master_ball_id, 1)
            parser.store_item_in_bag(cheri_berry_id, 1)
            inventory = parser.list_inventory()

            self.assertTrue(any(entry.pocket_name == "items" and entry.item_id == potion_id for entry in inventory))
            self.assertTrue(any(entry.pocket_name == "balls" and entry.item_id == master_ball_id for entry in inventory))
            self.assertTrue(any(entry.pocket_name == "berries" and entry.item_id == cheri_berry_id for entry in inventory))

    def test_apply_received_item_transfer_moves_existing_item_to_gen1_bag(self) -> None:
        potion_id = ITEM_IDS_BY_GENERATION_AND_NAME[(3, "potion")]
        ui = _StubUI()
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "blue.sav"
            save.write_bytes(synthetic_gen1_save())
            parser = Gen1Parser()
            parser.load(save)

            result = _apply_received_item_transfer(
                parser=parser,
                location="party:0",
                canonical_pokemon=_canonical_with_item(
                    generation=3,
                    game="pokemon_emerald",
                    national_id=151,
                    species_name="Mew",
                    item_id=potion_id,
                    item_name="Potion",
                ),
                ui=ui,
            )

            self.assertEqual(result["disposition"], "move_to_bag")
            self.assertTrue(any(entry.pocket_name == "bag_items" and entry.item_name == "Potion" for entry in parser.list_inventory()))

    def test_apply_received_item_transfer_falls_back_to_pc_when_gen1_bag_is_full(self) -> None:
        potion_id = ITEM_IDS_BY_GENERATION_AND_NAME[(3, "potion")]
        ui = _StubUI()
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "yellow.sav"
            save.write_bytes(synthetic_gen1_save())
            parser = Gen1Parser()
            parser.load(save)

            fill_ids = [item_id for item_id in sorted(parser_generation_item_ids(1)) if item_id != ITEM_IDS_BY_GENERATION_AND_NAME[(1, "potion")]][:20]
            for item_id in fill_ids:
                parser.store_item_in_bag(item_id, 1)

            result = _apply_received_item_transfer(
                parser=parser,
                location="party:0",
                canonical_pokemon=_canonical_with_item(
                    generation=3,
                    game="pokemon_emerald",
                    national_id=151,
                    species_name="Mew",
                    item_id=potion_id,
                    item_name="Potion",
                ),
                ui=ui,
            )

            self.assertEqual(result["disposition"], "move_to_pc")
            self.assertTrue(any(entry.pocket_name == "pc_items" and entry.item_name == "Potion" for entry in parser.list_inventory()))

    def test_apply_received_item_transfer_removes_absent_item(self) -> None:
        deep_sea_tooth_id = ITEM_IDS_BY_GENERATION_AND_NAME[(3, "deep sea tooth")]
        ui = _StubUI()
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "gold.sav"
            save.write_bytes(synthetic_gen2_save())
            parser = Gen2Parser()
            parser.load(save)

            result = _apply_received_item_transfer(
                parser=parser,
                location="party:0",
                canonical_pokemon=_canonical_with_item(
                    generation=3,
                    game="pokemon_emerald",
                    national_id=151,
                    species_name="Mew",
                    item_id=deep_sea_tooth_id,
                    item_name="Deep Sea Tooth",
                ),
                ui=ui,
            )

            self.assertEqual(result["disposition"], "remove")
            self.assertFalse(any(entry.item_name == "Deep Sea Tooth" for entry in parser.list_inventory()))

    def test_apply_received_item_transfer_moves_non_holdable_tm_to_tmhm_pocket(self) -> None:
        tm01_id = ITEM_IDS_BY_GENERATION_AND_NAME[(3, "tm01")]
        ui = _StubUI()
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "ruby.sav"
            save.write_bytes(synthetic_gen3_save("rse"))
            parser = Gen3Parser()
            parser.load(save)
            parser.set_held_item_id("party:0", tm01_id)

            result = _apply_received_item_transfer(
                parser=parser,
                location="party:0",
                canonical_pokemon=_canonical_with_item(
                    generation=3,
                    game="pokemon_ruby",
                    national_id=64,
                    species_name="Kadabra",
                    item_id=tm01_id,
                    item_name="TM01",
                ),
                ui=ui,
            )

            self.assertEqual(result["disposition"], "move_to_bag")
            self.assertTrue(any(entry.pocket_name == "tm_hm" and entry.item_id == tm01_id for entry in parser.list_inventory()))
            self.assertIsNone(parser.get_held_item_id("party:0"))


def parser_generation_item_ids(generation: int) -> list[int]:
    return [item_id for (gen, _name), item_id in ITEM_IDS_BY_GENERATION_AND_NAME.items() if gen == generation]


if __name__ == "__main__":
    unittest.main()
