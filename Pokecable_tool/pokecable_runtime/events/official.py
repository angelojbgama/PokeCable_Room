from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

REGION_ANY = "any"
REGION_INTERNATIONAL = "international"
REGION_JP = "jp"
REGION_UNKNOWN = "unknown"

STATUS_OFFICIAL_SUPPORTED = "official_supported"
STATUS_OFFICIAL_REMOVED = "official_removed"
STATUS_RESEARCH_REQUIRED = "research_required"
STATUS_OFFICIAL_UNRELEASED = "official_unreleased"
STATUS_UNSUPPORTED = "unsupported"

WRITER_IMPLEMENTED = "implemented"
WRITER_RESEARCH_REQUIRED = "research_required"

AUTHENTICITY_EVENT_ITEM_RESTORE = "event_item_restore"
AUTHENTICITY_OFFICIAL_CHANNEL_RECONSTRUCTED = "official_channel_reconstructed"


@dataclass(frozen=True, slots=True)
class ExtraSaveProfile:
    game_id: str
    generation: int
    region: str = REGION_UNKNOWN
    language: str = REGION_UNKNOWN
    revision: str = REGION_UNKNOWN
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OfficialExtra:
    id: str
    generation: int
    supported_games: tuple[str, ...]
    supported_regions: tuple[str, ...]
    name_key: str
    desc_key: str
    category: str
    distribution_channel: str
    target_system: str
    official_status: str = STATUS_OFFICIAL_SUPPORTED
    release_status: str = "released"
    distribution_method: str = ""
    storage_target: str = "bag:key_items"
    required_free_slots: int = 1
    required_any_capabilities: tuple[str, ...] = ()
    requires_wonder_card: bool = False
    requires_record_mixing: bool = False
    writer_status: str = WRITER_IMPLEMENTED
    blocked_reason: str = ""
    authenticity_level: str = AUTHENTICITY_EVENT_ITEM_RESTORE
    source_notes: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExtraCompatibility:
    extra_id: str
    available: bool
    can_apply: bool
    reason: str = ""
    message: str = ""


OFFICIAL_EXTRAS: tuple[OfficialExtra, ...] = (
    OfficialExtra(
        id="gen2_gsball_jp_mobile",
        generation=2,
        supported_games=("pokemon_crystal",),
        supported_regions=(REGION_JP,),
        name_key="event_gen2_gsball",
        desc_key="event_gen2_gsball_desc",
        category="ticket",
        distribution_channel="mobile_system_gb",
        target_system="gs_ball",
        distribution_method="mobile_system_gb",
        authenticity_level=AUTHENTICITY_OFFICIAL_CHANNEL_RECONSTRUCTED,
        source_notes="Japanese Crystal GS Ball path via Mobile System GB.",
        payload={"item_id": 115},
    ),
    OfficialExtra(
        id="gen2_gsball_vc",
        generation=2,
        supported_games=("pokemon_crystal",),
        supported_regions=(REGION_ANY,),
        name_key="event_gen2_gsball",
        desc_key="event_gen2_gsball_desc",
        category="ticket",
        distribution_channel="virtual_console",
        target_system="gs_ball",
        distribution_method="virtual_console",
        required_any_capabilities=("virtual_console",),
        authenticity_level=AUTHENTICITY_OFFICIAL_CHANNEL_RECONSTRUCTED,
        source_notes="Crystal Virtual Console GS Ball/Celebi event path.",
        payload={"item_id": 115},
    ),
    OfficialExtra(
        id="gen2_gsball_restore",
        generation=2,
        supported_games=("pokemon_crystal",),
        supported_regions=(REGION_ANY,),
        name_key="event_gen2_gsball",
        desc_key="event_gen2_gsball_desc",
        category="ticket",
        distribution_channel="save_reconstruction",
        target_system="gs_ball",
        distribution_method="save_reconstruction",
        authenticity_level=AUTHENTICITY_OFFICIAL_CHANNEL_RECONSTRUCTED,
        source_notes="Reconstructed GS Ball/Celebi event path for non-VC Crystal saves in Pokecable.",
        payload={"item_id": 115},
    ),
    OfficialExtra(
        id="gen3_eon_ticket",
        generation=3,
        supported_games=("pokemon_ruby", "pokemon_sapphire"),
        supported_regions=(REGION_ANY,),
        name_key="event_gen3_eon",
        desc_key="event_gen3_eon_desc",
        category="ticket",
        distribution_channel="mystery_event",
        target_system="bag_item",
        distribution_method="mystery_event",
        source_notes="Official Ruby/Sapphire Eon Ticket distribution path.",
        # EonTicket enables Southern Island (Latios/Latias). In R/S this is
        # FLAG_SYS_HAS_EON_TICKET = SYSTEM_FLAGS(0x800)+0x53 = 0x853 (2131).
        payload={"item_id": 275, "flags": {"rs": [2131]}},
    ),
    OfficialExtra(
        id="gen3_eon_ticket_emerald_record_mixing",
        generation=3,
        supported_games=("pokemon_emerald",),
        supported_regions=(REGION_ANY,),
        name_key="event_gen3_eon",
        desc_key="event_gen3_eon_emerald_desc",
        category="ticket",
        distribution_channel="record_mixing",
        target_system="bag_item",
        distribution_method="record_mixing",
        requires_record_mixing=True,
        authenticity_level=AUTHENTICITY_OFFICIAL_CHANNEL_RECONSTRUCTED,
        source_notes="Emerald receives Eon Ticket from Ruby/Sapphire through Record Mixing, not direct Mystery Event.",
        # Emerald uses FLAG_ENABLE_SHIP_SOUTHERN_ISLAND = SYSTEM_FLAGS(0x860)+0x53 = 0x8B3 (2227).
        payload={"item_id": 275, "flags": {"emerald": [2227]}},
    ),
    OfficialExtra(
        id="gen3_aurora",
        generation=3,
        supported_games=("pokemon_firered", "pokemon_leafgreen", "pokemon_emerald"),
        supported_regions=(REGION_ANY,),
        name_key="event_gen3_aurora",
        desc_key="event_gen3_aurora_desc",
        category="ticket",
        distribution_channel="mystery_gift",
        target_system="bag_item",
        distribution_method="mystery_gift",
        source_notes="Official AuroraTicket distribution path.",
        # AuroraTicket enables Birth Island (Deoxys) via FLAG_ENABLE_SHIP_BIRTH_ISLAND.
        # FR/LG 0x800+0x4B=0x84B(2123); Emerald 0x860+0x75=0x8D5(2261).
        # (Previously a flat [2122, 2123]: FR/LG-only and it also enabled Navel Rock.)
        payload={"item_id": 371, "flags": {"frlg": [2123], "emerald": [2261]}},
    ),
    OfficialExtra(
        id="gen3_mystic",
        generation=3,
        supported_games=("pokemon_firered", "pokemon_leafgreen", "pokemon_emerald"),
        supported_regions=(REGION_ANY,),
        name_key="event_gen3_mystic",
        desc_key="event_gen3_mystic_desc",
        category="ticket",
        distribution_channel="mystery_gift",
        target_system="bag_item",
        distribution_method="mystery_gift",
        source_notes="Official MysticTicket distribution path.",
        # Item alone is not enough: the ferry only offers Navel Rock (Ho-Oh/Lugia)
        # once FLAG_ENABLE_SHIP_NAVEL_ROCK is set. Flag id differs per game:
        # FR/LG SYS_FLAGS(0x800)+0x4A=0x84A(2122); Emerald SYSTEM_FLAGS(0x860)+0x80=0x8E0(2272).
        payload={"item_id": 370, "flags": {"frlg": [2122], "emerald": [2272]}},
    ),
    OfficialExtra(
        id="gen3_old_sea_map",
        generation=3,
        supported_games=("pokemon_emerald",),
        supported_regions=(REGION_ANY,),
        name_key="event_gen3_old_sea_map",
        desc_key="event_gen3_old_sea_map_desc",
        category="ticket",
        distribution_channel="mystery_gift",
        target_system="bag_item",
        distribution_method="mystery_gift",
        source_notes="Official Old Sea Map distribution is limited to Japanese Emerald; Pokecable exposes it for Emerald saves in Extras.",
        payload={"item_id": 376, "flags": [316, 2262]},
    ),
    OfficialExtra(
        id="gen4_member_card",
        generation=4,
        supported_games=("pokemon_diamond", "pokemon_pearl", "pokemon_platinum"),
        supported_regions=(REGION_ANY,),
        name_key="event_gen4_member_card",
        desc_key="event_gen4_member_card_desc",
        category="ticket",
        distribution_channel="mystery_gift",
        target_system="bag_item",
        distribution_method="mystery_gift",
        source_notes="Official Member Card distribution path.",
        payload={"item_id": 454},
    ),
    OfficialExtra(
        id="gen4_oaks_letter",
        generation=4,
        supported_games=("pokemon_platinum",),
        supported_regions=(REGION_ANY,),
        name_key="event_gen4_oaks_letter",
        desc_key="event_gen4_oaks_letter_desc",
        category="ticket",
        distribution_channel="mystery_gift",
        target_system="bag_item",
        distribution_method="mystery_gift",
        source_notes="Official Oak's Letter distribution path.",
        payload={"item_id": 452},
    ),
    OfficialExtra(
        id="gen4_secret_key",
        generation=4,
        supported_games=("pokemon_platinum",),
        supported_regions=(REGION_ANY,),
        name_key="event_gen4_secret_key",
        desc_key="event_gen4_secret_key_desc",
        category="ticket",
        distribution_channel="mystery_gift",
        target_system="bag_item",
        distribution_method="mystery_gift",
        source_notes="Official Platinum Secret Key distribution path.",
        payload={"item_id": 467},
    ),
    OfficialExtra(
        id="gen4_azure_flute",
        generation=4,
        supported_games=("pokemon_diamond", "pokemon_pearl", "pokemon_platinum"),
        supported_regions=(REGION_ANY,),
        name_key="event_gen4_azure_flute",
        desc_key="event_gen4_azure_flute_desc",
        category="ticket",
        distribution_channel="mystery_gift",
        target_system="bag_item",
        official_status=STATUS_OFFICIAL_UNRELEASED,
        release_status="unreleased",
        distribution_method="unreleased",
        blocked_reason="Azure Flute exists in game data but was not officially distributed.",
        source_notes="Explicitly blocked because it was unreleased.",
        payload={"item_id": 455},
    ),
    OfficialExtra(
        id="gen4_enigma_stone",
        generation=4,
        supported_games=("pokemon_heartgold", "pokemon_soulsilver"),
        supported_regions=(REGION_ANY,),
        name_key="event_gen4_enigma_stone",
        desc_key="event_gen4_enigma_stone_desc",
        category="ticket",
        distribution_channel="mystery_gift",
        target_system="bag_item",
        distribution_method="mystery_gift",
        source_notes="Official Enigma Stone distribution path.",
        payload={"item_id": 536},
    ),
    OfficialExtra(
        id="ereader",
        generation=3,
        supported_games=("pokemon_ruby", "pokemon_sapphire"),
        supported_regions=(REGION_INTERNATIONAL, REGION_JP),
        name_key="event_gen3_ereader",
        desc_key="event_gen3_ereader_desc",
        category="ereader",
        distribution_channel="e_reader",
        target_system="rs_battle_e",
        official_status=STATUS_RESEARCH_REQUIRED,
        release_status="released",
        distribution_method="e_reader",
        storage_target="rs_battle_e_slots",
        required_free_slots=0,
        writer_status=WRITER_RESEARCH_REQUIRED,
        blocked_reason="Writer R/S incorreto: assume 5 slots de 40 bytes em offset plano 0x3030; o real e um unico struct BattleTowerEReaderTrainer (188 bytes) em SaveBlock2+0x498, com party de 3 Pokemon completos e checksum proprio. Bloqueado ate reimplementar.",
        source_notes="Ruby/Sapphire Battle-e support; writer atual nao corresponde ao struct real do pokeruby (verificado na disassembly). Ver memoria gsball/extras.",
    ),
    OfficialExtra(
        id="emerald_international_battle_e",
        generation=3,
        supported_games=("pokemon_emerald",),
        supported_regions=(REGION_INTERNATIONAL,),
        name_key="event_gen3_ereader",
        desc_key="event_gen3_ereader_desc",
        category="ereader",
        distribution_channel="e_reader",
        target_system="emerald_trainer_hill",
        official_status=STATUS_OFFICIAL_REMOVED,
        release_status="removed_international",
        distribution_method="e_reader",
        storage_target="emerald_trainer_hill",
        required_free_slots=0,
        blocked_reason="Battle-e Trainer Hill support was removed from international Emerald.",
        source_notes="Battle-e Trainer Hill support was removed from international Emerald.",
    ),
    OfficialExtra(
        id="emerald_jp_trainer_hill",
        generation=3,
        supported_games=("pokemon_emerald",),
        supported_regions=(REGION_JP,),
        name_key="event_gen3_ereader",
        desc_key="event_gen3_ereader_desc",
        category="ereader",
        distribution_channel="e_reader",
        target_system="emerald_jp_trainer_hill",
        official_status=STATUS_RESEARCH_REQUIRED,
        release_status="released_jp",
        distribution_method="e_reader",
        storage_target="emerald_jp_trainer_hill",
        required_free_slots=0,
        writer_status=WRITER_RESEARCH_REQUIRED,
        blocked_reason="Japanese Emerald Trainer Hill writer is not implemented yet.",
        source_notes="Japanese Emerald Trainer Hill e-Reader support needs a dedicated writer.",
    ),
    OfficialExtra(
        id="frlg_jp_trainer_tower",
        generation=3,
        supported_games=("pokemon_firered", "pokemon_leafgreen"),
        supported_regions=(REGION_JP,),
        name_key="event_gen3_ereader",
        desc_key="event_gen3_ereader_desc",
        category="ereader",
        distribution_channel="e_reader",
        target_system="frlg_jp_trainer_tower",
        official_status=STATUS_RESEARCH_REQUIRED,
        release_status="released_jp",
        distribution_method="e_reader",
        storage_target="frlg_jp_trainer_tower",
        required_free_slots=0,
        writer_status=WRITER_RESEARCH_REQUIRED,
        blocked_reason="Japanese FireRed/LeafGreen Trainer Tower writer is not implemented yet.",
        source_notes="Japanese FireRed/LeafGreen Trainer Tower e-Reader support needs a dedicated writer.",
    ),
)


def profile_from_save(save_model) -> ExtraSaveProfile:
    game_id = str(getattr(save_model, "game", "") or "")
    generation = int(getattr(save_model, "generation", 0) or 0)
    path = getattr(save_model, "path", None)
    name = str(getattr(path, "name", "") or "").lower()
    region = _infer_region(name)
    language = "ja" if region == REGION_JP else ("en" if region == REGION_INTERNATIONAL else REGION_UNKNOWN)
    return ExtraSaveProfile(
        game_id=game_id,
        generation=generation,
        region=region,
        language=language,
        capabilities=_infer_capabilities(name),
    )


def profile_from_game(
    game_id: str,
    generation: int | None = None,
    region: str = REGION_UNKNOWN,
    capabilities: tuple[str, ...] = (),
) -> ExtraSaveProfile:
    return ExtraSaveProfile(
        game_id=str(game_id),
        generation=int(generation or _generation_from_game(game_id)),
        region=region,
        capabilities=tuple(capabilities),
    )


def get_official_extra(extra_id: str) -> OfficialExtra | None:
    for extra in OFFICIAL_EXTRAS:
        if extra.id == extra_id:
            return extra
    return None


def list_official_extras(*, include_unavailable: bool = True) -> list[OfficialExtra]:
    if include_unavailable:
        return list(OFFICIAL_EXTRAS)
    return [extra for extra in OFFICIAL_EXTRAS if extra.official_status == STATUS_OFFICIAL_SUPPORTED]


def get_available_extras_for_save(save_model) -> list[dict[str, Any]]:
    profile = profile_from_save(save_model)
    return [
        official_extra_to_event(extra)
        for extra in OFFICIAL_EXTRAS
        if compatibility_for_extra(profile, extra).available
    ]


def get_events_for_profile(profile: ExtraSaveProfile) -> list[dict[str, Any]]:
    return [
        official_extra_to_event(extra)
        for extra in OFFICIAL_EXTRAS
        if compatibility_for_extra(profile, extra).available
    ]


def compatibility_for_save(save_model, extra_or_id: OfficialExtra | str) -> ExtraCompatibility:
    extra = get_official_extra(extra_or_id) if isinstance(extra_or_id, str) else extra_or_id
    if extra is None:
        return ExtraCompatibility(str(extra_or_id), False, False, "not_found", "Evento nao encontrado")
    return compatibility_for_extra(profile_from_save(save_model), extra)


def compatibility_for_extra(profile: ExtraSaveProfile, extra: OfficialExtra) -> ExtraCompatibility:
    if profile.generation and profile.generation != extra.generation:
        return _blocked(extra, "generation_mismatch", "extras_not_supported")
    if profile.game_id not in extra.supported_games:
        return _blocked(extra, "game_not_supported", "extras_not_supported")
    if extra.official_status == STATUS_OFFICIAL_REMOVED:
        return _blocked(extra, "official_removed", "extras_not_supported")
    if extra.official_status == STATUS_RESEARCH_REQUIRED:
        return _blocked(extra, "research_required", "extras_not_supported")
    if extra.official_status == STATUS_OFFICIAL_UNRELEASED:
        return _blocked(extra, "official_unreleased", "extras_not_supported")
    if extra.official_status != STATUS_OFFICIAL_SUPPORTED:
        return _blocked(extra, "unsupported", "extras_not_supported")
    if not _region_matches(profile.region, extra.supported_regions):
        reason = "region_unknown" if profile.region == REGION_UNKNOWN else "region_not_supported"
        return _blocked(extra, reason, "extras_not_supported")
    if extra.required_any_capabilities and not set(profile.capabilities).intersection(extra.required_any_capabilities):
        return _blocked(extra, "capability_required", "extras_not_supported")
    if extra.writer_status != WRITER_IMPLEMENTED:
        return _blocked(extra, "writer_not_implemented", "extras_not_supported")
    return ExtraCompatibility(extra.id, True, True)


def official_extra_to_event(extra: OfficialExtra) -> dict[str, Any]:
    event = {
        "id": extra.id,
        "generation": extra.generation,
        "games": list(extra.supported_games),
        "regions": list(extra.supported_regions),
        "name_key": extra.name_key,
        "desc_key": extra.desc_key,
        "category": extra.category,
        "distribution_channel": extra.distribution_channel,
        "target_system": extra.target_system,
        "official_status": extra.official_status,
        "release_status": extra.release_status,
        "distribution_method": extra.distribution_method or extra.distribution_channel,
        "storage_target": extra.storage_target,
        "required_free_slots": extra.required_free_slots,
        "required_any_capabilities": list(extra.required_any_capabilities),
        "requires_wonder_card": extra.requires_wonder_card,
        "requires_record_mixing": extra.requires_record_mixing,
        "writer_status": extra.writer_status,
        "blocked_reason": extra.blocked_reason,
        "authenticity_level": extra.authenticity_level,
        "source_notes": extra.source_notes,
    }
    event.update(extra.payload)
    return event


def _blocked(extra: OfficialExtra, reason: str, message: str) -> ExtraCompatibility:
    return ExtraCompatibility(extra.id, False, False, reason, message)


def _region_matches(region: str, supported_regions: Iterable[str]) -> bool:
    supported = set(supported_regions)
    return REGION_ANY in supported or region in supported


def _infer_region(filename: str) -> str:
    if any(token in filename for token in ("japan", "japanese", "(j)", "[j]", "_jp", "-jp", " jp")):
        return REGION_JP
    if any(token in filename for token in ("usa", "europe", "english", "(u)", "[u]", " version")):
        return REGION_INTERNATIONAL
    return REGION_UNKNOWN


def _infer_capabilities(filename: str) -> tuple[str, ...]:
    capabilities: list[str] = []
    if any(token in filename for token in ("virtual console", "virtual-console", "_vc", "-vc", "(vc)", "[vc]")):
        capabilities.append("virtual_console")
    if any(token in filename for token in ("mobile system", "mobile_system", "mobile-gb", "mobilegb")):
        capabilities.append("mobile_system_gb")
    return tuple(capabilities)


def _generation_from_game(game_id: str) -> int:
    if game_id in {"pokemon_red", "pokemon_blue", "pokemon_yellow"}:
        return 1
    if game_id in {"pokemon_gold", "pokemon_silver", "pokemon_crystal"}:
        return 2
    if game_id in {"pokemon_ruby", "pokemon_sapphire", "pokemon_emerald", "pokemon_firered", "pokemon_leafgreen"}:
        return 3
    if game_id.startswith("pokemon_"):
        return 4
    return 0
