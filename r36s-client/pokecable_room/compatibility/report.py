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
        )
