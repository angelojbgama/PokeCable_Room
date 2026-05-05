from __future__ import annotations
import random
import logging
import math
from dataclasses import dataclass, field
from typing import Any

from .models import PokemonGen1, BattleMoveGen1
from .damage import calculate_damage_gen1
from .utils import determine_critical_gen1, calculate_hit_gen1

logger = logging.getLogger(__name__)

@dataclass
class BattleSideGen1:
    player_id: str
    player_name: str
    team: list[PokemonGen1] = field(default_factory=list)
    active_index: int = 0
    
    @property
    def active_pokemon(self) -> PokemonGen1 | None:
        if 0 <= self.active_index < len(self.team):
            return self.team[self.active_index]
        return None

class BattleEngineGen1:
    def __init__(self, battle_id: str, side1: BattleSideGen1, side2: BattleSideGen1):
        self.battle_id = battle_id
        self.sides = {"p1": side1, "p2": side2}
        self.turn = 0
        self.finished = False
        self.logs: list[str] = []
        
        # Ações pendentes
        self.pending_actions: dict[str, dict[str, Any]] = {}
        self.force_switch_player: str | None = None

    def add_log(self, log: str):
        self.logs.append(log)
        logger.debug(f"Gen1 Battle {self.battle_id}: {log}")

    def start_battle(self):
        self.add_log("|init|battle")
        for side_id, side in self.sides.items():
            self.add_log(f"|player|{side_id}|{side.player_name}")
            for pkmn in side.team:
                self.add_log(f"|poke|{side_id}|{pkmn.name}, L{pkmn.level}")
        self.add_log("|start|")
        
        # Na Gen 1, o primeiro Pokémon de cada time entra
        self._switch_in("p1", 0)
        self._switch_in("p2", 0)

    def _switch_in(self, side_id: str, index: int):
        side = self.sides[side_id]
        side.active_index = index
        pkmn = side.active_pokemon
        if not pkmn: return
        
        # Resetar estados voláteis ao entrar (exceto se for Baton Pass, mas Gen 1 não tem)
        pkmn.is_confused = False
        pkmn.is_trapped = False
        pkmn.substitute_hp = 0
        pkmn.stat_stages = {k: 0 for k in pkmn.stat_stages}
        
        self.add_log(f"|switch|{side_id}a: {pkmn.nickname}|{pkmn.name}, L{pkmn.level}|{self._condition(pkmn)}")

    def _condition(self, pkmn: PokemonGen1) -> str:
        status = pkmn.status_condition.upper() if pkmn.status_condition else ""
        return f"{pkmn.current_hp}/{pkmn.max_hp}{' ' + status if status else ''}"

    def submit_action(self, player_id: str, action: dict[str, Any]):
        side_id = "p1" if self.sides["p1"].player_id == player_id else "p2"
        
        # Se for troca forçada (após faint)
        if self.force_switch_player == player_id:
            if action["type"] == "switch":
                self._switch_in(side_id, action["index"])
                self.force_switch_player = None
                return
                
        self.pending_actions[side_id] = action
        
        if len(self.pending_actions) == 2:
            self._resolve_turn()

    def _resolve_turn(self):
        self.turn += 1
        self.add_log(f"|turn|{self.turn}")
        
        # 1. Determinar ordem (Prioridade -> Speed -> Random)
        actions = []
        for side_id, action in self.pending_actions.items():
            pkmn = self.sides[side_id].active_pokemon
            priority = 0
            if action["type"] == "move":
                move = pkmn.moves[action["move_index"]]
                priority = move.priority
            
            speed = pkmn.get_modified_stat("spe")
            actions.append({
                "side_id": side_id,
                "action": action,
                "priority": priority,
                "speed": speed,
                "random": random.random()
            })
            
        actions.sort(key=lambda x: (x["priority"], x["speed"], x["random"]), reverse=True)
        
        # 2. Executar ações
        for act in actions:
            if self.finished: break
            self._execute_action(act["side_id"], act["action"])
            self._check_win_condition()
            
        # 3. Efeitos de fim de turno
        if not self.finished:
            self._resolve_end_turn_effects()
            self._check_win_condition()

        self.pending_actions = {}

    def _can_pokemon_move(self, side_id: str, pkmn: PokemonGen1) -> bool:
        slot_tag = f"{side_id}a"
        
        if pkmn.status_condition == "slp":
            pkmn.status_turns -= 1
            if pkmn.status_turns <= 0:
                pkmn.status_condition = None
                self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|slp|[msg]")
                # Na Gen 1, perde o turno ao acordar
            else:
                self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|slp")
            return False
            
        if pkmn.status_condition == "frz":
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|frz")
            return False
            
        if pkmn.status_condition == "par":
            if random.random() < 0.25:
                self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|par")
                return False
                
        if pkmn.is_confused:
            self.add_log(f"|-activate|{slot_tag}: {pkmn.nickname}|confusion")
            pkmn.confusion_turns -= 1
            if pkmn.confusion_turns < 0:
                pkmn.is_confused = False
                self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|confusion")
            else:
                if random.random() < 0.5:
                    # Dano de confusão na Gen 1: Power 40, sem STAB, tipo ???
                    # Simplificado: 1/8 do HP ou fórmula de dano contra si mesmo?
                    # Na Gen 1 o dano de confusão usa o próprio Atk e Def.
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] confusion")
                    # TODO: Implementar dano real de confusão
                    return False

        if pkmn.must_recharge:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|recharge")
            pkmn.must_recharge = False
            return False

        return True

    def _resolve_end_turn_effects(self):
        for side_id, side in self.sides.items():
            pkmn = side.active_pokemon
            if not pkmn or pkmn.current_hp <= 0: continue
            
            slot_tag = f"{side_id}a"
            
            # Burn/Poison/Toxic
            if pkmn.status_condition in ["brn", "psn", "tox"]:
                damage = math.floor(pkmn.max_hp / 16)
                if pkmn.status_condition == "tox":
                    damage = math.floor(pkmn.max_hp / 16) * pkmn.toxic_n
                    pkmn.toxic_n += 1
                
                damage = max(1, damage)
                pkmn.current_hp = max(0, pkmn.current_hp - damage)
                
                from_effect = "psn" if pkmn.status_condition in ["psn", "tox"] else "brn"
                self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] {from_effect}")
                
                if pkmn.current_hp <= 0:
                    self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                    self.force_switch_player = side.player_id

    def _execute_action(self, side_id: str, action: dict[str, Any]):
        pkmn = self.sides[side_id].active_pokemon
        if not pkmn or pkmn.current_hp <= 0: return
        
        if action["type"] == "switch":
            self._switch_in(side_id, action["index"])
            return
            
        if not self._can_pokemon_move(side_id, pkmn):
            return

        if action["type"] == "move":
            move_idx = action["move_index"]
            move = pkmn.moves[move_idx]
            peer_side_id = "p2" if side_id == "p1" else "p1"
            target = self.sides[peer_side_id].active_pokemon
            
            # Trap Move Logic
            if pkmn.is_trapped:
                # Se ja esta usando Wrap, continua
                pkmn.trap_turns -= 1
                if pkmn.trap_turns <= 0:
                    pkmn.is_trapped = False
                    target.is_trapped = False
                    self.add_log(f"|-end|{peer_side_id}a: {target.nickname}|{move.name}")
                # Na Gen 1, Wrap nao gasta PP extra
            else:
                if move.name.lower() in ["wrap", "bind", "fire-spin", "clamp"]:
                    # Inicia trap
                    pkmn.is_trapped = True
                    target.is_trapped = True
                    pkmn.trap_turns = random.randint(2, 5)
                    self.add_log(f"|-activate|{peer_side_id}a: {target.nickname}|move: {move.name}")

            self.add_log(f"|move|{side_id}a: {pkmn.nickname}|{move.name}|{peer_side_id}a")
            
            # Hyper Beam Recharge setup
            if move.name.lower() == "hyper-beam":
                pkmn.must_recharge = True

            # Check accuracy
            if not calculate_hit_gen1(move.accuracy, pkmn.stat_stages["accuracy"], target.stat_stages["evasion"]):
                self.add_log(f"|-miss|{side_id}a: {pkmn.nickname}|{peer_side_id}a: {target.nickname}")
                pkmn.is_trapped = False
                target.is_trapped = False
                return
                
            # Check critical
            is_crit = determine_critical_gen1(pkmn.base_speed, move.high_crit)
            if is_crit: self.add_log("|-crit|")
            
            # Damage
            damage, mult = calculate_damage_gen1(pkmn, target, move, is_crit)
            if mult == 0:
                self.add_log(f"|-immune|{peer_side_id}a: {target.nickname}")
                pkmn.is_trapped = False
                target.is_trapped = False
                return
                
            if damage > 0:
                target.current_hp = max(0, target.current_hp - damage)
                self.add_log(f"|damage|{peer_side_id}a: {target.nickname}|{self._condition(target)}")
                
                if target.current_hp <= 0:
                    self.add_log(f"|faint|{peer_side_id}a: {target.nickname}")
                    self.force_switch_player = self.sides[peer_side_id].player_id
                    # Hyper Beam Kill Glitch
                    if move.name.lower() == "hyper-beam":
                        pkmn.must_recharge = False
                    
                    pkmn.is_trapped = False
                    target.is_trapped = False

    def _check_win_condition(self):
        for side_id, side in self.sides.items():
            if all(p.current_hp <= 0 for p in side.team):
                winner_side = "p2" if side_id == "p1" else "p1"
                self.add_log(f"|win|{self.sides[winner_side].player_name}")
                self.finished = True
                break

    def generate_request(self, player_id: str) -> dict[str, Any]:
        side_id = "p1" if self.sides["p1"].player_id == player_id else "p2"
        side = self.sides[side_id]
        pkmn = side.active_pokemon
        
        if not pkmn: return {}
        
        moves = []
        for i, m in enumerate(pkmn.moves):
            moves.append({
                "move": m.name,
                "id": m.move_id,
                "pp": m.pp,
                "maxpp": m.max_pp,
                "target": "normal",
                "disabled": False
            })
            
        return {
            "active": [{"moves": moves}],
            "side": {
                "name": side.player_name,
                "id": side_id,
                "pokemon": [
                    {
                        "ident": f"{side_id}: {p.nickname}",
                        "details": f"{p.name}, L{p.level}",
                        "condition": self._condition(p),
                        "active": (i == side.active_index),
                        "stats": {"atk": p.stats.atk, "def": p.stats.defen, "spa": p.stats.special, "spd": p.stats.special, "spe": p.stats.spe},
                        "moves": [m.name for m in p.moves],
                        "baseAbility": "none",
                        "item": "none",
                        "pokeball": "pokeball"
                    } for i, p in enumerate(side.team)
                ]
            }
        }
