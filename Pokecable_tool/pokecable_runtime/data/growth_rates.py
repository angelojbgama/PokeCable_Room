from __future__ import annotations

SLOW = 1
MEDIUM_FAST = 2
FAST = 3
MEDIUM_SLOW = 4
ERRATIC = 5
FLUCTUATING = 6

GEN3_SPECIES_GROWTH_RATE_IDS: tuple[int, ...] = (
    0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 4, 4, 4, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 4, 4, 4, 4, 4, 4, 3, 3, 2, 2, 3, 3, 2, 2, 4, 4, 4, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    1, 1, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 4, 4, 4, 2,
    2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 1, 1, 3, 2, 2, 2, 2, 2, 2,
    1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 3, 3, 3,
    3, 2, 1, 1, 2, 3, 3, 3, 3, 2, 2, 4, 4, 4, 4, 3, 3, 2, 4, 4, 4, 4, 3, 4,
    4, 2, 2, 2, 2, 2, 4, 2, 3, 2, 2, 2, 2, 2, 2, 4, 2, 3, 3, 2, 2, 4, 1, 4,
    2, 2, 2, 2, 1, 1, 3, 2, 2, 3, 1, 1, 1, 1, 2, 2, 2, 2, 1, 3, 2, 2, 2, 2,
    2, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 1, 1, 1, 2, 2, 6, 6, 1,
    1, 1, 5, 5, 5, 4, 4, 4, 6, 6, 3, 2, 3, 3, 4, 3, 1, 1, 1, 2, 2, 1, 1, 2,
    2, 5, 6, 4, 6, 6, 1, 1, 6, 6, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5,
    6, 3, 3, 2, 2, 6, 6, 2, 2, 5, 5, 5, 5, 5, 5, 2, 4, 3, 3, 3, 3, 1, 3, 4,
    2, 2, 2, 4, 4, 4, 5, 5, 5, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1,
)


def growth_rate_id_for_national(national_dex_id: int) -> int | None:
    national_dex_id = int(national_dex_id)
    if national_dex_id < 1 or national_dex_id >= len(GEN3_SPECIES_GROWTH_RATE_IDS):
        return None
    value = GEN3_SPECIES_GROWTH_RATE_IDS[national_dex_id]
    return value or None


def experience_for_level(growth_rate_id: int, level: int) -> int:
    growth_rate_id = int(growth_rate_id)
    level = max(1, min(100, int(level)))
    cube = level * level * level
    if growth_rate_id == SLOW:
        return (5 * cube) // 4
    if growth_rate_id == MEDIUM_FAST:
        return cube
    if growth_rate_id == FAST:
        return (4 * cube) // 5
    if growth_rate_id == MEDIUM_SLOW:
        return (6 * cube) // 5 - 15 * level * level + 100 * level - 140
    if growth_rate_id == ERRATIC:
        if level <= 50:
            return cube * (100 - level) // 50
        if level <= 68:
            return cube * (150 - level) // 100
        if level <= 98:
            mod = level % 3
            factor = 1274 + mod * mod - 9 * mod - 20 * (level // 3)
            return cube * factor // 1000
        return cube * (160 - level) // 100
    if growth_rate_id == FLUCTUATING:
        if level <= 15:
            return cube * (((level + 1) // 3) + 24) // 50
        if level <= 35:
            return cube * (level + 14) // 50
        return cube * ((level // 2) + 32) // 50
    raise ValueError(f"Growth rate desconhecido: {growth_rate_id}")


def level_from_experience(growth_rate_id: int, experience: int) -> int:
    experience = max(0, int(experience))
    current_level = 1
    for level in range(1, 101):
        if experience < experience_for_level(growth_rate_id, level):
            return current_level
        current_level = level
    return 100


def level_from_species_experience(national_dex_id: int, experience: int) -> int:
    growth_rate_id = growth_rate_id_for_national(national_dex_id)
    if growth_rate_id is None:
        raise ValueError(f"Growth rate nao encontrado para National Dex #{national_dex_id}.")
    return level_from_experience(growth_rate_id, experience)
