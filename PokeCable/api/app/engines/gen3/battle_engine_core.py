from __future__ import annotations
import asyncio
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .battle_pokemon import BattlePokemon, BattleMove

from .battle_utils import determine_critical, calculate_hit
from .battle_damage import calculate_damage
from .battle_move_effects import apply_move_effects, get_hit_count

logger = logging.getLogger(__name__)

# Task 7.7: Struggle move definition
STRUGGLE = None # Sera instanciado na CustomBattleEngine se necessário

@dataclass
class BattleSide:
    player_id: str
    player_name: str
    team: list[BattlePokemon] = field(default_factory=list)
    # No 1v1, active_indices = [0]. No 2v2, active_indices = [0, 1]
    active_indices: list[int] = field(default_factory=lambda: [0])
    spikes_layers: int = 0 # Task 7.8
    
    # Task 8.1: Side Conditions (Gen 3)
    reflect_turns: int = 0
    light_screen_turns: int = 0
    safeguard_turns: int = 0
    
    @property
    def active_list(self) -> list[BattlePokemon]:
        """Retorna a lista de pokemons ativos no campo."""
        return [self.team[i] for i in self.active_indices if 0 <= i < len(self.team)]

    def has_available_pokemon(self, exclude_active: bool = False) -> bool:
        """Verifica se ainda existem pokemons saudaveis no time."""
        for i, p in enumerate(self.team):
            if exclude_active and i in self.active_indices:
                continue
            if p.current_hp > 0:
                return True
        return False

class CustomBattleEngine:
    def __init__(self, battle_id: str, side1: BattleSide, side2: BattleSide, battle_format: str = "singles"):
        self.battle_id = battle_id
        self.sides = {"p1": side1, "p2": side2}
        self.format = battle_format # singles ou doubles
        self.turn = 0
        self.finished = False
        self.winner_id = None
        self.logs: list[str] = []
        self.weather = "none"
        self.weather_turns = 0
        
        # Acoes pendentes aguardando todos os jogadores
        # Chave: (side_id, slot_idx)
        self.pending_actions: dict[tuple[str, int], dict[str, Any]] = {}
        
        # force_switch_slots rastreia quais SLOTS precisam de troca
        self.force_switch_slots: set[tuple[str, int]] = set()
        
        # Task 8.2: Baton Pass
        self.baton_pass_slots: dict[tuple[str, int], dict[str, Any]] = {}
        
        # Struggle mock
        global STRUGGLE
        from .battle_pokemon import BattleMove
        STRUGGLE = BattleMove(
            move_id=-1, name="Struggle", type="normal", power=50, accuracy=0, 
            pp=1, max_pp=1, priority=0, damage_class="physical", effect="User receives 1/4 recoil."
        )

    def add_log(self, log: str):
        self.logs.append(log)
        logger.debug(f"Battle {self.battle_id}: {log}")

    def set_status(self, target: BattlePokemon, status: str, side_id: str, source: BattlePokemon | None = None) -> bool:
        """
        Aplica um status ao pokemon se ele ja nao tiver um.
        Retorna True se o status foi aplicado.
        """
        if target.status_condition or target.current_hp <= 0:
            return False
            
        # Task 8.1: Safeguard Check
        side = self.sides[side_id]
        if side.safeguard_turns > 0:
            return False

        # Imunidades de Tipo
        if status == "brn" and "fire" in target.types: return False
        if status == "par" and "electric" in target.types: return False
        if status == "psn" and ("poison" in target.types or "steel" in target.types): return False
        if status == "frz" and "ice" in target.types: return False
        
        target.status_condition = status
        if status == "slp":
            target.status_turns = random.randint(1, 4)
            
        # Determina slot_tag para o log
        slot_tag = f"{side_id}a" # Default
        for s_id, s in self.sides.items():
            if target in s.active_list:
                slot_tag = f"{s_id}{chr(97 + s.active_indices.index(s.team.index(target)))}"
                break

        self.add_log(f"|-status|{slot_tag}: {target.nickname}|{status}")

        # Task 7.4.B: Synchronize (Geração 3)
        if status in ["brn", "par", "psn"] and target.ability == "synchronize" and source:
            source_side_id = "p2" if side_id == "p1" else "p1"
            if source.ability != "synchronize":
                self.add_log(f"|-ability|{slot_tag}: {target.nickname}|Synchronize")
                self.set_status(source, status, source_side_id)

        return True

    def set_weather(self, weather: str, turns: int):
        """Define o clima da batalha."""
        if self.weather == weather:
            return
            
        self.weather = weather
        self.weather_turns = turns
        
        msg = {
            "rain": "It started to rain!",
            "sun": "The sunlight turned harsh!",
            "sandstorm": "A sandstorm brewed!",
            "hail": "It started to hail!"
        }.get(weather, "The weather returned to normal!")
        
        self.add_log(f"|-weather|{weather}")
        self.add_log(f"|message|{msg}")

    def submit_action(self, player_id: str, action: dict[str, Any]) -> bool:
        """Recebe a acao de um jogador para um slot especifico."""
        side_id = "p1" if self.sides["p1"].player_id == player_id else "p2"
        side = self.sides[side_id]
        slot_idx = action.get("slot", 0)
        
        if slot_idx >= len(side.active_indices):
            return False

        pkmn_idx = side.active_indices[slot_idx]
        pkmn = side.team[pkmn_idx]

        # Task 7.6: Se estiver preso, bloqueia troca
        if action["type"] == "switch" and pkmn and not (side_id, slot_idx) in self.force_switch_slots:
            if pkmn.trapped_by_side or pkmn.partial_trap_turns > 0 or pkmn.bide_turns is not None or pkmn.rage_turns > 0:
                self.add_log(f"DEBUG: {pkmn.nickname} esta preso e nao pode trocar!")
                return False

        # Task 7.2: Locked Moves
        if pkmn and pkmn.locked_move_index is not None and not (side_id, slot_idx) in self.force_switch_slots:
            action = {"type": "move", "move_index": pkmn.locked_move_index, "slot": slot_idx}
        
        # Task 8.4: Bide force
        if pkmn and pkmn.bide_turns is not None and not (side_id, slot_idx) in self.force_switch_slots:
             if pkmn.locked_move_index is not None:
                action = {"type": "move", "move_index": pkmn.locked_move_index, "slot": slot_idx}

        # Task 8.8: Rage moves force (Outrage, Thrash)
        if pkmn and pkmn.rage_turns > 0 and not (side_id, slot_idx) in self.force_switch_slots:
            if pkmn.locked_move_index is not None:
                action = {"type": "move", "move_index": pkmn.locked_move_index, "slot": slot_idx}

        # Task 9.2: Choice Band lock
        if pkmn and pkmn.last_move_id and pkmn.item_data and pkmn.item_data.get("effect_type") == "boost_stat" and pkmn.item_data.get("stat") == "atk":
             if action["type"] == "move" and action["move_index"] != -1:
                 m_obj = pkmn.moves[action["move_index"]]
                 if m_obj.move_id != pkmn.last_move_id:
                     self.add_log(f"DEBUG: {pkmn.nickname} esta travado pelo Choice Band!")
                     return False

        # Task 7.12: Encore
        if pkmn and pkmn.encore_turns > 0 and pkmn.encore_move_index is not None and not (side_id, slot_idx) in self.force_switch_slots:
            if action["type"] == "move":
                action = {"type": "move", "move_index": pkmn.encore_move_index, "slot": slot_idx}

        # Validacao Basica de Troca
        if action["type"] == "switch":
            idx = action["index"]
            if idx < 0 or idx >= len(side.team) or side.team[idx].current_hp <= 0 or idx in side.active_indices:
                self.add_log(f"DEBUG: Tentativa invalida de troca. Indice {idx} invalido ou pokemon indisponivel.")
                return False

        # Validacao Basica de Movimento
        if action["type"] == "move":
            move_idx = action["move_index"]
            if move_idx != -1 and (move_idx < 0 or move_idx >= len(pkmn.moves)):
                self.add_log(f"DEBUG: Indice de golpe invalido para {side_id}: {move_idx}")
                return False
        
        # Se for uma troca forçada por desmaio ou Baton Pass, processa na hora
        if (side_id, slot_idx) in self.force_switch_slots or (side_id, slot_idx) in self.baton_pass_slots:
            if action["type"] == "switch":
                baton_data = self.baton_pass_slots.pop((side_id, slot_idx), None)
                self._switch_in(side_id, action["index"], slot_idx, baton_pass_data=baton_data)
                if (side_id, slot_idx) in self.force_switch_slots:
                    self.force_switch_slots.remove((side_id, slot_idx))
                self.add_log(f"DEBUG: Troca de {side_id}:{slot_idx} resolvida.")
            return True
            
        self.pending_actions[(side_id, slot_idx)] = action
        
        # Turno normal: precisa de acoes para todos os pokemons ativos vivos
        total_required = 0
        for s_id, s in self.sides.items():
            for i, p_idx in enumerate(s.active_indices):
                if s.team[p_idx].current_hp > 0:
                    total_required += 1
        
        if len(self.pending_actions) >= total_required:
            self._resolve_turn()
            self.pending_actions.clear()
        
        return True

    def _resolve_turn(self):
        self.turn += 1
        self.add_log(f"|turn|{self.turn}")
        
        # 0. Limpeza de estados volateis do turno anterior
        for side in self.sides.values():
            for pkmn in side.active_list:
                pkmn.is_protected = False
                pkmn.is_flinching = False
                pkmn.destiny_bond = False
                pkmn.last_damage_taken = 0
                pkmn.last_damage_class = None

        # 1. Preparar lista de acoes ordenadas por prioridade e speed
        actions = []
        for (side_id, slot_idx), action in self.pending_actions.items():
            side = self.sides[side_id]
            pkmn = side.team[side.active_indices[slot_idx]]
            if pkmn.current_hp <= 0: continue
            
            priority = 0
            if action["type"] == "switch":
                priority = 10
            elif action["type"] == "move":
                move_idx = action.get("move_index", 0)
                if move_idx == -1: # Struggle
                    priority = 0
                else:
                    priority = pkmn.moves[move_idx].priority
            
            # Speed com modificadores (simplificado: so stage e para/brn)
            speed = pkmn.get_modified_stat("spe", self.weather)
            
            actions.append({
                "side_id": side_id,
                "slot_idx": slot_idx,
                "action": action,
                "priority": priority,
                "speed": speed,
                "random": random.random()
            })
            
        # Ordena: Prioridade desc, Speed desc, Random
        actions.sort(key=lambda x: (x["priority"], x["speed"], x["random"]), reverse=True)
        
        # 2. Executar acoes
        for act in actions:
            if self.finished: break
            self._execute_action(act["side_id"], act["action"], act["slot_idx"])
            self._check_win_condition()

        # 3. Efeitos de Fim de Turno (Clima, Leftovers, etc)
        if not self.finished:
            self._process_end_turn_effects()
            self._check_win_condition()
            
        # Task 7.15: Turn Limit
        if self.turn >= 100 and not self.finished:
            p1_hp = sum(p.current_hp for p in self.sides["p1"].team)
            p2_hp = sum(p.current_hp for p in self.sides["p2"].team)
            self.add_log("|message|Turn limit reached!")
            if p1_hp > p2_hp: self.add_log(f"|win|{self.sides['p1'].player_name}"); self.winner_id = self.sides["p1"].player_id; self.finished = True
            elif p2_hp > p1_hp: self.add_log(f"|win|{self.sides['p2'].player_name}"); self.winner_id = self.sides["p2"].player_id; self.finished = True
            else: self.add_log("|win|draw"); self.finished = True

    def start_battle(self):
        """Inicia a batalha enviando os logs iniciais."""
        self.add_log("|init|battle")
        for side_id, side in self.sides.items():
            self.add_log(f"|player|{side_id}|{side.player_name}")
            for pkmn in side.team:
                self.add_log(f"|poke|{side_id}|{pkmn.name}, L{pkmn.level}")
        self.add_log("|start|")
        
        # Switch in iniciais
        if self.format == "singles":
            self._switch_in("p1", 0, 0); self._switch_in("p2", 0, 0)
        else:
            self._switch_in("p1", 0, 0); self._switch_in("p1", 1, 1)
            self._switch_in("p2", 0, 0); self._switch_in("p2", 1, 1)

    def _switch_in(self, side_id: str, index: int, slot_idx: int, baton_pass_data: dict[str, Any] | None = None):
        side = self.sides[side_id]
        peer_side_id = "p2" if side_id == "p1" else "p1"
        
        # 1. Resetar Pokemon que esta saindo (se existir)
        old_pkmn_idx = side.active_indices[slot_idx]
        if old_pkmn_idx < len(side.team):
            old_pkmn = side.team[old_pkmn_idx]
            old_pkmn.stat_stages = {k: 0 for k in old_pkmn.stat_stages}
            old_pkmn.substitute_hp = 0
            old_pkmn.confusion_turns = 0
            old_pkmn.leech_seed_recipient = None
            old_pkmn.partial_trap_turns = 0
            old_pkmn.partial_trap_name = None
            old_pkmn.trapped_by_side = None
            old_pkmn.perish_song_turns = None
            old_pkmn.destiny_bond = False
            old_pkmn.must_recharge = False
            old_pkmn.rage_turns = 0
            old_pkmn.locked_move_index = None

        for p_idx in self.sides[peer_side_id].active_indices:
            p = self.sides[peer_side_id].team[p_idx]
            if p.trapped_by_side == side_id:
                p.trapped_by_side = None
                self.add_log(f"|-end|{peer_side_id}{chr(97 + self.sides[peer_side_id].active_indices.index(p_idx))}: {p.nickname}|Mean Look|[from] switch")

        side.active_indices[slot_idx] = index
        pkmn = side.team[index]
        slot_tag = f"{side_id}{chr(97 + slot_idx)}"
        
        # 2. Aplicar Estados ao que ENTRA (Baton Pass)
        if baton_pass_data:
            pkmn.stat_stages = baton_pass_data.get("stat_stages", pkmn.stat_stages.copy())
            pkmn.substitute_hp = baton_pass_data.get("substitute_hp", 0)
            pkmn.confusion_turns = baton_pass_data.get("confusion_turns", 0)
            pkmn.leech_seed_recipient = baton_pass_data.get("leech_seed_recipient")
            pkmn.perish_song_turns = baton_pass_data.get("perish_song_turns")
            pkmn.rage_turns = baton_pass_data.get("rage_turns", 0)
        
        # Limpeza redundante de seguranca
        pkmn.partial_trap_turns = 0; pkmn.partial_trap_name = None; pkmn.trapped_by_side = None
        pkmn.destiny_bond = False; pkmn.must_recharge = False
        
        self.add_log(f"|switch|{slot_tag}: {pkmn.nickname}|{pkmn.name}, L{pkmn.level}|{self._condition(pkmn)}")
        
        if side.spikes_layers > 0 and "flying" not in pkmn.types and pkmn.ability != "levitate":
            damage = math.floor(pkmn.max_hp * (0.125 * side.spikes_layers))
            pkmn.current_hp = max(0, pkmn.current_hp - damage)
            self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] Spikes")
            if pkmn.current_hp <= 0: self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}"); return

        # Task 6.1: Ability entry effects (Intimidate)
        if pkmn.ability == "intimidate":
            peer_side = self.sides[peer_side_id]
            for i, p_idx in enumerate(peer_side.active_indices):
                target = peer_side.team[p_idx]
                if target.current_hp > 0:
                    t_tag = f"{peer_side_id}{chr(97+i)}"
                    self.add_log(f"|-ability|{slot_tag}: {pkmn.nickname}|Intimidate")
                    _apply_stat_drop(self, target, t_tag, "atk", 1)

        if pkmn.ability == "trace":
            peer_side = self.sides[peer_side_id]
            for p_idx in peer_side.active_indices:
                target = peer_side.team[p_idx]
                if target.current_hp > 0 and target.ability:
                    pkmn.ability = target.ability
                    t_tag = f"{peer_side_id}{chr(97+peer_side.active_indices.index(p_idx))}"
                    self.add_log(f"|-ability|{slot_tag}: {pkmn.nickname}|{target.ability}|[from] ability: Trace|[of] {t_tag}: {target.nickname}")
                    break
        
        # Task 7.4: Weather abilities
        if pkmn.ability == "drizzle":
            self.set_weather("rain", -1)
        elif pkmn.ability == "drought":
            self.set_weather("sun", -1)
        elif pkmn.ability == "sand-stream":
            self.set_weather("sandstorm", -1)
        
        # Check items on entry (ex: White Herb)
        self._check_and_use_items("entry")

    def _execute_action(self, side_id: str, action: dict[str, Any], slot_idx: int):
        side = self.sides[side_id]
        pkmn_idx = side.active_indices[slot_idx]
        pkmn = side.team[pkmn_idx]
        if not pkmn or pkmn.current_hp <= 0: return

        slot_tag = f"{side_id}{chr(97 + slot_idx)}"

        if action["type"] == "switch":
            self._switch_in(side_id, action["index"], slot_idx)
            return

        if not self._can_pokemon_move(side_id, pkmn, slot_idx): return

        if action["type"] == "move":
            move_index = action.get("move_index", 0)
            is_struggle = (move_index == -1)
            move = STRUGGLE if is_struggle else pkmn.moves[move_index]
            move_name_lower = move.name.lower()

            # Multi-turn moves
            if "solar-beam" in move_name_lower:
                if not pkmn.is_charging and self.weather != "sun":
                    pkmn.is_charging = True
                    pkmn.locked_move_index = move_index
                    self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{move.name}|[still]")
                    self.add_log(f"|-prepare|{slot_tag}: {pkmn.nickname}|{move.name}")
                    return
                else:
                    pkmn.is_charging = False
                    pkmn.locked_move_index = None
                    original_power = move.power
                    if self.weather in ["rain", "sandstorm", "hail"]:
                        move.power = original_power // 2
                    pass 
            elif any(m in move_name_lower for m in ["fly", "dig", "dive", "bounce"]):
                if not pkmn.semi_invulnerable:
                    pkmn.semi_invulnerable = move_name_lower
                    pkmn.locked_move_index = move_index
                    self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{move.name}|[still]")
                    self.add_log(f"|-prepare|{slot_tag}: {pkmn.nickname}|{move.name}")
                    return
                else:
                    pkmn.semi_invulnerable = None
                    pkmn.locked_move_index = None

            if not is_struggle:
                if move.pp > 0: move.pp -= 1
                else:
                    self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|nopp")
                    return

            peer_side_id = "p2" if side_id == "p1" else "p1"
            peer_side = self.sides[peer_side_id]
            target_key = action.get("target")

            targets = []
            if self.format == "singles":
                if peer_side.active_list:
                    targets.append((peer_side_id, 0, peer_side.active_list[0]))
            else:
                if target_key:
                    t_side_id = target_key[:2]
                    t_slot_idx = ord(target_key[2]) - 97
                    t_side = self.sides.get(t_side_id)
                    if t_side and t_slot_idx < len(t_side.active_indices):
                        t_pkmn = t_side.team[t_side.active_indices[t_slot_idx]]
                        if t_pkmn.current_hp > 0:
                            targets.append((t_side_id, t_slot_idx, t_pkmn))

                if not targets:
                    for i, t_pkmn in enumerate(peer_side.active_list):
                        if t_pkmn.current_hp > 0:
                            targets.append((peer_side_id, i, t_pkmn))
                            if "earthquake" not in move_name_lower and "surf" not in move_name_lower:
                                break

            if not targets:
                self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{move.name}|[notarget]")
                self.add_log("|-notarget|")
                return

            t_side_id, t_slot_idx, first_target = targets[0]
            t_slot_tag = f"{t_side_id}{chr(97 + t_slot_idx)}"
            self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{move.name}|{t_slot_tag}")
            pkmn.last_move_id = move.move_id

            for t_side_id, t_slot_idx, target in targets:
                t_slot_tag = f"{t_side_id}{chr(97 + t_slot_idx)}"
                if target.is_protected:
                    self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|move: Protect")
                    continue
                if target.semi_invulnerable:
                    can_hit = False
                    if target.semi_invulnerable == "dig" and move_name_lower in ["earthquake", "magnitude"]: can_hit = True
                    if target.semi_invulnerable == "fly" and move_name_lower in ["gust", "twister", "thunder", "sky-uppercut"]: can_hit = True
                    if move_name_lower == "swift": can_hit = True
                    if not can_hit:
                        self.add_log(f"|-miss|{slot_tag}: {pkmn.nickname}|{t_slot_tag}: {target.nickname}")
                        continue

                if "roar" in move_name_lower or "whirlwind" in move_name_lower:
                    t_side = self.sides[t_side_id]
                    available_indices = [i for i, p in enumerate(t_side.team) if p.current_hp > 0 and i not in t_side.active_indices]
                    if available_indices:
                        new_idx = random.choice(available_indices)
                        self.add_log(f"|drag|{t_slot_tag}: {target.nickname}|{t_side.team[new_idx].name}, L{t_side.team[new_idx].level}|{self._condition(t_side.team[new_idx])}")
                        self._switch_in(t_side_id, new_idx, t_slot_idx)
                        continue
                    else:
                        self.add_log("|-fail|")
                        continue

                if not calculate_hit(move.accuracy, pkmn.stat_stages["accuracy"], target.stat_stages["evasion"], pkmn.level, target.level, move_name_lower in ["horn-drill", "fissure", "guillotine", "sheer-cold"]):
                    accuracy_override = False
                    if self.weather == "rain" and move_name_lower in ["thunder", "hurricane"]:
                        accuracy_override = True 
                    if move_name_lower in ["thunder", "hurricane"]:
                        acc = 100 if self.weather == "rain" else (50 if self.weather == "sun" else move.accuracy)
                        if calculate_hit(acc, pkmn.stat_stages["accuracy"], target.stat_stages["evasion"], pkmn.level, target.level):
                            accuracy_override = True
                    
                    if not accuracy_override:
                        self.add_log(f"|-miss|{slot_tag}: {pkmn.nickname}|{t_slot_tag}: {target.nickname}")
                        continue

                if target.substitute_hp > 0 and move.damage_class == "status":
                    if "confuse" not in move_name_lower and "confuse" not in move.effect.lower():
                        self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|move: Substitute|[damage]")
                        continue

                num_hits = 1 if is_struggle else get_hit_count(move)
                hits_landed = 0
                total_damage = 0
                
                if move.damage_class != "status":
                    for h in range(num_hits):
                        if target.current_hp <= 0: break
                        hits_landed += 1
                        is_crit = determine_critical(0)
                        damage, multiplier = calculate_damage(pkmn, target, move, is_crit, self.weather, target.semi_invulnerable, defending_side=self.sides[t_side_id])
                        if len(targets) > 1: damage = math.floor(damage * 0.5)
                        
                        if target.substitute_hp > 0:
                            target.substitute_hp = max(0, target.substitute_hp - damage)
                            self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|Substitute|[damage]")
                            if target.substitute_hp <= 0: self.add_log(f"|-end|{t_slot_tag}: {target.nickname}|Substitute")
                        else:
                            target.current_hp = max(0, target.current_hp - damage)
                            target.last_damage_taken = damage
                            target.last_damage_class = move.damage_class
                            if target.bide_turns is not None and target.bide_turns > 0:
                                target.bide_damage += damage
                            
                        if is_crit: self.add_log("|-crit|")
                        if h == 0:
                            if multiplier > 1: self.add_log("|-supereffective|")
                            elif 0 < multiplier < 1: self.add_log("|-resisted|")
                            elif multiplier == 0: self.add_log("|-immune|")
                        self.add_log(f"|damage|{t_slot_tag}: {target.nickname}|{self._condition(target)}")
                        if target.current_hp <= 0:
                            self.add_log(f"|faint|{t_slot_tag}: {target.nickname}")
                            if target.destiny_bond:
                                pkmn.current_hp = 0
                                self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|move: Destiny Bond")
                                self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                        total_damage += damage
                    
                    if num_hits > 1:
                        self.add_log(f"|-hitcount|{t_slot_tag}: {target.nickname}|{hits_landed}")

                if target.substitute_hp <= 0 or move.damage_class == "status":
                    if is_struggle:
                        recoil = math.floor(pkmn.max_hp / 4)
                        pkmn.current_hp = max(0, pkmn.current_hp - recoil)
                        self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] recoil")
                        if pkmn.current_hp <= 0: self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                    else:
                        apply_move_effects(self, pkmn, target, move, total_damage, side_id, move_index)

            if "solar-beam" in move_name_lower:
                 move.power = original_power

    def _can_pokemon_move(self, side_id: str, pkmn: BattlePokemon, slot_idx: int) -> bool:
        slot_tag = f"{side_id}{chr(97 + slot_idx)}"
        
        if pkmn.must_recharge:
            pkmn.must_recharge = False
            self.add_log(f"|-mustrecharge|{slot_tag}: {pkmn.nickname}")
            return False

        if pkmn.is_flinching:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|flinch")
            return False
        if pkmn.status_condition == "slp":
            if pkmn.status_turns > 0:
                pkmn.status_turns -= 1
                self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|slp")
                return False
            else:
                pkmn.status_condition = None
                self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|slp")
        if pkmn.status_condition == "frz":
            if random.random() < 0.2:
                pkmn.status_condition = None
                self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|frz")
            else:
                self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|frz")
                return False
        if pkmn.status_condition == "par" and random.random() < 0.25:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|par")
            return False
            
        if pkmn.confusion_turns > 0:
            pkmn.confusion_turns -= 1
            if pkmn.confusion_turns == 0:
                self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|confusion")
            else:
                self.add_log(f"|-activate|{slot_tag}: {pkmn.nickname}|confusion")
                if random.random() < 0.5:
                    damage = calculate_damage(pkmn, pkmn, 
                        BattleMove(0, "Confusion", "none", 40, 100, 1, 1, 0, "physical"),
                        random_factor=100)[0]
                    pkmn.current_hp = max(0, pkmn.current_hp - damage)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] confusion")
                    if pkmn.current_hp <= 0: self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                    return False
        return True

    def _condition(self, pkmn: BattlePokemon) -> str:
        status = pkmn.status_condition or ""
        if pkmn.current_hp <= 0: return "0 fnt"
        return f"{pkmn.current_hp}/{pkmn.max_hp} {status}".strip()

    def _check_win_condition(self):
        p1_alive = self.sides["p1"].has_available_pokemon()
        p2_alive = self.sides["p2"].has_available_pokemon()
        if not p1_alive and not p2_alive:
            self.add_log("|win|draw"); self.finished = True
        elif not p1_alive:
            self.add_log(f"|win|{self.sides['p2'].player_name}"); self.winner_id = self.sides["p2"].player_id; self.finished = True
        elif not p2_alive:
            self.add_log(f"|win|{self.sides['p1'].player_name}"); self.winner_id = self.sides["p1"].player_id; self.finished = True
        
        if self.finished:
            self.force_switch_slots.clear()
        else:
            for s_id, s in self.sides.items():
                for i, p_idx in enumerate(s.active_indices):
                    if s.team[p_idx].current_hp <= 0:
                        if s.has_available_pokemon(exclude_active=True):
                            self.force_switch_slots.add((s_id, i))
                            self.add_log(f"DEBUG: {s_id}:{i} precisa trocar o Pokemon desmaiado.")

    def _process_end_turn_effects(self):
        if self.weather != "none":
            self.weather_turns -= 1
            if self.weather_turns == 0:
                self.add_log("|-weather|none")
                self.weather = "none"
            else:
                for side_id, side in self.sides.items():
                    for slot_idx, pkmn_idx in enumerate(side.active_indices):
                        p = side.team[pkmn_idx]
                        if p.current_hp <= 0: continue
                        if self.weather == "sandstorm" and "rock" not in p.types and "ground" not in p.types and "steel" not in p.types:
                            dmg = math.floor(p.max_hp / 16)
                            p.current_hp = max(0, p.current_hp - dmg)
                            self.add_log(f"|-damage|{side_id}{chr(97+slot_idx)}: {p.nickname}|{self._condition(p)}|[from] Sandstorm")
                        elif self.weather == "hail" and "ice" not in p.types:
                            dmg = math.floor(p.max_hp / 16)
                            p.current_hp = max(0, p.current_hp - dmg)
                            self.add_log(f"|-damage|{side_id}{chr(97+slot_idx)}: {p.nickname}|{self._condition(p)}|[from] Hail")

        self._check_and_use_items("end")

        for side_id, side in self.sides.items():
            for slot_idx, pkmn_idx in enumerate(side.active_indices):
                pkmn = side.team[pkmn_idx]
                if not pkmn or pkmn.current_hp <= 0: continue
                
                slot_tag = f"{side_id}{chr(97 + slot_idx)}"
                
                if pkmn.status_condition == "psn":
                    dmg = math.floor(pkmn.max_hp / 8)
                    pkmn.current_hp = max(0, pkmn.current_hp - dmg)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] psn")
                elif pkmn.status_condition == "brn":
                    dmg = math.floor(pkmn.max_hp / 8)
                    pkmn.current_hp = max(0, pkmn.current_hp - dmg)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] brn")

                item = pkmn.item_data
                if item and item.get("effect_type") == "heal_end_turn":
                    heal = math.floor(pkmn.max_hp * item.get("value", 0.0625))
                    if pkmn.current_hp < pkmn.max_hp:
                        pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                        self.add_log(f"|-heal|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] item: {item['name']}")

                if pkmn.taunt_turns > 0:
                    pkmn.taunt_turns -= 1
                    if pkmn.taunt_turns == 0:
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|move: Taunt")
                
                if pkmn.disable_turns > 0:
                    pkmn.disable_turns -= 1
                    if pkmn.disable_turns == 0:
                        pkmn.disable_move_id = None
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|move: Disable")
                
                if pkmn.encore_turns > 0:
                    pkmn.encore_turns -= 1
                    if pkmn.encore_turns == 0:
                        pkmn.encore_move_index = None
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|Encore")

                if pkmn.ability == "speed-boost":
                    if pkmn.modify_stage("spe", 1) > 0:
                        self.add_log(f"|-ability|{slot_tag}: {pkmn.nickname}|Speed Boost")
                        self.add_log(f"|-boost|{slot_tag}: {pkmn.nickname}|spe|1")
                
                if pkmn.ability == "shed-skin" and pkmn.status_condition:
                    if random.random() < 0.33:
                        old_status = pkmn.status_condition
                        pkmn.status_condition = None
                        self.add_log(f"|-ability|{slot_tag}: {pkmn.nickname}|Shed Skin")
                        self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|{old_status}")

            if side.reflect_turns > 0:
                side.reflect_turns -= 1
                if side.reflect_turns == 0:
                    self.add_log(f"|-sideend|{side_id}: {side.player_name}|Reflect")
            
            if side.light_screen_turns > 0:
                side.light_screen_turns -= 1
                if side.light_screen_turns == 0:
                    self.add_log(f"|-sideend|{side_id}: {side.player_name}|move: Light Screen")
            
            if side.safeguard_turns > 0:
                side.safeguard_turns -= 1
                if side.safeguard_turns == 0:
                    self.add_log(f"|-sideend|{side_id}: {side.player_name}|move: Safeguard")

        for side_id, side in self.sides.items():
            for slot_idx, pkmn_idx in enumerate(side.active_indices):
                pkmn = side.team[pkmn_idx]
                if not pkmn or pkmn.current_hp <= 0: continue
                slot_tag = f"{side_id}{chr(97 + slot_idx)}"
                if pkmn.perish_song_turns is not None:
                    pkmn.perish_song_turns -= 1
                    self.add_log(f"|-start|{slot_tag}: {pkmn.nickname}|perish{pkmn.perish_song_turns}")
                    if pkmn.perish_song_turns <= 0:
                        pkmn.current_hp = 0
                        self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                        pkmn.perish_song_turns = None
                
                if pkmn.rage_turns > 0:
                    pkmn.rage_turns -= 1
                    if pkmn.rage_turns == 0:
                        pkmn.locked_move_index = None
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|move: Thrash")
                        if pkmn.confusion_turns == 0:
                            pkmn.confusion_turns = random.randint(2, 5)
                            self.add_log(f"|-start|{slot_tag}: {pkmn.nickname}|confusion")

    def _check_and_use_items(self, timing: str):
        for side_id, side in self.sides.items():
            for slot_idx, pkmn_idx in enumerate(side.active_indices):
                pkmn = side.team[pkmn_idx]
                if not pkmn or pkmn.current_hp <= 0: continue
                item = pkmn.item_data
                if not item: continue
                slot_tag = f"{side_id}{chr(97 + slot_idx)}"

                if item.get("effect_type") == "heal_threshold":
                    threshold = item.get("threshold", 0.5)
                    if pkmn.current_hp <= math.floor(pkmn.max_hp * threshold):
                        heal = item.get("value", 10)
                        if isinstance(heal, float): heal = math.floor(pkmn.max_hp * heal)
                        pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + int(heal))
                        self.add_log(f"|-item|{slot_tag}: {pkmn.nickname}|{item['name']}")
                        self.add_log(f"|-heal|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] item: {item['name']}")
                        pkmn.consumed_item = True
                elif item.get("effect_type") == "boost_threshold":
                    threshold = item.get("threshold", 0.25)
                    if pkmn.current_hp <= math.floor(pkmn.max_hp * threshold):
                        stat = item.get("stat", "atk")
                        if pkmn.modify_stage(stat, 1) > 0:
                            self.add_log(f"|-item|{slot_tag}: {pkmn.nickname}|{item['name']}")
                            self.add_log(f"|-boost|{slot_tag}: {pkmn.nickname}|{stat}|1")
                            pkmn.consumed_item = True
                elif item.get("effect_type") == "cure_status":
                    if pkmn.status_condition or pkmn.confusion_turns > 0:
                        old_status = pkmn.status_condition
                        pkmn.status_condition = None
                        pkmn.confusion_turns = 0
                        self.add_log(f"|-item|{slot_tag}: {pkmn.nickname}|{item['name']}")
                        if old_status: self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|{old_status}|[from] item: {item['name']}")
                        else: self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|confusion|[from] item: {item['name']}")
                        pkmn.consumed_item = True
                elif item.get("effect_type") == "white_herb":
                    restored = False
                    for s, stage in pkmn.stat_stages.items():
                        if stage < 0: pkmn.stat_stages[s] = 0; restored = True
                    if restored:
                        self.add_log(f"|-item|{slot_tag}: {pkmn.nickname}|White Herb")
                        self.add_log(f"|-clearnegativeboost|{slot_tag}: {pkmn.nickname}")
                        pkmn.consumed_item = True
                elif item.get("effect_type") == "mental_herb":
                    if pkmn.taunt_turns > 0 or pkmn.encore_turns > 0:
                        pkmn.taunt_turns = 0; pkmn.encore_turns = 0
                        self.add_log(f"|-item|{slot_tag}: {pkmn.nickname}|Mental Herb")
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|move: Taunt|[from] item: Mental Herb")
                        pkmn.consumed_item = True
