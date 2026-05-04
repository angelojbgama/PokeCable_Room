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

def test_abilities():
    print("Testing Abilities (Guts, Swift Swim, etc.)...")
    
    # Guts
    guts_pkmn = create_mock_pokemon("Rattata", "guts", status="brn")
    normal_pkmn = create_mock_pokemon("Pidgey", "keen-eye", status="brn")
    
    # Guts should have higher attack than normal when burned
    # Normal: 100 * 0.5 = 50
    # Guts: 100 * 1.5 = 150 (ignores burn penalty)
    atk_guts = guts_pkmn.get_modified_stat("atk")
    atk_normal = normal_pkmn.get_modified_stat("atk")
    
    print(f"Guts Atk (Burned): {atk_guts} (Expected: 150)")
    print(f"Normal Atk (Burned): {atk_normal} (Expected: 50)")
    assert atk_guts == 150
    assert atk_normal == 50
    
    # Swift Swim
    swift_pkmn = create_mock_pokemon("Lotad", "swift-swim")
    spe_rain = swift_pkmn.get_modified_stat("spe", weather="rain")
    spe_none = swift_pkmn.get_modified_stat("spe", weather="none")
    
    print(f"Swift Swim Spe (Rain): {spe_rain} (Expected: 200)")
    print(f"Swift Swim Spe (None): {spe_none} (Expected: 100)")
    assert spe_rain == 200
    assert spe_none == 100

def test_facade():
    print("\nTesting Facade...")
    attacker = create_mock_pokemon("Ursaring", "guts", status="brn")
    defender = create_mock_pokemon("Dummy", "none")
    move = attacker.moves[2] # Facade
    
    # Facade ignores burn penalty and doubles power
    # Power = 70 * 2 = 140
    # Atk = 100 * 1.5 (Guts) = 150
    dmg, _ = calculate_damage(attacker, defender, move, weather="none")
    print(f"Facade Damage (Burned+Guts): {dmg}")
    # Tackle for comparison
    tackle = attacker.moves[0]
    dmg_tackle, _ = calculate_damage(attacker, defender, tackle, weather="none")
    print(f"Tackle Damage (Burned+Guts): {dmg_tackle}")
    
    assert dmg > dmg_tackle * 2 # Roughly

def test_disruptions():
    print("\nTesting Disruptions (Taunt, Disable, Encore)...")
    p1 = BattleSide("p1", "Player 1", [create_mock_pokemon("P1", "none")])
    p2 = BattleSide("p2", "Player 2", [create_mock_pokemon("P2", "none")])
    engine = CustomBattleEngine("test", p1, p2)
    
    # Taunt
    p1.active.taunt_turns = 2
    req = engine.generate_request("p1")
    moves = req["active"][0]["moves"]
    print("Taunted Moves Status:")
    for m in moves:
        print(f" - {m['move']}: {'Disabled' if m['disabled'] else 'Enabled'}")
        if m['move'] == "Growl" or m['move'] == "Taunt":
            assert m['disabled'] == True
        else:
            assert m['disabled'] == False

    # Disable
    p1.active.taunt_turns = 0
    p1.active.disable_move_id = 1 # Tackle
    p1.active.disable_turns = 2
    req = engine.generate_request("p1")
    moves = req["active"][0]["moves"]
    print("Disabled Moves Status (Tackle):")
    for m in moves:
        print(f" - {m['move']}: {'Disabled' if m['disabled'] else 'Enabled'}")
        if m['move'] == "Tackle":
            assert m['disabled'] == True

    # Encore
    p1.active.disable_turns = 0
    p1.active.encore_move_index = 0 # Tackle
    p1.active.encore_turns = 2
    req = engine.generate_request("p1")
    moves = req["active"][0]["moves"]
    print("Encored Moves Status (Tackle):")
    assert len(moves) == 1
    assert moves[0]['move'] == "Tackle"

if __name__ == "__main__":
    try:
        test_abilities()
        test_facade()
        test_disruptions()
        print("\nAll Phase 1 tests passed!")
    except AssertionError as e:
        print(f"\nTest failed!")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
