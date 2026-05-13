from __future__ import annotations

from dataclasses import dataclass

from .move_combat_data import MOVE_COMBAT_DATA


@dataclass(frozen=True, slots=True)
class MoveData:
    move_id: int
    name: str
    generations: frozenset[int]
    base_pp: int | None = None


def _display_name(raw: str | None, move_id: int) -> str:
    value = str(raw or "").strip()
    if not value:
        return f"Move #{move_id}"
    return " ".join(part.capitalize() for part in value.replace("-", " ").split())


MOVE_DATA: dict[int, MoveData] = {}
for move_id in range(1, 355):
    generations = frozenset(gen for gen, max_move in {1: 165, 2: 251, 3: 354}.items() if move_id <= max_move)
    combat = MOVE_COMBAT_DATA.get(move_id) or {}
    MOVE_DATA[move_id] = MoveData(
        move_id=move_id,
        name=_display_name(combat.get("name"), move_id),
        generations=generations,
        base_pp=combat.get("pp"),
    )


def move_exists(move_id: int | None, generation: int) -> bool:
    if move_id in {None, 0}:
        return True
    move = MOVE_DATA.get(int(move_id))
    return move is not None and int(generation) in move.generations


def move_name(move_id: int | None) -> str | None:
    if move_id in {None, 0}:
        return None
    move = MOVE_DATA.get(int(move_id))
    return move.name if move else None
