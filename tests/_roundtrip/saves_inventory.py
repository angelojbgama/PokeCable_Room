"""Battery A: inventory every .sav, attempt load, classify OK vs corrupted."""
from __future__ import annotations

import sys
from pathlib import Path

# Path bootstrap
REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402
from parsers.gen4 import Gen4Parser  # noqa: E402
from save_curation import get_gen4_save_audit, get_curated_gen4_saves  # noqa: E402
from .report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"

GEN_DIRS = {
    1: TEST_SAVES_ROOT / "gen 1",
    2: TEST_SAVES_ROOT / "gen 2",
    3: TEST_SAVES_ROOT / "gen 3",
    4: TEST_SAVES_ROOT / "gen 4",
}

PARSER_BY_GEN = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser, 4: Gen4Parser}


def discover_saves() -> dict[int, list[Path]]:
    out: dict[int, list[Path]] = {1: [], 2: [], 3: [], 4: []}
    for gen, folder in GEN_DIRS.items():
        if not folder.exists():
            continue
        if gen == 4:
            out[gen].extend(get_curated_gen4_saves())
            continue
        for sav in sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".sav"):
            out[gen].append(sav)
    return out


def try_load(gen: int, path: Path) -> tuple[bool, str]:
    """Return (ok, message)."""
    try:
        parser = PARSER_BY_GEN[gen]()
        parser.load(path)
        party = parser.list_party()
        return True, f"party={len(party)}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def run() -> tuple[BatteryReport, dict[int, list[Path]]]:
    report = BatteryReport(name="A: saves inventory")
    saves = discover_saves()
    valid: dict[int, list[Path]] = {1: [], 2: [], 3: [], 4: []}
    gen4_audit = {record.path: record for record in get_gen4_save_audit()}
    for gen, paths in saves.items():
        for p in paths:
            ok, msg = try_load(gen, p)
            label = f"gen{gen}: {p.name}"
            if ok:
                report.add_pass()
                if gen == 4:
                    record = gen4_audit.get(p)
                    suffix = f"; {record.notes}" if record else ""
                    report.note(f"OK  {label} ({msg}{suffix})")
                else:
                    report.note(f"OK  {label} ({msg})")
                valid[gen].append(p)
            else:
                report.add_fail(f"{label} — {msg}")
                report.note(f"BAD {label} ({msg})")
    return report, valid
