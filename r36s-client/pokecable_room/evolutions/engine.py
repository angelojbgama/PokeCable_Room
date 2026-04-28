from __future__ import annotations

from .rules import (
    TradeEvolutionResult,
    TradeEvolutionRule,
    item_trade_rules_for_generation,
    simple_trade_rules_for_generation,
    species_exists_in_native_generation,
)


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
    if _find_simple_candidate(generation, species_id) is not None:
        return _not_evolved(species_id, reason="target_species_not_supported")
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
        if _find_item_candidate_for_item(generation, species_id, held_item_id) is not None:
            return _not_evolved(species_id, reason="target_species_not_supported")
        if any(rule.source_species_id == species_id for rule in item_trade_rules_for_generation(generation)):
            return _not_evolved(species_id, reason="wrong_held_item")
    elif any(rule.source_species_id == species_id for rule in item_trade_rules_for_generation(generation)):
        return _not_evolved(species_id, reason="item_trade_evolution_disabled")
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
    if _find_simple_candidate(generation, species_id) is not None:
        return _not_evolved(species_id, reason="target_species_not_supported")
    if item_based_evolutions_enabled:
        item_rule = _find_item_rule(generation, species_id, held_item_id)
        if item_rule is not None:
            return _result_from_rule(
                item_rule,
                consumed_item_id=held_item_id,
                evolved=True,
                reason="item_trade_evolution",
            )
        if _find_item_candidate_for_item(generation, species_id, held_item_id) is not None:
            return _not_evolved(species_id, reason="target_species_not_supported")
        if any(rule.source_species_id == species_id for rule in item_trade_rules_for_generation(generation)):
            return _not_evolved(species_id, reason="wrong_held_item")
    elif any(rule.source_species_id == species_id for rule in item_trade_rules_for_generation(generation)):
        return _not_evolved(species_id, reason="item_trade_evolution_disabled")
    return _not_evolved(species_id, reason="no_trade_evolution_rule")


def _find_simple_rule(generation: int, species_id: int) -> TradeEvolutionRule | None:
    rule = _find_simple_candidate(generation, species_id)
    if rule is None:
        return None
    if not species_exists_in_native_generation(generation, rule.target_species_id):
        return None
    return rule


def _find_simple_candidate(generation: int, species_id: int) -> TradeEvolutionRule | None:
    for rule in simple_trade_rules_for_generation(generation):
        if rule.source_species_id != species_id:
            continue
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
        if rule.required_item_id == held_item_id and species_exists_in_native_generation(generation, rule.target_species_id):
            return rule
    return None


def _find_item_candidate_for_item(generation: int, species_id: int, held_item_id: int | None) -> TradeEvolutionRule | None:
    if held_item_id is None:
        return None
    for rule in item_trade_rules_for_generation(generation):
        if rule.source_species_id == species_id and rule.required_item_id == held_item_id:
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
