#!/usr/bin/env python3
"""Stress test driver — cross-gen Pokémon retrocompatibility (1↔2↔3).

Usage:
  python tests/stress_cross_gen.py                    # full run
  python tests/stress_cross_gen.py --limit 5          # smoke (first 5 species per gen)
  python tests/stress_cross_gen.py --routes 1-2,2-3   # subset
  python tests/stress_cross_gen.py --policies auto_retrocompat
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Make the repo importable when invoked as `python tests/stress_cross_gen.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._stress.fixtures import POLICIES, ROUTES, load_parsers  # noqa: E402
from tests._stress.runner import format_report, run_route  # noqa: E402


def _parse_routes(spec: str | None) -> list[tuple[int, int]]:
    if not spec:
        return list(ROUTES)
    routes: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        a, b = part.split("-")
        routes.append((int(a), int(b)))
    return routes


def _parse_policies(spec: str | None) -> list[str]:
    if not spec:
        return list(POLICIES)
    return [p.strip() for p in spec.split(",") if p.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-gen retrocompatibility stress test")
    parser.add_argument("--routes", default=None, help="Comma-separated routes (e.g. 1-2,2-3)")
    parser.add_argument("--policies", default=None, help="Comma-separated policies (auto_retrocompat,strict)")
    parser.add_argument("--limit", type=int, default=None, help="Limit to first N species per gen (smoke mode)")
    parser.add_argument("--max-failures-print", type=int, default=20, help="Max failures to print per (route,policy)")
    args = parser.parse_args(argv)

    routes = _parse_routes(args.routes)
    policies = _parse_policies(args.policies)
    parsers = load_parsers()
    all_stats = []
    print(f"Loaded parsers; running {len(routes)} routes × {len(policies)} policies"
          + (f"; --limit {args.limit}" if args.limit else ""))
    t0 = time.perf_counter()
    for src, tgt in routes:
        for policy in policies:
            stats = run_route(src, tgt, policy, parsers, dex_limit=args.limit)
            print(f"  {src}→{tgt} {policy:<18} total={stats.total:5d} compat={stats.compatible:5d} "
                  f"convOK={stats.converted_ok:5d} verOK={stats.verified_ok:5d} failed={stats.failed:5d}")
            all_stats.append(stats)
    elapsed = time.perf_counter() - t0
    print()
    print(format_report(all_stats, max_print=args.max_failures_print))
    print(f"\nElapsed: {elapsed:.1f}s")
    return 0 if all(s.failed == 0 for s in all_stats) else 1


if __name__ == "__main__":
    sys.exit(main())
