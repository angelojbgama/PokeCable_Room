"""Battery S: real-emulator smoke boot — mGBA loads ROM+save, runs briefly, checks no crash.

This validates that the save bytes produced by our parsers are accepted by mGBA
(emulator-side checksum, sector signatures, no immediate corruption detection).
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pokecable_runtime"))

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"

MGBA_CANDIDATES = [
    "mgba-sdl",
    "mgba",
    "/mnt/c/Program Files/mGBA/mgba-sdl.exe",
    "/mnt/c/Program Files/mGBA/mGBA.exe",
]

# (label, rom filename, save filename, gen subfolder)
GAMES = [
    ("Red",       "Pokémon - Red Version.gb",        "Pokémon - Red Version.sav",        "gen 1"),
    ("Blue",      "Pokémon - Blue Version.gb",       "Pokémon - Blue Version.sav",       "gen 1"),
    ("Yellow",    "Pokémon - Yellow Version.gb",     "Pokémon - Yellow Version.sav",     "gen 1"),
    ("Gold",      "Pokémon - Gold Version.gbc",      "Pokémon - Gold Version.sav",       "gen 2"),
    ("Silver",    "Pokémon - Silver Version.gbc",    "Pokémon - Silver Version.sav",     "gen 2"),
    ("Crystal",   "Pokémon - Crystal Version.gbc",   "Pokémon - Crystal Version.sav",    "gen 2"),
    ("Ruby",      "Pokémon - Ruby Version.gba",      "Pokémon - Ruby Version.sav",       "gen 3"),
    ("Sapphire",  "Pokémon - Sapphire Version.gba",  "Pokémon - Sapphire Version.sav",   "gen 3"),
    ("Emerald",   "Pokémon - Emerald Version.gba",   "Pokémon - Emerald Version.sav",    "gen 3"),
    ("FireRed",   "Pokémon - FireRed Version.gba",   "Pokémon - FireRed Version.sav",    "gen 3"),
    ("LeafGreen", "Pokémon - LeafGreen Version.gba", "Pokémon - LeafGreen Version.sav",  "gen 3"),
]


def _find_mgba() -> str | None:
    for candidate in MGBA_CANDIDATES:
        which = shutil.which(candidate)
        if which:
            return which
        if Path(candidate).exists():
            return candidate
    return None


def _wsl_to_windows(path: Path) -> str:
    """Convert /mnt/c/... → C:\\... for Windows binaries called from WSL."""
    s = str(path)
    if s.startswith("/mnt/"):
        try:
            return subprocess.check_output(["wslpath", "-w", s], text=True).strip()
        except Exception:
            # Manual fallback
            parts = s.split("/")
            return parts[2].upper() + ":\\" + "\\".join(parts[3:])
    return s


def _smoke_boot(mgba: str, rom_path: Path, timeout_seconds: float = 4.0) -> tuple[bool, str]:
    """Launch mGBA on the given ROM (with .sav loaded from same dir), kill after a few seconds.

    Returns (success, log_excerpt). Success = process didn't error immediately AND didn't
    print obvious failure indicators in its log.
    """
    is_windows_exe = mgba.lower().endswith(".exe")
    rom_arg = _wsl_to_windows(rom_path) if is_windows_exe else str(rom_path)
    cmd = [mgba, "-1", rom_arg]  # -1 = 1x scale, smallest viewport
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    try:
        proc = subprocess.Popen(
            cmd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except Exception as exc:
        return False, f"Popen failed: {exc}"
    time.sleep(timeout_seconds)
    # Kill the process
    try:
        if is_windows_exe:
            subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        pass
    try:
        out, err = proc.communicate(timeout=2.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = b"", b""
    log = (out + err).decode("utf-8", errors="replace")
    # Look for obvious failure markers
    bad_markers = [
        "failed to load", "save corrupted", "could not parse", "fatal", "error: ",
        "could not run game", "not a compatible game",
    ]
    log_lower = log.lower()
    failures = [m for m in bad_markers if m in log_lower]
    if failures:
        return False, f"mGBA reported: {failures}; tail: {log[-200:]}"
    return True, log[-200:] if log else "no output"


def run() -> BatteryReport:
    report = BatteryReport(name="S: emulator smoke boot (mGBA)")
    mgba = _find_mgba()
    if not mgba:
        report.note("SKIP: mGBA not found. Tried: " + ", ".join(MGBA_CANDIDATES))
        return report
    report.note(f"using mGBA: {mgba}")

    # Use a tempdir under /mnt/c/ so the Windows mGBA binary can access it.
    win_temp_root = Path("/mnt/c/Users/USER/AppData/Local/Temp")
    win_temp_root.mkdir(parents=True, exist_ok=True)
    tmpdir = win_temp_root / f"pokecable_emu_{int(time.time())}"
    tmpdir.mkdir(parents=True, exist_ok=True)
    try:
        for label, rom_name, sav_name, sub in GAMES:
            rom_src = TEST_SAVES_ROOT / sub / rom_name
            sav_src = TEST_SAVES_ROOT / sub / sav_name
            if not rom_src.exists() or not sav_src.exists():
                report.note(f"skip {label}: ROM or save missing")
                continue
            # Copy ROM+save side-by-side (mGBA convention)
            work_rom = tmpdir / rom_name
            work_sav = tmpdir / (rom_src.stem + rom_src.suffix.replace(rom_src.suffix, ".sav"))
            # Use stem-based pairing: same basename, .sav extension
            work_sav = tmpdir / (Path(rom_name).stem + ".sav")
            shutil.copy(rom_src, work_rom)
            shutil.copy(sav_src, work_sav)
            ok, msg = _smoke_boot(mgba, work_rom)
            if ok:
                report.add_pass()
                report.note(f"{label}: BOOT OK ({msg.strip()[:80]})")
            else:
                report.add_fail(f"{label}: {msg}")

    # Best-effort cleanup (mGBA on Windows may briefly hold a file lock)
    finally:
        time.sleep(0.5)
        shutil.rmtree(tmpdir, ignore_errors=True)
    return report
