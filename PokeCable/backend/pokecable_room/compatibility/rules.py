from __future__ import annotations

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.data.items import equivalent_item_id, item_exists, item_name
from pokecable_room.data.learnsets import get_learnable_moves
from pokecable_room.data.moves import move_exists, move_name
from pokecable_room.data.species import national_to_native, species_exists_in_generation

from .matrix import (
    FORWARD_TRANSFER_TO_GEN3,
    LEGACY_DOWNCONVERT_EXPERIMENTAL,
    SAME_GENERATION,
    TIME_CAPSULE_GEN1_GEN2,
    UNSUPPORTED,
    get_trade_mode,
)
from .report import CompatibilityReport


POLICIES = {"strict", "permissive", "safe_default", "auto_retrocompat"}


def build_compatibility_report(
    canonical: CanonicalPokemon,
    target_generation: int,
    *,
    cross_generation_enabled: bool = True,
    policy: str = "safe_default",
) -> CompatibilityReport:
    if policy not in POLICIES:
        raise ValueError(f"Politica de compatibilidade invalida: {policy}")
    source_generation = int(canonical.source_generation)
    target_generation = int(target_generation)
    mode = get_trade_mode(source_generation, target_generation)
    report = CompatibilityReport(
        compatible=True,
        mode=mode,
        source_generation=source_generation,
        target_generation=target_generation,
    )
    if mode == UNSUPPORTED:
        report.compatible = False
        report.blocking_reasons.append("Par de geracoes nao suportado pela matriz de compatibilidade.")
        return report
    _apply_species_rules(report, canonical)
    _apply_move_rules(report, canonical, policy)
    _apply_item_rules(report, canonical, policy)
    _apply_generation_field_rules(report, canonical, policy)
    if mode == SAME_GENERATION:
        return report
    _apply_mode_rules(report, canonical)
    return report


def _apply_species_rules(report: CompatibilityReport, canonical: CanonicalPokemon) -> None:
    species = canonical.species
    national_id = species.national_dex_id if species is not None else canonical.species_national_id
    report.normalized_species = {
        "national_dex_id": national_id,
        "source_species_id": species.source_species_id if species is not None else canonical.species_national_id,
        "source_species_id_space": species.source_species_id_space if species is not None else "legacy_national_dex",
    }
    if national_id == 0 or canonical.metadata.get("is_egg"):
        report.compatible = False
        report.blocking_reasons.append("Egg nao e transferivel.")
        return
    if not species_exists_in_generation(national_id, report.target_generation):
        report.compatible = False
        report.blocking_reasons.append(
            f"{canonical.species_name} National Dex #{national_id} nao existe na Gen {report.target_generation}."
        )
        return
    target_native = national_to_native(report.target_generation, national_id)
    report.normalized_species["target_species_id"] = target_native
    report.normalized_species["target_species_id_space"] = {
        1: "gen1_internal",
        2: "national_dex",
        3: "gen3_internal",
    }[report.target_generation]


def _apply_move_rules(report: CompatibilityReport, canonical: CanonicalPokemon, policy: str) -> None:
    original_move_count = 0
    national_id = report.normalized_species.get("national_dex_id")
    learnable_ids = get_learnable_moves(report.target_generation, national_id) if national_id else []
    
    valid_replacements = []
    for m_id in learnable_ids:
        valid_replacements.append({"move_id": m_id, "name": move_name(m_id) or f"Move #{m_id}"})

    for move in canonical.moves:
        if move.move_id in {0, None}:
            continue
        original_move_count += 1
        if move_exists(move.move_id, report.target_generation):
            continue
        
        removed = {
            "move_id": move.move_id, 
            "name": move.name or move_name(move.move_id) or f"Move #{move.move_id}",
            "valid_replacements": valid_replacements
        }
        
        if policy in {"strict", "safe_default"}:
            report.compatible = False
            report.blocking_reasons.append(f"Move {removed['name']} nao existe na Gen {report.target_generation}.")
        else:
            report.removed_moves.append(removed)
            _add_unique(report.data_loss, "moves")
            if policy == "permissive":
                report.requires_user_confirmation = True
    if (
        policy == "auto_retrocompat"
        and original_move_count > 0
        and len(report.removed_moves) == original_move_count
    ):
        report.transformations.append("Todos os moves incompativeis foram removidos; Pound sera aplicado como fallback.")


def _apply_item_rules(report: CompatibilityReport, canonical: CanonicalPokemon, policy: str) -> None:
    if canonical.held_item is None or canonical.held_item.item_id in {None, 0}:
        return
    item = canonical.held_item
    if report.target_generation == 1:
        removed = {"item_id": item.item_id, "name": item.name or item_name(item.item_id, canonical.source_generation)}
        report.removed_items.append(removed)
        _add_unique(report.data_loss, "held_item")
        report.warnings.append("Held item nao existe em Gen 1 e sera removido.")
        if policy != "auto_retrocompat":
            report.requires_user_confirmation = True
        if policy == "strict":
            report.compatible = False
            report.blocking_reasons.append("Held item nao existe na Gen 1.")
        return
    mapped = equivalent_item_id(item.item_id, canonical.source_generation, report.target_generation)
    if mapped is not None and item_exists(mapped, report.target_generation):
        report.transformations.append(f"Held item convertido para ID {mapped} na Gen {report.target_generation}.")
        return
    if item_exists(item.item_id, report.target_generation):
        return
    if policy == "strict":
        report.compatible = False
        report.blocking_reasons.append("Held item nao existe na geracao destino.")
    else:
        report.removed_items.append({"item_id": item.item_id, "name": item.name})
        _add_unique(report.data_loss, "held_item")
        if policy != "auto_retrocompat":
            report.requires_user_confirmation = True


def _apply_generation_field_rules(report: CompatibilityReport, canonical: CanonicalPokemon, policy: str) -> None:
    if report.target_generation in {1, 2}:
        if canonical.ability:
            report.removed_fields.append("ability")
            _add_unique(report.data_loss, "ability")
        if canonical.nature:
            report.removed_fields.append("nature")
            _add_unique(report.data_loss, "nature")
        if canonical.source_generation == 3 and int(canonical.trainer_id) > 0xFFFF:
            report.removed_fields.append("trainer_id_high_bits")
            _add_unique(report.data_loss, "trainer_id_high_bits")
            report.transformations.append("Trainer ID Gen 3 sera reduzido para 16 bits no destino.")
        for metadata_field in ("gender", "sex", "form"):
            if metadata_field in canonical.metadata:
                report.removed_fields.append(metadata_field)
                _add_unique(report.data_loss, metadata_field)
        if canonical.ability or canonical.nature:
            if policy != "auto_retrocompat":
                report.requires_user_confirmation = True
            if policy == "strict":
                report.compatible = False
                report.blocking_reasons.append("Ability/nature nao existem na geracao destino.")
        if "trainer_id_high_bits" in report.removed_fields:
            if policy != "auto_retrocompat":
                report.requires_user_confirmation = True
            if policy == "strict":
                report.compatible = False
                report.blocking_reasons.append("Trainer ID Gen 3 perderia bits altos na geracao destino.")
        if any(field in report.removed_fields for field in ("gender", "sex", "form")) and policy != "auto_retrocompat":
            report.requires_user_confirmation = True
    elif report.target_generation == 3 and canonical.source_generation in {1, 2}:
        if not canonical.ability:
            report.transformations.append("Ability Gen 3 sera gerada pelo parser local.")
        if not canonical.nature:
            report.transformations.append("Nature Gen 3 sera gerada pelo parser local.")


def _apply_mode_rules(report: CompatibilityReport, canonical: CanonicalPokemon) -> None:
    if report.mode == TIME_CAPSULE_GEN1_GEN2:
        if report.source_generation == 2 and report.target_generation == 1 and canonical.held_item is not None:
            report.warnings.append("Held item nao existe em Gen 1 e sera removido no downconvert.")
            if "held_item" not in report.data_loss:
                _add_unique(report.data_loss, "held_item")
        if report.target_generation == 1:
            report.warnings.append("Gen 1 nao possui amizade, genero, shininess completo, held item ou breeding data.")
    elif report.mode == FORWARD_TRANSFER_TO_GEN3:
        report.warnings.append("Transfer para Gen 3 exigira recriar campos nativos Gen 3 localmente no client.")
    elif report.mode == LEGACY_DOWNCONVERT_EXPERIMENTAL:
        report.warnings.append("Downconvert de Gen 3 para Gen 1/2 e experimental e pode perder dados modernos.")
        if canonical.held_item is not None and report.target_generation == 1 and "held_item" not in report.data_loss:
            _add_unique(report.data_loss, "held_item")


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
