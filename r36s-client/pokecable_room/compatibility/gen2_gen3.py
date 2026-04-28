from __future__ import annotations

from pokecable_room.canonical import CanonicalPokemon

from .rules import build_compatibility_report


def report_forward_transfer(candidate: CanonicalPokemon, target_generation: int = 3, *, enabled: bool = False):
    return build_compatibility_report(candidate, target_generation, cross_generation_enabled=enabled)
