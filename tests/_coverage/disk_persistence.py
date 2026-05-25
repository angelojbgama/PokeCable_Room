"""Battery G: save to temp .sav, reload, verify checksum + data integrity."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from converters.gen2_to_gen3 import Gen2ToGen3Converter  # noqa: E402
from converters.gen1_to_gen2 import Gen1ToGen2Converter  # noqa: E402
from converters.gen3_to_gen2 import Gen3ToGen2Converter  # noqa: E402
from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def _fresh(parser_cls, path: Path):
    p = parser_cls()
    p.load(path)
    return p


def _do_one(src_parser, tgt_parser_cls, tgt_path: Path, converter_cls, label: str, report: BatteryReport):
    try:
        canonical = src_parser.export_canonical("party:0")
    except Exception as e:
        report.add_fail(f"{label}: export_canonical raised {e}")
        return
    tgt = _fresh(tgt_parser_cls, tgt_path)
    try:
        result = converter_cls().convert(canonical, tgt, "party:0", policy="auto_retrocompat")
        if not result.compatibility_report.compatible:
            report.note(f"{label}: skipped (report incompatible: {result.compatibility_report.blocking_reasons})")
            return
        tgt.import_canonical("party:0", result.canonical_after)
    except Exception as e:
        report.add_fail(f"{label}: convert/import raised {e}")
        return
    # Capture in-memory party[0] before writing to disk
    pre = tgt.list_party()[0]

    # Persist to a temp file, then reload from disk
    with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as f:
        temp_path = Path(f.name)
    try:
        tgt.save(temp_path)
        if not temp_path.exists() or temp_path.stat().st_size == 0:
            report.add_fail(f"{label}: temp .sav not written")
            return
        reloaded = tgt_parser_cls()
        reloaded.load(temp_path)
        post = reloaded.list_party()[0]
        # Compare a stable set of fields
        diffs = []
        for field in ("species_id", "level", "trainer_id", "nickname", "ot_name"):
            if getattr(pre, field) != getattr(post, field):
                diffs.append(f"{field}: {getattr(pre, field)!r} → {getattr(post, field)!r}")
        if diffs:
            report.add_fail(f"{label}: post-reload mismatches: {'; '.join(diffs)}")
        else:
            report.add_pass()
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def run() -> BatteryReport:
    report = BatteryReport(name="G: disk persistence + checksum")
    # Pick a representative set of routes & saves
    src_g1 = _fresh(Gen1Parser, TEST_SAVES_ROOT / "gen 1" / "Pokémon - Red Version.sav")
    src_g2 = _fresh(Gen2Parser, TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav")
    src_g3 = _fresh(Gen3Parser, TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav")
    tgt_g2 = TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav"
    tgt_g3 = TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav"

    _do_one(src_g1, Gen2Parser, tgt_g2, Gen1ToGen2Converter, "G1→G2 (Red→Crystal)", report)
    _do_one(src_g2, Gen3Parser, tgt_g3, Gen2ToGen3Converter, "G2→G3 (Crystal→Emerald)", report)
    _do_one(src_g3, Gen2Parser, tgt_g2, Gen3ToGen2Converter, "G3→G2 (Emerald→Crystal)", report)

    return report
