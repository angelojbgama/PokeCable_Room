EREADER_BATTLES_WESTERN = [
    {
        "id": "vincent",
        "name": "VINCENT",
        "trainer_class": 21,
        "mons": [
            {"species": 271, "level": 20},
            {"species": 319, "level": 25},
            {"species": 320, "level": 25},
        ],
    },
    {
        "id": "levi",
        "name": "LEVI",
        "trainer_class": 14,
        "mons": [
            {"species": 275, "level": 18},
            {"species": 284, "level": 22},
            {"species": 262, "level": 25},
        ],
    },
    {
        "id": "ernest",
        "name": "ERNEST",
        "trainer_class": 11,
        "mons": [
            {"species": 299, "level": 20},
            {"species": 304, "level": 22},
            {"species": 306, "level": 30},
        ],
    },
    {
        "id": "gwen",
        "name": "GWEN",
        "trainer_class": 29,
        "mons": [
            {"species": 298, "level": 15},
            {"species": 300, "level": 18},
            {"species": 313, "level": 20},
        ],
    },
    {
        "id": "larry",
        "name": "LARRY",
        "trainer_class": 34,
        "mons": [
            {"species": 327, "level": 20},
            {"species": 352, "level": 22},
            {"species": 275, "level": 28},
        ],
    },
]


def get_ereader_battle(battle_id):
    for battle in EREADER_BATTLES_WESTERN:
        if battle["id"] == battle_id:
            return battle
    return None


def list_ereader_battles():
    return EREADER_BATTLES_WESTERN
