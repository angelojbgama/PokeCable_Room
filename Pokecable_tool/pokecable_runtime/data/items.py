from __future__ import annotations

import re

from data.item_catalog import (
    GEN1_ITEMS_BY_ID,
    GEN2_ITEMS_BY_ID,
    GEN3_ITEMS_BY_ID,
    ITEMS_BY_GENERATION,
    ItemCatalogEntry,
)

try:
    from .gen4_static import GEN4_ITEM_DATA
except Exception:
    GEN4_ITEM_DATA = {}

ItemData = ItemCatalogEntry
GEN4_MAX_ITEM_ID = 600
GEN4_DISPLAY_NAME_OVERRIDES: dict[int, tuple[str, str]] = {
    112: ("Griseous Orb", "held_item"),
    221: ("King's Rock", "held_item"),
    226: ("Deep Sea Tooth", "held_item"),
    227: ("Deep Sea Scale", "held_item"),
    233: ("Metal Coat", "held_item"),
    235: ("Dragon Scale", "held_item"),
    252: ("Up-Grade", "held_item"),
    321: ("Protector", "held_item"),
    322: ("Electirizer", "held_item"),
    323: ("Magmarizer", "held_item"),
    324: ("Dubious Disc", "held_item"),
    325: ("Reaper Cloth", "held_item"),
}
GEN4_UNUSED_ITEM_IDS = set(range(113, 135))

DISPLAY_NAME_OVERRIDES: dict[str, str] = {
    "MASTER BALL": "Master Ball",
    "ULTRA BALL": "Ultra Ball",
    "GREAT BALL": "Great Ball",
    "Poke BALL": "Poke Ball",
    "PokeDEX": "Pokedex",
    "MOON STONE": "Moon Stone",
    "BURN HEAL": "Burn Heal",
    "ICE HEAL": "Ice Heal",
    "PARLYZ HEAL": "Parlyz Heal",
    "FULL RESTORE": "Full Restore",
    "MAX POTION": "Max Potion",
    "HYPER POTION": "Hyper Potion",
    "SUPER POTION": "Super Potion",
    "ESCAPE ROPE": "Escape Rope",
    "FIRE STONE": "Fire Stone",
    "THUNDERSTONE": "Thunderstone",
    "WATER STONE": "Water Stone",
    "HP UP": "HP Up",
    "RARE CANDY": "Rare Candy",
    "DOME FOSSIL": "Dome Fossil",
    "HELIX FOSSIL": "Helix Fossil",
    "SECRET KEY": "Secret Key",
    "X ACCURACY": "X Accuracy",
    "LEAF STONE": "Leaf Stone",
    "CARD KEY": "Card Key",
    "PP UP": "PP Up",
    "Poke DOLL": "Poke Doll",
    "FULL HEAL": "Full Heal",
    "MAX REVIVE": "Max Revive",
    "GUARD SPEC.": "Guard Spec.",
    "SUPER REPEL": "Super Repel",
    "MAX REPEL": "Max Repel",
    "DIRE HIT": "Dire Hit",
    "FRESH WATER": "Fresh Water",
    "SODA POP": "Soda Pop",
    "S.S.TICKET": "S.S.Ticket",
    "GOLD TEETH": "Gold Teeth",
    "X ATTACK": "X Attack",
    "X DEFEND": "X Defend",
    "X SPEED": "X Speed",
    "X SPECIAL": "X Special",
    "COIN CASE": "Coin Case",
    "OAK's PARCEL": "Oak's Parcel",
    "ITEMFINDER": "Itemfinder",
    "SILPH SCOPE": "Silph Scope",
    "Poke FLUTE": "Poke Flute",
    "LIFT KEY": "Lift Key",
    "EXP.ALL": "Exp.All",
    "OLD ROD": "Old Rod",
    "GOOD ROD": "Good Rod",
    "SUPER ROD": "Super Rod",
    "MAX ETHER": "Max Ether",
    "MAX ELIXER": "Max Elixer",
    "KING'S ROCK": "King's Rock",
    "METAL COAT": "Metal Coat",
    "DRAGON SCALE": "Dragon Scale",
    "UP-GRADE": "Up-Grade",
    "DEEPSEATOOTH": "Deep Sea Tooth",
    "DEEPSEASCALE": "Deep Sea Scale",
    "DEEP SEA TOOTH": "Deep Sea Tooth",
    "DEEP SEA SCALE": "Deep Sea Scale",
    "LIGHT BALL": "Light Ball",
    "SOFT SAND": "Soft Sand",
    "HARD STONE": "Hard Stone",
    "MIRACLE SEED": "Miracle Seed",
    "BLACKGLASSES": "BlackGlasses",
    "BLACKBELT": "Blackbelt",
    "MYSTIC WATER": "Mystic Water",
    "SHARP BEAK": "Sharp Beak",
    "POISON BARB": "Poison Barb",
    "NEVERMELTICE": "NeverMeltIce",
    "SPELL TAG": "Spell Tag",
    "TWISTEDSPOON": "TwistedSpoon",
    "DRAGON FANG": "Dragon Fang",
    "SILK SCARF": "Silk Scarf",
    "SHELL BELL": "Shell Bell",
    "SEA INCENSE": "Sea Incense",
    "LAX INCENSE": "Lax Incense",
    "LUCKY PUNCH": "Lucky Punch",
    "METAL POWDER": "Metal Powder",
    "THICK CLUB": "Thick Club",
    "MOOMOO MILK": "Moomoo Milk",
    "BERRY JUICE": "Berry Juice",
    "SACRED ASH": "Sacred Ash",
    "FLOWER MAIL": "Flower Mail",
    "SURF MAIL": "Surf Mail",
    "MYSTICTICKET": "MysticTicket",
    "AURORATICKET": "AuroraTicket",
}

def _fallback_display_name(name: str) -> str:
    if name in DISPLAY_NAME_OVERRIDES:
        return DISPLAY_NAME_OVERRIDES[name]
    if re.fullmatch(r"(TM|HM)\d{2}", name):
        return name
    if name.isupper():
        return " ".join(part.capitalize() for part in name.split())
    return name


def _normalized_entry(entry: ItemData) -> ItemData:
    return ItemData(
        item_id=entry.item_id,
        name=DISPLAY_NAME_OVERRIDES.get(entry.name, _fallback_display_name(entry.name)),
        generation=entry.generation,
        category=entry.category,
        equivalent_name=entry.equivalent_name,
    )


def _gen4_entry(item_id: int) -> ItemData | None:
    item_id = int(item_id)
    if item_id in GEN4_DISPLAY_NAME_OVERRIDES:
        name, category = GEN4_DISPLAY_NAME_OVERRIDES[item_id]
        return ItemData(item_id=item_id, name=name, generation=4, category=category)
    if item_id in GEN4_UNUSED_ITEM_IDS:
        return ItemData(item_id=item_id, name=f"Unused Item #{item_id}", generation=4, category="unused")
    data = GEN4_ITEM_DATA.get(item_id) or {}
    name = data.get("name")
    if name:
        return ItemData(
            item_id=item_id,
            name=str(name),
            generation=4,
            category=str(data.get("category") or "item"),
        )
    if 328 <= item_id <= 419:
        return ItemData(item_id=item_id, name=f"TM{item_id - 327:02d}", generation=4, category="tm")
    if 420 <= item_id <= 427:
        return ItemData(item_id=item_id, name=f"HM{item_id - 419:02d}", generation=4, category="hm")
    return None


def _name_index_entries() -> list[ItemData]:
    entries = [
        _normalized_entry(entry)
        for items in ITEMS_BY_GENERATION.values()
        for entry in items.values()
    ]
    for item_id in sorted(set(GEN4_ITEM_DATA) | set(GEN4_DISPLAY_NAME_OVERRIDES)):
        entry = _gen4_entry(int(item_id))
        if entry is not None:
            entries.append(entry)
    return entries


ITEM_IDS_BY_GENERATION_AND_NAME: dict[tuple[int, str], int] = {
    (entry.generation, entry.name.lower()): entry.item_id
    for entry in _name_index_entries()
}


def item_exists(item_id: int | None, generation: int) -> bool:
    if item_id in {None, 0}:
        return True
    if int(generation) == 4:
        entry = _gen4_entry(int(item_id))
        return entry is not None and entry.category != "unused"
    return int(item_id) in ITEMS_BY_GENERATION.get(int(generation), {})


def item_data(item_id: int | None, generation: int) -> ItemData | None:
    if item_id in {None, 0}:
        return None
    if int(generation) == 4:
        return _gen4_entry(int(item_id))
    entry = ITEMS_BY_GENERATION.get(int(generation), {}).get(int(item_id))
    return _normalized_entry(entry) if entry else None


def item_name(item_id: int | None, generation: int) -> str | None:
    entry = item_data(item_id, generation)
    return entry.name if entry else None


def item_category(item_id: int | None, generation: int) -> str | None:
    entry = item_data(item_id, generation)
    return entry.category if entry else None


def generation_items(generation: int) -> dict[int, ItemData]:
    if int(generation) == 4:
        return {
            item_id: entry
            for item_id in range(1, GEN4_MAX_ITEM_ID + 1)
            if (entry := _gen4_entry(item_id)) is not None
        }
    return {item_id: _normalized_entry(entry) for item_id, entry in ITEMS_BY_GENERATION.get(int(generation), {}).items()}


def equivalent_item_id(item_id: int | None, source_generation: int, target_generation: int) -> int | None:
    if item_id in {None, 0}:
        return None
    source = ITEMS_BY_GENERATION.get(int(source_generation), {}).get(int(item_id))
    if source is None:
        return None
    # Prefer explicit equivalent_name mapping, fall back to matching by display name across gens.
    candidate_names: list[str] = []
    if source.equivalent_name:
        candidate_names.append(source.equivalent_name)
    candidate_names.append(DISPLAY_NAME_OVERRIDES.get(source.name, _fallback_display_name(source.name)))
    candidate_names.append(source.name)
    seen: set[str] = set()
    for name in candidate_names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        target_id = ITEM_IDS_BY_GENERATION_AND_NAME.get((int(target_generation), key))
        if target_id is not None:
            return target_id
    return None
