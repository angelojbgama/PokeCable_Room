from __future__ import annotations

from pathlib import Path


VALID_GENERATIONS = {1, 2, 3}
VALID_POSES = {"front", "back"}


def resolve_sprite_path(generation: int, species: str, pose: str = "front") -> Path | None:
    base = Path(__file__).resolve().parents[2] / "frontend" / "sprites"
    slug = str(species or "").strip().lower().replace(" ", "-")
    for candidate in (
        base / str(int(generation)) / slug / f"{pose}.png",
        base / str(int(generation)) / f"{slug}-{pose}.png",
        base / str(int(generation)) / f"{slug}.png",
    ):
        if candidate.exists():
            return candidate
    return None
