from __future__ import annotations

import pytest

from app.engines.gen1 import damage as gen1_damage_mod
from app.engines.gen1 import engine as gen1_engine_mod
from app.engines.gen1 import utils as gen1_utils_mod
from app.engines.gen1.damage import calculate_damage_gen1
from app.engines.gen1.engine import BattleEngineGen1, BattleSideGen1
from app.engines.gen1.models import BattleMoveGen1, BattleStatsGen1, PokemonGen1
from app.engines.gen1.utils import calculate_hit_gen1, determine_critical_gen1


def make_move(
    move_id: int,
    name: str,
    move_type: str,
    power: int | None,
    accuracy: int | None,
    pp: int,
    damage_class: str,
    *,
    priority: int = 0,
    effect_chance: int | None = None,
    effect: str = "",
    high_crit: bool = False,
) -> BattleMoveGen1:
    return BattleMoveGen1(
        move_id=move_id,
        name=name,
        type=move_type,
        power=power,
        accuracy=accuracy,
        pp=pp,
        max_pp=pp,
        priority=priority,
        damage_class=damage_class,
        effect_chance=effect_chance,
        effect=effect,
        high_crit=high_crit,
    )


def make_pokemon(
    *,
    name: str = "Mew",
    nickname: str | None = None,
    level: int = 50,
    hp: int = 100,
    current_hp: int | None = None,
    types: tuple[str, ...] | list[str] = ("psychic",),
    moves: list[BattleMoveGen1] | None = None,
    atk: int = 100,
    defense: int = 100,
    speed: int = 100,
    special: int = 100,
    base_speed: int | None = None,
    status_condition: str | None = None,
    status_turns: int = 0,
    weight: float = 50.0,
) -> PokemonGen1:
    stats = BattleStatsGen1(hp=hp, atk=atk, defen=defense, spe=speed, special=special)
    default_moves = [make_move(1, "Pound", "normal", 40, 100, 35, "physical")]
    return PokemonGen1(
        national_id=151,
        name=name,
        nickname=nickname or name,
        level=level,
        types=list(types),
        max_hp=hp,
        current_hp=current_hp if current_hp is not None else hp,
        stats=stats,
        base_speed=base_speed if base_speed is not None else speed,
        dvs={"atk": 15, "def": 15, "spe": 15, "spc": 15, "hp": 15},
        moves=moves if moves is not None else default_moves,
        status_condition=status_condition,
        status_turns=status_turns,
        weight=weight,
    )


def make_engine(p1: PokemonGen1, p2: PokemonGen1) -> BattleEngineGen1:
    side1 = BattleSideGen1("p1", "Player 1", [p1])
    side2 = BattleSideGen1("p2", "Player 2", [p2])
    engine = BattleEngineGen1("test-gen1", side1, side2)
    engine.start_battle()
    return engine


def run_turn(engine: BattleEngineGen1, p1_action: dict[str, object], p2_action: dict[str, object]) -> None:
    engine.submit_action("p1", p1_action)
    engine.submit_action("p2", p2_action)


def patch_damage_roll(monkeypatch: pytest.MonkeyPatch, value: int = 255) -> None:
    monkeypatch.setattr(gen1_damage_mod.random, "randint", lambda a, b: value)


def patch_hit_roll(monkeypatch: pytest.MonkeyPatch, value: int = 0) -> None:
    monkeypatch.setattr(gen1_engine_mod, "calculate_hit_gen1", lambda *args, **kwargs: True)


def patch_crit_roll(monkeypatch: pytest.MonkeyPatch, value: float = 0.99) -> None:
    monkeypatch.setattr(gen1_engine_mod, "determine_critical_gen1", lambda *args, **kwargs: value < 0.5)


def patch_engine_randint(monkeypatch: pytest.MonkeyPatch, value: int = 1) -> None:
    monkeypatch.setattr(gen1_engine_mod.random, "randint", lambda a, b: value)


def patch_engine_random(monkeypatch: pytest.MonkeyPatch, value: float = 0.0) -> None:
    monkeypatch.setattr(gen1_engine_mod.random, "random", lambda: value)


def patch_engine_choice(monkeypatch: pytest.MonkeyPatch, chooser) -> None:
    monkeypatch.setattr(gen1_engine_mod.random, "choice", chooser)


def single_attack_damage(
    move: BattleMoveGen1,
    *,
    attacker_types: tuple[str, ...] = ("psychic",),
    defender_types: tuple[str, ...] = ("normal",),
    attacker_hp: int = 200,
    defender_hp: int = 200,
    attacker_speed: int = 100,
    defender_speed: int = 80,
    attacker_base_speed: int | None = None,
    defender_base_speed: int | None = None,
    attacker_weight: float = 50.0,
    defender_weight: float = 50.0,
    attacker_setup=None,
    defender_setup=None,
) -> tuple[BattleEngineGen1, int]:
    attacker = make_pokemon(
        hp=attacker_hp,
        current_hp=attacker_hp,
        types=attacker_types,
        moves=[move],
        speed=attacker_speed,
        base_speed=attacker_base_speed,
        weight=attacker_weight,
    )
    defender = make_pokemon(
        hp=defender_hp,
        current_hp=defender_hp,
        types=defender_types,
        moves=[make_move(1, "Pound", "normal", 40, 100, 35, "physical")],
        speed=defender_speed,
        base_speed=defender_base_speed,
        weight=defender_weight,
    )
    engine = make_engine(attacker, defender)
    if attacker_setup is not None:
        attacker_setup(engine)
    if defender_setup is not None:
        defender_setup(engine)
    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    return engine, defender_hp - engine.sides["p2"].active_pokemon.current_hp


def test_gen1_basic_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)

    p1 = make_pokemon(types=("psychic",), moves=[make_move(1, "Pound", "normal", 40, 100, 35, "physical")])
    p2 = make_pokemon(types=("water",))
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    damage = 100 - p2.current_hp
    assert 16 <= damage <= 19


def test_gen1_type_immunity(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)

    p1 = make_pokemon(
        types=("ghost",),
        moves=[make_move(122, "Lick", "ghost", 20, 100, 30, "physical")],
    )
    p2 = make_pokemon(types=("psychic",))
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.current_hp == 100
    assert any("|-immune|" in log for log in engine.logs)


def test_gen1_accuracy_glitch_matches_original_battle_math(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen1_utils_mod.random, "randint", lambda a, b: 255)
    assert calculate_hit_gen1(100, 0, 0) is False


def test_gen1_focus_energy_bug_reduces_critical_hit_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen1_utils_mod.random, "random", lambda: 0.3)
    assert determine_critical_gen1(255, is_high_crit=True, focus_energy=False) is True
    assert determine_critical_gen1(255, is_high_crit=True, focus_energy=True) is False


def test_gen1_burn_and_paralysis_modify_stats() -> None:
    burned = make_pokemon(status_condition="brn", speed=120, atk=120)
    paralyzed = make_pokemon(status_condition="par", speed=120, atk=120)

    assert burned.get_modified_stat("atk") == 60
    assert paralyzed.get_modified_stat("spe") == 30


def test_gen1_sleep_wake_loses_turn() -> None:
    p1 = make_pokemon(status_condition="slp", status_turns=1)
    p2 = make_pokemon()
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p1.status_condition is None
    assert any("|-curestatus|p1a: Mew|slp" in log for log in engine.logs)
    assert p2.current_hp == 100


def test_gen1_paralysis_can_block_action(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen1_utils_mod.random, "random", lambda: 0.1)

    p1 = make_pokemon(status_condition="par")
    p2 = make_pokemon()
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.current_hp == 100
    assert any("|cant|p1a: Mew|par" in log for log in engine.logs)


def test_gen1_freeze_blocks_action() -> None:
    p1 = make_pokemon(status_condition="frz")
    p2 = make_pokemon()
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.current_hp == 100
    assert any("|cant|p1a: Mew|frz" in log for log in engine.logs)


@pytest.mark.parametrize(
    "move, expected_status",
    [
        (make_move(86, "Thunder Wave", "electric", None, 100, 20, "status"), "par"),
        (make_move(47, "Sing", "normal", None, 55, 15, "status"), "slp"),
        (make_move(77, "Poison Powder", "poison", None, 75, 35, "status"), "psn"),
        (make_move(53, "Flamethrower", "fire", 90, 100, 15, "special", effect_chance=10), "brn"),
        (make_move(58, "Ice Beam", "ice", 90, 100, 10, "special", effect_chance=10), "frz"),
    ],
)
def test_gen1_major_status_moves_apply(monkeypatch: pytest.MonkeyPatch, move: BattleMoveGen1, expected_status: str) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_randint(monkeypatch, 1)

    p1 = make_pokemon(types=("psychic",), moves=[move], hp=200, current_hp=200)
    p2 = make_pokemon(types=("normal",), hp=200, current_hp=200)
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.status_condition == expected_status


@pytest.mark.parametrize(
    "move, target_types",
    [
        (make_move(86, "Thunder Wave", "electric", None, 100, 20, "status"), ("ground",)),
        (make_move(47, "Sing", "normal", None, 55, 15, "status"), ("ghost",)),
    ],
)
def test_gen1_type_immunity_blocks_status_moves(
    monkeypatch: pytest.MonkeyPatch,
    move: BattleMoveGen1,
    target_types: tuple[str, ...],
) -> None:
    patch_hit_roll(monkeypatch, 0)

    p1 = make_pokemon(types=("psychic",), moves=[move])
    p2 = make_pokemon(types=target_types)
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.status_condition is None


def test_gen1_burn_poison_and_toxic_tick_at_end_of_turn() -> None:
    burned = make_pokemon(hp=160, current_hp=160, status_condition="brn")
    poisoned = make_pokemon(hp=160, current_hp=160, status_condition="psn")
    engine = make_engine(burned, poisoned)

    run_turn(engine, {"type": "pass"}, {"type": "pass"})

    assert burned.current_hp == 150
    assert poisoned.current_hp == 150


def test_gen1_toxic_accumulates_each_turn() -> None:
    toxic = make_pokemon(hp=160, current_hp=160, status_condition="tox")
    target = make_pokemon()
    engine = make_engine(toxic, target)

    run_turn(engine, {"type": "pass"}, {"type": "pass"})
    assert toxic.current_hp == 150
    assert toxic.toxic_n == 2

    run_turn(engine, {"type": "pass"}, {"type": "pass"})
    assert toxic.current_hp == 130
    assert toxic.toxic_n == 3


def test_gen1_substitute_blocks_damage_and_status(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_randint(monkeypatch, 1)

    substitute = make_move(164, "Substitute", "normal", None, None, 10, "status")
    thunder_wave = make_move(86, "Thunder Wave", "electric", None, 100, 20, "status")

    p1 = make_pokemon(
        hp=160,
        current_hp=160,
        speed=200,
        moves=[substitute],
    )
    p2 = make_pokemon(
        hp=160,
        current_hp=160,
        speed=50,
        moves=[thunder_wave],
    )
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})

    assert p1.current_hp == 120
    assert p1.substitute_hp == 40
    assert p1.status_condition is None
    assert p2.current_hp == 160


def test_gen1_partial_trap_blocks_move_and_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_randint(monkeypatch, 2)

    wrap = make_move(35, "Wrap", "normal", 15, 100, 20, "physical")
    pound = make_move(1, "Pound", "normal", 40, 100, 35, "physical")

    p1 = make_pokemon(hp=160, current_hp=160, speed=200, moves=[wrap])
    p2 = make_pokemon(hp=160, current_hp=160, speed=50, moves=[pound])
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})

    assert p2.is_trapped is True
    assert any("|cant|p2a: Mew|trap" in log for log in engine.logs)

    engine.submit_action("p2", {"type": "switch", "index": 0})
    assert any("|cant|p2a: Mew|trap" in log for log in engine.logs)
    assert engine.sides["p2"].active_index == 0


def test_gen1_leech_seed_drains_and_heals(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_engine_randint(monkeypatch, 1)

    leech_seed = make_move(73, "Leech Seed", "grass", None, 90, 10, "status")
    p1 = make_pokemon(hp=160, current_hp=120, speed=200, moves=[leech_seed])
    p2 = make_pokemon(hp=160, current_hp=160)
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p1.current_hp == 140
    assert p2.current_hp == 140
    assert p2.leech_seeded is True


def test_gen1_disable_blocks_last_move(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_randint(monkeypatch, 1)

    pound = make_move(1, "Pound", "normal", 40, 100, 35, "physical")
    disable = make_move(50, "Disable", "normal", None, 100, 20, "status")

    p1 = make_pokemon(speed=50, moves=[pound, disable])
    p2 = make_pokemon(speed=200, moves=[pound])
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 1}, {"type": "move", "move_index": 0})

    assert p1.last_move_id == 50
    assert p2.disable_move_id == 1

    p2_hp_before = p2.current_hp
    run_turn(engine, {"type": "pass"}, {"type": "move", "move_index": 0})

    assert p2.current_hp == p2_hp_before
    assert any("|cant|p2a: Mew|disable" in log for log in engine.logs)


def test_gen1_fly_becomes_invulnerable_then_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_randint(monkeypatch, 1)

    fly = make_move(19, "Fly", "flying", 90, 95, 15, "physical")
    pound = make_move(1, "Pound", "normal", 40, 100, 35, "physical")

    p1 = make_pokemon(speed=200, base_speed=200, moves=[fly])
    p2 = make_pokemon(speed=50, base_speed=50, moves=[pound])
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    assert p2.current_hp == 100
    assert p1.semi_invulnerable == "fly"
    assert any("|-miss|" in log for log in engine.logs)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p2.current_hp < 100
    assert p1.semi_invulnerable is None


def test_gen1_hyper_beam_requires_recharge_only_if_target_survives(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_randint(monkeypatch, 1)

    hyper_beam = make_move(63, "Hyper Beam", "normal", 150, 90, 5, "special")
    p1 = make_pokemon(speed=150, base_speed=150, moves=[hyper_beam], atk=200, special=200)
    p2 = make_pokemon(hp=400, current_hp=400)
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p2.current_hp > 0
    assert p1.must_recharge is True

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p1.must_recharge is False
    assert any("|cant|p1a: Mew|recharge" in log for log in engine.logs)


def test_gen1_multi_hit_move_hits_multiple_times(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)

    double_kick = make_move(24, "Double Kick", "fighting", 30, 100, 30, "physical")
    p1 = make_pokemon(speed=200, moves=[double_kick])
    p2 = make_pokemon(hp=200, current_hp=200)
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    damage_logs = [log for log in engine.logs if log.startswith("|-damage|p2a:")]
    assert len(damage_logs) == 2
    assert p2.current_hp < 200


def test_gen1_drain_and_recoil_moves_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)

    mega_drain = make_move(72, "Mega Drain", "grass", 40, 100, 15, "special")
    take_down = make_move(36, "Take Down", "normal", 90, 85, 20, "physical")

    drain_user = make_pokemon(speed=200, current_hp=100, hp=200, moves=[mega_drain], types=("grass",))
    recoil_user = make_pokemon(speed=200, current_hp=200, hp=200, moves=[take_down], types=("normal",))
    target = make_pokemon(hp=200, current_hp=200)

    drain_engine = make_engine(drain_user, target)
    run_turn(drain_engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert drain_engine.sides["p1"].active_pokemon.current_hp > 100

    recoil_target = make_pokemon(hp=200, current_hp=200)
    recoil_engine = make_engine(recoil_user, recoil_target)
    run_turn(recoil_engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert recoil_engine.sides["p1"].active_pokemon.current_hp < 200


def test_gen1_counter_and_bide(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_randint(monkeypatch, 1)

    pound = make_move(1, "Pound", "normal", 40, 100, 35, "physical")
    counter = make_move(68, "Counter", "fighting", None, 100, 20, "status")
    bide = make_move(117, "Bide", "normal", None, None, 10, "status")

    counter_user = make_pokemon(speed=50, current_hp=200, hp=200, moves=[pound, counter], types=("water",))
    attacker = make_pokemon(speed=200, current_hp=200, hp=200, moves=[pound], types=("water",))
    counter_engine = make_engine(counter_user, attacker)

    run_turn(counter_engine, {"type": "pass"}, {"type": "move", "move_index": 0})
    run_turn(counter_engine, {"type": "move", "move_index": 1}, {"type": "pass"})
    assert attacker.current_hp < 200
    assert counter_user.last_damage_taken > 0

    bide_user = make_pokemon(speed=200, current_hp=200, hp=200, moves=[bide], types=("water",))
    bide_target = make_pokemon(speed=50, current_hp=200, hp=200, moves=[pound], types=("water",))
    bide_engine = make_engine(bide_user, bide_target)

    run_turn(bide_engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    run_turn(bide_engine, {"type": "pass"}, {"type": "move", "move_index": 0})
    run_turn(bide_engine, {"type": "pass"}, {"type": "pass"})

    assert bide_target.current_hp < 200
    assert bide_user.bide_turns is None


def test_gen1_rage_boosts_attack_when_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)

    rage = make_move(99, "Rage", "normal", 20, 100, 20, "physical")
    pound = make_move(1, "Pound", "normal", 40, 100, 35, "physical")

    p1 = make_pokemon(speed=200, current_hp=200, hp=200, moves=[rage], types=("normal",))
    p2 = make_pokemon(speed=50, current_hp=200, hp=200, moves=[pound], types=("normal",))
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})

    assert p1.rage_active is True
    assert p1.stat_stages["atk"] == 1


@pytest.mark.parametrize(
    "move, defender_setup",
    [
        (
            make_move(1, "Pound", "normal", 40, 100, 35, "physical"),
            lambda engine: setattr(engine.sides["p2"], "reflect_turns", 5),
        ),
        (
            make_move(55, "Water Gun", "water", 40, 100, 25, "special"),
            lambda engine: setattr(engine.sides["p2"], "light_screen_turns", 5),
        ),
    ],
)
def test_gen1_reflect_light_screen_reduce_damage(
    monkeypatch: pytest.MonkeyPatch,
    move: BattleMoveGen1,
    defender_setup,
) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)

    _, damage_plain = single_attack_damage(move, attacker_types=("psychic",) if move.damage_class == "physical" else ("normal",))
    _, damage_screen = single_attack_damage(
        move,
        attacker_types=("psychic",) if move.damage_class == "physical" else ("normal",),
        defender_setup=defender_setup,
    )
    assert damage_screen < damage_plain


def test_gen1_critical_hits_ignore_reflect(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    monkeypatch.setattr(gen1_utils_mod.random, "random", lambda: 0.0)

    slash = make_move(163, "Slash", "normal", 70, 100, 20, "physical", high_crit=True)

    attacker_a = make_pokemon(types=("psychic",), base_speed=255, moves=[slash], hp=200, current_hp=200)
    defender_a = make_pokemon(types=("normal",), hp=200, current_hp=200)
    engine_a = make_engine(attacker_a, defender_a)
    run_turn(engine_a, {"type": "move", "move_index": 0}, {"type": "pass"})
    damage_no_reflect = 200 - engine_a.sides["p2"].active_pokemon.current_hp
    assert any("|-crit|" in log for log in engine_a.logs)

    attacker_b = make_pokemon(types=("psychic",), base_speed=255, moves=[slash], hp=200, current_hp=200)
    defender_b = make_pokemon(types=("normal",), hp=200, current_hp=200)
    engine_b = make_engine(attacker_b, defender_b)
    engine_b.sides["p2"].reflect_turns = 5
    run_turn(engine_b, {"type": "move", "move_index": 0}, {"type": "pass"})
    damage_with_reflect = 200 - engine_b.sides["p2"].active_pokemon.current_hp

    assert damage_with_reflect == damage_no_reflect


def test_gen1_mist_blocks_stat_drops_and_haze_clears_modifiers(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_engine_randint(monkeypatch, 1)

    mist = make_move(54, "Mist", "ice", None, None, 30, "status")
    growl = make_move(45, "Growl", "normal", None, 100, 40, "status")
    haze = make_move(97, "Haze", "ice", None, None, 30, "status")

    p1 = make_pokemon(speed=200, moves=[mist, haze])
    p2 = make_pokemon(speed=50, moves=[growl])
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    run_turn(engine, {"type": "move", "move_index": 1}, {"type": "pass"})

    assert p1.stat_stages["atk"] == 0
    assert p1.stat_stages["def"] == 0
    assert p1.stat_stages["spe"] == 0
    assert p2.stat_stages["atk"] == 0


def test_gen1_metronome_mimic_and_mirror_move(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_choice(monkeypatch, lambda seq: seq[0])
    patch_engine_randint(monkeypatch, 1)

    metronome = make_move(118, "Metronome", "normal", None, None, 10, "status")
    mimic = make_move(102, "Mimic", "normal", None, None, 10, "status")
    mirror_move = make_move(119, "Mirror Move", "flying", None, None, 20, "status")
    pound = make_move(1, "Pound", "normal", 40, 100, 35, "physical")

    p1 = make_pokemon(speed=200, moves=[metronome, mimic, mirror_move])
    p2 = make_pokemon(speed=50, moves=[pound])
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p2.current_hp < 100
    assert any("Metronome" in log or "[into]" in log for log in engine.logs)

    run_turn(engine, {"type": "move", "move_index": 1}, {"type": "pass"})
    assert p1.moves[0].move_id == 1
    assert p1.moves[0].name.lower() == "pound"

    run_turn(engine, {"type": "move", "move_index": 2}, {"type": "pass"})
    assert p2.current_hp < 100


def test_gen1_transform_copies_target_state(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)

    transform = make_move(144, "Transform", "normal", None, None, 10, "status")
    surf = make_move(57, "Surf", "water", 90, 100, 15, "special")
    bite = make_move(44, "Bite", "dark", 60, 100, 25, "physical")

    p1 = make_pokemon(speed=200, moves=[transform])
    p2 = make_pokemon(speed=50, moves=[surf, bite], types=("water", "flying"), atk=120, defense=110)
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p1.is_transformed is True
    assert p1.types == p2.types
    assert [m.name for m in p1.moves] == [m.name for m in p2.moves]


def test_gen1_conversion_changes_type(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_choice(monkeypatch, lambda seq: "water")

    conversion = make_move(160, "Conversion", "normal", None, None, 30, "status")
    pound = make_move(1, "Pound", "normal", 40, 100, 35, "physical")
    surf = make_move(57, "Surf", "water", 90, 100, 15, "special")

    p1 = make_pokemon(speed=200, moves=[conversion, pound], types=("normal",))
    p2 = make_pokemon(speed=50, moves=[surf], types=("fire",))
    engine = make_engine(p1, p2)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p1.types == ["water"]


def test_gen1_fixed_damage_and_low_kick() -> None:
    attacker = make_pokemon(level=50, hp=200, current_hp=200)
    defender = make_pokemon(level=50, hp=200, current_hp=200)

    seismic_toss = make_move(69, "Seismic Toss", "fighting", None, 100, 20, "physical")
    dragon_rage = make_move(82, "Dragon Rage", "dragon", None, 100, 10, "special")
    sonic_boom = make_move(49, "Sonic Boom", "normal", None, 90, 20, "special")
    super_fang = make_move(162, "Super Fang", "normal", None, 90, 10, "physical")
    low_kick = make_move(67, "Low Kick", "fighting", None, 100, 20, "physical")

    assert calculate_damage_gen1(attacker, defender, seismic_toss)[0] == 50
    assert calculate_damage_gen1(attacker, defender, dragon_rage)[0] == 40
    assert calculate_damage_gen1(attacker, defender, sonic_boom)[0] == 20

    defender.current_hp = 200
    assert calculate_damage_gen1(attacker, defender, super_fang)[0] == 100

    light_target = make_pokemon(hp=200, current_hp=200, weight=5.0)
    heavy_target = make_pokemon(hp=200, current_hp=200, weight=250.0)
    light_damage = calculate_damage_gen1(attacker, light_target, low_kick, random_factor=255)[0]
    heavy_damage = calculate_damage_gen1(attacker, heavy_target, low_kick, random_factor=255)[0]
    assert heavy_damage > light_damage


def test_gen1_ohko_moves_follow_level_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_hit_roll(monkeypatch, 0)
    patch_damage_roll(monkeypatch, 255)
    patch_crit_roll(monkeypatch, 0.99)
    patch_engine_randint(monkeypatch, 1)

    horn_drill = make_move(32, "Horn Drill", "normal", None, 30, 5, "physical")
    attacker = make_pokemon(level=60, base_speed=60, moves=[horn_drill], hp=200, current_hp=200)
    defender = make_pokemon(level=50, hp=200, current_hp=200)
    engine = make_engine(attacker, defender)

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert defender.current_hp == 0

    low_level_attacker = make_pokemon(level=40, base_speed=40, moves=[horn_drill], hp=200, current_hp=200)
    defender2 = make_pokemon(level=50, hp=200, current_hp=200)
    engine2 = make_engine(low_level_attacker, defender2)

    run_turn(engine2, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert defender2.current_hp == 200
