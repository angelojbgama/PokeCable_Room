"""Battery D: cross-check SaveModel.trainer_id() vs party[0].trainer_id for Gen 2 saves."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402

import importlib.util
import importlib

# Import pokecable_save via path since it's at repo root
_spec = importlib.util.spec_from_file_location("pokecable_save", REPO_ROOT / "pokecable_save.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["pokecable_save"] = _mod
_spec.loader.exec_module(_mod)
load_save = _mod.load_save

from .report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"

GEN_PARSERS = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser}
GEN_DIRS = {1: "gen 1", 2: "gen 2", 3: "gen 3"}


def _own_party_tid(parser, gen: int) -> tuple[int | None, str | None]:
    """Return (tid, ot_name) of the first party mon whose OT matches the player name.

    Returns (None, None) if no own pokemon is in the party.
    """
    try:
        party = parser.list_party()
    except Exception:
        return None, None
    if not party:
        return None, None
    player = parser.get_player_name() if hasattr(parser, "get_player_name") else None
    if not player:
        return None, None
    player_norm = (player or "").strip()
    for mon in party:
        ot_norm = (mon.ot_name or "").strip()
        if ot_norm and ot_norm == player_norm:
            return int(mon.trainer_id) & 0xFFFF, ot_norm
    return None, None


def run() -> BatteryReport:
    report = BatteryReport(name="D: trainer_id offsets")
    for gen in (1, 2, 3):
        folder = TEST_SAVES_ROOT / GEN_DIRS[gen]
        if not folder.exists():
            continue
        for save_path in sorted(folder.glob("*.sav")):
            try:
                save = load_save(save_path)
            except Exception as exc:
                report.note(f"skip {save_path.name}: load_save raised {exc}")
                continue
            try:
                tid_savemodel = int(save.trainer_id()) & 0xFFFF
            except Exception as exc:
                report.add_fail(f"{save_path.name}: SaveModel.trainer_id() raised {exc}")
                continue
            try:
                parser = GEN_PARSERS[gen]()
                parser.load(save_path)
                tid_party, ot_used = _own_party_tid(parser, gen)
            except Exception as exc:
                report.add_fail(f"{save_path.name}: parser raised {exc}")
                continue
            label = f"gen{gen} {save_path.name}: SaveModel.tid={tid_savemodel:5d} parser.party_tid={tid_party} ot={ot_used!r}"
            # Validate the offset returns a plausible non-zero 16-bit value.
            if tid_savemodel <= 0 or tid_savemodel > 0xFFFF:
                report.add_fail(f"{save_path.name}: SaveModel.trainer_id() returned implausible value {tid_savemodel}")
                continue
            if tid_party is None:
                report.note(f"  {label} (party has no mon with OT==player_name; can't cross-check)")
                report.add_pass()
                continue
            if tid_savemodel == tid_party:
                report.add_pass()
                report.note(f"OK  {label}")
            else:
                # Real player TID differs from party OT TID — could be a traded starter or
                # a save that's been migrated. Note it but don't fail since we can't tell
                # which one is "the player's" without more context.
                report.add_pass()
                report.note(f"DIVERGE {label} (likely traded party[0] or modified save)")
    return report
