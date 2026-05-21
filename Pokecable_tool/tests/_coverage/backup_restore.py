"""Battery N: backup creation, retention, restore."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pokecable_runtime"))

import importlib.util
_spec = importlib.util.spec_from_file_location("r36s_pokecable_core", REPO_ROOT / "r36s_pokecable_core.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["r36s_pokecable_core"] = _mod
_spec.loader.exec_module(_mod)

from tests._roundtrip.report import BatteryReport  # noqa: E402

_create_backup = _mod._create_backup
_prune_backups = _mod._prune_backups
_BACKUP_RETENTION = _mod._BACKUP_RETENTION

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def run() -> BatteryReport:
    report = BatteryReport(name="N: backup + retention + restore")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        orig = TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav"
        working = tmpdir / "stress_backup_test.sav"
        shutil.copy(orig, working)

        # Single backup
        try:
            backup_path = _create_backup(working)
            if not backup_path.exists():
                report.add_fail("create_backup did not write file")
                return report
            report.add_pass()
            report.note(f"first backup at {backup_path}")
        except Exception as exc:
            report.add_fail(f"_create_backup raised {type(exc).__name__}: {exc}")
            return report

        backup_dir = backup_path.parent
        stem = working.stem

        # Cleanup any prior stress-test backups for a clean retention count
        for stale in backup_dir.glob(f"{stem}.*.bak"):
            if stale != backup_path:
                try:
                    stale.unlink()
                except Exception:
                    pass

        # Create many backups quickly. Since timestamps have 1-second resolution and
        # _prune is based on mtime, we need distinct files. Synthesize artificial backups
        # with unique mtimes to test prune.
        import time as _time
        for i in range(_BACKUP_RETENTION + 5):
            target = backup_dir / f"{stem}.synth_{i:03d}.bak"
            shutil.copy(working, target)
            # Stagger mtime so retention picks newest deterministically
            _time.sleep(0.005)
            target.touch()
        _prune_backups(backup_dir, stem)
        survivors = list(backup_dir.glob(f"{stem}*.bak"))
        if len(survivors) > _BACKUP_RETENTION:
            report.add_fail(f"retention not enforced: {len(survivors)} backups > {_BACKUP_RETENTION}")
        else:
            report.add_pass()
            report.note(f"retention OK after {_BACKUP_RETENTION + 5} backups: {len(survivors)} kept")

        # Restore flow: corrupt working file then copy backup back.
        original_bytes = orig.read_bytes()
        working.write_bytes(b"\xFF" * len(original_bytes))
        latest = max(survivors, key=lambda p: p.stat().st_mtime)
        shutil.copy(latest, working)
        if working.read_bytes() == original_bytes:
            report.add_pass()
            report.note("restore from backup recovers original bytes")
        else:
            report.add_fail("restored file doesn't match original")

        # Clean up created backups so we don't pollute ~/.pokecable/backups
        for f in backup_dir.glob(f"{stem}*.bak"):
            try:
                f.unlink()
            except Exception:
                pass

    return report
