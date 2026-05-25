from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from Pokecable_tool.pokecable_save import SaveError, load_save
from Pokecable_tool.r36s_pokecable_core import (
    apply_all_safe_events_to_save,
    apply_ereader_to_save,
    apply_event_to_save,
    get_applied_events,
    get_available_events,
    get_ereader_slots,
    preflight_extras_for_save,
)
from Pokecable_tool.pokecable_runtime.events.official import (
    STATUS_OFFICIAL_REMOVED,
    STATUS_RESEARCH_REQUIRED,
    STATUS_OFFICIAL_UNRELEASED,
    get_official_extra,
)
from save_repair import repair_gen3_save_file  # moved into tests/

TEST_SAVES = Path(__file__).resolve().parent.parent / "roms" / "test-saves"


@pytest.fixture
def backup_env(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    monkeypatch.setenv("POKECABLE_BACKUP_DIR", str(backup_dir))
    return backup_dir


@pytest.fixture
def save_copy(tmp_path):
    def _copy(relative_path: str) -> Path:
        src = TEST_SAVES / relative_path
        dst = tmp_path / src.name
        shutil.copy2(src, dst)
        return dst

    return _copy


def test_applied_events_are_filtered_by_game():
    platinum = TEST_SAVES / "gen 4" / "Pokemon - Platinum Version (USA).sav"
    result = get_applied_events(platinum)
    assert result["success"] is True
    assert result["applied_event_ids"] == {"gen4_member_card", "gen4_oaks_letter", "gen4_secret_key"}
    assert "gen3_eon_ticket" not in result["applied_event_ids"]
    assert "gen4_azure_flute" not in result["applied_event_ids"]


def test_ereader_slots_read_from_real_sapphire():
    sapphire = TEST_SAVES / "gen 3" / "Pokémon - Sapphire Version.sav"
    result = get_ereader_slots(sapphire)
    assert result["success"] is True
    assert len(result["slots"]) == 5
    assert all("is_empty" in slot for slot in result["slots"])


def test_ticket_apply_is_idempotent_on_real_save(save_copy, backup_env):
    sapphire = save_copy("gen 3/Pokémon - Sapphire Version.sav")
    before = get_applied_events(sapphire)
    assert "gen3_eon_ticket" not in before["applied_event_ids"]

    first = apply_event_to_save(sapphire, "gen3_eon_ticket")
    assert first["success"] is True

    after = get_applied_events(sapphire)
    assert "gen3_eon_ticket" in after["applied_event_ids"]

    second = apply_event_to_save(sapphire, "gen3_eon_ticket")
    assert second == {"success": False, "message": "extras_already_active"}
    assert any(backup_env.glob("*.bak"))


def test_ereader_duplicate_is_blocked_across_slots(save_copy, backup_env):
    sapphire = save_copy("gen 3/Pokémon - Sapphire Version.sav")

    first = apply_ereader_to_save(sapphire, 0, "vincent")
    assert first["success"] is True

    applied = get_applied_events(sapphire)
    assert applied["applied_ereader_battles"] == {"vincent"}
    assert applied["occupied_ereader_slots"] == {0}

    second = apply_ereader_to_save(sapphire, 1, "vincent")
    assert second == {"success": False, "message": "extras_already_active"}


def test_available_events_match_supported_games():
    crystal = get_available_events(TEST_SAVES / "gen 2" / "Pokémon - Crystal Version.sav")
    sapphire = get_available_events(TEST_SAVES / "gen 3" / "Pokémon - Sapphire Version.sav")
    emerald = get_available_events(TEST_SAVES / "gen 3" / "Pokémon - Emerald Version.sav")
    yellow = get_available_events(TEST_SAVES / "gen 1" / "Pokémon - Yellow Version.sav")

    assert crystal["events"] == []
    assert {event["id"] for event in sapphire["events"]} == {"gen3_eon_ticket", "ereader"}
    assert "gen3_eon_ticket_emerald_record_mixing" in {event["id"] for event in emerald["events"]}
    assert "gen3_eon_ticket" not in {event["id"] for event in emerald["events"]}
    assert "ereader" not in {event["id"] for event in emerald["events"]}
    assert "gen3_old_sea_map" not in {event["id"] for event in emerald["events"]}
    assert yellow["events"] == []


def test_official_catalog_tracks_removed_and_research_only_targets():
    emerald_removed = get_official_extra("emerald_international_battle_e")
    emerald_jp = get_official_extra("emerald_jp_trainer_hill")
    frlg_jp = get_official_extra("frlg_jp_trainer_tower")
    azure = get_official_extra("gen4_azure_flute")

    assert emerald_removed is not None
    assert emerald_removed.official_status == STATUS_OFFICIAL_REMOVED
    assert emerald_jp is not None
    assert emerald_jp.official_status == STATUS_RESEARCH_REQUIRED
    assert frlg_jp is not None
    assert frlg_jp.official_status == STATUS_RESEARCH_REQUIRED
    assert azure is not None
    assert azure.official_status == STATUS_OFFICIAL_UNRELEASED


def test_regional_official_policy_blocks_old_sea_map_on_international_emerald(save_copy, backup_env):
    emerald = save_copy("gen 3/Pokémon - Emerald Version.sav")

    result = apply_event_to_save(emerald, "gen3_old_sea_map")
    assert result == {"success": False, "message": "extras_not_supported"}


def test_unreleased_azure_flute_is_explicitly_blocked(save_copy, backup_env):
    platinum = save_copy("gen 4/Pokemon - Platinum Version (USA).sav")

    result = apply_event_to_save(platinum, "gen4_azure_flute")
    assert result == {"success": False, "message": "extras_not_supported"}


def test_preflight_reports_batch_without_writing(save_copy, backup_env):
    sapphire = save_copy("gen 3/Pokémon - Sapphire Version.sav")

    preflight = preflight_extras_for_save(sapphire, ["gen3_eon_ticket"])

    assert preflight["success"] is True
    assert preflight["can_apply"] is True
    assert preflight["event_ids_to_apply"] == ["gen3_eon_ticket"]
    assert preflight["events"][0]["status"] == "will_apply"
    assert "gen3_eon_ticket" not in get_applied_events(sapphire)["applied_event_ids"]


def test_apply_all_safe_events_is_atomic_and_idempotent(save_copy, backup_env):
    emerald = save_copy("gen 3/Pokemon - Emerald Version (USA, Europe) 389hrs.sav")

    first = apply_all_safe_events_to_save(emerald)
    assert first["success"] is True
    assert set(first["applied_event_ids"]) == {
        "gen3_eon_ticket_emerald_record_mixing",
        "gen3_aurora",
        "gen3_mystic",
    }

    applied = get_applied_events(emerald)
    assert set(first["applied_event_ids"]).issubset(applied["applied_event_ids"])

    second = apply_all_safe_events_to_save(emerald)
    assert second["success"] is True
    assert second["message"] == "extras_already_active"
    assert second["applied_event_ids"] == []


def test_preflight_blocks_full_key_item_pocket_before_write(save_copy, backup_env):
    sapphire = save_copy("gen 3/Pokémon - Sapphire Version.sav")
    _fill_gen3_key_items(sapphire, exclude={275})

    preflight = preflight_extras_for_save(sapphire, ["gen3_eon_ticket"])
    result = apply_event_to_save(sapphire, "gen3_eon_ticket")

    assert preflight["success"] is True
    assert preflight["can_apply"] is False
    assert preflight["blockers"][0]["reason"] == "missing_space"
    assert result == {"success": False, "message": "extras_no_space"}
    assert "gen3_eon_ticket" not in get_applied_events(sapphire)["applied_event_ids"]


@pytest.mark.slow
def test_extras_matrix_on_real_saves(save_copy, backup_env):
    matrix = [
        ("gen 3/Pokémon - Sapphire Version.sav", ["gen3_eon_ticket"]),
        ("gen 3/Pokémon - Emerald Version.sav", ["gen3_eon_ticket_emerald_record_mixing"]),
        ("gen 3/Pokémon - LeafGreen Version.sav", ["gen3_mystic"]),
        ("gen 4/Pokemon - Platinum Version (USA).sav", ["gen4_member_card", "gen4_oaks_letter", "gen4_secret_key"]),
    ]

    for relative_path, event_ids in matrix:
        save_path = save_copy(relative_path)
        for event_id in event_ids:
            before = get_applied_events(save_path)
            result = apply_event_to_save(save_path, event_id)
            if event_id in before["applied_event_ids"]:
                assert result == {"success": False, "message": "extras_already_active"}, (relative_path, event_id, result)
                continue
            assert result["success"] is True, (relative_path, event_id, result)
            applied = get_applied_events(save_path)
            assert event_id in applied["applied_event_ids"]


@pytest.mark.slow
def test_all_ereader_battles_fit_unique_slots(save_copy, backup_env):
    sapphire = save_copy("gen 3/Pokémon - Sapphire Version.sav")
    battle_ids = ["vincent", "levi", "ernest", "gwen", "larry"]

    for slot, battle_id in enumerate(battle_ids):
        result = apply_ereader_to_save(sapphire, slot, battle_id)
        assert result["success"] is True, (slot, battle_id, result)

    slots = get_ereader_slots(sapphire)
    assert slots["success"] is True
    assert [slot["battle_id"] for slot in slots["slots"]] == battle_ids


@pytest.mark.slow
def test_apply_all_safe_events_stress_all_real_saves(tmp_path, backup_env):
    stress_dir = tmp_path / "stress-saves"
    for source in sorted(TEST_SAVES.rglob("*.sav")):
        relative = source.relative_to(TEST_SAVES)
        target = stress_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

        available = get_available_events(target)
        if not available["success"]:
            continue

        preflight = preflight_extras_for_save(target)
        before_bytes = target.read_bytes()
        result = apply_all_safe_events_to_save(target)

        assert preflight["success"] is True, relative
        if not preflight["can_apply"]:
            assert result["success"] is False, (relative, result)
            assert target.read_bytes() == before_bytes, relative
            continue

        assert result["success"] is True, (relative, result)

        second = apply_all_safe_events_to_save(target)
        assert second["success"] is True, (relative, second)


@pytest.mark.parametrize(
    "relative_path",
    [
        "gen 3/Pokémon - FireRed Version.sav",
        "gen 3/Pokémon - Ruby Version.sav",
        "gen 3/Pokémon Ruby Version [save file].sav",
    ],
)
def test_repair_corrupted_gen3_saves(save_copy, relative_path):
    broken = save_copy(relative_path)

    try:
        load_save(broken)
        was_valid = True
    except SaveError:
        was_valid = False

    result = repair_gen3_save_file(broken)
    assert result["success"] is True
    assert result["changed"] is (not was_valid)

    repaired = load_save(broken)
    assert repaired.generation == 3


def _fill_gen3_key_items(save_path: Path, *, exclude: set[int]):
    from Pokecable_tool.pokecable_save import _ensure_backend_import_path

    _ensure_backend_import_path()
    from parsers import Gen3Parser

    parser = Gen3Parser()
    parser.load(save_path)
    candidates = [
        259,
        260,
        261,
        262,
        263,
        264,
        265,
        266,
        268,
        269,
        270,
        271,
        272,
        273,
        274,
        276,
        277,
        278,
        279,
        280,
        281,
        282,
        283,
        284,
        285,
        286,
        287,
        288,
        370,
        371,
        376,
    ]
    for item_id in candidates:
        if item_id in exclude:
            continue
        key_items = [entry for entry in parser.list_inventory() if entry.pocket_name == "key_items"]
        if len(key_items) >= 20:
            break
        if all(entry.item_id != item_id for entry in key_items):
            parser.store_item_in_bag(item_id, 1)
    parser.save(save_path)
