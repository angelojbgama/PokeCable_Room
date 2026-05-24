from __future__ import annotations

import logging
import os
import threading
import time

import pygame

from frontend.paths import ASSETS_DIR
from pokecable_save import _ensure_backend_import_path


logger = logging.getLogger("r36s_pokecable_ui")
POKEMON_SPRITE_ASSET_DIR = ASSETS_DIR / "pokemon_sprites"
SPRITE_CACHE_VERSION = "pixel-v1"
SPRITE_LOADING_MAX_SECONDS = float(os.getenv("POKECABLE_SPRITE_LOADING_MAX_SECONDS", "3"))
UNOWN_FORM_NAMES = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ("!", "?")


def pokemon_sprite_slug(name):
    value = str(name or "").strip().lower()
    replacements = {
        "mr. mime": "mr-mime",
        "farfetch'd": "farfetchd",
        "nidoran f": "nidoran-f",
        "nidoran m": "nidoran-m",
        "ho-oh": "ho-oh",
    }
    if value in replacements:
        return replacements[value]
    value = value.replace("♀", "-f").replace("♂", "-m")
    for token in ["'", ".", ":", ",", "(", ")", "[", "]"]:
        value = value.replace(token, "")
    value = value.replace(" ", "-")
    value = value.replace("--", "-")
    return value


def sprite_form_slug(form):
    value = str(form or "").strip().lower()
    if not value or value == "a":
        return ""
    if value == "!":
        return "exclamation"
    if value == "?":
        return "question"
    value = value.replace("!", "exclamation").replace("?", "question")
    for token in ["'", ".", ":", ",", "(", ")", "[", "]"]:
        value = value.replace(token, "")
    value = value.replace(" ", "-").replace("_", "-")
    while "--" in value:
        value = value.replace("--", "-")
    return value.strip("-")


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _first_present(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return ""


def _payload_national_dex_id(pokemon, raw, canonical):
    species_block = canonical.get("species", {}) if isinstance(canonical, dict) else {}
    for value in (
        (pokemon or {}).get("national_dex_id") if isinstance(pokemon, dict) else None,
        raw.get("national_dex_id") if isinstance(raw, dict) else None,
        canonical.get("species_national_id") if isinstance(canonical, dict) else None,
        species_block.get("national_dex_id") if isinstance(species_block, dict) else None,
    ):
        national_id = _safe_int(value)
        if national_id > 0:
            return national_id
    return 0


def _unown_form_name(value):
    if value in (None, ""):
        return ""
    if isinstance(value, int):
        return UNOWN_FORM_NAMES[value] if 0 <= value < len(UNOWN_FORM_NAMES) else ""
    text = str(value).strip()
    if not text:
        return ""
    if text.isdigit():
        index = int(text)
        return UNOWN_FORM_NAMES[index] if 0 <= index < len(UNOWN_FORM_NAMES) else ""
    upper = text.upper()
    return upper if upper in UNOWN_FORM_NAMES else text


def pokemon_sprite_variant(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    metadata = (pokemon or {}).get("metadata", {}) if isinstance(pokemon, dict) else {}
    raw_metadata = raw.get("metadata", {}) if isinstance(raw, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    canonical_metadata = canonical.get("metadata", {}) if isinstance(canonical, dict) else {}
    is_shiny = bool(
        (pokemon or {}).get("is_shiny")
        or (raw.get("is_shiny") if isinstance(raw, dict) else False)
        or (metadata.get("is_shiny") if isinstance(metadata, dict) else False)
        or (raw_metadata.get("is_shiny") if isinstance(raw_metadata, dict) else False)
        or (canonical.get("is_shiny") if isinstance(canonical, dict) else False)
        or (canonical_metadata.get("is_shiny") if isinstance(canonical_metadata, dict) else False)
    )
    national_dex_id = _payload_national_dex_id(pokemon, raw, canonical)
    species_name = str((pokemon or {}).get("species_name") or canonical.get("species_name") or "").strip().lower()
    if national_dex_id == 201 or species_name == "unown":
        form = _unown_form_name(
            _first_present(
                (pokemon or {}).get("unown_form"),
                metadata.get("unown_form") if isinstance(metadata, dict) else "",
                raw.get("unown_form") if isinstance(raw, dict) else "",
                raw_metadata.get("unown_form") if isinstance(raw_metadata, dict) else "",
                canonical_metadata.get("unown_form") if isinstance(canonical_metadata, dict) else "",
                (pokemon or {}).get("form"),
                metadata.get("form") if isinstance(metadata, dict) else "",
                raw.get("form") if isinstance(raw, dict) else "",
                raw_metadata.get("form") if isinstance(raw_metadata, dict) else "",
                canonical_metadata.get("form") if isinstance(canonical_metadata, dict) else "",
            )
        )
    else:
        form = (
            (pokemon or {}).get("form")
            or (metadata.get("form") if isinstance(metadata, dict) else "")
            or (raw.get("form") if isinstance(raw, dict) else "")
            or (raw_metadata.get("form") if isinstance(raw_metadata, dict) else "")
            or (canonical_metadata.get("form") if isinstance(canonical_metadata, dict) else "")
        )
    return "shiny" if is_shiny else "normal", sprite_form_slug(form)


def resolve_sprite_national_dex_id(generation, species_id, pokemon=None):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    species_block = canonical.get("species", {}) if isinstance(canonical, dict) else {}
    for value in (
        (pokemon or {}).get("national_dex_id") if isinstance(pokemon, dict) else None,
        raw.get("national_dex_id") if isinstance(raw, dict) else None,
        canonical.get("species_national_id") if isinstance(canonical, dict) else None,
        species_block.get("national_dex_id") if isinstance(species_block, dict) else None,
    ):
        try:
            national_id = int(value or 0)
        except (TypeError, ValueError):
            national_id = 0
        if national_id > 0:
            return national_id
    try:
        generation = int(generation or 0)
        species_id = int(species_id or 0)
        if generation <= 0 or species_id <= 0:
            return 0
        _ensure_backend_import_path()
        from data.species import native_to_national  # type: ignore

        return int(native_to_national(generation, species_id) or 0)
    except Exception as exc:
        logger.debug(
            "Sprite national dex lookup failed: generation=%s species_id=%s error=%s",
            generation,
            species_id,
            exc,
        )
        return 0


class SpriteLoader:
    def __init__(self, server_url: str):
        self.lock = threading.Lock()
        self.asset_dir = POKEMON_SPRITE_ASSET_DIR
        self.current_key = ""
        self.entries = {}
        del server_url

    def _identity(self, pokemon):
        species_name = pokemon.get("species_name") if pokemon else ""
        species_id = int((pokemon or {}).get("species_id") or 0)
        if not pokemon or (not species_name and not species_id) or species_name.lower() == "egg":
            return "", {}

        generation = int((pokemon or {}).get("generation") or 0)
        national_dex_id = resolve_sprite_national_dex_id(generation, species_id, pokemon)
        slug = pokemon_sprite_slug(species_name)
        if not slug and not national_dex_id:
            return "", {}
        variant, form = pokemon_sprite_variant(pokemon)
        sprite_id = self._sprite_id(national_dex_id, slug, form)
        key = f"{SPRITE_CACHE_VERSION}-{variant}-{sprite_id}-front"
        lookup = {
            "generation": generation,
            "species_slug": slug,
            "species_id": species_id,
            "national_dex_id": national_dex_id,
            "sprite_id": sprite_id,
            "variant": variant,
        }
        return key, lookup

    @staticmethod
    def _sprite_id(national_dex_id, species_slug="", form=""):
        base = str(int(national_dex_id)) if int(national_dex_id or 0) else str(species_slug or "")
        form = sprite_form_slug(form)
        if form:
            return f"{base}-{form}"
        return base

    def request(self, pokemon):
        self.request_for(pokemon)

    def request_for(self, pokemon):
        species_name = pokemon.get("species_name") if pokemon else ""
        species_id = int((pokemon or {}).get("species_id") or 0)
        logger.debug("Sprite request: species_id=%s species_name=%s", species_id, species_name)
        key, lookup = self._identity(pokemon)
        with self.lock:
            self.current_key = key
            if not key:
                return
            entry = self.entries.get(key)
            if entry and (entry.get("loading") or entry.get("surface") is not None):
                return
            self.entries[key] = {"surface": None, "loading": True, "error": "", "started_at": time.monotonic()}
        self._load(key, lookup)

    def _sprite_path(self, lookup):
        variant = str(lookup.get("variant") or "normal")
        sprite_id = str(lookup.get("sprite_id") or lookup.get("national_dex_id") or lookup.get("species_slug") or "")
        if not sprite_id:
            return None
        return self.asset_dir / variant / f"{sprite_id}.png"

    def _load(self, key, lookup):
        try:
            sprite_path = self._sprite_path(lookup)
            if not sprite_path or not sprite_path.exists():
                raise RuntimeError(f"local sprite not found: {sprite_path}")
            surface = pygame.image.load(str(sprite_path)).convert_alpha()
            bounds = surface.get_bounding_rect(min_alpha=1)
            if bounds.width > 0 and bounds.height > 0:
                cropped = surface.subsurface(bounds).copy()
                padded = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                pad_x = (surface.get_width() - cropped.get_width()) // 2
                pad_y = (surface.get_height() - cropped.get_height()) // 2
                padded.blit(cropped, (pad_x, pad_y))
                surface = padded
            error = ""
        except Exception as exc:
            surface = None
            error = str(exc)
            logger.warning("Sprite load failed: key=%s error=%s", key, exc)

        with self.lock:
            self.entries[key] = {"surface": surface, "loading": False, "error": error}

    def snapshot(self):
        return self.snapshot_key(self.current_key)

    def snapshot_for(self, pokemon):
        key, _ = self._identity(pokemon)
        return self.snapshot_key(key)

    def snapshot_key(self, key):
        with self.lock:
            entry = self.entries.get(key or "", {})
            loading = bool(entry.get("loading"))
            if loading and time.monotonic() - float(entry.get("started_at") or 0) > SPRITE_LOADING_MAX_SECONDS:
                loading = False
            return entry.get("surface"), loading, str(entry.get("error") or "")
