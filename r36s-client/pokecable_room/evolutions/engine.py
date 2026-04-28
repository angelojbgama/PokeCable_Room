from __future__ import annotations

from dataclasses import dataclass

from pokecable_room.canonical import CanonicalPokemon

from .rules import MAX_SPECIES_BY_GENERATION, SIMPLE_TRADE_EVOLUTIONS


@dataclass(slots=True)
class EvolutionContext:
    source_generation: int
    target_generation: int
    trade_mode: str
    item_based_evolutions_enabled: bool = False


def trade_evolution_target(species_id: int, context: EvolutionContext, held_item_id: int | None = None) -> int | None:
    simple_target = SIMPLE_TRADE_EVOLUTIONS.get(context.target_generation, {}).get(int(species_id))
    if simple_target is not None and _species_exists(simple_target, context.target_generation):
        return simple_target
    if held_item_id is not None and context.item_based_evolutions_enabled:
        # Item IDs differ by generation and game. Keep this disabled until each ID table is tested.
        return None
    return None


def apply_trade_evolution(pokemon: CanonicalPokemon, context: EvolutionContext) -> CanonicalPokemon:
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


def _species_exists(species_id: int, generation: int) -> bool:
    return 1 <= int(species_id) <= MAX_SPECIES_BY_GENERATION[int(generation)]
