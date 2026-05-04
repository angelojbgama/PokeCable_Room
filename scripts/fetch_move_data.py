import requests
import json
import os
import sys

def fetch_move_data(move_id):
    print(f"Fetching data for Move #{move_id}...", file=sys.stderr)
    url = f"https://pokeapi.co/api/v2/move/{move_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        
        # Extrair efeito curto em ingles
        effect = ""
        for entry in data.get("effect_entries", []):
            if entry.get("language", {}).get("name") == "en":
                effect = entry.get("short_effect", "")
                break

        return {
            "name": data["name"],
            "type": data["type"]["name"],
            "power": data.get("power"),
            "accuracy": data.get("accuracy"),
            "pp": data.get("pp"),
            "priority": data.get("priority", 0),
            "damage_class": data["damage_class"]["name"],
            "effect_chance": data.get("effect_chance"),
            "effect": effect
        }
    except Exception as e:
        print(f"Error fetching Move #{move_id}: {e}", file=sys.stderr)
        return None

def main():
    all_moves = {}
    # Gen 1-3 vai ate o move 354 (Psycho Boost)
    for i in range(1, 355):
        data = fetch_move_data(i)
        if data:
            all_moves[i] = data
            
    backend_path = "PokeCable/backend/pokecable_room/data/move_combat_data.py"
    os.makedirs(os.path.dirname(backend_path), exist_ok=True)
    with open(backend_path, "w", encoding="utf-8") as f:
        f.write("from __future__ import annotations\n\n")
        f.write("from typing import Any\n\n")
        f.write("# Mapeamento move_id -> { name, type, power, accuracy, pp, priority, damage_class, effect_chance, effect }\n")
        f.write("MOVE_COMBAT_DATA: dict[int, dict[str, Any]] = {\n")
        for move_id, data in sorted(all_moves.items()):
            f.write(f"    {move_id}: {repr(data)},\n")
        f.write("}\n\n")
        f.write("def get_move_combat_data(move_id: int) -> dict[str, Any] | None:\n")
        f.write("    return MOVE_COMBAT_DATA.get(int(move_id))\n")

    print(f"Successfully generated {backend_path}")

if __name__ == "__main__":
    main()
