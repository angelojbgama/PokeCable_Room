from __future__ import annotations

from pathlib import Path

import pygame

from frontend.paths import ASSETS_DIR

UI_FONT_PATH = ASSETS_DIR / "fonts" / "Pokemon Classic.ttf"
POKECABLE_TITLE_FONT_PATH = ASSETS_DIR / "fonts" / "Ketchum.otf"

FONT_CACHE = {}
TITLE_FONT_CACHE = {}


def font(size, bold=False):
    key = (int(size), bool(bold))
    cached = FONT_CACHE.get(key)
    if cached is not None:
        return cached

    adjusted_size = max(8, int(size) - 2 if UI_FONT_PATH.name == "Pokemon Classic.ttf" else int(size))
    candidates = [
        UI_FONT_PATH,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            FONT_CACHE[key] = pygame.font.Font(str(path), adjusted_size)
            return FONT_CACHE[key]
    FONT_CACHE[key] = pygame.font.SysFont(None, adjusted_size, bold=bold)
    return FONT_CACHE[key]


def title_font(size):
    key = int(size)
    cached = TITLE_FONT_CACHE.get(key)
    if cached is not None:
        return cached

    if POKECABLE_TITLE_FONT_PATH.exists():
        TITLE_FONT_CACHE[key] = pygame.font.Font(POKECABLE_TITLE_FONT_PATH, size)
        return TITLE_FONT_CACHE[key]
    TITLE_FONT_CACHE[key] = font(size, False)
    return TITLE_FONT_CACHE[key]
