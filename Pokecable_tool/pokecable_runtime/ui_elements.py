from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(slots=True)
class Scrollbar:
    """Reusable scrollbar component for list-style screens."""

    thumb_color: tuple[int, int, int] = (24, 212, 242)
    border_color: tuple[int, int, int] = (40, 36, 93)
    rail_color: tuple[int, int, int] = (238, 248, 255)
    hinge_rect: tuple[int, int, int, int] = (307, 54, 25, 370)
    track_width: int = 11
    rail_width: int = 7
    thumb_min_height: int = 24

    def _track_rect(self) -> pygame.Rect:
        hinge = pygame.Rect(self.hinge_rect)
        return pygame.Rect(
            hinge.x + (hinge.w - self.track_width) // 2,
            hinge.y + 10,
            self.track_width,
            hinge.h - 20,
        )

    def _draw_track(self, surface, track, offset, total, visible) -> None:
        if total <= visible:
            return

        max_offset = max(1, total - visible)
        rail = pygame.Rect(track.x + (track.w - self.rail_width) // 2, track.y + 1, self.rail_width, track.h - 2)
        thumb_h = max(self.thumb_min_height, int(track.h * visible / total))
        thumb_y = track.y + int((track.h - thumb_h) * min(max(offset, 0), max_offset) / max_offset)
        thumb = pygame.Rect(track.x + 1, thumb_y, track.w - 2, thumb_h)

        pygame.draw.rect(surface, self.border_color, track, border_radius=4)
        pygame.draw.rect(surface, self.rail_color, rail, border_radius=2)

        pygame.draw.rect(surface, self.thumb_color, thumb, border_radius=5)
        pygame.draw.rect(surface, self.border_color, thumb, 1, border_radius=5)

    def draw(
        self,
        surface,
        offset,
        total,
        visible=6,
    ) -> None:
        track = self._track_rect()
        self._draw_track(surface, track, offset, total, visible)


LIST_SCROLLBAR = Scrollbar()

__all__ = ["Scrollbar", "LIST_SCROLLBAR"]
