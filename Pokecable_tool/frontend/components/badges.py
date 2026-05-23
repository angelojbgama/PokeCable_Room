"""Badge metadata and sprite loading helpers."""
from __future__ import annotations

from typing import Iterable

import pygame
from frontend.paths import ASSETS_DIR

ASSETS_ROOT = ASSETS_DIR / "badges"

KANTO_SLOTS = ("boulder", "cascade", "thunder", "rainbow", "soul", "marsh", "volcano", "earth")
JOHTO_SLOTS = ("zephyr", "hive", "plain", "fog", "storm", "mineral", "glacier", "rising")
HOENN_SLOTS = ("stone", "knuckle", "dynamo", "heat", "balance", "feather", "mind", "rain")

GAME_BADGE_SETS: dict[str, tuple[str, tuple[str, ...]]] = {
    "pokemon_red": ("gen1", KANTO_SLOTS),
    "pokemon_blue": ("gen1", KANTO_SLOTS),
    "pokemon_yellow": ("gen1", KANTO_SLOTS),
    "pokemon_gold": ("gen2", JOHTO_SLOTS),
    "pokemon_silver": ("gen2", JOHTO_SLOTS),
    "pokemon_crystal": ("gen2", JOHTO_SLOTS),
    "pokemon_ruby": ("gen3_emerald", HOENN_SLOTS),
    "pokemon_sapphire": ("gen3_emerald", HOENN_SLOTS),
    "pokemon_emerald": ("gen3_emerald", HOENN_SLOTS),
    "pokemon_firered": ("gen3_firered", KANTO_SLOTS),
    "pokemon_leafgreen": ("gen3_firered", KANTO_SLOTS),
}

_sprite_cache: dict[tuple[str, str], pygame.Surface] = {}


def badge_slots_for(game_id: str) -> tuple[str, ...]:
    entry = GAME_BADGE_SETS.get(game_id)
    return entry[1] if entry else ()


def load_badge_sprite(game_id: str, slot: str) -> pygame.Surface | None:
    entry = GAME_BADGE_SETS.get(game_id)
    if not entry:
        return None
    folder, slots = entry
    if slot not in slots:
        return None
    cache_key = (folder, slot)
    cached = _sprite_cache.get(cache_key)
    if cached is not None:
        return cached
    path = ASSETS_ROOT / folder / f"{slot}.png"
    if not path.exists():
        return None
    surface = pygame.image.load(str(path)).convert_alpha()
    _sprite_cache[cache_key] = surface
    return surface


def draw_badge_strip(
    screen: pygame.Surface,
    origin: tuple[int, int],
    game_id: str,
    earned: Iterable[bool] | dict[str, bool] | int,
    *,
    size: int = 16,
    spacing: int = 4,
    dim_alpha: int = 60,
) -> int:
    """Draw 8 badge icons starting at origin. Dim unearned ones. Returns width drawn."""
    slots = badge_slots_for(game_id)
    if not slots:
        return 0
    if isinstance(earned, int):
        flags = [bool((earned >> i) & 1) for i in range(len(slots))]
    elif isinstance(earned, dict):
        flags = [bool(earned.get(s, False)) for s in slots]
    else:
        flags = list(earned)
        flags += [False] * (len(slots) - len(flags))
    x0, y0 = origin
    drawn = 0
    for idx, slot in enumerate(slots):
        sprite = load_badge_sprite(game_id, slot)
        if sprite is None:
            continue
        scaled = pygame.transform.scale(sprite, (size, size)) if sprite.get_width() != size else sprite
        if not flags[idx]:
            faded = scaled.copy()
            faded.set_alpha(dim_alpha)
            screen.blit(faded, (x0 + idx * (size + spacing), y0))
        else:
            screen.blit(scaled, (x0 + idx * (size + spacing), y0))
        drawn += 1
    return drawn * size + max(0, drawn - 1) * spacing
