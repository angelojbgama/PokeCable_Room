"""Shared report dataclass and printer for the save-roundtrip battery."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class BatteryReport:
    name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add_pass(self) -> None:
        self.total += 1
        self.passed += 1

    def add_fail(self, msg: str) -> None:
        self.total += 1
        self.failed += 1
        if len(self.failures) < 50:
            self.failures.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)
