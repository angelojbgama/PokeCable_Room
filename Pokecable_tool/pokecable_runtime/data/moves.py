from __future__ import annotations

from dataclasses import dataclass

try:
    from .gen4_static import GEN4_MOVE_DATA
except Exception:
    GEN4_MOVE_DATA = {}
from .move_combat_data import MOVE_COMBAT_DATA


@dataclass(frozen=True, slots=True)
class MoveData:
    move_id: int
    name: str
    generations: frozenset[int]
    base_pp: int | None = None
    base_pp_by_generation: dict[int, int] | None = None


def _display_name(raw: str | None, move_id: int) -> str:
    value = str(raw or "").strip()
    if not value:
        return f"Move #{move_id}"
    return " ".join(part.capitalize() for part in value.replace("-", " ").split())


MOVE_DATA: dict[int, MoveData] = {}
for move_id in range(1, 468):
    generations = frozenset(gen for gen, max_move in {1: 165, 2: 251, 3: 354, 4: 467}.items() if move_id <= max_move)
    combat = MOVE_COMBAT_DATA.get(move_id) or {}
    gen4 = GEN4_MOVE_DATA.get(move_id) or {}
    base_pp = combat.get("pp")
    if base_pp is None:
        base_pp = gen4.get("pp")
    base_pp_by_generation = {4: int(gen4["pp"])} if gen4.get("pp") is not None else None
    MOVE_DATA[move_id] = MoveData(
        move_id=move_id,
        name=_display_name(combat.get("name") or gen4.get("name"), move_id),
        generations=generations,
        base_pp=base_pp,
        base_pp_by_generation=base_pp_by_generation,
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


def move_base_pp(move_id: int | None, generation: int | None = None) -> int | None:
    if move_id in {None, 0}:
        return None
    move = MOVE_DATA.get(int(move_id))
    if move is None:
        return None
    if generation is not None and move.base_pp_by_generation:
        value = move.base_pp_by_generation.get(int(generation))
        if value is not None:
            return int(value)
    return int(move.base_pp) if move.base_pp is not None else None


def default_move_pp(move_id: int | None, generation: int | None = None, pp_ups: int = 0) -> int:
    if generation is not None and not move_exists(move_id, generation):
        return 0
    base_pp = move_base_pp(move_id, generation)
    if base_pp is None:
        return 1 if move_id not in {None, 0} else 0
    pp_ups = max(0, min(3, int(pp_ups or 0)))
    return min(64, base_pp + (base_pp * pp_ups // 5))
