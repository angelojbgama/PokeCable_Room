from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

@dataclass
class BattleStatsGen1:
    hp: int
    atk: int
    defen: int
    spe: int
    special: int # Unico para SpA e SpD

@dataclass
class BattleMoveGen1:
    move_id: int
    name: str
    type: str
    power: int
    accuracy: int
    pp: int
    max_pp: int
    priority: int
    damage_class: str # physical, special, status
    effect: str = ""
    high_crit: bool = False

def calc_gen1_stat(base, dv, exp, lvl, is_hp=False):
    # Formula Gen 1: floor(((Base + DV) * 2 + floor(ceil(sqrt(Exp)) / 4)) * Lvl / 100) + (Lvl + 10 if HP else 5)
    # Na pratica muitos usam floor(sqrt(exp)) simplificado
    bonus = math.floor(math.sqrt(exp)) // 4
    main = math.floor(((base + dv) * 2 + bonus) * lvl / 100)
    return main + (lvl + 10 if is_hp else 5)

@dataclass
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
    is_trapped: bool = False # Wrap, Bind, etc.
    trap_turns: int = 0
    must_recharge: bool = False # Hyper Beam
    substitute_hp: int = 0
    leech_seeded: bool = False
    toxic_n: int = 1 # Multiplicador de Toxic
    is_transformed: bool = False # Ditto
    
    def get_modified_stat(self, stat_name: str) -> int:
        if stat_name in ["accuracy", "evasion"]:
            # Gen 1 accuracy/evasion stages: 25/100, 33/100 ... 100/100 ... 300/100
            # Simplificaremos usando uma tabela similar a Gen 3 por enquanto se nao houver info exata
            return 0 # TODO: Implementar
            
        base_val = getattr(self.stats, stat_name if stat_name != "def" else "defen")

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
        base_data = get_base_stats(national_id)
        if not base_data: raise ValueError(f"Pokemon #{national_id} nao encontrado.")
        
        level = int(canonical.get("level") or 1)
        
        # DVs (0-15 na Gen 1)
        # Se vier de um save Gen 1, o conversor ja deve ter normalizado ou mantido
        c_ivs = canonical.get("ivs", {})
        dvs = {
            "atk": int(c_ivs.get("attack", 15)),
            "def": int(c_ivs.get("defense", 15)),
            "spe": int(c_ivs.get("speed", 15)),
            "spc": int(c_ivs.get("special", 15) or c_ivs.get("special_attack", 15)),
        }
        # DV de HP e derivado: bit menos significativo de cada DV (Atk, Def, Spe, Spc)
        hp_dv = ((dvs["atk"] & 1) << 3) | ((dvs["def"] & 1) << 2) | ((dvs["spe"] & 1) << 1) | (dvs["spc"] & 1)
        dvs["hp"] = hp_dv

        # Stat Exp (0-65535)
        c_evs = canonical.get("evs", {})
        stat_exp = {
            "hp": int(c_evs.get("hp", 65535)),
            "atk": int(c_evs.get("attack", 65535)),
            "def": int(c_evs.get("defense", 65535)),
            "spe": int(c_evs.get("speed", 65535)),
            "spc": int(c_evs.get("special", 65535) or c_evs.get("special_attack", 65535)),
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
                # Flag high crit para Gen 1
                is_high_crit = m_id in [13, 14, 43, 75, 99, 148] # Razor Leaf, Slash, Crabhammer, Karate Chop, etc.
                moves.append(BattleMoveGen1(
                    move_id=m_id, name=m_data["name"], type=m_data["type"],
                    power=m_data["power"] or 0, accuracy=m_data["accuracy"] or 100,
                    pp=m.get("pp", m_data["pp"]), max_pp=m_data["pp"],
                    priority=m_data["priority"], damage_class=m_data["damage_class"],
                    effect=m_data["effect"], high_crit=is_high_crit
                ))

        return cls(
            national_id=national_id, name=base_data["name"], nickname=canonical.get("nickname") or base_data["name"],
            level=level, types=base_data["types"], max_hp=stats.hp, current_hp=canonical.get("current_hp", stats.hp),
            stats=stats, base_speed=base_stats["spe"], dvs=dvs, moves=moves,
            status_condition=canonical.get("status_condition")
        )
