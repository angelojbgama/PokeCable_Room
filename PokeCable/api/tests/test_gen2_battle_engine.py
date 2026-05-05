import asyncio

from app.battle_engine import LocalBattleEngineAdapter
from app.engines.gen2.damage import calculate_damage_gen2
from app.engines.gen2.models import BattleMoveGen2, BattleStatsGen2, PokemonGen2


def create_mock_pokemon_gen2(name="Mew", level=50, hp=100, types=None):
    stats = BattleStatsGen2(hp=hp, atk=20, defen=100, spa=180, spd=100, spe=100)
    moves = [
        BattleMoveGen2(1, "Pound", "normal", 40, 100, 35, 35, 0, "physical"),
        BattleMoveGen2(52, "Ember", "fire", 40, 100, 25, 25, 0, "special"),
    ]
    return PokemonGen2(
        national_id=151,
        name=name,
        nickname=name,
        level=level,
        types=list(types or ["fire"]),
        max_hp=hp,
        current_hp=hp,
        stats=stats,
        base_speed=100,
        dvs={"atk": 15, "def": 15, "spe": 15, "spc": 15, "hp": 15},
        moves=moves,
        source_generation=2,
    )


def test_gen2_special_split_uses_special_attack():
    attacker = create_mock_pokemon_gen2()
    defender = create_mock_pokemon_gen2(types=["normal"])

    pound = attacker.moves[0]
    ember = attacker.moves[1]

    physical_damage, _ = calculate_damage_gen2(attacker, defender, pound, random_factor=255)
    special_damage, _ = calculate_damage_gen2(attacker, defender, ember, random_factor=255)

    assert special_damage > physical_damage


def test_gen2_router_supports_gen2_battles():
    adapter = LocalBattleEngineAdapter()
    team_a = [
        {
            "source_generation": 2,
            "species_national_id": 151,
            "species_name": "Mew",
            "nickname": "Mew",
            "level": 50,
            "trainer_id": 123,
            "ivs": {"attack": 15, "defense": 15, "speed": 15, "special": 15},
            "evs": {"attack": 65535, "defense": 65535, "speed": 65535, "special": 65535},
            "moves": [{"move_id": 52, "pp": 25}],
        }
    ]
    team_b = [
        {
            "source_generation": 2,
            "species_national_id": 151,
            "species_name": "Mew",
            "nickname": "Mew",
            "level": 50,
            "trainer_id": 456,
            "ivs": {"attack": 15, "defense": 15, "speed": 15, "special": 15},
            "evs": {"attack": 65535, "defense": 65535, "speed": 65535, "special": 65535},
            "moves": [{"move_id": 1, "pp": 35}],
        }
    ]

    result = asyncio.run(
        adapter.create_battle(
            "gen2customgame",
            team_a,
            team_b,
            player_a_id="a",
            player_b_id="b",
        )
    )

    assert result.battle_id.startswith("battle-")
    assert "|start|" in result.logs
    assert set(result.requests.keys()) == {"a", "b"}
