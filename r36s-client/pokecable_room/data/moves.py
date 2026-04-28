from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MoveData:
    move_id: int
    name: str
    generations: frozenset[int]
    base_pp: int | None = None


# The converters need reliable existence checks more than display names. Full
# move names can be expanded without changing the compatibility API.
MOVE_DATA: dict[int, MoveData] = {
    move_id: MoveData(
        move_id=move_id,
        name=f"Move #{move_id}",
        generations=frozenset(gen for gen, max_move in {1: 165, 2: 251, 3: 354}.items() if move_id <= max_move),
    )
    for move_id in range(1, 355)
}


def move_exists(move_id: int | None, generation: int) -> bool:
    if move_id in {None, 0}:
        return True
    move = MOVE_DATA.get(int(move_id))
    return move is not None and int(generation) in move.generations
