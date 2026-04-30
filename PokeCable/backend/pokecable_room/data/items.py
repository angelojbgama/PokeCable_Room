from __future__ import annotations

import re

from pokecable_room.data.item_catalog import (
    GEN1_ITEMS_BY_ID,
    GEN2_ITEMS_BY_ID,
    GEN3_ITEMS_BY_ID,
    ITEMS_BY_GENERATION,
    ItemCatalogEntry,
)

ItemData = ItemCatalogEntry

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


ITEM_IDS_BY_GENERATION_AND_NAME: dict[tuple[int, str], int] = {
    ((entry.generation, DISPLAY_NAME_OVERRIDES.get(entry.name, _fallback_display_name(entry.name)).lower())): entry.item_id
    for items in ITEMS_BY_GENERATION.values()
    for entry in items.values()
}


def _normalized_entry(entry: ItemData) -> ItemData:
    return ItemData(
        item_id=entry.item_id,
        name=DISPLAY_NAME_OVERRIDES.get(entry.name, _fallback_display_name(entry.name)),
        generation=entry.generation,
        category=entry.category,
        equivalent_name=entry.equivalent_name,
    )


def item_exists(item_id: int | None, generation: int) -> bool:
    if item_id in {None, 0}:
        return True
    return int(item_id) in ITEMS_BY_GENERATION.get(int(generation), {})


def item_data(item_id: int | None, generation: int) -> ItemData | None:
    if item_id in {None, 0}:
        return None
    entry = ITEMS_BY_GENERATION.get(int(generation), {}).get(int(item_id))
    return _normalized_entry(entry) if entry else None


def item_name(item_id: int | None, generation: int) -> str | None:
    entry = item_data(item_id, generation)
    return entry.name if entry else None


def item_category(item_id: int | None, generation: int) -> str | None:
    entry = item_data(item_id, generation)
    return entry.category if entry else None


def generation_items(generation: int) -> dict[int, ItemData]:
    return {item_id: _normalized_entry(entry) for item_id, entry in ITEMS_BY_GENERATION.get(int(generation), {}).items()}


def equivalent_item_id(item_id: int | None, source_generation: int, target_generation: int) -> int | None:
    if item_id in {None, 0}:
        return None
    source = ITEMS_BY_GENERATION.get(int(source_generation), {}).get(int(item_id))
    if source is None or source.equivalent_name is None:
        return None
    return ITEM_IDS_BY_GENERATION_AND_NAME.get((int(target_generation), source.equivalent_name.lower()))
