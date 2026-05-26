"""Classificação de itens "consumíveis" para o seletor de itens do Extras.

O catálogo de itens (data.item_catalog) só tem uma categoria genérica ("item")
para Gen 1/2 e mistura cura/vitaminas/repel em "item" mesmo na Gen 3, então não dá
para isolar consumíveis pela categoria. Aqui classificamos por NOME normalizado em
buckets (whitelist positiva): só entram itens que casam com um bucket conhecido —
pedras de evolução, fósseis, mapas, hold items, key items, TMs/HMs etc. ficam de fora.
"""
from __future__ import annotations

import re

from .items import item_category, item_exists, item_name

# Ordem dos grupos como aparecem na UI. (key, name_key i18n)
CONSUMABLE_BUCKETS: tuple[tuple[str, str], ...] = (
    ("balls", "items_cat_balls"),
    ("healing", "items_cat_healing"),
    ("status", "items_cat_status"),
    ("pp", "items_cat_pp"),
    ("vitamins", "items_cat_vitamins"),
    ("battle", "items_cat_battle"),
    ("repel", "items_cat_repel"),
    ("flute", "items_cat_flute"),
    ("berry", "items_cat_berry"),
)

_BALL_NAMES = {
    "masterball", "ultraball", "greatball", "pokeball", "safariball", "netball",
    "diveball", "nestball", "repeatball", "timerball", "luxuryball", "premierball",
    "healball", "quickball", "duskball", "cherishball", "sportball", "parkball",
    "heavyball", "levelball", "lureball", "fastball", "friendball", "moonball",
    "loveball",
}
_PP_NAMES = {"ether", "maxether", "elixir", "elixer", "maxelixir", "maxelixer", "ppup", "ppmax"}
_VITAMIN_NAMES = {"hpup", "protein", "iron", "carbos", "calcium", "zinc", "rarecandy"}
_STATUS_NAMES = {"antidote", "burnheal", "iceheal", "awakening", "parlyzheal", "fullheal"}
_HEALING_NAMES = {
    "potion", "superpotion", "hyperpotion", "maxpotion", "fullrestore",
    "revive", "maxrevive", "freshwater", "sodapop", "lemonade", "moomoomilk",
    "berryjuice", "sacredash", "energypowder", "energyroot", "healpowder",
    "revivalherb", "sweetheart",
}
_BATTLE_NAMES = {
    "xattack", "xdefend", "xdefense", "xspeed", "xspecial", "xspatk", "xspdef",
    "xaccuracy", "direhit", "guardspec",
}
_REPEL_NAMES = {"repel", "superrepel", "maxrepel", "escaperope"}


def _norm(name: str) -> str:
    """Normaliza o nome: minúsculas, sem espaços/pontuação (Guard Spec. -> guardspec)."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def classify_consumable(item_id: int, generation: int) -> str | None:
    """Retorna o bucket consumível do item, ou None se não for consumível."""
    name = item_name(item_id, generation)
    if not name:
        return None
    n = _norm(name)
    if not n or "?" in name:
        return None
    category = item_category(item_id, generation) or "item"

    if category == "ball" or n in _BALL_NAMES:
        return "balls"
    if category == "berry" or (n.endswith("berry") and "cure" in n) or n.endswith("berry"):
        return "berry"
    if n in _REPEL_NAMES:
        return "repel"
    if n in _PP_NAMES:
        return "pp"
    if n in _VITAMIN_NAMES:
        return "vitamins"
    if n in _STATUS_NAMES:
        return "status"
    if n in _HEALING_NAMES or n.endswith("potion"):
        return "healing"
    if n in _BATTLE_NAMES:
        return "battle"
    # Poke Flute é key item, não consumível — apenas as flutes coloridas da Gen 3 contam.
    if n != "pokeflute" and (n.endswith("flute") or n in {"lavacookie", "oldgateau"}):
        return "flute"
    return None


def consumable_groups(generation: int, max_item_id: int = 700) -> list[tuple[str, list[tuple[int, str]]]]:
    """Retorna [(bucket_key, [(item_id, name), ...]), ...] na ordem de CONSUMABLE_BUCKETS,
    omitindo buckets vazios. Apenas itens válidos na geração."""
    by_bucket: dict[str, list[tuple[int, str]]] = {key: [] for key, _ in CONSUMABLE_BUCKETS}
    seen_names: dict[str, set[str]] = {key: set() for key, _ in CONSUMABLE_BUCKETS}
    for item_id in range(1, max_item_id + 1):
        if not item_exists(item_id, generation):
            continue
        bucket = classify_consumable(item_id, generation)
        if bucket is None:
            continue
        name = item_name(item_id, generation)
        # Dedup por nome dentro do bucket (catálogos têm ids duplicados, ex. PP Up).
        if _norm(name) in seen_names[bucket]:
            continue
        seen_names[bucket].add(_norm(name))
        by_bucket[bucket].append((item_id, name))
    return [(key, by_bucket[key]) for key, _ in CONSUMABLE_BUCKETS if by_bucket[key]]


def max_item_stack(generation: int) -> int:
    """Stack máximo de um item consumível na geração (Gen 1/2 = 99, Gen 3/4 = 999)."""
    return 99 if int(generation) in (1, 2) else 999


def bucket_name_key(bucket_key: str) -> str:
    for key, name_key in CONSUMABLE_BUCKETS:
        if key == bucket_key:
            return name_key
    return bucket_key
