"""Battery L: malformed/glitched inputs — system must reject gracefully, never crash silently."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical import CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from converters.gen2_to_gen3 import Gen2ToGen3Converter  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def _glitched_canonical(species_id: int, level: int) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=2,
        source_game="pokemon_crystal",
        species_national_id=species_id,
        species_name=f"Glitch{species_id}",
        nickname="GLITCH",
        level=level,
        ot_name="STRESS",
        trainer_id=0xDEAD,
        experience=0,
        moves=[CanonicalMove(move_id=1, pp=1, max_pp=1, pp_ups=0, source_generation=2)],
        ivs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={"is_shiny": False, "gender": None},
        species=CanonicalSpecies(
            national_dex_id=species_id,
            source_species_id=species_id,
            source_species_id_space="national_dex",
            name=f"Glitch{species_id}",
        ),
    )


def run() -> BatteryReport:
    report = BatteryReport(name="L: glitched inputs")
    target = Gen3Parser()
    target.load(TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav")
    conv = Gen2ToGen3Converter()

    cases = [
        # (species_id, level, label, must_be_blocked)
        (0, 5, "species_id=0", True),
        (1000, 5, "species_id=1000 (over range)", True),
        (252, 5, "species_id=252 (only in Gen 3)", True),  # Treecko not in Gen 2 source
        # Levels outside range are silently clamped (1..100) — that's acceptable defensive behavior.
        (1, 0, "level=0", False),
        (1, 101, "level=101 (over cap)", False),
        (1, 255, "level=255 (byte overflow)", False),
    ]
    for sid, lvl, label, must_block in cases:
        can = _glitched_canonical(sid, lvl)
        try:
            rep = conv.can_convert(can, policy="auto_retrocompat")
        except Exception as exc:
            # Raise is also acceptable rejection
            report.add_pass()
            report.note(f"{label}: raised {type(exc).__name__} (acceptable)")
            continue
        if must_block and rep.compatible:
            report.add_fail(f"{label}: must be blocked but compatible=True")
        else:
            # Attempt to convert; should either work (clamped) or block cleanly
            try:
                if rep.compatible:
                    result = conv.convert(can, target, "party:0", policy="auto_retrocompat")
                    if result.compatibility_report.compatible:
                        # Attempt build to make sure no crash
                        target.build_party_mon_from_canonical(result.canonical_after)
                report.add_pass()
            except Exception as exc:
                if must_block:
                    report.add_pass()
                    report.note(f"{label}: build raised {type(exc).__name__} (acceptable for invalid input)")
                else:
                    report.add_fail(f"{label}: unexpected crash {type(exc).__name__}: {exc}")
    return report
