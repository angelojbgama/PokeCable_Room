from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .battle_utils import (
    STAT_STAGE_MODIFIERS,
    ACCURACY_EVASION_STAGE_MODIFIERS,
    calculate_hp,
    calculate_other_stat,
    get_nature_modifiers,
)
from ...data.base_stats import get_base_stats
from ...data.move_combat_data import get_move_combat_data
from ...data.pokemon_abilities import SPECIES_ABILITIES
from ...data.battle_items import BATTLE_ITEMS

@dataclass
class BattleMove:
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
    effect_chance: int | None = None

@dataclass
class BattleStats:
    hp: int
    atk: int
    defen: int # 'def' is a keyword
    spa: int
    spd: int
    spe: int

@dataclass
class BattlePokemon:
    national_id: int
    name: str
    nickname: str
    level: int
    types: list[str]
    base_stats: dict[str, int]
    ivs: dict[str, int]
    evs: dict[str, int]
    nature_id: int
    ability: str | None
    
    # Status em tempo real
    max_hp: int
    current_hp: int
    stats: BattleStats
    
    # Task 8.5: Movimentos Dinamicos
    weight: float = 50.0 # kg, padrao se nao fornecido
    
    # Task 8.6: Felicidade e Retrocompatibilidade
    happiness: int = 70 # Padrao gen 3
    source_generation: int = 3 # 1, 2 ou 3
    
    held_item_id: int | None = None
    moves: list[BattleMove] = field(default_factory=list)
    status_condition: str | None = None # burn, sleep, etc.
    status_turns: int = 0
    stat_stages: dict[str, int] = field(default_factory=lambda: {
        "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0, "accuracy": 0, "evasion": 0
    })
    consumed_item: bool = False
    
    # Task 7.3: Estados Volateis de Protecao
    is_protected: bool = False
    consecutive_protects: int = 0
    
    # Task 7.1: Outros Estados Volateis
    confusion_turns: int = 0
    is_flinching: bool = False
    
    # Task 7.2: Movimentos de Multiplos Turnos
    locked_move_index: int | None = None # -1 para Struggle, 0-3 para moves normais
    semi_invulnerable: str | None = None # "fly", "dig", "dive", "bounce"
    is_charging: bool = False # Para Solar Beam, etc.
    
    # Task 8.8: Bloqueio e Recarga
    must_recharge: bool = False
    rage_turns: int = 0 # Para Outrage, Thrash, Petal Dance

    # Task 7.6.B: Trapping (Mean Look, Fire Spin, etc.)
    trapped_by_side: str | None = None
    partial_trap_name: str | None = None
    partial_trap_turns: int = 0
    
    # Task 7.11: Leech Seed
    leech_seed_recipient: str | None = None # side_id que recebe a cura
    
    # Task 7.10: Substitute
    substitute_hp: int = 0

    # Task 8.2: Disrupcoes (Taunt, Disable, Encore)
    taunt_turns: int = 0
    disable_move_id: int | None = None
    disable_turns: int = 0
    encore_move_index: int | None = None
    encore_turns: int = 0
    last_move_id: int | None = None

    # Task 8.3: Instakill / Sacrificio
    destiny_bond: bool = False
    perish_song_turns: int | None = None # None = sem efeito, 0-3 turns

    # Task 8.4: Counters e Absorções
    last_damage_taken: int = 0
    last_damage_class: str | None = None # physical ou special
    bide_turns: int | None = None # None = sem efeito, 2 = carregando, 1 = carregando, 0 = liberando
    bide_damage: int = 0
    
    @property
    def item_data(self) -> dict[str, Any] | None:
        if self.held_item_id and not self.consumed_item:
            return BATTLE_ITEMS.get(self.held_item_id)
        return None

    def get_modified_stat(self, stat_name: str, weather: str = "none", stage_override: int | None = None, ignore_burn_penalty: bool = False, generation: int = 3) -> int:
        """Retorna o stat modificado pelos estagios (-6 a +6), condicoes de status e habilidades."""
        # Se for accuracy ou evasion, tratamos de forma diferente (base 100)
        if stat_name in ["accuracy", "evasion"]:
            base_val = 100
        else:
            # Na Gen 1, spd usa o valor de spa (Special)
            if generation == 1 and stat_name == "spd":
                base_val = self.stats.spa
            else:
                base_val = getattr(self.stats, stat_name if stat_name != "def" else "defen")
            
        stage = self.stat_stages.get(stat_name, 0) if stage_override is None else stage_override
        # Na Gen 1, o estagio de spd e o mesmo de spa
        if generation == 1 and stat_name == "spd":
            stage = self.stat_stages.get("spa", 0) if stage_override is None else stage_override

        # Clamp stage
        stage = max(-6, min(6, stage))
        
        if stat_name in ["accuracy", "evasion"]:
            multiplier = ACCURACY_EVASION_STAGE_MODIFIERS[stage]
        else:
            multiplier = STAT_STAGE_MODIFIERS[stage]
        
        final_val = math.floor(base_val * multiplier)

        # Penalidades e Bônus de Status/Ability (Gen 3)
        if generation >= 3:
            if stat_name == "atk":
                # Burn reduz atk pela metade, a menos que tenha Guts ou ignore_burn_penalty (ex: Facade)
                if self.status_condition == "brn" and self.ability != "guts" and not ignore_burn_penalty:
                    final_val = math.floor(final_val / 2)
                # Task 7.16: Guts (1.5x Atk se tiver qualquer status)
                if self.status_condition and self.ability == "guts":
                    final_val = math.floor(final_val * 1.5)
            
            elif stat_name == "def":
                # Task 7.16: Marvel Scale (1.5x Def se tiver qualquer status)
                if self.status_condition and self.ability == "marvel-scale":
                    final_val = math.floor(final_val * 1.5)

            elif stat_name == "spe":
                # Paralisia reduz speed para 1/4 (Gen 3)
                if self.status_condition == "par":
                    final_val = math.floor(final_val / 4)
                
                # Task 7.16: Swift Swim / Chlorophyll
                if (self.ability == "swift-swim" and weather == "rain") or \
                   (self.ability == "chlorophyll" and weather == "sun"):
                    final_val *= 2
        elif generation == 1:
            # Na Gen 1, Burn reduz Atk pela metade e Paralyze reduz Speed para 1/4
            if stat_name == "atk" and self.status_condition == "brn":
                final_val = math.floor(final_val / 2)
            elif stat_name == "spe" and self.status_condition == "par":
                final_val = math.floor(final_val / 4)
            
        return max(1, final_val)

    def modify_stage(self, stat_name: str, amount: int) -> int:
        """Altera um estagio de stat e retorna o quanto realmente mudou (respeitando os limites de -6 a 6)."""
        current = self.stat_stages.get(stat_name, 0)
        new_val = max(-6, min(6, current + amount))
        diff = new_val - current
        self.stat_stages[stat_name] = new_val
        return diff
    
    @classmethod
    def from_canonical(cls, canonical: dict[str, Any]) -> BattlePokemon:
        national_id = int(canonical.get("species_national_id") or canonical.get("species", {}).get("national_dex_id") or 0)
        base_data = get_base_stats(national_id)
        if not base_data:
            raise ValueError(f"Base stats nao encontrados para o Pokemon #{national_id}")
        
        level = int(canonical.get("level") or 1)
        source_gen = int(canonical.get("source_generation") or 3)
        trainer_id = int(canonical.get("trainer_id") or 0)
        
        # 1. IVs e EVs (se nao existirem, assume valores padrao de batalha justa)
        c_ivs = canonical.get("ivs", {}) or {}
        ivs = {
            "hp": int(c_ivs.get("hp", 31)),
            "atk": int(c_ivs.get("attack", 31) or c_ivs.get("atk", 31)),
            "def": int(c_ivs.get("defense", 31) or c_ivs.get("def", 31)),
            "spa": int(c_ivs.get("special_attack", 31) or c_ivs.get("spa", 31)),
            "spd": int(c_ivs.get("special_defense", 31) or c_ivs.get("spd", 31)),
            "spe": int(c_ivs.get("speed", 31) or c_ivs.get("spe", 31)),
        }
        
        # Task 10.2: Normalização de DVs para IVs (Gen 1/2 -> Gen 3)
        if source_gen < 3:
            for k in ivs:
                ivs[k] = min(31, ivs[k] * 2 + (1 if ivs[k] > 7 else 0))

        c_evs = canonical.get("evs", {}) or {}
        evs = {
            "hp": int(c_evs.get("hp", 0)),
            "atk": int(c_evs.get("attack", 0)),
            "def": int(c_evs.get("defense", 0)),
            "spa": int(c_evs.get("special_attack", 0)),
            "spd": int(c_evs.get("special_defense", 0)),
            "spe": int(c_evs.get("speed", 0)),
        }
        
        # Task 10.3: Normalização de Stat Exp para EVs (Cap 510)
        if source_gen < 3:
            for k in evs:
                evs[k] = min(255, math.floor(evs[k] / 256))
            
            # Aplica Cap de 510 (Balanceamento exigido pelo usuario)
            total_evs = sum(evs.values())
            if total_evs > 510:
                factor = 510.0 / total_evs
                for k in evs:
                    evs[k] = math.floor(evs[k] * factor)

        # Task 10.1: Natureza e Personality (Determinístico para Gen 1/2)
        personality = int(canonical.get("personality") or 0)
        if source_gen < 3 and personality == 0:
            personality = (ivs["atk"] & 0xF) | \
                          ((ivs["def"] & 0xF) << 4) | \
                          ((ivs["spe"] & 0xF) << 8) | \
                          ((ivs["spa"] & 0xF) << 12) | \
                          ((trainer_id & 0xFFFF) << 16)
            personality &= 0xFFFFFFFF

        nature_id = personality % 25
        modifiers = get_nature_modifiers(personality)
        
        # Resolucao de Ability Real (Gen 3)
        ability_name = canonical.get("ability")
        abilities = SPECIES_ABILITIES.get(national_id, [])
        if not ability_name or ability_name in {"0", "1"}:
            if abilities:
                ability_index = personality & 1
                ability_name = abilities[ability_index] if ability_index < len(abilities) else abilities[0]
        
        # Cálculo de Status
        base = base_data["stats"]
        max_hp = calculate_hp(base["hp"], ivs["hp"], evs["hp"], level, national_id)
        
        stats = BattleStats(
            hp=max_hp,
            atk=calculate_other_stat(base["atk"], ivs["atk"], evs["atk"], level, modifiers[0]),
            defen=calculate_other_stat(base["def"], ivs["def"], evs["def"], level, modifiers[1]),
            spe=calculate_other_stat(base["spe"], ivs["spe"], evs["spe"], level, modifiers[2]),
            spa=calculate_other_stat(base["spa"], ivs["spa"], evs["spa"], level, modifiers[3]),
            spd=calculate_other_stat(base["spd"], ivs["spd"], evs["spd"], level, modifiers[4]),
        )
        
        # Golpes
        battle_moves = []
        for m in canonical.get("moves", []):
            m_id = int(m.get("move_id") or 0)
            m_data = get_move_combat_data(m_id)
            if m_data:
                battle_moves.append(BattleMove(
                    move_id=m_id,
                    name=m_data["name"],
                    type=m_data["type"],
                    power=m_data["power"] or 0,
                    accuracy=m_data["accuracy"] or 100,
                    pp=m_data["pp"] or 0,
                    max_pp=m_data["pp"] or 0,
                    priority=m_data["priority"],
                    damage_class=m_data["damage_class"],
                    effect=m_data["effect"],
                    effect_chance=m_data.get("effect_chance")
                ))
        
        # Itens
        held_item_id = None
        if canonical.get("held_item"):
            held_item_id = int(canonical["held_item"].get("item_id") or 0)
        elif canonical.get("held_item_id"):
            held_item_id = int(canonical["held_item_id"])

        return cls(
            national_id=national_id,
            name=canonical.get("species_name") or base_data.get("name") or "Pokemon",
            nickname=canonical.get("nickname") or canonical.get("species_name") or "Pokemon",
            level=level,
            types=base_data["types"],
            base_stats=base,
            ivs=ivs,
            evs=evs,
            nature_id=nature_id,
            ability=ability_name or "none",
            max_hp=max_hp,
            current_hp=max_hp,
            stats=stats,
            held_item_id=held_item_id,
            moves=battle_moves,
            happiness=int(canonical.get("happiness", 70)),
            source_generation=source_gen,
            weight=base_data.get("weight", 50.0)
        )
