from __future__ import annotations

from pathlib import Path


VALID_GENERATIONS = {1, 2, 3}
VALID_POSES = {"front"}


def _ensure_backend_path() -> None:
    import sys

    backend = Path(__file__).resolve().parents[2] / "backend"
    if (backend / "data").exists() and str(backend) not in sys.path:
        sys.path.insert(0, str(backend))


def _slug(value: str) -> str:
    text = str(value or "").strip().lower()
    for token in ["'", ".", ":", ",", "(", ")", "[", "]"]:
        text = text.replace(token, "")
    return text.replace(" ", "-").replace("_", "-")


def _national_id_for_species(species: str) -> str:
    slug = _slug(species)
    if slug.replace("-", "").isdigit():
        return slug
    _ensure_backend_path()
    try:
        from data.species import SPECIES_NAMES_BY_NATIONAL  # type: ignore
    except Exception:
        return slug
    for national_id, name in SPECIES_NAMES_BY_NATIONAL.items():
        if _slug(name) == slug:
            return str(national_id)
    return slug


def resolve_sprite_path(generation: int, species: str, pose: str = "front") -> Path | None:
    del generation
    if pose != "front":
        return None
    base = Path(__file__).resolve().parents[2] / "frontend" / "sprites" / "pokemon" / "normal"
    sprite_id = _national_id_for_species(species)
    candidate = base / f"{sprite_id}.png"
    if candidate.exists():
        return candidate
    return None
