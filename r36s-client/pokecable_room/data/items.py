from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ItemData:
    item_id: int
    name: str
    generation: int
    equivalent_name: str | None = None


GEN2_ITEMS_BY_ID: dict[int, ItemData] = {
    0x52: ItemData(0x52, "King's Rock", 2, "King's Rock"),
    0x8F: ItemData(0x8F, "Metal Coat", 2, "Metal Coat"),
    0x97: ItemData(0x97, "Dragon Scale", 2, "Dragon Scale"),
    0xAC: ItemData(0xAC, "Up-Grade", 2, "Up-Grade"),
}

GEN3_ITEMS_BY_ID: dict[int, ItemData] = {
    187: ItemData(187, "King's Rock", 3, "King's Rock"),
    192: ItemData(192, "Deep Sea Tooth", 3, "Deep Sea Tooth"),
    193: ItemData(193, "Deep Sea Scale", 3, "Deep Sea Scale"),
    199: ItemData(199, "Metal Coat", 3, "Metal Coat"),
    201: ItemData(201, "Dragon Scale", 3, "Dragon Scale"),
    218: ItemData(218, "Up-Grade", 3, "Up-Grade"),
}

ITEMS_BY_GENERATION: dict[int, dict[int, ItemData]] = {
    1: {},
    2: GEN2_ITEMS_BY_ID,
    3: GEN3_ITEMS_BY_ID,
}

ITEM_IDS_BY_GENERATION_AND_NAME: dict[tuple[int, str], int] = {
    (item.generation, item.name.lower()): item.item_id
    for items in ITEMS_BY_GENERATION.values()
    for item in items.values()
}


def item_exists(item_id: int | None, generation: int) -> bool:
    if item_id in {None, 0}:
        return True
    return int(item_id) in ITEMS_BY_GENERATION.get(int(generation), {})


def item_name(item_id: int | None, generation: int) -> str | None:
    if item_id in {None, 0}:
        return None
    item = ITEMS_BY_GENERATION.get(int(generation), {}).get(int(item_id))
    return item.name if item else None


def equivalent_item_id(item_id: int | None, source_generation: int, target_generation: int) -> int | None:
    if item_id in {None, 0}:
        return None
    source = ITEMS_BY_GENERATION.get(int(source_generation), {}).get(int(item_id))
    if source is None or source.equivalent_name is None:
        return None
    return ITEM_IDS_BY_GENERATION_AND_NAME.get((int(target_generation), source.equivalent_name.lower()))
