"""Battery K: eggs negative-test — converters must refuse, never silently corrupt."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical import CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from converters.gen1_to_gen2 import Gen1ToGen2Converter  # noqa: E402
from converters.gen2_to_gen1 import Gen2ToGen1Converter  # noqa: E402
from converters.gen2_to_gen3 import Gen2ToGen3Converter  # noqa: E402
from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def _egg_canonical(src_gen: int) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=src_gen,
        source_game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[src_gen],
        species_national_id=1,  # Bulbasaur shell
        species_name="Egg",
        nickname="EGG",
        level=5,
        ot_name="STRESS",
        trainer_id=0x4242,
        experience=200,
        moves=[CanonicalMove(move_id=1, pp=20, max_pp=20, pp_ups=0, source_generation=src_gen)],
        ivs=CanonicalStats(hp=8, attack=8, defense=8, speed=8, special=8, special_attack=8, special_defense=8),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={"is_egg": True, "is_shiny": False, "gender": None},
        species=CanonicalSpecies(
            national_dex_id=1, source_species_id=1, source_species_id_space="national_dex", name="Egg",
        ),
    )


def _load(parser_cls, fname):
    p = parser_cls()
    p.load(TEST_SAVES_ROOT / fname)
    return p


def run() -> BatteryReport:
    report = BatteryReport(name="K: eggs negative-test")

    # Gen 1 import must refuse eggs (validate_can_write raises)
    egg = _egg_canonical(2)
    g1 = _load(Gen1Parser, "gen 1/Pokémon - Red Version.sav")
    try:
        result = Gen2ToGen1Converter().convert(egg, g1, "party:0", policy="auto_retrocompat")
        if result.compatibility_report.compatible:
            report.add_fail("Gen 2 egg → Gen 1: report.compatible=True, expected False")
        else:
            report.add_pass()
    except Exception as exc:
        # Raising is also acceptable behavior
        if "egg" in str(exc).lower() or "Egg" in str(exc):
            report.add_pass()
        else:
            report.add_fail(f"Gen 2 egg → Gen 1: unexpected exception {type(exc).__name__}: {exc}")

    # Gen 2 → Gen 3 egg: report should block
    egg2 = _egg_canonical(2)
    g3 = _load(Gen3Parser, "gen 3/Pokémon - Emerald Version.sav")
    rep = Gen2ToGen3Converter().can_convert(egg2, policy="auto_retrocompat")
    if rep.compatible:
        report.add_fail("Gen 2 egg → Gen 3: report.compatible=True, expected False")
    else:
        report.add_pass()

    # Gen 1 → Gen 2 with synthetic egg metadata (Gen 1 doesn't have egg byte, but metadata claim is one).
    egg1 = _egg_canonical(1)
    g2 = _load(Gen2Parser, "gen 2/Pokémon - Crystal Version.sav")
    rep = Gen1ToGen2Converter().can_convert(egg1, policy="auto_retrocompat")
    if rep.compatible:
        report.add_fail("Gen 1 egg → Gen 2: report.compatible=True, expected False")
    else:
        report.add_pass()

    return report
