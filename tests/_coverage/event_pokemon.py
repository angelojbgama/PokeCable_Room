"""Battery J: event Pokémon + fateful_encounter flag (Gen 3)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical import CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402
from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"
EVENT_SPECIES = [
    (151, "Mew"),
    (251, "Celebi"),
    (385, "Jirachi"),
    (386, "Deoxys"),
]


def _can(nat: int, name: str) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=3, source_game="pokemon_emerald",
        species_national_id=nat, species_name=name,
        nickname=name.upper()[:10], level=50,
        ot_name="STRESS", trainer_id=0xABCD,
        experience=125000,
        moves=[CanonicalMove(move_id=33, pp=20, max_pp=20, pp_ups=0, source_generation=3)],
        ivs=CanonicalStats(hp=25, attack=25, defense=25, speed=25, special=25, special_attack=25, special_defense=25),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={"is_shiny": False, "gender": None, "fateful_encounter": True},
        species=CanonicalSpecies(national_dex_id=nat, source_species_id=nat,
                                 source_species_id_space="national_dex", name=name),
    )


def run() -> BatteryReport:
    report = BatteryReport(name="J: event Pokémon + fateful_encounter")
    g3 = Gen3Parser()
    g3.load(TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav")
    for nat, name in EVENT_SPECIES:
        try:
            can = _can(nat, name)
            g3.import_canonical("party:0", can)
            mon = g3.list_party()[0]
        except Exception as exc:
            report.add_fail(f"{name}: import raised {exc}")
            continue
        # Roundtrip: read back as canonical and confirm fateful_encounter survived.
        try:
            roundtrip = g3.export_canonical("party:0")
        except Exception as exc:
            report.add_fail(f"{name}: re-export raised {exc}")
            continue
        if not roundtrip.metadata.get("fateful_encounter"):
            # KNOWN GAP: fateful_encounter not currently parsed/written by gen3 parser.
            report.add_fail(
                f"{name}: fateful_encounter not preserved (gap — parser doesn't read/write the bit)"
            )
        else:
            report.add_pass()
    return report
