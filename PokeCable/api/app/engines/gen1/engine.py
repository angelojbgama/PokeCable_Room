from __future__ import annotations

import copy
import logging
import math
import random
import re
from dataclasses import dataclass, field
from typing import Any

from ...data.move_combat_data import MOVE_COMBAT_DATA, get_move_combat_data
from .damage import calculate_damage_gen1
from .models import BattleMoveGen1, PokemonGen1
from .types import get_type_multiplier_gen1
from .utils import calculate_hit_gen1, determine_critical_gen1

logger = logging.getLogger(__name__)


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _build_move_from_data(move_id: int) -> BattleMoveGen1 | None:
    data = get_move_combat_data(move_id)
    if not data:
        return None

    effect = str(data.get("effect") or "")
    is_high_crit = "critical hit" in effect.lower()
    return BattleMoveGen1(
        move_id=int(move_id),
        name=str(data["name"]),
        type=str(data["type"]),
        power=int(data["power"]) if data.get("power") is not None else None,
        accuracy=int(data["accuracy"]) if data.get("accuracy") is not None else None,  # type: ignore[arg-type]
        pp=int(data["pp"]),
        max_pp=int(data["pp"]),
        priority=int(data.get("priority") or 0),
        damage_class=str(data["damage_class"]),
        effect_chance=int(data["effect_chance"]) if data.get("effect_chance") is not None else None,
        effect=effect,
        high_crit=is_high_crit,
    )


def _random_metronome_move() -> BattleMoveGen1 | None:
    candidates = []
    excluded = {
        "metronome",
        "mimic",
        "mirror move",
        "mirrormove",
        "struggle",
    }
    for move_id, data in MOVE_COMBAT_DATA.items():
        if move_id > 165:
            continue
        move_key = _normalize_key(str(data.get("name") or ""))
        if move_key in excluded:
            continue
        candidates.append(move_id)

    if not candidates:
        return None
    return _build_move_from_data(random.choice(candidates))


def _copy_move(move: BattleMoveGen1) -> BattleMoveGen1:
    return copy.deepcopy(move)


GEN1_SELF_TARGET_MOVES = {
    "swordsdance",
    "growth",
    "meditate",
    "agility",
    "harden",
    "barrier",
    "amnesia",
    "acidarmor",
    "sharpen",
    "withdraw",
    "defensecurl",
    "doubleteam",
    "minimize",
    "recover",
    "softboiled",
    "rest",
    "haze",
    "reflect",
    "lightscreen",
    "mist",
    "focusenergy",
    "bide",
    "metronome",
    "mimic",
    "mirrormove",
    "transform",
    "conversion",
    "substitute",
    "splash",
    "teleport",
    "disable",
    "leechseed",
    "roar",
    "whirlwind",
}

GEN1_MULTI_HIT_MOVES = {
    "doubleslap": (2, 5),
    "cometpunch": (2, 5),
    "furyattack": (2, 5),
    "pinmissile": (2, 5),
    "furyswipes": (2, 5),
    "barrage": (2, 5),
    "spikecannon": (2, 5),
    "doublekick": (2, 2),
    "twineedle": (2, 2),
    "bonemerang": (2, 2),
}

GEN1_CHARGE_MOVES = {
    "razorwind",
    "solarbeam",
    "skyattack",
    "skullbash",
    "fly",
    "dig",
}

GEN1_LOCK_MOVES = {"thrash", "petaldance"}
GEN1_RECHARGE_MOVES = {"hyperbeam"}
GEN1_BIDE_MOVES = {"bide"}
GEN1_COUNTER_MOVES = {"counter"}
GEN1_RAGE_MOVES = {"rage"}
GEN1_METRONOME_MOVES = {"metronome"}
GEN1_MIMIC_MOVES = {"mimic"}
GEN1_MIRROR_MOVE = {"mirrormove"}
GEN1_TRANSFORM_MOVES = {"transform"}
GEN1_CONVERSION_MOVES = {"conversion"}
GEN1_DISABLE_MOVES = {"disable"}
GEN1_LEECH_SEED_MOVES = {"leechseed"}
GEN1_SUBSTITUTE_MOVES = {"substitute"}
GEN1_RECOVERY_MOVES = {"recover", "softboiled", "rest"}
GEN1_SIDE_EFFECT_MOVES = {"reflect", "lightscreen", "mist"}
GEN1_HAZE_MOVES = {"haze"}
GEN1_FORCE_SWITCH_MOVES = {"roar", "whirlwind"}
GEN1_FOCUS_ENERGY_MOVES = {"focusenergy"}
GEN1_STATUS_INFLICTING_TARGET_MOVES = {
    "sing",
    "sleeppowder",
    "hypnosis",
    "spore",
    "lovelykiss",
    "thunderwave",
    "glare",
    "poisonpowder",
    "poisongas",
    "toxic",
    "poisonsting",
    "smog",
    "sludge",
}
GEN1_DRAIN_MOVES = {"absorb", "megadrain", "leechlife", "dreameater"}
GEN1_RECOIL_MOVES = {"takedown", "doubleedge", "submission", "jumpkick", "highjumpkick", "struggle"}
GEN1_FIXED_DAMAGE_MOVES = {
    "guillotine",
    "horndrill",
    "fissure",
    "seismictoss",
    "nightshade",
    "sonicboom",
    "dragonrage",
    "superfang",
    "psywave",
}
GEN1_OHKO_MOVES = {"guillotine", "horndrill", "fissure"}
GEN1_STATUS_EFFECT_BY_MOVE = {
    "thunderwave": "par",
    "sing": "slp",
    "sleeppowder": "slp",
    "hypnosis": "slp",
    "spore": "slp",
    "lovelykiss": "slp",
    "glare": "par",
    "poisonpowder": "psn",
    "poisongas": "psn",
    "toxic": "tox",
    "poisonsting": "psn",
    "smog": "psn",
    "sludge": "psn",
    "firepunch": "brn",
    "ember": "brn",
    "flamethrower": "brn",
    "fireblast": "brn",
    "icepunch": "frz",
    "icebeam": "frz",
    "blizzard": "frz",
    "powdersnow": "frz",
    "thundershock": "par",
    "thunderbolt": "par",
    "thunder": "par",
    "thunderpunch": "par",
    "lick": "par",
    "bodyslam": "par",
    "triattack": "triattack",
}
GEN1_CONFUSION_EFFECT_MOVES = {"supersonic", "confuseray", "psybeam", "dizzypunch", "confusion"}
GEN1_FLINCH_EFFECT_MOVES = {"bite", "stomp", "headbutt", "rockslide", "hyperfang", "skyattack"}
GEN1_STAT_BOOSTS = {
    "swordsdance": [("atk", 2)],
    "growth": [("special", 1)],
    "meditate": [("atk", 1)],
    "agility": [("spe", 2)],
    "harden": [("def", 1)],
    "barrier": [("def", 2)],
    "amnesia": [("special", 2)],
    "acidarmor": [("def", 2)],
    "sharpen": [("atk", 1)],
    "withdraw": [("def", 1)],
    "defensecurl": [("def", 1)],
    "doubleteam": [("evasion", 1)],
    "minimize": [("evasion", 2)],
}
GEN1_STAT_DROPS = {
    "tailwhip": [("def", 1)],
    "leer": [("def", 1)],
    "growl": [("atk", 1)],
    "sandattack": [("accuracy", 1)],
    "stringshot": [("spe", 1)],
    "screech": [("def", 2)],
    "smokescreen": [("accuracy", 1)],
    "kinesis": [("accuracy", 1)],
    "flash": [("accuracy", 1)],
    "constrict": [("spe", 1)],
    "bubble": [("spe", 1)],
    "bubblebeam": [("spe", 1)],
    "aurorabeam": [("atk", 1)],
    "acid": [("special", 1)],
}


@dataclass
class BattleSideGen1:
    player_id: str
    player_name: str
    team: list[PokemonGen1] = field(default_factory=list)
    active_index: int = 0
    reflect_turns: int = 0
    light_screen_turns: int = 0
    mist_turns: int = 0

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
        self.pending_actions: dict[str, dict[str, Any]] = {}
        self.force_switch_player: str | None = None

    def add_log(self, log: str) -> None:
        self.logs.append(log)
        logger.debug("Gen1 Battle %s: %s", self.battle_id, log)

    def start_battle(self) -> None:
        self.add_log("|init|battle")
        for side_id, side in self.sides.items():
            self.add_log(f"|player|{side_id}|{side.player_name}")
            for pkmn in side.team:
                self.add_log(f"|poke|{side_id}|{pkmn.name}, L{pkmn.level}")
        self.add_log("|start|")
        self._switch_in("p1", 0)
        self._switch_in("p2", 0)

    def _condition(self, pkmn: PokemonGen1) -> str:
        status = pkmn.status_condition.upper() if pkmn.status_condition else ""
        return f"{pkmn.current_hp}/{pkmn.max_hp}{' ' + status if status else ''}"

    def _switch_in(self, side_id: str, index: int) -> None:
        side = self.sides[side_id]
        previous = side.active_pokemon
        if previous is not None and side.active_index != index:
            previous.on_switch_out()

        side.active_index = index
        pkmn = side.active_pokemon
        if not pkmn:
            return

        pkmn.is_flinching = False
        pkmn.semi_invulnerable = None
        pkmn.trap_turns = 0
        pkmn.is_trapped = False
        pkmn.partial_trap_damage = 0
        pkmn.substitute_hp = 0
        pkmn.leech_seeded = False
        pkmn.leech_seed_source_side = None
        pkmn.disable_move_id = None
        pkmn.disable_turns = 0
        pkmn.must_recharge = False
        pkmn.rage_active = False
        pkmn.rage_hits = 0
        pkmn.locked_move_index = None
        pkmn.locked_turns = 0
        pkmn.charging_move_index = None
        pkmn.charging_turns = 0
        pkmn.charging_move_name = None
        pkmn.focus_energy = False
        pkmn.bide_turns = None
        pkmn.bide_damage = 0
        pkmn.is_transformed = False
        pkmn.transformed_from_name = None
        pkmn.toxic_n = 1
        pkmn.clear_battle_modifiers()

        self.add_log(f"|switch|{side_id}a: {pkmn.nickname}|{pkmn.name}, L{pkmn.level}|{self._condition(pkmn)}")

    def submit_action(self, player_id: str, action: dict[str, Any]) -> None:
        if self.finished:
            return

        if self.sides["p1"].player_id == player_id:
            side_id = "p1"
        elif self.sides["p2"].player_id == player_id:
            side_id = "p2"
        else:
            return

        if self.force_switch_player == player_id and action.get("type") != "switch":
            return

        if self.force_switch_player == player_id and action.get("type") == "switch":
            self._switch_in(side_id, int(action["index"]))
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
            if not pkmn or pkmn.current_hp <= 0:
                continue

            priority = 0
            if action["type"] == "move":
                move = pkmn.moves[int(action["move_index"])]
                priority = move.priority

            actions.append(
                {
                    "side_id": side_id,
                    "action": action,
                    "priority": priority,
                    "speed": pkmn.get_modified_stat("spe"),
                    "random": random.random(),
                }
            )

        actions.sort(key=lambda item: (item["priority"], item["speed"], item["random"]), reverse=True)

        for entry in actions:
            if self.finished:
                break
            self._execute_action(entry["side_id"], entry["action"])
            self._check_win_condition()

        if not self.finished:
            self._resolve_end_turn_effects()
            self._check_win_condition()

        self.pending_actions = {}

    def _can_pokemon_move(self, side_id: str, pkmn: PokemonGen1) -> bool:
        slot_tag = f"{side_id}a"

        if pkmn.is_trapped and pkmn.trap_turns > 0:
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|trap")
            return False

        if pkmn.status_condition == "slp":
            pkmn.status_turns -= 1
            if pkmn.status_turns <= 0:
                pkmn.status_condition = None
                pkmn.status_turns = 0
                self.add_log(f"|-curestatus|{slot_tag}: {pkmn.nickname}|slp|[msg]")
            else:
                self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|slp")
            return False

        if pkmn.status_condition == "frz":
            self.add_log(f"|cant|{slot_tag}: {pkmn.nickname}|frz")
            return False

        if pkmn.status_condition == "par" and random.random() < 0.25:
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

    def _apply_confusion_damage(self, side_id: str, pkmn: PokemonGen1) -> None:
        slot_tag = f"{side_id}a"
        confuse_move = BattleMoveGen1(0, "Confusion", "typeless", 40, 100, 1, 1, 0, "physical")
        damage, _ = calculate_damage_gen1(pkmn, pkmn, confuse_move, False)
        if damage <= 0:
            damage = 1

        pkmn.current_hp = max(0, pkmn.current_hp - damage)
        pkmn.last_damage_taken = damage
        pkmn.last_damage_class = "self"
        self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] confusion")
        if pkmn.current_hp <= 0:
            self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
            self.force_switch_player = self.sides[side_id].player_id

    def _apply_major_status(
        self,
        target: PokemonGen1,
        target_side_id: str,
        status: str,
        move_name: str,
        move_type: str,
        *,
        sleep_turns: int | None = None,
    ) -> bool:
        slot_tag = f"{target_side_id}a"

        if target.substitute_hp > 0:
            return False

        if get_type_multiplier_gen1(move_type, target.types) == 0:
            return False

        if status in {"psn", "tox"} and "poison" in target.types:
            return False
        if status == "par" and "electric" in target.types:
            return False
        if status == "brn" and "fire" in target.types:
            return False
        if status == "frz" and "ice" in target.types:
            return False
        if status == "slp" and target.status_condition == "slp":
            return False
        if target.status_condition in {"brn", "psn", "tox", "par", "slp", "frz"}:
            return False

        if status == "par":
            target.status_condition = "par"
            target.status_turns = 0
        elif status == "brn":
            target.status_condition = "brn"
        elif status == "psn":
            target.status_condition = "psn"
        elif status == "tox":
            target.status_condition = "tox"
            target.toxic_n = 1
        elif status == "frz":
            target.status_condition = "frz"
        elif status == "slp":
            target.status_condition = "slp"
            target.status_turns = sleep_turns if sleep_turns is not None else random.randint(1, 7)
        else:
            return False

        self.add_log(f"|-status|{slot_tag}: {target.nickname}|{target.status_condition}|[from] move: {move_name}")
        return True

    def _apply_stat_delta(self, side_id: str, pkmn: PokemonGen1, stat: str, amount: int) -> bool:
        side = self.sides[side_id]
        if amount < 0 and side.mist_turns > 0:
            return False

        delta = pkmn.modify_stage(stat, amount)
        slot_tag = f"{side_id}a"
        if delta > 0:
            self.add_log(f"|-boost|{slot_tag}: {pkmn.nickname}|{stat}|{delta}")
            return True
        if delta < 0:
            self.add_log(f"|-unboost|{slot_tag}: {pkmn.nickname}|{stat}|{abs(delta)}")
            return True
        return False

    def _apply_status_move(self, side_id: str, move: BattleMoveGen1, move_key: str, attacker: PokemonGen1, target: PokemonGen1, target_side_id: str) -> None:
        if move_key in GEN1_SELF_TARGET_MOVES:
            if move_key in GEN1_STAT_BOOSTS:
                for stat, amount in GEN1_STAT_BOOSTS[move_key]:
                    self._apply_stat_delta(side_id, attacker, stat, amount)
            if move_key == "focusenergy":
                attacker.focus_energy = True
                return

            if move_key in GEN1_RECOVERY_MOVES:
                if move_key == "rest":
                    attacker.current_hp = attacker.max_hp
                    attacker.status_condition = "slp"
                    attacker.status_turns = 2
                    attacker.clear_volatile_state()
                    attacker.status_condition = "slp"
                    attacker.status_turns = 2
                    self.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{self._condition(attacker)}|[from] move: Rest")
                    return

                heal = max(1, attacker.max_hp // 2)
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal)
                self.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{self._condition(attacker)}|[from] move: {move.name}")
                return

            if move_key in GEN1_SIDE_EFFECT_MOVES:
                side = self.sides[side_id]
                turns = 5
                if move_key == "reflect":
                    if side.reflect_turns > 0:
                        self.add_log("|-fail|")
                        return
                    side.reflect_turns = turns
                    self.add_log(f"|-sidestart|{side_id}: {side.player_name}|move: Reflect")
                elif move_key == "lightscreen":
                    if side.light_screen_turns > 0:
                        self.add_log("|-fail|")
                        return
                    side.light_screen_turns = turns
                    self.add_log(f"|-sidestart|{side_id}: {side.player_name}|move: Light Screen")
                elif move_key == "mist":
                    if side.mist_turns > 0:
                        self.add_log("|-fail|")
                        return
                    side.mist_turns = turns
                    self.add_log(f"|-sidestart|{side_id}: {side.player_name}|move: Mist")
                return

            if move_key in GEN1_HAZE_MOVES:
                for s in self.sides.values():
                    if s.active_pokemon:
                        s.active_pokemon.stat_stages = {k: 0 for k in s.active_pokemon.stat_stages}
                        s.active_pokemon.is_confused = False
                        s.active_pokemon.confusion_turns = 0
                        s.active_pokemon.focus_energy = False
                        s.active_pokemon.locked_move_index = None
                        s.active_pokemon.locked_turns = 0
                        s.active_pokemon.charging_move_index = None
                        s.active_pokemon.charging_turns = 0
                        s.active_pokemon.charging_move_name = None
                        s.active_pokemon.rage_active = False
                self.add_log(f"|-fieldstart|{side_id}: {self.sides[side_id].player_name}|move: Haze")
                return

            if move_key in GEN1_SUBSTITUTE_MOVES:
                cost = max(1, attacker.max_hp // 4)
                if attacker.current_hp <= cost or attacker.substitute_hp > 0:
                    self.add_log("|-fail|")
                    return
                attacker.current_hp -= cost
                attacker.substitute_hp = cost
                self.add_log(f"|-start|{side_id}a: {attacker.nickname}|Substitute")
                return

            if move_key in GEN1_METRONOME_MOVES:
                generated = _random_metronome_move()
                if not generated:
                    self.add_log("|-fail|")
                    return
                self.add_log(f"|-activate|{side_id}a: {attacker.nickname}|move: Metronome|[into] {generated.name}")
                self._execute_concrete_move(side_id, generated, attacker, target, target_side_id, forced=True)
                return

            if move_key in GEN1_MIMIC_MOVES:
                copied = target.last_move_id
                if not copied:
                    self.add_log("|-fail|")
                    return
                copied_move = _build_move_from_data(copied)
                if not copied_move:
                    self.add_log("|-fail|")
                    return
                if attacker.moves:
                    attacker.moves[0] = _copy_move(copied_move)
                    self.add_log(f"|-activate|{side_id}a: {attacker.nickname}|move: Mimic|[move] {copied_move.name}")
                else:
                    self.add_log("|-fail|")
                return

            if move_key in GEN1_MIRROR_MOVE:
                copied = target.last_move_id
                if not copied:
                    self.add_log("|-fail|")
                    return
                copied_move = _build_move_from_data(copied)
                if not copied_move or _normalize_key(copied_move.name) in GEN1_MIRROR_MOVE:
                    self.add_log("|-fail|")
                    return
                self.add_log(f"|-activate|{side_id}a: {attacker.nickname}|move: Mirror Move|[into] {copied_move.name}")
                self._execute_concrete_move(side_id, copied_move, attacker, target, target_side_id, forced=True)
                return

            if move_key in GEN1_TRANSFORM_MOVES:
                if target.current_hp <= 0:
                    self.add_log("|-fail|")
                    return
                attacker.types = copy.deepcopy(target.types)
                attacker.stats = copy.deepcopy(target.stats)
                attacker.base_speed = target.base_speed
                attacker.stat_stages = copy.deepcopy(target.stat_stages)
                attacker.moves = [_copy_move(m) for m in target.moves]
                attacker.is_transformed = True
                attacker.transformed_from_name = target.name
                self.add_log(f"|-transform|{side_id}a: {attacker.nickname}|{target.name}")
                return

            if move_key in GEN1_CONVERSION_MOVES:
                if not attacker.moves:
                    self.add_log("|-fail|")
                    return
                move_types = []
                for m in attacker.moves:
                    if m.type:
                        move_types.append(m.type)
                if not move_types:
                    self.add_log("|-fail|")
                    return
                chosen = random.choice(move_types)
                attacker.types = [chosen]
                self.add_log(f"|-transform|{side_id}a: {attacker.nickname}|{chosen}")
                return

            if move_key == "teleport":
                self.add_log("|-fail|")
                return

            if move_key == "bide":
                if attacker.bide_turns is None:
                    attacker.bide_turns = 2
                    attacker.bide_damage = 0
                    self.add_log(f"|-start|{side_id}a: {attacker.nickname}|Bide")
                    return
                if attacker.bide_turns > 1:
                    attacker.bide_turns -= 1
                    self.add_log(f"|move|{side_id}a: {attacker.nickname}|Bide|{side_id}a|[still]")
                    return
                stored_damage = max(1, attacker.bide_damage * 2)
                attacker.bide_turns = None
                attacker.bide_damage = 0
                self.add_log(f"|move|{side_id}a: {attacker.nickname}|Bide|{target_side_id}a")
                self._apply_direct_damage(side_id, attacker, target_side_id, target, stored_damage, "Bide", "physical", ignore_type=False)
                return

            if move_key == "focusenergy":
                attacker.focus_energy = True
                self.add_log(f"|-start|{side_id}a: {attacker.nickname}|focusenergy")
                return

            if move_key in GEN1_DISABLE_MOVES:
                if not target.last_move_id:
                    self.add_log("|-fail|")
                    return
                target.disable_move_id = target.last_move_id
                # O turno em que Disable foi usado nao deve consumir a duracao inteira.
                target.disable_turns = random.randint(1, 8) + 1
                self.add_log(f"|-start|{target_side_id}a: {target.nickname}|Disable|[of] {move.name}")
                return

            if move_key in GEN1_LEECH_SEED_MOVES:
                if "grass" in target.types or target.substitute_hp > 0:
                    self.add_log("|-fail|")
                    return
                if target.leech_seeded:
                    self.add_log("|-fail|")
                    return
                target.leech_seeded = True
                target.leech_seed_source_side = side_id
                self.add_log(f"|-start|{target_side_id}a: {target.nickname}|move: Leech Seed")
                return

            if move_key == "roar" or move_key == "whirlwind":
                self.force_switch_player = self.sides[target_side_id].player_id
                self.add_log(f"|-forceswitch|{target_side_id}a: {target.nickname}|[from] move: {move.name}")
                return

            if move_key == "splash":
                return

        if move_key in GEN1_STAT_DROPS:
            for stat, amount in GEN1_STAT_DROPS[move_key]:
                self._apply_stat_delta(target_side_id, target, stat, -amount)
            return

        if move_key in GEN1_STATUS_INFLICTING_TARGET_MOVES:
            status = GEN1_STATUS_EFFECT_BY_MOVE.get(move_key)
            if status == "triattack":
                if target.substitute_hp > 0:
                    return
                possible = ["brn", "frz", "par"]
                random.shuffle(possible)
                for candidate in possible:
                    if self._apply_major_status(target, target_side_id, candidate, move.name, move.type):
                        return
                return
            if status and self._apply_major_status(target, target_side_id, status, move.name, move.type):
                return
            return

        if move_key in GEN1_CONFUSION_EFFECT_MOVES:
            if target.substitute_hp > 0:
                return
            if get_type_multiplier_gen1(move.type, target.types) == 0:
                return
            if target.is_confused:
                return
            target.is_confused = True
            target.confusion_turns = random.randint(1, 4)
            self.add_log(f"|-start|{target_side_id}a: {target.nickname}|confusion")
            return

        if move_key in GEN1_FORCE_SWITCH_MOVES:
            self.force_switch_player = self.sides[target_side_id].player_id
            self.add_log(f"|-forceswitch|{target_side_id}a: {target.nickname}|[from] move: {move.name}")
            return

    def _apply_move_secondary_effects(
        self,
        side_id: str,
        target_side_id: str,
        attacker: PokemonGen1,
        target: PokemonGen1,
        move: BattleMoveGen1,
        damage: int,
        move_key: str,
        was_critical: bool,
    ) -> None:
        if damage <= 0:
            return

        if move_key in GEN1_STATUS_EFFECT_BY_MOVE and move_key not in {"triattack"}:
            status = GEN1_STATUS_EFFECT_BY_MOVE[move_key]
            if move.effect_chance and random.randint(1, 100) <= int(move.effect_chance):
                self._apply_major_status(target, target_side_id, status, move.name, move.type)

        if move_key in GEN1_CONFUSION_EFFECT_MOVES and move.effect_chance:
            if random.randint(1, 100) <= int(move.effect_chance):
                if not target.is_confused:
                    target.is_confused = True
                    target.confusion_turns = random.randint(1, 4)
                    self.add_log(f"|-start|{target_side_id}a: {target.nickname}|confusion")

        if move_key in GEN1_FLINCH_EFFECT_MOVES and move.effect_chance:
            if random.randint(1, 100) <= int(move.effect_chance):
                target.is_flinching = True

        if move_key in GEN1_DRAIN_MOVES:
            if move_key == "dreameater" and target.status_condition != "slp":
                return
            heal_amount = max(1, damage // 2)
            attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
            self.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{self._condition(attacker)}|[from] drain")

        if move_key in GEN1_RECOIL_MOVES:
            if move_key == "struggle":
                recoil = max(1, attacker.max_hp // 4)
            elif move_key == "doubleedge":
                recoil = max(1, damage // 3)
            else:
                recoil = max(1, damage // 4)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            self.add_log(f"|-damage|{side_id}a: {attacker.nickname}|{self._condition(attacker)}|[from] recoil")
            if attacker.current_hp <= 0:
                self.add_log(f"|faint|{side_id}a: {attacker.nickname}")
                self.force_switch_player = self.sides[side_id].player_id

        if move_key in GEN1_RAGE_MOVES:
            attacker.rage_active = True

        if move_key == "selfdestruct" or move_key == "explosion":
            attacker.current_hp = 0
            self.add_log(f"|faint|{side_id}a: {attacker.nickname}")
            self.force_switch_player = self.sides[side_id].player_id

    def _apply_direct_damage(
        self,
        side_id: str,
        attacker: PokemonGen1,
        target_side_id: str,
        target: PokemonGen1,
        damage: int,
        move_name: str,
        damage_class: str,
        *,
        ignore_type: bool = False,
    ) -> None:
        if damage <= 0:
            return

        slot_tag = f"{target_side_id}a"
        if target.substitute_hp > 0 and move_name.lower() != "bide":
            target.substitute_hp = max(0, target.substitute_hp - damage)
            self.add_log(f"|-damage|{slot_tag}: {target.nickname}|{self._condition(target)}|[from] substitute")
            if target.substitute_hp <= 0:
                self.add_log(f"|-end|{slot_tag}: {target.nickname}|Substitute")
            return

        if target.semi_invulnerable and _normalize_key(move_name) not in {"swift"}:
            self.add_log(f"|-miss|{side_id}a: {attacker.nickname}|{slot_tag}: {target.nickname}")
            return

        target.current_hp = max(0, target.current_hp - damage)
        target.last_damage_taken = damage
        target.last_damage_class = damage_class
        self.add_log(f"|-damage|{slot_tag}: {target.nickname}|{self._condition(target)}")

        if target.bide_turns is not None and target.bide_turns > 0:
            target.bide_damage += damage

        if target.rage_active and side_id != target_side_id and damage > 0:
            target.modify_stage("atk", 1)

        if target.current_hp <= 0:
            self.add_log(f"|faint|{slot_tag}: {target.nickname}")
            self.force_switch_player = self.sides[target_side_id].player_id

    def _apply_ohko(self, attacker: PokemonGen1, target: PokemonGen1, move: BattleMoveGen1) -> tuple[bool, int]:
        if attacker.level < target.level:
            return False, 0
        chance = min(100, max(0, 30 + attacker.level - target.level))
        if random.randint(1, 100) > chance:
            return False, 0
        return True, target.current_hp

    def _execute_concrete_move(
        self,
        side_id: str,
        move: BattleMoveGen1,
        attacker: PokemonGen1,
        target: PokemonGen1,
        target_side_id: str,
        *,
        forced: bool = False,
        move_index: int | None = None,
        consume_pp: bool = True,
    ) -> None:
        move_key = _normalize_key(move.name)
        started_lock = False

        if move_key in GEN1_SELF_TARGET_MOVES or move_key in GEN1_STATUS_INFLICTING_TARGET_MOVES or move_key in GEN1_CONFUSION_EFFECT_MOVES or move_key in GEN1_FORCE_SWITCH_MOVES or move_key in GEN1_DISABLE_MOVES or move_key in GEN1_LEECH_SEED_MOVES:
            if move_key not in GEN1_SELF_TARGET_MOVES:
                if get_type_multiplier_gen1(move.type, target.types) == 0:
                    self.add_log(f"|-fail|{target_side_id}a: {target.nickname}")
                    return

            self._apply_status_move(side_id, move, move_key, attacker, target, target_side_id)
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if move_key in GEN1_METRONOME_MOVES or move_key in GEN1_MIMIC_MOVES or move_key in GEN1_MIRROR_MOVE or move_key in GEN1_TRANSFORM_MOVES or move_key in GEN1_CONVERSION_MOVES:
            self._apply_status_move(side_id, move, move_key, attacker, target, target_side_id)
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if move_key in GEN1_BIDE_MOVES:
            self._apply_status_move(side_id, move, move_key, attacker, target, target_side_id)
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if move_key in GEN1_CHARGE_MOVES and attacker.charging_turns == 0:
            attacker.charging_move_index = move_index
            attacker.charging_move_name = move.name
            attacker.charging_turns = 1
            if move_key in {"fly", "dig"}:
                attacker.semi_invulnerable = move_key
            if move_key == "skullbash":
                self._apply_stat_delta(side_id, attacker, "def", 1)
            self.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: {move.name}")
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if move_key in GEN1_CHARGE_MOVES and attacker.charging_turns > 0:
            self.add_log(f"|-activate|{side_id}a: {attacker.nickname}|move: {move.name}")
            attacker.charging_turns = 0
            attacker.semi_invulnerable = None
            attacker.charging_move_index = None
            attacker.charging_move_name = None

        if move_key in GEN1_LOCK_MOVES and attacker.locked_move_index is None:
            attacker.locked_move_index = move_index if move_index is not None else 0
            attacker.locked_turns = random.randint(2, 3) - 1
            started_lock = True

        if move_key in GEN1_LOCK_MOVES and attacker.locked_move_index is not None and attacker.locked_turns > 0:
            self.add_log(f"|-start|{side_id}a: {attacker.nickname}|move: {move.name}")

        if move_key in GEN1_OHKO_MOVES:
            success, damage = self._apply_ohko(attacker, target, move)
            if not success:
                self.add_log(f"|-miss|{side_id}a: {attacker.nickname}|{target_side_id}a: {target.nickname}")
                return
            before_hp = target.current_hp
            self._apply_direct_damage(side_id, attacker, target_side_id, target, damage, move.name, "physical")
            if target.current_hp < before_hp:
                target.last_move_id = move.move_id
                target.last_move_name = move.name
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if move_key == "counter":
            if attacker.last_damage_taken <= 0 or attacker.last_damage_class != "physical":
                self.add_log("|-fail|")
                return
            damage = attacker.last_damage_taken * 2
            before_hp = target.current_hp
            self._apply_direct_damage(side_id, attacker, target_side_id, target, damage, move.name, "physical")
            if target.current_hp < before_hp:
                target.last_move_id = move.move_id
                target.last_move_name = move.name
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if move_key == "dreameater" and target.status_condition != "slp":
            self.add_log("|-fail|")
            return

        if move_key == "highjumpkick" or move_key == "jumpkick":
            hit = True
            if move.accuracy is not None:
                hit = calculate_hit_gen1(move.accuracy, attacker.stat_stages["accuracy"], target.stat_stages["evasion"])
            if not hit:
                fake_damage, _ = calculate_damage_gen1(attacker, target, move)
                recoil = max(1, fake_damage // 2)
                attacker.current_hp = max(0, attacker.current_hp - recoil)
                self.add_log(f"|-damage|{side_id}a: {attacker.nickname}|{self._condition(attacker)}|[from] recoil")
                if attacker.current_hp <= 0:
                    self.add_log(f"|faint|{side_id}a: {attacker.nickname}")
                    self.force_switch_player = self.sides[side_id].player_id
                return

        if move_key in GEN1_MULTI_HIT_MOVES:
            min_hits, max_hits = GEN1_MULTI_HIT_MOVES[move_key]
            if min_hits == max_hits:
                hit_count = min_hits
            else:
                roll = random.random()
                if roll < 0.375:
                    hit_count = 2
                elif roll < 0.75:
                    hit_count = 3
                elif roll < 0.875:
                    hit_count = 4
                else:
                    hit_count = 5

            total_damage = 0
            for _ in range(hit_count):
                if target.current_hp <= 0:
                    break
                hit = True
                if move.accuracy is not None:
                    hit = calculate_hit_gen1(move.accuracy, attacker.stat_stages["accuracy"], target.stat_stages["evasion"])
                if not hit:
                    self.add_log(f"|-miss|{side_id}a: {attacker.nickname}|{target_side_id}a: {target.nickname}")
                    break
                is_crit = determine_critical_gen1(attacker.base_speed, move.high_crit, attacker.focus_energy)
                damage, type_multiplier = calculate_damage_gen1(attacker, target, move, is_crit)
                if type_multiplier == 0:
                    self.add_log(f"|-immune|{target_side_id}a: {target.nickname}")
                    break
                if damage <= 0:
                    continue
                before_hp = target.current_hp
                self._apply_direct_damage(side_id, attacker, target_side_id, target, damage, move.name, "physical")
                total_damage += max(0, before_hp - target.current_hp)
                if target.current_hp < before_hp:
                    target.last_move_id = move.move_id
                    target.last_move_name = move.name
                if target.current_hp <= 0:
                    break
            if total_damage > 0:
                self._apply_move_secondary_effects(side_id, target_side_id, attacker, target, move, total_damage, move_key, False)
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        hit = True
        if move.accuracy is not None:
            hit = calculate_hit_gen1(move.accuracy, attacker.stat_stages["accuracy"], target.stat_stages["evasion"])
        if not hit:
            self.add_log(f"|-miss|{side_id}a: {attacker.nickname}|{target_side_id}a: {target.nickname}")
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if move_key in GEN1_SELF_TARGET_MOVES:
            self._apply_status_move(side_id, move, move_key, attacker, target, target_side_id)
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        is_crit = determine_critical_gen1(attacker.base_speed, move.high_crit, attacker.focus_energy)
        if is_crit:
            self.add_log("|-crit|")

        damage_modifier = 1.0
        if not is_crit and self.sides[target_side_id].reflect_turns > 0 and move.damage_class == "physical" and move_key not in GEN1_FIXED_DAMAGE_MOVES:
            damage_modifier *= 0.5
        if not is_crit and self.sides[target_side_id].light_screen_turns > 0 and move.damage_class == "special" and move_key not in GEN1_FIXED_DAMAGE_MOVES:
            damage_modifier *= 0.5

        defense_modifier = 1.0
        if move_key in {"selfdestruct", "explosion"}:
            defense_modifier = 0.5

        damage, type_multiplier = calculate_damage_gen1(
            attacker,
            target,
            move,
            is_critical=is_crit,
            defense_modifier=defense_modifier,
        )

        if type_multiplier == 0:
            self.add_log(f"|-immune|{target_side_id}a: {target.nickname}")
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if move_key == "superfang":
            damage = max(1, target.current_hp // 2)

        if damage_modifier != 1.0 and move_key not in GEN1_FIXED_DAMAGE_MOVES:
            damage = max(1, math.floor(damage * damage_modifier))

        if move_key == "rage":
            attacker.rage_active = True

        if damage <= 0:
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        before_hp = target.current_hp
        self._apply_direct_damage(side_id, attacker, target_side_id, target, damage, move.name, move.damage_class)
        if target.current_hp < before_hp:
            target.last_move_id = move.move_id
            target.last_move_name = move.name

        # If the target was behind a substitute, no secondary effects should apply.
        if before_hp == target.current_hp and target.substitute_hp > 0:
            attacker.last_move_id = move.move_id
            attacker.last_move_name = move.name
            return

        if target.current_hp > 0 and move_key in {"wrap", "bind", "firespin", "clamp"}:
            target.is_trapped = True
            target.trap_turns = random.randint(1, 4)
            target.partial_trap_damage = max(1, damage)
            self.add_log(f"|-activate|{target_side_id}a: {target.nickname}|move: {move.name}")

        if target.current_hp > 0 and move_key in GEN1_LOCK_MOVES and attacker.locked_move_index is None:
            attacker.locked_move_index = move_index if move_index is not None else 0
            attacker.locked_turns = random.randint(2, 3) - 1

        if target.current_hp > 0 and move_key in GEN1_STATUS_EFFECT_BY_MOVE and move_key != "triattack":
            status = GEN1_STATUS_EFFECT_BY_MOVE[move_key]
            if move.effect_chance and random.randint(1, 100) <= int(move.effect_chance):
                self._apply_major_status(target, target_side_id, status, move.name, move.type)
        elif target.current_hp > 0 and move_key == "triattack" and move.effect_chance:
            if random.randint(1, 100) <= int(move.effect_chance):
                for candidate in random.sample(["brn", "frz", "par"], 3):
                    if self._apply_major_status(target, target_side_id, candidate, move.name, move.type):
                        break

        if target.current_hp > 0 and move_key in GEN1_CONFUSION_EFFECT_MOVES and move.effect_chance:
            if random.randint(1, 100) <= int(move.effect_chance) and not target.is_confused:
                target.is_confused = True
                target.confusion_turns = random.randint(1, 4)
                self.add_log(f"|-start|{target_side_id}a: {target.nickname}|confusion")

        if target.current_hp > 0 and move_key in GEN1_FLINCH_EFFECT_MOVES and move.effect_chance:
            if random.randint(1, 100) <= int(move.effect_chance):
                target.is_flinching = True

        if move_key in GEN1_DRAIN_MOVES:
            if move_key == "dreameater" and target.status_condition != "slp":
                self.add_log("|-fail|")
            else:
                heal_amount = max(1, damage // 2)
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
                self.add_log(f"|-heal|{side_id}a: {attacker.nickname}|{self._condition(attacker)}|[from] drain")

        if move_key in GEN1_RECOIL_MOVES:
            if move_key == "struggle":
                recoil = max(1, attacker.max_hp // 4)
            elif move_key == "doubleedge":
                recoil = max(1, damage // 3)
            else:
                recoil = max(1, damage // 4)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            self.add_log(f"|-damage|{side_id}a: {attacker.nickname}|{self._condition(attacker)}|[from] recoil")
            if attacker.current_hp <= 0:
                self.add_log(f"|faint|{side_id}a: {attacker.nickname}")
                self.force_switch_player = self.sides[side_id].player_id

        if move_key in GEN1_RAGE_MOVES:
            attacker.rage_active = True

        if move_key in GEN1_RECHARGE_MOVES:
            if target.current_hp > 0:
                attacker.must_recharge = True
            else:
                attacker.must_recharge = False

        if move_key in {"selfdestruct", "explosion"}:
            attacker.current_hp = 0
            self.add_log(f"|faint|{side_id}a: {attacker.nickname}")
            self.force_switch_player = self.sides[side_id].player_id

        if move_key in GEN1_LOCK_MOVES and not started_lock and attacker.locked_move_index is not None:
            attacker.locked_turns -= 1
            if attacker.locked_turns <= 0:
                attacker.locked_move_index = None
                attacker.locked_turns = 0
                attacker.is_confused = True
                attacker.confusion_turns = random.randint(1, 4)
                self.add_log(f"|-start|{side_id}a: {attacker.nickname}|confusion")

        attacker.last_move_id = move.move_id
        attacker.last_move_name = move.name

    def _resolve_end_turn_effects(self) -> None:
        for side_id, side in self.sides.items():
            pkmn = side.active_pokemon
            if pkmn and pkmn.current_hp > 0:
                slot_tag = f"{side_id}a"

                if pkmn.status_condition in {"brn", "psn", "tox"}:
                    damage = max(1, pkmn.max_hp // 16)
                    if pkmn.status_condition == "tox":
                        damage = max(1, (pkmn.max_hp // 16) * pkmn.toxic_n)
                        pkmn.toxic_n += 1
                    pkmn.current_hp = max(0, pkmn.current_hp - damage)
                    pkmn.last_damage_taken = damage
                    pkmn.last_damage_class = "status"
                    from_effect = "psn" if pkmn.status_condition in {"psn", "tox"} else "brn"
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] {from_effect}")
                    if pkmn.current_hp <= 0:
                        self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                        self.force_switch_player = side.player_id

                if pkmn.is_trapped and pkmn.trap_turns > 0 and pkmn.partial_trap_damage > 0 and pkmn.current_hp > 0:
                    pkmn.current_hp = max(0, pkmn.current_hp - pkmn.partial_trap_damage)
                    pkmn.last_damage_taken = pkmn.partial_trap_damage
                    pkmn.last_damage_class = "physical"
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] move: Partial Trap")
                    if pkmn.current_hp <= 0:
                        self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                        self.force_switch_player = side.player_id
                    pkmn.trap_turns -= 1
                    if pkmn.trap_turns <= 0:
                        pkmn.is_trapped = False
                        pkmn.partial_trap_damage = 0
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|trap")

                if pkmn.leech_seeded and pkmn.current_hp > 0:
                    drain = max(1, pkmn.max_hp // 8)
                    pkmn.current_hp = max(0, pkmn.current_hp - drain)
                    pkmn.last_damage_taken = drain
                    pkmn.last_damage_class = "status"
                    self.add_log(f"|-damage|{slot_tag}: {pkmn.nickname}|{self._condition(pkmn)}|[from] Leech Seed")
                    if pkmn.current_hp <= 0:
                        self.add_log(f"|faint|{slot_tag}: {pkmn.nickname}")
                        self.force_switch_player = side.player_id
                    source_side = self.sides.get(pkmn.leech_seed_source_side or "")
                    if source_side and source_side.active_pokemon and source_side.active_pokemon.current_hp > 0:
                        source = source_side.active_pokemon
                        source.current_hp = min(source.max_hp, source.current_hp + drain)
                        self.add_log(f"|-heal|{pkmn.leech_seed_source_side}a: {source.nickname}|{self._condition(source)}|[from] Leech Seed")

                if pkmn.disable_turns > 0:
                    pkmn.disable_turns -= 1
                    if pkmn.disable_turns <= 0:
                        pkmn.disable_move_id = None
                        self.add_log(f"|-end|{slot_tag}: {pkmn.nickname}|disable")

            if side.reflect_turns > 0:
                side.reflect_turns -= 1
                if side.reflect_turns <= 0:
                    self.add_log(f"|-end|{side_id}: {side.player_name}|Reflect")

            if side.light_screen_turns > 0:
                side.light_screen_turns -= 1
                if side.light_screen_turns <= 0:
                    self.add_log(f"|-end|{side_id}: {side.player_name}|Light Screen")

            if side.mist_turns > 0:
                side.mist_turns -= 1
                if side.mist_turns <= 0:
                    self.add_log(f"|-end|{side_id}: {side.player_name}|Mist")

        for side in self.sides.values():
            pkmn = side.active_pokemon
            if pkmn:
                pkmn.is_flinching = False

    def _check_win_condition(self) -> None:
        for side_id, side in self.sides.items():
            if all(p.current_hp <= 0 for p in side.team):
                winner_side = "p2" if side_id == "p1" else "p1"
                self.add_log(f"|win|{self.sides[winner_side].player_name}")
                self.finished = True
                break

    def _execute_action(self, side_id: str, action: dict[str, Any]) -> None:
        pkmn = self.sides[side_id].active_pokemon
        if not pkmn or pkmn.current_hp <= 0:
            return

        if pkmn.bide_turns is not None:
            target_side_id = "p2" if side_id == "p1" else "p1"
            target = self.sides[target_side_id].active_pokemon
            if pkmn.bide_turns > 1:
                pkmn.bide_turns -= 1
                self.add_log(f"|move|{side_id}a: {pkmn.nickname}|Bide|{side_id}a|[still]")
                return
            pkmn.bide_turns = None
            stored_damage = max(1, pkmn.bide_damage * 2)
            pkmn.bide_damage = 0
            if target and target.current_hp > 0:
                self.add_log(f"|move|{side_id}a: {pkmn.nickname}|Bide|{target_side_id}a")
                self._apply_direct_damage(side_id, pkmn, target_side_id, target, stored_damage, "Bide", "physical")
            return

        if action["type"] == "switch":
            if pkmn.is_trapped:
                self.add_log(f"|cant|{side_id}a: {pkmn.nickname}|trap")
                return
            self._switch_in(side_id, int(action["index"]))
            return

        if action["type"] != "move":
            return

        move_index = int(action["move_index"])
        if not (0 <= move_index < len(pkmn.moves)):
            return

        move = pkmn.moves[move_index]
        move_key = _normalize_key(move.name)
        move_pp = int(move.pp or 0)
        target_side_id = "p2" if side_id == "p1" else "p1"
        target = self.sides[target_side_id].active_pokemon
        if not target or target.current_hp <= 0:
            return

        if pkmn.disable_turns > 0 and pkmn.disable_move_id == move.move_id:
            self.add_log(f"|cant|{side_id}a: {pkmn.nickname}|disable")
            return

        if move_pp <= 0 and move_key != "struggle":
            if any(int(m.pp or 0) > 0 for m in pkmn.moves):
                self.add_log(f"|cant|{side_id}a: {pkmn.nickname}|nopp")
                return
            struggle_move = _build_move_from_data(165)
            if not struggle_move:
                self.add_log(f"|cant|{side_id}a: {pkmn.nickname}|nopp")
                return
            move = struggle_move
            move_key = "struggle"
            move_pp = int(move.pp or 0)

        forced_move = None

        if pkmn.charging_turns > 0 and pkmn.charging_move_index is not None:
            forced_move = pkmn.moves[pkmn.charging_move_index]
            move = forced_move
            move_index = pkmn.charging_move_index
            move_key = _normalize_key(move.name)
        elif move_key in GEN1_CHARGE_MOVES and pkmn.charging_turns == 0:
            if not self._can_pokemon_move(side_id, pkmn):
                return
            move.pp = max(0, move_pp - 1)
            self._execute_concrete_move(side_id, move, pkmn, target, target_side_id, move_index=move_index)
            return

        if pkmn.locked_move_index is not None and pkmn.locked_turns > 0:
            move = pkmn.moves[pkmn.locked_move_index]
            move_index = pkmn.locked_move_index
            move_key = _normalize_key(move.name)

        if not self._can_pokemon_move(side_id, pkmn):
            return

        if move_pp > 0 and move_key != "struggle" and forced_move is None and not (pkmn.charging_turns > 0 and pkmn.charging_move_index is not None):
            move.pp = max(0, move_pp - 1)

        if move_key in GEN1_CHARGE_MOVES and pkmn.charging_turns > 0:
            self._execute_concrete_move(side_id, move, pkmn, target, target_side_id, move_index=move_index)
            return

        if move_key in GEN1_LOCK_MOVES and pkmn.locked_move_index is not None and pkmn.locked_turns > 0:
            self._execute_concrete_move(side_id, move, pkmn, target, target_side_id, move_index=move_index)
            pkmn.locked_turns -= 1
            if pkmn.locked_turns <= 0:
                pkmn.locked_move_index = None
                pkmn.is_confused = True
                pkmn.confusion_turns = random.randint(1, 4)
                self.add_log(f"|-start|{side_id}a: {pkmn.nickname}|confusion")
            return

        self._execute_concrete_move(side_id, move, pkmn, target, target_side_id, move_index=move_index)

    def generate_request(self, player_id: str) -> dict[str, Any]:
        if self.sides["p1"].player_id == player_id:
            side_id = "p1"
        else:
            side_id = "p2"
        side = self.sides[side_id]
        pkmn = side.active_pokemon
        if not pkmn:
            return {}

        moves = []
        for i, m in enumerate(pkmn.moves):
            moves.append(
                {
                    "move": m.name,
                    "id": m.move_id,
                    "pp": int(m.pp or 0),
                    "maxpp": m.max_pp,
                    "target": "normal",
                    "disabled": (
                        int(m.pp or 0) <= 0
                        or (pkmn.disable_turns > 0 and pkmn.disable_move_id == m.move_id)
                    ),
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
                            "spa": p.stats.special,
                            "spd": p.stats.special,
                            "spe": p.stats.spe,
                        },
                        "moves": [m.name for m in p.moves],
                        "baseAbility": "none",
                        "item": "none",
                        "pokeball": "pokeball",
                    }
                    for i, p in enumerate(side.team)
                ],
            },
        }
