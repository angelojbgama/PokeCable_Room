EVENTS_CATALOG = [
    {
        "id": "gen2_gsball",
        "generation": 2,
        "games": ["pokemon_crystal"],
        "name_key": "event_gen2_gsball",
        "desc_key": "event_gen2_gsball_desc",
        "category": "ticket",
        "item_id": 115,
    },
    {
        "id": "gen3_eon_ticket",
        "generation": 3,
        "games": ["pokemon_ruby", "pokemon_sapphire", "pokemon_emerald"],
        "name_key": "event_gen3_eon",
        "desc_key": "event_gen3_eon_desc",
        "category": "ticket",
        "item_id": 275,
    },
    {
        "id": "gen3_aurora",
        "generation": 3,
        "games": ["pokemon_firered", "pokemon_leafgreen", "pokemon_emerald"],
        "name_key": "event_gen3_aurora",
        "desc_key": "event_gen3_aurora_desc",
        "category": "ticket",
        "item_id": 371,
        "flags": [2122, 2123],
    },
    {
        "id": "gen3_mystic",
        "generation": 3,
        "games": ["pokemon_firered", "pokemon_leafgreen", "pokemon_emerald"],
        "name_key": "event_gen3_mystic",
        "desc_key": "event_gen3_mystic_desc",
        "category": "ticket",
        "item_id": 370,
    },
    {
        "id": "gen3_old_sea_map",
        "generation": 3,
        "games": ["pokemon_emerald"],
        "name_key": "event_gen3_old_sea_map",
        "desc_key": "event_gen3_old_sea_map_desc",
        "category": "ticket",
        "item_id": 376,
        "flags": [316, 2262],
    },
    {
        "id": "gen4_member_card",
        "generation": 4,
        "games": ["pokemon_diamond", "pokemon_pearl", "pokemon_platinum"],
        "name_key": "event_gen4_member_card",
        "desc_key": "event_gen4_member_card_desc",
        "category": "ticket",
        "item_id": 467,
    },
    {
        "id": "gen4_oaks_letter",
        "generation": 4,
        "games": ["pokemon_platinum"],
        "name_key": "event_gen4_oaks_letter",
        "desc_key": "event_gen4_oaks_letter_desc",
        "category": "ticket",
        "item_id": 466,
    },
    {
        "id": "gen4_enigma_stone",
        "generation": 4,
        "games": ["pokemon_heartgold", "pokemon_soulsilver"],
        "name_key": "event_gen4_enigma_stone",
        "desc_key": "event_gen4_enigma_stone_desc",
        "category": "ticket",
        "item_id": 469,
    },
]

EREADER_BATTLES_CATALOG = [
    {
        "id": "ereader",
        "generation": 3,
        "games": ["pokemon_ruby", "pokemon_sapphire"],
        "name_key": "event_gen3_ereader",
        "desc_key": "event_gen3_ereader_desc",
        "category": "ereader",
    },
]


def get_events_for_game(game_id):
    events = []
    for event in EVENTS_CATALOG:
        if game_id in event["games"]:
            events.append(event)

    if game_id in ["pokemon_ruby", "pokemon_sapphire"]:
        events.extend(EREADER_BATTLES_CATALOG)

    return events


def get_event_by_id(event_id):
    for event in EVENTS_CATALOG + EREADER_BATTLES_CATALOG:
        if event["id"] == event_id:
            return event
    return None
