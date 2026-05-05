from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import BattleMoveGen2, PokemonGen2

from .types import get_type_multiplier_gen2, is_special_type_gen2


def calculate_damage_gen2(
    attacker: PokemonGen2,
    defender: PokemonGen2,
    move: BattleMoveGen2,
    is_critical: bool = False,
    random_factor: int | None = None,
    *,
    power_override: int | None = None,
    weather: str | None = None,
) -> tuple[int, float]:
    move_type = move.type
    type_multiplier = get_type_multiplier_gen2(move_type, defender.types)
    effective_power = move.power if power_override is None else power_override

    if type_multiplier > 0:
        move_name_lower = move.name.lower().replace("-", "").replace(" ", "")
        if move_name_lower in ["horndrill", "fissure", "guillotine", "sheercold"]:
            return defender.current_hp, type_multiplier
        if move_name_lower in ["seismictoss", "nightshade"]:
            return attacker.level, type_multiplier
        if move_name_lower == "dragonrage":
            return 40, type_multiplier
        if move_name_lower == "sonicboom":
            return 20, type_multiplier
        if move_name_lower == "psywave":
            dmg = math.floor(attacker.level * (random.randint(0, 100) + 50) / 100)
            return max(1, dmg), type_multiplier

    if effective_power <= 0 or move.damage_class == "status":
        return 0, type_multiplier

    is_special = is_special_type_gen2(move_type)

    if is_critical:
        a = attacker.stats.spa if is_special else attacker.stats.atk
        d = defender.stats.spd if is_special else defender.stats.defen
    else:
        a = attacker.get_modified_stat("spa") if is_special else attacker.get_modified_stat("atk")
        d = defender.get_modified_stat("spd") if is_special else defender.get_modified_stat("def")

    if d <= 0:
        d = 1

    level = attacker.level
    if is_critical:
        level *= 2

    v = math.floor(math.floor(math.floor(2 * level / 5 + 2) * effective_power * a / d) / 50) + 2

    if weather == "rain":
        if move_type == "water":
            v = math.floor(v * 1.5)
        elif move_type == "fire":
            v = math.floor(v * 0.5)
    elif weather == "sun":
        if move_type == "fire":
            v = math.floor(v * 1.5)
        elif move_type == "water":
            v = math.floor(v * 0.5)

    if move_type in attacker.types:
        v = math.floor(v * 1.5)

    v = math.floor(v * type_multiplier)

    if random_factor is None:
        random_factor = random.randint(217, 255)
    v = math.floor(v * random_factor / 255)

    if type_multiplier > 0 and v <= 0:
        v = 1
    return int(v), type_multiplier
