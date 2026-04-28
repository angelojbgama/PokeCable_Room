from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport, build_compatibility_report


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
        return build_compatibility_report(canonical, self.target_generation, cross_generation_enabled=True, policy=policy)

    def convert(self, canonical: CanonicalPokemon, target_parser, target_location: str, policy: str = "safe_default") -> ConversionResult:
        report = self.can_convert(canonical, policy=policy)
        converted = self._normalized_copy(canonical, report)
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

    def apply_to_save(
        self,
        target_parser,
        target_location: str,
        canonical: CanonicalPokemon,
        policy: str = "safe_default",
    ) -> ConversionResult:
        result = self.convert(canonical, target_parser, target_location, policy=policy)
        if not result.compatibility_report.compatible:
            raise ValueError("; ".join(result.compatibility_report.blocking_reasons))
        target_parser.import_canonical(target_location, result.canonical_after)
        result.wrote_to_save = True
        return result

    def _normalized_copy(self, canonical: CanonicalPokemon, report: CompatibilityReport) -> CanonicalPokemon:
        converted = deepcopy(canonical)
        if converted.species is not None:
            converted.species.target_species_id = report.normalized_species.get("target_species_id")
            converted.species.target_species_id_space = report.normalized_species.get("target_species_id_space")
        return converted


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
