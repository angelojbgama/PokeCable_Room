from __future__ import annotations

from dataclasses import dataclass
import warnings

from pokecable_room.canonical import CanonicalPokemon

from .rules import (
    MAX_SPECIES_BY_GENERATION,
    TradeEvolutionResult,
    TradeEvolutionRule,
    item_trade_rules_for_generation,
    simple_trade_rules_for_generation,
)


@dataclass(slots=True)
class EvolutionContext:
    source_generation: int
    target_generation: int
    trade_mode: str
    item_based_evolutions_enabled: bool = False


def preview_trade_evolution_for_parser(
    parser,
    location: str,
    item_based_evolutions_enabled: bool = False,
) -> TradeEvolutionResult:
    generation = int(parser.get_generation())
    species_id = int(parser.get_species_id(location))
    rule = _find_simple_rule(generation, species_id)
    if rule is not None:
        return _result_from_rule(rule, consumed_item_id=None, evolved=True, reason="simple_trade_evolution")
    if item_based_evolutions_enabled:
        held_item_id = parser.get_held_item_id(location)
        item_rule = _find_item_rule(generation, species_id, held_item_id)
        if item_rule is not None:
            return _result_from_rule(
                item_rule,
                consumed_item_id=held_item_id,
                evolved=True,
                reason="item_trade_evolution",
            )
        if any(rule.source_species_id == species_id for rule in item_trade_rules_for_generation(generation)):
            return _not_evolved(species_id, reason="item_trade_evolution_rule_has_no_validated_item_id")
    return _not_evolved(species_id, reason="no_trade_evolution_rule")


def apply_trade_evolution_to_parser(
    parser,
    location: str,
    item_based_evolutions_enabled: bool = False,
) -> TradeEvolutionResult:
    result = preview_trade_evolution_for_parser(
        parser,
        location,
        item_based_evolutions_enabled=item_based_evolutions_enabled,
    )
    if not result.evolved:
        return result
    parser.set_species_id(location, result.target_species_id)
    if item_based_evolutions_enabled and result.consumed_item_id is not None:
        parser.clear_held_item(location)
    return result


def preview_trade_evolution(
    generation: int,
    species_id: int,
    held_item_id: int | None = None,
    item_based_evolutions_enabled: bool = False,
) -> TradeEvolutionResult:
    generation = int(generation)
    species_id = int(species_id)
    rule = _find_simple_rule(generation, species_id)
    if rule is not None:
        return _result_from_rule(rule, consumed_item_id=None, evolved=True, reason="simple_trade_evolution")
    if item_based_evolutions_enabled:
        item_rule = _find_item_rule(generation, species_id, held_item_id)
        if item_rule is not None:
            return _result_from_rule(
                item_rule,
                consumed_item_id=held_item_id,
                evolved=True,
                reason="item_trade_evolution",
            )
    return _not_evolved(species_id, reason="no_trade_evolution_rule")


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
        "apply_trade_evolution mutates only CanonicalPokemon and does not update save raw data; "
        "use apply_trade_evolution_to_parser for real save edits.",
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


def _find_simple_rule(generation: int, species_id: int) -> TradeEvolutionRule | None:
    for rule in simple_trade_rules_for_generation(generation):
        if rule.source_species_id == species_id and _species_exists(rule.target_species_id, generation):
            return rule
    return None


def _find_item_rule(generation: int, species_id: int, held_item_id: int | None) -> TradeEvolutionRule | None:
    if held_item_id is None:
        return None
    for rule in item_trade_rules_for_generation(generation):
        if rule.source_species_id != species_id:
            continue
        if rule.required_item_id is None:
            continue
        if rule.required_item_id == held_item_id and _species_exists(rule.target_species_id, generation):
            return rule
    return None


def _result_from_rule(
    rule: TradeEvolutionRule,
    *,
    consumed_item_id: int | None,
    evolved: bool,
    reason: str,
) -> TradeEvolutionResult:
    return TradeEvolutionResult(
        evolved=evolved,
        source_species_id=rule.source_species_id,
        target_species_id=rule.target_species_id,
        source_name=rule.source_name,
        target_name=rule.target_name,
        consumed_item_id=consumed_item_id if rule.consume_item else None,
        consumed_item_name=rule.required_item_name if consumed_item_id is not None and rule.consume_item else None,
        reason=reason,
    )


def _not_evolved(species_id: int, *, reason: str) -> TradeEvolutionResult:
    return TradeEvolutionResult(
        evolved=False,
        source_species_id=species_id,
        target_species_id=species_id,
        source_name=f"Species #{species_id}",
        target_name=f"Species #{species_id}",
        reason=reason,
    )


def _species_exists(species_id: int, generation: int) -> bool:
    return 1 <= int(species_id) <= MAX_SPECIES_BY_GENERATION[int(generation)]
