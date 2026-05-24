from __future__ import annotations

from data.unown_forms import gen3_unown_form_from_personality


UNOWN_NATIONAL_DEX_ID = 201
WURMPLE_NATIONAL_DEX_ID = 265
SILCOON_NATIONAL_DEX_ID = 266
CASCOON_NATIONAL_DEX_ID = 268
SPINDA_NATIONAL_DEX_ID = 327


def normalize_personality(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value) & 0xFFFFFFFF
    except (TypeError, ValueError):
        return None


def gen3_unown_form(personality: int) -> str:
    return gen3_unown_form_from_personality(normalize_personality(personality) or 0)


def gen3_wurmple_branch(personality: int) -> str:
    normalized = normalize_personality(personality) or 0
    return "silcoon" if normalized % 10 < 5 else "cascoon"


def gen3_spinda_spot_signature(personality: int) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]]:
    normalized = normalize_personality(personality) or 0
    return tuple(
        (
            (((normalized >> (byte_index * 8)) & 0x0F) - 8),
            ((((normalized >> (byte_index * 8)) >> 4) & 0x0F) - 8),
        )
        for byte_index in range(4)
    )


def gen3_spinda_pattern_key(personality: int) -> str:
    return "|".join(f"{x:+d},{y:+d}" for x, y in gen3_spinda_spot_signature(personality))


def gen3_species_pid_traits(national_dex_id: int, personality: int) -> dict[str, object]:
    normalized = normalize_personality(personality)
    if normalized is None:
        return {}
    traits: dict[str, object] = {"personality": normalized}
    if int(national_dex_id) == UNOWN_NATIONAL_DEX_ID:
        traits["unown_form"] = gen3_unown_form(normalized)
    if int(national_dex_id) == WURMPLE_NATIONAL_DEX_ID:
        traits["wurmple_branch"] = gen3_wurmple_branch(normalized)
    if int(national_dex_id) == SPINDA_NATIONAL_DEX_ID:
        traits["spinda_pattern"] = gen3_spinda_pattern_key(normalized)
    return traits
