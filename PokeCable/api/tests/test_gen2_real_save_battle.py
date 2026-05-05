from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.engines.gen2.damage import calculate_damage_gen2
from app.engines.gen2.engine import BattleEngineGen2, BattleSideGen2
from app.engines.gen2.models import PokemonGen2


BACKEND_PATH = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from pokecable_room.parsers.gen2 import Gen2Parser

SAVE_ROOT = Path(__file__).resolve().parents[3] / "save"


def require_real_save(relative: str) -> Path:
    path = SAVE_ROOT / relative
    if not path.exists():
        pytest.skip(f"Save real ausente: {path}")
    return path


def make_real_team(relative: str) -> tuple[str, list[PokemonGen2]]:
    parser = Gen2Parser()
    parser.load(require_real_save(relative))

    party = parser.list_party()
    assert len(party) == 6

    team: list[PokemonGen2] = []
    for index in range(6):
        canonical = parser.export_canonical(f"party:{index}").to_dict()
        pokemon = PokemonGen2.from_canonical(canonical)
        team.append(pokemon)
    return parser.get_player_name(), team


def patch_deterministic_battle(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.engines.gen2.engine as gen2_engine_mod
    import app.engines.gen2.damage as gen2_damage_mod

    monkeypatch.setattr(gen2_engine_mod, "calculate_hit_gen2", lambda *args, **kwargs: True)
    monkeypatch.setattr(gen2_engine_mod, "determine_critical_gen2", lambda *args, **kwargs: False)
    monkeypatch.setattr(gen2_engine_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen2_engine_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen2_damage_mod.random, "randint", lambda a, b: b)


def choose_best_move(engine: BattleEngineGen2, side_id: str, attacker: PokemonGen2, defender: PokemonGen2) -> int:
    request = engine.generate_request(engine.sides[side_id].player_id)
    enabled_ids = {
        int(move["id"])
        for move in request.get("active", [{}])[0].get("moves", [])
        if not move.get("disabled")
    }

    best_idx = 0
    best_damage = -1
    for idx, move in enumerate(attacker.moves):
        if enabled_ids and move.move_id not in enabled_ids:
            continue
        if move.pp <= 0 and move.move_id not in enabled_ids:
            continue
        if move.damage_class == "status" or move.power <= 0:
            continue
        damage, _ = calculate_damage_gen2(attacker, defender, move, is_critical=False, random_factor=255)
        if damage > best_damage:
            best_damage = damage
            best_idx = idx
    return best_idx


def ensure_switch_if_needed(engine: BattleEngineGen2, side_id: str) -> None:
    side = engine.sides[side_id]
    active = side.active_pokemon
    if active is not None and active.current_hp > 0 and engine.force_switch_player != side.player_id:
        return

    alive_indices = [index for index, pokemon in enumerate(side.team) if pokemon.current_hp > 0]
    if not alive_indices:
        return

    next_index = alive_indices[0]
    if engine.force_switch_player == side.player_id:
        engine.submit_action(side.player_id, {"type": "switch", "index": next_index})
    else:
        engine._switch_in(side_id, next_index)


def advance_battle_until_exhaustion(engine: BattleEngineGen2, turn_limit: int = 250) -> None:
    for _ in range(turn_limit):
        if engine.finished:
            return

        ensure_switch_if_needed(engine, "p1")
        ensure_switch_if_needed(engine, "p2")

        if engine.finished:
            return

        p1_active = engine.sides["p1"].active_pokemon
        p2_active = engine.sides["p2"].active_pokemon
        if p1_active is None or p2_active is None:
            return

        p1_move = choose_best_move(engine, "p1", p1_active, p2_active)
        p2_move = choose_best_move(engine, "p2", p2_active, p1_active)

        engine.submit_action(engine.sides["p1"].player_id, {"type": "move", "move_index": p1_move})
        engine.submit_action(engine.sides["p2"].player_id, {"type": "move", "move_index": p2_move})

    assert engine.finished, "A batalha Gen 2 nao terminou dentro do limite esperado."


def test_gen2_real_save_six_vs_six_battle_reaches_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1_name, p1_team = make_real_team("gen 2/Pokémon - Gold Version.sav")
    p2_name, p2_team = make_real_team("gen 2/Pokémon - Silver Version.sav")

    engine = BattleEngineGen2(
        "real-save-gen2-6v6",
        BattleSideGen2("p1", p1_name, p1_team),
        BattleSideGen2("p2", p2_name, p2_team),
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
