import requests
import json
import os
import sys

# Mapeamento de grupos de versoes da PokeAPI para as Geracoes do PokeCable
VERSION_GROUPS = {
    1: ["red-blue", "yellow"],
    2: ["gold-silver", "crystal"],
    3: ["ruby-sapphire", "emerald", "firered-leafgreen"]
}

def fetch_pokemon_moves(pokemon_id):
    print(f"Fetching moves for Pokemon #{pokemon_id}...", file=sys.stderr)
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Estrutura: { gen: set(move_ids) }
        learnsets = {1: set(), 2: set(), 3: set()}
        
        for move_entry in data["moves"]:
            move_url = move_entry["move"]["url"]
            move_id = int(move_url.split("/")[-2])
            
            for version_details in move_entry["version_group_details"]:
                group_name = version_details["version_group"]["name"]
                
                for gen, groups in VERSION_GROUPS.items():
                    if group_name in groups:
                        learnsets[gen].add(move_id)
        
        return learnsets
    except Exception as e:
        print(f"Error fetching Pokemon #{pokemon_id}: {e}", file=sys.stderr)
        return None

def main():
    all_learnsets = {} # (gen, national_id) -> list[move_id]
    
    # Vamos processar do 1 ao 386 (Deoxys)
    for i in range(1, 387):
        learnsets = fetch_pokemon_moves(i)
        if learnsets:
            for gen, moves in learnsets.items():
                if moves:
                    all_learnsets[f"{gen}-{i}"] = sorted(list(moves))
    
    # Gerar arquivo Python (Backend)
    backend_path = "PokeCable/backend/pokecable_room/data/learnsets.py"
    os.makedirs(os.path.dirname(backend_path), exist_ok=True)
    with open(backend_path, "w", encoding="utf-8") as f:
        f.write("from __future__ import annotations\n\n")
        f.write("# Mapeamento (generation, national_dex_id) -> list[move_id]\n")
        f.write("LEARNSETS: dict[tuple[int, int], list[int]] = {\n")
        for key, moves in sorted(all_learnsets.items()):
            gen, national_id = key.split("-")
            f.write(f"    ({gen}, {national_id}): {moves},\n")
        f.write("}\n\n")
        f.write("def get_learnable_moves(generation: int, national_dex_id: int) -> list[int]:\n")
        f.write("    return LEARNSETS.get((int(generation), int(national_dex_id)), [])\n")

    # Gerar arquivo JS (Frontend)
    frontend_path = "PokeCable/frontend/learnsets.js"
    with open(frontend_path, "w", encoding="utf-8") as f:
        f.write("// Mapeamento \"gen-id\": [move_ids]\n")
        f.write("window.POKECABLE_LEARNSETS = ")
        json.dump(all_learnsets, f, indent=2)
        f.write(";\n")

    print(f"Successfully generated {backend_path} and {frontend_path}")

if __name__ == "__main__":
    main()
