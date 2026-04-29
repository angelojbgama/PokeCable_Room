from __future__ import annotations


SHOWDOWN_FORMATS_BY_GENERATION = {
    1: "gen1customgame",
    2: "gen2customgame",
    3: "gen3customgame",
}


def format_id_for_generation(generation: int) -> str:
    try:
        return SHOWDOWN_FORMATS_BY_GENERATION[int(generation)]
    except KeyError as exc:
        raise ValueError(f"Geracao de batalha nao suportada: {generation}") from exc
