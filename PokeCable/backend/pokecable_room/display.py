from __future__ import annotations

import re

from pokecable_room.data.species import SPECIES_NAMES_BY_NATIONAL


_SPECIES_PLACEHOLDER_RE = re.compile(r"^species\s*#\s*\d+$", re.IGNORECASE)


def _clean_text(value: str | None) -> str:
    return " ".join(str(value or "").replace("\x00", "").strip().split())


def _canonical_compare(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", _clean_text(value).lower())


def _species_display_name(national_dex_id: int | None, species_name: str) -> str:
    cleaned = _clean_text(species_name)
    if national_dex_id is not None:
        mapped = SPECIES_NAMES_BY_NATIONAL.get(int(national_dex_id))
        if mapped and (not cleaned or _SPECIES_PLACEHOLDER_RE.match(cleaned) or cleaned.casefold().startswith("species #")):
            return mapped
    return cleaned or (f"Species #{national_dex_id}" if national_dex_id is not None else "Pokemon")


def normalize_pokemon_display(
    national_dex_id: int | None,
    species_name: str,
    level: int,
    nickname: str | None = None,
    gender: str | None = None,
    unown_form: str | None = None,
    held_item_name: str | None = None,
) -> str:
    """Return the compact display string used by R36S and web clients."""
    display_name = _species_display_name(national_dex_id, species_name)
    if int(national_dex_id or 0) == 201 and unown_form:
        display_name = f"{display_name} ({_clean_text(unown_form)})"
    dex_prefix = f"#{int(national_dex_id)} " if national_dex_id is not None and int(national_dex_id) > 0 else ""
    gender_text = f" {gender.strip()}" if gender and gender.strip() else ""
    text = f"{dex_prefix}{display_name}{gender_text} Lv. {int(level)}"
    text += f" — Item: {held_item_name}" if held_item_name else " — Sem item"
    cleaned_nickname = _clean_text(nickname)
    if cleaned_nickname and _canonical_compare(cleaned_nickname) != _canonical_compare(display_name):
        text += f' "{cleaned_nickname}"'
    return text
