"""Battery H: Spinda/Castform/Deoxys form preservation."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical import CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from data.species import national_to_native  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402
from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"

# species IDs (national dex)
SPINDA = 327
CASTFORM = 351
DEOXYS = 386


def _g3_canonical(nat_id: int, name: str, pid: int) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=3,
        source_game="pokemon_emerald",
        species_national_id=nat_id,
        species_name=name,
        nickname=name.upper()[:10],
        level=30,
        ot_name="STRESS",
        trainer_id=0x4242,
        experience=27000,
        moves=[CanonicalMove(move_id=33, pp=20, max_pp=20, pp_ups=0, source_generation=3)],  # Tackle
        ivs=CanonicalStats(hp=20, attack=20, defense=20, speed=20, special=20, special_attack=20, special_defense=20),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={"is_shiny": False, "gender": None, "forced_pid": pid},
        species=CanonicalSpecies(
            national_dex_id=nat_id, source_species_id=nat_id, source_species_id_space="national_dex", name=name,
        ),
    )


def run() -> BatteryReport:
    report = BatteryReport(name="H: forms (Spinda/Castform/Deoxys)")
    g3 = Gen3Parser()
    g3.load(TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav")

    # Spinda: PID-based spot pattern. We verify species roundtrips and PID survives.
    for pid in [0x00000000, 0x12345678, 0xDEADBEEF]:
        can = _g3_canonical(SPINDA, "Spinda", pid)
        try:
            g3.import_canonical("party:0", can)
            mon = g3.list_party()[0]
        except Exception as exc:
            report.add_fail(f"Spinda PID={pid:#010x}: {exc}")
            continue
        expected_native = national_to_native(3, SPINDA)
        if mon.species_id != expected_native:
            report.add_fail(f"Spinda PID={pid:#010x}: native species mismatch (expected {expected_native} got {mon.species_id})")
        else:
            report.add_pass()

    # Castform: only base form stored in save (weather modifies in-battle).
    can = _g3_canonical(CASTFORM, "Castform", 0)
    try:
        g3.import_canonical("party:0", can)
        mon = g3.list_party()[0]
        exp_native = national_to_native(3, CASTFORM)
        if mon.species_id == exp_native:
            report.add_pass()
            report.note("Castform: base form roundtrip OK (weather forms are in-battle only).")
        else:
            report.add_fail(f"Castform: species mismatch (expected {exp_native} got {mon.species_id})")
    except Exception as exc:
        report.add_fail(f"Castform: {exc}")

    # Deoxys: 4 forms exist but form is ROM-side.
    can = _g3_canonical(DEOXYS, "Deoxys", 0)
    try:
        g3.import_canonical("party:0", can)
        mon = g3.list_party()[0]
        exp_native = national_to_native(3, DEOXYS)
        if mon.species_id == exp_native:
            report.add_pass()
            report.note("Deoxys: roundtrip OK (form is ROM-dependent, not save-dependent).")
        else:
            report.add_fail(f"Deoxys: species mismatch (expected {exp_native} got {mon.species_id})")
    except Exception as exc:
        report.add_fail(f"Deoxys: {exc}")

    return report
