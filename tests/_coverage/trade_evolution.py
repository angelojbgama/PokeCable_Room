"""Battery I: trade evolution preview + apply per known case."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from data.species import national_to_native  # noqa: E402
from evolutions.engine import preview_trade_evolution  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

# Canonical trade evolutions (national dex IDs)
SIMPLE_CASES = [
    # (name, gen, src_native_id, expected_target_native_id)
    ("Kadabra→Alakazam G1", 1, national_to_native(1, 64), national_to_native(1, 65)),
    ("Machoke→Machamp G1", 1, national_to_native(1, 67), national_to_native(1, 68)),
    ("Graveler→Golem G1", 1, national_to_native(1, 75), national_to_native(1, 76)),
    ("Haunter→Gengar G1", 1, national_to_native(1, 93), national_to_native(1, 94)),
    ("Kadabra→Alakazam G2", 2, 64, 65),
    ("Machoke→Machamp G2", 2, 67, 68),
    ("Graveler→Golem G2", 2, 75, 76),
    ("Haunter→Gengar G2", 2, 93, 94),
    ("Kadabra→Alakazam G3", 3, national_to_native(3, 64), national_to_native(3, 65)),
]

# Held-item trade evolutions (Gen 2/3 only)
# (name, gen, src_native_id, item_id, expected_target_native_id)
# Gen 2 item IDs (from item_catalog.py): KingsRock=82, MetalCoat=143, DragonScale=151, UpGrade=172.
# Gen 3 item IDs: KingsRock=187, MetalCoat=199, DragonScale=201, UpGrade=218.
ITEM_CASES = [
    ("Onix+Metal Coat→Steelix G2", 2, 95, 143, 208),
    ("Scyther+Metal Coat→Scizor G2", 2, 123, 143, 212),
    ("Poliwhirl+King's Rock→Politoed G2", 2, 61, 82, 186),
    ("Slowpoke+King's Rock→Slowking G2", 2, 79, 82, 199),
    ("Seadra+Dragon Scale→Kingdra G2", 2, 117, 151, 230),
    ("Porygon+Up-Grade→Porygon2 G2", 2, 137, 172, 233),
]


def run() -> BatteryReport:
    report = BatteryReport(name="I: trade evolution")
    # Simple (no held item)
    for label, gen, src_native, exp_target_native in SIMPLE_CASES:
        result = preview_trade_evolution(gen, src_native, held_item_id=None)
        if not result.evolved:
            report.add_fail(f"{label}: not evolved (reason={result.reason})")
            continue
        if result.target_species_id != exp_target_native:
            report.add_fail(f"{label}: expected target {exp_target_native}, got {result.target_species_id}")
            continue
        report.add_pass()

    # Held item
    for label, gen, src_native, item_id, exp_target_native in ITEM_CASES:
        result = preview_trade_evolution(gen, src_native, held_item_id=item_id)
        if not result.evolved:
            report.add_fail(f"{label}: not evolved (reason={result.reason})")
            continue
        if result.target_species_id != exp_target_native:
            report.add_fail(f"{label}: expected target {exp_target_native}, got {result.target_species_id}")
            continue
        report.add_pass()

    # Negative case: Pikachu does not evolve by trade
    result = preview_trade_evolution(1, national_to_native(1, 25), held_item_id=None)
    if result.evolved:
        report.add_fail("Pikachu must NOT evolve by trade")
    else:
        report.add_pass()

    return report
