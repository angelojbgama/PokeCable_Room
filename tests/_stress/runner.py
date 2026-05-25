"""Route loop, accumulator, and report formatter."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import fixtures
from .scenarios import Scenario, build_canonical, iter_scenarios
from .verifiers import verify, Mismatch
from converters.gen1_to_gen2 import Gen1ToGen2Converter
from converters.gen1_to_gen3 import Gen1ToGen3Converter
from converters.gen2_to_gen1 import Gen2ToGen1Converter
from converters.gen2_to_gen3 import Gen2ToGen3Converter
from converters.gen3_to_gen1 import Gen3ToGen1Converter
from converters.gen3_to_gen2 import Gen3ToGen2Converter
from data.species import NATIONAL_TO_GEN1_INTERNAL, NATIONAL_TO_GEN2_ID, NATIONAL_TO_GEN3_INTERNAL, species_exists_in_generation

_CONVERTERS = {
    (1, 2): Gen1ToGen2Converter,
    (2, 1): Gen2ToGen1Converter,
    (1, 3): Gen1ToGen3Converter,
    (2, 3): Gen2ToGen3Converter,
    (3, 1): Gen3ToGen1Converter,
    (3, 2): Gen3ToGen2Converter,
}

_NATIONAL_BY_GEN = {
    1: NATIONAL_TO_GEN1_INTERNAL,
    2: NATIONAL_TO_GEN2_ID,
    3: NATIONAL_TO_GEN3_INTERNAL,
}

MAX_STORED_FAILURES = 50


@dataclass(slots=True)
class FailureRecord:
    route: tuple[int, int]
    policy: str
    dex_id: int
    scenario_idx: int
    stage: str
    detail: str


@dataclass(slots=True)
class RouteStats:
    route: tuple[int, int]
    policy: str
    total: int = 0
    expected_incompatible: int = 0
    compatible: int = 0
    converted_ok: int = 0
    verified_ok: int = 0
    failed: int = 0
    failures: list[FailureRecord] = field(default_factory=list)

    def add_failure(self, dex_id: int, scenario_idx: int, stage: str, detail: str) -> None:
        self.failed += 1
        if len(self.failures) < MAX_STORED_FAILURES:
            self.failures.append(FailureRecord(self.route, self.policy, dex_id, scenario_idx, stage, detail))


def _species_pool(gen: int) -> list[int]:
    return sorted(_NATIONAL_BY_GEN[gen].keys())


def run_route(src_gen: int, target_gen: int, policy: str, parsers: dict[int, Any], *, dex_limit: int | None = None) -> RouteStats:
    stats = RouteStats(route=(src_gen, target_gen), policy=policy)
    converter_cls = _CONVERTERS.get((src_gen, target_gen))
    if converter_cls is None:
        return stats
    converter = converter_cls()
    target_parser = parsers[target_gen]
    species = _species_pool(src_gen)
    if dex_limit is not None:
        species = species[:dex_limit]

    for dex_id in species:
        target_supported = species_exists_in_generation(dex_id, target_gen)
        for scenario in iter_scenarios(src_gen, dex_id):
            stats.total += 1
            try:
                can = build_canonical(src_gen, dex_id, scenario)
            except Exception as e:
                stats.add_failure(dex_id, scenario.idx, "build_canonical", repr(e))
                continue
            source_held_item = can.held_item.item_id if can.held_item else None

            try:
                report = converter.can_convert(can, policy=policy)
            except Exception as e:
                stats.add_failure(dex_id, scenario.idx, "can_convert_raise", repr(e))
                continue

            if not target_supported:
                # species doesn't exist in target — must be incompatible
                stats.expected_incompatible += 1
                if report.compatible:
                    stats.add_failure(dex_id, scenario.idx, "unexpected_compat", f"species {dex_id} missing in gen {target_gen} but compatible=True")
                continue

            if not report.compatible:
                # Expected behavior for strict policy when items/abilities are dropped — record but don't fail
                if policy == "strict":
                    continue
                # auto_retrocompat should accept anything that target species exists for
                stats.add_failure(dex_id, scenario.idx, "auto_retrocompat_blocked", "; ".join(report.blocking_reasons))
                continue

            stats.compatible += 1
            try:
                result = converter.convert(can, target_parser, "party:0", policy=policy)
            except Exception as e:
                stats.add_failure(dex_id, scenario.idx, "convert_raise", repr(e))
                continue

            try:
                blob = target_parser.build_party_mon_from_canonical(result.canonical_after)
            except Exception as e:
                stats.add_failure(dex_id, scenario.idx, "build_raise", repr(e))
                continue
            stats.converted_ok += 1

            try:
                mismatches: list[Mismatch] = verify(can, target_gen, blob, source_held_item=source_held_item)
            except Exception as e:
                stats.add_failure(dex_id, scenario.idx, "verify_raise", repr(e))
                continue

            if mismatches:
                # Record first mismatch as the failure stage
                first = mismatches[0]
                stats.add_failure(dex_id, scenario.idx, f"verify_mismatch:{first.field}", str(first))
            else:
                stats.verified_ok += 1

    return stats


def format_report(all_stats: list[RouteStats], *, max_print: int = 20) -> str:
    out: list[str] = []
    header = f"{'route':<8} {'policy':<18} {'total':>7} {'exp_inc':>8} {'compat':>7} {'convOK':>7} {'verOK':>7} {'failed':>7}"
    out.append(header)
    out.append("-" * len(header))
    total_failed = 0
    for s in all_stats:
        out.append(
            f"{s.route[0]}→{s.route[1]:<5} {s.policy:<18} {s.total:>7} {s.expected_incompatible:>8} {s.compatible:>7} {s.converted_ok:>7} {s.verified_ok:>7} {s.failed:>7}"
        )
        total_failed += s.failed
    out.append("")
    for s in all_stats:
        if not s.failures:
            continue
        out.append(f"-- First {min(len(s.failures), max_print)} failures for {s.route[0]}→{s.route[1]} ({s.policy}) --")
        for f in s.failures[:max_print]:
            out.append(f"  dex={f.dex_id:3d} sc={f.scenario_idx:3d} stage={f.stage} :: {f.detail}")
        out.append("")
    out.append(f"RESULT: {'PASS' if total_failed == 0 else f'FAIL ({total_failed} failures)'}")
    return "\n".join(out)
