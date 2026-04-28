from __future__ import annotations

from copy import deepcopy

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport

from .base import BaseConverter


class Gen3ToGen1Converter(BaseConverter):
    source_generation = 3
    target_generation = 1
    mode = "legacy_downconvert_experimental"

    def _normalized_copy(self, canonical: CanonicalPokemon, report: CompatibilityReport) -> CanonicalPokemon:
        converted = deepcopy(canonical)
        converted.held_item = None
        converted.ability = None
        converted.nature = None
        converted.moves = [move for move in converted.moves if move.move_id <= 165]
        if converted.species is not None:
            converted.species.target_species_id = report.normalized_species.get("target_species_id")
            converted.species.target_species_id_space = report.normalized_species.get("target_species_id_space")
        return converted
