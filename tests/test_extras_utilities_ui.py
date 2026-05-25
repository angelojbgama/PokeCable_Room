#!/usr/bin/env python3
"""Regressao da UI de Extras para utilitarios de save.

Valida o fluxo incremental da Parte 1:
  listar utilitarios na categoria Extras a partir de save real;
  rotear a categoria "utilities" para a tela correta;
  aplicar um utilitario pela screen e reabrir com load_save.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import r36s_pokecable_core as core
from frontend.screens.controller import ScreenController, register_default_screens
from frontend.screens.menu import ExtrasCategoryScreen, ExtrasUtilitiesScreen
from frontend.session import InputSessionState, UiSessionState
from pokecable_save import _bcd_be_to_int, gen1_checksum, load_save, validate_gen1


TEST_SAVES = Path(__file__).resolve().parent.parent / "roms" / "test-saves"
RED_SAVE = TEST_SAVES / "gen 1" / "Pokémon - Red Version.sav"


class _Services:
    def __init__(self):
        self.switched_to = None
        self.switch_reason = None
        self.back_to = None

    def switch_screen(self, screen_id, reason):
        self.switched_to = screen_id
        self.switch_reason = reason

    def go_back(self, screen_id, reason):
        self.back_to = screen_id
        self.switch_reason = reason


def _copy_red_save(tmp_path: Path) -> Path:
    if not RED_SAVE.exists():
        pytest.skip(f"save ausente: {RED_SAVE}")
    work = tmp_path / RED_SAVE.name
    shutil.copy2(RED_SAVE, work)
    return work


def test_controller_registers_extras_utilities_screen():
    controller = register_default_screens(
        ScreenController(UiSessionState(), InputSessionState(), SimpleNamespace(info=lambda *a, **k: None), 0.0)
    )
    assert "extras_utilities" in controller.screens


def test_extras_category_lists_utilities_for_real_save(tmp_path):
    work = _copy_red_save(tmp_path)
    session = UiSessionState(extras_save_path=work)
    state = SimpleNamespace(language="pt")
    screen = ExtrasCategoryScreen()

    screen._load_events_bg(session, state)

    utility_ids = {utility["id"] for utility in session.extras_utilities}
    assert "utilities" in screen._categories
    assert {"pokedex_complete", "gen1_money_coins"}.issubset(utility_ids)


def test_extras_category_routes_to_utilities_screen():
    session = UiSessionState(menu_index=0)
    state = SimpleNamespace(language="pt")
    screen = ExtrasCategoryScreen()
    screen._categories = ["utilities"]
    services = _Services()

    screen.handle_action("select", None, session, state, services)

    assert session.extras_category == "utilities"
    assert services.switched_to == "extras_utilities"


def test_extras_utilities_screen_applies_utility_and_sets_result(tmp_path, monkeypatch):
    work = _copy_red_save(tmp_path)
    monkeypatch.setenv("POKECABLE_BACKUP_DIR", str(tmp_path / "backups"))

    model = load_save(work)
    model.bytes[0x25F3:0x25F6] = b"\x00\x00\x00"
    model.bytes[0x2850:0x2852] = b"\x00\x00"
    model.bytes[0x3523] = gen1_checksum(model.bytes)
    model.write_to_disk()

    utilities = core.get_available_utilities(work).get("utilities", [])
    utility_ids = [utility["id"] for utility in utilities]
    assert "gen1_money_coins" in utility_ids

    session = UiSessionState(
        extras_save_path=work,
        extras_utilities=utilities,
        extras_utility_index=utility_ids.index("gen1_money_coins"),
    )
    services = _Services()
    screen = ExtrasUtilitiesScreen()

    screen.handle_action("select", None, session, SimpleNamespace(language="pt"), services)

    assert services.switched_to == "extras_result"
    assert session.extras_result.get("success"), session.extras_result.get("message")
    assert session.extras_result.get("money") == 999999
    assert session.extras_result.get("coins") == 9999

    reloaded = load_save(work)
    assert validate_gen1(reloaded.bytes)
    assert _bcd_be_to_int(bytes(reloaded.bytes[0x25F3:0x25F6])) == 999999
    assert _bcd_be_to_int(bytes(reloaded.bytes[0x2850:0x2852])) == 9999
