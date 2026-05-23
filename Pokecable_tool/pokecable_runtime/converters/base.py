from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from canonical import CanonicalMove, CanonicalPokemon
from compatibility import CompatibilityReport, build_compatibility_report
from data.items import equivalent_item_id, item_exists, item_name
from data.moves import default_move_pp, move_exists, move_name


@dataclass(slots=True)
class ConversionResult:
    canonical_before: CanonicalPokemon
    canonical_after: CanonicalPokemon
    compatibility_report: CompatibilityReport
    target_generation: int
    target_game: str
    wrote_to_save: bool
    data_loss: list[str] = field(default_factory=list)
    transformations: list[str] = field(default_factory=list)


class BaseConverter:
    source_generation: int = 0
    target_generation: int = 0
    mode: str = "unsupported"

    def can_convert(
        self,
        canonical: CanonicalPokemon,
        policy: str = "safe_default",
        target_game: str = "",
    ) -> CompatibilityReport:
        report = build_compatibility_report(
            canonical,
            self.target_generation,
            cross_generation_enabled=True,
            policy=policy,
            target_game=target_game,
        )
        if int(canonical.source_generation) != int(self.source_generation):
            report.compatible = False
            report.blocking_reasons.append(
                f"Conversor Gen {self.source_generation} -> Gen {self.target_generation} recebeu Gen {canonical.source_generation}."
            )
        if report.mode != self.mode:
            report.compatible = False
            report.blocking_reasons.append(f"Conversor {self.mode} recebeu payload do modo {report.mode}.")
        return report

    def convert(
        self,
        canonical: CanonicalPokemon,
        target_parser,
        target_location: str,
        policy: str = "safe_default",
        resolved_moves: dict[int, int] | None = None,
        item_relocation_choice: str | None = None,
        relocate_dropped_item: bool = False,
    ) -> ConversionResult:
        target_game = str(target_parser.get_game_id() or "")
        report = self.can_convert(canonical, policy=policy, target_game=target_game)
        converted = self._normalized_copy(canonical, report, resolved_moves=resolved_moves)
        del item_relocation_choice, relocate_dropped_item
        return ConversionResult(
            canonical_before=canonical,
            canonical_after=converted,
            compatibility_report=report,
            target_generation=self.target_generation,
            target_game=target_game,
            wrote_to_save=False,
            data_loss=list(report.data_loss),
            transformations=list(report.transformations),
        )

    def inspect_item_relocation(
        self,
        original: CanonicalPokemon,
        source_parser,
        report: CompatibilityReport | None = None,
    ) -> dict[str, object] | None:
        src_item = original.held_item
        if src_item is None or not src_item.item_id:
            return None
        if report is not None and not report.removed_items:
            return None
        src_id = int(src_item.item_id)
        src_gen = int(original.source_generation or self.source_generation)
        target_gen = int(self.target_generation)
        item_label = item_name(src_id, src_gen) or str(src_id)
        if target_gen == 1:
            compatibility_reason = (
                f"A Gen 1 nao possui a mecânica de Pokemon segurar item. "
                f"Deseja enviar o item {item_label} para a mochila, para o computador, ou jogar fora neste save antes de transferir?"
            )
            manual_remove_reason = (
                f"A Gen 1 nao possui a mecânica de Pokemon segurar item. "
                f"Como nao ha espaco disponivel neste save, remova o item {item_label} manualmente no seu jogo antes de transferir."
            )
        else:
            target_item_label = item_name(equivalent_item_id(src_id, src_gen, target_gen) or 0, target_gen) or item_label
            compatibility_reason = (
                f"O item {target_item_label} nao pode acompanhar o Pokemon na Gen {target_gen}. "
                f"Deseja enviar o item original {item_label} para a mochila, para o computador, ou jogar fora neste save antes de transferir?"
            )
            manual_remove_reason = (
                f"O item {item_label} nao pode acompanhar o Pokemon na Gen {target_gen}. "
                f"Como nao ha espaco disponivel neste save, remova esse item manualmente no seu jogo antes de transferir."
            )
        bag_available = False
        pc_available = False
        try:
            bag_available = bool(source_parser.has_bag_space(src_id, 1))
        except Exception:
            bag_available = False
        try:
            pc_available = bool(source_parser.has_pc_space(src_id, 1))
        except Exception:
            pc_available = False
        options: list[str] = []
        if bag_available or pc_available:
            if bag_available:
                options.append("bag")
            if pc_available:
                options.append("pc")
            options.append("remove")
            status = "choose_destination"
            reason = compatibility_reason
        else:
            status = "manual_remove_required"
            reason = manual_remove_reason
        return {
            "status": status,
            "reason": reason,
            "item_id": src_id,
            "item_name": item_label,
            "target_item_id": equivalent_item_id(src_id, src_gen, target_gen) or 0,
            "target_item_name": item_name(equivalent_item_id(src_id, src_gen, target_gen) or 0, target_gen),
            "target_generation": target_gen,
            "bag_available": bag_available,
            "pc_available": pc_available,
            "options": options,
        }

    def _relocate_dropped_item(
        self,
        original: CanonicalPokemon,
        converted: CanonicalPokemon,
        source_parser,
        report: CompatibilityReport,
        *,
        item_relocation_choice: str | None = None,
    ) -> None:
        if converted.held_item and converted.held_item.item_id:
            return
        plan = self.inspect_item_relocation(original, source_parser, report)
        if not plan:
            return
        status = str(plan.get("status") or "")
        if status == "manual_remove_required":
            report.compatible = False
            reason = str(plan.get("reason") or "Remova o item do Pokemon antes de transferir.")
            if reason not in report.blocking_reasons:
                report.blocking_reasons.append(reason)
            if reason not in report.suggested_actions:
                report.suggested_actions.append(reason)
            return
        source_id = int(plan.get("item_id") or 0)
        source_name = str(plan.get("item_name") or source_id)
        target_gen = int(plan.get("target_generation") or self.target_generation)
        normalized_choice = str(item_relocation_choice or "").strip().lower()
        if normalized_choice not in {"bag", "pc", "remove"}:
            report.compatible = False
            report.blocking_reasons.append(
                f"Escolha o que fazer com o item segurado {source_name} antes de transferir: mochila, computador ou jogar fora."
            )
            report.suggested_actions.append("Escolha mochila, computador ou jogar fora para o item incompatível.")
            return
        if normalized_choice == "remove":
            report.transformations.append(
                f"Item segurado {source_name} foi jogado fora antes da transferencia para a Gen {target_gen}."
            )
            return
        if normalized_choice == "bag":
            source_parser.store_item_in_bag(source_id, 1)
            report.transformations.append(
                f"Item segurado {source_name} voltou para a mochila deste save antes da transferencia para a Gen {target_gen}."
            )
            return
        source_parser.store_item_in_pc(source_id, 1)
        report.transformations.append(
            f"Item segurado {source_name} voltou para o computador deste save antes da transferencia para a Gen {target_gen}."
        )

    def apply_to_save(
        self,
        target_parser,
        target_location: str,
        canonical: CanonicalPokemon,
        policy: str = "safe_default",
        resolved_moves: dict[int, int] | None = None,
        item_relocation_choice: str | None = None,
    ) -> ConversionResult:
        result = self.convert(
            canonical,
            target_parser,
            target_location,
            policy=policy,
            resolved_moves=resolved_moves,
            item_relocation_choice=item_relocation_choice,
        )
        if not result.compatibility_report.compatible:
            raise ValueError("; ".join(result.compatibility_report.blocking_reasons))
        target_parser.import_canonical(target_location, result.canonical_after)
        result.wrote_to_save = True
        return result

    def _normalized_copy(
        self, canonical: CanonicalPokemon, report: CompatibilityReport, resolved_moves: dict[int, int] | None = None
    ) -> CanonicalPokemon:
        converted = deepcopy(canonical)
        self._apply_report_normalization(converted, report, resolved_moves=resolved_moves)
        return converted

    def _apply_report_normalization(
        self, converted: CanonicalPokemon, report: CompatibilityReport, resolved_moves: dict[int, int] | None = None
    ) -> None:
        if converted.species is not None:
            target_species_id = report.normalized_species.get("target_species_id")
            if target_species_id is None:
                if report.compatible:
                    report.compatible = False
                    report.blocking_reasons.append("target_species_id ausente: especie nao mapeada na geracao destino.")
                return
            converted.species.target_species_id = target_species_id
            converted.species.target_species_id_space = report.normalized_species.get("target_species_id_space")
        
        removed_move_entries = {
            int(move["move_id"]): move
            for move in report.removed_moves
            if move.get("move_id") is not None
        }
        removed_move_ids = set(removed_move_entries)
        
        if removed_move_ids:
            replacement_choices: dict[int, int] = {}
            for removed_id, removed_entry in removed_move_entries.items():
                replacement_id = (
                    int(resolved_moves.get(removed_id, resolved_moves.get(str(removed_id), 0)))
                    if resolved_moves
                    else 0
                )
                if replacement_id <= 0:
                    continue
                valid_replacement_ids = {
                    int(option.get("move_id") or 0)
                    for option in (removed_entry.get("valid_replacements") or [])
                    if int(option.get("move_id") or 0) > 0
                }
                if replacement_id not in valid_replacement_ids:
                    report.compatible = False
                    removed_name = removed_entry.get("name") or move_name(removed_id) or f"Move #{removed_id}"
                    replacement_name = move_name(replacement_id) or f"Move #{replacement_id}"
                    reason = (
                        f"Move substituto {replacement_name} nao e valido para substituir {removed_name} "
                        f"na Gen {self.target_generation} neste jogo/nivel."
                    )
                    if reason not in report.blocking_reasons:
                        report.blocking_reasons.append(reason)
                    return
                replacement_choices[removed_id] = replacement_id

            new_moves = []
            for move in converted.moves:
                m_id = int(move.move_id or 0)
                if m_id in removed_move_ids:
                    replacement_id = replacement_choices.get(m_id, 0)
                    if replacement_id > 0:
                        replacement_pp = default_move_pp(replacement_id, self.target_generation)
                        new_moves.append(
                            CanonicalMove(
                                move_id=replacement_id,
                                name=move_name(replacement_id) or f"Move #{replacement_id}",
                                pp=replacement_pp,
                                max_pp=replacement_pp,
                                pp_ups=0,
                                source_generation=self.target_generation,
                            )
                        )
                    # Se replacement_id == 0, o move e simplesmente removido
                elif move_exists(m_id, self.target_generation):
                    new_moves.append(move)
            
            converted.moves = new_moves

            should_apply_fallback = any("Pound sera aplicado" in item for item in report.transformations)
            if not converted.moves and should_apply_fallback:
                fallback_pp = default_move_pp(1, self.target_generation)
                converted.moves = [
                    CanonicalMove(
                        move_id=1,
                        name=move_name(1) or "Pound",
                        pp=fallback_pp,
                        max_pp=fallback_pp,
                        pp_ups=0,
                        source_generation=self.target_generation,
                    )
                ]
                fallback = "Fallback move Pound aplicado apos remocao de moves incompativeis."
                if fallback not in report.transformations:
                    report.transformations.append(fallback)
        if report.removed_items:
            converted.held_item = None
        if "ability" in report.removed_fields:
            converted.ability = None
        if "nature" in report.removed_fields:
            converted.nature = None
        if "trainer_id_high_bits" in report.removed_fields:
            converted.trainer_id = int(converted.trainer_id) & 0xFFFF
        for metadata_field in ("gender", "sex", "form"):
            if metadata_field in report.removed_fields:
                converted.metadata.pop(metadata_field, None)


def get_converter(source_generation: int, target_generation: int) -> BaseConverter:
    from .gen1_to_gen2 import Gen1ToGen2Converter
    from .gen1_to_gen3 import Gen1ToGen3Converter
    from .gen2_to_gen1 import Gen2ToGen1Converter
    from .gen2_to_gen3 import Gen2ToGen3Converter
    from .gen3_to_gen1 import Gen3ToGen1Converter
    from .gen3_to_gen2 import Gen3ToGen2Converter

    converters: dict[tuple[int, int], type[BaseConverter]] = {
        (1, 2): Gen1ToGen2Converter,
        (2, 1): Gen2ToGen1Converter,
        (1, 3): Gen1ToGen3Converter,
        (2, 3): Gen2ToGen3Converter,
        (3, 2): Gen3ToGen2Converter,
        (3, 1): Gen3ToGen1Converter,
    }
    return converters[(int(source_generation), int(target_generation))]()
