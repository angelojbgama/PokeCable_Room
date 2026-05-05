from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from ..gen1.models import PokemonGen1, BattleMoveGen1, BattleStatsGen1, calc_gen1_stat

@dataclass
class BattleStatsGen2:
    hp: int
    atk: int
    defen: int
    spa: int
    spd: int
    spe: int

@dataclass
class PokemonGen2(PokemonGen1):
    stats_gen2: BattleStatsGen2
    held_item: Any | None = None

    @classmethod
    def from_canonical(cls, canonical: dict[str, Any]) -> PokemonGen2:
        pkmn_gen1 = super().from_canonical(canonical)

        # Na Gen 2, os stats sao calculados de forma similar a Gen 1,
        # mas com a divisao de Special.
        # Para retrocompatibilidade, o DV e Stat Exp de Special sao copiados para ambos.
        base_stats = pkmn_gen1.base_stats
        dvs = pkmn_gen1.dvs
        stat_exp = pkmn_gen1.stat_exp

        stats_gen2 = BattleStatsGen2(
            hp=pkmn_gen1.stats.hp,
            atk=pkmn_gen1.stats.atk,
            defen=pkmn_gen1.stats.defen,
            spe=pkmn_gen1.stats.spe,
            spa=calc_gen1_stat(base_stats["spa"], dvs["spc"], stat_exp["spc"], pkmn_gen1.level),
            spd=calc_gen1_stat(base_stats["spd"], dvs["spc"], stat_exp["spc"], pkmn_gen1.level),
        )
        
        # Construtor da PkmnGen2
        instance = cls(**pkmn_gen1.__dict__)
        instance.stats_gen2 = stats_gen2
        
        # TODO: Adicionar logica de Held Item a partir do canonical
        
        return instance
