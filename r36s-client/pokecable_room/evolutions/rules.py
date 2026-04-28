from __future__ import annotations


SIMPLE_TRADE_EVOLUTIONS: dict[int, dict[int, int]] = {
    1: {
        38: 149,
        41: 126,
        39: 49,
        147: 14,
    },
    2: {
        64: 65,
        67: 68,
        75: 76,
        93: 94,
    },
    3: {
        64: 65,
        67: 68,
        75: 76,
        93: 94,
    },
}


ITEM_TRADE_EVOLUTION_RULES: dict[int, tuple[str, ...]] = {
    2: (
        "Poliwhirl + King's Rock -> Politoed",
        "Slowpoke + King's Rock -> Slowking",
        "Onix + Metal Coat -> Steelix",
        "Scyther + Metal Coat -> Scizor",
        "Seadra + Dragon Scale -> Kingdra",
        "Porygon + Up-Grade -> Porygon2",
    ),
    3: (
        "Poliwhirl + King's Rock -> Politoed",
        "Slowpoke + King's Rock -> Slowking",
        "Onix + Metal Coat -> Steelix",
        "Scyther + Metal Coat -> Scizor",
        "Seadra + Dragon Scale -> Kingdra",
        "Porygon + Up-Grade -> Porygon2",
        "Clamperl + Deep Sea Tooth -> Huntail",
        "Clamperl + Deep Sea Scale -> Gorebyss",
    ),
}


MAX_SPECIES_BY_GENERATION = {1: 151, 2: 251, 3: 386}
