from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class CompatibilityReport:
    compatible: bool
    mode: str
    source_generation: int
    target_generation: int
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    data_loss: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    transformations: list[str] = field(default_factory=list)
    removed_moves: list[dict[str, Any]] = field(default_factory=list)
    removed_items: list[dict[str, Any]] = field(default_factory=list)
    removed_fields: list[str] = field(default_factory=list)
    normalized_species: dict[str, Any] = field(default_factory=dict)
    requires_user_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CompatibilityReport":
        return cls(
            compatible=bool(value["compatible"]),
            mode=str(value["mode"]),
            source_generation=int(value["source_generation"]),
            target_generation=int(value["target_generation"]),
            blocking_reasons=list(value.get("blocking_reasons") or []),
            warnings=list(value.get("warnings") or []),
            data_loss=list(value.get("data_loss") or []),
            suggested_actions=list(value.get("suggested_actions") or []),
            transformations=list(value.get("transformations") or []),
            removed_moves=list(value.get("removed_moves") or []),
            removed_items=list(value.get("removed_items") or []),
            removed_fields=list(value.get("removed_fields") or []),
            normalized_species=dict(value.get("normalized_species") or {}),
            requires_user_confirmation=bool(value.get("requires_user_confirmation") or False),
        )
