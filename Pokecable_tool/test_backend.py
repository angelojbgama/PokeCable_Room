#!/usr/bin/env python3
"""
Local smoke test for the R36S PokeCable save parser.

Kept under the original filename so existing shortcuts continue to work.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

from pokecable_save import SaveError, load_save


def test_local_save(save_file: str) -> bool:
    save_path = Path(save_file)
    if not save_path.exists():
        print(f"ERROR: Save file not found: {save_file}")
        return False

    print(f"\n{'=' * 60}")
    print("Local Save Test")
    print(f"{'=' * 60}")
    print(f"Save file:  {save_path.name}")
    print(f"Size:       {save_path.stat().st_size} bytes")
    print(f"{'=' * 60}\n")

    try:
        save = load_save(save_path)
    except SaveError as exc:
        print(f"ERROR: {exc}")
        return False

    print(f"✓ Generation: {save.generation}")
    print(f"✓ Game: {save.game}")
    print(f"✓ Label: {save.label}")
    print(f"✓ Player: {save.player_name}")
    print(f"✓ Party Pokémon: {len(save.party)}")
    print(f"✓ PC/Boxes Pokémon: {len(save.boxes)}")

    if not save.party:
        print("ERROR: Save carregou, mas a party está vazia.")
        return False

    first = save.party[0]
    print("\n[First Party Pokémon]")
    print(f"  - {first.get('display_summary')}")
    print(f"  - Location: {first.get('location')}")

    payload = save.export_payload(first["location"])
    raw_b64 = payload.get("raw_data_base64", "")
    raw_len = len(base64.b64decode(raw_b64)) if raw_b64 else 0

    print("\n[Export Payload]")
    print(f"  - Format: {payload.get('raw', {}).get('format')}")
    print(f"  - Raw bytes: {raw_len}")
    print(f"  - Species: {payload.get('species_name')}")
    print(f"  - Nickname: {payload.get('nickname')}")
    print(f"  - Level: {payload.get('level')}")

    if save.boxes:
        first_box = save.boxes[0]
        print("\n[First PC Pokémon]")
        print(f"  - {first_box.get('display_summary')}")
        print(f"  - Location: {first_box.get('location')}")
        print(f"  - Box: {first_box.get('box_name')}")
        box_payload = save.export_payload(first_box["location"])
        box_raw_b64 = box_payload.get("raw_data_base64", "")
        box_raw_len = len(base64.b64decode(box_raw_b64)) if box_raw_b64 else 0
        print("\n[Export PC Payload]")
        print(f"  - Format: {box_payload.get('raw', {}).get('format')}")
        print(f"  - Raw bytes: {box_raw_len}")
        print(f"  - Species: {box_payload.get('species_name')}")
        print(f"  - Nickname: {box_payload.get('nickname')}")
        print(f"  - Level: {box_payload.get('level')}")

    print(f"\n{'=' * 60}")
    print("✓ Parser local está funcionando corretamente.")
    print(f"{'=' * 60}\n")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 test_backend.py <save_file>")
        sys.exit(1)

    ok = test_local_save(sys.argv[1])
    sys.exit(0 if ok else 1)
