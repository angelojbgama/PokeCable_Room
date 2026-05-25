#!/usr/bin/env python3
"""Regressao do utilitario 'Kit de itens' (Gen 1/2).

IDs do kit validados contra pokecable_runtime/data/item_catalog.py.
Pockets/offsets usam os parsers e layouts existentes:
  Gen 1 bag_items 0x25C9, capacidade 20 (pret/pokered wBagItems)
  Gen 2 items/balls/tm_hm por layout Gold/Silver/Crystal (pret/pokecrystal)

Cada caso usa uma copia de save real, prepara espaco na bag da copia, aplica o
utilitario via core, reabre com load_save e confere inventario + checksum.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pokecable_save import load_save, validate_gen1, validate_gen2
from pokecable_runtime.data.inventory_layouts import inventory_layout_for_game
from pokecable_runtime.events.applicator import _get_parser_for_save
from pokecable_runtime.events.save_utilities import GIVE_ITEMS_KIT_BY_GENERATION
import r36s_pokecable_core as core


TEST_SAVES = Path(__file__).resolve().parent.parent / "roms" / "test-saves"
CASES = [
    ("gen 1/Pokémon - Yellow Version.sav", 1),
    ("gen 2/Pokémon - Gold Version.sav", 2),
    ("gen 2/Pokémon - Crystal Version.sav", 2),
]


def _copy_save(tmp_path: Path, subpath: str) -> Path:
    src = TEST_SAVES / subpath
    if not src.exists():
        pytest.skip(f"save ausente: {subpath}")
    work = tmp_path / src.name
    shutil.copy2(src, work)
    return work


def _parser_for(path: Path):
    model = load_save(path)
    parser = _get_parser_for_save(model)
    if parser is None:
        pytest.fail(f"parser indisponivel para {path}")
    return model, parser


def _prepare_room_in_bag(path: Path) -> None:
    model, parser = _parser_for(path)
    layout = inventory_layout_for_game(model.game)
    if model.generation == 1:
        pocket = layout.pocket("bag_items")
        parser._write_counted_item_pairs(pocket.offset, pocket.capacity, [])
    elif model.generation == 2:
        for pocket_name in ("items", "balls"):
            pocket = layout.pocket(pocket_name)
            parser._write_counted_item_pairs(pocket.offset, pocket.capacity, [])
        tmhm = layout.pocket("tm_hm")
        parser.data[tmhm.offset : tmhm.offset + tmhm.size] = b"\x00" * tmhm.size
        parser.recalculate_checksums()
    else:
        pytest.fail(f"geracao inesperada: {model.generation}")
    parser.save(path)


def _bag_inventory_by_id(path: Path) -> dict[int, object]:
    model, parser = _parser_for(path)
    return {
        int(entry.item_id): entry
        for entry in parser.list_inventory()
        if entry.storage == "bag"
    }


@pytest.mark.parametrize("subpath,generation", CASES)
def test_give_items_kit_on_real_saves(tmp_path, monkeypatch, subpath, generation):
    work = _copy_save(tmp_path, subpath)
    monkeypatch.setenv("POKECABLE_BACKUP_DIR", str(tmp_path / "backups"))
    _prepare_room_in_bag(work)

    result = core.apply_utility_to_save(work, "give_items_kit")
    assert result.get("success"), result.get("message")
    assert result.get("kit_size") == len(GIVE_ITEMS_KIT_BY_GENERATION[generation])
    assert result.get("changed_items") == len(GIVE_ITEMS_KIT_BY_GENERATION[generation])

    reloaded = load_save(work)
    assert reloaded.generation == generation
    if generation == 1:
        assert validate_gen1(reloaded.bytes)
    else:
        assert validate_gen2(reloaded.bytes[:0x8000], reloaded.layout)

    inventory = _bag_inventory_by_id(work)
    for spec in GIVE_ITEMS_KIT_BY_GENERATION[generation]:
        item_id = int(spec["item_id"])
        assert item_id in inventory
        assert int(inventory[item_id].quantity) == int(spec["quantity"])

    if generation == 2:
        assert inventory[1].pocket_name == "balls"
        for hm_id in range(243, 250):
            assert inventory[hm_id].pocket_name == "tm_hm"


def test_give_items_kit_is_idempotent(tmp_path, monkeypatch):
    work = _copy_save(tmp_path, "gen 1/Pokémon - Yellow Version.sav")
    monkeypatch.setenv("POKECABLE_BACKUP_DIR", str(tmp_path / "backups"))
    _prepare_room_in_bag(work)

    first = core.apply_utility_to_save(work, "give_items_kit")
    assert first.get("success"), first.get("message")
    before = {item_id: entry.quantity for item_id, entry in _bag_inventory_by_id(work).items()}

    second = core.apply_utility_to_save(work, "give_items_kit")
    assert second.get("success"), second.get("message")
    assert second.get("changed_items") == 0
    assert second.get("total_quantity_added") == 0
    after = {item_id: entry.quantity for item_id, entry in _bag_inventory_by_id(work).items()}
    assert after == before


def test_give_items_kit_listed_only_for_gen1_gen2():
    for subpath, _generation in CASES:
        path = TEST_SAVES / subpath
        if not path.exists():
            continue
        ids = {utility["id"] for utility in core.get_available_utilities(path).get("utilities", [])}
        assert "give_items_kit" in ids

    gen3 = TEST_SAVES / "gen 3" / "Pokémon - FireRed Version.sav"
    if gen3.exists():
        ids = {utility["id"] for utility in core.get_available_utilities(gen3).get("utilities", [])}
        assert "give_items_kit" not in ids
