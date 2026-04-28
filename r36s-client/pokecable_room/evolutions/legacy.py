from __future__ import annotations

from dataclasses import dataclass
import warnings

from pokecable_room.canonical import CanonicalPokemon

from .engine import preview_trade_evolution


@dataclass(slots=True)
class EvolutionContext:
    source_generation: int
    target_generation: int
    trade_mode: str
    item_based_evolutions_enabled: bool = False


def trade_evolution_target(species_id: int, context: EvolutionContext, held_item_id: int | None = None) -> int | None:
    result = preview_trade_evolution(
        context.target_generation,
        species_id,
        held_item_id=held_item_id,
        item_based_evolutions_enabled=context.item_based_evolutions_enabled,
    )
    return result.target_species_id if result.evolved else None


def apply_trade_evolution(pokemon: CanonicalPokemon, context: EvolutionContext) -> CanonicalPokemon:
    warnings.warn(
        "Nao usar para edicao real de save. Esta funcao altera apenas CanonicalPokemon; "
        "use apply_trade_evolution_to_parser para aplicar evolucao no parser local.",
        DeprecationWarning,
        stacklevel=2,
    )
    target = trade_evolution_target(
        pokemon.species_national_id,
        context,
        pokemon.held_item.item_id if pokemon.held_item is not None else None,
    )
    if target is None:
        return pokemon
    pokemon.species_national_id = target
    pokemon.metadata["trade_evolution_applied"] = True
    pokemon.metadata["trade_evolution_context"] = {
        "source_generation": context.source_generation,
        "target_generation": context.target_generation,
        "trade_mode": context.trade_mode,
    }
    return pokemon
