from __future__ import annotations

from copy import deepcopy

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport

from .base import BaseConverter


class Gen2ToGen1Converter(BaseConverter):
    source_generation = 2
    target_generation = 1
    mode = "time_capsule_gen1_gen2"

    def _normalized_copy(self, canonical: CanonicalPokemon, report: CompatibilityReport) -> CanonicalPokemon:
        converted = deepcopy(canonical)
        converted.held_item = None
        converted.ability = None
        converted.nature = None
        self._apply_report_normalization(converted, report)
        return converted
