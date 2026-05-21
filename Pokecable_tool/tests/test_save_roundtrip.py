#!/usr/bin/env python3
"""Roundtrip via real saves + Unown/TID/LAN quirks.

Usage:  python tests/test_save_roundtrip.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests._roundtrip.quirks_lan import run as run_lan  # noqa: E402
from tests._roundtrip.quirks_tid import run as run_tid  # noqa: E402
from tests._roundtrip.quirks_unown import run as run_unown  # noqa: E402
from tests._roundtrip.roundtrip_real import run as run_roundtrip  # noqa: E402
from tests._roundtrip.saves_inventory import run as run_inventory  # noqa: E402


def main() -> int:
    t0 = time.perf_counter()
    print("=== Save Roundtrip & Quirks Test Suite ===\n")
    reports = []

    # Battery A
    rep_a, valid_saves = run_inventory()
    reports.append(rep_a)
    print(f"[A] {rep_a.name}")
    for n in rep_a.notes:
        print(f"    {n}")
    print()

    # Battery B
    rep_b = run_roundtrip(valid_saves)
    reports.append(rep_b)

    # Battery C
    rep_c = run_unown()
    reports.append(rep_c)

    # Battery D
    rep_d = run_tid()
    reports.append(rep_d)
    print(f"[D] {rep_d.name}")
    for n in rep_d.notes:
        print(f"    {n}")
    print()

    # Battery E
    rep_e = run_lan()
    reports.append(rep_e)

    elapsed = time.perf_counter() - t0

    # Summary table
    print("=== Summary ===")
    header = f"{'Battery':<40} {'total':>6} {'passed':>7} {'failed':>7}"
    print(header)
    print("-" * len(header))
    total_failed = 0
    for r in reports:
        print(f"{r.name:<40} {r.total:>6} {r.passed:>7} {r.failed:>7}")
        total_failed += r.failed

    # Failure detail
    if total_failed:
        print("\n=== Failures ===")
        for r in reports:
            if r.failures:
                print(f"\n[{r.name}]")
                for f in r.failures[:20]:
                    print(f"  • {f}")

    print(f"\nElapsed: {elapsed:.2f}s")
    print(f"RESULT: {'PASS' if total_failed == 0 else f'FAIL ({total_failed} failures)'}")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
