from __future__ import annotations

UNOWN_FORM_NAMES: tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ("!", "?")


def gen2_unown_form_from_dvs(attack_dv: int, defense_dv: int, speed_dv: int, special_dv: int) -> str:
    value = (
        ((int(attack_dv) & 0x6) << 5)
        | ((int(defense_dv) & 0x6) << 3)
        | ((int(speed_dv) & 0x6) << 1)
        | ((int(special_dv) & 0x6) >> 1)
    )
    return UNOWN_FORM_NAMES[min(25, value // 10)]


def gen3_unown_form_from_personality(personality: int) -> str:
    value = (
        ((int(personality) & 0x03000000) >> 18)
        | ((int(personality) & 0x00030000) >> 12)
        | ((int(personality) & 0x00000300) >> 6)
        | (int(personality) & 0x00000003)
    ) % 28
    return UNOWN_FORM_NAMES[value]


def gen3_unown_form(species_id: int, personality: int) -> str | None:
    species_id = int(species_id)
    if species_id == 201:
        return gen3_unown_form_from_personality(personality)
    if 252 <= species_id <= 276:
        return UNOWN_FORM_NAMES[species_id - 251]
    return None
