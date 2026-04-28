from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class CanonicalItem:
    item_id: int | None = None
    name: str | None = None
    source_generation: int | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "CanonicalItem | None":
        if not value:
            return None
        return cls(
            item_id=int(value["item_id"]) if value.get("item_id") is not None else None,
            name=str(value["name"]) if value.get("name") is not None else None,
            source_generation=int(value["source_generation"]) if value.get("source_generation") is not None else None,
            metadata=dict(value.get("metadata") or {}),
        )
