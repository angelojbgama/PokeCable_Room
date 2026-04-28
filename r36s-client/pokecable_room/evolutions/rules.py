from __future__ import annotations

from dataclasses import dataclass

from pokecable_room.data.items import ITEM_IDS_BY_GENERATION_AND_NAME


@dataclass(frozen=True, slots=True)
class TradeEvolutionRule:
    generation: int
    source_species_id: int
    target_species_id: int
    source_name: str
    target_name: str
    required_item_id: int | None = None
    required_item_name: str | None = None
    consume_item: bool = True


@dataclass(slots=True)
class TradeEvolutionResult:
    evolved: bool
    source_species_id: int
    target_species_id: int
    source_name: str
    target_name: str
    consumed_item_id: int | None = None
    consumed_item_name: str | None = None
    reason: str = ""


SIMPLE_TRADE_EVOLUTION_RULES: tuple[TradeEvolutionRule, ...] = (
    TradeEvolutionRule(1, 38, 149, "Kadabra", "Alakazam"),
    TradeEvolutionRule(1, 41, 126, "Machoke", "Machamp"),
    TradeEvolutionRule(1, 39, 49, "Graveler", "Golem"),
    TradeEvolutionRule(1, 147, 14, "Haunter", "Gengar"),
    TradeEvolutionRule(2, 64, 65, "Kadabra", "Alakazam"),
    TradeEvolutionRule(2, 67, 68, "Machoke", "Machamp"),
    TradeEvolutionRule(2, 75, 76, "Graveler", "Golem"),
    TradeEvolutionRule(2, 93, 94, "Haunter", "Gengar"),
    TradeEvolutionRule(3, 64, 65, "Kadabra", "Alakazam"),
    TradeEvolutionRule(3, 67, 68, "Machoke", "Machamp"),
    TradeEvolutionRule(3, 75, 76, "Graveler", "Golem"),
    TradeEvolutionRule(3, 93, 94, "Haunter", "Gengar"),
)


def _item_id(generation: int, name: str) -> int:
    return ITEM_IDS_BY_GENERATION_AND_NAME[(generation, name.lower())]


ITEM_TRADE_EVOLUTION_RULES: tuple[TradeEvolutionRule, ...] = (
    TradeEvolutionRule(2, 61, 186, "Poliwhirl", "Politoed", _item_id(2, "King's Rock"), "King's Rock"),
    TradeEvolutionRule(2, 79, 199, "Slowpoke", "Slowking", _item_id(2, "King's Rock"), "King's Rock"),
    TradeEvolutionRule(2, 95, 208, "Onix", "Steelix", _item_id(2, "Metal Coat"), "Metal Coat"),
    TradeEvolutionRule(2, 123, 212, "Scyther", "Scizor", _item_id(2, "Metal Coat"), "Metal Coat"),
    TradeEvolutionRule(2, 117, 230, "Seadra", "Kingdra", _item_id(2, "Dragon Scale"), "Dragon Scale"),
    TradeEvolutionRule(2, 137, 233, "Porygon", "Porygon2", _item_id(2, "Up-Grade"), "Up-Grade"),
    TradeEvolutionRule(3, 61, 186, "Poliwhirl", "Politoed", _item_id(3, "King's Rock"), "King's Rock"),
    TradeEvolutionRule(3, 79, 199, "Slowpoke", "Slowking", _item_id(3, "King's Rock"), "King's Rock"),
    TradeEvolutionRule(3, 95, 208, "Onix", "Steelix", _item_id(3, "Metal Coat"), "Metal Coat"),
    TradeEvolutionRule(3, 123, 212, "Scyther", "Scizor", _item_id(3, "Metal Coat"), "Metal Coat"),
    TradeEvolutionRule(3, 117, 230, "Seadra", "Kingdra", _item_id(3, "Dragon Scale"), "Dragon Scale"),
    TradeEvolutionRule(3, 137, 233, "Porygon", "Porygon2", _item_id(3, "Up-Grade"), "Up-Grade"),
    TradeEvolutionRule(3, 373, 374, "Clamperl", "Huntail", _item_id(3, "Deep Sea Tooth"), "Deep Sea Tooth"),
    TradeEvolutionRule(3, 373, 375, "Clamperl", "Gorebyss", _item_id(3, "Deep Sea Scale"), "Deep Sea Scale"),
)


MAX_SPECIES_BY_GENERATION = {1: 190, 2: 251, 3: 412}


def simple_trade_rules_for_generation(generation: int) -> tuple[TradeEvolutionRule, ...]:
    return tuple(rule for rule in SIMPLE_TRADE_EVOLUTION_RULES if rule.generation == int(generation))


def item_trade_rules_for_generation(generation: int) -> tuple[TradeEvolutionRule, ...]:
    return tuple(rule for rule in ITEM_TRADE_EVOLUTION_RULES if rule.generation == int(generation))
