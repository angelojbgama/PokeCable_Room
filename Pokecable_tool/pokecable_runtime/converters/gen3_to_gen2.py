from __future__ import annotations

from copy import deepcopy

from canonical import CanonicalPokemon
from compatibility import CompatibilityReport
from data.items import equivalent_item_id, item_exists

from .base import BaseConverter


class Gen3ToGen2Converter(BaseConverter):
    source_generation = 3
    target_generation = 2
    mode = "legacy_downconvert_experimental"

    def _normalized_copy(self, canonical: CanonicalPokemon, report: CompatibilityReport, resolved_moves: dict[int, int] | None = None) -> CanonicalPokemon:
        converted = deepcopy(canonical)
        converted.ability = None
        converted.nature = None
        if converted.held_item and converted.held_item.item_id:
            mapped = equivalent_item_id(converted.held_item.item_id, 3, 2)
            if mapped is None or not item_exists(mapped, 2):
                converted.held_item = None
            else:
                converted.held_item.item_id = mapped
                converted.held_item.source_generation = 2
        self._apply_report_normalization(converted, report, resolved_moves=resolved_moves)
        return converted
