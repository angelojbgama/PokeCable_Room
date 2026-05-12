import requests
import json
import os
import sys

def fetch_pokemon_data(pokemon_id):
    print(f"Fetching data for Pokemon #{pokemon_id}...", file=sys.stderr)
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        stats = {}
        for stat in data["stats"]:
            stat_name = stat["stat"]["name"]
            name_map = {
                "hp": "hp",
                "attack": "atk",
                "defense": "def",
                "special-attack": "spa",
                "special-defense": "spd",
                "speed": "spe"
            }
            mapped_name = name_map.get(stat_name, stat_name)
            stats[mapped_name] = stat["base_stat"]
            
        types = [t["type"]["name"] for t in sorted(data["types"], key=lambda x: x["slot"])]
        
        return {
            "stats": stats,
            "types": types
        }
    except Exception as e:
        print(f"Error fetching Pokemon #{pokemon_id}: {e}", file=sys.stderr)
        return None

def main():
    all_data = {}
    for i in range(1, 387): # Gen 1-3
        data = fetch_pokemon_data(i)
        if data:
            all_data[i] = data
            
    backend_path = "PokeCable/backend/pokecable_room/data/base_stats.py"
    os.makedirs(os.path.dirname(backend_path), exist_ok=True)
    with open(backend_path, "w", encoding="utf-8") as f:
        f.write("from __future__ import annotations\n\n")
        f.write("from typing import Any\n\n")
        f.write("# Mapeamento national_dex_id -> { stats: dict, types: list }\n")
        f.write("BASE_STATS: dict[int, dict[str, Any]] = {\n")
        for pkmn_id, data in sorted(all_data.items()):
            f.write(f"    {pkmn_id}: {repr(data)},\n")
        f.write("}\n\n")
        f.write("def get_base_stats(national_dex_id: int) -> dict[str, Any] | None:\n")
        f.write("    return BASE_STATS.get(int(national_dex_id))\n")

    print(f"Successfully generated {backend_path}")

if __name__ == "__main__":
    main()
