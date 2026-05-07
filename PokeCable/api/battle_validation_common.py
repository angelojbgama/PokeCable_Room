from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SAVE_ROOT = Path(__file__).resolve().parents[2] / "save"
REPORT_ROOT = Path(__file__).resolve().parents[1] / "docs" / "battle-validation"


def require_real_save(relative: str) -> Path:
    path = SAVE_ROOT / relative
    if not path.exists():
        raise FileNotFoundError(f"Save real ausente: {path}")
    return path


def ensure_report_root() -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    return REPORT_ROOT


def normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def clone_team_with_active(team: list[Any], active_index: int) -> list[Any]:
    if active_index < 0 or active_index >= len(team):
        raise IndexError(f"Indice ativo invalido: {active_index}")
    cloned = copy.deepcopy(team)
    active = cloned.pop(active_index)
    return [active] + cloned


def clone_team_with_actives(team: list[Any], active_indices: list[int]) -> list[Any]:
    if not active_indices:
        raise ValueError("active_indices nao pode ser vazio")
    cloned = copy.deepcopy(team)
    active_set = set(active_indices)
    selected = [cloned[index] for index in active_indices]
    rest = [pokemon for index, pokemon in enumerate(cloned) if index not in active_set]
    return selected + rest


def tail_logs(logs: list[str], limit: int = 6) -> list[str]:
    if limit <= 0:
        return []
    return logs[-limit:]


def battle_pokemon_state(pokemon: Any) -> str:
    status = getattr(pokemon, "status_condition", None) or "ok"
    hp = getattr(pokemon, "current_hp", "?")
    max_hp = getattr(pokemon, "max_hp", "?")
    return f"{hp}/{max_hp} {status}"


@dataclass
class ValidationReport:
    title: str
    source_a: str
    source_b: str
    lines: list[str] = field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0

    def add_header(self) -> None:
        self.lines.extend(
            [
                f"# {self.title}",
                f"source_a: {self.source_a}",
                f"source_b: {self.source_b}",
                "",
            ]
        )

    def add_case(
        self,
        label: str,
        ok: bool,
        detail: str = "",
        *,
        logs: list[str] | None = None,
    ) -> None:
        status = "PASS" if ok else "FAIL"
        line = f"{status} | {label}"
        if detail:
            line = f"{line} | {detail}"
        self.lines.append(line)
        if logs:
            for log in logs:
                self.lines.append(f"    {log}")
        if ok:
            self.pass_count += 1
        else:
            self.fail_count += 1

    def add_blank(self) -> None:
        self.lines.append("")

    def add_summary(self) -> None:
        self.lines.extend(
            [
                "",
                f"summary: pass={self.pass_count} fail={self.fail_count} total={self.pass_count + self.fail_count}",
            ]
        )

    def write(self, filename: str) -> Path:
        ensure_report_root()
        path = REPORT_ROOT / filename
        content = "\n".join(self.lines).rstrip() + "\n"
        path.write_text(content, encoding="utf-8")
        return path
