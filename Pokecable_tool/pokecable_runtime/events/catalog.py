from __future__ import annotations

from .official import (
    OFFICIAL_EXTRAS,
    REGION_INTERNATIONAL,
    STATUS_OFFICIAL_SUPPORTED,
    get_available_extras_for_save,
    get_events_for_profile,
    get_official_extra,
    official_extra_to_event,
    profile_from_game,
)


EVENTS_CATALOG = [
    official_extra_to_event(extra)
    for extra in OFFICIAL_EXTRAS
    if extra.category == "ticket" and extra.official_status == STATUS_OFFICIAL_SUPPORTED
]

EREADER_BATTLES_CATALOG = [
    official_extra_to_event(extra)
    for extra in OFFICIAL_EXTRAS
    if extra.category == "ereader" and extra.official_status == STATUS_OFFICIAL_SUPPORTED
]


def get_events_for_game(game_id):
    profile = profile_from_game(game_id, region=REGION_INTERNATIONAL)
    return get_events_for_profile(profile)


def get_events_for_save(save_model):
    return get_available_extras_for_save(save_model)


def get_event_by_id(event_id):
    extra = get_official_extra(event_id)
    if extra is None:
        return None
    return official_extra_to_event(extra)
