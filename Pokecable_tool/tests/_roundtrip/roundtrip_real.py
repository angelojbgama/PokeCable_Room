"""Battery B: real save roundtrip — src.export_canonical → convert → tgt.import_canonical → list_party → verify."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402
from converters.gen1_to_gen2 import Gen1ToGen2Converter  # noqa: E402
from converters.gen1_to_gen3 import Gen1ToGen3Converter  # noqa: E402
from converters.gen2_to_gen1 import Gen2ToGen1Converter  # noqa: E402
from converters.gen2_to_gen3 import Gen2ToGen3Converter  # noqa: E402
from converters.gen3_to_gen1 import Gen3ToGen1Converter  # noqa: E402
from converters.gen3_to_gen2 import Gen3ToGen2Converter  # noqa: E402
from data.items import equivalent_item_id  # noqa: E402
from data.species import species_exists_in_generation  # noqa: E402

from .report import BatteryReport  # noqa: E402

PARSER_BY_GEN = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser}
CONVERTERS = {
    (1, 2): Gen1ToGen2Converter,
    (1, 3): Gen1ToGen3Converter,
    (2, 1): Gen2ToGen1Converter,
    (2, 3): Gen2ToGen3Converter,
    (3, 1): Gen3ToGen1Converter,
    (3, 2): Gen3ToGen2Converter,
}

TARGET_SAVES = {
    1: "Pokémon - Red Version.sav",
    2: "Pokémon - Crystal Version.sav",
    3: "Pokémon - Emerald Version.sav",
}
TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"
GEN_DIR = {1: "gen 1", 2: "gen 2", 3: "gen 3"}


def _fresh(gen: int, path: Path):
    p = PARSER_BY_GEN[gen]()
    p.load(path)
    return p


def _target_path(gen: int) -> Path:
    return TEST_SAVES_ROOT / GEN_DIR[gen] / TARGET_SAVES[gen]


def _verify(report: BatteryReport, label: str, src_can, tgt_summary, target_gen: int, source_held_item: int | None) -> None:
    # Species (national or native depending on gen)
    expected_national = src_can.species_national_id
    if not species_exists_in_generation(expected_national, target_gen):
        # Should never happen here because we filter — defensive
        report.add_fail(f"{label}: species {expected_national} not in target gen {target_gen}")
        return
    if target_gen == 2:
        expected_species = expected_national  # gen 2 species_id == national_dex_id
        actual_species = tgt_summary.species_id
    else:
        # gen 1 native id and gen 3 native id read straight from PokemonSummary
        actual_species = tgt_summary.species_id
        # We don't compare native id directly — easier to compare national via summary.national_dex_id
        actual_national = getattr(tgt_summary, "national_dex_id", None)
        if actual_national is not None and actual_national != expected_national:
            report.add_fail(f"{label}: national_dex mismatch expected={expected_national} actual={actual_national}")
            return
    # Level
    expected_level = max(1, min(100, int(src_can.level)))
    if tgt_summary.level != expected_level:
        report.add_fail(f"{label}: level mismatch expected={expected_level} actual={tgt_summary.level}")
        return
    # TID (low 16)
    expected_tid = int(src_can.trainer_id) & 0xFFFF
    actual_tid = int(tgt_summary.trainer_id) & 0xFFFF
    if expected_tid != actual_tid:
        report.add_fail(f"{label}: trainer_id mismatch expected={expected_tid} actual={actual_tid}")
        return
    # Held item — only if target supports
    if target_gen == 1:
        if getattr(tgt_summary, "held_item_id", None):
            report.add_fail(f"{label}: gen1 target should not carry held_item, got {tgt_summary.held_item_id}")
            return
    else:
        expected_item = 0
        if source_held_item:
            expected_item = equivalent_item_id(source_held_item, int(src_can.source_generation), target_gen) or 0
        actual_item = getattr(tgt_summary, "held_item_id", None) or 0
        if expected_item != actual_item:
            report.add_fail(f"{label}: held_item mismatch expected={expected_item} actual={actual_item}")
            return
    report.add_pass()


def run(valid_saves: dict[int, list[Path]]) -> BatteryReport:
    report = BatteryReport(name="B: real-save roundtrip")
    for (src_gen, tgt_gen), conv_cls in CONVERTERS.items():
        if not valid_saves.get(src_gen):
            continue
        target_path = _target_path(tgt_gen)
        if not target_path.exists():
            report.add_fail(f"{src_gen}→{tgt_gen}: target save missing ({target_path})")
            continue
        for src_path in valid_saves[src_gen]:
            label = f"{src_gen}→{tgt_gen} :: {src_path.name}"
            try:
                src_parser = _fresh(src_gen, src_path)
                src_can = src_parser.export_canonical("party:0")
            except Exception as exc:
                report.add_fail(f"{label}: export_canonical raised {type(exc).__name__}: {exc}")
                continue
            if not species_exists_in_generation(src_can.species_national_id, tgt_gen):
                continue  # legitimately incompatible, skip
            try:
                tgt_parser = _fresh(tgt_gen, target_path)
                conv = conv_cls()
                result = conv.convert(src_can, tgt_parser, "party:0", policy="auto_retrocompat")
                if not result.compatibility_report.compatible:
                    report.add_fail(f"{label}: auto_retrocompat blocked: {result.compatibility_report.blocking_reasons}")
                    continue
                tgt_parser.import_canonical("party:0", result.canonical_after)
            except Exception as exc:
                report.add_fail(f"{label}: convert/import raised {type(exc).__name__}: {exc}")
                continue
            try:
                tgt_party = tgt_parser.list_party()
            except Exception as exc:
                report.add_fail(f"{label}: list_party post-import raised {type(exc).__name__}: {exc}")
                continue
            if not tgt_party:
                report.add_fail(f"{label}: list_party empty after import")
                continue
            src_held = src_can.held_item.item_id if src_can.held_item else None
            _verify(report, label, src_can, tgt_party[0], tgt_gen, src_held)
    return report
