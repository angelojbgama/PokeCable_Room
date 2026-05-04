from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .battle_pokemon import BattlePokemon, BattleMove

def apply_ability_immunities(move: BattleMove, defender: BattlePokemon, type_multiplier: float) -> float | None:
    """
    Retorna o novo multiplicador de dano se a habilidade conferir imunidade.
    Retorna None se a habilidade nao afetar este golpe.
    """
    ability = defender.ability
    move_type = move.type
    
    if not ability:
        return None
        
    # Gen 3 Immunities
    if ability == "levitate" and move_type == "ground":
        return 0.0
        
    if ability == "flash-fire" and move_type == "fire":
        return 0.0
        
    if ability == "water-absorb" and move_type == "water":
        return 0.0
        
    if ability == "volt-absorb" and move_type == "electric":
        return 0.0
        
    if ability == "wonder-guard" and move.power > 0:
        # Imune a tudo que NAO seja Super Effective
        if type_multiplier <= 1.0:
            return 0.0

    return None
