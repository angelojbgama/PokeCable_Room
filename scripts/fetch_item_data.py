import requests
import json
import os
import sys

ITEM_NAMES = [
    "leftovers", "oran-berry", "lum-berry", "sitrus-berry", "silk-scarf", 
    "choice-band", "mystic-water", "charcoal", "magnet", "sharp-beak", 
    "silver-powder", "never-melt-ice", "black-belt", "poison-barb", 
    "soft-sand", "spell-tag", "dragon-fang", "black-glasses", "metal-coat"
]

ITEM_EFFECT_MAP = {
    "leftovers": {"effect_type": "heal_end_turn", "value": 0.0625},
    "oran-berry": {"effect_type": "heal_threshold", "value": 10, "threshold": 0.5},
    "sitrus-berry": {"effect_type": "heal_threshold", "value": 30, "threshold": 0.5},
    "lum-berry": {"effect_type": "cure_status"},
    "choice-band": {"effect_type": "boost_stat", "stat": "atk", "value": 1.5},
    "silk-scarf": {"effect_type": "boost_type", "boost_type": "normal", "value": 1.1},
    "mystic-water": {"effect_type": "boost_type", "boost_type": "water", "value": 1.1},
    "charcoal": {"effect_type": "boost_type", "boost_type": "fire", "value": 1.1},
    "magnet": {"effect_type": "boost_type", "boost_type": "electric", "value": 1.1},
    "sharp-beak": {"effect_type": "boost_type", "boost_type": "flying", "value": 1.1},
    "silver-powder": {"effect_type": "boost_type", "boost_type": "bug", "value": 1.1},
    "never-melt-ice": {"effect_type": "boost_type", "boost_type": "ice", "value": 1.1},
    "black-belt": {"effect_type": "boost_type", "boost_type": "fighting", "value": 1.1},
    "poison-barb": {"effect_type": "boost_type", "boost_type": "poison", "value": 1.1},
    "soft-sand": {"effect_type": "boost_type", "boost_type": "ground", "value": 1.1},
    "spell-tag": {"effect_type": "boost_type", "boost_type": "ghost", "value": 1.1},
    "dragon-fang": {"effect_type": "boost_type", "boost_type": "dragon", "value": 1.1},
    "black-glasses": {"effect_type": "boost_type", "boost_type": "dark", "value": 1.1},
    "metal-coat": {"effect_type": "boost_type", "boost_type": "steel", "value": 1.1},
}

def fetch_item_data(item_name):
    print(f"Fetching data for Item '{item_name}'...", file=sys.stderr)
    url = f"https://pokeapi.co/api/v2/item/{item_name}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        
        item_id = data["id"]
        # Convert name from "silk-scarf" to "Silk Scarf"
        display_name = data["name"].replace("-", " ").title()
        
        effect_data = ITEM_EFFECT_MAP.get(item_name, {})
        
        result = {
            "name": display_name,
        }
        result.update(effect_data)
        
        return item_id, result
    except Exception as e:
        print(f"Error fetching Item '{item_name}': {e}", file=sys.stderr)
        return None

def main():
    battle_items = {}
    for name in ITEM_NAMES:
        res = fetch_item_data(name)
        if res:
            item_id, data = res
            battle_items[item_id] = data
            
    output_path = "PokeCable/api/app/data/battle_items.py"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("from __future__ import annotations\n\n")
        f.write("# Mapeamento item_id -> { name, effect_type, ... }\n")
        f.write("BATTLE_ITEMS: dict[int, dict] = {\n")
        for item_id in sorted(battle_items.keys()):
            f.write(f"    {item_id}: {json.dumps(battle_items[item_id])},\n")
        f.write("}\n")

    print(f"Successfully generated {output_path}")

if __name__ == "__main__":
    main()
