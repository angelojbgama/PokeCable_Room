from __future__ import annotations

from copy import deepcopy
import sys
from pathlib import Path

import pytest

from battle_validation_common import ValidationReport, battle_pokemon_state, tail_logs
from app.data.move_combat_data import MOVE_COMBAT_DATA
from app.engines.gen3 import battle_damage as gen3_damage_mod
from app.engines.gen3 import battle_engine_core as gen3_engine_mod
from app.engines.gen3 import battle_move_effects as gen3_move_effects_mod
from app.engines.gen3 import battle_utils as gen3_utils_mod
from app.engines.gen3.battle_damage import calculate_damage
from app.engines.gen3.battle_engine_core import BattleSide, CustomBattleEngine
from app.engines.gen3.battle_pokemon import BattleMove, BattlePokemon


BACKEND_PATH = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from pokecable_room.parsers.gen3 import Gen3Parser

SAVE_ROOT = Path(__file__).resolve().parents[3] / "save"


def require_real_save(relative: str) -> Path:
    path = SAVE_ROOT / relative
    if not path.exists():
        pytest.skip(f"Save real ausente: {path}")
    return path


def deterministic_randint(a: int, b: int) -> int:
    if (a, b) in {(1, 4), (2, 5), (2, 3)}:
        return a
    return b


def patch_deterministic_battle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen3_engine_mod, "calculate_hit", lambda *args, **kwargs: True)
    monkeypatch.setattr(gen3_engine_mod, "determine_critical", lambda *args, **kwargs: False)
    monkeypatch.setattr(gen3_engine_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen3_engine_mod.random, "randint", deterministic_randint)
    monkeypatch.setattr(gen3_engine_mod.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(gen3_damage_mod.random, "randint", deterministic_randint)
    monkeypatch.setattr(gen3_move_effects_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen3_move_effects_mod.random, "randint", deterministic_randint)
    monkeypatch.setattr(gen3_utils_mod.random, "random", lambda: 0.99)
    monkeypatch.setattr(gen3_utils_mod.random, "randint", deterministic_randint)


def load_real_team(relative: str) -> tuple[str, list[BattlePokemon]]:
    parser = Gen3Parser()
    parser.load(require_real_save(relative))

    party = parser.list_party()
    assert len(party) == 6

    team: list[BattlePokemon] = []
    for index in range(6):
        canonical = parser.export_canonical(f"party:{index}").to_dict()
        team.append(BattlePokemon.from_canonical(canonical))
    return parser.get_player_name(), team


def load_real_pokemon(relative: str, party_index: int) -> tuple[str, BattlePokemon]:
    parser = Gen3Parser()
    parser.load(require_real_save(relative))
    canonical = parser.export_canonical(f"party:{party_index}").to_dict()
    return parser.get_player_name(), BattlePokemon.from_canonical(canonical)


def move_index_by_name(pokemon: BattlePokemon, move_name: str) -> int:
    normalized = move_name.lower().replace("-", "").replace(" ", "")
    for index, move in enumerate(pokemon.moves):
        if move.name.lower().replace("-", "").replace(" ", "") == normalized:
            return index
    raise AssertionError(f"Golpe {move_name!r} nao encontrado em {pokemon.nickname}.")


def move_id_by_name(move_name: str) -> int:
    normalized = move_name.lower().replace("-", "").replace(" ", "")
    for move_id, data in MOVE_COMBAT_DATA.items():
        if str(data.get("name") or "").lower().replace("-", "").replace(" ", "") == normalized:
            return int(move_id)
    raise AssertionError(f"Golpe {move_name!r} nao encontrado em MOVE_COMBAT_DATA.")


def damage_from_single_attack(
    attacker_relative: str,
    attacker_index: int,
    defender_relative: str,
    defender_index: int,
    move_name: str,
    *,
    attacker_hp: int | None = None,
) -> int:
    engine, attacker, defender = build_single_engine(attacker_relative, attacker_index, defender_relative, defender_index)
    if attacker_hp is not None:
        attacker.current_hp = attacker_hp

    defender_hp = defender.current_hp
    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(attacker, move_name)})
    engine.submit_action("p2", {"type": "pass"})
    return defender_hp - defender.current_hp


def make_move(move_id: int) -> BattleMove:
    data = MOVE_COMBAT_DATA[move_id]
    return BattleMove(
        move_id=move_id,
        name=str(data["name"]),
        type=str(data["type"]),
        power=int(data["power"]) if data.get("power") is not None else 0,
        accuracy=int(data["accuracy"]) if data.get("accuracy") is not None else 100,
        pp=int(data["pp"]),
        max_pp=int(data["pp"]),
        priority=int(data.get("priority") or 0),
        damage_class=str(data["damage_class"]),
        effect=str(data.get("effect") or ""),
        effect_chance=data.get("effect_chance"),
    )


def replace_moves(pokemon: BattlePokemon, move_names: list[str]) -> None:
    moves = [make_move(move_id_by_name(move_name)) for move_name in move_names]
    pokemon.moves = moves
    pokemon.original_moves = deepcopy(moves)


def build_single_engine(
    p1_relative: str,
    p1_index: int,
    p2_relative: str,
    p2_index: int,
) -> tuple[CustomBattleEngine, BattlePokemon, BattlePokemon]:
    p1_name, p1 = load_real_pokemon(p1_relative, p1_index)
    p2_name, p2 = load_real_pokemon(p2_relative, p2_index)

    engine = CustomBattleEngine(
        f"real-save-gen3-{p1_index}-{p2_index}",
        BattleSide("p1", p1_name, [p1]),
        BattleSide("p2", p2_name, [p2]),
    )
    engine.start_battle()
    return engine, p1, p2


def build_doubles_engine(
    p1_relative: str,
    p1_indices: list[int],
    p2_relative: str,
    p2_indices: list[int],
) -> CustomBattleEngine:
    p1_name, p1_team = load_real_team(p1_relative)
    p2_name, p2_team = load_real_team(p2_relative)

    engine = CustomBattleEngine(
        f"real-save-gen3-doubles-{p1_indices}-{p2_indices}",
        BattleSide("p1", p1_name, [p1_team[index] for index in p1_indices]),
        BattleSide("p2", p2_name, [p2_team[index] for index in p2_indices]),
        battle_format="doubles",
    )
    engine.start_battle()
    return engine


def run_doubles_turn(
    engine: CustomBattleEngine,
    p1_action: dict[str, int | str],
    p1_slot1_action: dict[str, int | str],
    p2_slot0_action: dict[str, int | str],
    p2_slot1_action: dict[str, int | str],
) -> None:
    assert engine.submit_action("p1", p1_action) is True
    assert engine.submit_action("p1", p1_slot1_action) is True
    assert engine.submit_action("p2", p2_slot0_action) is True
    assert engine.submit_action("p2", p2_slot1_action) is True


def run_turn(
    engine: CustomBattleEngine,
    p1_action: dict[str, int | str],
    p2_action: dict[str, int | str],
) -> None:
    assert engine.submit_action("p1", p1_action) is True
    assert engine.submit_action("p2", p2_action) is True


def first_alive_bench_index(side: BattleSide) -> int | None:
    active_indices = set(side.active_indices)
    for index, pokemon in enumerate(side.team):
        if index in active_indices:
            continue
        if pokemon.current_hp > 0:
            return index
    return None


def ensure_switch_if_needed(engine: CustomBattleEngine, side_id: str) -> bool:
    side = engine.sides[side_id]
    request = engine.generate_request(side.player_id)

    if not request.get("forceSwitch"):
        active = side.active_pokemon
        if active is not None and active.current_hp > 0:
            return True

    next_index = first_alive_bench_index(side)
    if next_index is None:
        return False

    engine.submit_action(side.player_id, {"type": "switch", "index": next_index})
    return True


def choose_best_action(engine: CustomBattleEngine, side_id: str, attacker: BattlePokemon, defender: BattlePokemon) -> dict[str, int | str]:
    request = engine.generate_request(engine.sides[side_id].player_id)

    if request.get("forceSwitch"):
        next_index = first_alive_bench_index(engine.sides[side_id])
        if next_index is None:
            return {"type": "pass"}
        return {"type": "switch", "index": next_index}

    if attacker.must_recharge or attacker.status_condition in {"slp", "frz"}:
        return {"type": "pass"}

    enabled_ids = {
        int(move["id"])
        for move in request.get("active", [{}])[0].get("moves", [])
        if not move.get("disabled")
    }

    if not enabled_ids:
        return {"type": "move", "move_index": -1}

    best_idx: int | None = None
    best_damage = -1

    for idx, move in enumerate(attacker.moves):
        if move.move_id not in enabled_ids:
            continue
        if move.damage_class == "status":
            continue

        effective_weather = engine._effective_weather() if hasattr(engine, "_effective_weather") else engine.weather

        damage, _ = calculate_damage(
            attacker,
            defender,
            move,
            is_critical=False,
            weather=effective_weather,
            defender_semi_invulnerable=defender.semi_invulnerable,
            defending_side=engine.sides["p2" if side_id == "p1" else "p1"],
            random_factor=100,
            generation=3,
        )
        if damage > best_damage:
            best_damage = damage
            best_idx = idx

    if best_idx is None or best_damage <= 0:
        return {"type": "move", "move_index": -1}

    return {"type": "move", "move_index": best_idx}


def advance_battle_until_exhaustion(engine: CustomBattleEngine, turn_limit: int = 120) -> None:
    for _ in range(turn_limit):
        if engine.finished:
            return

        if not ensure_switch_if_needed(engine, "p1"):
            return
        if not ensure_switch_if_needed(engine, "p2"):
            return

        if engine.finished:
            return

        p1_active = engine.sides["p1"].active_pokemon
        p2_active = engine.sides["p2"].active_pokemon
        if p1_active is None or p2_active is None:
            return

        p1_action = choose_best_action(engine, "p1", p1_active, p2_active)
        p2_action = choose_best_action(engine, "p2", p2_active, p1_active)

        engine.submit_action(engine.sides["p1"].player_id, p1_action)
        if engine.finished:
            return
        engine.submit_action(engine.sides["p2"].player_id, p2_action)

    assert engine.finished, "A batalha Gen 3 nao terminou dentro do limite esperado."


def test_gen3_real_save_six_vs_six_battle_reaches_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1_name, p1_team = load_real_team("gen 3/Pokémon - Ruby Version.sav")
    p2_name, p2_team = load_real_team("gen 3/Pokémon - FireRed Version.sav")

    engine = CustomBattleEngine(
        "real-save-gen3-6v6",
        BattleSide("p1", p1_name, p1_team),
        BattleSide("p2", p2_name, p2_team),
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


def test_gen3_real_save_detect_blocks_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, zapdos, mewtwo = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        3,
        "gen 3/Pokémon - Ruby Version.sav",
        5,
    )

    zapdos_hp = zapdos.current_hp
    mewtwo_hp = mewtwo.current_hp

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(zapdos, "detect")})
    engine.submit_action("p2", {"type": "move", "move_index": move_index_by_name(mewtwo, "psychic")})

    assert zapdos.current_hp == zapdos_hp
    assert mewtwo.current_hp == mewtwo_hp
    assert zapdos.is_protected is True
    assert any("detect" in log.lower() for log in engine.logs)


def test_gen3_real_save_endure_leaves_one_hp(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, moltres, mewtwo = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        5,
        "gen 3/Pokémon - Ruby Version.sav",
        5,
    )
    moltres.current_hp = 20

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(moltres, "endure")})
    engine.submit_action("p2", {"type": "move", "move_index": move_index_by_name(mewtwo, "psychic")})

    assert moltres.current_hp == 1
    assert any("Endure" in log for log in engine.logs)


def test_gen3_real_save_substitute_absorbs_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, aggron, charmeleon = build_single_engine(
        "gen 3/Pokémon - Emerald Version.sav",
        3,
        "gen 3/Pokémon - FireRed Version.sav",
        2,
    )

    aggron_hp = aggron.current_hp
    substitute_cost = max(1, aggron.max_hp // 4)

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(aggron, "substitute")})
    engine.submit_action("p2", {"type": "move", "move_index": move_index_by_name(charmeleon, "ember")})

    assert aggron.current_hp == aggron_hp - substitute_cost
    assert aggron.substitute_hp > 0
    assert charmeleon.current_hp == charmeleon.max_hp
    assert any("Substitute" in log for log in engine.logs)


def test_gen3_real_save_whirlpool_traps_target(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, wailord, mewtwo = build_single_engine(
        "gen 3/Pokémon - Ruby Version.sav",
        0,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
    )

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(wailord, "whirlpool")})
    engine.submit_action("p2", {"type": "move", "move_index": move_index_by_name(mewtwo, "swift")})

    assert mewtwo.partial_trap_turns > 0
    assert mewtwo.trapped_by_side == "p1"
    assert mewtwo.current_hp < mewtwo.max_hp
    assert any("Whirlpool" in log or "whirlpool" in log.lower() for log in engine.logs)


def test_gen3_real_save_focus_punch_fails_after_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, aggron, zapdos = build_single_engine(
        "gen 3/Pokémon - Emerald Version.sav",
        3,
        "gen 3/Pokémon - FireRed Version.sav",
        3,
    )

    zapdos_hp = zapdos.current_hp
    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(aggron, "focus-punch")})
    engine.submit_action("p2", {"type": "move", "move_index": move_index_by_name(zapdos, "drill-peck")})

    assert zapdos.current_hp == zapdos_hp
    assert aggron.current_hp < aggron.max_hp
    assert any("fail" in log.lower() for log in engine.logs)


def test_gen3_real_save_toxic_damage_scales_each_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, mightyena, blastoise = build_single_engine(
        "gen 3/Pokémon - Emerald Version.sav",
        1,
        "gen 3/Pokémon - FireRed Version.sav",
        1,
    )

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(mightyena, "toxic")})
    engine.submit_action("p2", {"type": "pass"})

    first_hp = blastoise.current_hp
    assert blastoise.status_condition == "tox"
    assert first_hp == blastoise.max_hp - 12

    engine.submit_action("p1", {"type": "pass"})
    engine.submit_action("p2", {"type": "pass"})

    second_hp = blastoise.current_hp
    assert first_hp - second_hp == 25
    assert blastoise.status_condition == "tox"
    assert blastoise.toxic_turns >= 3
    assert any("tox" in log.lower() for log in engine.logs)


def test_gen3_real_save_recover_heals_half_hp(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, milotic, dratini = build_single_engine(
        "gen 3/Pokémon - Emerald Version.sav",
        5,
        "gen 3/Pokémon - FireRed Version.sav",
        0,
    )

    milotic.current_hp = 100
    expected_hp = min(milotic.max_hp, 100 + (milotic.max_hp // 2))

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(milotic, "recover")})
    engine.submit_action("p2", {"type": "pass"})

    assert milotic.current_hp == expected_hp
    assert dratini.current_hp == dratini.max_hp
    assert any("recover" in log.lower() for log in engine.logs)


def test_gen3_real_save_fury_cutter_power_scales(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, sceptile, blastoise = build_single_engine(
        "gen 3/Pokémon - Emerald Version.sav",
        0,
        "gen 3/Pokémon - FireRed Version.sav",
        1,
    )

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(sceptile, "fury-cutter")})
    engine.submit_action("p2", {"type": "pass"})
    first_hp = blastoise.current_hp

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(sceptile, "fury-cutter")})
    engine.submit_action("p2", {"type": "pass"})
    second_hp = blastoise.current_hp

    first_damage = blastoise.max_hp - first_hp
    second_damage = first_hp - second_hp
    assert first_damage > 0
    assert second_damage > first_damage
    assert sceptile.fury_cutter_hits == 2
    assert any("fury" in log.lower() for log in engine.logs)


def test_gen3_real_save_spite_reduces_last_move_pp(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, haunter, charmeleon = build_single_engine(
        "gen 3/Pokémon - LeafGreen Version.sav",
        4,
        "gen 3/Pokémon - FireRed Version.sav",
        2,
    )

    ember_idx = move_index_by_name(charmeleon, "ember")
    ember_move = charmeleon.moves[ember_idx]

    engine.submit_action("p1", {"type": "pass"})
    engine.submit_action("p2", {"type": "move", "move_index": ember_idx})

    pp_after_use = ember_move.pp

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(haunter, "spite")})
    engine.submit_action("p2", {"type": "pass"})

    assert ember_move.pp == max(0, pp_after_use - 4)
    assert any("spite" in log.lower() for log in engine.logs)


def test_gen3_real_save_mimic_copies_last_move(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, mewtwo, charmeleon = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "gen 3/Pokémon - FireRed Version.sav",
        2,
    )

    mimic_idx = move_index_by_name(mewtwo, "mimic")

    engine.submit_action("p1", {"type": "pass"})
    engine.submit_action("p2", {"type": "move", "move_index": move_index_by_name(charmeleon, "ember")})

    engine.submit_action("p1", {"type": "move", "move_index": mimic_idx})
    engine.submit_action("p2", {"type": "pass"})

    copied_move = mewtwo.moves[mimic_idx]
    assert copied_move.name.lower().replace("-", "").replace(" ", "") == "ember"
    assert any("mimic" in log.lower() for log in engine.logs)


def test_gen3_real_save_metronome_uses_forced_move(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    recover_id = next(move_id for move_id, data in MOVE_COMBAT_DATA.items() if str(data.get("name")).lower() == "recover")
    monkeypatch.setattr(gen3_engine_mod.random, "choice", lambda seq: recover_id if recover_id in seq else seq[0])

    engine, mew, dratini = build_single_engine(
        "gen 3/Pokémon - Ruby Version.sav",
        3,
        "gen 3/Pokémon - FireRed Version.sav",
        0,
    )

    mew.current_hp = mew.max_hp - 80
    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(mew, "metronome")})
    engine.submit_action("p2", {"type": "pass"})

    assert mew.current_hp > mew.max_hp - 80
    assert dratini.current_hp == dratini.max_hp
    assert any("recover" in log.lower() for log in engine.logs)


def test_gen3_real_save_calm_mind_boosts_special_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, mewtwo, charmeleon = build_single_engine(
        "gen 3/Pokémon - Emerald Version.sav",
        2,
        "gen 3/Pokémon - FireRed Version.sav",
        2,
    )

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(mewtwo, "calm-mind")})
    engine.submit_action("p2", {"type": "pass"})

    assert mewtwo.stat_stages["spa"] == 1
    assert mewtwo.stat_stages["spd"] == 1
    assert charmeleon.current_hp == charmeleon.max_hp
    assert any("calm" in log.lower() for log in engine.logs)


def test_gen3_real_save_dive_charges_then_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, golbat, dratini = build_single_engine(
        "gen 3/Pokémon - Ruby Version.sav",
        2,
        "gen 3/Pokémon - FireRed Version.sav",
        0,
    )

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(golbat, "dive")})
    engine.submit_action("p2", {"type": "pass"})

    assert golbat.semi_invulnerable == "dive"
    assert dratini.current_hp == dratini.max_hp

    engine.submit_action("p1", {"type": "pass"})
    engine.submit_action("p2", {"type": "pass"})

    assert golbat.semi_invulnerable is None
    assert dratini.current_hp < dratini.max_hp
    assert any("dive" in log.lower() for log in engine.logs)


def test_gen3_real_save_pressure_costs_two_pp(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, dratini, mewtwo = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        0,
        "gen 3/Pokémon - LeafGreen Version.sav",
        2,
    )

    thunder_wave_idx = move_index_by_name(dratini, "thunder-wave")
    thunder_wave_move = dratini.moves[thunder_wave_idx]
    starting_pp = thunder_wave_move.pp

    engine.submit_action("p1", {"type": "move", "move_index": thunder_wave_idx})
    engine.submit_action("p2", {"type": "pass"})

    assert mewtwo.status_condition == "par"
    assert thunder_wave_move.pp == starting_pp - 2
    assert any("pressure" in log.lower() for log in engine.logs)


def test_gen3_real_save_foresight_allows_normal_moves_to_hit_ghost(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, charizard, haunter = build_single_engine(
        "gen 3/Pokémon - LeafGreen Version.sav",
        3,
        "gen 3/Pokémon - LeafGreen Version.sav",
        4,
    )

    charizard.moves[0] = make_move(193)

    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})

    assert haunter.foresight_active is True
    assert haunter.current_hp == haunter.max_hp

    strength_idx = move_index_by_name(charizard, "strength")
    engine.submit_action("p1", {"type": "move", "move_index": strength_idx})
    engine.submit_action("p2", {"type": "pass"})

    assert haunter.current_hp < haunter.max_hp
    assert any("foresight" in log.lower() for log in engine.logs)


def test_gen3_real_save_spikes_damage_on_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1_name, p1_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    p2_name, p2_team = load_real_team("gen 3/Pokémon - FireRed Version.sav")

    p1_active = p1_team[1]
    p1_bench = p1_team[0]

    p2_active = p2_team[0]
    p2_bench = p2_team[1]

    engine = CustomBattleEngine(
        "real-save-gen3-spikes",
        BattleSide("p1", p1_name, [p1_active, p1_bench]),
        BattleSide("p2", p2_name, [p2_active, p2_bench]),
    )
    engine.start_battle()
    engine.sides["p1"].active_pokemon.moves[1] = make_move(191)

    engine.submit_action("p1", {"type": "move", "move_index": 1})
    engine.submit_action("p2", {"type": "pass"})

    assert engine.sides["p2"].spikes_layers == 1

    blastoise_hp_before = p2_bench.current_hp

    engine.submit_action("p1", {"type": "pass"})
    engine.submit_action("p2", {"type": "switch", "index": 1})

    expected_damage = max(1, p2_bench.max_hp // 8)
    assert p2_bench.current_hp == blastoise_hp_before - expected_damage
    assert engine.sides["p2"].active_pokemon is p2_bench
    assert any("spikes" in log.lower() for log in engine.logs)


def test_gen3_real_save_doubles_request_exposes_active_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1_name, p1_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    p2_name, p2_team = load_real_team("gen 3/Pokémon - FireRed Version.sav")

    engine = CustomBattleEngine(
        "real-save-gen3-doubles-request",
        BattleSide("p1", p1_name, p1_team[:2]),
        BattleSide("p2", p2_name, p2_team[:2]),
        battle_format="doubles",
    )
    engine.start_battle()

    request = engine.generate_request(engine.sides["p1"].player_id)

    assert len(request["active"]) == 2
    assert request["active"][0]["slot"] == 0
    assert request["active"][1]["slot"] == 1
    assert request["forceSwitch"] is False
    assert request["forceSwitchSlots"] == [False, False]
    assert any(move["target"] == "self" for move in request["active"][0]["moves"])
    assert any(move["target"] == "self" for move in request["active"][1]["moves"])


def test_gen3_real_save_air_lock_suppresses_rain_boost(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    control_engine = build_doubles_engine(
        "gen 3/Pokémon - Ruby Version.sav",
        [2, 3],
        "gen 3/Pokémon - Ruby Version.sav",
        [0, 5],
    )
    suppressed_engine = build_doubles_engine(
        "gen 3/Pokémon - Ruby Version.sav",
        [2, 3],
        "gen 3/Pokémon - Ruby Version.sav",
        [1, 5],
    )

    control_mewtwo = control_engine.sides["p2"].team[1]
    suppressed_mewtwo = suppressed_engine.sides["p2"].team[1]

    control_before = control_mewtwo.current_hp
    run_doubles_turn(
        control_engine,
        {"type": "move", "move_index": move_index_by_name(control_engine.sides["p1"].active_pokemon, "surf"), "slot": 0},
        {"type": "pass", "slot": 1},
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
    )
    control_damage = control_before - control_mewtwo.current_hp

    suppressed_before = suppressed_mewtwo.current_hp
    run_doubles_turn(
        suppressed_engine,
        {"type": "move", "move_index": move_index_by_name(suppressed_engine.sides["p1"].active_pokemon, "surf"), "slot": 0},
        {"type": "pass", "slot": 1},
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
    )
    suppressed_damage = suppressed_before - suppressed_mewtwo.current_hp

    assert control_engine.weather == "rain"
    assert suppressed_engine.weather == "rain"
    assert control_engine._effective_weather() == "rain"
    assert suppressed_engine._effective_weather() == "none"
    assert control_damage > suppressed_damage
    assert any(getattr(p, "ability", None) == "air-lock" for p in suppressed_engine.sides["p2"].active_list)


def test_gen3_real_save_swift_bypasses_accuracy_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("calculate_hit should not be called for Swift")

    monkeypatch.setattr(gen3_engine_mod, "calculate_hit", fail_if_called)

    engine, mewtwo, dratini = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "gen 3/Pokémon - FireRed Version.sav",
        0,
    )

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(mewtwo, "swift")})
    engine.submit_action("p2", {"type": "pass"})

    assert dratini.current_hp < dratini.max_hp
    assert any("swift" in log.lower() for log in engine.logs)


def test_gen3_real_save_overgrow_boosts_grass_damage_at_low_hp(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    normal_damage = damage_from_single_attack(
        "gen 3/Pokémon - Emerald Version.sav",
        0,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "leaf-blade",
    )
    boosted_damage = damage_from_single_attack(
        "gen 3/Pokémon - Emerald Version.sav",
        0,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "leaf-blade",
        attacker_hp=1,
    )

    assert boosted_damage > normal_damage


def test_gen3_real_save_blaze_boosts_fire_damage_at_low_hp(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    normal_damage = damage_from_single_attack(
        "gen 3/Pokémon - LeafGreen Version.sav",
        3,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "heat-wave",
    )
    boosted_damage = damage_from_single_attack(
        "gen 3/Pokémon - LeafGreen Version.sav",
        3,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "heat-wave",
        attacker_hp=1,
    )

    assert boosted_damage > normal_damage


def test_gen3_real_save_torrent_boosts_water_damage_at_low_hp(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    normal_damage = damage_from_single_attack(
        "gen 3/Pokémon - FireRed Version.sav",
        1,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "surf",
    )
    boosted_damage = damage_from_single_attack(
        "gen 3/Pokémon - FireRed Version.sav",
        1,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "surf",
        attacker_hp=1,
    )

    assert boosted_damage > normal_damage


def test_gen3_real_save_soundproof_blocks_sound_move(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, charmeleon, mewtwo = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        2,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
    )
    mewtwo.ability = "soundproof"

    engine.submit_action("p1", {"type": "move", "move_index": move_index_by_name(charmeleon, "growl")})
    engine.submit_action("p2", {"type": "pass"})

    assert mewtwo.stat_stages["atk"] == 0
    assert any("fail" in log.lower() for log in engine.logs)


def test_gen3_real_save_fake_out_is_blocked_by_inner_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    engine, attacker, defender = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        2,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
    )

    attacker.moves[0] = make_move(move_id_by_name("fake-out"))
    defender.ability = "inner-focus"
    defender.moves[0] = make_move(move_id_by_name("psychic"))

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})

    assert defender.is_flinching is False
    assert attacker.current_hp < attacker.max_hp
    assert defender.current_hp < defender.max_hp
    assert any("inner focus" in log.lower() for log in engine.logs)


def test_gen3_real_save_sleep_talk_uses_another_move(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    recover_id = move_id_by_name("recover")
    sleep_talk_id = move_id_by_name("sleep-talk")
    monkeypatch.setattr(gen3_engine_mod.random, "choice", lambda seq: 1 if 1 in seq else seq[0])

    engine, mewtwo, dratini = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "gen 3/Pokémon - FireRed Version.sav",
        0,
    )

    mewtwo.moves[0] = make_move(sleep_talk_id)
    mewtwo.moves[1] = make_move(recover_id)
    mewtwo.current_hp = max(1, mewtwo.max_hp - 80)
    mewtwo.status_condition = "slp"
    mewtwo.status_turns = 3

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert mewtwo.current_hp > max(1, mewtwo.max_hp - 80)
    assert dratini.current_hp == dratini.max_hp
    assert any("recover" in log.lower() for log in engine.logs)


def test_gen3_real_save_heal_bell_skips_soundproof_party_member(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    heal_bell_id = move_id_by_name("heal-bell")
    p1_name, p1_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    p2_name, p2_team = load_real_team("gen 3/Pokémon - FireRed Version.sav")

    healer = p1_team[2]
    protected_ally = p1_team[3]
    healer.moves[0] = make_move(heal_bell_id)
    healer.status_condition = "psn"
    protected_ally.status_condition = "brn"
    protected_ally.ability = "soundproof"

    engine = CustomBattleEngine(
        "real-save-gen3-heal-bell",
        BattleSide("p1", p1_name, [healer, protected_ally]),
        BattleSide("p2", p2_name, [p2_team[0]]),
    )
    engine.start_battle()

    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})

    assert healer.status_condition is None
    assert protected_ally.status_condition == "brn"
    assert any("heal-bell" in log.lower() for log in engine.logs)


def test_gen3_real_save_perish_song_skips_soundproof_target(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    perish_song_id = move_id_by_name("perish-song")
    engine, attacker, defender = build_single_engine(
        "gen 3/Pokémon - Ruby Version.sav",
        3,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
    )

    attacker.moves[0] = make_move(perish_song_id)
    defender.ability = "soundproof"

    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})

    assert attacker.perish_song_turns == 2
    assert defender.perish_song_turns is None
    assert any("perish song" in log.lower() for log in engine.logs)


def test_gen3_real_save_lightning_rod_redirects_electric_move_in_doubles(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    thunderbolt_id = move_id_by_name("thunderbolt")
    p1_name, p1_team = load_real_team("gen 3/Pokémon - FireRed Version.sav")
    p2_name, p2_team = load_real_team("gen 3/Pokémon - Ruby Version.sav")

    attacker = p1_team[4]
    non_rod_target = p2_team[0]
    lightning_rod_target = p2_team[1]
    attacker.moves[0] = make_move(thunderbolt_id)
    lightning_rod_target.ability = "lightning-rod"

    engine = CustomBattleEngine(
        "real-save-gen3-lightning-rod",
        BattleSide("p1", p1_name, [attacker, p1_team[0]]),
        BattleSide("p2", p2_name, [non_rod_target, lightning_rod_target]),
        battle_format="doubles",
    )
    engine.start_battle()

    engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 0, "target": "p2a"})
    engine.submit_action("p1", {"type": "pass", "slot": 1})
    engine.submit_action("p2", {"type": "pass", "slot": 0})
    engine.submit_action("p2", {"type": "pass", "slot": 1})

    assert lightning_rod_target.current_hp < lightning_rod_target.max_hp
    assert non_rod_target.current_hp == non_rod_target.max_hp
    assert any("|move|p1a: MEWTWO|thunderbolt|p2b" in log for log in engine.logs)


def test_gen3_real_save_damp_blocks_explosion(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    explosion_id = move_id_by_name("explosion")
    engine, attacker, defender = build_single_engine(
        "gen 3/Pokémon - Emerald Version.sav",
        0,
        "gen 3/Pokémon - FireRed Version.sav",
        4,
    )

    attacker.moves[0] = make_move(explosion_id)
    defender.ability = "damp"

    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})

    assert attacker.current_hp == attacker.max_hp
    assert defender.current_hp == defender.max_hp
    assert any("damp" in log.lower() for log in engine.logs)


def test_gen3_real_save_triple_kick_power_ramps(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    report = ValidationReport(
        title="Gen 3 Triple Kick validation",
        source_a="Pokémon - FireRed Version.sav",
        source_b="Pokémon - FireRed Version.sav",
    )
    report.add_header()

    engine, attacker, defender = build_single_engine(
        "gen 3/Pokémon - FireRed Version.sav",
        4,
        "gen 3/Pokémon - FireRed Version.sav",
        1,
    )

    triple_kick = BattleMove(
        move_id=9999,
        name="Triple Kick",
        type="fighting",
        power=10,
        accuracy=100,
        pp=10,
        max_pp=10,
        priority=0,
        damage_class="physical",
        effect="Hits 3 times.",
    )
    attacker.moves[0] = triple_kick
    attacker.original_moves = deepcopy(attacker.moves)
    attacker.current_hp = attacker.max_hp
    defender.current_hp = defender.max_hp

    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})

    damage_logs = [log for log in engine.logs if log.startswith("|damage|p2a:")]
    hp_values: list[int] = []
    for log in damage_logs:
        tail = log.split("|", 3)[-1]
        hp_part = tail.split(" ", 1)[0]
        hp_values.append(int(hp_part.split("/", 1)[0]))

    damages = [defender.max_hp - hp_values[0]]
    damages.extend(hp_values[i - 1] - hp_values[i] for i in range(1, len(hp_values)))

    ok = len(hp_values) >= 3 and damages[0] > 0 and damages[1] >= damages[0] and damages[2] >= damages[1]
    report.add_case(
        "Triple Kick ramp",
        ok,
        f"attacker={battle_pokemon_state(attacker)} defender={battle_pokemon_state(defender)} damages={damages[:3]} logs={'; '.join(tail_logs(engine.logs, 6))}",
        logs=tail_logs(engine.logs, 6),
    )
    report.add_summary()
    report_path = report.write("gen3-triple-kick.txt")

    assert ok, report_path.read_text(encoding="utf-8")


def test_gen3_real_save_suction_cups_blocks_roar(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    roar_id = move_id_by_name("roar")
    p1_name, p1_team = load_real_team("gen 3/Pokémon - LeafGreen Version.sav")
    p2_name, p2_team = load_real_team("gen 3/Pokémon - FireRed Version.sav")

    attacker = p1_team[3]
    target = p2_team[0]
    bench = p2_team[1]
    attacker.moves[0] = make_move(roar_id)
    target.ability = "suction-cups"

    engine = CustomBattleEngine(
        "real-save-gen3-suction-cups",
        BattleSide("p1", p1_name, [attacker]),
        BattleSide("p2", p2_name, [target, bench]),
    )
    engine.start_battle()

    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})

    assert engine.sides["p2"].active_pokemon is target
    assert any("fail" in log.lower() for log in engine.logs)


def test_gen3_real_save_counter_mirrorcoat_bide_source_tracking_report(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    report = ValidationReport(
        title="Gen 3 source tracking validation",
        source_a="Pokémon - Emerald Version.sav",
        source_b="Pokémon - Emerald Version.sav",
    )
    report.add_header()

    def active(side: BattleSide, slot_idx: int) -> BattlePokemon:
        return side.active_list[slot_idx]

    def state_line(label: str, engine: CustomBattleEngine, p1a: BattlePokemon, p1b: BattlePokemon, p2a: BattlePokemon, p2b: BattlePokemon) -> str:
        return (
            f"{label} | "
            f"p1a={battle_pokemon_state(p1a)} "
            f"p1b={battle_pokemon_state(p1b)} "
            f"p2a={battle_pokemon_state(p2a)} "
            f"p2b={battle_pokemon_state(p2b)} "
            f"logs={'; '.join(tail_logs(engine.logs, 5))}"
        )

    # Counter: the reflected hit must go back to the source of the damage, not the manually selected target.
    counter_user_name, counter_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    _, counter_foe_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    counter_engine = CustomBattleEngine(
        "real-save-gen3-counter-source-tracking",
        BattleSide("p1", counter_user_name, [counter_team[3], counter_team[5]]),
        BattleSide("p2", counter_user_name, [counter_foe_team[1], counter_foe_team[2]]),
        battle_format="doubles",
    )
    counter_engine.start_battle()
    counter_p1a = active(counter_engine.sides["p1"], 0)
    counter_p1b = active(counter_engine.sides["p1"], 1)
    counter_p2a = active(counter_engine.sides["p2"], 0)
    counter_p2b = active(counter_engine.sides["p2"], 1)
    replace_moves(counter_p1a, ["counter", "recover"])
    replace_moves(counter_p1b, ["surf", "recover"])
    replace_moves(counter_p2a, ["crunch", "dig"])
    replace_moves(counter_p2b, ["psychic", "protect"])
    for pokemon in (counter_p1a, counter_p1b, counter_p2a, counter_p2b):
        pokemon.current_hp = pokemon.max_hp

    run_doubles_turn(
        counter_engine,
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
        {"type": "move", "move_index": 0, "slot": 0, "target": "p1a"},
        {"type": "pass", "slot": 1},
    )
    run_doubles_turn(
        counter_engine,
        {"type": "move", "move_index": 0, "slot": 0, "target": "p2b"},
        {"type": "pass", "slot": 1},
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
    )
    counter_ok = counter_p2a.current_hp < counter_p2a.max_hp and counter_p2b.current_hp == counter_p2b.max_hp
    report.add_case(
        "Counter source",
        counter_ok,
        state_line("counter", counter_engine, counter_p1a, counter_p1b, counter_p2a, counter_p2b),
        logs=tail_logs(counter_engine.logs, 6),
    )

    # Counter with Follow Me: the original hit should be redirected on the target side,
    # but the reflected Counter still needs to go back to the real attacker.
    counter_follow_name, counter_follow_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    _, counter_follow_foe_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    counter_follow_engine = CustomBattleEngine(
        "real-save-gen3-counter-follow-me",
        BattleSide("p1", counter_follow_name, [counter_follow_team[3], counter_follow_team[5]]),
        BattleSide("p2", counter_follow_name, [counter_follow_foe_team[1], counter_follow_foe_team[2]]),
        battle_format="doubles",
    )
    counter_follow_engine.start_battle()
    counter_follow_p1a = active(counter_follow_engine.sides["p1"], 0)
    counter_follow_p1b = active(counter_follow_engine.sides["p1"], 1)
    counter_follow_p2a = active(counter_follow_engine.sides["p2"], 0)
    counter_follow_p2b = active(counter_follow_engine.sides["p2"], 1)
    replace_moves(counter_follow_p1a, ["recover", "recover"])
    replace_moves(counter_follow_p1b, ["follow me", "counter"])
    replace_moves(counter_follow_p2a, ["crunch", "dig"])
    replace_moves(counter_follow_p2b, ["protect", "recover"])
    for pokemon in (counter_follow_p1a, counter_follow_p1b, counter_follow_p2a, counter_follow_p2b):
        pokemon.current_hp = pokemon.max_hp

    run_doubles_turn(
        counter_follow_engine,
        {"type": "pass", "slot": 0},
        {"type": "move", "move_index": 0, "slot": 1, "target": "p1a"},
        {"type": "move", "move_index": 0, "slot": 0, "target": "p1a"},
        {"type": "pass", "slot": 1},
    )
    run_doubles_turn(
        counter_follow_engine,
        {"type": "pass", "slot": 0},
        {"type": "move", "move_index": 1, "slot": 1, "target": "p2a"},
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
    )
    counter_follow_ok = (
        counter_follow_p1b.current_hp < counter_follow_p1b.max_hp
        and counter_follow_p2a.current_hp < counter_follow_p2a.max_hp
        and counter_follow_p2b.current_hp == counter_follow_p2b.max_hp
    )
    report.add_case(
        "Counter follow-me",
        counter_follow_ok,
        state_line("counter-follow", counter_follow_engine, counter_follow_p1a, counter_follow_p1b, counter_follow_p2a, counter_follow_p2b),
        logs=tail_logs(counter_follow_engine.logs, 6),
    )

    # Mirror Coat: same source tracking, but for special damage.
    mirror_user_name, mirror_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    _, mirror_foe_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    mirror_engine = CustomBattleEngine(
        "real-save-gen3-mirror-coat-source-tracking",
        BattleSide("p1", mirror_user_name, [mirror_team[5], mirror_team[3]]),
        BattleSide("p2", mirror_user_name, [mirror_foe_team[2], mirror_foe_team[1]]),
        battle_format="doubles",
    )
    mirror_engine.start_battle()
    mirror_p1a = active(mirror_engine.sides["p1"], 0)
    mirror_p1b = active(mirror_engine.sides["p1"], 1)
    mirror_p2a = active(mirror_engine.sides["p2"], 0)
    mirror_p2b = active(mirror_engine.sides["p2"], 1)
    replace_moves(mirror_p1a, ["mirror coat", "recover"])
    replace_moves(mirror_p1b, ["surf", "recover"])
    replace_moves(mirror_p2a, ["psychic", "thunderbolt"])
    replace_moves(mirror_p2b, ["crunch", "protect"])
    for pokemon in (mirror_p1a, mirror_p1b, mirror_p2a, mirror_p2b):
        pokemon.current_hp = pokemon.max_hp

    run_doubles_turn(
        mirror_engine,
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
        {"type": "move", "move_index": 0, "slot": 0, "target": "p1a"},
        {"type": "pass", "slot": 1},
    )
    run_doubles_turn(
        mirror_engine,
        {"type": "move", "move_index": 0, "slot": 0, "target": "p2b"},
        {"type": "pass", "slot": 1},
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
    )
    mirror_ok = mirror_p2a.current_hp < mirror_p2a.max_hp and mirror_p2b.current_hp == mirror_p2b.max_hp
    report.add_case(
        "Mirror Coat source",
        mirror_ok,
        state_line("mirror", mirror_engine, mirror_p1a, mirror_p1b, mirror_p2a, mirror_p2b),
        logs=tail_logs(mirror_engine.logs, 6),
    )

    # Bide: the stored energy should release on the last attacker, not the manually selected target.
    bide_user_name, bide_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    _, bide_foe_team = load_real_team("gen 3/Pokémon - Emerald Version.sav")
    bide_engine = CustomBattleEngine(
        "real-save-gen3-bide-source-tracking",
        BattleSide("p1", bide_user_name, [bide_team[5], bide_team[3]]),
        BattleSide("p2", bide_user_name, [bide_foe_team[1], bide_foe_team[2]]),
        battle_format="doubles",
    )
    bide_engine.start_battle()
    bide_p1a = active(bide_engine.sides["p1"], 0)
    bide_p1b = active(bide_engine.sides["p1"], 1)
    bide_p2a = active(bide_engine.sides["p2"], 0)
    bide_p2b = active(bide_engine.sides["p2"], 1)
    replace_moves(bide_p1a, ["bide", "recover"])
    replace_moves(bide_p1b, ["surf", "recover"])
    replace_moves(bide_p2a, ["crunch", "dig"])
    replace_moves(bide_p2b, ["psychic", "protect"])
    for pokemon in (bide_p1a, bide_p1b, bide_p2a, bide_p2b):
        pokemon.current_hp = pokemon.max_hp

    run_doubles_turn(
        bide_engine,
        {"type": "move", "move_index": 0, "slot": 0, "target": "p2b"},
        {"type": "pass", "slot": 1},
        {"type": "move", "move_index": 0, "slot": 0, "target": "p1a"},
        {"type": "pass", "slot": 1},
    )
    run_doubles_turn(
        bide_engine,
        {"type": "move", "move_index": 0, "slot": 0, "target": "p2b"},
        {"type": "pass", "slot": 1},
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
    )
    run_doubles_turn(
        bide_engine,
        {"type": "move", "move_index": 0, "slot": 0, "target": "p2b"},
        {"type": "pass", "slot": 1},
        {"type": "pass", "slot": 0},
        {"type": "pass", "slot": 1},
    )
    bide_ok = bide_p2a.current_hp < bide_p2a.max_hp and bide_p2b.current_hp == bide_p2b.max_hp
    report.add_case(
        "Bide source",
        bide_ok,
        state_line("bide", bide_engine, bide_p1a, bide_p1b, bide_p2a, bide_p2b),
        logs=tail_logs(bide_engine.logs, 6),
    )

    report.add_summary()
    report_path = report.write("gen3-counter-mirrorcoat-bide.txt")

    assert report.fail_count == 0, report_path.read_text(encoding="utf-8")
