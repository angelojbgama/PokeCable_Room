from __future__ import annotations

GENDER_RATES_BY_NATIONAL_DEX: list[int | None] = [None, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 8, 8, 8, 0, 0, 0, 6, 6, 6, 6, 6, 6, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 4, 4, 4, 2, 2, 2, 2, 2, 2, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, -1, -1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, -1, -1, 4, 4, 4, 4, 0, 0, 4, 4, 4, 4, 4, 8, 4, 8, 4, 4, 4, 4, -1, -1, 4, 4, 8, 2, 2, 4, 0, 4, 4, 4, -1, 1, 1, 1, 1, -1, 1, 1, 1, 1, 1, 1, -1, -1, -1, 4, 4, 4, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 1, 1, 4, 4, 4, -1, 4, 4, 4, 4, 4, 4, 4, 6, 6, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, -1, 4, 4, 0, 0, 8, 2, 2, 8, 8, -1, -1, -1, 4, 4, 4, -1, -1, -1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, -1, 4, 4, 4, 2, 2, 6, 4, 6, 6, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 0, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, -1, -1, 4, 4, 4, 4, -1, -1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 1, 6, 4, 4, 4, -1, -1, -1, -1, -1, -1, 8, 0, -1, -1, -1, -1, -1]


def gender_rate_for_species(national_dex_id: int | None) -> int | None:
    dex_id = int(national_dex_id or 0)
    if dex_id <= 0 or dex_id >= len(GENDER_RATES_BY_NATIONAL_DEX):
        return None
    return GENDER_RATES_BY_NATIONAL_DEX[dex_id]


def gender_from_gen2_attack_dv(national_dex_id: int | None, attack_dv: int) -> str | None:
    rate = gender_rate_for_species(national_dex_id)
    if rate is None or rate < 0:
        return None
    if rate == 0:
        return "♂"
    if rate >= 8:
        return "♀"
    threshold = rate * 2 - 1
    return "♀" if int(attack_dv) <= threshold else "♂"


def gender_from_gen3_personality(national_dex_id: int | None, personality: int) -> str | None:
    rate = gender_rate_for_species(national_dex_id)
    if rate is None or rate < 0:
        return None
    if rate == 0:
        return "♂"
    if rate >= 8:
        return "♀"
    threshold = rate * 32
    return "♀" if (int(personality) & 0xFF) < threshold else "♂"
