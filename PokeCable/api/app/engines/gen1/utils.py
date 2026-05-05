from __future__ import annotations
import random
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PokemonGen1

def determine_critical_gen1(base_speed: int, is_high_crit: bool = False, focus_energy: bool = False) -> bool:
    """
    Determina se um golpe sera critico na Gen 1.
    Formula: P = BaseSpeed * Multiplier / 512
    Multiplier: 8 para moves de alto critico, 1 para normais.
    """
    multiplier = 8.0 if is_high_crit else 1.0
    chance = (base_speed * multiplier) / 512.0
    if chance > 0.996:
        chance = 0.996
    if focus_energy:
        # Gen 1 bug: Focus Energy worsens critical hit odds instead of improving them.
        chance /= 4.0
        
    return random.random() < chance

def calculate_hit_gen1(accuracy: int | None, user_acc_stage: int, target_eva_stage: int) -> bool:
    """
    Verifica se um golpe acertou na Gen 1.
    Inclui o famoso glitch do 1/256 (exceto para Swift).
    """
    if accuracy is None or accuracy == 0: # Moves que nao erram (Swift) ou nao usam accuracy
        return True
        
    # Multiplicadores de stage Gen 1
    # stages: -6 a 6 -> 25/100 a 300/100
    modifiers = {
        -6: 0.25, -5: 0.28, -4: 0.33, -3: 0.40, -2: 0.50, -1: 0.66,
         0: 1.0,
         1: 1.5, 2: 2.0, 3: 2.5, 4: 3.0, 5: 3.5, 6: 4.0
    }
    
    stage_diff = user_acc_stage - target_eva_stage
    stage_diff = max(-6, min(6, stage_diff))
    
    # Probabilidade base (0-255)
    # Na Gen 1, a precisao e baseada em 255.
    # Se Prob >= RNG(0-255), entao errou? Nao, Showdown diz:
    # if (RNG < threshold) hit; threshold = accuracy * stage_mod * 255 / 100
    threshold = math.floor(accuracy * modifiers.get(stage_diff, 1.0) * 255 / 100)
    
    # O threshold e limitado a 255. 
    # O RNG vai de 0 a 255 inclusive.
    # Se o threshold for 255, e o RNG for 255, ele ERRA. (O glitch do 1/256)
    if threshold > 255: threshold = 255
    
    rng = random.randint(0, 255)
    return rng < threshold
