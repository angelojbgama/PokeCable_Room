from __future__ import annotations

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.data.items import item_name
from pokecable_room.data.moves import move_name


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _same_name(left: str | None, right: str | None) -> bool:
    return _clean(left).casefold() == _clean(right).casefold()


def _item_name(canonical: CanonicalPokemon, target_generation: int) -> str | None:
    if canonical.held_item is None or canonical.held_item.item_id in {None, 0}:
        return None
    if canonical.held_item.name:
        return canonical.held_item.name
    generation = canonical.held_item.source_generation or target_generation
    return item_name(canonical.held_item.item_id, generation) or f"Item {canonical.held_item.item_id}"


def canonical_to_battle_set(canonical: CanonicalPokemon, target_generation: int) -> dict:
    species = _clean(canonical.species.name if canonical.species else canonical.species_name)
    nickname = _clean(canonical.nickname)
    name = nickname if nickname and not _same_name(nickname, species) else species
    moves = []
    for move in canonical.moves[:4]:
        name_or_fallback = move.name or move_name(move.move_id) or f"Move {move.move_id}"
        if name_or_fallback and move.move_id:
            moves.append(name_or_fallback)
    result = {
        "name": name,
        "species": species,
        "item": _item_name(canonical, target_generation),
        "level": max(1, min(100, int(canonical.level or 1))),
        "gender": canonical.metadata.get("gender") if canonical.metadata else None,
        "ability": canonical.ability,
        "nature": canonical.nature,
        "moves": moves,
    }
    if int(target_generation) <= 2:
        result["ability"] = result["ability"] or "No Ability"
        result["nature"] = result["nature"] or "Serious"
    return result


def _header(battle_set: dict) -> str:
    species = battle_set["species"]
    name = battle_set["name"]
    label = f"{name} ({species})" if not _same_name(name, species) else species
    if battle_set.get("gender"):
        label += f" ({battle_set['gender']})"
    if battle_set.get("item"):
        label += f" @ {battle_set['item']}"
    return label


def canonical_team_to_battle_text(team: list[CanonicalPokemon], target_generation: int) -> str:
    blocks: list[str] = []
    for canonical in team[:6]:
        battle_set = canonical_to_battle_set(canonical, target_generation)
        lines = [_header(battle_set), f"Level: {battle_set['level']}"]
        if battle_set.get("ability"):
            lines.append(f"Ability: {battle_set['ability']}")
        if battle_set.get("nature"):
            lines.append(f"{battle_set['nature']} Nature")
        for move in battle_set["moves"]:
            lines.append(f"- {move}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
