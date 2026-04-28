from __future__ import annotations

from copy import deepcopy

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport
from pokecable_room.data.items import equivalent_item_id

from .base import BaseConverter


class Gen3ToGen2Converter(BaseConverter):
    source_generation = 3
    target_generation = 2
    mode = "legacy_downconvert_experimental"

    def _normalized_copy(self, canonical: CanonicalPokemon, report: CompatibilityReport) -> CanonicalPokemon:
        converted = deepcopy(canonical)
        converted.ability = None
        converted.nature = None
        if converted.held_item and converted.held_item.item_id:
            mapped = equivalent_item_id(converted.held_item.item_id, 3, 2)
            if mapped is None:
                converted.held_item = None
            else:
                converted.held_item.item_id = mapped
                converted.held_item.source_generation = 2
        converted.moves = [move for move in converted.moves if move.move_id <= 251]
        if converted.species is not None:
            converted.species.target_species_id = report.normalized_species.get("target_species_id")
            converted.species.target_species_id_space = report.normalized_species.get("target_species_id_space")
        return converted
