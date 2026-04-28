from __future__ import annotations

from .parsers.base import PokemonPayload


TRADE_EVOLUTIONS: dict[int, dict[int, tuple[int, str]]] = {
    1: {
        64: (65, "Alakazam"),
        67: (68, "Machamp"),
        75: (76, "Golem"),
        93: (94, "Gengar"),
    },
    2: {
        64: (65, "Alakazam"),
        67: (68, "Machamp"),
        75: (76, "Golem"),
        93: (94, "Gengar"),
    },
    3: {
        64: (65, "Alakazam"),
        67: (68, "Machamp"),
        75: (76, "Golem"),
        93: (94, "Gengar"),
    },
}


def validate_payload_for_local_save(payload: PokemonPayload, local_generation: int) -> None:
    if payload.generation != local_generation:
        raise ValueError(
            f"Payload recebido e Gen {payload.generation}, mas o save local e Gen {local_generation}. "
            "Trocas entre geracoes diferentes ainda nao sao suportadas."
        )


def maybe_apply_trade_evolution(payload: PokemonPayload, enabled: bool) -> PokemonPayload:
    if not enabled:
        return payload
    # Evolucao automatica precisa alterar dados internos por geracao. Enquanto isso nao
    # estiver validado para cada formato, preservar o payload bruto e mais seguro.
    return payload
