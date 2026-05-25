#!/usr/bin/env python3
"""Regressão da utilidade 'Dinheiro + Fichas (máx)' do Gen 1.

Offsets internacionais (confirmados via PKHeX, correlacionados com Party 0x2F2C):
  Money 0x25F3 (BCD big-endian, 3 bytes, máx 999999)
  Coin  0x2850 (BCD big-endian, 2 bytes, máx 9999)
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pokecable_save import load_save, validate_gen1, _bcd_be_to_int, _int_to_bcd_be
import r36s_pokecable_core as core

TEST_SAVES = Path(__file__).resolve().parent.parent / "roms" / "test-saves"
GEN1_DIR = TEST_SAVES / "gen 1"
SAVES = ["Pokémon - Red Version.sav", "Pokémon - Blue Version.sav", "Pokémon - Yellow Version.sav"]


@pytest.mark.parametrize("value,num_bytes,expected_hex", [
    (999999, 3, "999999"),
    (9999, 2, "9999"),
    (1250, 2, "1250"),
    (0, 3, "000000"),
    (123456, 3, "123456"),
])
def test_bcd_roundtrip(value, num_bytes, expected_hex):
    enc = _int_to_bcd_be(value, num_bytes)
    assert enc.hex() == expected_hex
    assert _bcd_be_to_int(enc) == value


@pytest.mark.parametrize("filename", SAVES)
def test_money_coins_max_on_real_save(tmp_path, filename):
    src = GEN1_DIR / filename
    if not src.exists():
        pytest.skip(f"save ausente: {filename}")
    work = tmp_path / filename
    shutil.copy2(src, work)

    # Zera antes para garantir delta visível, recalculando o checksum.
    from pokecable_save import gen1_checksum
    model = load_save(work)
    model.bytes[0x25F3:0x25F6] = b"\x00\x00\x00"
    model.bytes[0x2850:0x2852] = b"\x00\x00"
    model.bytes[0x3523] = gen1_checksum(model.bytes)
    model.write_to_disk()

    result = core.apply_utility_to_save(work, "gen1_money_coins")
    assert result.get("success"), result.get("message")
    assert result.get("money") == 999999
    assert result.get("coins") == 9999

    reloaded = load_save(work)  # reload valida o save
    assert validate_gen1(reloaded.bytes)
    assert _bcd_be_to_int(bytes(reloaded.bytes[0x25F3:0x25F6])) == 999999
    assert _bcd_be_to_int(bytes(reloaded.bytes[0x2850:0x2852])) == 9999


def test_utility_only_listed_for_gen1():
    # Gen 1 lista; Gen 3 não.
    g1 = GEN1_DIR / "Pokémon - Red Version.sav"
    g3 = TEST_SAVES / "gen 3" / "Pokémon - FireRed Version.sav"
    if g1.exists():
        ids = {u["id"] for u in core.get_available_utilities(g1).get("utilities", [])}
        assert "gen1_money_coins" in ids
    if g3.exists():
        ids = {u["id"] for u in core.get_available_utilities(g3).get("utilities", [])}
        assert "gen1_money_coins" not in ids
