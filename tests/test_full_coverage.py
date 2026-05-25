#!/usr/bin/env python3
"""Full-coverage driver: batteries F..S closing all 14 listed gaps.

Usage:  python tests/test_full_coverage.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Pokecable_tool"))


def main() -> int:
    t0 = time.perf_counter()
    print("=== Full Coverage Suite (Batteries F..S) ===\n")

    # Import all batteries lazily to keep failure isolation
    from tests._coverage import (  # noqa: E402
        backup_restore,
        boxes_full,
        crystal_layout,
        disk_persistence,
        eggs,
        event_pokemon,
        forms_quirks,
        fresh_saves,
        glitched_inputs,
        inventory,
        item_relocation,
        lan_loopback,
        trade_evolution,
        ui_snapshot,
    )
    from tests.emulator import test_rom_validation  # noqa: E402
    from tests.emulator import test_gen3_smoke  # noqa: E402

    batteries = [
        ("F", boxes_full.run, "boxes export+roundtrip"),
        ("G", disk_persistence.run, "disk persistence + checksum"),
        ("H", forms_quirks.run, "forms (Spinda/Castform/Deoxys)"),
        ("I", trade_evolution.run, "trade evolution"),
        ("J", event_pokemon.run, "event Pokémon (fateful encounter)"),
        ("K", eggs.run, "eggs negative-test"),
        ("L", glitched_inputs.run, "glitched inputs"),
        ("M", lan_loopback.run, "LAN loopback"),
        ("N", backup_restore.run, "backup + restore"),
        ("O", fresh_saves.run, "fresh / edge-case party sizes"),
        ("P", crystal_layout.run, "Crystal/GS layout"),
        ("Q", inventory.run, "inventory listing"),
        ("R", ui_snapshot.run, "UI snapshot smoke"),
        ("U", item_relocation.run, "held item → bag/PC on cross-gen"),
        ("S", test_rom_validation.run, "PyBoy SRAM dump Gen 1/2"),
        ("T", test_gen3_smoke.run, "Gen 3 mGBA smoke boot"),
    ]

    reports = []
    for code, fn, desc in batteries:
        print(f"[{code}] {desc} ...")
        try:
            r = fn()
        except Exception as exc:
            print(f"  ERROR running battery {code}: {exc}")
            continue
        reports.append((code, r))
        print(f"  {code}: total={r.total} passed={r.passed} failed={r.failed}")
        for note in r.notes[:3]:
            print(f"     · {note}")
        if r.notes[3:]:
            print(f"     · ... ({len(r.notes) - 3} more notes)")

    elapsed = time.perf_counter() - t0

    print("\n=== Summary ===")
    header = f"{'#':<3} {'Battery':<45} {'total':>6} {'passed':>7} {'failed':>7}"
    print(header)
    print("-" * len(header))
    total_failed = 0
    for code, r in reports:
        print(f"{code:<3} {r.name:<45} {r.total:>6} {r.passed:>7} {r.failed:>7}")
        total_failed += r.failed

    if total_failed:
        print("\n=== Failures detail ===")
        for code, r in reports:
            if r.failures:
                print(f"\n[{code}] {r.name}")
                for f in r.failures[:10]:
                    print(f"  • {f}")
                if r.failures[10:]:
                    print(f"  · ... {len(r.failures) - 10} more")

    print(f"\nElapsed: {elapsed:.2f}s")
    print(f"RESULT: {'PASS' if total_failed == 0 else f'FAIL ({total_failed} failures)'}")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
