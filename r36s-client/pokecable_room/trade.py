from __future__ import annotations

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import build_compatibility_report

from .parsers.base import PokemonPayload


def validate_payload_for_local_save(payload: PokemonPayload, local_generation: int) -> None:
    if payload.generation != local_generation:
        report = None
        if payload.canonical:
            report = build_compatibility_report(
                CanonicalPokemon.from_dict(payload.canonical),
                local_generation,
                cross_generation_enabled=False,
            )
        raise ValueError(
            f"Payload recebido e Gen {payload.generation}, mas o save local e Gen {local_generation}. "
            "Raw payload de uma geracao nao pode ser gravado diretamente em save de outra geracao. "
            "Para cross-generation, o client precisa usar o modelo canonico e um conversor local."
            f"{_format_report_hint(report)}"
        )


def _format_report_hint(report) -> str:
    if report is None:
        return ""
    reasons = "; ".join(report.blocking_reasons)
    return f" Motivo: {reasons}" if reasons else ""
