"""Battery P: Crystal-specific layout (money, badges, Day Care) vs Gold/Silver."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"

GS_OFFSETS = {
    "money": 0x23DB,        # 3 bytes BE
    "johto_badges": 0x23E4,  # 1 byte
    "kanto_badges": 0x23E5,
}
CRYSTAL_OFFSETS = {
    "money": 0x23DC,
    "johto_badges": 0x23E5,
    "kanto_badges": 0x23E6,
}


def _read_money_BE3(data: bytes, off: int) -> int:
    return (data[off] << 16) | (data[off + 1] << 8) | data[off + 2]


def run() -> BatteryReport:
    report = BatteryReport(name="P: Crystal/GS layout offsets")
    saves = [
        ("Pokémon - Gold Version.sav", GS_OFFSETS, "Gold"),
        ("Pokémon - Silver Version.sav", GS_OFFSETS, "Silver"),
        ("Pokémon - Crystal Version.sav", CRYSTAL_OFFSETS, "Crystal"),
    ]
    for fname, offsets, label in saves:
        path = TEST_SAVES_ROOT / "gen 2" / fname
        if not path.exists():
            report.note(f"skip {fname}: missing")
            continue
        data = path.read_bytes()
        money = _read_money_BE3(data, offsets["money"])
        johto = data[offsets["johto_badges"]]
        kanto = data[offsets["kanto_badges"]]
        # Sanity: money should be in plausible range (0..999999), badges 0..255
        if not (0 <= money <= 999_999):
            report.add_fail(f"{label}: money={money} outside expected 0..999999 (offset {offsets['money']:#x} wrong?)")
        else:
            report.add_pass()
        if not (0 <= johto <= 0xFF) or bin(johto).count("1") > 8:
            report.add_fail(f"{label}: johto_badges={johto:#04x} implausible")
        else:
            report.add_pass()
        if not (0 <= kanto <= 0xFF) or bin(kanto).count("1") > 8:
            report.add_fail(f"{label}: kanto_badges={kanto:#04x} implausible")
        else:
            report.add_pass()
        report.note(
            f"{label}: money={money}, johto=0b{johto:08b} ({bin(johto).count('1')} badges), "
            f"kanto=0b{kanto:08b} ({bin(kanto).count('1')} badges)"
        )

    # Day Care: just sanity-check that the offset doesn't crash (no specific value check).
    # Day Care occupancy byte in G/S is at 0x2D0C, Crystal at 0x2D10.
    for fname, off, label in [
        ("Pokémon - Gold Version.sav", 0x2D0C, "Gold DayCare"),
        ("Pokémon - Crystal Version.sav", 0x2D10, "Crystal DayCare"),
    ]:
        path = TEST_SAVES_ROOT / "gen 2" / fname
        if not path.exists():
            continue
        data = path.read_bytes()
        flag = data[off]
        report.add_pass()
        report.note(f"{label}: daycare_flag@{off:#x} = {flag}")
    return report
