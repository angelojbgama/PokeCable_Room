#!/usr/bin/env python3
"""Round-trip stress: A → B → A for every (src,inter) pair, every species, every scenario.

Validates the user's concern: "se eu passar de Gen 3 → Gen 1 → Gen 3, o pokémon volta com
os MESMOS HP/XP/IV/EV?". Diffs are classified as lossless / lossy_known / lossy_unexpected.

Usage:
  python tests/stress_round_trip.py           # full
  python tests/stress_round_trip.py --limit 5 # smoke
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Pokecable_tool"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Pokecable_tool" / "pokecable_runtime"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Round-trip stress test")
    parser.add_argument("--limit", type=int, default=None, help="Cap species per gen (smoke mode)")
    args = parser.parse_args()
    from tests._roundtrip_stress.runner import run_all, format_report

    t0 = time.perf_counter()
    print(f"=== Round-Trip Stress Suite ===")
    print(f"(every species × scenarios, A → B → A; classifies lossless / known-loss / unexpected)\n")
    stats = run_all(dex_limit=args.limit)
    elapsed = time.perf_counter() - t0
    print(format_report(stats))
    total_unexpected = sum(s.lossy_unexpected for s in stats)
    print(f"\nElapsed: {elapsed:.1f}s")
    print(f"RESULT: {'PASS' if total_unexpected == 0 else f'FAIL ({total_unexpected} unexpected losses)'}")
    return 0 if total_unexpected == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
