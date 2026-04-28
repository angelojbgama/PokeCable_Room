from __future__ import annotations

from copy import deepcopy

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport
from pokecable_room.data.items import equivalent_item_id

from .base import BaseConverter


class Gen2ToGen3Converter(BaseConverter):
    source_generation = 2
    target_generation = 3
    mode = "forward_transfer_to_gen3"

    def _normalized_copy(self, canonical: CanonicalPokemon, report: CompatibilityReport) -> CanonicalPokemon:
        converted = deepcopy(canonical)
        if converted.held_item and converted.held_item.item_id:
            mapped = equivalent_item_id(converted.held_item.item_id, 2, 3)
            if mapped is None:
                converted.held_item = None
            else:
                converted.held_item.item_id = mapped
                converted.held_item.source_generation = 3
        self._apply_report_normalization(converted, report)
        return converted
