from __future__ import annotations

import sys
from pathlib import Path

import pytest

from battle_validation_common import (
    ValidationReport,
    battle_pokemon_state,
    clone_team_with_active,
    clone_team_with_actives,
    normalize_key,
    require_real_save,
    tail_logs,
)
from app.data.move_combat_data import MOVE_COMBAT_DATA
from app.engines.gen3 import battle_damage as gen3_damage_mod
from app.engines.gen3 import battle_engine_core as gen3_engine_mod
from app.engines.gen3 import battle_move_effects as gen3_move_effects_mod
from app.engines.gen3 import battle_utils as gen3_utils_mod
from app.engines.gen3.battle_engine_core import (
    BattleSide,
    CustomBattleEngine,
    DOUBLE_ALLY_TARGET_MOVES,
    DOUBLE_ONLY_MOVES,
    DOUBLE_SPREAD_MOVES,
    _move_target_mode,
)
from app.engines.gen3.battle_pokemon import BattleMove, BattlePokemon


BACKEND_PATH = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from pokecable_room.parsers.gen3 import Gen3Parser


def patch_deterministic_battle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen3_engine_mod, "calculate_hit", lambda *args, **kwargs: True)
    monkeypatch.setattr(gen3_engine_mod, "determine_critical", lambda *args, **kwargs: False)
    monkeypatch.setattr(gen3_engine_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen3_engine_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen3_engine_mod.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(gen3_damage_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen3_move_effects_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen3_move_effects_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen3_utils_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen3_utils_mod.random, "randint", lambda a, b: b)


def load_real_team(relative: str) -> tuple[str, list[BattlePokemon]]:
    parser = Gen3Parser()
    parser.load(require_real_save(relative))

    party = parser.list_party()
    assert len(party) == 6

    team: list[BattlePokemon] = []
    for index in range(6):
        canonical = parser.export_canonical(f"party:{index}").to_dict()
        pokemon = BattlePokemon.from_canonical(canonical)
        for move in pokemon.moves:
            move.pp = max(1, int(move.pp or 0))
            move.max_pp = max(1, int(move.max_pp or move.pp))
        team.append(pokemon)

    return parser.get_player_name(), team


def move_key(move: BattleMove) -> str:
    return normalize_key(move.name)


def first_move_index(pokemon: BattlePokemon, *, damage_class: str | None = None) -> int:
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


def build_move_by_name(move_name: str) -> BattleMove:
    target_key = normalize_key(move_name)
    for move_id, data in MOVE_COMBAT_DATA.items():
        if normalize_key(str(data.get("name") or "")) == target_key:
            return BattleMove(
                move_id=int(move_id),
                name=str(data["name"]),
                type=str(data["type"]),
                power=int(data["power"]) if data.get("power") is not None else 0,
                accuracy=int(data["accuracy"]) if data.get("accuracy") is not None else 100,
                pp=max(1, int(data.get("pp") or 1)),
                max_pp=max(1, int(data.get("pp") or 1)),
                priority=int(data.get("priority") or 0),
                damage_class=str(data["damage_class"]),
                effect=str(data.get("effect") or ""),
                effect_chance=data.get("effect_chance"),
            )
    raise AssertionError(f"Golpe {move_name!r} nao encontrado.")


def battle_note(attacker: BattlePokemon, defender: BattlePokemon, engine: CustomBattleEngine) -> str:
    return (
        f"attacker={battle_pokemon_state(attacker)} "
        f"defender={battle_pokemon_state(defender)} "
        f"logs={'; '.join(tail_logs(engine.logs, 4))}"
    )


def apply_singles_setup(
    engine: CustomBattleEngine,
    attacker: BattlePokemon,
    defender: BattlePokemon,
    move_name_key: str,
) -> None:
    if move_name_key in {"sleeptalk", "snore"}:
        attacker.status_condition = "slp"
        attacker.status_turns = 3
    if move_name_key in {"dreameater", "nightmare"}:
        defender.status_condition = "slp"
        defender.status_turns = 3
    if move_name_key in {"healbell", "aromatherapy"}:
        attacker.status_condition = "psn"
        if len(engine.sides["p1"].team) > 1:
            engine.sides["p1"].team[1].status_condition = "brn"
            engine.sides["p1"].team[1].ability = "soundproof"
        if len(engine.sides["p1"].team) > 2:
            engine.sides["p1"].team[2].status_condition = "par"
    if move_name_key == "rest":
        attacker.current_hp = max(1, attacker.max_hp // 2)
    if move_name_key in {"mimic", "mirrormove", "disable", "encore", "spite"}:
        defender.moves[0].pp = max(1, int(defender.moves[0].pp or 0))


def use_singles_setup_turn(engine: CustomBattleEngine, move_name_key: str) -> bool:
    if move_name_key in {"mimic", "mirrormove", "disable", "encore", "spite"}:
        engine.submit_action("p1", {"type": "pass"})
        engine.submit_action("p2", {"type": "move", "move_index": 0})
        return True
    if move_name_key == "counter":
        defender_idx = first_move_index(engine.sides["p2"].active_pokemon, damage_class="physical")
        engine.submit_action("p1", {"type": "pass"})
        engine.submit_action("p2", {"type": "move", "move_index": defender_idx})
        return True
    if move_name_key == "mirrorcoat":
        defender_idx = first_move_index(engine.sides["p2"].active_pokemon, damage_class="special")
        engine.submit_action("p1", {"type": "pass"})
        engine.submit_action("p2", {"type": "move", "move_index": defender_idx})
        return True
    if move_name_key == "bide":
        defender_idx = first_move_index(engine.sides["p2"].active_pokemon)
        engine.submit_action("p1", {"type": "pass"})
        engine.submit_action("p2", {"type": "move", "move_index": defender_idx})
        return True
    return False


def run_single_case(
    attacker_label: str,
    attacker_source: list[BattlePokemon],
    attacker_index: int,
    defender_label: str,
    defender_source: list[BattlePokemon],
    defender_index: int,
    move_index: int,
) -> tuple[bool, str, list[str]]:
    attacker_team = clone_team_with_active(attacker_source, attacker_index)
    defender_team = clone_team_with_active(defender_source, defender_index)
    attacker = attacker_team[0]
    defender = defender_team[0]
    move_obj = attacker.moves[move_index]
    move_name_key = move_key(move_obj)

    if move_name_key in DOUBLE_ONLY_MOVES or move_name_key in DOUBLE_ALLY_TARGET_MOVES:
        return True, f"skipped singles-only for doubles move {move_obj.name}", []

    engine = CustomBattleEngine(
        f"gen3-single-{attacker_label}-{attacker_index}-{move_index}-{defender_label}-{defender_index}",
        BattleSide("p1", attacker_label.title(), attacker_team),
        BattleSide("p2", defender_label.title(), defender_team),
    )

    engine.start_battle()
    apply_singles_setup(engine, attacker, defender, move_name_key)

    if use_singles_setup_turn(engine, move_name_key) and engine.finished:
        return True, battle_note(attacker, defender, engine), []

    repeat_turns = 1
    if move_name_key in {"solarbeam", "razorwind", "skullbash", "skyattack", "fly", "dig", "dive", "bounce"}:
        repeat_turns = 2
    elif move_name_key in {"rollout", "furycutter"}:
        repeat_turns = 2
    elif move_name_key == "bide":
        repeat_turns = 3

    for _ in range(repeat_turns):
        if engine.finished:
            break
        engine.submit_action("p1", {"type": "move", "move_index": move_index})
        engine.submit_action("p2", {"type": "pass"})

    return True, battle_note(attacker, defender, engine), []


def run_doubles_case(
    attacker_label: str,
    attacker_source: list[BattlePokemon],
    attacker_index: int,
    defender_label: str,
    defender_source: list[BattlePokemon],
    defender_index: int,
    move_name: str,
) -> tuple[bool, str, list[str]]:
    attacker_team = clone_team_with_actives(attacker_source, [attacker_index, (attacker_index + 1) % 6])
    defender_team = clone_team_with_actives(defender_source, [defender_index, (defender_index + 1) % 6])
    attacker = attacker_team[0]
    partner = attacker_team[1]
    foe = defender_team[0]
    foe_partner = defender_team[1]
    move_obj = build_move_by_name(move_name)
    attacker.moves[0] = move_obj
    move_name_key = move_key(move_obj)

    engine = CustomBattleEngine(
        f"gen3-double-{attacker_label}-{attacker_index}-{move_name_key}-{defender_label}-{defender_index}",
        BattleSide("p1", attacker_label.title(), attacker_team, active_indices=[0, 1]),
        BattleSide("p2", defender_label.title(), defender_team, active_indices=[0, 1]),
        battle_format="doubles",
    )
    engine.start_battle()

    if len(engine.sides["p2"].team) > 1 and move_obj.type == "electric":
        engine.sides["p2"].team[1].ability = "lightning-rod"
    if move_name_key == "snatch":
        engine.sides["p2"].team[0].moves[0] = build_move_by_name("recover")
    elif move_name_key == "followme":
        engine.sides["p2"].team[0].moves[0] = build_move_by_name("thunderbolt")

    if move_name_key == "followme":
        p2_move_idx = first_move_index(foe, damage_class="physical")
        engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 0})
        engine.submit_action("p1", {"type": "pass", "slot": 1})
        engine.submit_action("p2", {"type": "move", "move_index": p2_move_idx, "slot": 0})
        engine.submit_action("p2", {"type": "pass", "slot": 1})
    elif move_name_key == "snatch":
        p2_move_idx = first_move_index(foe, damage_class=None)
        engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 0})
        engine.submit_action("p1", {"type": "pass", "slot": 1})
        engine.submit_action("p2", {"type": "move", "move_index": p2_move_idx, "slot": 0})
        engine.submit_action("p2", {"type": "pass", "slot": 1})
    else:
        engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 0})
        engine.submit_action("p1", {"type": "pass", "slot": 1})
        engine.submit_action("p2", {"type": "pass", "slot": 0})
        engine.submit_action("p2", {"type": "pass", "slot": 1})

    return True, f"attacker={battle_pokemon_state(attacker)} partner={battle_pokemon_state(partner)} foe={battle_pokemon_state(foe)} foe_partner={battle_pokemon_state(foe_partner)} logs={'; '.join(tail_logs(engine.logs, 4))}", []


def test_gen3_real_save_validation_matrix_singles(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    emerald_name, emerald_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    firered_name, firered_team = load_real_team("gen 3/Pokémon - FireRed Version.sav")

    report = ValidationReport("Gen 3 Singles Matrix", emerald_name, firered_name)
    report.add_header()

    cases = 0
    failures: list[str] = []

    for attacker_label, attacker_source, defender_label, defender_source in (
        ("emerald", emerald_team, "firered", firered_team),
        ("firered", firered_team, "emerald", emerald_team),
    ):
        for attacker_index, attacker_template in enumerate(attacker_source):
            for move_index, move in enumerate(attacker_template.moves):
                for defender_index, defender_template in enumerate(defender_source):
                    cases += 1
                    ok = True
                    detail = ""
                    logs: list[str] = []
                    try:
                        ok, detail, logs = run_single_case(
                            attacker_label,
                            attacker_source,
                            attacker_index,
                            defender_label,
                            defender_source,
                            defender_index,
                            move_index,
                        )
                    except Exception as exc:  # pragma: no cover - matrix report path
                        ok = False
                        detail = f"{type(exc).__name__}: {exc}"
                        failures.append(
                            f"gen3 singles {attacker_label}[{attacker_index}] vs {defender_label}[{defender_index}] "
                            f"move={move.name}: {detail}"
                        )

                    report.add_case(
                        f"{attacker_label}[{attacker_index}] {attacker_template.nickname} -> "
                        f"{defender_label}[{defender_index}] {defender_template.nickname} | move={move.name}",
                        ok,
                        detail,
                        logs=logs if not ok else None,
                    )

    report.add_summary()
    report.write("gen3-matrix.txt")

    assert not failures, "\n".join(failures[:20])
    assert cases == report.pass_count + report.fail_count


def test_gen3_real_save_validation_matrix_doubles(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    emerald_name, emerald_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    firered_name, firered_team = load_real_team("gen 3/Pokémon - FireRed Version.sav")

    report = ValidationReport("Gen 3 Doubles Matrix", emerald_name, firered_name)
    report.add_header()

    cases = 0
    failures: list[str] = []

    for attacker_label, attacker_source, defender_label, defender_source in (
        ("emerald", emerald_team, "firered", firered_team),
        ("firered", firered_team, "emerald", emerald_team),
    ):
        for attacker_index, attacker_template in enumerate(attacker_source):
            for move_name in (
                "helping-hand",
                "follow-me",
                "snatch",
                "surf",
                "earthquake",
                "rock-slide",
                "magnitude",
                "thunderbolt",
            ):
                defender_index = 0
                cases += 1
                ok = True
                detail = ""
                logs: list[str] = []
                try:
                    ok, detail, logs = run_doubles_case(
                        attacker_label,
                        attacker_source,
                        attacker_index,
                        defender_label,
                        defender_source,
                        defender_index,
                        move_name,
                    )
                except Exception as exc:  # pragma: no cover - matrix report path
                    ok = False
                    detail = f"{type(exc).__name__}: {exc}"
                    failures.append(
                        f"gen3 doubles {attacker_label}[{attacker_index}] vs {defender_label}[{defender_index}] "
                        f"move={move_name}: {detail}"
                    )

                report.add_case(
                    f"{attacker_label}[{attacker_index}] {attacker_template.nickname} | move={move_name} | doubles",
                    ok,
                    detail,
                    logs=logs if not ok else None,
                )

    report.add_summary()
    report.write("gen3-doubles-matrix.txt")

    assert not failures, "\n".join(failures[:20])
    assert cases == report.pass_count + report.fail_count
