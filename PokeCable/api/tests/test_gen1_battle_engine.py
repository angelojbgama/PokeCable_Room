import pytest
import math
from app.engines.gen1.engine import BattleEngineGen1, BattleSideGen1
from app.engines.gen1.models import PokemonGen1, BattleMoveGen1, BattleStatsGen1

def create_mock_pokemon_gen1(name="Mew", level=50, hp=100):
    stats = BattleStatsGen1(hp=hp, atk=100, defen=100, spe=100, special=100)
    moves = [
        BattleMoveGen1(1, "Pound", "normal", 40, 100, 35, 35, 0, "physical"),
        BattleMoveGen1(14, "Slash", "normal", 70, 100, 20, 20, 0, "physical", high_crit=True),
        BattleMoveGen1(63, "Hyper Beam", "normal", 150, 90, 5, 5, 0, "physical")
    ]
    return PokemonGen1(
        national_id=151,
        name=name,
        nickname=name,
        level=level,
        types=["psychic"],
        max_hp=hp,
        current_hp=hp,
        stats=stats,
        base_speed=100,
        dvs={"atk": 15, "def": 15, "spe": 15, "spc": 15, "hp": 15},
        moves=moves
    )

def setup_engine_gen1(p1, p2):
    side1 = BattleSideGen1("p1", "Player 1", [p1])
    side2 = BattleSideGen1("p2", "Player 2", [p2])
    engine = BattleEngineGen1("test-gen1", side1, side2)
    engine.start_battle()
    return engine

def test_gen1_basic_damage():
    p1 = create_mock_pokemon_gen1()
    p2 = create_mock_pokemon_gen1()
    engine = setup_engine_gen1(p1, p2)
    
    # Mew usa Pound (Normal) contra Mew
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})
    
    # Mew e psiquico, Pound e Normal (neutro)
    # Dano esperado: level 50, power 40, atk 100, def 100
    # Base = floor(floor(floor(2*50/5 + 2) * 40 * 100 / 100) / 50) + 2
    # Base = floor(floor(22 * 40) / 50) + 2 = floor(880 / 50) + 2 = 17 + 2 = 19
    # STAB: No (Normal != Psychic)
    # Type: 1.0
    # Random: 217-255 -> 19 * 217 / 255 = 16, 19 * 255 / 255 = 19
    assert 16 <= (100 - p2.current_hp) <= 19

def test_gen1_critical_hit():
    p1 = create_mock_pokemon_gen1()
    p1.base_speed = 255 # Chance altissima de critico
    p2 = create_mock_pokemon_gen1()
    engine = setup_engine_gen1(p1, p2)
    
    # Slash tem high_crit
    # Chance = 255 * 8 / 512 = 3.98 -> 99.6%
    engine.submit_action("p1", {"type": "move", "move_index": 1})
    engine.submit_action("p2", {"type": "pass"})
    
    # Dano Critico na Gen 1: Level dobrado na formula
    # Level = 100
    # Base = floor(floor(floor(2*100/5 + 2) * 70 * 100 / 100) / 50) + 2
    # Base = floor(floor(42 * 70) / 50) + 2 = floor(2940 / 50) + 2 = 58 + 2 = 60
    # Random: 60 * 217 / 255 = 51, 60 * 255 / 255 = 60
    assert 51 <= (100 - p2.current_hp) <= 60
    assert any("|-crit|" in log for log in engine.logs)

def test_gen1_type_effectiveness():
    p1 = create_mock_pokemon_gen1()
    p1.types = ["ghost"]
    # Na Gen 1, Ghost nao afeta Psychic (Bug original)
    lick = BattleMoveGen1(122, "Lick", "ghost", 20, 100, 30, 30, 0, "physical")
    p1.moves = [lick]
    
    p2 = create_mock_pokemon_gen1() # Psychic
    engine = setup_engine_gen1(p1, p2)
    
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})
    
    assert p2.current_hp == 100
    assert any("|-immune|" in log for log in engine.logs)

def test_gen1_sleep_lose_turn_on_wake():
    p1 = create_mock_pokemon_gen1()
    p1.status_condition = "slp"
    p1.status_turns = 1 # Vai acordar no proximo turno
    
    p2 = create_mock_pokemon_gen1()
    engine = setup_engine_gen1(p1, p2)
    
    # Turno 1: Mew (p1) tenta atacar mas acorda e perde o turno
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})
    
    assert p1.status_condition is None
    assert any("|-curestatus|p1a: Mew|slp" in log for log in engine.logs)
    # p2 nao deve ter levado dano porque p1 perdeu o turno ao acordar
    assert p2.current_hp == 100

def test_gen1_hyper_beam_kill_no_recharge():
    p1 = create_mock_pokemon_gen1()
    p1.stats.atk = 200 # Garante o nocaute
    p2 = create_mock_pokemon_gen1(hp=10) # Morre com um golpe
    engine = setup_engine_gen1(p1, p2)
    
    # Mew p1 usa Hyper Beam e mata p2
    engine.submit_action("p1", {"type": "move", "move_index": 2}) # Hyper Beam
    engine.submit_action("p2", {"type": "pass"})
    
    assert p2.current_hp == 0
    assert any("|faint|p2a: Mew" in log for log in engine.logs)
    
    # Na Gen 1, se matou, must_recharge deve ser False (Glitch fiel)
    assert p1.must_recharge is False

def test_gen1_toxic_accumulation():
    p1 = create_mock_pokemon_gen1(hp=160)
    p1.status_condition = "tox"
    p1.toxic_n = 1
    
    p2 = create_mock_pokemon_gen1()
    engine = setup_engine_gen1(p1, p2)
    
    # Turno 1: Dano = floor(160/16) * 1 = 10
    engine.submit_action("p1", {"type": "pass"})
    engine.submit_action("p2", {"type": "pass"})
    assert p1.current_hp == 160 - 10
    assert p1.toxic_n == 2
    
    # Turno 2: Dano = floor(160/16) * 2 = 20
    engine.submit_action("p1", {"type": "pass"})
    engine.submit_action("p2", {"type": "pass"})
    assert p1.current_hp == 150 - 20
    assert p1.toxic_n == 3

def test_gen1_sleep_lose_turn_on_wake():
    p1 = create_mock_pokemon_gen1()
    p1.status_condition = "slp"
    p1.status_turns = 1 # Vai acordar no proximo turno
    
    p2 = create_mock_pokemon_gen1()
    engine = setup_engine_gen1(p1, p2)
    
    # Turno 1: Mew (p1) tenta atacar mas acorda e perde o turno
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "pass"})
    
    assert p1.status_condition is None
    assert any("|-curestatus|p1a: Mew|slp" in log for log in engine.logs)
    # p2 nao deve ter levado dano porque p1 perdeu o turno ao acordar
    assert p2.current_hp == 100
