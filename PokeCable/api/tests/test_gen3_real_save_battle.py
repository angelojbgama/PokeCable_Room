from __future__ import annotations

import sys
from pathlib import Path

import pytest

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

        damage, _ = calculate_damage(
            attacker,
            defender,
            move,
            is_critical=False,
            weather=engine.weather,
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
