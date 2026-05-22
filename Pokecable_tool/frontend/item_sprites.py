from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import pygame

from frontend.paths import ASSETS_DIR


logger = logging.getLogger("r36s_pokecable_ui")
ITEM_SPRITE_ROOT = ASSETS_DIR / "item_sprites"
ITEM_SPRITE_ITEMS_DIR = ITEM_SPRITE_ROOT / "items"
ITEM_SPRITE_MANIFEST = ITEM_SPRITE_ROOT / "manifest.json"

_MANIFEST: dict[str, Any] | None = None
_SURFACES: dict[str, pygame.Surface | None] = {}

GROUP_PREFERENCE_BY_CATEGORY = {
    "ball": ("ball",),
    "berry": ("berry",),
    "key_item": ("key-item",),
    "tm": ("tm",),
    "hm": ("tm",),
    "tmhm": ("tm",),
    "hold_item": ("held-item", "ev-item", "incense", "scarf", "plate", "other-item"),
    "item": ("medicine", "other-item", "valuable-item", "battle-item", "berry", "ball"),
}


def _slug(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("'", "").replace(".", "").replace(":", "").replace(",", "")
    value = value.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def _manifest() -> dict[str, Any]:
    global _MANIFEST
    if _MANIFEST is not None:
        return _MANIFEST
    try:
        _MANIFEST = json.loads(ITEM_SPRITE_MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Item sprite manifest unavailable: %s", exc)
        _MANIFEST = {}
    return _MANIFEST


def _candidate_aliases(item_info: dict[str, Any]) -> list[str]:
    name = str(item_info.get("name") or "")
    item_id = str(item_info.get("id") or "")
    aliases = [_slug(name)]
    if name.lower().endswith(" berry"):
        aliases.append(_slug(name[:-6]))
    if name.lower().endswith(" ball"):
        aliases.append(_slug(name[:-5]))
    if item_id:
        aliases.append(_slug(f"item-{item_id}"))
    seen: set[str] = set()
    return [alias for alias in aliases if alias and not (alias in seen or seen.add(alias))]


def _prefer_by_category(paths: list[str], category: str) -> str:
    preferred_groups = GROUP_PREFERENCE_BY_CATEGORY.get(str(category or ""), ())
    for group in preferred_groups:
        for path in paths:
            if path.startswith(f"{group}/"):
                return path
    return paths[0] if paths else ""


def item_sprite_path(item_info: dict[str, Any] | None) -> Path | None:
    if not item_info:
        return None
    manifest = _manifest()
    aliases = manifest.get("aliases") if isinstance(manifest, dict) else {}
    if not isinstance(aliases, dict):
        return None
    for alias in _candidate_aliases(item_info):
        paths = aliases.get(alias) or []
        if not isinstance(paths, list) or not paths:
            continue
        rel = _prefer_by_category([str(path) for path in paths], str(item_info.get("category") or ""))
        if not rel:
            continue
        path = ITEM_SPRITE_ITEMS_DIR / rel
        if path.exists():
            return path
    return None


def _load_surface(path: Path) -> pygame.Surface | None:
    key = str(path)
    if key in _SURFACES:
        return _SURFACES[key]
    try:
        surface = pygame.image.load(key)
        try:
            surface = surface.convert_alpha()
        except pygame.error:
            surface = surface.copy()
    except Exception as exc:
        logger.debug("Item sprite load failed: %s", exc)
        surface = None
    _SURFACES[key] = surface
    return surface


def draw_item_sprite(surface: pygame.Surface, area: pygame.Rect, item_info: dict[str, Any] | None, fill) -> bool:
    path = item_sprite_path(item_info)
    if path is None:
        return False
    sprite = _load_surface(path)
    if sprite is None:
        return False
    pygame.draw.rect(surface, fill, area, 0)
    target_size = (max(1, area.w), max(1, area.h))
    scaled = pygame.transform.scale(sprite, target_size)
    surface.blit(scaled, area.topleft)
    return True
