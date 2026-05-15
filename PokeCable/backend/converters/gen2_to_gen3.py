from __future__ import annotations

from copy import deepcopy

from canonical import CanonicalPokemon
from compatibility import CompatibilityReport
from data.items import equivalent_item_id, item_exists

from .base import BaseConverter


class Gen2ToGen3Converter(BaseConverter):
    source_generation = 2
    target_generation = 3
    mode = "forward_transfer_to_gen3"

    def _normalized_copy(self, canonical: CanonicalPokemon, report: CompatibilityReport, resolved_moves: dict[int, int] | None = None) -> CanonicalPokemon:
        converted = deepcopy(canonical)
        if converted.held_item and converted.held_item.item_id:
            mapped = equivalent_item_id(converted.held_item.item_id, 2, 3)
            if mapped is None or not item_exists(mapped, 3):
                converted.held_item = None
            else:
                converted.held_item.item_id = mapped
                converted.held_item.source_generation = 3
        self._apply_report_normalization(converted, report, resolved_moves=resolved_moves)
        return converted
