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

_KNOWN_MOVES = {
    1: ("Pound", 35),
    5: ("Mega Punch", 20),
    7: ("Fire Punch", 15),
    8: ("Ice Punch", 15),
    9: ("Thunder Punch", 15),
    33: ("Tackle", 35),
    45: ("Growl", 40),
    64: ("Peck", 35),
    93: ("Confusion", 25),
    100: ("Teleport", 20),
    117: ("Bide", 10),
    129: ("Swift", 20),
    154: ("Fury Swipes", 15),
    165: ("Struggle", 1),
    166: ("Sketch", 1),
    200: ("Outrage", 15),
    251: ("Beat Up", 10),
    252: ("Fake Out", 10),
    300: ("Mud Sport", 15),
    354: ("Psycho Boost", 5),
}

for move_id, (name, base_pp) in _KNOWN_MOVES.items():
    current = MOVE_DATA[move_id]
    MOVE_DATA[move_id] = MoveData(
        move_id=move_id,
        name=name,
        generations=current.generations,
        base_pp=base_pp,
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
