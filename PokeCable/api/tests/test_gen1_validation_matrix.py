from __future__ import annotations

import copy
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
from app.engines.gen1 import damage as gen1_damage_mod
from app.engines.gen1 import engine as gen1_engine_mod
from app.engines.gen1 import utils as gen1_utils_mod
from app.engines.gen1.engine import BattleEngineGen1, BattleSideGen1
from app.engines.gen1.models import BattleMoveGen1, PokemonGen1


BACKEND_PATH = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from pokecable_room.parsers.gen1 import Gen1Parser


def patch_deterministic_battle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen1_engine_mod, "calculate_hit_gen1", lambda *args, **kwargs: True)
    monkeypatch.setattr(gen1_engine_mod, "determine_critical_gen1", lambda *args, **kwargs: False)
    monkeypatch.setattr(gen1_engine_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen1_engine_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen1_engine_mod.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(gen1_damage_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen1_utils_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen1_utils_mod.random, "randint", lambda a, b: b)


def load_real_team(relative: str) -> tuple[str, list[PokemonGen1]]:
    parser = Gen1Parser()
    parser.load(require_real_save(relative))

    party = parser.list_party()
    assert len(party) == 6

    team: list[PokemonGen1] = []
    for index in range(6):
        canonical = parser.export_canonical(f"party:{index}").to_dict()
        pokemon = PokemonGen1.from_canonical(canonical)
        for move in pokemon.moves:
            move.pp = max(1, int(move.pp or 0))
            move.max_pp = max(1, int(move.max_pp or move.pp))
        team.append(pokemon)

    return parser.get_player_name(), team


def move_key(move: BattleMoveGen1) -> str:
    return normalize_key(move.name)


def first_damaging_move_index(pokemon: PokemonGen1, *, damage_class: str | None = None) -> int:
    candidates: list[tuple[int, int]] = []
    for index, move in enumerate(pokemon.moves):
        if int(move.pp or 0) <= 0:
            continue
        if (int(move.power or 0)) <= 0:
            continue
        if damage_class is not None and move.damage_class != damage_class:
            continue
        candidates.append((int(move.power or 0), index))
    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][1]
    return 0


def use_pre_turn_if_needed(
    engine: BattleEngineGen1,
    attacker_key: str,
    defender_key: str,
    attacker: PokemonGen1,
    defender: PokemonGen1,
    move_name_key: str,
) -> bool:
    if move_name_key in {"mimic", "mirrormove", "disable"}:
        setup_move_index = first_damaging_move_index(defender)
        engine.submit_action(attacker_key, {"type": "pass"})
        engine.submit_action(defender_key, {"type": "move", "move_index": setup_move_index})
        return True

    if move_name_key == "counter":
        setup_move_index = first_damaging_move_index(defender, damage_class="physical")
        engine.submit_action(attacker_key, {"type": "pass"})
        engine.submit_action(defender_key, {"type": "move", "move_index": setup_move_index})
        return True

    return False


def build_case_note(attacker: PokemonGen1, defender: PokemonGen1, engine: BattleEngineGen1) -> str:
    return (
        f"attacker={battle_pokemon_state(attacker)} "
        f"defender={battle_pokemon_state(defender)} "
        f"logs={'; '.join(tail_logs(engine.logs, 4))}"
    )


def test_gen1_real_save_validation_matrix(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    yellow_name, yellow_team = load_real_team("gen 1/Pokémon - Yellow Version.sav")
    red_name, red_team = load_real_team("gen 1/Pokémon - Red Version.sav")

    report = ValidationReport("Gen 1 Battle Matrix", yellow_name, red_name)
    report.add_header()

    cases = 0
    failures: list[str] = []

    for attacker_label, attacker_source, defender_label, defender_source in (
        ("yellow", yellow_team, "red", red_team),
        ("red", red_team, "yellow", yellow_team),
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

                    if move_name_key in {"rest", "recover", "softboiled"}:
                        attacker.current_hp = max(1, attacker.max_hp // 2)
                    if move_name_key == "dreameater":
                        defender.status_condition = "slp"
                        defender.status_turns = 3
                    if move_name_key in {"mimic", "mirrormove", "disable"}:
                        defender.moves[0].pp = max(1, int(defender.moves[0].pp or 0))
                    if move_name_key == "counter":
                        defender.moves[0].pp = max(1, int(defender.moves[0].pp or 0))

                    engine = BattleEngineGen1(
                        f"gen1-matrix-{attacker_label}-{attacker_index}-{move_index}-{defender_label}-{defender_index}",
                        BattleSideGen1("p1", attacker_label.title(), attacker_team),
                        BattleSideGen1("p2", defender_label.title(), defender_team),
                    )

                    ok = True
                    detail = ""
                    try:
                        engine.start_battle()
                        use_pre_turn_if_needed(
                            engine,
                            "p1",
                            "p2",
                            attacker,
                            defender,
                            move_name_key,
                        )

                        if not engine.finished:
                            repeat_turns = 1
                            if move_name_key in {"razorwind", "solarbeam", "skyattack", "skullbash", "fly", "dig"}:
                                repeat_turns = 2
                            elif move_name_key == "bide":
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
                            f"gen1 {attacker_label}[{attacker_index}] vs {defender_label}[{defender_index}] "
                            f"move={move_obj.name}: {detail}"
                        )
                    else:
                        detail = build_case_note(attacker, defender, engine)

                    report.add_case(
                        f"{attacker_label}[{attacker_index}] {attacker_template.nickname} -> "
                        f"{defender_label}[{defender_index}] {defender_template.nickname} | move={move_obj.name}",
                        ok,
                        detail,
                        logs=tail_logs(engine.logs, 3) if not ok else None,
                    )

    report.add_summary()
    report.write("gen1-matrix.txt")

    assert not failures, "\n".join(failures[:20])
    assert cases == report.pass_count + report.fail_count
