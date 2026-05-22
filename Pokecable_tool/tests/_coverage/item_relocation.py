"""Battery U: when a held item won't survive the transfer, it must go to bag → PC → discard."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical import CanonicalItem, CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from converters.gen2_to_gen1 import Gen2ToGen1Converter  # noqa: E402
from converters.gen3_to_gen1 import Gen3ToGen1Converter  # noqa: E402
from converters.gen3_to_gen2 import Gen3ToGen2Converter  # noqa: E402
from data.items import item_name  # noqa: E402
from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def _can(src_gen: int, item_id: int, item_name_: str) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=src_gen,
        source_game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[src_gen],
        species_national_id=1, species_name="Bulbasaur",
        nickname="BULBA", level=20, ot_name="STRESS", trainer_id=0x1234, experience=8000,
        moves=[CanonicalMove(move_id=33, pp=20, max_pp=20, pp_ups=0, source_generation=src_gen)],
        ivs=CanonicalStats(hp=10, attack=10, defense=10, speed=10, special=10, special_attack=10, special_defense=10),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={"is_shiny": False, "gender": "♂"},
        species=CanonicalSpecies(
            national_dex_id=1, source_species_id=1,
            source_species_id_space={1: "gen1_internal", 2: "national_dex", 3: "gen3_internal"}[src_gen],
            name="Bulbasaur",
        ),
        held_item=CanonicalItem(item_id=item_id, name=item_name_, source_generation=src_gen),
    )


def run() -> BatteryReport:
    report = BatteryReport(name="U: item relocation on cross-gen transfer")

    # --- Case 1: Gen 2 Potion → Gen 1 (Gen 1 has no held items at all). Item must go to bag. ---
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "yellow.sav"
        shutil.copy(TEST_SAVES_ROOT / "gen 1" / "Pokémon - Yellow Version.sav", work)
        target = Gen1Parser(); target.load(work)
        before = sum(e.quantity for e in target.list_inventory() if e.item_id == 20)
        can = _can(2, 18, "Potion")  # Gen 2 Potion #18 → Gen 1 Potion #20
        result = Gen2ToGen1Converter().convert(can, target, "party:0", policy="auto_retrocompat")
        after = sum(e.quantity for e in target.list_inventory() if e.item_id == 20)
        if after == before + 1:
            report.add_pass()
            report.note(f"Gen 2 Potion → Gen 1 bag (delta +1, transformations: {result.transformations})")
        else:
            report.add_fail(f"Gen 2 Potion → Gen 1: bag count {before} → {after} (expected +1)")

    # --- Case 2: Gen 3 King's Rock → Gen 1 (King's Rock doesn't exist in Gen 1).
    # Trade must be REFUSED so item isn't lost. ---
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "red.sav"
        shutil.copy(TEST_SAVES_ROOT / "gen 1" / "Pokémon - Red Version.sav", work)
        target = Gen1Parser(); target.load(work)
        can = _can(3, 187, "King's Rock")
        result = Gen3ToGen1Converter().convert(can, target, "party:0", policy="auto_retrocompat")
        report_obj = result.compatibility_report
        if not report_obj.compatible and any("nao existe" in r.lower() for r in report_obj.blocking_reasons):
            report.add_pass()
            report.note(f"Gen 3 King's Rock → Gen 1: trade REFUSED (item has no Gen 1 equivalent)")
        else:
            report.add_fail(
                f"Gen 3 King's Rock → Gen 1: expected refused trade, got compatible={report_obj.compatible} "
                f"reasons={report_obj.blocking_reasons}"
            )

    # --- Case 3: Gen 3 Potion → Gen 2 (Potion exists in both, mapped to #18). Item should
    # stay ON the pokemon (no relocation needed). ---
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "crystal.sav"
        shutil.copy(TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav", work)
        target = Gen2Parser(); target.load(work)
        can = _can(3, 13, "Potion")  # Gen 3 Potion #13 → Gen 2 #18
        result = Gen3ToGen2Converter().convert(can, target, "party:0", policy="auto_retrocompat")
        target.import_canonical("party:0", result.canonical_after)
        summary = target.list_party()[0]
        if summary.held_item_id == 18:
            report.add_pass()
            report.note(f"Gen 3 Potion → Gen 2: item stayed on pokemon as #18")
        else:
            report.add_fail(f"Gen 3 Potion → Gen 2: expected mon to hold #18, got {summary.held_item_id}")

    # --- Case 4: Gen 3 Soothe Bell → Gen 2 (no Gen 2 equivalent). Trade must be REFUSED. ---
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "crystal2.sav"
        shutil.copy(TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav", work)
        target = Gen2Parser(); target.load(work)
        can = _can(3, 132, "Soothe Bell")
        result = Gen3ToGen2Converter().convert(can, target, "party:0", policy="auto_retrocompat")
        report_obj = result.compatibility_report
        if not report_obj.compatible and any("nao existe" in r.lower() for r in report_obj.blocking_reasons):
            report.add_pass()
            report.note(f"Gen 3 Soothe Bell → Gen 2: trade REFUSED (item has no Gen 2 equivalent)")
        else:
            report.add_fail(
                f"Gen 3 Soothe Bell → Gen 2: expected refused trade, got compatible={report_obj.compatible} "
                f"reasons={report_obj.blocking_reasons}"
            )

    return report
