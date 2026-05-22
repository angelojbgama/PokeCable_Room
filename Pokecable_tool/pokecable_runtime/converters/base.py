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

    def can_convert(self, canonical: CanonicalPokemon, policy: str = "safe_default") -> CompatibilityReport:
        report = build_compatibility_report(canonical, self.target_generation, cross_generation_enabled=True, policy=policy)
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
        relocate_dropped_item: bool = True,
    ) -> ConversionResult:
        report = self.can_convert(canonical, policy=policy)
        converted = self._normalized_copy(canonical, report, resolved_moves=resolved_moves)
        # When the pokemon's held item won't survive the transfer (no equivalent in target gen,
        # or target gen has no held-item concept at all like Gen 1), try to save the item to the
        # destination trainer's bag → PC instead of silently dropping it.
        if relocate_dropped_item:
            self._relocate_dropped_item(canonical, converted, target_parser, report)
        return ConversionResult(
            canonical_before=canonical,
            canonical_after=converted,
            compatibility_report=report,
            target_generation=self.target_generation,
            target_game=target_parser.get_game_id(),
            wrote_to_save=False,
            data_loss=list(report.data_loss),
            transformations=list(report.transformations),
        )

    def _relocate_dropped_item(
        self,
        original: CanonicalPokemon,
        converted: CanonicalPokemon,
        target_parser,
        report: CompatibilityReport,
    ) -> None:
        """If the original held item was dropped during conversion, the item must NOT be
        discarded. We try:
          1) target trainer's bag
          2) target trainer's PC items
          3) Refuse the trade (set report.compatible=False) — user must clear space or
             remove the item before retrying.
        """
        src_item = original.held_item
        if src_item is None or not src_item.item_id:
            return
        # Item still on the pokemon? Then no relocation needed.
        if converted.held_item and converted.held_item.item_id:
            return
        src_id = int(src_item.item_id)
        src_gen = int(original.source_generation or self.source_generation)
        target_gen = int(self.target_generation)
        # Resolve item id in the target gen (name-based mapping preferred over raw id).
        target_id = equivalent_item_id(src_id, src_gen, target_gen) or 0
        if not target_id and src_gen == target_gen:
            target_id = src_id
        if not target_id or not item_exists(target_id, target_gen):
            # No equivalent in destination at all — refuse trade so item isn't lost.
            report.compatible = False
            report.blocking_reasons.append(
                f"Item segurado {item_name(src_id, src_gen) or src_id} nao existe na Gen {target_gen}. "
                f"Remova-o antes de transferir ou troque por um item compativel."
            )
            return
        # Try bag, then PC. Wrap in try/except since some parsers' has_bag_space can raise
        # for incompatible item categories.
        try:
            if target_parser.has_bag_space(target_id, 1):
                target_parser.store_item_in_bag(target_id, 1)
                report.transformations.append(
                    f"Item segurado {item_name(target_id, target_gen) or target_id} foi para a mochila "
                    f"do treinador destino (Gen {target_gen})."
                )
                return
        except Exception:
            pass
        try:
            if target_parser.has_pc_space(target_id, 1):
                target_parser.store_item_in_pc(target_id, 1)
                report.transformations.append(
                    f"Item segurado {item_name(target_id, target_gen) or target_id} foi para o PC "
                    f"de itens (mochila cheia, Gen {target_gen})."
                )
                return
        except Exception:
            pass
        # Out of bag and PC space — refuse the trade so the item isn't lost.
        report.compatible = False
        report.blocking_reasons.append(
            f"Mochila e PC cheios na Gen {target_gen}; nao ha onde guardar o item segurado "
            f"{item_name(target_id, target_gen) or target_id}. Libere espaco antes de transferir."
        )

    def apply_to_save(
        self,
        target_parser,
        target_location: str,
        canonical: CanonicalPokemon,
        policy: str = "safe_default",
        resolved_moves: dict[int, int] | None = None,
    ) -> ConversionResult:
        result = self.convert(canonical, target_parser, target_location, policy=policy, resolved_moves=resolved_moves)
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
        
        removed_move_ids = {int(move["move_id"]) for move in report.removed_moves if move.get("move_id") is not None}
        
        if removed_move_ids:
            new_moves = []
            for move in converted.moves:
                m_id = int(move.move_id or 0)
                if m_id in removed_move_ids:
                    # Aplica resolucao do usuario se existir
                    replacement_id = int(resolved_moves.get(m_id, resolved_moves.get(str(m_id), 0))) if resolved_moves else 0
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
