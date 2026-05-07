from __future__ import annotations

import sys
from pathlib import Path

import pytest

from battle_validation_common import (
    ValidationReport,
    battle_pokemon_state,
    clone_team_with_active,
    normalize_key,
    require_real_save,
    tail_logs,
)
from app.engines.gen2 import damage as gen2_damage_mod
from app.engines.gen2 import engine as gen2_engine_mod
from app.engines.gen2.engine import (
    BattleEngineGen2,
    BattleSideGen2,
    GEN2_BIDE_MOVES,
    GEN2_CHARGE_MOVES,
    GEN2_COUNTER_MOVES,
    GEN2_DISABLE_MOVES,
    GEN2_ENCORE_MOVES,
    GEN2_FORESIGHT_MOVES,
    GEN2_LEECH_SEED_MOVES,
    GEN2_MIMIC_MOVES,
    GEN2_MIRROR_COAT_MOVES,
    GEN2_MIRROR_MOVE_MOVES,
    GEN2_NIGHTMARE_MOVES,
    GEN2_PAIN_SPLIT_MOVES,
    GEN2_PRESENT_MOVES,
    GEN2_POWERSHIFT_MOVES,
    GEN2_SPITE_MOVES,
    GEN2_TRANSFORM_MOVES,
    GEN2_WEATHER_MOVES,
)
from app.engines.gen2.models import BattleMoveGen2, PokemonGen2


BACKEND_PATH = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from pokecable_room.parsers.gen2 import Gen2Parser


def patch_deterministic_battle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen2_engine_mod, "calculate_hit_gen2", lambda *args, **kwargs: True)
    monkeypatch.setattr(gen2_engine_mod, "determine_critical_gen2", lambda *args, **kwargs: False)
    monkeypatch.setattr(gen2_engine_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen2_engine_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen2_engine_mod.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(gen2_damage_mod.random, "randint", lambda a, b: b)


def load_real_team(relative: str) -> tuple[str, list[PokemonGen2]]:
    parser = Gen2Parser()
    parser.load(require_real_save(relative))

    party = parser.list_party()
    assert len(party) == 6

    team: list[PokemonGen2] = []
    for index in range(6):
        canonical = parser.export_canonical(f"party:{index}").to_dict()
        pokemon = PokemonGen2.from_canonical(canonical)
        for move in pokemon.moves:
            move.pp = max(1, int(move.pp or 0))
            move.max_pp = max(1, int(move.max_pp or move.pp))
        team.append(pokemon)

    return parser.get_player_name(), team


def move_key(move: BattleMoveGen2) -> str:
    return normalize_key(move.name)


def first_move_index(pokemon: PokemonGen2, *, damage_class: str | None = None) -> int:
    candidates: list[tuple[int, int]] = []
    for index, move in enumerate(pokemon.moves):
        if int(move.pp or 0) <= 0:
            continue
        if damage_class is not None and move.damage_class != damage_class:
            continue
        if damage_class is not None and int(move.power or 0) <= 0:
            continue
        candidates.append((int(move.power or 0), index))
    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][1]
    return 0


def battle_note(attacker: PokemonGen2, defender: PokemonGen2, engine: BattleEngineGen2) -> str:
    return (
        f"attacker={battle_pokemon_state(attacker)} "
        f"defender={battle_pokemon_state(defender)} "
        f"logs={'; '.join(tail_logs(engine.logs, 4))}"
    )


def apply_setup(engine: BattleEngineGen2, attacker: PokemonGen2, defender: PokemonGen2, move_name_key: str) -> None:
    if move_name_key in {"sleeptalk", "snore"}:
        attacker.status_condition = "slp"
        attacker.status_turns = 3
    if move_name_key in {"dreameater", "nightmare"}:
        defender.status_condition = "slp"
        defender.status_turns = 3
    if move_name_key in {"healbell"}:
        attacker.status_condition = "psn"
        attacker.current_hp = attacker.max_hp
        for ally in engine.sides["p1"].team[1:]:
            ally.status_condition = "brn"
    if move_name_key == "rest":
        attacker.current_hp = max(1, attacker.max_hp // 2)
    if move_name_key in {"mimic", "mirrormove", "disable", "encore", "spite"}:
        defender.moves[0].pp = max(1, int(defender.moves[0].pp or 0))


def use_setup_turn(engine: BattleEngineGen2, move_name_key: str) -> bool:
    if move_name_key in {"mimic", "mirrormove", "disable", "encore", "spite"}:
        engine.submit_action("p1", {"type": "pass"})
        engine.submit_action("p2", {"type": "move", "move_index": 0})
        return True
    if move_name_key in GEN2_COUNTER_MOVES:
        defender_idx = first_move_index(engine.sides["p2"].active_pokemon, damage_class="physical")
        engine.submit_action("p1", {"type": "pass"})
        engine.submit_action("p2", {"type": "move", "move_index": defender_idx})
        return True
    if move_name_key in GEN2_MIRROR_COAT_MOVES:
        defender_idx = first_move_index(engine.sides["p2"].active_pokemon, damage_class="special")
        engine.submit_action("p1", {"type": "pass"})
        engine.submit_action("p2", {"type": "move", "move_index": defender_idx})
        return True
    return False


def test_gen2_real_save_validation_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    gold_name, gold_team = load_real_team("gen 2/Pokémon - Gold Version.sav")
    silver_name, silver_team = load_real_team("gen 2/Pokémon - Silver Version.sav")

    report = ValidationReport("Gen 2 Battle Matrix", gold_name, silver_name)
    report.add_header()

    cases = 0
    failures: list[str] = []

    for attacker_label, attacker_source, defender_label, defender_source in (
        ("gold", gold_team, "silver", silver_team),
        ("silver", silver_team, "gold", gold_team),
    ):
        for attacker_index, attacker_template in enumerate(attacker_source):
            for move_index, move in enumerate(attacker_template.moves):
                for defender_index, defender_template in enumerate(defender_source):
                    cases += 1
                    attacker_team = clone_team_with_active(attacker_source, attacker_index)
                    defender_team = clone_team_with_active(defender_source, defender_index)
                    attacker = attacker_team[0]
                    defender = defender_team[0]
                    move_obj = attacker.moves[move_index]
                    move_name_key = move_key(move_obj)

                    engine = BattleEngineGen2(
                        f"gen2-matrix-{attacker_label}-{attacker_index}-{move_index}-{defender_label}-{defender_index}",
                        BattleSideGen2("p1", attacker_label.title(), attacker_team),
                        BattleSideGen2("p2", defender_label.title(), defender_team),
                    )

                    ok = True
                    detail = ""
                    try:
                        engine.start_battle()
                        apply_setup(engine, attacker, defender, move_name_key)
                        use_setup_turn(engine, move_name_key)

                        if not engine.finished:
                            repeat_turns = 1
                            if move_name_key in GEN2_CHARGE_MOVES:
                                repeat_turns = 2
                            elif move_name_key in GEN2_BIDE_MOVES:
                                repeat_turns = 3

                            for _ in range(repeat_turns):
                                if engine.finished:
                                    break
                                engine.submit_action("p1", {"type": "move", "move_index": move_index})
                                engine.submit_action("p2", {"type": "pass"})
                    except Exception as exc:  # pragma: no cover - matrix report path
                        ok = False
                        detail = f"{type(exc).__name__}: {exc}"
                        failures.append(
                            f"gen2 {attacker_label}[{attacker_index}] vs {defender_label}[{defender_index}] "
                            f"move={move_obj.name}: {detail}"
                        )
                    else:
                        detail = battle_note(attacker, defender, engine)

                    report.add_case(
                        f"{attacker_label}[{attacker_index}] {attacker_template.nickname} -> "
                        f"{defender_label}[{defender_index}] {defender_template.nickname} | move={move_obj.name}",
                        ok,
                        detail,
                        logs=tail_logs(engine.logs, 3) if not ok else None,
                    )

    report.add_summary()
    report.write("gen2-matrix.txt")

    assert not failures, "\n".join(failures[:20])
    assert cases == report.pass_count + report.fail_count
