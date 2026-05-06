from __future__ import annotations

from copy import deepcopy

import pytest

from app.data.move_combat_data import get_move_combat_data
from app.engines.gen3 import battle_damage as gen3_damage_mod
from app.engines.gen3 import battle_engine_core as gen3_engine_mod
from app.engines.gen3 import battle_move_effects as gen3_move_effects_mod
from app.engines.gen3 import battle_utils as gen3_utils_mod
from app.engines.gen3.battle_engine_core import BattleSide, CustomBattleEngine
from app.engines.gen3.battle_pokemon import BattleMove, BattlePokemon, BattleStats


def make_move(move_id: int, pp: int | None = None) -> BattleMove:
    data = get_move_combat_data(move_id)
    assert data is not None
    return BattleMove(
        move_id=move_id,
        name=str(data["name"]),
        type=str(data["type"]),
        power=int(data["power"]) if data.get("power") is not None else 0,
        accuracy=int(data["accuracy"]) if data.get("accuracy") is not None else 100,
        pp=int(pp if pp is not None else data["pp"]),
        max_pp=int(data["pp"]),
        priority=int(data.get("priority") or 0),
        damage_class=str(data["damage_class"]),
        effect=str(data.get("effect") or ""),
        effect_chance=data.get("effect_chance"),
    )


def create_mock_pokemon(
    *,
    name: str = "Mew",
    nickname: str | None = None,
    level: int = 50,
    hp: int = 200,
    types: list[str] | None = None,
    gender: str | None = None,
    moves: list[BattleMove] | None = None,
    ability: str | None = None,
    atk: int = 100,
    defen: int = 100,
    spa: int = 100,
    spd: int = 100,
    spe: int = 100,
) -> BattlePokemon:
    stats = BattleStats(hp=hp, atk=atk, defen=defen, spa=spa, spd=spd, spe=spe)
    if moves is None:
        moves = [make_move(33)]
    return BattlePokemon(
        national_id=151,
        name=name,
        nickname=nickname or name,
        level=level,
        types=list(types or ["normal"]),
        original_types=list(types or ["normal"]),
        base_stats={"hp": hp, "atk": atk, "def": defen, "spa": spa, "spd": spd, "spe": spe},
        ivs={"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
        evs={"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
        nature_id=0,
        ability=ability,
        original_ability=ability,
        max_hp=hp,
        current_hp=hp,
        stats=stats,
        original_stats=stats,
        moves=moves,
        original_moves=deepcopy(moves),
        gender=gender,
    )


def setup_engine(p1_pkmn: BattlePokemon, p2_pkmn: BattlePokemon) -> CustomBattleEngine:
    engine = CustomBattleEngine(
        "gen3-mechanics",
        BattleSide("p1", "Player 1", [p1_pkmn]),
        BattleSide("p2", "Player 2", [p2_pkmn]),
    )
    engine.start_battle()
    return engine


def patch_deterministic_battle(monkeypatch: pytest.MonkeyPatch, *, random_value: float = 0.99) -> None:
    monkeypatch.setattr(gen3_engine_mod, "calculate_hit", lambda *args, **kwargs: True)
    monkeypatch.setattr(gen3_engine_mod, "determine_critical", lambda *args, **kwargs: False)
    monkeypatch.setattr(gen3_engine_mod.random, "random", lambda: random_value)
    monkeypatch.setattr(gen3_engine_mod.random, "randint", lambda a, b: a)
    monkeypatch.setattr(gen3_engine_mod.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(gen3_damage_mod.random, "randint", lambda a, b: a)
    monkeypatch.setattr(gen3_move_effects_mod.random, "random", lambda: random_value)
    monkeypatch.setattr(gen3_move_effects_mod.random, "randint", lambda a, b: a)
    monkeypatch.setattr(gen3_utils_mod.random, "random", lambda: random_value)
    monkeypatch.setattr(gen3_utils_mod.random, "randint", lambda a, b: a)


def run_turn(engine: CustomBattleEngine, p1_action: dict[str, int | str], p2_action: dict[str, int | str]) -> None:
    assert engine.submit_action("p1", p1_action) is True
    assert engine.submit_action("p2", p2_action) is True


def test_gen3_leech_seed_drains_and_heals(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(moves=[make_move(73)], hp=200)
    p2 = create_mock_pokemon(name="Snorlax", types=["normal"], moves=[make_move(33)], hp=200)
    p1.current_hp = 150
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.leech_seed_recipient == "p1"
    assert p2.current_hp == 175
    assert p1.current_hp == 175


def test_gen3_disable_blocks_last_move(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)
    monkeypatch.setattr(gen3_engine_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen3_move_effects_mod.random, "randint", lambda a, b: b)

    p1 = create_mock_pokemon(name="DisableUser", moves=[make_move(50), make_move(33)], spe=120)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], spe=80)
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "pass"}, {"type": "move", "move_index": 0})
    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.disable_move_id == 33
    assert p2.disable_turns > 0
    assert engine.submit_action("p2", {"type": "move", "move_index": 0}) is False
    assert any("disable" in log.lower() for log in engine.logs)


def test_gen3_encore_forces_last_move_repeat(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="EncoreUser", moves=[make_move(227), make_move(33)], spe=120)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33), make_move(45)], spe=80)
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "pass"}, {"type": "move", "move_index": 0})
    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 1})
    assert p2.encore_turns > 0
    assert p2.encore_move_index == 0

    run_turn(engine, {"type": "pass"}, {"type": "move", "move_index": 1})

    assert p2.last_move_id == 33
    assert p2.moves[0].pp < 35


def test_gen3_attract_can_prevent_action(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch, random_value=0.0)

    p1 = create_mock_pokemon(name="Male", gender="♂", moves=[make_move(213)], spe=120)
    p2 = create_mock_pokemon(name="Female", gender="♀", moves=[make_move(33)], spe=80)
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    run_turn(engine, {"type": "pass"}, {"type": "move", "move_index": 0})

    assert p2.current_hp == p2.max_hp
    assert any("attract" in log.lower() for log in engine.logs)


def test_gen3_future_sight_hits_after_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Psi", moves=[make_move(248)], spa=140, spe=120)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=300, spe=80)
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert engine.sides["p2"].future_sight_turns == 1
    assert p2.current_hp == p2.max_hp

    run_turn(engine, {"type": "pass"}, {"type": "pass"})
    assert engine.sides["p2"].future_sight_turns == 0
    assert p2.current_hp < p2.max_hp


def test_gen3_pursuit_hits_switching_target(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Hunter", moves=[make_move(228)], atk=140, spe=120)
    p2_active = create_mock_pokemon(name="Runner", moves=[make_move(33)], hp=220, spe=80)
    p2_bench = create_mock_pokemon(name="Bench", moves=[make_move(33)], hp=220, spe=60)
    engine = CustomBattleEngine(
        "gen3-pursuit",
        BattleSide("p1", "Player 1", [p1]),
        BattleSide("p2", "Player 2", [p2_active, p2_bench]),
    )
    engine.start_battle()

    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "switch", "index": 1})

    assert p2_active.current_hp < p2_active.max_hp
    assert engine.sides["p2"].active_pokemon is p2_bench


def test_gen3_pain_split_averages_hp(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Splitter", moves=[make_move(220)], hp=400)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=400)
    p1.current_hp = 100
    p2.current_hp = 300
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p1.current_hp == 200
    assert p2.current_hp == 200


def test_gen3_refresh_cures_self(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Cleaner", moves=[make_move(287)], hp=200)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=200)
    p1.status_condition = "brn"
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p1.status_condition is None
    assert p1.toxic_turns == 0


def test_gen3_heal_bell_cures_party(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Bell", moves=[make_move(215)], hp=200)
    p1_bench = create_mock_pokemon(name="Bench", moves=[make_move(33)], hp=200)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=200)
    p1.status_condition = "psn"
    p1_bench.status_condition = "brn"
    p2.status_condition = "par"

    engine = CustomBattleEngine(
        "gen3-heal-bell",
        BattleSide("p1", "Player 1", [p1, p1_bench]),
        BattleSide("p2", "Player 2", [p2]),
    )
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p1.status_condition is None
    assert p1_bench.status_condition is None
    assert p2.status_condition == "par"


def test_gen3_psych_up_copies_stat_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Copycat", moves=[make_move(244)], hp=200)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=200)
    p2.stat_stages["atk"] = 2
    p2.stat_stages["spd"] = -1
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p1.stat_stages == p2.stat_stages


def test_gen3_rollout_scales_power(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Roller", moves=[make_move(205)], atk=140, spe=120)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=400, spe=80)
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    first_damage = p2.max_hp - p2.current_hp
    assert p1.rollout_turns == 1

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    second_damage = p2.max_hp - p2.current_hp - first_damage
    assert p1.rollout_turns == 2
    assert second_damage > first_damage


def test_gen3_stockpile_spit_up_and_swallow(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Tank", moves=[make_move(254), make_move(255), make_move(256)], hp=320, atk=120, spa=120, spe=80)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=320, defen=90, spd=90, spe=70)
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p1.stockpile_count == 1
    assert p1.stat_stages["def"] == 1
    assert p1.stat_stages["spd"] == 1

    p1.current_hp = 100
    run_turn(engine, {"type": "move", "move_index": 2}, {"type": "pass"})
    assert p1.stockpile_count == 0
    assert p1.current_hp > 100

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    run_turn(engine, {"type": "move", "move_index": 1}, {"type": "pass"})
    assert p1.stockpile_count == 0
    assert p2.current_hp < p2.max_hp


def test_gen3_yawn_and_nightmare(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Sleeper", moves=[make_move(281), make_move(171)], hp=240)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=240)
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p2.yawn_turns == 1

    run_turn(engine, {"type": "pass"}, {"type": "pass"})
    assert p2.status_condition == "slp"

    p2.current_hp = p2.max_hp
    p2.status_turns = 2
    run_turn(engine, {"type": "move", "move_index": 1}, {"type": "pass"})
    assert p2.current_hp < p2.max_hp
    assert p2.nightmare_active is True


def test_gen3_lock_on_bypasses_semi_invulnerable(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Locker", moves=[make_move(199), make_move(33)], atk=140, spe=120)
    p2 = create_mock_pokemon(name="Dodger", moves=[make_move(19)], hp=260, spe=80)
    engine = setup_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    assert p2.semi_invulnerable == "fly"
    assert p1.lock_on_turns == 1

    run_turn(engine, {"type": "move", "move_index": 1}, {"type": "pass"})
    assert p2.current_hp < p2.max_hp
    assert p1.lock_on_turns == 0


def test_gen3_transform_copies_and_reverts_on_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon(name="Transformer", moves=[make_move(144), make_move(33)], ability="torrent", types=["water"], hp=220)
    p1_bench = create_mock_pokemon(name="Bench", moves=[make_move(33)], ability="overgrow", types=["grass"], hp=220)
    p2 = create_mock_pokemon(name="Target", moves=[make_move(33)], ability="levitate", types=["ghost"], hp=220)
    engine = CustomBattleEngine(
        "gen3-transform",
        BattleSide("p1", "Player 1", [p1, p1_bench]),
        BattleSide("p2", "Player 2", [p2]),
    )
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p1.ability == "levitate"
    assert p1.types == ["ghost"]

    run_turn(engine, {"type": "switch", "index": 1}, {"type": "pass"})
    assert p1.ability == "torrent"
    assert p1.types == ["water"]


def test_gen3_doubles_follow_me_redirects_single_target_attack(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1_redir = create_mock_pokemon(name="Redirector", moves=[make_move(266)], hp=220, spe=120)
    p1_ally = create_mock_pokemon(name="Ally", moves=[make_move(33)], hp=220, spe=100)
    p2_attacker = create_mock_pokemon(name="Attacker", moves=[make_move(33)], hp=220, spe=80)
    p2_bench = create_mock_pokemon(name="Bench", moves=[make_move(33)], hp=220, spe=70)

    engine = CustomBattleEngine(
        "gen3-follow-me",
        BattleSide("p1", "Player 1", [p1_redir, p1_ally]),
        BattleSide("p2", "Player 2", [p2_attacker, p2_bench]),
        battle_format="doubles",
    )
    engine.start_battle()

    engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 0})
    engine.submit_action("p1", {"type": "pass", "slot": 1})
    engine.submit_action("p2", {"type": "move", "move_index": 0, "slot": 0, "target": "p1b"})
    engine.submit_action("p2", {"type": "pass", "slot": 1})

    assert p1_redir.current_hp < p1_redir.max_hp
    assert p1_ally.current_hp == p1_ally.max_hp
    assert any("follow me" in log.lower() for log in engine.logs)


def test_gen3_doubles_helping_hand_boosts_partner_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    helper = create_mock_pokemon(name="Helper", moves=[make_move(270)], hp=220, spe=120)
    striker = create_mock_pokemon(name="Striker", moves=[make_move(33)], atk=130, hp=220, spe=100)
    target = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=220, spe=80)
    target_bench = create_mock_pokemon(name="Bench", moves=[make_move(33)], hp=220, spe=70)

    boosted_engine = CustomBattleEngine(
        "gen3-helping-hand-boosted",
        BattleSide("p1", "Player 1", [helper, striker]),
        BattleSide("p2", "Player 2", [target, target_bench]),
        battle_format="doubles",
    )
    boosted_engine.start_battle()
    boosted_engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 0})
    boosted_engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 1, "target": "p2a"})
    boosted_engine.submit_action("p2", {"type": "pass", "slot": 0})
    boosted_engine.submit_action("p2", {"type": "pass", "slot": 1})
    boosted_damage = target.max_hp - target.current_hp

    baseline_helper = create_mock_pokemon(name="Helper", moves=[make_move(270)], hp=220, spe=120)
    baseline_striker = create_mock_pokemon(name="Striker", moves=[make_move(33)], atk=130, hp=220, spe=100)
    baseline_target = create_mock_pokemon(name="Target", moves=[make_move(33)], hp=220, spe=80)
    baseline_bench = create_mock_pokemon(name="Bench", moves=[make_move(33)], hp=220, spe=70)

    baseline_engine = CustomBattleEngine(
        "gen3-helping-hand-baseline",
        BattleSide("p1", "Player 1", [baseline_helper, baseline_striker]),
        BattleSide("p2", "Player 2", [baseline_target, baseline_bench]),
        battle_format="doubles",
    )
    baseline_engine.start_battle()
    baseline_engine.submit_action("p1", {"type": "pass", "slot": 0})
    baseline_engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 1, "target": "p2a"})
    baseline_engine.submit_action("p2", {"type": "pass", "slot": 0})
    baseline_engine.submit_action("p2", {"type": "pass", "slot": 1})
    baseline_damage = baseline_target.max_hp - baseline_target.current_hp

    assert boosted_damage > baseline_damage
    assert any("helping hand" in log.lower() for log in boosted_engine.logs)


def test_gen3_doubles_snatch_steals_self_target_boost(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    snatcher = create_mock_pokemon(name="Snatcher", moves=[make_move(289)], hp=220, spe=120)
    snatch_partner = create_mock_pokemon(name="Partner", moves=[make_move(33)], hp=220, spe=100)
    setup_user = create_mock_pokemon(name="Setup", moves=[make_move(14)], hp=220, spe=80)
    setup_partner = create_mock_pokemon(name="Bench", moves=[make_move(33)], hp=220, spe=70)

    engine = CustomBattleEngine(
        "gen3-snatch",
        BattleSide("p1", "Player 1", [snatcher, snatch_partner]),
        BattleSide("p2", "Player 2", [setup_user, setup_partner]),
        battle_format="doubles",
    )
    engine.start_battle()

    engine.submit_action("p1", {"type": "move", "move_index": 0, "slot": 0})
    engine.submit_action("p1", {"type": "pass", "slot": 1})
    engine.submit_action("p2", {"type": "move", "move_index": 0, "slot": 0})
    engine.submit_action("p2", {"type": "pass", "slot": 1})

    assert snatcher.stat_stages["atk"] == 2
    assert setup_user.stat_stages["atk"] == 0
    assert any("snatch" in log.lower() for log in engine.logs)
