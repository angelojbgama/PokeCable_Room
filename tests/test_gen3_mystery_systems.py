#!/usr/bin/env python3
"""Regression for the Gen 3 Mystery Gift/Event flag utility.

Each case edits a copy of a real save: clear the target flag(s), write/reload
to validate checksums, apply the utility through core, then reload and confirm
that the expected game-specific bits are set.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pokecable_save import load_save
from pokecable_runtime.events.applicator import (
    _get_event_flag_offset,
    _read_gen3_saveblock1,
    _write_gen3_saveblock1,
)
import r36s_pokecable_core as core


TEST_SAVES = Path(__file__).resolve().parent.parent / "roms" / "test-saves"
GEN3_DIR = TEST_SAVES / "gen 3"

# (filename, game group, expected system flags)
CASES = [
    ("Pokémon - FireRed Version.sav", "frlg", (0x839,)),
    ("Pokémon - LeafGreen Version.sav", "frlg", (0x839,)),
    ("Pokémon - Emerald Version.sav", "emerald", (0x8AC, 0x8DB)),
    ("Pokémon - Ruby Version.sav", "rs", (0x84C,)),
    ("Pokémon - Sapphire Version.sav", "rs", (0x84C,)),
]


def _copy_save(tmp_path: Path, filename: str) -> Path:
    src = GEN3_DIR / filename
    if not src.exists():
        pytest.skip(f"save missing: {filename}")
    work = tmp_path / filename
    shutil.copy2(src, work)
    return work


def _flag_is_set(model, flag_id: int) -> bool:
    offset = _get_event_flag_offset(model) + flag_id // 8
    byte = _read_gen3_saveblock1(model, offset, 1)[0]
    return bool(byte & (1 << (flag_id % 8)))


def _clear_flag(model, flag_id: int) -> None:
    offset = _get_event_flag_offset(model) + flag_id // 8
    current = _read_gen3_saveblock1(model, offset, 1)[0]
    _write_gen3_saveblock1(model, offset, bytes([current & ~(1 << (flag_id % 8))]))


@pytest.mark.parametrize("filename,group,flag_ids", CASES)
def test_gen3_mystery_systems_sets_verified_flags(tmp_path, monkeypatch, filename, group, flag_ids):
    work = _copy_save(tmp_path, filename)
    monkeypatch.setenv("POKECABLE_BACKUP_DIR", str(tmp_path / "backups"))

    model = load_save(work)
    for flag_id in flag_ids:
        _clear_flag(model, flag_id)
    model.write_to_disk()

    baseline = load_save(work)
    for flag_id in flag_ids:
        assert not _flag_is_set(baseline, flag_id)

    result = core.apply_utility_to_save(work, "gen3_mystery_systems")
    assert result.get("success"), result.get("message")
    assert result.get("game_group") == group
    assert result.get("flag_ids") == list(flag_ids)

    reloaded = load_save(work)
    assert reloaded.generation == 3
    for flag_id in flag_ids:
        assert _flag_is_set(reloaded, flag_id)


def test_gen3_mystery_systems_listed_only_for_gen3():
    for filename, _group, _flag_ids in CASES:
        path = GEN3_DIR / filename
        if not path.exists():
            continue
        ids = {utility["id"] for utility in core.get_available_utilities(path).get("utilities", [])}
        assert "gen3_mystery_systems" in ids

    for subpath in ("gen 1/Pokémon - Yellow Version.sav", "gen 2/Pokémon - Crystal Version.sav"):
        path = TEST_SAVES / subpath
        if not path.exists():
            continue
        ids = {utility["id"] for utility in core.get_available_utilities(path).get("utilities", [])}
        assert "gen3_mystery_systems" not in ids
