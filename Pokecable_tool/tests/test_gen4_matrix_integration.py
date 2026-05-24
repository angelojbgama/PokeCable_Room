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

from canonical import CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from compatibility import build_compatibility_report  # noqa: E402
from converters import get_converter  # noqa: E402
from data.growth_rates import experience_for_level, growth_rate_id_for_national  # noqa: E402
from data.items import item_category, item_exists, item_name  # noqa: E402
from data.learnsets import get_learnable_moves, get_level_up_replacements, is_hm_move_for_game  # noqa: E402
from data.moves import default_move_pp, move_exists, move_name  # noqa: E402
from data.species import SPECIES_NAMES_BY_NATIONAL, national_to_native, species_exists_in_generation  # noqa: E402
from parsers.gen4 import Gen4Parser  # noqa: E402
from pokecable_save import load_save  # noqa: E402
from save_curation import GEN4_SAVE_DIR, get_curated_gen4_saves  # noqa: E402


GENS = (1, 2, 3, 4)
GEN_LIMITS = {1: 151, 2: 251, 3: 386, 4: 493}
GAME_BY_GEN = {
    1: "pokemon_red",
    2: "pokemon_crystal",
    3: "pokemon_emerald",
    4: "pokemon_platinum",
}
SPECIES_SPACE_BY_GEN = {
    1: "gen1_internal",
    2: "national_dex",
    3: "gen3_internal",
    4: "gen4_native",
}
SAVE_BY_GEN = {
    1: REPO_ROOT.parent / "roms" / "test-saves" / "gen 1" / "Pokémon - Red Version.sav",
    2: REPO_ROOT.parent / "roms" / "test-saves" / "gen 2" / "Pokémon - Crystal Version.sav",
    3: REPO_ROOT.parent / "roms" / "test-saves" / "gen 3" / "Pokémon - Emerald Version.sav",
    4: REPO_ROOT.parent / "roms" / "test-saves" / "gen 4" / "Pokemon - Platinum Version (USA).sav",
}


class _TargetParserStub:
    def __init__(self, game_id: str) -> None:
        self._game_id = game_id

    def get_game_id(self) -> str:
        return self._game_id


def _experience_for_species_level(national_dex_id: int, level: int) -> int:
    growth_rate_id = growth_rate_id_for_national(national_dex_id)
    if growth_rate_id is None:
        return level * level * level
    return experience_for_level(growth_rate_id, level)


def _source_moves(generation: int, national_dex_id: int, level: int) -> list[CanonicalMove]:
    moves: list[CanonicalMove] = []
    for entry in get_level_up_replacements(GAME_BY_GEN[generation], national_dex_id, level, generation=generation):
        move_id = int(entry["move_id"])
        if not move_exists(move_id, generation):
            continue
        pp = default_move_pp(move_id, generation)
        moves.append(
            CanonicalMove(
                move_id=move_id,
                name=move_name(move_id),
                pp=pp,
                max_pp=pp,
                pp_ups=0,
                source_generation=generation,
            )
        )
        if len(moves) == 4:
            break
    if not moves:
        pp = default_move_pp(1, generation)
        moves.append(CanonicalMove(move_id=1, name=move_name(1), pp=pp, max_pp=pp, pp_ups=0, source_generation=generation))
    return moves


def _canonical_for(generation: int, national_dex_id: int, *, level: int = 50) -> CanonicalPokemon:
    species_name = SPECIES_NAMES_BY_NATIONAL[national_dex_id]
    native_id = national_to_native(generation, national_dex_id)
    if generation in {1, 2}:
        ivs = CanonicalStats(hp=15, attack=14, defense=13, speed=12, special=11)
        evs = CanonicalStats(hp=32000, attack=30000, defense=28000, speed=26000, special=24000)
        nature = None
        ability = None
    else:
        ivs = CanonicalStats(hp=31, attack=30, defense=29, speed=28, special_attack=27, special_defense=26)
        evs = CanonicalStats(hp=20, attack=30, defense=40, speed=50, special_attack=60, special_defense=70)
        nature = "Hardy"
        ability = "Index 1"
    return CanonicalPokemon(
        source_generation=generation,
        source_game=GAME_BY_GEN[generation],
        species_national_id=national_dex_id,
        species_name=species_name,
        nickname=species_name.upper()[:10],
        level=level,
        ot_name="TESTER",
        trainer_id=0x12345678 if generation >= 3 else 0x1234,
        experience=_experience_for_species_level(national_dex_id, level),
        moves=_source_moves(generation, national_dex_id, level),
        held_item=None,
        ivs=ivs,
        evs=evs,
        nature=nature,
        ability=ability,
        metadata={"gender": "♂", "source_species_id": native_id, "source_species_id_space": SPECIES_SPACE_BY_GEN[generation]},
        species=CanonicalSpecies(
            national_dex_id=national_dex_id,
            source_species_id=native_id,
            source_species_id_space=SPECIES_SPACE_BY_GEN[generation],
            name=species_name,
        ),
    )


def _payload_for(canonical: CanonicalPokemon) -> dict[str, object]:
    moves = [move.to_dict() for move in canonical.moves]
    return {
        "generation": canonical.source_generation,
        "source_generation": canonical.source_generation,
        "source_game": canonical.source_game,
        "species_id": canonical.species.source_species_id if canonical.species else canonical.species_national_id,
        "national_dex_id": canonical.species_national_id,
        "species_name": canonical.species_name,
        "level": canonical.level,
        "nickname": canonical.nickname,
        "ot_name": canonical.ot_name,
        "trainer_id": canonical.trainer_id,
        "experience": canonical.experience,
        "moves": moves,
        "summary": {
            "national_dex_id": canonical.species_national_id,
            "species_name": canonical.species_name,
            "level": canonical.level,
            "nickname": canonical.nickname,
            "moves": [move.move_id for move in canonical.moves],
            "move_names": [move.name for move in canonical.moves],
        },
        "canonical": canonical.to_dict(),
    }


def _exported_national_id(payload: dict[str, object]) -> int:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    canonical = payload.get("canonical") if isinstance(payload.get("canonical"), dict) else {}
    species = canonical.get("species") if isinstance(canonical.get("species"), dict) else {}
    return int(
        summary.get("national_dex_id")
        or canonical.get("species_national_id")
        or species.get("national_dex_id")
        or payload.get("national_dex_id")
        or payload.get("species_id")
    )


def test_flat_learnsets_cover_every_species_through_gen4():
    missing: list[tuple[int, int]] = []
    for generation in GENS:
        for national_dex_id in range(1, GEN_LIMITS[generation] + 1):
            if not species_exists_in_generation(national_dex_id, generation):
                continue
            if not get_learnable_moves(generation, national_dex_id):
                missing.append((generation, national_dex_id))

    assert missing == []


def test_level_up_replacements_are_level_limited_and_hm_filtered_for_all_species():
    failures: list[tuple[int, int, int, str]] = []
    for generation in GENS:
        game = GAME_BY_GEN[generation]
        for national_dex_id in range(1, GEN_LIMITS[generation] + 1):
            if not species_exists_in_generation(national_dex_id, generation):
                continue
            for entry in get_level_up_replacements(game, national_dex_id, 50, generation=generation):
                move_id = int(entry["move_id"])
                learn_level = int(entry.get("learn_level") or 1)
                if learn_level > 50:
                    failures.append((generation, national_dex_id, move_id, "above-level"))
                if is_hm_move_for_game(game, move_id, generation=generation):
                    failures.append((generation, national_dex_id, move_id, "hm"))
                if not move_exists(move_id, generation):
                    failures.append((generation, national_dex_id, move_id, "missing-move"))

    assert failures == []


def test_cross_generation_reports_cover_every_species_and_pair():
    failures: list[tuple[int, int, int, str]] = []
    for source_generation in GENS:
        for target_generation in GENS:
            if source_generation == target_generation:
                continue
            for national_dex_id in range(1, GEN_LIMITS[source_generation] + 1):
                if not species_exists_in_generation(national_dex_id, source_generation):
                    continue
                canonical = _canonical_for(source_generation, national_dex_id)
                report = build_compatibility_report(
                    canonical,
                    target_generation,
                    policy="auto_retrocompat",
                    target_game=GAME_BY_GEN[target_generation],
                )
                target_has_species = species_exists_in_generation(national_dex_id, target_generation)
                if not target_has_species:
                    if report.compatible:
                        failures.append((source_generation, target_generation, national_dex_id, "missing-target-species-compatible"))
                    continue
                if not report.compatible:
                    failures.append((source_generation, target_generation, national_dex_id, "; ".join(report.blocking_reasons)))
                    continue
                if report.normalized_species.get("target_species_id") != national_to_native(target_generation, national_dex_id):
                    failures.append((source_generation, target_generation, national_dex_id, "bad-target-species-id"))
                for removed_move in report.removed_moves:
                    replacements = removed_move.get("valid_replacements") or []
                    if not replacements:
                        failures.append((source_generation, target_generation, national_dex_id, "removed-move-without-replacement"))
                    for option in replacements:
                        replacement_id = int(option.get("move_id") or 0)
                        if not move_exists(replacement_id, target_generation):
                            failures.append((source_generation, target_generation, national_dex_id, "replacement-missing-target"))
                        if is_hm_move_for_game(GAME_BY_GEN[target_generation], replacement_id, generation=target_generation):
                            failures.append((source_generation, target_generation, national_dex_id, "replacement-is-hm"))

    assert failures[:20] == []


def test_converters_normalize_every_common_species_across_generation_pairs():
    failures: list[tuple[int, int, int, str]] = []
    for source_generation in GENS:
        for target_generation in GENS:
            if source_generation == target_generation:
                continue
            converter = get_converter(source_generation, target_generation)
            target_parser = _TargetParserStub(GAME_BY_GEN[target_generation])
            for national_dex_id in range(1, GEN_LIMITS[source_generation] + 1):
                if not species_exists_in_generation(national_dex_id, source_generation):
                    continue
                if not species_exists_in_generation(national_dex_id, target_generation):
                    continue
                canonical = _canonical_for(source_generation, national_dex_id)
                result = converter.convert(canonical, target_parser, "party:0", policy="auto_retrocompat")
                report = result.compatibility_report
                if not report.compatible:
                    failures.append((source_generation, target_generation, national_dex_id, "; ".join(report.blocking_reasons)))
                    continue
                target_species = result.canonical_after.species.target_species_id if result.canonical_after.species else None
                if target_species != national_to_native(target_generation, national_dex_id):
                    failures.append((source_generation, target_generation, national_dex_id, "bad-converted-target-species"))
                for move in result.canonical_after.moves:
                    if not move_exists(move.move_id, target_generation):
                        failures.append((source_generation, target_generation, national_dex_id, f"bad-move-{move.move_id}"))

    assert failures[:20] == []


@pytest.mark.skipif(not all(path.exists() for path in SAVE_BY_GEN.values()), reason="saves de teste 1-4 nao disponiveis")
def test_save_model_payload_writes_all_cross_generation_routes(tmp_path: Path):
    failures: list[tuple[int, int, str]] = []
    for source_generation in GENS:
        payload = _payload_for(_canonical_for(source_generation, 1, level=12))
        for target_generation in GENS:
            if source_generation == target_generation:
                continue
            target_save = SAVE_BY_GEN[target_generation]
            work = tmp_path / f"gen{source_generation}_to_gen{target_generation}_{target_save.name}"
            shutil.copy2(target_save, work)
            try:
                save = load_save(work)
                result = save.apply_payload("party:0", payload)
                save.write_to_disk()
                reloaded = load_save(work)
                exported = reloaded.export_payload("party:0")
            except Exception as exc:  # pragma: no cover - assertion reports route details
                failures.append((source_generation, target_generation, str(exc)))
                continue
            if _exported_national_id(exported) != 1:
                failures.append((source_generation, target_generation, f"wrong species: {result}"))
            if int(exported.get("generation") or 0) != target_generation:
                failures.append((source_generation, target_generation, "wrong exported generation"))
            canonical = exported.get("canonical") if isinstance(exported.get("canonical"), dict) else {}
            if int(canonical.get("source_generation") or 0) != target_generation:
                failures.append((source_generation, target_generation, "wrong canonical source generation after write"))
            for move in canonical.get("moves") or []:
                name = str(move.get("name") or "")
                if not name or name.startswith("Move #"):
                    failures.append((source_generation, target_generation, f"bad move display: {move}"))
                if int(move.get("pp") or 0) > int(move.get("max_pp") or 0):
                    failures.append((source_generation, target_generation, f"bad pp: {move}"))

    assert failures == []


@pytest.mark.skipif(not GEN4_SAVE_DIR.exists(), reason="pasta de saves Gen4 nao disponivel")
def test_gen4_real_saves_do_not_show_unknown_item_or_move_fallbacks():
    saves = get_curated_gen4_saves()
    assert saves
    failures: list[tuple[str, str, str, int | None, str]] = []

    for save_path in saves:
        parser = Gen4Parser()
        if not parser.detect(save_path):
            continue
        parser.load(save_path)
        for entry in parser.list_inventory():
            name = str(entry.item_name or "")
            if "?" in name or name.startswith("Item #"):
                failures.append((save_path.name, entry.storage, entry.pocket_name or "", entry.item_id, name))
        for summary in parser.list_party() + parser.list_boxes():
            item = str(summary.held_item_name or "")
            if item and ("?" in item or item.startswith("Item #")):
                failures.append((save_path.name, summary.location, "held_item", summary.held_item_id, item))
            canonical = parser.export_canonical(summary.location)
            for move in canonical.moves:
                name = str(move.name or "")
                if not name or name.startswith("Move #"):
                    failures.append((save_path.name, summary.location, "move", move.move_id, name))
                if int(move.pp or 0) > int(move.max_pp or 0):
                    failures.append((save_path.name, summary.location, "pp", move.move_id, f"{move.pp}/{move.max_pp}"))

    assert failures == []


def test_gen4_unused_item_slots_are_visible_but_not_compatible_items():
    assert item_name(112, 4) == "Griseous Orb"
    assert item_exists(112, 4)
    assert item_category(112, 4) == "held_item"
    assert item_name(117, 4) == "Unused Item #117"
    assert item_category(117, 4) == "unused"
    assert not item_exists(117, 4)
