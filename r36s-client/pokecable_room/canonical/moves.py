from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class CanonicalMove:
    move_id: int
    name: str | None = None
    pp: int | None = None
    max_pp: int | None = None
    pp_ups: int | None = None
    source_generation: int | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CanonicalMove":
        return cls(
            move_id=int(value["move_id"]),
            name=str(value["name"]) if value.get("name") is not None else None,
            pp=int(value["pp"]) if value.get("pp") is not None else None,
            max_pp=int(value["max_pp"]) if value.get("max_pp") is not None else None,
            pp_ups=int(value["pp_ups"]) if value.get("pp_ups") is not None else None,
            source_generation=int(value["source_generation"]) if value.get("source_generation") is not None else None,
            metadata=dict(value.get("metadata") or {}),
        )
