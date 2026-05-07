from __future__ import annotations
import asyncio
import logging
import math
import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .battle_pokemon import BattlePokemon, BattleMove

from .battle_utils import determine_critical, calculate_hit
from .battle_damage import calculate_damage
from .battle_ability_effects import blocks_soundproof, is_status_immune, is_volatile_immune, is_weather_suppressed
from .battle_move_effects import apply_move_effects, get_hit_count, _apply_stat_drop
from .battle_move_properties import move_is_high_critical, normalize_move_name
from ...data.move_combat_data import MOVE_COMBAT_DATA, get_move_combat_data
from .battle_pokemon import BattleMove

logger = logging.getLogger(__name__)

# Task 7.7: Struggle move definition
STRUGGLE = None # Sera instanciado na CustomBattleEngine se necessário

METRONOME_BANNED_MOVES = {
    "metronome",
    "mimic",
    "mirrormove",
    "struggle",
    "counter",
    "mirrorcoat",
    "bide",
    "disable",
    "encore",
    "leechseed",
    "present",
    "stockpile",
    "spitup",
    "swallow",
    "watersport",
    "mudsport",
    "uproar",
    "beatup",
    "conversion",
    "conversion2",
    "doomdesire",
}

DOUBLE_SPREAD_MOVES = {
    "earthquake",
    "surf",
    "rockslide",
    "magnitude",
    "explosion",
    "selfdestruct",
}

DOUBLE_SELF_TARGET_MOVES = {
    "protect",
    "detect",
    "endure",
    "substitute",
    "recover",
    "refresh",
    "healbell",
    "aromatherapy",
    "stockpile",
    "swallow",
    "wish",
    "ingrain",
    "lockon",
    "mindreader",
    "conversion",
    "conversion2",
    "curse",
    "bellydrum",
    "uproar",
    "growth",
    "calmmind",
    "bulkup",
    "dragondance",
    "meditate",
    "harden",
    "amnesia",
    "agility",
    "defensecurl",
    "cosmicpower",
    "safeguard",
    "reflect",
    "lightscreen",
    "mist",
    "metronome",
    "bide",
    "followme",
    "snatch",
    "sleeptalk",
}

DOUBLE_ALLY_TARGET_MOVES = {
    "helpinghand",
}

DOUBLE_ONLY_MOVES = {
    "helpinghand",
    "followme",
    "snatch",
}

NEVER_MISS_MOVES = {
    "swift",
    "feintattack",
    "vitalthrow",
    "shadowpunch",
    "aerialace",
    "magicalleaf",
    "shockwave",
}

SNATCH_BANNED_MOVES = {
    "snatch",
    "followme",
    "metronome",
    "mimic",
    "mirrormove",
    "bide",
}


def _normalize_move_name(value: str) -> str:
    return normalize_move_name(value)


def _move_target_mode(move: BattleMove, attacker: BattlePokemon | None = None) -> str:
    move_name_norm = _normalize_move_name(move.name)
    effect_lower = move.effect.lower().replace("’", "'")
    if move_name_norm in DOUBLE_ALLY_TARGET_MOVES:
        return "ally"
    if move_name_norm in DOUBLE_SPREAD_MOVES:
        return "all_adjacent"
    if move_name_norm in DOUBLE_SELF_TARGET_MOVES:
        if move_name_norm == "curse" and attacker is not None and "ghost" in attacker.types:
            return "foe"
        return "self"
    if move.damage_class == "status":
        if "ally" in effect_lower:
            return "ally"
        if "user" in effect_lower and "target" not in effect_lower:
            return "self"
    return "foe"


def _is_snatchable_move(move: BattleMove, attacker: BattlePokemon | None = None) -> bool:
    move_name_norm = _normalize_move_name(move.name)
    if move_name_norm in SNATCH_BANNED_MOVES:
        return False
    return _move_target_mode(move, attacker) in {"self", "ally"}


def _build_move_from_data(move_id: int) -> BattleMove | None:
    data = get_move_combat_data(int(move_id))
    if not data:
        return None
    return BattleMove(
        move_id=int(move_id),
        name=str(data["name"]),
        type=str(data["type"]),
        power=int(data["power"]) if data.get("power") is not None else 0,
        accuracy=int(data["accuracy"]) if data.get("accuracy") is not None else 100,
        pp=int(data["pp"]),
        max_pp=int(data["pp"]),
        priority=int(data.get("priority") or 0),
        damage_class=str(data["damage_class"]),
        effect=str(data.get("effect") or ""),
        effect_chance=data.get("effect_chance"),
    )

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
    mist_turns: int = 0
    future_sight_turns: int = 0
    future_sight_damage: int = 0
    future_sight_source_side: str | None = None
    wish_turns: dict[int, int] = field(default_factory=dict)
    wish_amounts: dict[int, int] = field(default_factory=dict)
    
    @property
    def active_list(self) -> list[BattlePokemon]:
        """Retorna a lista de pokemons ativos no campo."""
        return [self.team[i] for i in self.active_indices if 0 <= i < len(self.team)]

    @property
    def active_pokemon(self) -> BattlePokemon | None:
        """Atalho de compatibilidade para a primeira posicao ativa."""
        return self.active_list[0] if self.active_list else None

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
        if status == "slp":
            if any(p.uproar_turns > 0 for battle_side in self.sides.values() for p in battle_side.active_list):
                if target.ability != "soundproof":
                    return False

        if is_status_immune(target.ability, status):
            return False

        # Imunidades de Tipo
        if status == "brn" and "fire" in target.types: return False
        if status == "par" and "electric" in target.types: return False
        if status in {"psn", "tox"} and ("poison" in target.types or "steel" in target.types): return False
        if status == "frz" and "ice" in target.types: return False
        
        target.status_condition = status
        if status == "slp":
            target.status_turns = random.randint(1, 4)
        elif status == "tox":
            target.toxic_turns = 1
            
        # Determina slot_tag para o log
        slot_tag = f"{side_id}a" # Default
        for s_id, s in self.sides.items():
            if target in s.active_list:
                slot_tag = f"{s_id}{chr(97 + s.active_indices.index(s.team.index(target)))}"
                break

        self.add_log(f"|-status|{slot_tag}: {target.nickname}|{status}")

        # Task 7.4.B: Synchronize (Geração 3)
        if status in ["brn", "par", "psn", "tox"] and target.ability == "synchronize" and source:
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
        self._update_weather_forms()

    def _slot_tag(self, side_id: str, slot_idx: int) -> str:
        return f"{side_id}{chr(97 + slot_idx)}"

    def _active_slot_for_pokemon(self, side_id: str, pokemon: BattlePokemon) -> int | None:
        side = self.sides[side_id]
        for slot_idx, p_idx in enumerate(side.active_indices):
            if side.team[p_idx] is pokemon:
                return slot_idx
        return None

    def _pokemon_at_slot(self, side_id: str, slot_idx: int | None) -> BattlePokemon | None:
        if slot_idx is None:
            return None
        side = self.sides.get(side_id)
        if side is None or slot_idx < 0 or slot_idx >= len(side.active_indices):
            return None
        pokemon_index = side.active_indices[slot_idx]
        if pokemon_index < 0 or pokemon_index >= len(side.team):
            return None
        return side.team[pokemon_index]

    def _partner_active(self, side_id: str, slot_idx: int) -> tuple[int, BattlePokemon] | None:
        if self.format != "doubles":
            return None
        side = self.sides[side_id]
        for partner_slot_idx, p_idx in enumerate(side.active_indices):
            if partner_slot_idx == slot_idx:
                continue
            partner = side.team[p_idx]
            if partner.current_hp > 0:
                return partner_slot_idx, partner
        return None

    def _weather_suppressed(self) -> bool:
        for side in self.sides.values():
            for pkmn in side.active_list:
                if pkmn.current_hp > 0 and is_weather_suppressed(pkmn.ability):
                    return True
        return False

    def _effective_weather(self) -> str:
        return "none" if self._weather_suppressed() else self.weather

    def _update_weather_forms(self) -> None:
        for side in self.sides.values():
            for pkmn in side.active_list:
                if pkmn.current_hp <= 0:
                    continue
                if pkmn.ability == "forecast":
                    pkmn.apply_forecast(self._effective_weather())

    def _switch_blocked_by_abilities(self, side_id: str, pokemon: BattlePokemon) -> str | None:
        peer_side_id = "p2" if side_id == "p1" else "p1"
        peer_side = self.sides[peer_side_id]

        if any(p.current_hp > 0 and p.ability == "shadow-tag" for p in peer_side.active_list):
            return "shadow-tag"

        if (
            any(p.current_hp > 0 and p.ability == "arena-trap" for p in peer_side.active_list)
            and "flying" not in pokemon.types
            and pokemon.ability != "levitate"
        ):
            return "arena-trap"

        if any(p.current_hp > 0 and p.ability == "magnet-pull" for p in peer_side.active_list) and "steel" in pokemon.types:
            return "magnet-pull"

        return None

    def submit_action(self, player_id: str, action: dict[str, Any]) -> bool:
        """Recebe a acao de um jogador para um slot especifico."""
        side_id = "p1" if self.sides["p1"].player_id == player_id else "p2"
        side = self.sides[side_id]
        slot_idx = action.get("slot", 0)
        
        if slot_idx >= len(side.active_indices):
            return False

        pkmn_idx = side.active_indices[slot_idx]
        pkmn = side.team[pkmn_idx]
        slot_tag = f"{side_id}{chr(97 + slot_idx)}"

        # Task 7.6: Se estiver preso, bloqueia troca
        if action["type"] == "switch" and pkmn and not (side_id, slot_idx) in self.force_switch_slots:
            if (
                pkmn.trapped_by_side
                or pkmn.partial_trap_turns > 0
                or pkmn.bide_turns is not None
                or pkmn.rage_turns > 0
                or pkmn.ingrain
            ):
                logger.debug("Battle %s: %s esta preso e nao pode trocar!", self.battle_id, pkmn.nickname)
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
                     logger.debug("Battle %s: %s esta travado pelo Choice Band!", self.battle_id, pkmn.nickname)
                     return False

        # Task 7.12: Encore
        if pkmn and pkmn.encore_turns > 0 and pkmn.encore_move_index is not None and not (side_id, slot_idx) in self.force_switch_slots:
            if action["type"] == "move":
                action = {"type": "move", "move_index": pkmn.encore_move_index, "slot": slot_idx}

        if pkmn and pkmn.torment_turns > 0 and action["type"] == "move" and action.get("move_index", -1) != -1:
            move_idx = action["move_index"]
            if pkmn.last_move_id is not None and pkmn.moves[move_idx].move_id == pkmn.last_move_id:
                self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|torment")
                return False

        # Validacao Basica de Troca
        if action["type"] == "switch":
            idx = action["index"]
            if idx < 0 or idx >= len(side.team) or side.team[idx].current_hp <= 0 or idx in side.active_indices:
                logger.debug(
                    "Battle %s: tentativa invalida de troca. Indice %s invalido ou pokemon indisponivel.",
                    self.battle_id,
                    idx,
                )
                return False
            if (side_id, slot_idx) not in self.force_switch_slots:
                blocked_by = self._switch_blocked_by_abilities(side_id, side.team[idx])
                if blocked_by is not None:
                    self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|{blocked_by}")
                    return False

        # Validacao Basica de Movimento
        if action["type"] == "move":
            move_idx = action["move_index"]
            if move_idx != -1 and (move_idx < 0 or move_idx >= len(pkmn.moves)):
                logger.debug("Battle %s: indice de golpe invalido para %s: %s", self.battle_id, side_id, move_idx)
                return False
            if move_idx != -1:
                move_obj = pkmn.moves[move_idx]
                if pkmn.disable_turns > 0 and pkmn.disable_move_id == move_obj.move_id:
                    self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|disable")
                    return False
                if pkmn.taunt_turns > 0 and move_obj.damage_class == "status":
                    self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|taunt")
                    return False
        
        # Se for uma troca forçada por desmaio ou Baton Pass, processa na hora
        if (side_id, slot_idx) in self.force_switch_slots or (side_id, slot_idx) in self.baton_pass_slots:
            if action["type"] == "switch":
                baton_data = self.baton_pass_slots.pop((side_id, slot_idx), None)
                self._switch_in(side_id, action["index"], slot_idx, baton_pass_data=baton_data)
                if (side_id, slot_idx) in self.force_switch_slots:
                    self.force_switch_slots.remove((side_id, slot_idx))
                logger.debug("Battle %s: troca de %s:%s resolvida.", self.battle_id, side_id, slot_idx)
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
                pkmn.endure_active = False
                pkmn.damage_taken_this_turn = 0

        # 1. Preparar lista de acoes ordenadas por prioridade e speed
        actions = []
        effective_weather = self._effective_weather()
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
                    move_name_norm = pkmn.moves[move_idx].name.lower().replace("-", "").replace(" ", "")
                    priority = pkmn.moves[move_idx].priority
                    if move_name_norm == "pursuit":
                        peer_side_id = "p2" if side_id == "p1" else "p1"
                        if any(
                            peer_action.get("type") == "switch"
                            for (peer_side_key, _peer_slot), peer_action in self.pending_actions.items()
                            if peer_side_key == peer_side_id
                        ):
                            priority = max(priority, 11)

            # Speed com modificadores (simplificado: so stage e para/brn)
            speed = pkmn.get_modified_stat("spe", effective_weather)
            
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
        if slot_idx >= len(side.active_indices):
            side.active_indices.extend([-1] * (slot_idx - len(side.active_indices) + 1))
        old_pkmn_idx = side.active_indices[slot_idx]
        if 0 <= old_pkmn_idx < len(side.team) and old_pkmn_idx != index:
            old_pkmn = side.team[old_pkmn_idx]
            if old_pkmn.ability == "natural-cure" and old_pkmn.status_condition is not None:
                old_pkmn.status_condition = None
                old_pkmn.status_turns = 0
                old_pkmn.toxic_turns = 0
                self.add_log(f"|-curestatus|{side_id}{chr(97 + slot_idx)}: {old_pkmn.nickname}|[from] ability: Natural Cure")
            old_pkmn.stat_stages = {k: 0 for k in old_pkmn.stat_stages}
            if old_pkmn.original_stats is not None:
                old_pkmn.stats = deepcopy(old_pkmn.original_stats)
            if old_pkmn.original_moves:
                old_pkmn.moves = deepcopy(old_pkmn.original_moves)
            if old_pkmn.original_types:
                old_pkmn.types = list(old_pkmn.original_types)
            if old_pkmn.original_ability is not None:
                old_pkmn.ability = old_pkmn.original_ability
            old_pkmn.substitute_hp = 0
            old_pkmn.confusion_turns = 0
            old_pkmn.leech_seed_recipient = None
            old_pkmn.nightmare_active = False
            old_pkmn.yawn_turns = 0
            old_pkmn.ingrain = False
            old_pkmn.torment_turns = 0
            old_pkmn.partial_trap_turns = 0
            old_pkmn.partial_trap_name = None
            old_pkmn.trapped_by_side = None
            old_pkmn.perish_song_turns = None
            old_pkmn.destiny_bond = False
            old_pkmn.must_recharge = False
            old_pkmn.rage_turns = 0
            old_pkmn.fury_cutter_hits = 0
            old_pkmn.rollout_turns = 0
            old_pkmn.stockpile_count = 0
            old_pkmn.uproar_turns = 0
            old_pkmn.lock_on_turns = 0
            old_pkmn.focus_energy = False
            old_pkmn.truant_counter = 0
            old_pkmn.locked_move_index = None
            old_pkmn.toxic_turns = 0
            old_pkmn.attracted_to_side = None
            old_pkmn.curse_active = False
            old_pkmn.foresight_active = False
            old_pkmn.helping_hand_turns = 0
            old_pkmn.follow_me_turns = 0
            old_pkmn.snatch_turns = 0
            old_pkmn.last_damage_move_type = None
            old_pkmn.last_damage_taken = 0
            old_pkmn.last_damage_class = None
            old_pkmn.last_damage_source_side = None
            old_pkmn.last_damage_source_slot = None
            old_pkmn.bide_target_side = None
            old_pkmn.bide_target_slot = None
            old_pkmn.damage_taken_this_turn = 0

        for p_idx in self.sides[peer_side_id].active_indices:
            p = self.sides[peer_side_id].team[p_idx]
            if p.trapped_by_side == side_id:
                p.trapped_by_side = None
                self.add_log(f"|-end|{peer_side_id}{chr(97 + self.sides[peer_side_id].active_indices.index(p_idx))}: {p.nickname}|Mean Look|[from] switch")
            if p.attracted_to_side == side_id:
                p.attracted_to_side = None
                self.add_log(f"|-end|{peer_side_id}{chr(97 + self.sides[peer_side_id].active_indices.index(p_idx))}: {p.nickname}|move: Attract|[from] switch")

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
            pkmn.stockpile_count = baton_pass_data.get("stockpile_count", 0)
            pkmn.ingrain = baton_pass_data.get("ingrain", False)

        # Limpeza redundante de seguranca
        pkmn.partial_trap_turns = 0; pkmn.partial_trap_name = None; pkmn.trapped_by_side = None
        pkmn.destiny_bond = False; pkmn.must_recharge = False
        pkmn.truant_counter = 0
        pkmn.first_turn_on_field = True

        self.add_log(f"|switch|{slot_tag}: {pkmn.nickname}|{pkmn.name}, L{pkmn.level}|{self._condition(pkmn)}")
        
        if side.spikes_layers > 0 and "flying" not in pkmn.types and pkmn.ability != "levitate":
            spikes_fraction = {1: 1 / 8, 2: 1 / 6, 3: 1 / 4}.get(side.spikes_layers, 0)
            damage = max(1, math.floor(pkmn.max_hp * spikes_fraction))
            pkmn.current_hp = max(0, pkmn.current_hp - damage)
            pkmn.damage_taken_this_turn = max(pkmn.damage_taken_this_turn, damage)
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
        self._update_weather_forms()

    def _execute_action(self, side_id: str, action: dict[str, Any], slot_idx: int):
        side = self.sides[side_id]
        pkmn_idx = side.active_indices[slot_idx]
        pkmn = side.team[pkmn_idx]
        if not pkmn or pkmn.current_hp <= 0: return

        slot_tag = f"{side_id}{chr(97 + slot_idx)}"

        if action["type"] == "switch":
            self._switch_in(side_id, action["index"], slot_idx)
            return

        if action["type"] == "move":
            move_index = action.get("move_index", 0)
            is_struggle = (move_index == -1)
            move = STRUGGLE if is_struggle else pkmn.moves[move_index]
            pp_move = move
            move_power_override: int | None = None
            battle_weather = self._effective_weather()
            move_name_lower = move.name.lower()
            move_name_norm = move_name_lower.replace("-", "").replace(" ", "")
            command_move_name_norm = move_name_norm

            if not self._can_pokemon_move(side_id, pkmn, slot_idx, move_name_norm):
                return

            if command_move_name_norm == "sleeptalk":
                if pkmn.status_condition != "slp":
                    self.add_log("|-fail|")
                    return
                eligible_indices = [
                    idx
                    for idx, candidate in enumerate(pkmn.moves)
                    if idx != move_index and normalize_move_name(candidate.name) not in {"sleeptalk", "struggle"} and int(candidate.pp or 0) > 0
                ]
                if not eligible_indices:
                    self.add_log("|-fail|")
                    return
                chosen_index = random.choice(eligible_indices)
                move_index = chosen_index
                move = pkmn.moves[chosen_index]
                move_name_lower = move.name.lower()
                move_name_norm = move_name_lower.replace("-", "").replace(" ", "")

            if move_name_norm == "metronome":
                metronome_move = self._random_metronome_move()
                if metronome_move is None:
                    self.add_log("|-fail|")
                    return
                pp_move = move
                move = metronome_move
                move_name_lower = move.name.lower()
                move_name_norm = move_name_lower.replace("-", "").replace(" ", "")

            if move_name_norm != "furycutter":
                pkmn.fury_cutter_hits = 0
            if move_name_norm != "rollout":
                pkmn.rollout_turns = 0

            if move_name_norm not in {"protect", "detect"}:
                pkmn.consecutive_protects = 0

            # Multi-turn moves
            if "solar-beam" in move_name_lower:
                if not pkmn.is_charging and battle_weather != "sun":
                    pkmn.is_charging = True
                    pkmn.locked_move_index = move_index
                    self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{move.name}|[still]")
                    self.add_log(f"|-prepare|{slot_tag}: {pkmn.nickname}|{move.name}")
                    return
                else:
                    pkmn.is_charging = False
                    pkmn.locked_move_index = None
                    pass 
            elif move_name_norm in {"razorwind", "skullbash", "skyattack"}:
                if not pkmn.is_charging:
                    pkmn.is_charging = True
                    pkmn.locked_move_index = move_index
                    if move_name_norm == "skullbash":
                        _apply_stat_boost(engine, pkmn, side_id, "def", 1)
                    if move_name_norm == "skyattack":
                        pkmn.semi_invulnerable = "sky-attack"
                    self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{move.name}|[still]")
                    self.add_log(f"|-prepare|{slot_tag}: {pkmn.nickname}|{move.name}")
                    return
                else:
                    pkmn.is_charging = False
                    pkmn.locked_move_index = None
                    if move_name_norm == "skyattack":
                        pkmn.semi_invulnerable = None
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

            if move_name_norm == "fakeout" and not pkmn.first_turn_on_field:
                self.add_log("|-fail|")
                return

            if not is_struggle:
                if pp_move.pp > 0:
                    pp_move.pp -= 1
                else:
                    self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|nopp")
                    return

            peer_side_id = "p2" if side_id == "p1" else "p1"
            peer_side = self.sides[peer_side_id]
            target_key = action.get("target")
            target_mode = _move_target_mode(move, pkmn)

            targets = []
            if target_key:
                t_side_id = target_key[:2]
                t_slot_idx = ord(target_key[2]) - 97
                t_side = self.sides.get(t_side_id)
                if t_side and t_slot_idx < len(t_side.active_indices):
                    t_pkmn = t_side.team[t_side.active_indices[t_slot_idx]]
                    if t_pkmn.current_hp > 0:
                        targets.append((t_side_id, t_slot_idx, t_pkmn))
            if not targets:
                if target_mode == "ally":
                    partner_info = self._partner_active(side_id, slot_idx)
                    if partner_info is not None:
                        partner_slot_idx, partner = partner_info
                        targets.append((side_id, partner_slot_idx, partner))
                elif target_mode == "self":
                    targets.append((side_id, slot_idx, pkmn))
                elif target_mode == "all_adjacent":
                    for t_side_id, t_side in self.sides.items():
                        for i, p_idx in enumerate(t_side.active_indices):
                            t_pkmn = t_side.team[p_idx]
                            if t_pkmn.current_hp > 0 and not (t_side_id == side_id and i == slot_idx):
                                targets.append((t_side_id, i, t_pkmn))
                else:
                    for i, t_pkmn in enumerate(peer_side.active_list):
                        if t_pkmn.current_hp > 0:
                            targets.append((peer_side_id, i, t_pkmn))
                            if move_name_norm not in DOUBLE_SPREAD_MOVES:
                                break

            if not targets:
                self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{move.name}|[notarget]")
                self.add_log("|-notarget|")
                return

            if self.format == "doubles" and target_mode == "foe" and move.type == "electric" and targets:
                current_target_side_id, current_target_slot_idx, current_target = targets[0]
                if current_target.ability != "lightning-rod":
                    lightning_rod_candidates = [
                        (
                            target_pkmn.get_modified_stat("spe", battle_weather),
                            t_slot_idx,
                            target_pkmn,
                        )
                        for t_slot_idx, p_idx in enumerate(self.sides[current_target_side_id].active_indices)
                        if (
                            (target_pkmn := self.sides[current_target_side_id].team[p_idx]).current_hp > 0
                            and target_pkmn.ability == "lightning-rod"
                        )
                    ]
                    if lightning_rod_candidates:
                        _, current_target_slot_idx, current_target = max(lightning_rod_candidates, key=lambda item: (item[0], -item[1]))
                        targets[0] = (current_target_side_id, current_target_slot_idx, current_target)

            pressure_targets = [
                (t_side_id, t_slot_idx, target)
                for t_side_id, t_slot_idx, target in targets
                if t_side_id != side_id and target.ability == "pressure"
            ]
            if command_move_name_norm == "perishsong":
                pressure_targets = [
                    (t_side_id, t_slot_idx, target)
                    for t_side_id, t_side in self.sides.items()
                    for t_slot_idx, p_idx in enumerate(t_side.active_indices)
                    if t_side_id != side_id and (target := t_side.team[p_idx]).current_hp > 0 and target.ability == "pressure"
                ]
            if pressure_targets and not is_struggle:
                for p_side_id, p_slot_idx, pressure_target in pressure_targets:
                    self.add_log(f"|-ability|{self._slot_tag(p_side_id, p_slot_idx)}: {pressure_target.nickname}|Pressure")
                pp_move.pp = max(0, pp_move.pp - len(pressure_targets))

            t_side_id, t_slot_idx, first_target = targets[0]
            t_slot_tag = f"{t_side_id}{chr(97 + t_slot_idx)}"
            self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{move.name}|{t_slot_tag}")
            pkmn.last_move_id = pp_move.move_id if command_move_name_norm in {"metronome", "sleeptalk"} else move.move_id
            helping_hand_consumed = pkmn.helping_hand_turns > 0

            if move_name_norm in {"selfdestruct", "explosion"}:
                damp_target = next(
                    (
                        (p_side_id, p_slot_idx, pressure_target)
                        for p_side_id, side in self.sides.items()
                        for p_slot_idx, p_idx in enumerate(side.active_indices)
                        if (pressure_target := side.team[p_idx]).current_hp > 0 and pressure_target.ability == "damp"
                    ),
                    None,
                )
                if damp_target is not None:
                    damp_side_id, damp_slot_idx, damp_pkmn = damp_target
                    self.add_log(f"|-ability|{self._slot_tag(damp_side_id, damp_slot_idx)}: {damp_pkmn.nickname}|Damp")
                    self.add_log("|-fail|")
                    return
                if pkmn.current_hp > 0:
                    pkmn.current_hp = 0
                    self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")

            if move_name_norm == "present":
                present_roll = random.random()
                if present_roll < 0.1:
                    heal_amount = max(1, math.floor(first_target.max_hp / 4))
                    first_target.current_hp = min(first_target.max_hp, first_target.current_hp + heal_amount)
                    self.add_log(f"|-heal|{t_slot_tag}: {first_target.nickname}|{self._condition(first_target)}|[from] move: Present")
                    return
                if present_roll < 0.4:
                    move_power_override = 40
                elif present_roll < 0.7:
                    move_power_override = 80
                else:
                    move_power_override = 120

            if move_name_norm == "futuresight":
                apply_move_effects(self, pkmn, targets[0][2], move, 0, side_id, move_index)
                return

            for t_side_id, t_slot_idx, target in targets:
                t_slot_tag = f"{t_side_id}{chr(97 + t_slot_idx)}"
                if self.format == "doubles" and target_mode == "foe":
                    follow_me_target = next(
                        (
                            (i, t_pkmn)
                            for i, p_idx in enumerate(self.sides[t_side_id].active_indices)
                            if (t_pkmn := self.sides[t_side_id].team[p_idx]).current_hp > 0 and t_pkmn.follow_me_turns > 0
                        ),
                        None,
                    )
                    if follow_me_target is not None and follow_me_target[1] is not target:
                        t_slot_idx, target = follow_me_target
                        t_slot_tag = self._slot_tag(t_side_id, t_slot_idx)
                        self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|move: Follow Me")
                if target.is_protected:
                    if move_name_norm == "furycutter":
                        pkmn.fury_cutter_hits = 0
                    if move_name_norm == "rollout":
                        pkmn.rollout_turns = 0
                    self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|move: Protect")
                    if move_name_norm == "triplekick":
                        break
                    continue
                if target.semi_invulnerable:
                    can_hit = pkmn.lock_on_turns > 0
                    if target.semi_invulnerable == "dig" and move_name_lower in ["earthquake", "magnitude"]: can_hit = True
                    if target.semi_invulnerable == "dive" and move_name_lower in ["surf"]: can_hit = True
                    if target.semi_invulnerable in {"fly", "sky-attack"} and move_name_lower in ["gust", "twister", "thunder", "sky-uppercut"]: can_hit = True
                    if not can_hit:
                        if move_name_norm == "furycutter":
                            pkmn.fury_cutter_hits = 0
                        if move_name_norm == "rollout":
                            pkmn.rollout_turns = 0
                        self.add_log(f"|-miss|{slot_tag}: {pkmn.nickname}|{t_slot_tag}: {target.nickname}")
                        if move_name_norm == "triplekick":
                            break
                        continue

                if target.ability == "soundproof" and blocks_soundproof(move):
                    if move_name_norm == "furycutter":
                        pkmn.fury_cutter_hits = 0
                    if move_name_norm == "rollout":
                        pkmn.rollout_turns = 0
                    self.add_log("|-fail|")
                    continue

                if "roar" in move_name_lower or "whirlwind" in move_name_lower:
                    if target.ability == "suction-cups":
                        self.add_log("|-fail|")
                        continue
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

                if move_name_norm == "snore" and pkmn.status_condition != "slp":
                    self.add_log("|-fail|")
                    return
                if move_name_norm == "dreameater" and target.status_condition != "slp":
                    self.add_log("|-fail|")
                    continue

                if move_name_norm in NEVER_MISS_MOVES:
                    accuracy_override = True
                else:
                    accuracy_override = calculate_hit(
                        move.accuracy,
                        pkmn.stat_stages["accuracy"],
                        0 if getattr(target, "foresight_active", False) else target.stat_stages["evasion"],
                        pkmn.level,
                        target.level,
                        move_name_lower in ["horn-drill", "fissure", "guillotine", "sheer-cold"],
                        attacker_ability=pkmn.ability,
                        target_ability=target.ability,
                        weather=battle_weather,
                        move_damage_class=move.damage_class,
                    )
                if pkmn.lock_on_turns > 0:
                    accuracy_override = True
                if not accuracy_override:
                    if battle_weather == "rain" and move_name_lower in ["thunder", "hurricane"]:
                        accuracy_override = True
                    if move_name_lower in ["thunder", "hurricane"]:
                        acc = 100 if battle_weather == "rain" else (50 if battle_weather == "sun" else move.accuracy)
                        if calculate_hit(
                            acc,
                            pkmn.stat_stages["accuracy"],
                            target.stat_stages["evasion"],
                            pkmn.level,
                            target.level,
                            attacker_ability=pkmn.ability,
                            target_ability=target.ability,
                            weather=battle_weather,
                            move_damage_class=move.damage_class,
                        ):
                            accuracy_override = True

                if not accuracy_override:
                    if move_name_norm == "furycutter":
                        pkmn.fury_cutter_hits = 0
                    if move_name_norm == "rollout":
                        pkmn.rollout_turns = 0
                    self.add_log(f"|-miss|{slot_tag}: {pkmn.nickname}|{t_slot_tag}: {target.nickname}")
                    if move_name_norm == "triplekick":
                        break
                    continue

                if move_name_norm == "focuspunch" and pkmn.damage_taken_this_turn > 0:
                    self.add_log("|-fail|")
                    return

                if move_name_norm in {"counter", "mirrorcoat"}:
                    source_side_id = pkmn.last_damage_source_side
                    source_slot_idx = pkmn.last_damage_source_slot
                    if (
                        pkmn.last_damage_taken <= 0
                        or source_side_id is None
                        or source_slot_idx is None
                    ):
                        self.add_log("|-fail|")
                        return
                    source_target = self._pokemon_at_slot(source_side_id, source_slot_idx)
                    if source_target is None or source_target.current_hp <= 0 or source_side_id == side_id:
                        self.add_log("|-fail|")
                        return
                    target_to_hit = source_target
                    target_side_id = source_side_id
                    target_slot_idx = source_slot_idx
                    if self.format == "doubles":
                        follow_me_target = next(
                            (
                                (idx, pokemon)
                                for idx, p_idx in enumerate(self.sides[source_side_id].active_indices)
                                if (pokemon := self.sides[source_side_id].team[p_idx]).current_hp > 0 and pokemon.follow_me_turns > 0
                            ),
                            None,
                        )
                        if follow_me_target is not None and follow_me_target[1] is not source_target:
                            target_slot_idx, target_to_hit = follow_me_target
                    dmg = pkmn.last_damage_taken * 2
                    reactive_name = "Counter" if move_name_norm == "counter" else "Mirror Coat"
                    damage_class = "physical" if move_name_norm == "counter" else "special"
                    self.add_log(f"|move|{slot_tag}: {pkmn.nickname}|{reactive_name}|{target_side_id}{chr(97 + target_slot_idx)}")
                    from .battle_move_effects import _apply_reactive_damage
                    _apply_reactive_damage(
                        self,
                        side_id,
                        slot_idx,
                        target_side_id,
                        target_slot_idx,
                        target_to_hit,
                        move,
                        dmg,
                        damage_class,
                    )
                    return

                if move_name_norm == "pursuit":
                    peer_pending = any(
                        peer_action.get("type") == "switch"
                        for (peer_side_key, _peer_slot), peer_action in self.pending_actions.items()
                        if peer_side_key == ("p2" if side_id == "p1" else "p1")
                    )
                    if peer_pending:
                        move_power_override = max(1, int(move.power or 0) * 2)

                if target.substitute_hp > 0 and move.damage_class == "status":
                    move_effect_lower = move.effect.lower().replace("’", "'")
                    if "confuse" not in move_name_lower and "confuse" not in move_effect_lower:
                        self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|move: Substitute|[damage]")
                        continue

                if move_name_norm == "beatup":
                    num_hits = max(1, sum(1 for member in side.team if member.current_hp > 0))
                    move_power_override = 10
                else:
                    num_hits = 1 if is_struggle else get_hit_count(move)
                hits_landed = 0
                total_damage = 0
                
                if move.damage_class != "status":
                    for h in range(num_hits):
                        if target.current_hp <= 0: break
                        hits_landed += 1
                        crit_stage = 0
                        if pkmn.focus_energy:
                            crit_stage += 2
                        if move_is_high_critical(move):
                            crit_stage += 1
                        is_crit = determine_critical(crit_stage, defender_ability=target.ability)
                        hit_power_override = move_power_override
                        if move_name_norm == "triplekick":
                            hit_power_override = 10 * (h + 1)
                        damage, multiplier = calculate_damage(
                            pkmn,
                            target,
                            move,
                            is_crit,
                            battle_weather,
                            target.semi_invulnerable,
                            defending_side=self.sides[t_side_id],
                            attacking_side=self.sides[side_id],
                            power_override=hit_power_override,
                        )
                        if damage > 0 and helping_hand_consumed and move.damage_class != "status":
                            damage = max(1, math.floor(damage * 1.5))
                        if len(targets) > 1: damage = math.floor(damage * 0.5)
                        
                        if target.substitute_hp > 0:
                            target.substitute_hp = max(0, target.substitute_hp - damage)
                            self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|Substitute|[damage]")
                            if target.substitute_hp <= 0: self.add_log(f"|-end|{t_slot_tag}: {target.nickname}|Substitute")
                        else:
                            if target.endure_active and damage >= target.current_hp and target.current_hp > 1:
                                damage = target.current_hp - 1
                            target.current_hp = max(0, target.current_hp - damage)
                            target.last_damage_taken = damage
                            target.last_damage_class = move.damage_class
                            target.last_damage_move_type = move.type
                            target.last_damage_source_side = side_id
                            target.last_damage_source_slot = slot_idx
                            target.damage_taken_this_turn = max(target.damage_taken_this_turn, damage)
                            if target.bide_turns is not None and target.bide_turns > 0:
                                target.bide_damage += damage
                                target.bide_target_side = side_id
                                target.bide_target_slot = slot_idx
                            
                        if is_crit: self.add_log("|-crit|")
                        if h == 0:
                            if multiplier > 1: self.add_log("|-supereffective|")
                            elif 0 < multiplier < 1: self.add_log("|-resisted|")
                            elif multiplier == 0: self.add_log("|-immune|")
                        self.add_log(f"|damage|{t_slot_tag}: {target.nickname}|{self._condition(target)}")
                        if move_name_norm == "triplekick" and multiplier == 0:
                            break
                        if target.current_hp <= 0:
                            self.add_log(f"|faint|{t_slot_tag}: {target.nickname}")
                            if target.destiny_bond:
                                pkmn.current_hp = 0
                                self.add_log(f"|-activate|{t_slot_tag}: {target.nickname}|move: Destiny Bond")
                                self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                        total_damage += damage
                        if move_name_norm == "triplekick" and damage <= 0:
                            break
                    
                    if num_hits > 1:
                        self.add_log(f"|-hitcount|{t_slot_tag}: {target.nickname}|{hits_landed}")

                if target.substitute_hp <= 0 or move.damage_class == "status":
                    if is_struggle:
                        recoil = math.floor(pkmn.max_hp / 4)
                        pkmn.current_hp = max(0, pkmn.current_hp - recoil)
                        self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] recoil")
                        if pkmn.current_hp <= 0: self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                    else:
                        if move.damage_class == "status" and _is_snatchable_move(move, pkmn):
                            snatcher_info = next(
                                (
                                    (i, p_idx)
                                    for i, p_idx in enumerate(peer_side.active_indices)
                                    if peer_side.team[p_idx].current_hp > 0 and peer_side.team[p_idx].snatch_turns > 0
                                ),
                                None,
                            )
                            if snatcher_info is not None:
                                snatch_slot_idx, snatch_pkmn_idx = snatcher_info
                                snatch_pkmn = peer_side.team[snatch_pkmn_idx]
                                snatch_pkmn.snatch_turns = 0
                                snatch_tag = self._slot_tag(peer_side_id, snatch_slot_idx)
                                self.add_log(f"|-activate|{snatch_tag}: {snatch_pkmn.nickname}|move: Snatch")
                                apply_move_effects(self, snatch_pkmn, snatch_pkmn, move, total_damage, peer_side_id, move_index)
                                continue
                        apply_move_effects(self, pkmn, target, move, total_damage, side_id, move_index)

                if pkmn.lock_on_turns > 0 and move_name_norm not in {"lockon", "mindreader"}:
                    pkmn.lock_on_turns = 0

            if pkmn.lock_on_turns > 0 and move_name_norm not in {"lockon", "mindreader"}:
                pkmn.lock_on_turns = 0

            if helping_hand_consumed:
                pkmn.helping_hand_turns = 0

    def _can_pokemon_move(self, side_id: str, pkmn: BattlePokemon, slot_idx: int, move_name_norm: str | None = None) -> bool:
        slot_tag = f"{side_id}{chr(97 + slot_idx)}"
        
        if pkmn.must_recharge:
            pkmn.must_recharge = False
            self.add_log(f"|-mustrecharge|{slot_tag}: {pkmn.nickname}")
            return False

        if pkmn.is_flinching:
            if pkmn.ability == "inner-focus":
                pkmn.is_flinching = False
            else:
                self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|flinch")
                return False

        if pkmn.ability == "truant" and pkmn.truant_counter:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|truant")
            return False

        sleep_usable = move_name_norm in {"snore", "sleeptalk"}
        if pkmn.status_condition == "slp":
            uproar_active = any(p.uproar_turns > 0 for battle_side in self.sides.values() for p in battle_side.active_list)
            if uproar_active and pkmn.ability != "soundproof":
                pkmn.status_condition = None
                pkmn.status_turns = 0
                self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|slp")
            elif pkmn.status_turns > 0:
                to_sub = 2 if pkmn.ability == "early-bird" else 1
                pkmn.status_turns = max(0, pkmn.status_turns - to_sub)
                if pkmn.status_turns > 0:
                    if sleep_usable:
                        return True
                    self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|slp")
                    return False
                pkmn.status_condition = None
                self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|slp")
                if sleep_usable:
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

        if pkmn.attracted_to_side is not None and random.random() < 0.5:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|attract")
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

    def _process_end_turn_effects(self):
        if self.weather != "none":
            battle_weather = self._effective_weather()
            if not self._weather_suppressed():
                for side_id, side in self.sides.items():
                    for slot_idx, pkmn_idx in enumerate(side.active_indices):
                        p = side.team[pkmn_idx]
                        if p.current_hp <= 0:
                            continue
                        if battle_weather == "sandstorm" and "rock" not in p.types and "ground" not in p.types and "steel" not in p.types:
                            dmg = math.floor(p.max_hp / 16)
                            p.current_hp = max(0, p.current_hp - dmg)
                            self.add_log(f"|-damage|{side_id}{chr(97+slot_idx)}: {p.nickname}|{self._condition(p)}|[from] Sandstorm")
                        elif battle_weather == "hail" and "ice" not in p.types:
                            dmg = math.floor(p.max_hp / 16)
                            p.current_hp = max(0, p.current_hp - dmg)
                            self.add_log(f"|-damage|{side_id}{chr(97+slot_idx)}: {p.nickname}|{self._condition(p)}|[from] Hail")
            if self.weather_turns > 0:
                self.weather_turns -= 1
                if self.weather_turns == 0:
                    self.add_log("|-weather|none")
                    self.weather = "none"
                    self._update_weather_forms()

        self._check_and_use_items("end")

        for side_id, side in self.sides.items():
            for wish_slot in list(side.wish_turns.keys()):
                side.wish_turns[wish_slot] -= 1
                if side.wish_turns[wish_slot] <= 0:
                    heal_amount = side.wish_amounts.pop(wish_slot, 0)
                    side.wish_turns.pop(wish_slot, None)
                    if wish_slot < len(side.active_indices):
                        wish_target = side.team[side.active_indices[wish_slot]]
                        if wish_target.current_hp > 0 and heal_amount > 0:
                            wish_target.current_hp = min(wish_target.max_hp, wish_target.current_hp + heal_amount)
                            self.add_log(f"|-heal|{side_id}{chr(97 + wish_slot)}: {wish_target.nickname}|{self._condition(wish_target)}|[from] move: Wish")

            if side.future_sight_turns > 0:
                side.future_sight_turns -= 1
                if side.future_sight_turns == 0:
                    if side.future_sight_damage > 0:
                        target = side.active_pokemon
                        if target and target.current_hp > 0:
                            slot_tag = f"{side_id}a"
                            target.current_hp = max(0, target.current_hp - side.future_sight_damage)
                            self.add_log(f"|-damage|{slot_tag}: {target.nickname}|{self._condition(target)}|[from] move: Future Sight")
                            if target.current_hp <= 0:
                                self.add_log(f"|faint|{slot_tag}: {target.nickname}")
                    side.future_sight_damage = 0
                    side.future_sight_source_side = None

            for slot_idx, pkmn_idx in enumerate(side.active_indices):
                pkmn = side.team[pkmn_idx]
                if not pkmn or pkmn.current_hp <= 0: continue
                
                slot_tag = f"{side_id}{chr(97 + slot_idx)}"

                if pkmn.yawn_turns > 0:
                    pkmn.yawn_turns -= 1
                    if pkmn.yawn_turns == 0 and pkmn.current_hp > 0 and pkmn.status_condition is None:
                        self.set_status(pkmn, "slp", side_id)

                if pkmn.nightmare_active:
                    if pkmn.status_condition != "slp":
                        pkmn.nightmare_active = False
                    else:
                        dmg = max(1, math.floor(pkmn.max_hp / 4))
                        pkmn.current_hp = max(0, pkmn.current_hp - dmg)
                        self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: Nightmare")
                        if pkmn.current_hp <= 0:
                            self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")

                if pkmn.curse_active:
                    dmg = max(1, math.floor(pkmn.max_hp / 4))
                    pkmn.current_hp = max(0, pkmn.current_hp - dmg)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: Curse")
                    if pkmn.current_hp <= 0:
                        self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")

                if pkmn.ingrain and pkmn.current_hp > 0:
                    heal = max(1, math.floor(pkmn.max_hp / 16))
                    if pkmn.current_hp < pkmn.max_hp:
                        pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                        self.add_log(f"|-heal|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: Ingrain")

                if pkmn.ability == "rain-dish" and self._effective_weather() == "rain" and pkmn.current_hp > 0:
                    heal = max(1, math.floor(pkmn.max_hp / 16))
                    if pkmn.current_hp < pkmn.max_hp:
                        pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                        self.add_log(f"|-heal|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] ability: Rain Dish")

                if pkmn.status_condition == "tox":
                    toxic_turns = pkmn.toxic_turns if pkmn.toxic_turns > 0 else 1
                    dmg = max(1, math.floor(pkmn.max_hp * toxic_turns / 16))
                    pkmn.current_hp = max(0, pkmn.current_hp - dmg)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] tox")
                    pkmn.toxic_turns = min(toxic_turns + 1, 15)
                elif pkmn.status_condition == "psn":
                    dmg = math.floor(pkmn.max_hp / 8)
                    pkmn.current_hp = max(0, pkmn.current_hp - dmg)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] psn")
                elif pkmn.status_condition == "brn":
                    dmg = math.floor(pkmn.max_hp / 8)
                    pkmn.current_hp = max(0, pkmn.current_hp - dmg)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] brn")

                if pkmn.leech_seed_recipient is not None and pkmn.current_hp > 0:
                    drain = max(1, math.floor(pkmn.max_hp / 8))
                    pkmn.current_hp = max(0, pkmn.current_hp - drain)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: Leech Seed")
                    source_side = self.sides.get(pkmn.leech_seed_recipient)
                    source_pkmn = source_side.active_pokemon if source_side else None
                    if source_pkmn and source_pkmn.current_hp > 0:
                        if pkmn.ability == "liquid-ooze":
                            source_pkmn.current_hp = max(0, source_pkmn.current_hp - drain)
                            self.add_log(f"|-damage|{pkmn.leech_seed_recipient}a: {source_pkmn.nickname}|{self._condition(source_pkmn)}|[from] ability: Liquid Ooze")
                            if source_pkmn.current_hp <= 0:
                                self.add_log(f"|faint|{pkmn.leech_seed_recipient}a: {source_pkmn.nickname}")
                        else:
                            source_pkmn.current_hp = min(source_pkmn.max_hp, source_pkmn.current_hp + drain)
                            self.add_log(f"|-heal|{pkmn.leech_seed_recipient}a: {source_pkmn.nickname}|{self._condition(source_pkmn)}|[from] move: Leech Seed")

                if pkmn.partial_trap_turns > 0:
                    dmg = max(1, math.floor(pkmn.max_hp / 16))
                    pkmn.current_hp = max(0, pkmn.current_hp - dmg)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] {pkmn.partial_trap_name or 'partial-trap'}")
                    pkmn.partial_trap_turns -= 1
                    if pkmn.partial_trap_turns <= 0:
                        pkmn.partial_trap_turns = 0
                        pkmn.partial_trap_name = None
                        pkmn.trapped_by_side = None

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

                if pkmn.torment_turns > 0:
                    pkmn.torment_turns -= 1
                    if pkmn.torment_turns == 0:
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|move: Torment")

                if pkmn.uproar_turns > 0:
                    pkmn.uproar_turns -= 1
                    if pkmn.uproar_turns == 0:
                        pkmn.locked_move_index = None
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|move: Uproar")

                if pkmn.helping_hand_turns > 0:
                    pkmn.helping_hand_turns = 0

                if pkmn.follow_me_turns > 0:
                    pkmn.follow_me_turns = 0

                if pkmn.snatch_turns > 0:
                    pkmn.snatch_turns = 0

                if pkmn.ability == "speed-boost":
                    if pkmn.modify_stage("spe", 1) > 0:
                        self.add_log(f"|-ability|{slot_tag}: {pkmn.nickname}|Speed Boost")
                        self.add_log(f"|-boost|{slot_tag}: {pkmn.nickname}|spe|1")

                if pkmn.ability == "shed-skin" and pkmn.status_condition:
                    if random.random() < 0.33:
                        old_status = pkmn.status_condition
                        pkmn.status_condition = None
                        pkmn.toxic_turns = 0
                        self.add_log(f"|-ability|{slot_tag}: {pkmn.nickname}|Shed Skin")
                        self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|{old_status}")

                if pkmn.ability == "truant":
                    pkmn.truant_counter ^= 1

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

            if side.mist_turns > 0:
                side.mist_turns -= 1
                if side.mist_turns == 0:
                    self.add_log(f"|-sideend|{side_id}: {side.player_name}|move: Mist")

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

                pkmn.first_turn_on_field = False

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
                        pkmn.toxic_turns = 0
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

    def _random_metronome_move(self) -> BattleMove | None:
        candidates: list[int] = []
        for move_id, data in sorted(MOVE_COMBAT_DATA.items()):
            move_name = str(data.get("name") or "").lower().replace("-", "").replace(" ", "")
            if move_name in METRONOME_BANNED_MOVES:
                continue
            candidates.append(int(move_id))

        if not candidates:
            return None

        chosen = random.choice(candidates)
        return _build_move_from_data(int(chosen))

    def generate_request(self, player_id: str) -> dict[str, Any]:
        """Gera o request de batalha no formato esperado pelo router e pela UI."""
        if self.finished:
            return {}

        side_id = "p1" if self.sides["p1"].player_id == player_id else "p2"
        side = self.sides[side_id]
        force_switch_slots: list[bool] = []
        active_payloads: list[dict[str, Any]] = []
        uproar_active = any(p.uproar_turns > 0 for battle_side in self.sides.values() for p in battle_side.active_list)

        for slot_idx, pkmn_idx in enumerate(side.active_indices):
            active = side.team[pkmn_idx]
            slot_force_switch = (side_id, slot_idx) in self.force_switch_slots
            if active.current_hp <= 0 and side.has_available_pokemon(exclude_active=True):
                slot_force_switch = True

            force_switch_slots.append(slot_force_switch)

            moves: list[dict[str, Any]] = []
            if active.current_hp > 0 and not slot_force_switch:
                for idx, move in enumerate(active.moves):
                    disabled = False

                    sleep_locked = active.status_condition == "slp" and not (uproar_active and active.ability != "soundproof")
                    move_name_norm = _normalize_move_name(move.name)

                    if active.must_recharge or active.status_condition == "frz":
                        disabled = True
                    elif active.ability == "truant" and active.truant_counter:
                        disabled = True
                    elif active.locked_move_index is not None:
                        disabled = idx != active.locked_move_index
                    elif active.encore_turns > 0 and active.encore_move_index is not None:
                        disabled = idx != active.encore_move_index
                    else:
                        disabled = (
                            int(move.pp or 0) <= 0
                            or (active.disable_turns > 0 and active.disable_move_id == move.move_id)
                            or (active.taunt_turns > 0 and move.damage_class == "status" and move.move_id != -1)
                            or (active.torment_turns > 0 and active.last_move_id == move.move_id)
                            or (move_name_norm in {"snore", "sleeptalk"} and active.status_condition != "slp")
                            or (sleep_locked and move_name_norm not in {"snore", "sleeptalk"})
                            or (move_name_norm == "fakeout" and not active.first_turn_on_field)
                        )

                    move_name_norm = _normalize_move_name(move.name)
                    target_mode = _move_target_mode(move, active)
                    target_value = "normal"
                    if target_mode == "self":
                        target_value = "self"
                    elif target_mode == "ally":
                        target_value = "ally"
                    elif target_mode == "all_adjacent":
                        target_value = "allAdjacent"

                    if self.format != "doubles" and move_name_norm in DOUBLE_ONLY_MOVES:
                        disabled = True
                    if target_mode == "ally" and self._partner_active(side_id, slot_idx) is None:
                        disabled = True

                    moves.append(
                        {
                            "move": move.name,
                            "id": move.move_id,
                            "pp": int(move.pp or 0),
                            "maxpp": int(move.max_pp or 0),
                            "target": target_value,
                            "disabled": disabled,
                        }
                    )

            active_payloads.append(
                {
                    "slot": slot_idx,
                    "moves": moves,
                    "forceSwitch": slot_force_switch,
                    "active": active.current_hp > 0,
                    "condition": self._condition(active),
                }
            )

        return {
            "active": active_payloads,
            "forceSwitch": any(force_switch_slots),
            "forceSwitchSlots": force_switch_slots,
            "side": {
                "name": side.player_name,
                "id": side_id,
                "pokemon": [
                    {
                        "ident": f"{side_id}: {pokemon.nickname}",
                        "details": f"{pokemon.name}, L{pokemon.level}",
                        "condition": self._condition(pokemon),
                        "active": (index in side.active_indices),
                        "stats": {
                            "atk": pokemon.stats.atk,
                            "def": pokemon.stats.defen,
                            "spa": pokemon.stats.spa,
                            "spd": pokemon.stats.spd,
                            "spe": pokemon.stats.spe,
                        },
                        "moves": [move.name for move in pokemon.moves],
                        "baseAbility": pokemon.ability or "none",
                        "item": pokemon.item_data["name"] if pokemon.item_data else "none",
                        "pokeball": "pokeball",
                    }
                    for index, pokemon in enumerate(side.team)
                ],
            },
        }
