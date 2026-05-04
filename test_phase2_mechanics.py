import sys
import os
import math

# Adiciona o diretório atual ao sys.path para importar os módulos do app
sys.path.append(os.path.join(os.getcwd(), "PokeCable", "api"))

from app.battle_pokemon import BattlePokemon, BattleMove, BattleStats
from app.battle_engine_core import CustomBattleEngine, BattleSide
from app.battle_damage import calculate_damage

def create_mock_pokemon(name, ability, hp=100, atk=100, defen=100, spa=100, spd=100, spe=100, status=None):
    stats = BattleStats(hp=hp, atk=atk, defen=defen, spa=spa, spd=spd, spe=spe)
    pkmn = BattlePokemon(
        national_id=1,
        name=name,
        nickname=name,
        level=50,
        types=["normal"],
        base_stats={"hp": 50, "atk": 50, "def": 50, "spa": 50, "spd": 50, "spe": 50},
        ivs={"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31},
        evs={"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0},
        nature_id=0,
        ability=ability,
        max_hp=hp,
        current_hp=hp,
        stats=stats,
        status_condition=status
    )
    # Adiciona alguns moves
    pkmn.moves = [
        BattleMove(1, "Tackle", "normal", 40, 100, 35, 35, 0, "physical"),
        BattleMove(45, "Growl", "normal", 0, 100, 40, 40, 0, "status"),
        BattleMove(263, "Facade", "normal", 70, 100, 20, 20, 0, "physical"),
        BattleMove(269, "Taunt", "dark", 0, 100, 20, 20, 0, "status")
    ]
    return pkmn

def test_singles_compatibility():
    print("Testing Singles Compatibility...")
    p1 = BattleSide("p1", "Player 1", [create_mock_pokemon("P1", "none")], active_indices=[0])
    p2 = BattleSide("p2", "Player 2", [create_mock_pokemon("P2", "none")], active_indices=[0])
    engine = CustomBattleEngine("singles", p1, p2, battle_format="singles")
    engine.start_battle()
    
    # Simula um turno
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    
    print(f"Turn 1 Logs: {len(engine.logs)}")
    assert any("p1a: P1" in log for log in engine.logs)
    assert any("p2a: P2" in log for log in engine.logs)
    print("Singles Compatibility OK!")

def test_doubles_targeting():
    print("\nTesting Doubles Targeting and Spread...")
    p1 = BattleSide("p1", "Player 1", [create_mock_pokemon("P1A", "none"), create_mock_pokemon("P1B", "none")], active_indices=[0, 1])
    p2 = BattleSide("p2", "Player 2", [create_mock_pokemon("P2A", "none"), create_mock_pokemon("P2B", "none")], active_indices=[0, 1])
    engine = CustomBattleEngine("doubles", p1, p2, battle_format="doubles")
    engine.start_battle()
    
    # P1A ataca P2B
    engine.submit_action("p1", {"type": "move", "move_index": 0, "target": "p2b", "slot": 0})
    # P1B ataca P2A
    engine.submit_action("p1", {"type": "move", "move_index": 0, "target": "p2a", "slot": 1})
    # P2A e P2B atacam P1A
    engine.submit_action("p2", {"type": "move", "move_index": 0, "target": "p1a", "slot": 0})
    engine.submit_action("p2", {"type": "move", "move_index": 0, "target": "p1a", "slot": 1})
    
    print(f"Doubles Turn Logs: {len(engine.logs)}")
    # Verifica se os logs contêm p1a, p1b, p2a, p2b
    assert any("p1a: P1A" in log for log in engine.logs)
    assert any("p1b: P1B" in log for log in engine.logs)
    assert any("p2a: P2A" in log for log in engine.logs)
    assert any("p2b: P2B" in log for log in engine.logs)
    
    # Verifica HP de P1A (recebeu 2 ataques)
    print(f"P1A HP: {p1.team[0].current_hp}/100")
    assert p1.team[0].current_hp < 100
    
    print("Doubles Targeting OK!")

if __name__ == "__main__":
    try:
        test_singles_compatibility()
        test_doubles_targeting()
        print("\nAll Phase 2 tests passed!")
    except AssertionError as e:
        print(f"\nTest failed!")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
