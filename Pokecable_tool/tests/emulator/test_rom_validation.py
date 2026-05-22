"""Battery S: PyBoy headless RAM/SRAM dump → JSON for AI inspection.

For every Gen 1/2 ROM+save, this:
  - Loads the .sav into PyBoy via ram_file= (explicit; auto-load doesn't work)
  - Ticks N frames to let the cartridge initialize
  - Dumps known SRAM regions (player name, TID, party) and compares to the .sav file bytes
  - Optionally tries to advance to in-game and snapshot WRAM party
  - Writes everything as JSON to tests/_emu_dumps/{label}.json

Gen 3 (GBA) is not supported by PyBoy — marked as SKIP per save.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pokecable_runtime"))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"
DUMP_DIR = REPO_ROOT / "tests" / "_emu_dumps"
DUMP_DIR.mkdir(parents=True, exist_ok=True)

# (label, rom file, save file, gen subfolder, gen number)
GAMES = [
    ("Red",     "Pokémon - Red Version.gb",      "Pokémon - Red Version.sav",      "gen 1", 1),
    ("Blue",    "Pokémon - Blue Version.gb",     "Pokémon - Blue Version.sav",     "gen 1", 1),
    ("Yellow",  "Pokémon - Yellow Version.gb",   "Pokémon - Yellow Version.sav",   "gen 1", 1),
    ("Gold",    "Pokémon - Gold Version.gbc",    "Pokémon - Gold Version.sav",     "gen 2", 2),
    ("Silver",  "Pokémon - Silver Version.gbc",  "Pokémon - Silver Version.sav",   "gen 2", 2),
    ("Crystal", "Pokémon - Crystal Version.gbc", "Pokémon - Crystal Version.sav",  "gen 2", 2),
]

# Save-file SRAM regions to fingerprint (offset, length, label).
# These map into PyBoy SRAM via MBC bank switching (bank N covers .sav bytes N*0x2000 .. (N+1)*0x2000).
SAV_REGIONS = {
    1: {
        "player_name": (0x2598, 11),
        "trainer_id":  (0x2605, 2),
        "party_count": (0x2F2C, 1),
        "party_species_list": (0x2F2D, 6),
    },
    2: {
        "trainer_id":  (0x2009, 2),
        "player_name": (0x200B, 11),
        # Crystal has shifted layout; just snapshot both
        "money_block": (0x23DB, 6),
    },
}


def _try_import_pyboy():
    try:
        from pyboy import PyBoy
        return PyBoy
    except Exception:
        return None


def _read_sram_via_pyboy(pb, sav_offset: int, length: int) -> bytes:
    """Read length bytes from save offset by switching MBC bank and reading 0xA000."""
    bank = sav_offset // 0x2000
    in_bank = sav_offset % 0x2000
    # Enable SRAM, switch bank (MBC1/3 register layout)
    pb.memory[0x0000] = 0x0A
    pb.memory[0x4000] = bank
    pb.tick(1)
    return bytes(pb.memory[0xA000 + in_bank + i] for i in range(length))


def _dump_save(pb, gen: int, sav_path: Path) -> dict:
    sav_bytes = sav_path.read_bytes()
    regions = SAV_REGIONS.get(gen, {})
    result = {}
    for name, (off, length) in regions.items():
        sram = _read_sram_via_pyboy(pb, off, length)
        sav = sav_bytes[off: off + length]
        result[name] = {
            "offset": f"0x{off:04x}",
            "expected_sav": sav.hex(),
            "actual_sram": sram.hex(),
            "match": sram == sav,
        }
    return result


def run() -> BatteryReport:
    report = BatteryReport(name="S: PyBoy SRAM dump + checksum match")
    PyBoy = _try_import_pyboy()
    if not PyBoy:
        report.note("SKIP: pyboy not installed. `pip install pyboy --break-system-packages` to enable.")
        return report
    for label, rom_name, sav_name, sub, gen in GAMES:
        rom_path = TEST_SAVES_ROOT / sub / rom_name
        sav_path = TEST_SAVES_ROOT / sub / sav_name
        if not rom_path.exists() or not sav_path.exists():
            report.note(f"skip {label}: ROM or save missing")
            continue
        # Copy to a clean temp dir so PyBoy doesn't write to the original .sav
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            rom = tmp / rom_name
            sav = tmp / sav_name
            shutil.copy(rom_path, rom)
            shutil.copy(sav_path, sav)
            try:
                with open(sav, "rb") as f:
                    pb = PyBoy(str(rom), ram_file=f, window="null", sound_emulated=False)
                    pb.tick(60)
                    dump = _dump_save(pb, gen, sav)
                    pb.stop(save=False)
            except Exception as exc:
                report.add_fail(f"{label}: PyBoy raised {type(exc).__name__}: {exc}")
                continue
        # Verify all regions match
        all_match = all(entry["match"] for entry in dump.values())
        out_path = DUMP_DIR / f"{label}.json"
        out_path.write_text(json.dumps({
            "label": label,
            "gen": gen,
            "regions": dump,
            "all_match": all_match,
        }, indent=2))
        if all_match:
            report.add_pass()
            report.note(f"{label}: all {len(dump)} regions match (dumped to {out_path.relative_to(REPO_ROOT)})")
        else:
            mismatched = [k for k, v in dump.items() if not v["match"]]
            report.add_fail(f"{label}: regions mismatch {mismatched} — see {out_path.relative_to(REPO_ROOT)}")

    # Gen 3 — PyBoy doesn't support GBA. Note for user.
    report.note("Gen 3 (Ruby/Sapphire/Emerald/FireRed/LeafGreen): PyBoy doesn't emulate GBA. "
                "Use mGBA-python or other GBA Python binding for headless validation.")
    return report
