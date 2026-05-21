"""Fixtures: parser bootstrap, holdable items, route/policy constants."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME_PATH = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME_PATH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402
from data.item_catalog import GEN2_ITEMS_BY_ID, GEN3_ITEMS_BY_ID  # noqa: E402
from data.item_transfer_policy import NON_HOLDABLE_CATEGORIES  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"

ROUTES: list[tuple[int, int]] = [(1, 2), (2, 1), (1, 3), (2, 3), (3, 1), (3, 2)]
POLICIES: list[str] = ["auto_retrocompat", "strict"]

_PARSERS: dict[int, Any] = {}


def load_parsers() -> dict[int, Any]:
    """Load and cache one parser instance per generation, backed by a real test save.

    `build_party_mon_from_canonical` is a pure function once the parser layout
    is initialized — it never writes to disk in our stress test.
    """
    if _PARSERS:
        return _PARSERS
    targets = {
        1: TEST_SAVES_ROOT / "gen 1" / "Pokémon - Red Version.sav",
        2: TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav",
        3: TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav",
    }
    classes = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser}
    for gen, path in targets.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing test save for gen {gen}: {path}")
        parser = classes[gen]()
        parser.load(path)
        _PARSERS[gen] = parser
    return _PARSERS


def holdable_items(gen: int) -> list[int]:
    """Return a sorted list of item IDs that can be held by a Pokémon."""
    catalog = {2: GEN2_ITEMS_BY_ID, 3: GEN3_ITEMS_BY_ID}.get(int(gen))
    if not catalog:
        return []
    return sorted(
        item_id
        for item_id, entry in catalog.items()
        if (entry.category or "").lower() not in NON_HOLDABLE_CATEGORIES and item_id > 0
    )


def representative_held_item(gen: int) -> int | None:
    """Return a stable single item id we use whenever we need 'some holdable item'."""
    items = holdable_items(gen)
    return items[0] if items else None
