#!/usr/bin/env python3
"""Regressão da utilidade 'Pokédex completa' (Gen 1/2/3).

Offsets validados:
  Gen 1  owned 0x25A3 / seen 0x25B6 (19 bytes, 151 espécies)
  Gen 2  owned/seen via layout (Crystal 0x2A27/0x2A47, GS 0x2A4C/0x2A6C; 32 bytes, 251)
  Gen 3  SaveBlock2 owned +0x28 / seen +0x5C + 2 espelhos de 'seen' (49 bytes)

A utilidade marca a Pokédex regional do jogo como vista+capturada e recalcula
os checksums; o reload via load_save valida implicitamente (Gen 3 levanta em
checksum inválido).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pokecable_save import (
    GEN3_NATIONAL_DEX_MAGIC,
    gen1_checksum,
    gen3_sector_checksum,
    load_save,
    write_gen2_checksums,
    write_u16,
)
import r36s_pokecable_core as core

TEST_SAVES = Path(__file__).resolve().parent.parent / "roms" / "test-saves"

# (subpath, generation, expected species count)
CASES = [
    ("gen 1/Pokémon - Red Version.sav", 1, 151),
    ("gen 1/Pokémon - Blue Version.sav", 1, 151),
    ("gen 2/Pokémon - Crystal Version.sav", 2, 251),
    ("gen 2/Pokémon - Gold Version.sav", 2, 251),
    ("gen 3/Pokémon - FireRed Version.sav", 3, 151),
    ("gen 3/Pokémon - Emerald Version.sav", 3, 202),
    ("gen 3/Pokémon - Ruby Version.sav", 3, 202),
]


def _owned_base_and_len(model):
    if model.generation == 1:
        return 0x25A3, 19
    if model.generation == 2:
        return model.layout["pokedex_owned_offset"], 32
    sec0 = model.slot["section_offsets"][0]
    return sec0 + 0x28, 49


def _owned_popcount(model) -> int:
    base, n = _owned_base_and_len(model)
    return sum(bin(model.bytes[base + i]).count("1") for i in range(n))


def _owned_has(model, national_dex_id: int) -> bool:
    base, _ = _owned_base_and_len(model)
    dex_idx = int(national_dex_id) - 1
    return bool(model.bytes[base + (dex_idx >> 3)] & (1 << (dex_idx & 7)))


def _load(subpath: str):
    path = TEST_SAVES / subpath
    if not path.exists():
        pytest.skip(f"save de teste ausente: {subpath}")
    try:
        return load_save(path)
    except Exception as exc:
        pytest.skip(f"save não carregou ({subpath}): {exc}")


def _clear_pokedex(path: Path) -> None:
    model = load_save(path)
    if model.generation == 1:
        for base in (0x25A3, 0x25B6):
            model.bytes[base:base + 19] = b"\x00" * 19
        model.bytes[0x3523] = gen1_checksum(model.bytes)
    elif model.generation == 2:
        owned = model.layout["pokedex_owned_offset"]
        seen = model.layout["pokedex_seen_offset"]
        model.bytes[owned:owned + 32] = b"\x00" * 32
        model.bytes[seen:seen + 32] = b"\x00" * 32
        write_gen2_checksums(model.bytes, model.layout)
    elif model.generation == 3:
        section_offsets = model.slot["section_offsets"]
        sec0 = section_offsets[0]
        sec1 = section_offsets[1]
        sec4 = section_offsets[4]
        is_frlg = model.game in ("pokemon_firered", "pokemon_leafgreen")
        is_emerald = model.game == "pokemon_emerald"
        seen_b = 0x05F8 if is_frlg else (0x0988 if is_emerald else 0x0938)
        seen_c = 0x0B98 if is_frlg else (0x0CA4 if is_emerald else 0x0C0C)
        model.bytes[sec0 + 0x18:sec0 + 0x1B] = b"\x00\x00\x00"
        for base in (sec0 + 0x28, sec0 + 0x5C, sec1 + seen_b, sec4 + seen_c):
            model.bytes[base:base + 49] = b"\x00" * 49
        for section in (sec0, sec1, sec4):
            write_u16(model.bytes, section + 0xFF6, gen3_sector_checksum(model.bytes, section))
    else:
        pytest.fail(f"geração inesperada: {model.generation}")
    model.write_to_disk()


@pytest.mark.parametrize("subpath,generation,expected", CASES)
def test_complete_pokedex_marks_game_dex_only(tmp_path, monkeypatch, subpath, generation, expected):
    src = TEST_SAVES / subpath
    if not src.exists():
        pytest.skip(f"save ausente: {subpath}")
    work = tmp_path / src.name
    shutil.copy2(src, work)
    monkeypatch.setenv("POKECABLE_BACKUP_DIR", str(tmp_path / "backups"))

    _clear_pokedex(work)

    result = core.apply_utility_to_save(work, "pokedex_complete")
    assert result.get("success"), f"apply falhou: {result.get('message')}"
    assert result.get("count") == expected

    # reload valida checksums; dex regional deve estar completa
    reloaded = load_save(work)
    assert reloaded.generation == generation
    assert _owned_popcount(reloaded) == expected
    if generation == 3:
        sec0 = reloaded.slot["section_offsets"][0]
        assert reloaded.bytes[sec0 + 0x1A] != GEN3_NATIONAL_DEX_MAGIC
        if reloaded.game in ("pokemon_firered", "pokemon_leafgreen"):
            assert _owned_has(reloaded, 150)
            assert not _owned_has(reloaded, 252)
        else:
            assert _owned_has(reloaded, 252)
            assert _owned_has(reloaded, 386)
            assert not _owned_has(reloaded, 1)


def test_utility_listed_for_each_generation():
    for subpath, generation, _ in CASES:
        model = _load(subpath)
        res = core.get_available_utilities(model.path)
        ids = {u["id"] for u in res.get("utilities", [])}
        assert "pokedex_complete" in ids, f"não listado para gen{generation} ({subpath})"
