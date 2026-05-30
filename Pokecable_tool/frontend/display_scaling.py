from __future__ import annotations

import os
import logging
from dataclasses import dataclass

import pygame


logger = logging.getLogger("pokecable.display")

@dataclass(frozen=True)
class DisplayConfig:
    logical_size: tuple[int, int] = (640, 480)
    flags: int = 0
    scaled: bool = False


def create_display(logical_size: tuple[int, int]) -> tuple[pygame.Surface, DisplayConfig]:
    flags = 0
    scaled = os.getenv("POKECABLE_DISABLE_SCALE", "0").lower() not in ("1", "true", "yes")
    fullscreen = os.getenv("POKECABLE_FULLSCREEN", "0").lower() in ("1", "true", "yes")
    if fullscreen:
        flags |= pygame.FULLSCREEN
    if scaled and hasattr(pygame, "SCALED"):
        flags |= pygame.SCALED
    try:
        screen = pygame.display.set_mode(logical_size, flags)
    except pygame.error as exc:
        logger.error("Display set_mode failed with flags=%s logical_size=%s: %s", flags, logical_size, exc)
        flags &= ~getattr(pygame, "SCALED", 0)
        screen = pygame.display.set_mode(logical_size, flags)
        scaled = False
        logger.info("Display fallback without SCALED succeeded: flags=%s logical_size=%s", flags, logical_size)
    logger.info(
        "Display ready: logical_size=%s window_size=%s flags=%s scaled=%s driver=%s",
        logical_size,
        screen.get_size(),
        flags,
        scaled,
        pygame.display.get_driver(),
    )
    return screen, DisplayConfig(logical_size=logical_size, flags=flags, scaled=scaled)
