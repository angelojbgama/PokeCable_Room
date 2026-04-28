from __future__ import annotations

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import build_compatibility_report
from pokecable_room.evolutions import EvolutionContext, apply_trade_evolution

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
            "Cross-generation esta protegido por bloqueio de seguranca enquanto a camada de conversao local "
            f"esta em desenvolvimento.{_format_report_hint(report)}"
        )


def maybe_apply_trade_evolution(payload: PokemonPayload, enabled: bool) -> PokemonPayload:
    if not enabled:
        return payload
    if payload.canonical:
        canonical = CanonicalPokemon.from_dict(payload.canonical)
        context = EvolutionContext(
            source_generation=canonical.source_generation,
            target_generation=payload.target_generation or payload.generation,
            trade_mode=payload.trade_mode,
        )
        payload.canonical = apply_trade_evolution(canonical, context).to_dict()
    # Same-generation raw payload permanece como fonte de escrita estavel. Evolucao
    # automatica de raw precisa alterar bytes internos por parser e segue desativada.
    return payload


def _format_report_hint(report) -> str:
    if report is None:
        return ""
    reasons = "; ".join(report.blocking_reasons)
    return f" Motivo: {reasons}" if reasons else ""
