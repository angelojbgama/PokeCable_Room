from __future__ import annotations

from pokecable_room.canonical import CanonicalPokemon

from .rules import build_compatibility_report


def report_gen1_gen3(candidate: CanonicalPokemon, target_generation: int, *, enabled: bool = False):
    return build_compatibility_report(candidate, target_generation, cross_generation_enabled=enabled)
