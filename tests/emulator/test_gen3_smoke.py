"""Battery T: Gen 3 SRAM dump via libmgba+ctypes.

For each Gen 3 ROM+save: boot in libmgba headlessly, run a few frames so the cart
initializes, then dump the GBA SRAM region (0x0E000000, 128KB) and compare against
the .sav file we passed in. Writes JSON dumps to tests/_emu_dumps/ for AI inspection.

Skips cleanly if libmgba or mgba_wrapper.so are not available.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pokecable_runtime"))

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"
DUMP_DIR = REPO_ROOT / "tests" / "_emu_dumps"
DUMP_DIR.mkdir(parents=True, exist_ok=True)

GEN3_GAMES = [
    ("Emerald",   "Pokémon - Emerald Version.gba",   "Pokémon - Emerald Version.sav"),
    ("FireRed",   "Pokémon - FireRed Version.gba",   "Pokémon - FireRed Version.sav"),
    ("LeafGreen", "Pokémon - LeafGreen Version.gba", "Pokémon - LeafGreen Version.sav"),
    ("Ruby",      "Pokémon - Ruby Version.gba",      "Pokémon - Ruby Version.sav"),
    ("Sapphire",  "Pokémon - Sapphire Version.gba",  "Pokémon - Sapphire Version.sav"),
]

# Gen 3 save sectors live in SRAM/flash. Each sector is 4096 bytes, 14 sectors per slot,
# so 14*4096 = 57344 bytes per slot, two slots = 114688 bytes total in a 128KB SRAM image.
# Sector signature 0x08012025 lives at sector offset 0xFF8-0xFFC (last 8 bytes of the 4KB sector).
SECTOR_SIZE = 0x1000
SECTORS_PER_SLOT = 14
SECTOR_SIGNATURE = 0x08012025


def _section_signature(sram: bytes, sector_index: int) -> int | None:
    """Return the 4-byte signature at the tail of a sector, or None if out of range."""
    start = sector_index * SECTOR_SIZE
    if start + SECTOR_SIZE > len(sram):
        return None
    return int.from_bytes(sram[start + 0xFF8: start + 0xFFC], "little")


def run() -> BatteryReport:
    report = BatteryReport(name="T: Gen 3 SRAM dump via libmgba")
    try:
        from tests.emulator._libmgba import LibMGBA, MGBASession
        lib = LibMGBA()
    except OSError as exc:
        report.note(f"SKIP: {exc}")
        return report
    except Exception as exc:
        report.note(f"SKIP: libmgba init failed: {type(exc).__name__}: {exc}")
        return report

    report.note(f"libmgba loaded; wrapper at tests/emulator/mgba_wrapper.so")

    for label, rom_name, sav_name in GEN3_GAMES:
        rom_src = TEST_SAVES_ROOT / "gen 3" / rom_name
        sav_src = TEST_SAVES_ROOT / "gen 3" / sav_name
        if not rom_src.exists() or not sav_src.exists():
            report.note(f"skip {label}: ROM or save missing")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            rom = tmp / rom_name
            sav = tmp / sav_name
            shutil.copy(rom_src, rom)
            shutil.copy(sav_src, sav)
            sav_bytes = sav_src.read_bytes()
            try:
                with MGBASession(lib, rom) as session:
                    # Advance frames so the cartridge initializes its SRAM mapping.
                    session.run_frames(120)
                    sram = session.read_block(0x0E000000)
            except Exception as exc:
                report.add_fail(f"{label}: session raised {type(exc).__name__}: {exc}")
                continue
        if sram is None or len(sram) == 0:
            report.add_fail(f"{label}: empty SRAM dump")
            continue
        # Inspect sector signatures (Gen 3 saves have 14 sectors of 4KB each, signature at 0xFF8)
        good_sectors = sum(
            1 for i in range(min(len(sram) // SECTOR_SIZE, 2 * SECTORS_PER_SLOT))
            if _section_signature(sram, i) == SECTOR_SIGNATURE
        )
        # The .sav file IS the SRAM image — they should be byte-identical (or very close).
        compare_len = min(len(sram), len(sav_bytes))
        matching_bytes = sum(1 for i in range(compare_len) if sram[i] == sav_bytes[i])
        match_pct = matching_bytes * 100 // compare_len if compare_len else 0
        dump_path = DUMP_DIR / f"{label}_gen3.json"
        dump_path.write_text(json.dumps({
            "label": label,
            "sram_size": len(sram),
            "sav_size": len(sav_bytes),
            "good_sector_signatures": good_sectors,
            "expected_min_sectors": SECTORS_PER_SLOT,  # at least one full slot
            "bytes_matching_pct": match_pct,
            "first_16_sram": sram[:16].hex(),
            "first_16_sav": sav_bytes[:16].hex(),
        }, indent=2))
        if good_sectors >= SECTORS_PER_SLOT and match_pct >= 95:
            report.add_pass()
            report.note(
                f"{label}: SRAM dump OK — {good_sectors}/14+ valid sectors, "
                f"{match_pct}% byte-match with .sav (see {dump_path.relative_to(REPO_ROOT)})"
            )
        else:
            report.add_fail(
                f"{label}: SRAM mismatch — good_sectors={good_sectors}/14 byte_match={match_pct}% "
                f"(dump at {dump_path.relative_to(REPO_ROOT)})"
            )
    return report
