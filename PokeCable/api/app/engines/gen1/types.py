from __future__ import annotations

# Matriz de Efetividade Gen 1 (15 tipos)
# TYPE_CHART_GEN1[Ataque][Defesa] -> Multiplicador
TYPE_CHART_GEN1: dict[str, dict[str, float]] = {
    "normal": {"rock": 0.5, "ghost": 0.0},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5},
    "water": {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass": {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5},
    "ice": {"fire": 1.0, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0},
    "fighting": {"normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0},
    "poison": {"grass": 2.0, "poison": 0.5, "ground": 0.5, "bug": 2.0, "rock": 0.5, "ghost": 0.5},
    "ground": {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0},
    "flying": {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5},
    "psychic": {"fighting": 2.0, "poison": 2.0, "psychic": 0.5},
    "bug": {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 2.0, "flying": 0.5, "psychic": 2.0, "ghost": 0.5},
    "rock": {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0},
    "ghost": {"normal": 0.0, "psychic": 0.0, "ghost": 2.0}, # Bug da Gen 1: Ghost nao afeta Psychic
    "dragon": {"dragon": 2.0}
}

def get_type_multiplier_gen1(attack_type: str, defender_types: list[str]) -> float:
    multiplier = 1.0
    atk = attack_type.lower()
    
    if atk not in TYPE_CHART_GEN1:
        return 1.0
        
    for def_type in defender_types:
        def_t = def_type.lower()
        multiplier *= TYPE_CHART_GEN1[atk].get(def_t, 1.0)
        
    return multiplier

def is_special_type_gen1(type_name: str) -> bool:
    special_types = {
        "fire", "water", "electric", "grass", "ice", "psychic", "dragon"
    }
    return type_name.lower() in special_types
