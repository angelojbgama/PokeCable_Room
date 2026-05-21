"""Battery O: edge cases — party_count=1 and party_count=0 (synthesized)."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from parsers.gen1 import Gen1Parser, PARTY_OFFSET as G1_PARTY_OFFSET  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def _check(parser, label: str, report: BatteryReport, expected_count: int) -> None:
    try:
        party = parser.list_party()
    except Exception as exc:
        report.add_fail(f"{label}: list_party raised {exc}")
        return
    if len(party) != expected_count:
        report.add_fail(f"{label}: party len {len(party)} != expected {expected_count}")
    else:
        report.add_pass()


def run() -> BatteryReport:
    report = BatteryReport(name="O: fresh / edge-case party sizes")

    # Mutate party_count byte in-memory (not via load — load validates checksums).

    # Gen 1
    g1 = Gen1Parser()
    g1.load(TEST_SAVES_ROOT / "gen 1" / "Pokémon - Red Version.sav")
    g1._require_data()[G1_PARTY_OFFSET] = 1
    _check(g1, "Gen 1 party_count=1", report, 1)
    g1._require_data()[G1_PARTY_OFFSET] = 0
    _check(g1, "Gen 1 party_count=0", report, 0)

    # Gen 2
    g2 = Gen2Parser()
    g2.load(TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav")
    layout = g2._require_layout()
    g2._require_data()[layout.party_offset] = 1
    _check(g2, "Gen 2 party_count=1", report, 1)
    g2._require_data()[layout.party_offset] = 0
    _check(g2, "Gen 2 party_count=0", report, 0)

    # Gen 3 — party count is in SaveBlock1 at section1 + party_count_offset
    g3 = Gen3Parser()
    g3.load(TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav")
    layout3 = g3._require_layout()
    section_offsets = (g3.slot.section_offsets if g3.slot else None) if hasattr(g3, "slot") else None
    if section_offsets and 1 in section_offsets:
        addr = section_offsets[1] + layout3.party_count_offset
        g3._require_data()[addr] = 1
        _check(g3, "Gen 3 party_count=1", report, 1)
        g3._require_data()[addr] = 0
        _check(g3, "Gen 3 party_count=0", report, 0)

    return report
