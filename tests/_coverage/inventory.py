"""Battery Q: inventory listing for each save; flag items without cross-gen mapping."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from data.items import equivalent_item_id, item_name  # noqa: E402
from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"
GEN_DIRS = {1: "gen 1", 2: "gen 2", 3: "gen 3"}
PARSER_BY_GEN = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser}


def run() -> BatteryReport:
    report = BatteryReport(name="Q: inventory")
    for gen, sub in GEN_DIRS.items():
        folder = TEST_SAVES_ROOT / sub
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.sav")):
            try:
                p = PARSER_BY_GEN[gen]()
                p.load(path)
                inv = p.list_inventory()
            except Exception as exc:
                report.add_fail(f"gen{gen} {path.name}: list_inventory raised {exc}")
                continue
            if inv is None:
                report.add_fail(f"gen{gen} {path.name}: list_inventory returned None")
                continue
            # Non-empty inventory expected for veteran saves
            if not inv:
                report.note(f"gen{gen} {path.name}: empty inventory")
                report.add_pass()
                continue
            unmapped: list[int] = []
            target_gens = [g for g in (1, 2, 3) if g != gen]
            for entry in inv:
                item_id = int(entry.item_id)
                if item_id == 0:
                    continue
                # Check at least ONE target gen has a mapping for this item
                has_any = any(equivalent_item_id(item_id, gen, tgt) for tgt in target_gens)
                if not has_any:
                    unmapped.append(item_id)
            report.add_pass()
            report.note(
                f"gen{gen} {path.name}: {len(inv)} entries, {len(unmapped)} unmapped to other gens"
                + (f"; sample unmapped IDs: {unmapped[:5]}" if unmapped else "")
            )
    return report
