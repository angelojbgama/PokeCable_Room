from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PokemonGen1, BattleMoveGen1

from .types import get_type_multiplier_gen1, is_special_type_gen1

def calculate_damage_gen1(
    attacker: PokemonGen1, 
    defender: PokemonGen1, 
    move: BattleMoveGen1, 
    is_critical: bool = False,
    random_factor: int | None = None
) -> tuple[int, float]:
    """
    Calcula o dano usando a formula exata da Geração 1.
    """
    move_type = move.type
    type_multiplier = get_type_multiplier_gen1(move_type, defender.types)
    
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
    is_special = is_special_type_gen1(move_type)
    
    if is_critical:
        # Crítico na Gen 1 ignora modificadores de status
        a = attacker.stats.special if is_special else attacker.stats.atk
        d = defender.stats.special if is_special else defender.stats.defen
    else:
        a = attacker.get_modified_stat("special") if is_special else attacker.get_modified_stat("atk")
        d = defender.get_modified_stat("special") if is_special else defender.get_modified_stat("defen")

    if d <= 0: d = 1
    
    level = attacker.level
    if is_critical: level *= 2
    
    # Formula Gen 1: floor(floor(floor(2 * L / 5 + 2) * P * A / D) / 50) + 2
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
