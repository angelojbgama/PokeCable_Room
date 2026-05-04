from __future__ import annotations

import math
import random
from typing import Any

# Multiplicadores de Natureza (Gen 3+)
# Natureza -> (Ataque, Defesa, Velocidade, Sp. Atk, Sp. Def)
# 1.1 = +10%, 0.9 = -10%, 1.0 = neutro
NATURE_MODIFIERS: dict[int, tuple[float, float, float, float, float]] = {
    0: (1.0, 1.0, 1.0, 1.0, 1.0),  # Hardy
    1: (1.1, 0.9, 1.0, 1.0, 1.0),  # Lonely
    2: (1.1, 1.0, 0.9, 1.0, 1.0),  # Brave
    3: (1.1, 1.0, 1.0, 0.9, 1.0),  # Adamant
    4: (1.1, 1.0, 1.0, 1.0, 0.9),  # Naughty
    5: (0.9, 1.1, 1.0, 1.0, 1.0),  # Bold
    6: (1.0, 1.0, 1.0, 1.0, 1.0),  # Docile
    7: (1.0, 1.1, 0.9, 1.0, 1.0),  # Relaxed
    8: (1.0, 1.1, 1.0, 0.9, 1.0),  # Impish
    9: (1.0, 1.1, 1.0, 1.0, 0.9),  # Lax
    10: (0.9, 1.0, 1.1, 1.0, 1.0), # Timid
    11: (1.0, 0.9, 1.1, 1.0, 1.0), # Hasty
    12: (1.0, 1.0, 1.0, 1.0, 1.0), # Serious
    13: (1.0, 1.0, 1.1, 0.9, 1.0), # Jolly
    14: (1.0, 1.0, 1.1, 1.0, 0.9), # Naive
    15: (0.9, 1.0, 1.0, 1.1, 1.0), # Modest
    16: (1.0, 0.9, 1.0, 1.1, 1.0), # Mild
    17: (1.0, 1.0, 0.9, 1.1, 1.0), # Quiet
    18: (1.0, 1.0, 1.0, 1.0, 1.0), # Bashful
    19: (1.0, 1.0, 1.0, 1.1, 0.9), # Rash
    20: (0.9, 1.0, 1.0, 1.0, 1.1), # Calm
    21: (1.0, 0.9, 1.0, 1.0, 1.1), # Gentle
    22: (1.0, 1.0, 0.9, 1.0, 1.1), # Sassy
    23: (1.0, 1.0, 1.0, 0.9, 1.1), # Careful
    24: (1.0, 1.0, 1.0, 1.0, 1.0), # Quirky
}

def calculate_hp(base: int, iv: int, ev: int, level: int, national_id: int) -> int:
    """Calcula o HP real usando a formula da Gen 3."""
    if national_id == 292:  # Shedinja
        return 1
    
    # Formula: floor(((2 * Base + IV + floor(EV / 4)) * Level) / 100) + Level + 10
    return math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100) + level + 10

def calculate_other_stat(base: int, iv: int, ev: int, level: int, modifier: float) -> int:
    """Calcula stats (Atk, Def, Spe, SpA, SpD) usando a formula da Gen 3."""
    # Formula: floor((floor(((2 * Base + IV + floor(EV / 4)) * Level) / 100) + 5) * Modifier)
    stat_base = math.floor(((2 * base + iv + math.floor(ev / 4)) * level) / 100) + 5
    return math.floor(stat_base * modifier)

def get_nature_modifiers(personality: int) -> tuple[float, float, float, float, float]:
    """Retorna os multiplicadores baseados no ID da Personalidade."""
    nature_id = personality % 25
    return NATURE_MODIFIERS.get(nature_id, (1.0, 1.0, 1.0, 1.0, 1.0))

# Multiplicadores de Estágio de Stat (-6 a +6)
# HP nao tem estagio. Atk, Def, Spe, SpA, SpD usam esta tabela:
STAT_STAGE_MODIFIERS: dict[int, float] = {
    -6: 2/8, -5: 2/7, -4: 2/6, -3: 2/5, -2: 2/4, -1: 2/3,
    0: 2/2,
    1: 3/2, 2: 4/2, 3: 5/2, 4: 6/2, 5: 7/2, 6: 8/2
}

# Tabela especial para Accuracy e Evasion
ACCURACY_EVASION_STAGE_MODIFIERS: dict[int, float] = {
    -6: 3/9, -5: 3/8, -4: 3/7, -3: 3/6, -2: 3/5, -1: 3/4,
    0: 3/3,
    1: 4/3, 2: 5/3, 3: 6/3, 4: 7/3, 5: 8/3, 6: 9/3
}

# Tabela de chances de Crítico (Gen 3)
# Stage -> Probabilidade
CRIT_CHANCE_STAGES: dict[int, float] = {
    0: 1/16,
    1: 1/8,
    2: 1/4,
    3: 1/3,
    4: 1/2
}

def determine_critical(crit_stage: int) -> bool:
    """Determina se um golpe sera critico baseado no estagio de critico (0-4+)."""
    stage = max(0, min(4, crit_stage))
    chance = CRIT_CHANCE_STAGES[stage]
    return random.random() < chance

def calculate_hit(
    move_accuracy: int, 
    user_acc_stage: int, 
    target_eva_stage: int,
    user_level: int = 1,
    target_level: int = 1,
    is_ohko: bool = False
) -> bool:
    """
    Verifica se um golpe acertou baseado no RNG.
    Suporta a formula especial de OHKO (One-Hit KO) da Gen 3.
    """
    if move_accuracy <= 0:
        return True

    # Task 7.14: Formula OHKO
    if is_ohko:
        if user_level < target_level:
            return False
        # Accuracy = (UserLevel - TargetLevel) + 30
        chance = (user_level - target_level) + 30
    else:
        # Formula Normal
        stage_diff = user_acc_stage - target_eva_stage
        stage_diff = max(-6, min(6, stage_diff))
        chance = move_accuracy * ACCURACY_EVASION_STAGE_MODIFIERS[stage_diff]
    
    return random.randint(1, 100) <= chance

