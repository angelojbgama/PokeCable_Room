from __future__ import annotations

import pytest

from app.data.move_combat_data import get_move_combat_data
from app.engines.gen2 import damage as gen2_damage_mod
from app.engines.gen2 import engine as gen2_engine_mod
from app.engines.gen2.engine import BattleEngineGen2, BattleSideGen2
from app.engines.gen2.models import BattleMoveGen2, BattleStatsGen2, PokemonGen2


def make_move(move_id: int, pp: int | None = None) -> BattleMoveGen2:
    data = get_move_combat_data(move_id)
    return BattleMoveGen2(
        move_id=move_id,
        name=data["name"],
        type=data["type"],
        power=int(data["power"]) if data.get("power") is not None else 0,
        accuracy=int(data["accuracy"]) if data.get("accuracy") is not None else 100,
        pp=int(pp if pp is not None else data["pp"]),
        max_pp=int(data["pp"]),
        priority=int(data.get("priority") or 0),
        damage_class=str(data["damage_class"]),
        effect=str(data.get("effect") or ""),
        high_crit="critical hit" in str(data.get("effect") or "").lower(),
        effect_chance=data.get("effect_chance"),
    )


def create_mock_pokemon_gen2(
    *,
    name: str = "Mew",
    level: int = 50,
    hp: int = 300,
    types: list[str] | None = None,
    moves: list[BattleMoveGen2] | None = None,
    atk: int = 120,
    defen: int = 100,
    spa: int = 120,
    spd: int = 100,
    spe: int = 100,
) -> PokemonGen2:
    stats = BattleStatsGen2(hp=hp, atk=atk, defen=defen, spa=spa, spd=spd, spe=spe)
    if moves is None:
        moves = [make_move(33)]

    return PokemonGen2(
        national_id=151,
        name=name,
        nickname=name,
        level=level,
        types=list(types or ["normal"]),
        max_hp=hp,
        current_hp=hp,
        stats=stats,
        base_speed=spe,
        dvs={"atk": 15, "def": 15, "spe": 15, "spc": 15, "hp": 15},
        moves=moves,
        source_generation=2,
    )


def make_engine(side1: PokemonGen2, side2: PokemonGen2) -> BattleEngineGen2:
    return BattleEngineGen2(
        "gen2-test",
        BattleSideGen2("p1", "Red", [side1]),
        BattleSideGen2("p2", "Blue", [side2]),
    )


def patch_deterministic_battle(monkeypatch: pytest.MonkeyPatch, *, random_value: float = 0.99) -> None:
    monkeypatch.setattr(gen2_engine_mod, "calculate_hit_gen2", lambda *args, **kwargs: True)
    monkeypatch.setattr(gen2_engine_mod, "determine_critical_gen2", lambda *args, **kwargs: False)
    monkeypatch.setattr(gen2_engine_mod.random, "random", lambda: random_value)
    monkeypatch.setattr(gen2_engine_mod.random, "randint", lambda a, b: b)
    monkeypatch.setattr(gen2_damage_mod.random, "randint", lambda a, b: b)


def run_turn(engine: BattleEngineGen2, p1_action: dict[str, int | str], p2_action: dict[str, int | str]) -> None:
    engine.submit_action("p1", p1_action)  # type: ignore[arg-type]
    engine.submit_action("p2", p2_action)  # type: ignore[arg-type]


def test_gen2_pp_consumption_and_struggle_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(moves=[make_move(33, pp=1)], hp=500)
    p2 = create_mock_pokemon_gen2(name="Blue", moves=[make_move(33)], hp=500)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p1.moves[0].pp == 0

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert any("Struggle" in log for log in engine.logs)


def test_gen2_thunder_wave_paralyzes_target(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(moves=[make_move(86)], hp=250)
    p2 = create_mock_pokemon_gen2(name="Snorlax", types=["normal"], moves=[make_move(33)], hp=250, spe=120)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.status_condition == "par"
    assert p2.get_modified_stat("spe") == 30


def test_gen2_poison_powder_fails_on_grass_types(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(moves=[make_move(77)], hp=250)
    p2 = create_mock_pokemon_gen2(name="Venusaur", types=["grass"], moves=[make_move(33)], hp=250)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.status_condition is None
    assert any("|-fail|" in log for log in engine.logs)


def test_gen2_rest_heals_and_puts_user_to_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(moves=[make_move(156)], hp=250)
    p1.current_hp = 91
    p1.status_condition = "brn"
    p2 = create_mock_pokemon_gen2(name="Blue", moves=[make_move(33)], hp=250)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p1.current_hp == p1.max_hp
    assert p1.status_condition == "slp"


def test_gen2_confusion_causes_self_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch, random_value=0.0)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(33)], hp=250)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(33)], hp=250)
    engine = make_engine(p1, p2)
    engine.start_battle()
    p2.is_confused = True
    p2.confusion_turns = 2

    run_turn(engine, {"type": "pass"}, {"type": "move", "move_index": 0})

    assert p2.current_hp < p2.max_hp
    assert any("from] confusion" in log for log in engine.logs)


def test_gen2_hyper_beam_requires_recharge_after_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(moves=[make_move(63)], hp=350)
    p2 = create_mock_pokemon_gen2(name="Blue", moves=[make_move(33)], hp=350)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p1.must_recharge is True

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p1.must_recharge is False
    assert any("recharge" in log for log in engine.logs)


def test_gen2_disable_forces_struggle_when_no_other_moves(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(33)], hp=250, spe=120)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(50)], hp=250, spe=80)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p1.last_move_name == "Struggle"
    assert any("Struggle" in log for log in engine.logs)


def test_gen2_encore_forces_last_move_repeat(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(
        name="Alpha",
        moves=[make_move(33), make_move(45)],
        hp=250,
        spe=120,
    )
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(227)], hp=250, spe=80)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    run_turn(engine, {"type": "move", "move_index": 1}, {"type": "pass"})

    assert p1.moves[0].pp == 33
    assert p1.moves[1].pp == 40
    assert any("|move|p1a: alpha|tackle|" in log.lower() for log in engine.logs)


def test_gen2_fly_makes_user_semi_invulnerable_then_attacks(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(19)], hp=250, spe=120)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(33)], hp=250, spe=80)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    assert p1.current_hp == p1.max_hp
    assert p1.semi_invulnerable == "fly"

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    assert p1.semi_invulnerable is None
    assert p2.current_hp < p2.max_hp


def test_gen2_leech_seed_drains_and_heals_source(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(73)], hp=250, spe=120)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(33)], hp=250, spe=80)
    p1.current_hp = 100
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert p2.current_hp < p2.max_hp
    assert p1.current_hp > 100


def test_gen2_bide_accumulates_and_releases_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(117)], hp=250, spe=120)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(33)], hp=250, spe=80)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})
    first_damage = p2.max_hp - p2.current_hp

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p2.current_hp == p2.max_hp

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    assert p2.max_hp - p2.current_hp > first_damage
    assert p1.bide_turns is None


def test_gen2_counter_reflects_physical_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(68)], hp=250, spe=120)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(33)], hp=250, spe=80)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})

    assert p2.current_hp < p2.max_hp
    assert any("counter" in log.lower() for log in engine.logs)


def test_gen2_mirror_coat_reflects_special_damage(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(243)], hp=250, spe=120)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(52)], hp=250, spe=80)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "move", "move_index": 0})

    assert p2.current_hp < p2.max_hp
    assert any("mirror" in log.lower() and "coat" in log.lower() for log in engine.logs)


def test_gen2_rollout_scales_power_across_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(205)], hp=400, spe=120)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(33)], hp=400, spe=80)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    damage_turn_one = p2.max_hp - p2.current_hp

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})
    damage_turn_two = p2.max_hp - p2.current_hp - damage_turn_one

    assert damage_turn_two > damage_turn_one


def test_gen2_sunny_day_sets_weather(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_deterministic_battle(monkeypatch)

    p1 = create_mock_pokemon_gen2(name="Alpha", moves=[make_move(241)], hp=250, spe=120)
    p2 = create_mock_pokemon_gen2(name="Beta", moves=[make_move(33)], hp=250, spe=80)
    engine = make_engine(p1, p2)
    engine.start_battle()

    run_turn(engine, {"type": "move", "move_index": 0}, {"type": "pass"})

    assert engine.weather == "sun"
