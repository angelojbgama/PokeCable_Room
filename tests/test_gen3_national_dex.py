#!/usr/bin/env python3
"""Regressao do utilitario 'Destravar National Dex' (Gen 3).

Cada caso usa uma copia de save real, aplica o utilitario via core, reabre com
load_save para validar checksums e confere os campos usados pelo jogo:
SaveBlock2.pokedex order/mode/nationalMagic, VAR_NATIONAL_DEX e
FLAG_SYS_NATIONAL_DEX.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pokecable_save import (
    GEN3_NATIONAL_DEX_MAGIC,
    GEN3_NATIONAL_DEX_MODE,
    GEN3_NATIONAL_DEX_ORDER,
    GEN3_NATIONAL_DEX_VAR_INDEX,
    GEN3_NATIONAL_DEX_VAR_VALUE,
    load_save,
)
from pokecable_runtime.events.applicator import _get_event_flag_offset, _read_gen3_saveblock1
import r36s_pokecable_core as core


TEST_SAVES = Path(__file__).resolve().parent.parent / "roms" / "test-saves"
GEN3_DIR = TEST_SAVES / "gen 3"

# (filename, game group, SaveBlock1 vars base, FLAG_SYS_NATIONAL_DEX)
CASES = [
    ("Pokémon - FireRed Version.sav", "frlg", 0x1000, 0x840),
    ("Pokémon - LeafGreen Version.sav", "frlg", 0x1000, 0x840),
    ("Pokémon - Emerald Version.sav", "emerald", 0x139C, 0x896),
    ("Pokémon - Ruby Version.sav", "rs", 0x1340, 0x836),
    ("Pokémon - Sapphire Version.sav", "rs", 0x1340, 0x836),
]


def _copy_save(tmp_path: Path, filename: str) -> Path:
    src = GEN3_DIR / filename
    if not src.exists():
        pytest.skip(f"save ausente: {filename}")
    work = tmp_path / filename
    shutil.copy2(src, work)
    return work


def _flag_is_set(model, flag_id: int) -> bool:
    offset = _get_event_flag_offset(model) + flag_id // 8
    byte = _read_gen3_saveblock1(model, offset, 1)[0]
    return bool(byte & (1 << (flag_id % 8)))


@pytest.mark.parametrize("filename,group,var_base,flag_id", CASES)
def test_gen3_national_dex_unlock_on_real_saves(tmp_path, monkeypatch, filename, group, var_base, flag_id):
    work = _copy_save(tmp_path, filename)
    monkeypatch.setenv("POKECABLE_BACKUP_DIR", str(tmp_path / "backups"))

    result = core.apply_utility_to_save(work, "gen3_national_dex")
    assert result.get("success"), result.get("message")
    assert result.get("game_group") == group
    assert result.get("flag_id") == flag_id

    reloaded = load_save(work)
    assert reloaded.generation == 3

    sec0 = reloaded.slot["section_offsets"][0]
    assert reloaded.bytes[sec0 + 0x18] == GEN3_NATIONAL_DEX_ORDER
    assert reloaded.bytes[sec0 + 0x19] == GEN3_NATIONAL_DEX_MODE
    assert reloaded.bytes[sec0 + 0x1A] == GEN3_NATIONAL_DEX_MAGIC

    var_offset = var_base + GEN3_NATIONAL_DEX_VAR_INDEX * 2
    assert result.get("var_offset") == var_offset
    assert int.from_bytes(_read_gen3_saveblock1(reloaded, var_offset, 2), "little") == GEN3_NATIONAL_DEX_VAR_VALUE
    assert _flag_is_set(reloaded, flag_id)


def test_gen3_national_dex_listed_only_for_gen3():
    for filename, _group, _var_base, _flag_id in CASES:
        path = GEN3_DIR / filename
        if not path.exists():
            continue
        ids = {utility["id"] for utility in core.get_available_utilities(path).get("utilities", [])}
        assert "gen3_national_dex" in ids

    for subpath in ("gen 1/Pokémon - Yellow Version.sav", "gen 2/Pokémon - Crystal Version.sav"):
        path = TEST_SAVES / subpath
        if not path.exists():
            continue
        ids = {utility["id"] for utility in core.get_available_utilities(path).get("utilities", [])}
        assert "gen3_national_dex" not in ids
