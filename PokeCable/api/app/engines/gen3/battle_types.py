from __future__ import annotations

# Matriz de Efetividade Gen 3 (17 tipos)
# TYPE_CHART[Ataque][Defesa] -> Multiplicador
TYPE_CHART: dict[str, dict[str, float]] = {
    "normal": {
        "rock": 0.5, "ghost": 0.0, "steel": 0.5
    },
    "fire": {
        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0
    },
    "water": {
        "fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5
    },
    "electric": {
        "water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5
    },
    "grass": {
        "fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5
    },
    "ice": {
        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5
    },
    "fighting": {
        "normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0, "dark": 2.0, "steel": 2.0
    },
    "poison": {
        "grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0
    },
    "ground": {
        "fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0
    },
    "flying": {
        "electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5
    },
    "psychic": {
        "fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5
    },
    "bug": {
        "fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5
    },
    "rock": {
        "fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5
    },
    "ghost": {
        "normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "steel": 0.5
    },
    "dragon": {
        "dragon": 2.0, "steel": 0.5
    },
    "dark": {
        "fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "steel": 0.5
    },
    "steel": {
        "fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "steel": 0.5
    }
}

# Matriz de Efetividade Gen 1 (15 tipos)
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

def get_type_multiplier(attack_type: str, defender_types: list[str], generation: int = 3) -> float:
    """Calcula o multiplicador de dano total contra um Pokemon (incluindo tipos duplos)."""
    multiplier = 1.0
    atk = attack_type.lower()
    
    chart = TYPE_CHART if generation >= 2 else TYPE_CHART_GEN1
    
    if atk not in chart:
        return 1.0
        
    for def_type in defender_types:
        def_t = def_type.lower()
        multiplier *= chart[atk].get(def_t, 1.0)
        
    return multiplier

def is_special_type(type_name: str, generation: int = 3) -> bool:
    """Na Gen 1-3, a classe do golpe (Physical/Special) e determinada pelo Tipo."""
    special_types = {
        "fire", "water", "electric", "grass", "ice", "psychic", "dragon"
    }
    if generation >= 2:
        special_types.add("dark")
        
    return type_name.lower() in special_types
