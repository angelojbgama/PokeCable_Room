"""Battery C: Unown form preservation Gen 2 ↔ Gen 3."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical import CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from converters.gen2_to_gen3 import Gen2ToGen3Converter  # noqa: E402
from converters.gen3_to_gen2 import Gen3ToGen2Converter  # noqa: E402
from data.unown_forms import gen2_unown_form_from_dvs, gen3_unown_form_from_personality  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402

from .report import BatteryReport  # noqa: E402

UNOWN_NATIONAL = 201
TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def _g2_canonical_with_dvs(atk: int, df: int, spd: int, spc: int) -> CanonicalPokemon:
    can = CanonicalPokemon(
        source_generation=2,
        source_game="pokemon_crystal",
        species_national_id=UNOWN_NATIONAL,
        species_name="Unown",
        nickname="UNOWN",
        level=20,
        ot_name="STRESS",
        trainer_id=0x1234,
        experience=8000,
        moves=[CanonicalMove(move_id=149, pp=15, max_pp=15, pp_ups=0, source_generation=2)],  # Hidden Power
        ivs=CanonicalStats(hp=((atk & 1) << 3) | ((df & 1) << 2) | ((spd & 1) << 1) | (spc & 1),
                            attack=atk, defense=df, speed=spd, special=spc, special_attack=spc, special_defense=spc),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={
            "unown_form": gen2_unown_form_from_dvs(atk, df, spd, spc),
            "is_shiny": False,
            "gender": None,
        },
        species=CanonicalSpecies(
            national_dex_id=UNOWN_NATIONAL,
            source_species_id=UNOWN_NATIONAL,
            source_species_id_space="national_dex",
            name="Unown",
        ),
    )
    return can


def _g3_canonical_with_pid(pid: int) -> CanonicalPokemon:
    can = CanonicalPokemon(
        source_generation=3,
        source_game="pokemon_emerald",
        species_national_id=UNOWN_NATIONAL,
        species_name="Unown",
        nickname="UNOWN",
        level=20,
        ot_name="STRESS",
        trainer_id=0x1234,
        experience=8000,
        moves=[CanonicalMove(move_id=149, pp=15, max_pp=15, pp_ups=0, source_generation=3)],
        ivs=CanonicalStats(hp=20, attack=20, defense=20, speed=20, special=20, special_attack=20, special_defense=20),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={
            "unown_form": gen3_unown_form_from_personality(pid),
            "is_shiny": False,
            "gender": None,
            "forced_pid": pid,
        },
        species=CanonicalSpecies(
            national_dex_id=UNOWN_NATIONAL,
            source_species_id=UNOWN_NATIONAL,
            source_species_id_space="gen3_internal",
            name="Unown",
        ),
    )
    return can


def _load_target_g3() -> Gen3Parser:
    p = Gen3Parser()
    p.load(TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav")
    return p


def _load_target_g2() -> Gen2Parser:
    p = Gen2Parser()
    p.load(TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav")
    return p


def run() -> BatteryReport:
    report = BatteryReport(name="C: Unown form preservation")

    # Gen 2 → Gen 3: pick DV patterns that map to distinct Gen 2 forms,
    # see if the resulting Gen 3 Unown matches the metadata form.
    g2g3 = Gen2ToGen3Converter()
    for atk, df, spd, spc in [(15, 15, 15, 15), (8, 4, 6, 2), (0, 0, 0, 0), (10, 6, 14, 8)]:
        src = _g2_canonical_with_dvs(atk, df, spd, spc)
        expected_form = src.metadata["unown_form"]
        tgt = _load_target_g3()
        res = g2g3.convert(src, tgt, "party:0", policy="auto_retrocompat")
        tgt.import_canonical("party:0", res.canonical_after)
        tgt_summary = tgt.list_party()[0]
        actual_form = getattr(tgt_summary, "unown_form", None)
        label = f"G2→G3 DVs=({atk},{df},{spd},{spc}) expect_form={expected_form}"
        if expected_form != actual_form:
            report.add_fail(f"{label} :: actual_form={actual_form!r}")
        else:
            report.add_pass()

    # Gen 3 → Gen 2: pick PIDs that map to distinct Gen 3 forms, see if Gen 2 result matches.
    g3g2 = Gen3ToGen2Converter()
    for pid in [0x00000000, 0x03030303, 0xAAAAAAAA, 0x12345678]:
        src = _g3_canonical_with_pid(pid)
        expected_form = src.metadata["unown_form"]
        tgt = _load_target_g2()
        res = g3g2.convert(src, tgt, "party:0", policy="auto_retrocompat")
        tgt.import_canonical("party:0", res.canonical_after)
        tgt_summary = tgt.list_party()[0]
        actual_form = getattr(tgt_summary, "unown_form", None)
        label = f"G3→G2 PID={pid:#010x} expect_form={expected_form}"
        if expected_form != actual_form:
            report.add_fail(f"{label} :: actual_form={actual_form!r}")
        else:
            report.add_pass()

    # Gen 3 -> Gen 2 -> Gen 3: PID exacto nao volta, mas a forma precisa permanecer identica.
    for pid in [0x00000000, 0x03030303, 0xAAAAAAAA, 0x12345678]:
        src = _g3_canonical_with_pid(pid)
        expected_form = src.metadata["unown_form"]

        mid_g2 = _load_target_g2()
        g3_to_g2 = g3g2.convert(src, mid_g2, "party:0", policy="auto_retrocompat")
        mid_g2.import_canonical("party:0", g3_to_g2.canonical_after)
        mid_canonical = mid_g2.export_canonical("party:0")

        final_g3 = _load_target_g3()
        g2_to_g3 = g2g3.convert(mid_canonical, final_g3, "party:0", policy="auto_retrocompat")
        final_g3.import_canonical("party:0", g2_to_g3.canonical_after)
        final_summary = final_g3.list_party()[0]
        final_form = getattr(final_summary, "unown_form", None)

        label = f"G3→G2→G3 PID={pid:#010x} expect_form={expected_form}"
        if expected_form != final_form:
            report.add_fail(f"{label} :: final_form={final_form!r}")
        else:
            report.add_pass()

    return report
