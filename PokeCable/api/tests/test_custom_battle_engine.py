import pytest
import math
from app.battle_engine_core import CustomBattleEngine, BattleSide, STRUGGLE
from app.battle_pokemon import BattlePokemon, BattleMove, BattleStats

def create_mock_pokemon(name="Mew", level=50, moves=None, ability=None, hp=100):
    stats = BattleStats(hp=hp, atk=100, defen=100, spa=100, spd=100, spe=100)
    if not moves:
        moves = [BattleMove(1, "Pound", "normal", 40, 100, 35, 35, 0, "physical", "")]
    return BattlePokemon(
        species_id=151,
        name=name,
        nickname=name,
        level=level,
        types=["psychic"],
        base_stats={"hp": 100, "atk": 100, "def": 100, "spa": 100, "spd": 100, "spe": 100},
        ivs={"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
        evs={"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
        nature_id=0,
        ability=ability,
        max_hp=hp,
        current_hp=hp,
        stats=stats,
        moves=moves
    )

def setup_engine(p1_pkmn, p2_pkmn):
    side1 = BattleSide("p1", "Player 1", [p1_pkmn])
    side2 = BattleSide("p2", "Player 2", [p2_pkmn])
    engine = CustomBattleEngine("test-battle", side1, side2)
    engine.start_battle()
    return engine

def test_struggle_recoil():
    p1 = create_mock_pokemon(hp=100)
    p2 = create_mock_pokemon(hp=100)
    engine = setup_engine(p1, p2)
    
    # Simula ação de struggle (move_index = -1)
    engine.submit_action("p1", {"type": "move", "move_index": -1})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    
    # Struggle na Gen 3 tira 1/4 do HP maximo em recoil
    assert p1.current_hp == 100 - 25

def test_ohko_moves():
    # Horn Drill (Normal) contra Mew
    horn_drill = BattleMove(12, "Horn Drill", "normal", 1, 30, 5, 5, 0, "physical", "OHKO")
    p1 = create_mock_pokemon(level=100, moves=[horn_drill])
    p2 = create_mock_pokemon(level=50, hp=200) # Level menor para garantir acerto se RNG ajudar
    engine = setup_engine(p1, p2)
    
    # Forçamos o hit na engine ou no calculate_hit? 
    # Aqui vamos testar a lógica do calculo de dano
    from app.battle_damage import calculate_damage
    dmg, mult = calculate_damage(p1, p2, horn_drill)
    
    assert dmg == p2.current_hp
    
    # Testar falha por level menor
    p1.level = 40
    from app.battle_utils import calculate_hit
    hit = calculate_hit(30, 0, 0, user_level=p1.level, target_level=p2.level, is_ohko=True)
    assert hit is False

def test_substitute_absorption():
    p1 = create_mock_pokemon(hp=400)
    p2 = create_mock_pokemon(hp=400)
    engine = setup_engine(p1, p2)
    
    p1.substitute_hp = 100
    
    # Ataca Mew com Substitute
    pound = BattleMove(1, "Pound", "normal", 40, 100, 35, 35, 0, "physical", "")
    engine._execute_action("p2", {"type": "move", "move_index": 0})
    
    # HP real de p1 nao deve mudar, substitute_hp deve diminuir
    assert p1.current_hp == 400
    assert p1.substitute_hp < 100

def test_synchronize_ability():
    # Mew com Synchronize
    p1 = create_mock_pokemon(ability="synchronize", hp=100)
    # Oponente usa Thunder Wave
    t_wave = BattleMove(86, "Thunder Wave", "electric", 0, 100, 20, 20, 0, "status", "Paralyzes")
    p2 = create_mock_pokemon(moves=[t_wave])
    engine = setup_engine(p1, p2)
    
    engine._execute_action("p2", {"type": "move", "move_index": 0})
    
    assert p1.status_condition == "par"
    # Synchronize deve ter passado para p2
    assert p2.status_condition == "par"

def test_weather_auto_activation():
    # Kyogre entra com Drizzle
    p1 = create_mock_pokemon(ability="drizzle")
    p2 = create_mock_pokemon()
    
    engine = setup_engine(p1, p2)
    # _switch_in e chamado no start_battle
    assert engine.weather == "rain"
    assert engine.weather_turns > 100 # Permanente

def test_spikes_damage():
    p1 = create_mock_pokemon()
    p2_active = create_mock_pokemon(hp=100)
    p2_bench = create_mock_pokemon(hp=100)
    
    side1 = BattleSide("p1", "P1", [p1])
    side2 = BattleSide("p2", "P2", [p2_active, p2_bench])
    engine = CustomBattleEngine("test", side1, side2)
    
    engine.sides["p2"].spikes_layers = 1
    engine._switch_in("p2", 1) # Troca para o reserva
    
    # 1 layer = 1/8 de 100 = 12
    assert p2_bench.current_hp == 100 - 12
