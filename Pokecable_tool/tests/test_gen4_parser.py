from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _path in (str(REPO_ROOT), str(RUNTIME)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from parsers.gen4 import Gen4Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402
from canonical import CanonicalMove, CanonicalPokemon, CanonicalStats  # noqa: E402
from compatibility import build_compatibility_report  # noqa: E402
from converters import get_converter  # noqa: E402
from data.learnsets import get_level_up_replacements, is_hm_move_for_game  # noqa: E402
from data.items import item_category, item_name  # noqa: E402
from data.moves import default_move_pp  # noqa: E402
from data.species import SPECIES_NAMES_BY_NATIONAL  # noqa: E402
from evolutions.engine import preview_trade_evolution  # noqa: E402
from pokecable_save import load_save  # noqa: E402
from save_curation import GEN4_SAVE_DIR, get_curated_gen4_saves, get_gen4_save_audit  # noqa: E402


TEST_SAVE = REPO_ROOT.parent / "roms" / "test-saves" / "gen 4" / "Pokemon - Platinum Version (USA).sav"
SOULSILVER_SAVE = GEN4_SAVE_DIR / "Pokemon_SoulSilver8gyn.sav"
GEN3_SAVE = REPO_ROOT.parent / "roms" / "test-saves" / "gen 3" / "Pokémon - Emerald Version.sav"


@pytest.mark.skipif(not TEST_SAVE.exists(), reason="save de Platinum nao disponivel")
def test_gen4_detect_and_load():
    parser = Gen4Parser()
    assert parser.detect(TEST_SAVE)
    parser.load(TEST_SAVE)
    assert parser.get_generation() == 4
    assert parser.get_game_id() == "pokemon_platinum"
    assert parser.get_player_name()
    assert len(parser.list_party()) > 0
    assert parser.validate()


def test_species_catalog_has_legacy_gen1_gen2_names():
    assert SPECIES_NAMES_BY_NATIONAL[21] == "Spearow"
    assert SPECIES_NAMES_BY_NATIONAL[33] == "Nidorino"
    assert SPECIES_NAMES_BY_NATIONAL[175] == "Togepi"


@pytest.mark.skipif(not SOULSILVER_SAVE.exists(), reason="save de SoulSilver nao disponivel")
def test_gen4_box_filters_stale_invalid_pk4_records():
    parser = Gen4Parser()
    parser.load(SOULSILVER_SAVE)

    boxes = {summary.location: summary for summary in parser.list_boxes()}
    assert "box:1:4" not in boxes
    with pytest.raises(ValueError):
        parser.export_canonical("box:1:4")

    dratini = boxes["box:1:7"]
    assert dratini.national_dex_id == 147
    assert dratini.species_name == "Dratini"
    assert dratini.nickname == "DRATINI"

    spearow = boxes["box:1:15"]
    assert spearow.national_dex_id == 21
    assert spearow.species_name == "Spearow"
    assert spearow.nickname == "SPEAROW"
    exported = parser.export_canonical("box:1:15")
    assert [move.name for move in exported.moves[:3]] == ["Peck", "Growl", "Leer"]


@pytest.mark.skipif(not TEST_SAVE.exists(), reason="save de Platinum nao disponivel")
def test_gen4_save_model_roundtrip(tmp_path: Path):
    work = tmp_path / TEST_SAVE.name
    shutil.copy2(TEST_SAVE, work)
    save = load_save(work)
    assert save.generation == 4
    payload = save.export_payload("party:0")
    before = work.read_bytes()
    result = save.apply_payload("party:0", payload)
    after = work.read_bytes()
    assert len(before) == len(after)
    assert result["location"] == "party:0"
    reparsed = load_save(work)
    assert reparsed.party


@pytest.mark.skipif(not TEST_SAVE.exists(), reason="save de Platinum nao disponivel")
def test_platinum_giratina_genderless_and_griseous_orb_item():
    parser = Gen4Parser()
    parser.load(TEST_SAVE)

    party_giratina = [
        summary
        for summary in parser.list_party()
        if summary.national_dex_id == 487
    ]

    assert len(party_giratina) == 2
    assert {summary.held_item_id for summary in party_giratina} == {None, 112}
    assert all(summary.gender is None for summary in party_giratina)
    assert item_name(112, 4) == "Griseous Orb"

    orb_holder = next(summary for summary in party_giratina if summary.held_item_id == 112)
    assert orb_holder.held_item_name == "Griseous Orb"
    exported = parser.export_canonical(orb_holder.location)
    assert exported.metadata["gender"] is None
    assert exported.metadata["raw_gender_code"] == 2
    assert exported.held_item is not None
    assert exported.held_item.name == "Griseous Orb"


@pytest.mark.skipif(not GEN4_SAVE_DIR.exists(), reason="pasta de saves Gen4 nao disponivel")
def test_all_gen4_saves_export_clean_item_move_and_pp_data(tmp_path: Path):
    saves = get_curated_gen4_saves()
    assert saves

    for save_path in saves:
        parser = Gen4Parser()
        assert parser.detect(save_path), save_path.name
        parser.load(save_path)
        assert parser.validate(), save_path.name

        for summary in parser.list_party() + parser.list_boxes():
            if summary.held_item_name:
                assert "?" not in summary.held_item_name, (save_path.name, summary.location, summary.held_item_id)
            canonical = parser.export_canonical(summary.location)
            if canonical.held_item and canonical.held_item.name:
                assert "?" not in canonical.held_item.name, (save_path.name, summary.location, canonical.held_item.item_id)
            for move in canonical.moves:
                assert move.name and not str(move.name).startswith("Move #"), (save_path.name, summary.location, move.move_id)
                assert 0 <= int(move.pp_ups or 0) <= 3, (save_path.name, summary.location, move.to_dict())
                assert 0 <= int(move.pp or 0) <= int(move.max_pp or 0), (save_path.name, summary.location, move.to_dict())

    nocash_saves = [path for path in saves if path.read_bytes().startswith(b"NocashGbaBackupMediaSavDataFile\x1a")]
    assert nocash_saves
    for save_path in nocash_saves:
        work = tmp_path / save_path.name
        shutil.copy2(save_path, work)
        parser = Gen4Parser()
        parser.load(work)
        assert getattr(parser, "_nocash_metadata", None)
        parser.save(work)
        assert work.read_bytes().startswith(b"NocashGbaBackupMediaSavDataFile\x1a")
        reparsed = Gen4Parser()
        reparsed.load(work)
        assert reparsed.validate()
        save_model = load_save(work)
        assert save_model.generation == 4
        assert save_model.party


@pytest.mark.skipif(not GEN4_SAVE_DIR.exists(), reason="pasta de saves Gen4 nao disponivel")
def test_gen4_curated_corpus_marks_residue_without_rejecting_functional_saves():
    audit = {record.path.name: record for record in get_gen4_save_audit()}
    assert audit
    assert all(record.approved_for_analysis for record in audit.values())
    assert any(record.has_box_residue for record in audit.values())
    assert "Pokemon - Platinum Version (USA).sav" in audit


def _canonical_gen3_for_gen4() -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=3,
        source_game="pokemon_emerald",
        species_national_id=261,
        species_name="Poochyena",
        nickname="POOCHY",
        level=12,
        ot_name="RUBY",
        trainer_id=0x12345678,
        experience=1728,
        moves=[
            CanonicalMove(move_id=33, name="Tackle", pp=35, max_pp=35, pp_ups=0, source_generation=3),
            CanonicalMove(move_id=44, name="Bite", pp=25, max_pp=25, pp_ups=0, source_generation=3),
        ],
        ivs=CanonicalStats(hp=20, attack=21, defense=22, speed=23, special_attack=24, special_defense=25),
        evs=CanonicalStats(hp=10, attack=20, defense=30, speed=40, special_attack=50, special_defense=60),
        nature="Hardy",
        ability="Index 1",
        metadata={"personality": 0x12345678, "gender": "♂"},
    )


def _canonical_gen4_for_gen3() -> CanonicalPokemon:
    canonical = _canonical_gen3_for_gen4()
    canonical.source_generation = 4
    canonical.source_game = "pokemon_platinum"
    canonical.nature = "Hardy"
    canonical.ability = "Index 1"
    return canonical


@pytest.mark.skipif(not TEST_SAVE.exists(), reason="save de Platinum nao disponivel")
def test_gen3_to_gen4_converter_writes_pk4(tmp_path: Path):
    work = tmp_path / TEST_SAVE.name
    shutil.copy2(TEST_SAVE, work)
    parser = Gen4Parser()
    parser.load(work)
    canonical = _canonical_gen3_for_gen4()
    converter = get_converter(3, 4)

    report = converter.can_convert(canonical, policy="auto_retrocompat", target_game="pokemon_platinum")
    assert report.compatible
    result = converter.apply_to_save(parser, "party:0", canonical, policy="auto_retrocompat")
    assert result.wrote_to_save

    exported = parser.export_canonical("party:0")
    assert exported.source_generation == 4
    assert exported.species_national_id == 261
    assert exported.nickname == "POOCHY"
    assert [move.move_id for move in exported.moves[:2]] == [33, 44]
    assert exported.metadata["personality"] == 0x12345678
    assert exported.level == 12
    parser.save(work)
    reparsed = Gen4Parser()
    reparsed.load(work)
    assert reparsed.validate()


def test_gen4_cross_generation_registry_and_reports():
    canonical = _canonical_gen3_for_gen4()
    for source, target in ((1, 4), (2, 4), (3, 4), (4, 1), (4, 2), (4, 3)):
        assert get_converter(source, target)
    report = build_compatibility_report(canonical, 4, policy="auto_retrocompat", target_game="pokemon_platinum")
    assert report.compatible
    assert report.mode == "forward_transfer_to_gen4"


@pytest.mark.skipif(not GEN3_SAVE.exists(), reason="save de Emerald nao disponivel")
def test_gen4_to_gen3_preserves_modern_iv_ev_values(tmp_path: Path):
    work = tmp_path / GEN3_SAVE.name
    shutil.copy2(GEN3_SAVE, work)
    parser = Gen3Parser()
    parser.load(work)
    canonical = _canonical_gen4_for_gen3()
    converter = get_converter(4, 3)

    report = converter.can_convert(canonical, policy="auto_retrocompat", target_game="pokemon_emerald")
    assert report.compatible
    converter.apply_to_save(parser, "party:0", canonical, policy="auto_retrocompat")

    exported = parser.export_canonical("party:0")
    assert exported.ivs.hp == 20
    assert exported.ivs.attack == 21
    assert exported.evs.hp == 10
    assert exported.evs.attack == 20


def test_gen4_learnsets_are_level_based_and_hm_filtered():
    replacements = get_level_up_replacements("pokemon_platinum", 448, 50, generation=4)
    assert replacements
    assert all(int(entry["learn_level"]) <= 50 for entry in replacements)
    assert is_hm_move_for_game("pokemon_platinum", 431, generation=4)
    assert all(int(entry["move_id"]) != 431 for entry in replacements)


def test_gen4_item_trade_evolutions_and_item_names():
    assert item_name(112, 4) == "Griseous Orb"
    assert item_category(112, 4) == "held_item"
    assert item_name(229, 4) == "Everstone"
    assert item_category(229, 4) == "held_item"
    assert item_name(322, 4) == "Electirizer"
    result = preview_trade_evolution(4, 125, 322)
    assert result.evolved
    assert result.target_species_id == 466
    assert result.consumed_item_name == "Electirizer"
    assert not preview_trade_evolution(4, 125, 221).evolved


def test_gen4_move_pp_uses_historical_generation_4_values():
    assert default_move_pp(74, 4) == 40  # Growth changed in later generations.
    assert default_move_pp(141, 4) == 15  # Leech Life changed in later generations.
    assert default_move_pp(200, 4) == 15  # Outrage changed in later generations.


@pytest.mark.skipif(
    not (TEST_SAVE.exists() and SOULSILVER_SAVE.exists()),
    reason="both Platinum and SoulSilver saves required"
)
def test_gen4_same_generation_roundtrip_between_saves(tmp_path: Path):
    src_work = tmp_path / TEST_SAVE.name
    tgt_work = tmp_path / SOULSILVER_SAVE.name
    shutil.copy2(TEST_SAVE, src_work)
    shutil.copy2(SOULSILVER_SAVE, tgt_work)

    src_parser = Gen4Parser()
    src_parser.load(src_work)

    canonical = _first_valid_party_canonical(src_parser)
    assert canonical is not None, "No valid party Pokémon in source save"

    tgt_parser = Gen4Parser()
    tgt_parser.load(tgt_work)
    tgt_parser.import_canonical("party:0", canonical)

    tgt_party = tgt_parser.list_party()
    assert tgt_party
    tgt_summary = tgt_party[0]

    assert tgt_summary.species_name == canonical.species_name
    assert tgt_summary.nickname == canonical.nickname
    assert tgt_summary.level == canonical.level
    assert tgt_summary.national_dex_id == canonical.species_national_id

    exported = tgt_parser.export_canonical("party:0")
    assert exported.species_name == canonical.species_name
    assert exported.nickname == canonical.nickname
    assert exported.level == canonical.level
    assert exported.species_national_id == canonical.species_national_id
    assert len(exported.moves) == len(canonical.moves)
    for i, (src_move, tgt_move) in enumerate(zip(canonical.moves, exported.moves)):
        assert src_move.move_id == tgt_move.move_id, f"Move {i} mismatch"
        assert src_move.pp == tgt_move.pp, f"Move {i} PP mismatch"


def _first_valid_party_canonical(parser: Gen4Parser):
    for summary in parser.list_party():
        try:
            canonical = parser.export_canonical(summary.location)
            if not canonical.metadata.get("is_egg"):
                return canonical
        except Exception:
            continue
    return None
