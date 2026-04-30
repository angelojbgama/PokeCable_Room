from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pokecable_room.data.items import ITEM_IDS_BY_GENERATION_AND_NAME, equivalent_item_id, item_category, item_data

TransferDisposition = Literal["keep_held", "move_to_bag", "move_to_pc", "remove"]
TransferReason = Literal[
    "no_item",
    "equivalent_held_item_available",
    "same_item_available",
    "item_exists_but_target_cannot_hold",
    "item_exists_but_category_not_holdable",
    "item_absent_in_target_generation",
]

NON_HOLDABLE_CATEGORIES = frozenset({"badge", "system", "tm", "hm", "unused"})


@dataclass(frozen=True, slots=True)
class ItemTransferDecision:
    source_item_id: int
    source_generation: int
    target_generation: int
    resolved_item_id: int | None
    resolved_item_name: str | None
    resolved_category: str | None
    disposition: TransferDisposition
    fallback_disposition: TransferDisposition | None
    preferred_pocket_name: str | None
    fallback_pocket_name: str | None
    reason: TransferReason
    requires_bag_space_check: bool
    requires_pc_space_check: bool


def _preferred_bag_pocket_name(target_generation: int, category: str | None) -> str:
    generation = int(target_generation)
    normalized_category = str(category or "")
    if generation == 1:
        return "bag_items"
    if generation == 2:
        if normalized_category in {"tm", "hm", "tmhm"}:
            return "tm_hm"
        if normalized_category == "ball":
            return "balls"
        if normalized_category == "key_item":
            return "key_items"
        return "items"
    if generation == 3:
        if normalized_category == "ball":
            return "balls"
        if normalized_category == "berry":
            return "berries"
        if normalized_category in {"tm", "hm", "tmhm"}:
            return "tm_hm"
        if normalized_category == "key_item":
            return "key_items"
        return "items"
    return "items"


def _lookup_same_name_item_id(item_id: int, source_generation: int, target_generation: int) -> int | None:
    source = item_data(item_id, source_generation)
    if source is None:
        return None
    return ITEM_IDS_BY_GENERATION_AND_NAME.get((int(target_generation), source.name.lower()))


def resolve_item_transfer_decision(
    item_id: int | None,
    *,
    source_generation: int,
    target_generation: int,
    target_supports_held_items: bool,
) -> ItemTransferDecision:
    if item_id in {None, 0}:
        return ItemTransferDecision(
            source_item_id=0,
            source_generation=int(source_generation),
            target_generation=int(target_generation),
            resolved_item_id=None,
            resolved_item_name=None,
            resolved_category=None,
            disposition="remove",
            fallback_disposition=None,
            preferred_pocket_name=None,
            fallback_pocket_name=None,
            reason="no_item",
            requires_bag_space_check=False,
            requires_pc_space_check=False,
        )

    source_item_id = int(item_id)
    resolved_item_id = equivalent_item_id(source_item_id, int(source_generation), int(target_generation))
    if resolved_item_id is None:
        resolved_item_id = _lookup_same_name_item_id(source_item_id, int(source_generation), int(target_generation))
    resolved = item_data(resolved_item_id, int(target_generation)) if resolved_item_id else None

    if resolved is None:
        return ItemTransferDecision(
            source_item_id=source_item_id,
            source_generation=int(source_generation),
            target_generation=int(target_generation),
            resolved_item_id=None,
            resolved_item_name=None,
            resolved_category=None,
            disposition="remove",
            fallback_disposition=None,
            preferred_pocket_name=None,
            fallback_pocket_name=None,
            reason="item_absent_in_target_generation",
            requires_bag_space_check=False,
            requires_pc_space_check=False,
        )

    category = item_category(resolved.item_id, int(target_generation))
    can_hold = target_supports_held_items and category not in NON_HOLDABLE_CATEGORIES
    if can_hold:
        return ItemTransferDecision(
            source_item_id=source_item_id,
            source_generation=int(source_generation),
            target_generation=int(target_generation),
            resolved_item_id=resolved.item_id,
            resolved_item_name=resolved.name,
            resolved_category=category,
            disposition="keep_held",
            fallback_disposition=None,
            preferred_pocket_name=None,
            fallback_pocket_name=None,
            reason="equivalent_held_item_available" if int(source_generation) != int(target_generation) else "same_item_available",
            requires_bag_space_check=False,
            requires_pc_space_check=False,
        )

    preferred_pocket_name = _preferred_bag_pocket_name(int(target_generation), category)
    return ItemTransferDecision(
        source_item_id=source_item_id,
        source_generation=int(source_generation),
        target_generation=int(target_generation),
        resolved_item_id=resolved.item_id,
        resolved_item_name=resolved.name,
        resolved_category=category,
        disposition="move_to_bag",
        fallback_disposition="move_to_pc",
        preferred_pocket_name=preferred_pocket_name,
        fallback_pocket_name="pc_items",
        reason="item_exists_but_target_cannot_hold" if not target_supports_held_items else "item_exists_but_category_not_holdable",
        requires_bag_space_check=True,
        requires_pc_space_check=True,
    )
