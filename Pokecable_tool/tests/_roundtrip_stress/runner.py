"""Round-trip stress: for each pair (gen_src ↔ gen_inter), iterate all species/scenarios.

Pipeline per case:
  1. Synthesize canonical at gen_src (using existing scenario factories).
  2. Convert + import into gen_inter parser → read back as canonical_after_forward.
  3. Convert + import back into gen_src parser → read as canonical_after_roundtrip.
  4. Compare canonical_before vs canonical_after_roundtrip and classify diffs.

Outputs per-route counts and detailed first N failures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from converters.gen1_to_gen2 import Gen1ToGen2Converter
from converters.gen1_to_gen3 import Gen1ToGen3Converter
from converters.gen2_to_gen1 import Gen2ToGen1Converter
from converters.gen2_to_gen3 import Gen2ToGen3Converter
from converters.gen3_to_gen1 import Gen3ToGen1Converter
from converters.gen3_to_gen2 import Gen3ToGen2Converter
from data.species import species_exists_in_generation
from parsers.gen1 import Gen1Parser
from parsers.gen2 import Gen2Parser
from parsers.gen3 import Gen3Parser

from tests._stress.scenarios import build_canonical, iter_scenarios
from tests._stress.fixtures import load_parsers

from .compare import DiffReport, compare


CONVERTER = {
    (1, 2): Gen1ToGen2Converter,
    (1, 3): Gen1ToGen3Converter,
    (2, 1): Gen2ToGen1Converter,
    (2, 3): Gen2ToGen3Converter,
    (3, 1): Gen3ToGen1Converter,
    (3, 2): Gen3ToGen2Converter,
}

# A → B → A round trips
ROUND_TRIPS = [
    (1, 2),  # gen1 → gen2 → gen1
    (1, 3),
    (2, 1),
    (2, 3),
    (3, 1),  # most lossy direction
    (3, 2),
]


@dataclass(slots=True)
class RouteStats:
    src: int
    inter: int
    total: int = 0
    lossless: int = 0
    lossy_known: int = 0
    lossy_unexpected: int = 0
    skipped_no_species: int = 0
    skipped_blocked: int = 0
    sample_failures: list[DiffReport] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.src}→{self.inter}→{self.src}"


def _do_one_trip(
    can_before,
    src_gen: int,
    inter_gen: int,
    parsers: dict[int, Any],
):
    """Returns the final canonical after a full round trip, or (None, reason)."""
    fwd_conv = CONVERTER[(src_gen, inter_gen)]()
    back_conv = CONVERTER[(inter_gen, src_gen)]()
    # Build a target gen_inter parser session by re-using the cached singleton
    # but giving it a fresh location to write into.
    inter_parser = parsers[inter_gen]
    src_parser = parsers[src_gen]

    fwd_report = fwd_conv.can_convert(can_before, policy="auto_retrocompat")
    if not fwd_report.compatible:
        return None, f"forward blocked: {fwd_report.blocking_reasons}"
    fwd = fwd_conv.convert(can_before, inter_parser, "party:0", policy="auto_retrocompat")
    inter_parser.import_canonical("party:0", fwd.canonical_after)
    canonical_at_inter = inter_parser.export_canonical("party:0")

    back_report = back_conv.can_convert(canonical_at_inter, policy="auto_retrocompat")
    if not back_report.compatible:
        return None, f"backward blocked: {back_report.blocking_reasons}"
    back = back_conv.convert(canonical_at_inter, src_parser, "party:0", policy="auto_retrocompat")
    src_parser.import_canonical("party:0", back.canonical_after)
    canonical_after_roundtrip = src_parser.export_canonical("party:0")
    return canonical_after_roundtrip, None


def run_route(src: int, inter: int, parsers: dict[int, Any], *, dex_limit: int | None = None) -> RouteStats:
    stats = RouteStats(src=src, inter=inter)
    # Iterate species available in BOTH src and inter (otherwise round trip is impossible)
    from data.species import NATIONAL_TO_GEN1_INTERNAL, NATIONAL_TO_GEN2_ID, NATIONAL_TO_GEN3_INTERNAL
    pool = sorted(
        {1: NATIONAL_TO_GEN1_INTERNAL, 2: NATIONAL_TO_GEN2_ID, 3: NATIONAL_TO_GEN3_INTERNAL}[src].keys()
    )
    if dex_limit is not None:
        pool = pool[:dex_limit]

    for dex_id in pool:
        if not species_exists_in_generation(dex_id, inter):
            stats.skipped_no_species += 1
            continue
        for scenario in iter_scenarios(src, dex_id):
            stats.total += 1
            try:
                can_before = build_canonical(src, dex_id, scenario)
            except Exception:
                stats.lossy_unexpected += 1
                continue
            try:
                can_after, reason = _do_one_trip(can_before, src, inter, parsers)
            except Exception as exc:
                stats.lossy_unexpected += 1
                if len(stats.sample_failures) < 30:
                    stats.sample_failures.append(DiffReport(
                        label=f"dex={dex_id} sc={scenario.idx}",
                        lossy_unexpected=[f"trip raised {type(exc).__name__}: {exc}"],
                    ))
                continue
            if can_after is None:
                stats.skipped_blocked += 1
                continue
            diff = compare(
                can_before, can_after,
                src_gen=src, inter_gen=inter,
                label=f"dex={dex_id} sc={scenario.idx}",
            )
            if not diff.lossy_unexpected:
                if diff.lossy_known:
                    stats.lossy_known += 1
                else:
                    stats.lossless += 1
            else:
                stats.lossy_unexpected += 1
                if len(stats.sample_failures) < 30:
                    stats.sample_failures.append(diff)
    return stats


def run_all(*, dex_limit: int | None = None) -> list[RouteStats]:
    parsers = load_parsers()
    return [run_route(src, inter, parsers, dex_limit=dex_limit) for src, inter in ROUND_TRIPS]


def format_report(stats_list: list[RouteStats], *, max_failures: int = 20) -> str:
    out: list[str] = []
    header = (
        f"{'Round Trip':<12} {'total':>7} {'lossless':>9} {'lossy_known':>12} "
        f"{'lossy_unexpected':>16} {'skipped':>9}"
    )
    out.append(header)
    out.append("-" * len(header))
    total_unexpected = 0
    for s in stats_list:
        out.append(
            f"{s.label:<12} {s.total:>7} {s.lossless:>9} {s.lossy_known:>12} "
            f"{s.lossy_unexpected:>16} {s.skipped_no_species + s.skipped_blocked:>9}"
        )
        total_unexpected += s.lossy_unexpected

    if total_unexpected:
        out.append("")
        out.append("=== Sample unexpected diffs ===")
        for s in stats_list:
            if not s.sample_failures:
                continue
            out.append(f"\n[{s.label}] {len(s.sample_failures)} sample failures (showing up to {max_failures}):")
            for diff in s.sample_failures[:max_failures]:
                out.append(f"  • {diff.label}")
                for item in diff.lossy_unexpected[:4]:
                    out.append(f"      {item}")
    return "\n".join(out)
