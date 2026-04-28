from __future__ import annotations

from pokecable_room.canonical import CanonicalPokemon

from .matrix import (
    FORWARD_TRANSFER_TO_GEN3,
    LEGACY_DOWNCONVERT_EXPERIMENTAL,
    SAME_GENERATION,
    TIME_CAPSULE_GEN1_GEN2,
    UNSUPPORTED,
    get_trade_mode,
)
from .report import CompatibilityReport


MAX_SPECIES_BY_GENERATION = {1: 151, 2: 251, 3: 386}


def build_compatibility_report(
    canonical: CanonicalPokemon,
    target_generation: int,
    *,
    cross_generation_enabled: bool = False,
) -> CompatibilityReport:
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
    if mode == SAME_GENERATION:
        return report
    if not cross_generation_enabled:
        report.compatible = False
        report.blocking_reasons.append(
            "Cross-generation esta protegido por feature guard enquanto os conversores locais estao em desenvolvimento."
        )
        report.suggested_actions.append("Use uma sala same-generation ou aguarde o conversor deste modo ficar habilitado.")
    _apply_species_rules(report, canonical)
    _apply_mode_rules(report, canonical)
    return report


def _apply_species_rules(report: CompatibilityReport, canonical: CanonicalPokemon) -> None:
    max_species = MAX_SPECIES_BY_GENERATION.get(report.target_generation, 0)
    if canonical.species_national_id > max_species:
        report.compatible = False
        report.blocking_reasons.append(
            f"{canonical.species_name} National Dex #{canonical.species_national_id} nao existe na Gen {report.target_generation}."
        )


def _apply_mode_rules(report: CompatibilityReport, canonical: CanonicalPokemon) -> None:
    if report.mode == TIME_CAPSULE_GEN1_GEN2:
        if report.source_generation == 2 and report.target_generation == 1 and canonical.held_item is not None:
            report.warnings.append("Held item nao existe em Gen 1 e sera removido no downconvert.")
            report.data_loss.append("held_item")
        if report.target_generation == 1:
            report.warnings.append("Gen 1 nao possui amizade, genero, shininess completo, held item ou breeding data.")
    elif report.mode == FORWARD_TRANSFER_TO_GEN3:
        report.warnings.append("Transfer para Gen 3 exigira recriar campos nativos Gen 3 localmente no client.")
    elif report.mode == LEGACY_DOWNCONVERT_EXPERIMENTAL:
        report.warnings.append("Downconvert de Gen 3 para Gen 1/2 e experimental e pode perder dados modernos.")
        if canonical.held_item is not None and report.target_generation == 1:
            report.data_loss.append("held_item")
