from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from ...data.battle_items import BATTLE_ITEMS
from ...data.base_stats import get_base_stats
from ...data.move_combat_data import get_move_combat_data
from .utils import ACCURACY_EVASION_STAGE_MODIFIERS, STAT_STAGE_MODIFIERS


def _pick_int(value_map: dict[str, Any], *keys: str, default: int) -> int:
    for key in keys:
        if key in value_map and value_map[key] is not None:
            return int(value_map[key])
    return default


def calc_gen2_stat(base: int, dv: int, exp: int, lvl: int, is_hp: bool = False) -> int:
    bonus = math.floor(math.sqrt(exp)) // 4
    main = math.floor(((base + dv) * 2 + bonus) * lvl / 100)
    return main + (lvl + 10 if is_hp else 5)


@dataclass(slots=True)
class BattleStatsGen2:
    hp: int
    atk: int
    defen: int
    spa: int
    spd: int
    spe: int


@dataclass(slots=True)
class BattleMoveGen2:
    move_id: int
    name: str
    type: str
    power: int
    accuracy: int
    pp: int
    max_pp: int
    priority: int
    damage_class: str
    effect: str = ""
    high_crit: bool = False
    effect_chance: int | None = None


@dataclass(slots=True)
class PokemonGen2:
    national_id: int
    name: str
    nickname: str
    level: int
    types: list[str]
    max_hp: int
    current_hp: int
    stats: BattleStatsGen2
    base_speed: int
    dvs: dict[str, int]
    moves: list[BattleMoveGen2] = field(default_factory=list)
    status_condition: str | None = None
    status_turns: int = 0
    semi_invulnerable: str | None = None
    last_move_id: int | None = None
    last_move_name: str | None = None
    last_damage_taken: int = 0
    last_damage_class: str = ""
    disable_move_id: int | None = None
    disable_turns: int = 0
    encore_move_id: int | None = None
    encore_turns: int = 0
    charging_move_index: int | None = None
    charging_turns: int = 0
    charging_move_name: str | None = None
    bide_turns: int | None = None
    bide_damage: int = 0
    rage_active: bool = False
    rollout_turns: int = 0
    fury_cutter_turns: int = 0
    stat_stages: dict[str, int] = field(
        default_factory=lambda: {
            "atk": 0,
            "def": 0,
            "spe": 0,
            "spa": 0,
            "spd": 0,
            "accuracy": 0,
            "evasion": 0,
        }
    )
    is_confused: bool = False
    confusion_turns: int = 0
    is_flinching: bool = False
    is_trapped: bool = False
    trap_turns: int = 0
    must_recharge: bool = False
    substitute_hp: int = 0
    leech_seeded: bool = False
    leech_seed_source_side: str | None = None
    toxic_n: int = 1
    held_item_id: int | None = None
    consumed_item: bool = False
    source_generation: int = 2

    @property
    def item_data(self) -> dict[str, Any] | None:
        if self.held_item_id and not self.consumed_item:
            return BATTLE_ITEMS.get(self.held_item_id)
        return None

    def get_modified_stat(
        self,
        stat_name: str,
        weather: str = "none",
        stage_override: int | None = None,
        ignore_burn_penalty: bool = False,
        generation: int = 2,
    ) -> int:
        if stat_name in ["accuracy", "evasion"]:
            base_val = 100
        else:
            base_attr = stat_name if stat_name != "def" else "defen"
            base_val = getattr(self.stats, base_attr)

        stage = self.stat_stages.get(stat_name, 0) if stage_override is None else stage_override
        stage = max(-6, min(6, stage))

        if stat_name in ["accuracy", "evasion"]:
            multiplier = ACCURACY_EVASION_STAGE_MODIFIERS[stage]
        else:
            multiplier = STAT_STAGE_MODIFIERS[stage]

        final_val = math.floor(base_val * multiplier)

        if stat_name == "atk" and self.status_condition == "brn" and not ignore_burn_penalty:
            final_val = math.floor(final_val / 2)
        elif stat_name == "spe" and self.status_condition == "par":
            final_val = math.floor(final_val / 4)

        return max(1, final_val)

    def modify_stage(self, stat_name: str, amount: int) -> int:
        current = self.stat_stages.get(stat_name, 0)
        new_val = max(-6, min(6, current + amount))
        diff = new_val - current
        self.stat_stages[stat_name] = new_val
        return diff

    def clear_volatile_state(self) -> None:
        self.semi_invulnerable = None
        self.last_damage_taken = 0
        self.last_damage_class = ""
        self.disable_move_id = None
        self.disable_turns = 0
        self.encore_move_id = None
        self.encore_turns = 0
        self.charging_move_index = None
        self.charging_turns = 0
        self.charging_move_name = None
        self.bide_turns = None
        self.bide_damage = 0
        self.rage_active = False
        self.rollout_turns = 0
        self.fury_cutter_turns = 0
        self.is_confused = False
        self.confusion_turns = 0
        self.is_flinching = False
        self.is_trapped = False
        self.trap_turns = 0
        self.must_recharge = False
        self.substitute_hp = 0
        self.leech_seeded = False
        self.leech_seed_source_side = None

    @classmethod
    def from_canonical(cls, canonical: dict[str, Any]) -> "PokemonGen2":
        source_gen = int(canonical.get("source_generation") or canonical.get("generation") or 2)
        if source_gen != 2:
            raise ValueError(f"PokemonGen2 requer source_generation=2, recebeu {source_gen}.")

        national_id = int(canonical.get("species_national_id") or canonical.get("species", {}).get("national_dex_id") or 0)
        base_data = get_base_stats(national_id)
        if not base_data:
            raise ValueError(f"Pokemon #{national_id} nao encontrado.")

        level = int(canonical.get("level") or 1)
        species_name = canonical.get("species_name") or canonical.get("species", {}).get("name") or f"Pokemon #{national_id}"
        trainer_id = int(canonical.get("trainer_id") or 0)

        c_ivs = canonical.get("ivs", {}) or {}
        dvs = {
            "atk": _pick_int(c_ivs, "attack", "atk", default=15),
            "def": _pick_int(c_ivs, "defense", "def", default=15),
            "spe": _pick_int(c_ivs, "speed", "spe", default=15),
            "spc": _pick_int(c_ivs, "special", "special_attack", "special_defense", "spa", "spd", default=15),
        }
        if "hp" in c_ivs and c_ivs.get("hp") is not None:
            dvs["hp"] = _pick_int(c_ivs, "hp", default=15)
        else:
            dvs["hp"] = ((dvs["atk"] & 1) << 3) | ((dvs["def"] & 1) << 2) | ((dvs["spe"] & 1) << 1) | (dvs["spc"] & 1)

        c_evs = canonical.get("evs", {}) or {}
        stat_exp = {
            "hp": _pick_int(c_evs, "hp", default=65535),
            "atk": _pick_int(c_evs, "attack", "atk", default=65535),
            "def": _pick_int(c_evs, "defense", "def", default=65535),
            "spe": _pick_int(c_evs, "speed", "spe", default=65535),
            "spc": _pick_int(c_evs, "special", "special_attack", "special_defense", "spa", "spd", default=65535),
        }

        base_stats = base_data["stats"]
        stats = BattleStatsGen2(
            hp=calc_gen2_stat(base_stats["hp"], dvs["hp"], stat_exp["hp"], level, True),
            atk=calc_gen2_stat(base_stats["atk"], dvs["atk"], stat_exp["atk"], level),
            defen=calc_gen2_stat(base_stats["def"], dvs["def"], stat_exp["def"], level),
            spe=calc_gen2_stat(base_stats["spe"], dvs["spe"], stat_exp["spe"], level),
            spa=calc_gen2_stat(base_stats["spa"], dvs["spc"], stat_exp["spc"], level),
            spd=calc_gen2_stat(base_stats["spd"], dvs["spc"], stat_exp["spc"], level),
        )

        moves: list[BattleMoveGen2] = []
        for m in canonical.get("moves", []):
            m_id = int(m.get("move_id") or 0)
            m_data = get_move_combat_data(m_id)
            if m_data:
                moves.append(
                    BattleMoveGen2(
                        move_id=m_id,
                        name=m_data["name"],
                        type=m_data["type"],
                        power=m_data["power"] or 0,
                        accuracy=m_data["accuracy"] or 100,
                        pp=m.get("pp") if m.get("pp") is not None else m_data["pp"],
                        max_pp=m_data["pp"],
                        priority=m_data["priority"],
                        damage_class=m_data["damage_class"],
                        effect=m_data["effect"],
                        high_crit="critical hit" in str(m_data.get("effect") or "").lower(),
                        effect_chance=m_data.get("effect_chance"),
                    )
                )

        held_item_id = None
        if canonical.get("held_item"):
            held_item_id = int(canonical["held_item"].get("item_id") or 0)
        elif canonical.get("held_item_id"):
            held_item_id = int(canonical["held_item_id"])

        return cls(
            national_id=national_id,
            name=species_name,
            nickname=canonical.get("nickname") or species_name,
            level=level,
            types=base_data["types"],
            max_hp=stats.hp,
            current_hp=canonical.get("current_hp") if canonical.get("current_hp") is not None else stats.hp,
            stats=stats,
            base_speed=base_stats["spe"],
            dvs=dvs,
            moves=moves,
            status_condition=canonical.get("status_condition"),
            held_item_id=held_item_id,
            source_generation=source_gen,
        )
