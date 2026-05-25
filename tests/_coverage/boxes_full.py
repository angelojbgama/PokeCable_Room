"""Battery F: exhaustive roundtrip of EVERY box slot (not just party:0)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from data.species import species_exists_in_generation  # noqa: E402
from converters.gen1_to_gen2 import Gen1ToGen2Converter  # noqa: E402
from converters.gen1_to_gen3 import Gen1ToGen3Converter  # noqa: E402
from converters.gen2_to_gen1 import Gen2ToGen1Converter  # noqa: E402
from converters.gen2_to_gen3 import Gen2ToGen3Converter  # noqa: E402
from converters.gen3_to_gen1 import Gen3ToGen1Converter  # noqa: E402
from converters.gen3_to_gen2 import Gen3ToGen2Converter  # noqa: E402
from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

PARSER_BY_GEN = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser}
CONVERTERS = {
    (1, 2): Gen1ToGen2Converter,
    (1, 3): Gen1ToGen3Converter,
    (2, 1): Gen2ToGen1Converter,
    (2, 3): Gen2ToGen3Converter,
    (3, 1): Gen3ToGen1Converter,
    (3, 2): Gen3ToGen2Converter,
}
TARGET_SAVE = {
    1: "Pokémon - Red Version.sav",
    2: "Pokémon - Crystal Version.sav",
    3: "Pokémon - Emerald Version.sav",
}

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"
GEN_DIR = {1: "gen 1", 2: "gen 2", 3: "gen 3"}


def _fresh(gen, path):
    p = PARSER_BY_GEN[gen]()
    p.load(path)
    return p


def run() -> BatteryReport:
    """For each save, probe whether export_canonical accepts box:N:M and roundtrip if so.

    Currently Gen 2 and Gen 3 parsers raise on box:* — this battery surfaces that gap
    and counts each per-save probe as 1 pass when supported / 1 known-failure when not.
    """
    report = BatteryReport(name="F: boxes export+roundtrip")
    KNOWN_GAP = "feature pending: export_canonical('box:N:M') not implemented in this parser"
    for src_gen in (2, 3):
        src_folder = TEST_SAVES_ROOT / GEN_DIR[src_gen]
        if not src_folder.exists():
            continue
        for src_path in sorted(src_folder.glob("*.sav")):
            try:
                src = _fresh(src_gen, src_path)
                boxes = src.list_boxes()
            except Exception as exc:
                # Corrupted saves (Ruby missing PC sections, Sapphire bad checksums) — skip cleanly.
                report.note(f"skip gen{src_gen} {src_path.name}: {exc}")
                continue
            if not boxes:
                report.note(f"gen{src_gen} {src_path.name}: empty boxes (skipped)")
                continue
            # Probe export support on the FIRST non-empty box slot
            sample_loc = next((m.location for m in boxes if int(m.species_id) > 0), None)
            if not sample_loc:
                report.note(f"gen{src_gen} {src_path.name}: all box slots empty")
                continue
            try:
                src.export_canonical(sample_loc)
            except Exception as exc:
                if "party:N" in str(exc) or "box" in str(exc).lower():
                    report.add_fail(f"gen{src_gen} {src_path.name}: {KNOWN_GAP} ({sample_loc})")
                    continue
                report.add_fail(f"gen{src_gen} {src_path.name}: unexpected error on {sample_loc}: {exc}")
                continue
            # If we reach here, export of box works. Run all routes × all box slots.
            for tgt_gen in (1, 2, 3):
                if tgt_gen == src_gen:
                    continue
                conv_cls = CONVERTERS.get((src_gen, tgt_gen))
                if not conv_cls:
                    continue
                target_path = TEST_SAVES_ROOT / GEN_DIR[tgt_gen] / TARGET_SAVE[tgt_gen]
                for mon in boxes:
                    if int(mon.species_id) <= 0:
                        continue
                    if not species_exists_in_generation(int(mon.species_id), tgt_gen):
                        continue
                    can = src.export_canonical(mon.location)
                    tgt = _fresh(tgt_gen, target_path)
                    try:
                        result = conv_cls().convert(can, tgt, "party:0", policy="auto_retrocompat")
                        if not result.compatibility_report.compatible:
                            continue
                        tgt.import_canonical("party:0", result.canonical_after)
                        tgt_summary = tgt.list_party()[0]
                    except Exception as exc:
                        report.add_fail(f"{src_path.name} {mon.location} → gen{tgt_gen}: {exc}")
                        continue
                    if tgt_summary.level != max(1, min(100, can.level)):
                        report.add_fail(f"{src_path.name} {mon.location} → gen{tgt_gen}: level mismatch")
                        continue
                    report.add_pass()
    return report
