from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .battle_pokemon import BattlePokemon, BattleMove

from .battle_types import get_type_multiplier, is_special_type
from .battle_ability_effects import apply_ability_immunities

def get_hidden_power_data(pkmn: BattlePokemon) -> tuple[str, int]:
    """Calcula o Tipo e Poder do Hidden Power baseado nos IVs (Gen 3)."""
    ivs = pkmn.ivs
    a = ivs.get("hp", 0) & 1
    b = ivs.get("atk", 0) & 1
    c = ivs.get("defense", 0) & 1
    d = ivs.get("speed", 0) & 1
    e = ivs.get("special_attack", 0) & 1
    f = ivs.get("special_defense", 0) & 1
    
    t_val = math.floor(((a + 2*b + 4*c + 8*d + 16*e + 32*f) * 15) / 63)
    types = [
        "fighting", "flying", "poison", "ground", "rock", "bug", "ghost", "steel",
        "fire", "water", "grass", "electric", "psychic", "ice", "dragon", "dark"
    ]
    move_type = types[t_val]
    
    u = (ivs.get("hp", 0) >> 1) & 1
    v = (ivs.get("atk", 0) >> 1) & 1
    w = (ivs.get("defense", 0) >> 1) & 1
    x = (ivs.get("speed", 0) >> 1) & 1
    y = (ivs.get("special_attack", 0) >> 1) & 1
    z = (ivs.get("special_defense", 0) >> 1) & 1
    
    p_val = math.floor(((u + 2*v + 4*w + 8*x + 16*y + 32*z) * 40) / 63) + 30
    return move_type, p_val

def get_dynamic_power(attacker: BattlePokemon, defender: BattlePokemon, move: BattleMove, weather: str = "none") -> int:
    """Calcula o poder base de movimentos que variam conforme HP, Peso, Felicidade ou Clima (Gen 3)."""
    name = move.name.lower().replace("-", "").replace(" ", "")
    
    if name in ["flail", "reversal"]:
        n = attacker.current_hp
        m = attacker.max_hp
        ratio = (n * 48) // m
        if ratio >= 33: return 20
        if ratio >= 17: return 40
        if ratio >= 10: return 80
        if ratio >= 5: return 100
        if ratio >= 2: return 150
        return 200

    if name in ["eruption", "waterspout"]:
        p = math.floor(150 * attacker.current_hp / attacker.max_hp)
        return max(1, p)

    if name == "lowkick":
        w = defender.weight
        if w < 10: return 20
        if w < 25: return 40
        if w < 50: return 60
        if w < 100: return 80
        if w < 200: return 100
        return 120
        
    if name == "return":
        return max(1, math.floor(attacker.happiness / 2.5))
    if name == "frustration":
        return max(1, math.floor((255 - attacker.happiness) / 2.5))
        
    if name == "hiddenpower":
        _, p = get_hidden_power_data(attacker)
        return p
        
    if name == "weatherball" and weather != "none":
        return 100

    return move.power

def calculate_damage_gen1(
    attacker: BattlePokemon, 
    defender: BattlePokemon, 
    move: BattleMove, 
    is_critical: bool = False,
    random_factor: int | None = None
) -> tuple[int, float]:
    """
    Calcula o dano usando a formula da Geração 1.
    Retorna (dano_final, multiplicador_tipo).
    """
    move_type = move.type
    type_multiplier = get_type_multiplier(move_type, defender.types, generation=1)

    if type_multiplier > 0:
        move_name_lower = move.name.lower().replace("-", "").replace(" ", "")
        if move_name_lower in ["horndrill", "fissure", "guillotine"]:
            return defender.current_hp, type_multiplier
        if move_name_lower in ["seismictoss", "nightshade"]:
            return attacker.level, type_multiplier
        elif move_name_lower == "dragonrage":
            return 40, type_multiplier
        elif move_name_lower == "sonicboom":
            return 20, type_multiplier
        elif move_name_lower == "psywave":
            dmg = math.floor(attacker.level * (random.randint(0, 100) + 50) / 100)
            return max(1, dmg), type_multiplier

    if move.power <= 0 or move.damage_class == "status":
        return 0, type_multiplier

    # Stats: Na Gen 1, Special Attack = Special Defense
    is_special = is_special_type(move_type, generation=1)

    if is_critical:
        # Crítico na Gen 1 ignora modificadores de status
        a = attacker.stats.spa if is_special else attacker.stats.atk
        d = defender.stats.spa if is_special else defender.stats.defen
    else:
        a = attacker.get_modified_stat("spa") if is_special else attacker.get_modified_stat("atk")
        d = defender.get_modified_stat("spa") if is_special else defender.get_modified_stat("def")

    if d <= 0: d = 1

    level = attacker.level
    if is_critical: level *= 2

    v = math.floor(math.floor(math.floor(2 * level / 5 + 2) * move.power * a / d) / 50) + 2

    # STAB
    if move_type in attacker.types:
        v = math.floor(v * 1.5)

    # Tipo
    v = math.floor(v * type_multiplier)

    # Random Factor (217-255) / 255
    if random_factor is None:
        random_factor = random.randint(217, 255)
    v = math.floor(v * random_factor / 255)

    if type_multiplier > 0 and v <= 0: v = 1
    return int(v), type_multiplier

def calculate_damage(
    attacker: BattlePokemon, 
    defender: BattlePokemon, 
    move: BattleMove, 
    is_critical: bool = False,
    weather: str = "none",
    defender_semi_invulnerable: str | None = None,
    defending_side: Any = None,
    random_factor: int | None = None,
    generation: int = 3
) -> tuple[int, float]:
    """
    Calcula o dano de um golpe usando a formula da geracao correspondente.
    Retorna (dano_final, multiplicador_tipo).
    """
    if generation == 1:
        return calculate_damage_gen1(attacker, defender, move, is_critical, random_factor)

    move_type = move.type
    move_name_lower = move.name.lower().replace("-", "").replace(" ", "")

    
    if move_name_lower == "hiddenpower":
        move_type, _ = get_hidden_power_data(attacker)
        
    if move_name_lower == "weatherball":
        if weather == "rain": move_type = "water"
        elif weather == "sun": move_type = "fire"
        elif weather == "sandstorm": move_type = "rock"
        elif weather == "hail": move_type = "ice"

    type_multiplier = get_type_multiplier(move_type, defender.types)
    ability_multiplier = apply_ability_immunities(move, defender, type_multiplier)
    if ability_multiplier is not None:
        type_multiplier = ability_multiplier

    if type_multiplier > 0:
        if move_name_lower in ["horndrill", "fissure", "guillotine", "sheercold"]:
            if defender.ability == "sturdy": return 0, type_multiplier
            return defender.current_hp, type_multiplier

        if move_name_lower in ["seismictoss", "nightshade"]:
            return attacker.level, type_multiplier
        elif move_name_lower == "dragonrage":
            return 40, type_multiplier
        elif move_name_lower == "sonicboom":
            return 20, type_multiplier
        elif move_name_lower == "psywave":
            dmg = math.floor(attacker.level * (random.randint(0, 100) + 50) / 100)
            return max(1, dmg), type_multiplier

    move_power = get_dynamic_power(attacker, defender, move, weather)
    if move_power <= 0 and move.damage_class != "status": return 0, type_multiplier
    if move.damage_class == "status": return 0, type_multiplier
    
    # 1. Determinar Stats de Ataque (A) e Defesa (D)
    is_special = is_special_type(move_type)
    ignore_burn = move_name_lower == "facade"
    
    if is_special:
        spa_stage = attacker.stat_stages.get("spa", 0)
        spd_stage = defender.stat_stages.get("spd", 0)
        if is_critical:
            a = attacker.get_modified_stat("spa", weather, stage_override=max(0, spa_stage))
            d = defender.get_modified_stat("spd", weather, stage_override=min(0, spd_stage))
        else:
            a = attacker.get_modified_stat("spa", weather)
            d = defender.get_modified_stat("spd", weather)
            
        # Task 9.3: Species Boost (Offensive Special)
        a_item = attacker.item_data
        if a_item and a_item.get("effect_type") == "species_boost" and attacker.national_id in a_item.get("species", []):
            if a_item.get("stat") == "spa" or a_item.get("stat") == "special":
                a = math.floor(a * a_item.get("value", 2.0))
        
        # Task 9.3: Species Boost (Defensive Special)
        d_item = defender.item_data
        if d_item and d_item.get("effect_type") == "species_boost" and defender.national_id in d_item.get("species", []):
            if d_item.get("stat") == "spd" or d_item.get("stat") == "special":
                d = math.floor(d * d_item.get("value", 2.0))

        if weather == "sandstorm" and "rock" in defender.types:
            d = math.floor(d * 1.5)
    else:
        atk_stage = attacker.stat_stages.get("atk", 0)
        def_stage = defender.stat_stages.get("def", 0)
        if is_critical:
            a = attacker.get_modified_stat("atk", weather, stage_override=max(0, atk_stage), ignore_burn_penalty=ignore_burn)
            d = defender.get_modified_stat("def", weather, stage_override=min(0, def_stage))
        else:
            a = attacker.get_modified_stat("atk", weather, ignore_burn_penalty=ignore_burn)
            d = defender.get_modified_stat("def", weather)
            
        # Task 9.3: Species Boost (Offensive Physical)
        a_item = attacker.item_data
        if a_item and a_item.get("effect_type") == "species_boost" and attacker.national_id in a_item.get("species", []):
            if a_item.get("stat") == "atk":
                a = math.floor(a * a_item.get("value", 2.0))

    # Item Boost (Stats)
    if not is_special:
        if attacker.ability in ["huge-power", "pure-power"]: a *= 2
        item = attacker.item_data
        if item and item.get("effect_type") == "boost_stat" and item.get("stat") == "atk":
            a = math.floor(a * item.get("value", 1.5))

    # 2. Formula Base de Dano (Gen 3)
    level_factor = math.floor(2 * attacker.level / 5 + 2)
    if d <= 0: d = 1
    if move_name_lower == "facade" and attacker.status_condition: move_power *= 2
    
    v = math.floor(math.floor(level_factor * move_power * a / d) / 50) + 2

    # 3. Modificadores Sequenciais
    if defender.ability == "thick-fat" and move_type in ["fire", "ice"]: v = math.floor(v * 0.5)

    if weather == "rain":
        if move_type == "water": v = math.floor(v * 1.5)
        elif move_type == "fire": v = math.floor(v * 0.5)
    elif weather == "sun":
        if move_type == "fire": v = math.floor(v * 1.5)
        elif move_type == "water": v = math.floor(v * 0.5)

    if is_critical: v = math.floor(v * 2.0)
    if random_factor is None: random_factor = random.randint(85, 100)
    v = math.floor(v * random_factor / 100)
    if move_type in attacker.types: v = math.floor(v * 1.5)

    if type_multiplier == 0: v = 0
    elif type_multiplier == 0.25: v = math.floor(v * 0.25)
    elif type_multiplier == 0.5: v = math.floor(v * 0.5)
    elif type_multiplier == 2.0: v = math.floor(v * 2.0)
    elif type_multiplier == 4.0: v = math.floor(v * 4.0)

    if not is_critical and defending_side:
        if not is_special and defending_side.reflect_turns > 0:
            multiplier = 0.5 if len(defending_side.active_indices) == 1 else 0.66
            v = math.floor(v * multiplier)
        elif is_special and defending_side.light_screen_turns > 0:
            multiplier = 0.5 if len(defending_side.active_indices) == 1 else 0.66
            v = math.floor(v * multiplier)

    if defender_semi_invulnerable == "dig" and move_name_lower in ["earthquake", "magnitude"]:
        v = math.floor(v * 2.0)
    
    if type_multiplier > 0 and v <= 0: v = 1
    return int(v), type_multiplier
