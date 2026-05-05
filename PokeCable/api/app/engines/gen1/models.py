from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


ACCURACY_EVASION_STAGE_MODIFIERS: dict[int, float] = {
    -6: 3 / 9,
    -5: 3 / 8,
    -4: 3 / 7,
    -3: 3 / 6,
    -2: 3 / 5,
    -1: 3 / 4,
    0: 3 / 3,
    1: 4 / 3,
    2: 5 / 3,
    3: 6 / 3,
    4: 7 / 3,
    5: 8 / 3,
    6: 9 / 3,
}


def _pick_int(value_map: dict[str, Any], *keys: str, default: int) -> int:
    for key in keys:
        if key in value_map and value_map[key] is not None:
            return int(value_map[key])
    return default

@dataclass(slots=True)
class BattleStatsGen1:
    hp: int
    atk: int
    defen: int
    spe: int
    special: int # Unico para SpA e SpD

@dataclass(slots=True)
class BattleMoveGen1:
    move_id: int
    name: str
    type: str
    power: int | None
    accuracy: int | None
    pp: int
    max_pp: int
    priority: int
    damage_class: str # physical, special, status
    effect_chance: int | None = None
    effect: str = ""
    high_crit: bool = False

def calc_gen1_stat(base, dv, exp, lvl, is_hp=False):
    # Formula Gen 1: floor(((Base + DV) * 2 + floor(ceil(sqrt(Exp)) / 4)) * Lvl / 100) + (Lvl + 10 if HP else 5)
    # Na pratica muitos usam floor(sqrt(exp)) simplificado
    bonus = math.floor(math.sqrt(exp)) // 4
    main = math.floor(((base + dv) * 2 + bonus) * lvl / 100)
    return main + (lvl + 10 if is_hp else 5)

@dataclass(slots=True)
class PokemonGen1:
    national_id: int
    name: str
    nickname: str
    level: int
    types: list[str]
    
    # Status em tempo real
    max_hp: int
    current_hp: int
    stats: BattleStatsGen1
    base_speed: int # Para calculo de critico
    
    # DVs (0-15)
    dvs: dict[str, int]
    
    moves: list[BattleMoveGen1] = field(default_factory=list)
    status_condition: str | None = None # brn, par, slp, frz, psn
    status_turns: int = 0 # Para Sleep
    
    stat_stages: dict[str, int] = field(default_factory=lambda: {
        "atk": 0, "def": 0, "spe": 0, "special": 0, "accuracy": 0, "evasion": 0
    })
    
    # Estados Volateis Gen 1
    is_confused: bool = False
    confusion_turns: int = 0
    is_flinching: bool = False
    semi_invulnerable: str | None = None
    is_trapped: bool = False # Wrap, Bind, etc.
    trap_turns: int = 0
    partial_trap_damage: int = 0
    must_recharge: bool = False # Hyper Beam
    substitute_hp: int = 0
    leech_seeded: bool = False
    leech_seed_source_side: str | None = None
    toxic_n: int = 1 # Multiplicador de Toxic
    is_transformed: bool = False # Ditto
    source_generation: int = 1
    last_move_id: int | None = None
    last_move_name: str | None = None
    last_damage_taken: int = 0
    last_damage_class: str | None = None
    disable_move_id: int | None = None
    disable_turns: int = 0
    rage_active: bool = False
    rage_hits: int = 0
    locked_move_index: int | None = None
    locked_turns: int = 0
    charging_move_index: int | None = None
    charging_turns: int = 0
    charging_move_name: str | None = None
    focus_energy: bool = False
    bide_turns: int | None = None
    bide_damage: int = 0
    transformed_from_name: str | None = None
    weight: float = 50.0

    def clear_volatile_state(self) -> None:
        self.is_confused = False
        self.confusion_turns = 0
        self.is_flinching = False
        self.semi_invulnerable = None
        self.is_trapped = False
        self.trap_turns = 0
        self.partial_trap_damage = 0
        self.must_recharge = False
        self.substitute_hp = 0
        self.leech_seeded = False
        self.leech_seed_source_side = None
        self.disable_move_id = None
        self.disable_turns = 0
        self.rage_active = False
        self.rage_hits = 0
        self.locked_move_index = None
        self.locked_turns = 0
        self.charging_move_index = None
        self.charging_turns = 0
        self.charging_move_name = None
        self.focus_energy = False
        self.bide_turns = None
        self.bide_damage = 0
        self.is_transformed = False
        self.transformed_from_name = None

    def clear_battle_modifiers(self) -> None:
        self.stat_stages = {k: 0 for k in self.stat_stages}
        self.toxic_n = 1

    def on_switch_out(self) -> None:
        self.clear_volatile_state()
        self.clear_battle_modifiers()

    def modify_stage(self, stat_name: str, amount: int) -> int:
        current = self.stat_stages.get(stat_name, 0)
        next_value = max(-6, min(6, current + amount))
        delta = next_value - current
        self.stat_stages[stat_name] = next_value
        return delta

    def get_modified_stat(self, stat_name: str) -> int:
        if stat_name in ["accuracy", "evasion"]:
            stage = max(-6, min(6, self.stat_stages.get(stat_name, 0)))
            return max(1, math.floor(100 * ACCURACY_EVASION_STAGE_MODIFIERS[stage]))

        base_attr = stat_name if stat_name != "def" else "defen"
        base_val = getattr(self.stats, base_attr)

        stage = self.stat_stages.get(stat_name, 0)
        
        # Multiplicadores de estagio Gen 1 (iguais a Gen 3)
        modifiers = {
            -6: 0.25, -5: 0.28, -4: 0.33, -3: 0.40, -2: 0.50, -1: 0.66,
             0: 1.0,
             1: 1.5, 2: 2.0, 3: 2.5, 4: 3.0, 5: 3.5, 6: 4.0
        }
        
        val = math.floor(base_val * modifiers.get(stage, 1.0))
        
        # Penalidades de Status
        if stat_name == "atk" and self.status_condition == "brn":
            val = math.floor(val / 2)
        if stat_name == "spe" and self.status_condition == "par":
            val = math.floor(val / 4)
            
        return max(1, val)

    @classmethod
    def from_canonical(cls, canonical: dict[str, Any]) -> PokemonGen1:
        # Importacao dinamica para evitar circularidade ou dependencias pesadas no modelo
        from ...data.base_stats import get_base_stats
        from ...data.move_combat_data import get_move_combat_data
        
        national_id = int(canonical.get("species_national_id") or 0)
        source_gen = int(canonical.get("source_generation") or canonical.get("generation") or 1)
        if source_gen != 1:
            raise ValueError(f"PokemonGen1 requer source_generation=1, recebeu {source_gen}.")

        base_data = get_base_stats(national_id)
        if not base_data: raise ValueError(f"Pokemon #{national_id} nao encontrado.")
        
        level = int(canonical.get("level") or 1)
        species_name = canonical.get("species_name") or canonical.get("species", {}).get("name") or f"Pokemon #{national_id}"
        
        # DVs (0-15 na Gen 1)
        c_ivs = canonical.get("ivs", {})
        dvs = {
            "atk": _pick_int(c_ivs, "attack", "atk", default=15),
            "def": _pick_int(c_ivs, "defense", "def", default=15),
            "spe": _pick_int(c_ivs, "speed", "spe", default=15),
            "spc": _pick_int(c_ivs, "special", "special_attack", "spa", default=15),
        }
        # DV de HP e derivado: bit menos significativo de cada DV (Atk, Def, Spe, Spc)
        hp_dv = ((dvs["atk"] & 1) << 3) | ((dvs["def"] & 1) << 2) | ((dvs["spe"] & 1) << 1) | (dvs["spc"] & 1)
        dvs["hp"] = hp_dv

        # Stat Exp (0-65535)
        c_evs = canonical.get("evs", {})
        stat_exp = {
            "hp": _pick_int(c_evs, "hp", default=65535),
            "atk": _pick_int(c_evs, "attack", "atk", default=65535),
            "def": _pick_int(c_evs, "defense", "def", default=65535),
            "spe": _pick_int(c_evs, "speed", "spe", default=65535),
            "spc": _pick_int(c_evs, "special", "special_attack", "spa", default=65535),
        }

        base_stats = base_data["stats"]
        
        # A função calc_gen1_stat é definida fora da classe para ser exportável
        stats = BattleStatsGen1(
            hp=calc_gen1_stat(base_stats["hp"], dvs["hp"], stat_exp["hp"], level, True),
            atk=calc_gen1_stat(base_stats["atk"], dvs["atk"], stat_exp["atk"], level),
            defen=calc_gen1_stat(base_stats["def"], dvs["def"], stat_exp["def"], level),
            spe=calc_gen1_stat(base_stats["spe"], dvs["spe"], stat_exp["spe"], level),
            special=calc_gen1_stat(base_stats["spa"], dvs["spc"], stat_exp["spc"], level),
        )

        moves = []
        for m in canonical.get("moves", []):
            m_id = int(m.get("move_id") or 0)
            m_data = get_move_combat_data(m_id)
            if m_data:
                is_high_crit = "critical hit" in str(m_data.get("effect") or "").lower()
                pp_value = m.get("pp")
                max_pp_value = m.get("max_pp")
                moves.append(BattleMoveGen1(
                    move_id=m_id, name=m_data["name"], type=m_data["type"],
                    power=m_data["power"] if m_data.get("power") is not None else None,
                    accuracy=m_data["accuracy"] if m_data.get("accuracy") is not None else None,
                    pp=int(pp_value) if pp_value is not None else int(m_data["pp"]),
                    max_pp=int(max_pp_value) if max_pp_value is not None else int(m_data["pp"]),
                    priority=m_data["priority"], damage_class=m_data["damage_class"],
                    effect_chance=m_data.get("effect_chance"),
                    effect=m_data["effect"], high_crit=is_high_crit
                ))

        return cls(
            national_id=national_id, name=species_name, nickname=canonical.get("nickname") or species_name,
            level=level, types=base_data["types"], max_hp=stats.hp, current_hp=canonical.get("current_hp", stats.hp),
            stats=stats, base_speed=base_stats["spe"], dvs=dvs, moves=moves,
            weight=float(canonical.get("weight") or 50.0),
            status_condition=canonical.get("status_condition"),
            source_generation=source_gen,
        )
