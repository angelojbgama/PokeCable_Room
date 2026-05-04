import asyncio
import os
import random
import sys
import logging
import math
from pathlib import Path

# Configura o logger
logging.basicConfig(level=logging.ERROR)

# Adiciona o diretório PokeCable e root ao sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "PokeCable"))
sys.path.insert(0, str(ROOT_DIR / "PokeCable" / "api"))
sys.path.insert(0, str(ROOT_DIR / "PokeCable" / "backend"))

from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen3 import Gen3Parser
from app.battle_engine_core import CustomBattleEngine, BattleSide, STRUGGLE
from app.battle_pokemon import BattlePokemon, BattleMove

def load_party(save_path: str, parser_class) -> list[BattlePokemon]:
    parser = parser_class()
    p = Path(save_path)
    if not p.exists():
        print(f"ERRO: Save nao encontrado em {save_path}")
        return []
    try:
        parser.load(save_path)
    except Exception as e:
        print(f"ERRO ao carregar save: {e}")
        return []

    party = []
    for i in range(6):
        try:
            canonical = parser.export_canonical(f"party:{i}")
            if canonical and canonical.species_national_id > 0:
                canonical_dict = {
                    "species_national_id": canonical.species_national_id,
                    "species_name": canonical.species_name,
                    "nickname": canonical.nickname,
                    "level": canonical.level,
                    "source_generation": 1 if "gen 1" in str(save_path).lower() else (2 if "gen 2" in str(save_path).lower() else 3),
                    "personality": canonical.metadata.get("personality", 0) if canonical.metadata else 0,
                    "ability": canonical.ability,
                    "ivs": {k: getattr(canonical.ivs, k) for k in ["hp", "attack", "defense", "special_attack", "special_defense", "speed"]} if canonical.ivs else {},
                    "evs": {k: getattr(canonical.evs, k) for k in ["hp", "attack", "defense", "special_attack", "special_defense", "speed"]} if canonical.evs else {},
                    "moves": [{"move_id": m.move_id} for m in canonical.moves if m.move_id],
                    "held_item": {"item_id": canonical.held_item.item_id} if canonical.held_item else None
                }
                party.append(BattlePokemon.from_canonical(canonical_dict))
        except:
            pass
    return party

def choose_random_action(engine: CustomBattleEngine, side_id: str) -> dict:
    side = engine.sides[side_id]
    force_slots = [slot for (s_id, slot) in engine.force_switch_slots if s_id == side_id]
    if force_slots:
        slot = force_slots[0]
        valid_switches = [i for i, p in enumerate(side.team) if p.current_hp > 0 and i not in side.active_indices]
        return {"type": "switch", "index": random.choice(valid_switches), "slot": slot} if valid_switches else {"type": "pass", "slot": slot}
        
    # No 1v1, slot eh sempre 0
    slot = 0
    pkmn_idx = side.active_indices[slot]
    pkmn = side.team[pkmn_idx]
    if not pkmn or pkmn.current_hp <= 0: return {"type": "pass", "slot": slot}
        
    valid_moves = [i for i, m in enumerate(pkmn.moves) if m.pp > 0]
    if valid_moves:
        return {"type": "move", "move_index": random.choice(valid_moves), "slot": slot}
    else:
        return {"type": "move", "move_index": -1, "slot": slot}

def run_battle(engine: CustomBattleEngine, title: str, turn_limit: int = 50):
    print(f"\n--- {title} ---")
    engine.start_battle()
    for log in engine.logs: print(log)
    engine.logs.clear()

    while not engine.finished and engine.turn < turn_limit:
        if engine.force_switch_slots:
            for side_id, slot in list(engine.force_switch_slots):
                action = choose_random_action(engine, side_id)
                engine.submit_action(engine.sides[side_id].player_id, action)
        else:
            engine.submit_action(engine.sides["p1"].player_id, choose_random_action(engine, "p1"))
            engine.submit_action(engine.sides["p2"].player_id, choose_random_action(engine, "p2"))
        for log in engine.logs: print(log)
        engine.logs.clear()

def create_mock_pokemon(name: str, moves: list[int], ability: str = None, item_id: int = None) -> BattlePokemon:
    # Cria um Pokemon genérico para testes
    pkmn_dict = {
        "species_national_id": 1, "species_name": name, "nickname": name, "level": 100,
        "ability": ability, "moves": [{"move_id": m} for m in moves],
        "held_item": {"item_id": item_id} if item_id else None
    }
    return BattlePokemon.from_canonical(pkmn_dict)

def main():
    # 1. TESTE COM SAVES REAIS
    print("Iniciando Teste com Saves Reais...")
    team1 = load_party("save/gen 1/Pokémon - Yellow Version.sav", Gen1Parser)
    team2 = load_party("save/gen 3/Pokémon - LeafGreen Version.sav", Gen3Parser)
    
    if team1 and team2:
        engine = CustomBattleEngine("real_saves", 
            BattleSide("ash", "Ash", team1), 
            BattleSide("leaf", "Leaf", team2))
        run_battle(engine, "BATALHA REAL: ASH vs LEAF", turn_limit=100)

    # 2. TESTES DE MECÂNICAS ESPECÍFICAS (SINTÉTICO)
    print("\n" + "="*50)
    print("INICIANDO TESTES DE MECANICAS ESPECIFICAS")
    print("="*50)

    # A. Struggle Test
    p1_struggle = create_mock_pokemon("Pikachu", [1]) # Pound
    p1_struggle.moves[0].pp = 0 # Força Struggle
    p2_dummy = create_mock_pokemon("Bulbasaur", [1])
    engine = CustomBattleEngine("struggle_test", 
        BattleSide("p1", "P1", [p1_struggle]), 
        BattleSide("p2", "P2", [p2_dummy]))
    run_battle(engine, "TESTE: STRUGGLE (Sem PP)", turn_limit=3)

    # B. Protection & Multi-turn Test
    p1_protect = create_mock_pokemon("ProtectUser", [182, 91]) # Protect, Dig
    p2_attacker = create_mock_pokemon("Attacker", [33]) # Tackle
    engine = CustomBattleEngine("protect_test", 
        BattleSide("p1", "P1", [p1_protect]), 
        BattleSide("p2", "P2", [p2_attacker]))
    # Forçamos as ações para garantir o teste
    engine.start_battle()
    engine.logs.clear()
    print("Turno 1: P1 usa Protect")
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    for log in engine.logs: print(log)
    engine.logs.clear()
    
    print("\nTurno 2: P1 usa Dig (Carga)")
    engine.submit_action("p1", {"type": "move", "move_index": 1})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    for log in engine.logs: print(log)
    engine.logs.clear()

    print("\nTurno 3: P1 usa Dig (Ataque)")
    engine.submit_action("p1", {"type": "move", "move_index": 1})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    for log in engine.logs: print(log)
    engine.logs.clear()

    # C. Phazing & Spikes Test
    p1_phazer = create_mock_pokemon("Skarmory", [191, 18]) # Spikes, Whirlwind
    p2_team = [create_mock_pokemon("P2-A", [33]), create_mock_pokemon("P2-B", [33])]
    engine = CustomBattleEngine("phazing_test", 
        BattleSide("p1", "P1", [p1_phazer]), 
        BattleSide("p2", "P2", p2_team))
    engine.start_battle()
    engine.logs.clear()
    print("\nTurno 1: P1 usa Spikes")
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    for log in engine.logs: print(log)
    engine.logs.clear()
    print("\nTurno 2: P1 usa Whirlwind")
    engine.submit_action("p1", {"type": "move", "move_index": 1})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    for log in engine.logs: print(log)
    engine.logs.clear()

    # D. Synchronize & Intimidate Test
    p1_sync = create_mock_pokemon("Alakazam", [77], ability="synchronize") # Poison Powder
    p2_intimidate = create_mock_pokemon("Gyarados", [33], ability="intimidate") # Tackle
    engine = CustomBattleEngine("ability_test", 
        BattleSide("p1", "P1", [p1_sync]), 
        BattleSide("p2", "P2", [p2_intimidate]))
    engine.start_battle() # Intimidate deve ativar aqui
    for log in engine.logs: print(log)
    engine.logs.clear()
    print("\nTurno 1: P1 envenena P2, Synchronize deve ativar")
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    for log in engine.logs: print(log)
    engine.logs.clear()

    # E. Healing & Items Test
    # 146 is Leftovers in Gen 3 (item_id)
    p1_heal = create_mock_pokemon("Healer", [105], item_id=146) # Recover, Leftovers
    p1_heal.current_hp = 100 # Reduz HP para testar cura
    p2_dummy = create_mock_pokemon("Dummy", [33])
    engine = CustomBattleEngine("heal_test", 
        BattleSide("p1", "P1", [p1_heal]), 
        BattleSide("p2", "P2", [p2_dummy]))
    engine.start_battle()
    engine.logs.clear()
    print("\nTurno 1: P1 usa Recover e Leftovers cura no fim do turno")
    engine.submit_action("p1", {"type": "move", "move_index": 0})
    engine.submit_action("p2", {"type": "move", "move_index": 0})
    for log in engine.logs: print(log)
    engine.logs.clear()

    print("\n=== TODOS OS TESTES CONCLUIDOS ===")

if __name__ == "__main__":
    main()
