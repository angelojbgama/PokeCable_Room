"""Battery E: export_payload → JSON dumps/loads → from_dict → canonical preserved end-to-end."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import importlib.util
_spec = importlib.util.spec_from_file_location("pokecable_save", REPO_ROOT / "pokecable_save.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["pokecable_save"] = _mod
_spec.loader.exec_module(_mod)
load_save = _mod.load_save

from canonical import CanonicalPokemon  # noqa: E402
from parsers.base import PokemonPayload  # noqa: E402

from .report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def _crit_fields(can: CanonicalPokemon) -> dict:
    """Return a dict of canonical fields we must preserve through JSON roundtrip."""
    return {
        "species_national_id": can.species_national_id,
        "level": can.level,
        "trainer_id": can.trainer_id & 0xFFFF,
        "nickname": can.nickname,
        "ot_name": can.ot_name,
        "moves": [(m.move_id, m.pp, m.pp_ups) for m in can.moves],
        "held_item_id": can.held_item.item_id if can.held_item else None,
        "ivs_atk": can.ivs.attack if can.ivs else None,
        "evs_atk": can.evs.attack if can.evs else None,
        "is_shiny": bool(can.metadata.get("is_shiny")),
        "gender": can.metadata.get("gender"),
        "unown_form": can.metadata.get("unown_form"),
    }


def run() -> BatteryReport:
    report = BatteryReport(name="E: LAN payload JSON roundtrip")
    cases = [
        ("gen 1", "Pokémon - Red Version.sav"),
        ("gen 2", "Pokémon - Crystal Version.sav"),
        ("gen 2", "Pokémon - Gold Version.sav"),
        ("gen 3", "Pokémon - Emerald Version.sav"),
        ("gen 3", "Pokémon - FireRed Version.sav"),
    ]
    for sub, name in cases:
        path = TEST_SAVES_ROOT / sub / name
        try:
            save = load_save(path)
        except Exception as exc:
            report.add_fail(f"{name}: load_save raised {exc}")
            continue
        if not save.party:
            report.note(f"skip {name}: empty party")
            continue
        location = "party:0"
        try:
            payload = save.export_payload(location)
        except Exception as exc:
            report.add_fail(f"{name}: export_payload raised {exc}")
            continue

        # JSON round trip
        try:
            json_blob = json.dumps(payload)
            decoded_dict = json.loads(json_blob)
        except Exception as exc:
            report.add_fail(f"{name}: JSON round trip raised {exc}")
            continue

        try:
            pp = PokemonPayload.from_dict(decoded_dict)
        except Exception as exc:
            report.add_fail(f"{name}: PokemonPayload.from_dict raised {exc}")
            continue

        # Critical scalar checks
        if pp.trainer_id & 0xFFFF != int(payload["trainer_id"]) & 0xFFFF:
            report.add_fail(f"{name}: TID lost in JSON roundtrip")
            continue
        if (pp.metadata or {}).get("gender") != (payload.get("metadata") or {}).get("gender"):
            report.add_fail(f"{name}: gender lost in JSON roundtrip (top metadata)")
            continue

        # canonical block JSON roundtrip
        if not pp.canonical:
            report.add_fail(f"{name}: PokemonPayload.canonical empty after roundtrip")
            continue
        try:
            can_from_payload = CanonicalPokemon.from_dict(pp.canonical)
        except Exception as exc:
            report.add_fail(f"{name}: CanonicalPokemon.from_dict raised {exc}")
            continue

        original_canonical = CanonicalPokemon.from_dict(payload["canonical"])
        before = _crit_fields(original_canonical)
        after = _crit_fields(can_from_payload)
        diffs = {k: (before[k], after[k]) for k in before if before[k] != after[k]}
        if diffs:
            report.add_fail(f"{name}: canonical fields differ after roundtrip: {diffs}")
        else:
            report.add_pass()
            report.note(f"OK  {name}")
    return report
