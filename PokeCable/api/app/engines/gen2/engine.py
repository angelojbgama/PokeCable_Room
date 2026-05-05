from __future__ import annotations

import copy
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any

from ...data.move_combat_data import MOVE_COMBAT_DATA, get_move_combat_data
from .damage import calculate_damage_gen2
from .models import BattleMoveGen2, PokemonGen2
from .utils import calculate_hit_gen2, determine_critical_gen2
from .types import get_type_multiplier_gen2, is_special_type_gen2

logger = logging.getLogger(__name__)


def _normalize_move_name(name: str) -> str:
    return name.lower().replace("-", "").replace(" ", "")


def _build_move_from_data(move_id: int) -> BattleMoveGen2 | None:
    data = get_move_combat_data(move_id)
    if not data:
        return None

    return BattleMoveGen2(
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
        high_crit="critical hit" in str(data.get("effect") or "").lower(),
        effect_chance=data.get("effect_chance"),
    )


def _build_move_from_name(move_name: str) -> BattleMoveGen2 | None:
    target_key = _normalize_move_name(move_name)
    for move_id, data in MOVE_COMBAT_DATA.items():
        if _normalize_move_name(str(data.get("name") or "")) == target_key:
            return _build_move_from_data(move_id)
    return None


def _random_metronome_move() -> BattleMoveGen2 | None:
    excluded = {
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
    }
    candidates = []
    for move_id, data in MOVE_COMBAT_DATA.items():
        if move_id > 251:
            continue
        if _normalize_move_name(str(data.get("name") or "")) in excluded:
            continue
        candidates.append(move_id)

    if not candidates:
        return None
    return _build_move_from_data(random.choice(candidates))


def _copy_move(move: BattleMoveGen2) -> BattleMoveGen2:
    return copy.deepcopy(move)


GEN2_SELF_TARGET_MOVES = {
    "agility",
    "batonpass",
    "conversion",
    "lightscreen",
    "moonlight",
    "reflect",
    "recover",
    "rest",
    "morningsun",
    "synthesis",
    "swordsdance",
    "milkdrink",
    "softboiled",
}

GEN2_STATUS_TARGET_MOVES = {
    "confuseray",
    "flash",
    "poisonpowder",
    "poisongas",
    "thunderwave",
    "toxic",
    "mudslap",
    "growl",
    "leer",
    "screech",
    "tailwhip",
}

GEN2_MAJOR_STATUS_BY_MOVE = {
    "poisonpowder": "psn",
    "poisongas": "psn",
    "thunderwave": "par",
    "toxic": "tox",
}

GEN2_STAT_RAISE_BY_MOVE = {
    "agility": ("spe", 2),
    "swordsdance": ("atk", 2),
}

GEN2_STAT_LOWER_BY_MOVE = {
    "flash": ("accuracy", -1),
    "mudslap": ("accuracy", -1),
    "growl": ("atk", -1),
    "leer": ("def", -1),
    "screech": ("def", -2),
    "tailwhip": ("def", -1),
}

GEN2_CONFUSION_MOVES = {"confuseray", "dynamicpunch"}
GEN2_FLINCH_MOVES = {"bite", "stomp", "headbutt", "rockslide", "hyperfang"}
GEN2_DRAIN_MOVES = {"absorb", "megadrain", "gigadrain", "leechlife"}
GEN2_RECOIL_MOVES = {"takedown", "doubleedge", "submission", "jumpkick", "highjumpkick", "struggle"}
GEN2_TRAP_MOVES = {"wrap", "bind", "firespin", "clamp", "whirlpool"}
GEN2_BIDE_MOVES = {"bide"}
GEN2_COUNTER_MOVES = {"counter"}
GEN2_MIRROR_COAT_MOVES = {"mirrorcoat"}
GEN2_DISABLE_MOVES = {"disable"}
GEN2_ENCORE_MOVES = {"encore"}
GEN2_LEECH_SEED_MOVES = {"leechseed"}
GEN2_MIMIC_MOVES = {"mimic"}
GEN2_MIRROR_MOVE_MOVES = {"mirrormove"}
GEN2_METRONOME_MOVES = {"metronome"}
GEN2_TRANSFORM_MOVES = {"transform"}
GEN2_CONVERSION_MOVES = {"conversion"}
GEN2_RAGE_MOVES = {"rage"}
GEN2_WEATHER_MOVES = {"raindance", "sunnyday", "sandstorm"}
GEN2_CHARGE_MOVES = {"fly", "dig", "razorwind", "solarbeam", "skyattack", "skullbash"}
GEN2_CALL_MOVE_NAMES = {"metronome", "sleeptalk"}
GEN2_SLEEP_ALLOWED_MOVES = {"sleeptalk", "snore"}
GEN2_HEAL_BY_WEATHER_MOVES = {"morningsun", "synthesis", "moonlight"}
GEN2_DIRECT_SEMI_INVULN_HITS = {
    "earthquake",
    "magnitude",
    "fissure",
    "gust",
    "twister",
    "thunder",
    "whirlwind",
}
GEN2_RECHARGE_MOVES = {"hyperbeam"}
GEN2_FIXED_DAMAGE_MOVES = {"seismictoss", "nightshade", "sonicboom", "dragonrage", "psywave", "guillotine", "horndrill", "fissure", "sheercold"}
GEN2_SEMI_INVULN_MOVES = {"fly", "dig"}
GEN2_STRUGGLE_MOVE = BattleMoveGen2(
    move_id=0,
    name="Struggle",
    type="typeless",
    power=50,
    accuracy=100,
    pp=1,
    max_pp=1,
    priority=0,
    damage_class="physical",
)


@dataclass(slots=True)
class BattleSideGen2:
    player_id: str
    player_name: str
    team: list[PokemonGen2] = field(default_factory=list)
    active_index: int = 0
    reflect_turns: int = 0
    light_screen_turns: int = 0

    @property
    def active_pokemon(self) -> PokemonGen2 | None:
        if 0 <= self.active_index < len(self.team):
            return self.team[self.active_index]
        return None


class BattleEngineGen2:
    def __init__(self, battle_id: str, side1: BattleSideGen2, side2: BattleSideGen2):
        self.battle_id = battle_id
        self.sides = {"p1": side1, "p2": side2}
        self.turn = 0
        self.finished = False
        self.logs: list[str] = []
        self.pending_actions: dict[str, dict[str, Any]] = {}
        self.force_switch_player: str | None = None
        self.weather: str | None = None
        self.weather_turns: int = 0

    def add_log(self, log: str) -> None:
        self.logs.append(log)
        logger.debug("Gen2 Battle %s: %s", self.battle_id, log)

    def start_battle(self) -> None:
        self.add_log("|init|battle")
        for side_id, side in self.sides.items():
            self.add_log(f"|player|{side_id}|{side.player_name}")
            for pkmn in side.team:
                self.add_log(f"|poke|{side_id}|{pkmn.name}, L{pkmn.level}")
        self.add_log("|start|")
        self._switch_in("p1", 0)
        self._switch_in("p2", 0)

    def _switch_in(self, side_id: str, index: int) -> None:
        side = self.sides[side_id]
        side.active_index = index
        pkmn = side.active_pokemon
        if not pkmn:
            return

        pkmn.is_flinching = False
        pkmn.toxic_n = 1
        pkmn.stat_stages = {k: 0 for k in pkmn.stat_stages}
        pkmn.clear_volatile_state()
        self.add_log(f"|switch|{side_id}a: {pkmn.nickname}|{pkmn.name}, L{pkmn.level}|{self._condition(pkmn)}")

    def _condition(self, pkmn: PokemonGen2) -> str:
        status = pkmn.status_condition.upper() if pkmn.status_condition else ""
        return f"{pkmn.current_hp}/{pkmn.max_hp}{' ' + status if status else ''}"

    def _move_index_by_id(self, pkmn: PokemonGen2, move_id: int | None) -> int | None:
        if move_id is None:
            return None
        for index, move in enumerate(pkmn.moves):
            if move.move_id == move_id:
                return index
        return None

    def _has_usable_move(self, pkmn: PokemonGen2, *, ignore_move_id: int | None = None) -> bool:
        for move in pkmn.moves:
            if ignore_move_id is not None and move.move_id == ignore_move_id:
                continue
            if move.pp > 0 and not self._move_is_locked(pkmn, move):
                return True
        return False

    def _start_weather(self, weather: str, move_name: str) -> bool:
        if weather == "sand" and self.weather == "sand":
            self.add_log("|-fail|")
            return False
        self.weather = weather
        self.weather_turns = 5
        self.add_log(f"|-fieldstart|weather|{move_name}")
        return True

    def _move_hits_semi_invulnerable(self, move_key: str, target: PokemonGen2) -> bool:
        if not target.semi_invulnerable:
            return True

        if target.semi_invulnerable == "dig":
            return move_key in {"earthquake", "magnitude", "fissure"}
        if target.semi_invulnerable == "fly":
            return move_key in {"gust", "twister", "thunder", "whirlwind"}
        return False

    def _apply_weather_damage_and_timers(self) -> None:
        if self.weather and self.weather_turns > 0:
            self.weather_turns -= 1
            if self.weather_turns <= 0:
                self.add_log(f"|-fieldend|weather|{self.weather}")
                self.weather = None

    def _weather_damage_multiplier(self, move_type: str) -> float:
        if self.weather == "rain":
            if move_type == "water":
                return 1.5
            if move_type == "fire":
                return 0.5
        if self.weather == "sun":
            if move_type == "fire":
                return 1.5
            if move_type == "water":
                return 0.5
        return 1.0

    def _apply_confusion_damage(self, side_id: str, pkmn: PokemonGen2) -> None:
        slot_tag = f"{side_id}a"
        confusion_move = BattleMoveGen2(
            move_id=0,
            name="Confusion",
            type="typeless",
            power=40,
            accuracy=100,
            pp=1,
            max_pp=1,
            priority=0,
            damage_class="physical",
        )
        damage, _ = calculate_damage_gen2(pkmn, pkmn, confusion_move, False, random_factor=255)
        damage = max(1, damage)
        pkmn.current_hp = max(0, pkmn.current_hp - damage)
        self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] confusion")
        if pkmn.current_hp <= 0:
            self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
            self.force_switch_player = self.sides[side_id].player_id

    def _apply_major_status(self, target: PokemonGen2, side_id: str, status: str, move_name: str) -> bool:
        slot_tag = f"{side_id}a"

        if target.substitute_hp > 0:
            return False

        major_statuses = {"brn", "psn", "tox", "par", "slp", "frz"}
        if target.status_condition in major_statuses:
            return False

        if status in {"psn", "tox"} and any(type_name in {"poison", "steel"} for type_name in target.types):
            return False
        if status == "par" and ("electric" in target.types or "ground" in target.types):
            return False
        if status == "brn" and "fire" in target.types:
            return False
        if status == "frz" and "ice" in target.types:
            return False

        target.status_condition = status
        if status == "slp":
            target.status_turns = random.randint(2, 8)
        elif status == "tox":
            target.toxic_n = 1
        self.add_log(f"|-status|{slot_tag}: {target.nickname}|{status}|[from] move: {move_name}")
        return True

    def _apply_stat_stage(self, target: PokemonGen2, side_id: str, stat_name: str, amount: int, move_name: str) -> bool:
        slot_tag = f"{side_id}a"
        delta = target.modify_stage(stat_name, amount)
        if delta == 0:
            return False
        direction = "up" if delta > 0 else "down"
        self.add_log(f"|-boost|{slot_tag}: {target.nickname}|{stat_name}|{direction}|[from] move: {move_name}")
        return True

    def _use_move(self, pkmn: PokemonGen2, move_index: int) -> BattleMoveGen2:
        move = pkmn.moves[move_index]
        if move.pp <= 0:
            return GEN2_STRUGGLE_MOVE
        move.pp = max(0, move.pp - 1)
        return move

    def _move_is_locked(self, pkmn: PokemonGen2, move: BattleMoveGen2) -> bool:
        move_key = _normalize_move_name(move.name)
        if pkmn.encore_turns > 0 and pkmn.encore_move_id is not None:
            if move.move_id != pkmn.encore_move_id:
                return True
        if pkmn.disable_turns > 0 and pkmn.disable_move_id is not None:
            if move.move_id == pkmn.disable_move_id:
                return True
        if pkmn.charging_move_index is not None and pkmn.charging_turns > 0:
            if move_key not in GEN2_SLEEP_ALLOWED_MOVES:
                return True
        return False

    def _tick_move_locks(self, pkmn: PokemonGen2) -> None:
        if pkmn.disable_turns > 0:
            pkmn.disable_turns = max(0, pkmn.disable_turns - 1)
            if pkmn.disable_turns == 0:
                pkmn.disable_move_id = None
        if pkmn.encore_turns > 0:
            pkmn.encore_turns = max(0, pkmn.encore_turns - 1)
            if pkmn.encore_turns == 0:
                pkmn.encore_move_id = None

    def _apply_direct_damage(
        self,
        side_id: str,
        attacker: PokemonGen2,
        target: PokemonGen2,
        move: BattleMoveGen2,
        damage: int,
        *,
        damage_class: str | None = None,
    ) -> int:
        if damage <= 0 or target.current_hp <= 0:
            return 0

        peer_side_id = "p2" if side_id == "p1" else "p1"
        target.current_hp = max(0, target.current_hp - damage)
        target.last_damage_taken = damage
        target.last_damage_class = damage_class or move.damage_class
        if target.bide_turns is not None:
            target.bide_damage += damage
        if target.rage_active:
            delta = target.modify_stage("atk", 1)
            if delta:
                self.add_log(f"|-boost|{peer_side_id}a: {target.nickname}|atk|up|[from] move: Rage")
        self.add_log(f"|damage|{peer_side_id}a: {target.nickname}|{self._condition(target)}")
        if target.current_hp <= 0:
            self.add_log(f"|faint|{peer_side_id}a: {target.nickname}")
            self.force_switch_player = self.sides[peer_side_id].player_id
        return damage

    def _record_last_move(self, pkmn: PokemonGen2, move: BattleMoveGen2) -> None:
        pkmn.last_move_id = move.move_id
        pkmn.last_move_name = move.name

    def _copy_target_move_into_slot(self, pkmn: PokemonGen2, target_move: BattleMoveGen2) -> bool:
        for index, move in enumerate(pkmn.moves):
            if _normalize_move_name(move.name) == "mimic":
                copied = _copy_move(target_move)
                copied.pp = min(5, max(1, copied.pp))
                copied.max_pp = copied.pp
                pkmn.moves[index] = copied
                return True
        return False

    def _maybe_handle_sleep_turn(self, pkmn: PokemonGen2, move_key: str, side_id: str) -> bool:
        slot_tag = f"{side_id}a"
        if pkmn.status_condition != "slp":
            return False

        pkmn.status_turns -= 1
        if pkmn.status_turns <= 0:
            pkmn.status_condition = None
            self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|slp|[msg]")
            return False

        if move_key in GEN2_SLEEP_ALLOWED_MOVES:
            return True

        self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|slp")
        return False

    def _resolve_status_move(
        self,
        side_id: str,
        pkmn: PokemonGen2,
        target: PokemonGen2 | None,
        move: BattleMoveGen2,
        move_key: str,
    ) -> bool:
        peer_side_id = "p2" if side_id == "p1" else "p1"

        if move_key in GEN2_SELF_TARGET_MOVES:
            if move_key == "recover":
                heal = max(1, pkmn.max_hp // 2)
                pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                self.add_log(f"|-heal|{side_id}a: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: {move.name}")
                return True
            if move_key in {"milkdrink", "softboiled"}:
                heal = max(1, pkmn.max_hp // 2)
                pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                self.add_log(f"|-heal|{side_id}a: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: {move.name}")
                return True
            if move_key in GEN2_HEAL_BY_WEATHER_MOVES:
                if self.weather == "sun":
                    heal_ratio = 2 / 3
                elif self.weather in {"rain", "sand"}:
                    heal_ratio = 1 / 4
                else:
                    heal_ratio = 1 / 2
                heal = max(1, math.floor(pkmn.max_hp * heal_ratio))
                pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                self.add_log(f"|-heal|{side_id}a: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: {move.name}")
                return True
            if move_key == "rest":
                pkmn.current_hp = pkmn.max_hp
                pkmn.status_condition = "slp"
                pkmn.status_turns = 2
                self.add_log(f"|-status|{side_id}a: {pkmn.nickname}|slp|[from] move: {move.name}")
                self.add_log(f"|-heal|{side_id}a: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: {move.name}")
                return True
            if move_key in GEN2_STAT_RAISE_BY_MOVE:
                stat_name, amount = GEN2_STAT_RAISE_BY_MOVE[move_key]
                return self._apply_stat_stage(pkmn, side_id, stat_name, amount, move.name)
            if move_key == "conversion":
                if not pkmn.moves:
                    return False
                candidates = [candidate for candidate in pkmn.moves if candidate.type != "typeless"]
                if not candidates:
                    return False
                chosen = random.choice(candidates)
                pkmn.types = [chosen.type]
                self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
                return True
            if move_key == "lightscreen":
                self.sides[side_id].light_screen_turns = 5
                self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
                return True
            if move_key == "reflect":
                self.sides[side_id].reflect_turns = 5
                self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
                return True
            if move_key == "batonpass":
                self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
                return True
            return False

        if move_key in GEN2_WEATHER_MOVES:
            if move_key == "raindance":
                return self._start_weather("rain", move.name)
            if move_key == "sunnyday":
                return self._start_weather("sun", move.name)
            if move_key == "sandstorm":
                return self._start_weather("sand", move.name)
            return False

        if move_key in GEN2_DISABLE_MOVES:
            if not target or target.disable_turns > 0 or target.disable_move_id is not None:
                return False
            if target.last_move_id is None or target.last_move_name in GEN2_CALL_MOVE_NAMES or target.last_move_name == "struggle":
                return False
            target.disable_move_id = target.last_move_id
            target.disable_turns = random.randint(1, 7)
            disabled_name = target.last_move_name or "move"
            self.add_log(f"|-activate|{peer_side_id}a: {target.nickname}|move: Disable|[of] {disabled_name}")
            return True

        if move_key in GEN2_ENCORE_MOVES:
            if not target or target.encore_turns > 0:
                return False
            if target.last_move_id is None or target.last_move_name in GEN2_CALL_MOVE_NAMES or target.last_move_name == "struggle":
                return False
            target.encore_move_id = target.last_move_id
            target.encore_turns = random.randint(2, 6)
            self.add_log(f"|-activate|{peer_side_id}a: {target.nickname}|move: Encore")
            return True

        if move_key in GEN2_LEECH_SEED_MOVES:
            if not target or target.leech_seeded or target.substitute_hp > 0:
                return False
            if any(type_name == "grass" for type_name in target.types):
                return False
            target.leech_seeded = True
            target.leech_seed_source_side = side_id
            self.add_log(f"|-start|{peer_side_id}a: {target.nickname}|move: Leech Seed")
            return True

        if move_key in GEN2_MIMIC_MOVES:
            if not target or target.last_move_id is None or target.last_move_name in GEN2_CALL_MOVE_NAMES or target.last_move_name == "struggle":
                return False
            source_move = _build_move_from_data(target.last_move_id)
            if source_move is None:
                return False
            if not self._copy_target_move_into_slot(pkmn, source_move):
                return False
            self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
            return True

        if move_key in GEN2_MIRROR_MOVE_MOVES:
            if not target or target.last_move_id is None or target.last_move_name in GEN2_CALL_MOVE_NAMES or target.last_move_name == "struggle":
                return False
            copied_move = _build_move_from_data(target.last_move_id)
            if copied_move is None:
                return False
            self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
            return self._execute_generated_move(side_id, pkmn, target, copied_move)

        if move_key in GEN2_METRONOME_MOVES:
            copied_move = _random_metronome_move()
            if copied_move is None:
                return False
            self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
            return self._execute_generated_move(side_id, pkmn, target, copied_move)

        if move_key == "sleeptalk":
            if pkmn.status_condition != "slp":
                return False
            candidates = [
                candidate
                for candidate in pkmn.moves
                if candidate.move_id != move.move_id and candidate.pp > 0 and not self._move_is_locked(pkmn, candidate)
            ]
            if not candidates:
                return False
            chosen = random.choice(candidates)
            self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
            return self._execute_generated_move(side_id, pkmn, target, chosen)

        if move_key in GEN2_TRANSFORM_MOVES:
            if not target:
                return False
            pkmn.types = list(target.types)
            pkmn.stats = copy.deepcopy(target.stats)
            pkmn.base_speed = target.base_speed
            copied_moves = []
            for target_move in target.moves[:4]:
                copied = _copy_move(target_move)
                copied.pp = 5
                copied.max_pp = 5
                copied_moves.append(copied)
            if copied_moves:
                pkmn.moves = copied_moves
            self.add_log(f"|-transform|{side_id}a: {pkmn.nickname}|{peer_side_id}a: {target.nickname}")
            return True

        if move_key in GEN2_CONVERSION_MOVES:
            if not pkmn.moves:
                return False
            candidates = [candidate for candidate in pkmn.moves if candidate.type not in {"typeless"}]
            if not candidates:
                return False
            chosen = random.choice(candidates)
            pkmn.types = [chosen.type]
            self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
            return True

        if move_key in GEN2_COUNTER_MOVES:
            if pkmn.last_damage_taken <= 0 or pkmn.last_damage_class != "physical":
                return False
            raw_damage = pkmn.last_damage_taken * 2
            multiplier = get_type_multiplier_gen2("fighting", target.types if target else [])
            if multiplier <= 0:
                self.add_log(f"|-immune|{peer_side_id}a: {target.nickname if target else 'target'}")
                return True
            if target is None:
                return False
            damage = max(1, math.floor(raw_damage * multiplier))
            reflected = BattleMoveGen2(
                move_id=0,
                name=move.name,
                type="fighting",
                power=1,
                accuracy=100,
                pp=1,
                max_pp=1,
                priority=0,
                damage_class="physical",
            )
            self._apply_direct_damage(side_id, pkmn, target, reflected, damage, damage_class="physical")
            return True

        if move_key in GEN2_MIRROR_COAT_MOVES:
            if pkmn.last_damage_taken <= 0 or pkmn.last_damage_class != "special":
                return False
            raw_damage = pkmn.last_damage_taken * 2
            multiplier = get_type_multiplier_gen2("psychic", target.types if target else [])
            if multiplier <= 0:
                self.add_log(f"|-immune|{peer_side_id}a: {target.nickname if target else 'target'}")
                return True
            if target is None:
                return False
            damage = max(1, math.floor(raw_damage * multiplier))
            reflected = BattleMoveGen2(
                move_id=0,
                name=move.name,
                type="psychic",
                power=1,
                accuracy=100,
                pp=1,
                max_pp=1,
                priority=0,
                damage_class="special",
            )
            self._apply_direct_damage(side_id, pkmn, target, reflected, damage, damage_class="special")
            return True

        if move_key in GEN2_BIDE_MOVES:
            if pkmn.bide_turns is None:
                pkmn.bide_turns = 2
                pkmn.bide_damage = 0
                self.add_log(f"|-prepare|{side_id}a: {pkmn.nickname}|move: {move.name}")
                return True
            if pkmn.bide_turns <= 0:
                if target is None or pkmn.bide_damage <= 0:
                    return False
                damage = max(1, pkmn.bide_damage * 2)
                bide_move = BattleMoveGen2(
                    move_id=0,
                    name=move.name,
                    type="typeless",
                    power=1,
                    accuracy=100,
                    pp=1,
                    max_pp=1,
                    priority=0,
                    damage_class="physical",
                )
                self._apply_direct_damage(side_id, pkmn, target, bide_move, damage, damage_class="physical")
                pkmn.bide_turns = None
                pkmn.bide_damage = 0
                return True
            return False

        if move_key in GEN2_STATUS_TARGET_MOVES:
            if not target:
                return False
            if target.substitute_hp > 0:
                return False
            if move_key == "confuseray":
                target.is_confused = True
                target.confusion_turns = random.randint(2, 5)
                self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")
                return True
            if move_key in {"sing", "sleeppowder"}:
                return self._apply_major_status(target, peer_side_id, "slp", move.name)
            if move_key in GEN2_MAJOR_STATUS_BY_MOVE:
                if move_key == "poisonpowder" and any(type_name in {"grass", "poison", "steel"} for type_name in target.types):
                    return False
                return self._apply_major_status(target, peer_side_id, GEN2_MAJOR_STATUS_BY_MOVE[move_key], move.name)
            if move_key in GEN2_STAT_LOWER_BY_MOVE:
                stat_name, amount = GEN2_STAT_LOWER_BY_MOVE[move_key]
                return self._apply_stat_stage(target, peer_side_id, stat_name, amount, move.name)

        if move_key in GEN2_SELF_TARGET_MOVES:
            return False

        return False

    def _execute_generated_move(
        self,
        side_id: str,
        pkmn: PokemonGen2,
        target: PokemonGen2 | None,
        move: BattleMoveGen2,
        *,
        forced_charge_complete: bool = False,
    ) -> bool:
        move_key = _normalize_move_name(move.name)
        if move.damage_class == "status":
            return self._resolve_status_move(side_id, pkmn, target, move, move_key)
        return self._resolve_damage_move(
            side_id,
            pkmn,
            target,
            move,
            move_key,
            forced_charge_complete=forced_charge_complete,
            record_last_move=False,
        )

    def _resolve_damage_move(
        self,
        side_id: str,
        pkmn: PokemonGen2,
        target: PokemonGen2 | None,
        move: BattleMoveGen2,
        move_key: str,
        *,
        forced_charge_complete: bool = False,
        move_index: int | None = None,
        record_last_move: bool = True,
    ) -> bool:
        peer_side_id = "p2" if side_id == "p1" else "p1"
        if not target:
            return False

        if not forced_charge_complete and move_key in GEN2_CHARGE_MOVES:
            if move_key == "solarbeam" and self.weather == "sun":
                forced_charge_complete = True
            else:
                if move_key == "skullbash":
                    self._apply_stat_stage(pkmn, side_id, "def", 1, move.name)
                if move_key in GEN2_SEMI_INVULN_MOVES:
                    pkmn.semi_invulnerable = move_key
                pkmn.charging_move_index = move_index
                pkmn.charging_turns = 1
                pkmn.charging_move_name = move.name
                self.add_log(f"|-prepare|{side_id}a: {pkmn.nickname}|move: {move.name}")
                return True

        previous_rollout = pkmn.rollout_turns
        previous_fury_cutter = pkmn.fury_cutter_turns
        previous_move_id = pkmn.last_move_id
        if record_last_move:
            self._record_last_move(pkmn, move)

        power_override: int | None = None
        if move_key == "rollout":
            if previous_move_id == move.move_id and previous_rollout > 0:
                pkmn.rollout_turns = min(5, previous_rollout + 1)
            else:
                pkmn.rollout_turns = 1
            power_override = max(1, move.power) * (2 ** (pkmn.rollout_turns - 1))
        elif previous_rollout > 0:
            pkmn.rollout_turns = 0

        if move_key == "furycutter":
            if previous_move_id == move.move_id and previous_fury_cutter > 0:
                pkmn.fury_cutter_turns = min(5, previous_fury_cutter + 1)
            else:
                pkmn.fury_cutter_turns = 1
            power_override = max(1, move.power) * (2 ** (pkmn.fury_cutter_turns - 1))
        elif previous_fury_cutter > 0:
            pkmn.fury_cutter_turns = 0

        if move_key == "magnitude":
            power_override = random.choice([10, 30, 50, 70, 90, 110, 150])

        accuracy = move.accuracy
        if move_key == "thunder" and self.weather == "rain":
            accuracy = 100

        if target.semi_invulnerable:
            if not self._move_hits_semi_invulnerable(move_key, target):
                self.add_log(f"|-miss|{side_id}a: {pkmn.nickname}|{peer_side_id}a: {target.nickname}")
                return False

        if accuracy is not None and accuracy > 0:
            if not calculate_hit_gen2(
                accuracy,
                pkmn.stat_stages["accuracy"],
                target.stat_stages["evasion"],
            ):
                self.add_log(f"|-miss|{side_id}a: {pkmn.nickname}|{peer_side_id}a: {target.nickname}")
                return False

        is_crit = determine_critical_gen2(crit_stage=1 if move.high_crit else 0)
        if is_crit:
            self.add_log("|-crit|")

        damage, mult = calculate_damage_gen2(
            pkmn,
            target,
            move,
            is_crit,
            weather=self.weather,
            power_override=power_override,
        )

        if mult == 0:
            self.add_log(f"|-immune|{peer_side_id}a: {target.nickname}")
            return False

        if move_key == "falseswipe" and damage >= target.current_hp:
            damage = max(0, target.current_hp - 1)

        if not is_crit:
            if is_special_type_gen2(move.type) and self.sides[peer_side_id].light_screen_turns > 0:
                damage = max(1, math.floor(damage / 2)) if damage > 0 else 0
            elif not is_special_type_gen2(move.type) and self.sides[peer_side_id].reflect_turns > 0:
                damage = max(1, math.floor(damage / 2)) if damage > 0 else 0

        if damage <= 0:
            if forced_charge_complete or move_key in GEN2_CHARGE_MOVES or move_key in GEN2_SEMI_INVULN_MOVES:
                pkmn.semi_invulnerable = None
                pkmn.charging_move_index = None
                pkmn.charging_turns = 0
                pkmn.charging_move_name = None
            return False

        self._apply_direct_damage(side_id, pkmn, target, move, damage)
        self._apply_post_damage_effects(side_id, pkmn, target, move, move_key, damage, is_crit)

        if move_key == "rage":
            pkmn.rage_active = True

        if move_key == "rapidspin":
            pkmn.is_trapped = False
            pkmn.trap_turns = 0
            pkmn.leech_seeded = False
            pkmn.leech_seed_source_side = None
            self.add_log(f"|-activate|{side_id}a: {pkmn.nickname}|move: {move.name}")

        if move_key in GEN2_SEMI_INVULN_MOVES or forced_charge_complete or move_key in {"razorwind", "solarbeam", "skyattack", "skullbash"}:
            pkmn.semi_invulnerable = None
            pkmn.charging_move_index = None
            pkmn.charging_turns = 0
            pkmn.charging_move_name = None

        if move_key in GEN2_RECHARGE_MOVES:
            pkmn.must_recharge = True

        return True

    def _apply_post_damage_effects(
        self,
        side_id: str,
        pkmn: PokemonGen2,
        target: PokemonGen2,
        move: BattleMoveGen2,
        move_key: str,
        damage: int,
        is_crit: bool,
    ) -> None:
        peer_side_id = "p2" if side_id == "p1" else "p1"
        if damage > 0 and target.current_hp > 0:
            if move_key in GEN2_CONFUSION_MOVES and target.current_hp > 0:
                if move.effect_chance is None or random.random() < (move.effect_chance / 100):
                    target.is_confused = True
                    target.confusion_turns = random.randint(2, 5)
                    self.add_log(f"|-activate|{peer_side_id}a: {target.nickname}|confusion")

            if move_key in GEN2_FLINCH_MOVES and move.effect_chance is not None:
                if random.random() < (move.effect_chance / 100):
                    target.is_flinching = True
                    self.add_log(f"|-flinch|{peer_side_id}a: {target.nickname}")

            if move_key in {"firepunch", "ember", "flamethrower", "fireblast", "sacredfire"}:
                if target.status_condition is None and random.random() < ((move.effect_chance or 0) / 100):
                    self._apply_major_status(target, peer_side_id, "brn", move.name)
            elif move_key in {"icepunch", "icebeam", "blizzard", "powdersnow"}:
                if target.status_condition is None and random.random() < ((move.effect_chance or 0) / 100):
                    self._apply_major_status(target, peer_side_id, "frz", move.name)
            elif move_key in {"thunderpunch", "thundershock", "thunderbolt", "thunder", "bodyslam", "lick", "dragonbreath"}:
                if target.status_condition is None and random.random() < ((move.effect_chance or 0) / 100):
                    self._apply_major_status(target, peer_side_id, "par", move.name)
            elif move_key in {"poisonsting", "smog", "sludge"}:
                if target.status_condition is None and random.random() < ((move.effect_chance or 0) / 100):
                    self._apply_major_status(target, peer_side_id, "psn", move.name)

            if move_key == "mudslap":
                self._apply_stat_stage(target, peer_side_id, "accuracy", -1, move.name)

            if move_key in GEN2_DRAIN_MOVES:
                heal = max(1, damage // 2)
                pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                self.add_log(f"|-heal|{side_id}a: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: {move.name}")

            if move_key in GEN2_RECOIL_MOVES:
                recoil = max(1, damage // 4)
                pkmn.current_hp = max(0, pkmn.current_hp - recoil)
                self.add_log(f"|-damage|{side_id}a: {pkmn.nickname}|{self._condition(pkmn)}|[from] recoil")
                if pkmn.current_hp <= 0:
                    self.add_log(f"|faint|{side_id}a: {pkmn.nickname}")
                    self.force_switch_player = self.sides[side_id].player_id

            if move_key in GEN2_TRAP_MOVES:
                target.is_trapped = True
                target.trap_turns = random.randint(2, 5)
                self.add_log(f"|-activate|{peer_side_id}a: {target.nickname}|move: {move.name}")

    def submit_action(self, player_id: str, action: dict[str, Any]) -> None:
        if self.sides["p1"].player_id == player_id:
            side_id = "p1"
        elif self.sides["p2"].player_id == player_id:
            side_id = "p2"
        else:
            return

        if self.force_switch_player == player_id:
            if action["type"] == "switch":
                self._switch_in(side_id, action["index"])
                self.force_switch_player = None
                return

        pkmn = self.sides[side_id].active_pokemon
        if action.get("type") == "switch" and pkmn and pkmn.is_trapped:
            self.add_log(f"|cant|{side_id}a: {pkmn.nickname}|trap")
            return

        self.pending_actions[side_id] = action

        if len(self.pending_actions) == 2:
            self._resolve_turn()

    def _resolve_turn(self) -> None:
        self.turn += 1
        self.add_log(f"|turn|{self.turn}")

        actions = []
        for side_id, action in self.pending_actions.items():
            pkmn = self.sides[side_id].active_pokemon
            priority = 0
            if action["type"] == "move":
                move = pkmn.moves[action["move_index"]]
                priority = move.priority

            speed = pkmn.get_modified_stat("spe")
            actions.append(
                {
                    "side_id": side_id,
                    "action": action,
                    "priority": priority,
                    "speed": speed,
                    "random": random.random(),
                }
            )

        actions.sort(key=lambda x: (x["priority"], x["speed"], x["random"]), reverse=True)

        for act in actions:
            if self.finished:
                break
            self._execute_action(act["side_id"], act["action"])
            self._check_win_condition()

        if not self.finished:
            self._resolve_end_turn_effects()
            self._check_win_condition()

        self.pending_actions = {}

    def _can_pokemon_move(self, side_id: str, pkmn: PokemonGen2, move_key: str | None = None) -> bool:
        slot_tag = f"{side_id}a"

        if pkmn.is_trapped and pkmn.trap_turns > 0:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|trap")
            return False

        if pkmn.status_condition == "slp":
            pkmn.status_turns -= 1
            if pkmn.status_turns <= 0:
                pkmn.status_condition = None
                self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|slp|[msg]")
                return True
            if move_key in GEN2_SLEEP_ALLOWED_MOVES:
                return True
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|slp")
            return False

        if move_key in GEN2_SLEEP_ALLOWED_MOVES:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|slp")
            return False

        if pkmn.status_condition == "frz":
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|frz")
            return False

        if pkmn.status_condition == "par":
            if random.random() < 0.25:
                self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|par")
                return False

        if pkmn.is_flinching:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|flinch")
            pkmn.is_flinching = False
            return False

        if pkmn.is_confused:
            self.add_log(f"|-activate|{slot_tag}: {pkmn.nickname}|confusion")
            if random.random() < 0.5:
                self._apply_confusion_damage(side_id, pkmn)
                pkmn.confusion_turns -= 1
                if pkmn.confusion_turns <= 0:
                    pkmn.is_confused = False
                    pkmn.confusion_turns = 0
                    self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|confusion")
                return False

            pkmn.confusion_turns -= 1
            if pkmn.confusion_turns <= 0:
                pkmn.is_confused = False
                pkmn.confusion_turns = 0
                self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|confusion")

        if pkmn.must_recharge:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|recharge")
            pkmn.must_recharge = False
            return False

        return True

    def _resolve_end_turn_effects(self) -> None:
        for side_id, side in self.sides.items():
            pkmn = side.active_pokemon
            if not pkmn or pkmn.current_hp <= 0:
                continue

            slot_tag = f"{side_id}a"

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

            if pkmn.leech_seeded and pkmn.current_hp > 0 and pkmn.status_condition != "frz":
                drain = max(1, math.floor(pkmn.max_hp / 8))
                pkmn.current_hp = max(0, pkmn.current_hp - drain)
                self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: Leech Seed")
                if pkmn.current_hp <= 0:
                    self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                    self.force_switch_player = side.player_id

                source_side_id = pkmn.leech_seed_source_side
                if source_side_id and source_side_id in self.sides:
                    source_side = self.sides[source_side_id]
                    source_pkmn = source_side.active_pokemon
                    if source_pkmn and source_pkmn.current_hp > 0:
                        source_pkmn.current_hp = min(source_pkmn.max_hp, source_pkmn.current_hp + drain)
                        self.add_log(f"|-heal|{source_side_id}a: {source_pkmn.nickname}|{self._condition(source_pkmn)}|[from] move: Leech Seed")

            if pkmn.item_data and not pkmn.consumed_item:
                item = pkmn.item_data
                if item.get("effect_type") == "cure_status" and pkmn.status_condition:
                    pkmn.status_condition = None
                    pkmn.consumed_item = True
                    self.add_log(f"|-activate|{slot_tag}: {pkmn.nickname}|item: {item['name']}")
                elif item.get("effect_type") == "heal_threshold":
                    threshold = float(item.get("threshold", 0))
                    if pkmn.current_hp > 0 and pkmn.current_hp <= math.floor(pkmn.max_hp * threshold):
                        heal = max(1, int(item.get("value", 0)))
                        pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                        pkmn.consumed_item = True
                        self.add_log(f"|-heal|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] item: {item['name']}")
                elif item.get("effect_type") == "heal_end_turn":
                    heal = max(1, math.floor(pkmn.max_hp * float(item.get("value", 0))))
                    pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                    self.add_log(f"|-heal|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] item: {item['name']}")

            if pkmn.is_trapped:
                trap_damage = max(1, math.floor(pkmn.max_hp / 8))
                pkmn.current_hp = max(0, pkmn.current_hp - trap_damage)
                self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: binding")
                if pkmn.current_hp <= 0:
                    self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                    self.force_switch_player = side.player_id
                pkmn.trap_turns -= 1
                if pkmn.trap_turns <= 0:
                    pkmn.is_trapped = False
                    pkmn.trap_turns = 0
                    self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|trap")

            if side.reflect_turns > 0:
                side.reflect_turns -= 1
                if side.reflect_turns == 0:
                    self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|reflect")

            if side.light_screen_turns > 0:
                side.light_screen_turns -= 1
                if side.light_screen_turns == 0:
                    self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|lightscreen")

            if self.weather == "sand" and pkmn.semi_invulnerable != "dig":
                if not any(type_name in {"rock", "ground", "steel"} for type_name in pkmn.types):
                    sand_damage = max(1, math.floor(pkmn.max_hp / 8))
                    pkmn.current_hp = max(0, pkmn.current_hp - sand_damage)
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] Sandstorm")
                    if pkmn.current_hp <= 0:
                        self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                        self.force_switch_player = side.player_id

        self._apply_weather_damage_and_timers()

    def _execute_action(self, side_id: str, action: dict[str, Any]) -> None:
        pkmn = self.sides[side_id].active_pokemon
        if not pkmn or pkmn.current_hp <= 0:
            return

        if action["type"] == "switch":
            if pkmn.is_trapped:
                self.add_log(f"|cant|{side_id}a: {pkmn.nickname}|trap")
                return
            self._switch_in(side_id, action["index"])
            return

        if action["type"] != "move":
            return

        peer_side_id = "p2" if side_id == "p1" else "p1"
        target = self.sides[peer_side_id].active_pokemon
        if not target or target.current_hp <= 0:
            return

        move_idx = action["move_index"]
        forced_charge_complete = False
        if pkmn.bide_turns is not None:
            if pkmn.bide_turns > 1:
                pkmn.bide_turns -= 1
                self.add_log(f"|-prepare|{side_id}a: {pkmn.nickname}|move: Bide")
                return
            if pkmn.bide_damage <= 0:
                pkmn.bide_turns = None
                pkmn.bide_damage = 0
                return
            bide_move = BattleMoveGen2(
                move_id=0,
                name="Bide",
                type="typeless",
                power=1,
                accuracy=100,
                pp=1,
                max_pp=1,
                priority=0,
                damage_class="physical",
            )
            self.add_log(f"|move|{side_id}a: {pkmn.nickname}|Bide|{peer_side_id}a")
            self._apply_direct_damage(side_id, pkmn, target, bide_move, max(1, pkmn.bide_damage * 2), damage_class="physical")
            pkmn.last_move_id = bide_move.move_id
            pkmn.last_move_name = bide_move.name
            pkmn.bide_turns = None
            pkmn.bide_damage = 0
            return

        if pkmn.charging_move_name and pkmn.charging_turns > 0:
            move_idx = pkmn.charging_move_index if pkmn.charging_move_index is not None else move_idx
            move = _build_move_from_name(pkmn.charging_move_name)
            if move is None:
                pkmn.charging_move_index = None
                pkmn.charging_turns = 0
                pkmn.charging_move_name = None
                return
            forced_charge_complete = True
        else:
            if move_idx < 0 or move_idx >= len(pkmn.moves):
                return
            move = pkmn.moves[move_idx]

            if pkmn.encore_turns > 0 and pkmn.encore_move_id is not None:
                encore_idx = self._move_index_by_id(pkmn, pkmn.encore_move_id)
                if encore_idx is not None:
                    move_idx = encore_idx
                    move = pkmn.moves[encore_idx]

            if self._move_is_locked(pkmn, move):
                if not self._has_usable_move(pkmn, ignore_move_id=move.move_id):
                    move = GEN2_STRUGGLE_MOVE
                    move_idx = None
                else:
                    self.add_log(f"|cant|{side_id}a: {pkmn.nickname}|{move.name}")
                    return
            elif move.pp <= 0:
                if not self._has_usable_move(pkmn):
                    move = GEN2_STRUGGLE_MOVE
                    move_idx = None
                else:
                    self.add_log(f"|cant|{side_id}a: {pkmn.nickname}|{move.name}")
                    return

        if not forced_charge_complete and move is not GEN2_STRUGGLE_MOVE and move_idx is not None:
            move = self._use_move(pkmn, move_idx)

        move_key = _normalize_move_name(move.name)
        if not self._can_pokemon_move(side_id, pkmn, move_key):
            return

        self._tick_move_locks(pkmn)
        self.add_log(f"|move|{side_id}a: {pkmn.nickname}|{move.name}|{peer_side_id}a")

        resolved = False
        if move.damage_class == "status" or move_key in GEN2_MIRROR_COAT_MOVES:
            resolved = self._resolve_status_move(side_id, pkmn, target, move, move_key)
            if not resolved:
                self.add_log(f"|-fail|{side_id}a: {pkmn.nickname}|{move.name}")
        else:
            resolved = self._resolve_damage_move(
                side_id,
                pkmn,
                target,
                move,
                move_key,
                forced_charge_complete=forced_charge_complete,
                move_index=move_idx,
            )

        pkmn.last_move_id = move.move_id
        pkmn.last_move_name = move.name
        return

    def _check_win_condition(self) -> None:
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

        if not pkmn:
            return {}

        forced_move_key = None
        if pkmn.charging_move_name and pkmn.charging_turns > 0:
            forced_move_key = _normalize_move_name(pkmn.charging_move_name)

        moves = []
        for m in pkmn.moves:
            move_key = _normalize_move_name(m.name)
            disabled = m.pp <= 0 or self._move_is_locked(pkmn, m)
            if pkmn.must_recharge:
                disabled = True
            if pkmn.status_condition == "frz":
                disabled = True
            if pkmn.status_condition == "slp" and move_key not in GEN2_SLEEP_ALLOWED_MOVES:
                disabled = True
            if forced_move_key is not None:
                disabled = move_key != forced_move_key
            moves.append(
                {
                    "move": m.name,
                    "id": m.move_id,
                    "pp": m.pp,
                    "maxpp": m.max_pp,
                    "target": "normal",
                    "disabled": disabled,
                }
            )

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
                        "stats": {
                            "atk": p.stats.atk,
                            "def": p.stats.defen,
                            "spa": p.stats.spa,
                            "spd": p.stats.spd,
                            "spe": p.stats.spe,
                        },
                        "moves": [m.name for m in p.moves],
                        "baseAbility": "none",
                        "item": p.item_data["name"] if p.item_data else "none",
                        "pokeball": "pokeball",
                    }
                    for i, p in enumerate(side.team)
                ],
            },
        }
