from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.engines.gen1 import damage as gen1_damage_mod
from app.engines.gen1 import engine as gen1_engine_mod
from app.engines.gen1 import utils as gen1_utils_mod
from app.engines.gen1.engine import BattleEngineGen1, BattleSideGen1
from app.engines.gen1.models import PokemonGen1


BACKEND_PATH = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from pokecable_room.parsers.gen1 import Gen1Parser

SAVE_ROOT = Path(__file__).resolve().parents[3] / "save"


def require_real_save(relative: str) -> Path:
    path = SAVE_ROOT / relative
    if not path.exists():
        pytest.skip(f"Save real ausente: {path}")
    return path


def patch_deterministic_battle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen1_engine_mod, "calculate_hit_gen1", lambda *args, **kwargs: True)
    monkeypatch.setattr(gen1_engine_mod, "determine_critical_gen1", lambda *args, **kwargs: False)
    monkeypatch.setattr(gen1_engine_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen1_engine_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen1_engine_mod.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(gen1_damage_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen1_utils_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen1_utils_mod.random, "randint", lambda a, b: b)


def load_real_team(relative: str) -> list[PokemonGen1]:
    parser = Gen1Parser()
    parser.load(require_real_save(relative))

    party = parser.list_party()
    assert len(party) == 6

    team: list[PokemonGen1] = []
    for index in range(6):
        canonical = parser.export_canonical(f"party:{index}").to_dict()
        pokemon = PokemonGen1.from_canonical(canonical)
        for move in pokemon.moves:
            move.pp = 0
            move.max_pp = 0
        team.append(pokemon)
    return team


def ensure_active_slot(engine: BattleEngineGen1, side_id: str) -> bool:
    side = engine.sides[side_id]
    active = side.active_pokemon
    if active is None:
        return False
    if active.current_hp > 0:
        return True

    alive = [index for index, pokemon in enumerate(side.team) if pokemon.current_hp > 0]
    if not alive:
        return False

    next_index = alive[0] if side.active_index not in alive else next(
        (index for index in alive if index != side.active_index),
        alive[0],
    )
    engine._switch_in(side_id, next_index)
    return True


def advance_battle_until_exhaustion(engine: BattleEngineGen1, turn_limit: int = 100) -> None:
    for turn in range(1, turn_limit + 1):
        if engine.finished:
            break

        if not ensure_active_slot(engine, "p1") or not ensure_active_slot(engine, "p2"):
            break

        p1_active = engine.sides["p1"].active_pokemon
        p2_active = engine.sides["p2"].active_pokemon
        if p1_active is None or p2_active is None:
            break

        engine.add_log(f"|turn|{turn}")
        engine._execute_action("p1", {"type": "move", "move_index": 0})
        if engine.finished:
            break
        engine._execute_action("p2", {"type": "move", "move_index": 0})
        engine._resolve_end_turn_effects()
        engine._check_win_condition()

        if all(pokemon.current_hp <= 0 for pokemon in engine.sides["p1"].team):
            break
        if all(pokemon.current_hp <= 0 for pokemon in engine.sides["p2"].team):
            break


def test_gen1_real_save_six_vs_six_battle_reaches_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1_team = load_real_team("gen 1/Pokémon - Yellow Version.sav")
    p2_team = load_real_team("gen 1/Pokémon - Red Version.sav")
    engine = BattleEngineGen1(
        "real-save-gen1-6v6",
        BattleSideGen1("p1", "Yellow", p1_team),
        BattleSideGen1("p2", "Red", p2_team),
    )

    engine.start_battle()
    advance_battle_until_exhaustion(engine)

    assert engine.finished is True
    assert len(engine.sides["p1"].team) == 6
    assert len(engine.sides["p2"].team) == 6
    assert any(log.startswith("|win|") for log in engine.logs)
    assert all(pokemon.current_hp <= 0 for pokemon in engine.sides["p1"].team) or all(
        pokemon.current_hp <= 0 for pokemon in engine.sides["p2"].team
    )
