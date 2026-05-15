from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for sub in ("PokeCable/backend", "Pokecable_tool"):
    full = str((_ROOT / sub).resolve())
    if full not in sys.path:
        sys.path.insert(0, full)


@pytest.fixture(scope="session")
def all_species_by_gen() -> dict[int, list[int]]:
    """Mapeia gen -> lista de national_dex_ids existentes naquela gen.

    Gen 1 = 1..151, Gen 2 = 1..251, Gen 3 = 1..386.
    """
    from data.species import species_exists_in_generation

    result: dict[int, list[int]] = {}
    limits = {1: 151, 2: 251, 3: 386}
    for gen, limit in limits.items():
        result[gen] = [ndex for ndex in range(1, limit + 1) if species_exists_in_generation(ndex, gen)]
    return result


@pytest.fixture(scope="session")
def all_moves_by_gen() -> dict[int, list[int]]:
    """Mapeia gen -> lista de move_ids existentes naquela gen, derivada de MOVE_DATA."""
    from data.moves import MOVE_DATA

    out: dict[int, list[int]] = {1: [], 2: [], 3: []}
    for move_id, meta in MOVE_DATA.items():
        for gen in meta.generations:
            if gen in out:
                out[gen].append(int(move_id))
    for gen in out:
        out[gen].sort()
    return out


@pytest.fixture(scope="session")
def learnset_for():
    from data.learnsets import get_learnable_moves

    def _resolve(gen: int, ndex: int) -> List[int]:
        return list(get_learnable_moves(int(gen), int(ndex)) or [])

    return _resolve


@pytest.fixture(scope="session")
def canonical_factory():
    from canonical import (
        CanonicalMove,
        CanonicalPokemon,
        CanonicalSpecies,
    )
    from data.moves import move_name
    from data.species import SPECIES_NAMES_BY_NATIONAL

    def _build(
        gen: int,
        national_dex_id: int,
        moves: Optional[Iterable[int]] = None,
        level: int = 50,
        nickname: Optional[str] = None,
        ot_name: str = "TRAINER",
        trainer_id: int = 12345,
    ) -> CanonicalPokemon:
        species_name = SPECIES_NAMES_BY_NATIONAL.get(int(national_dex_id), f"Species #{national_dex_id}")
        moves_list: list[CanonicalMove] = []
        for mid in list(moves or [])[:4]:
            mid_int = int(mid)
            if mid_int <= 0:
                continue
            moves_list.append(
                CanonicalMove(
                    move_id=mid_int,
                    name=move_name(mid_int) or f"Move #{mid_int}",
                    source_generation=int(gen),
                )
            )
        return CanonicalPokemon(
            source_generation=int(gen),
            source_game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[int(gen)],
            species_national_id=int(national_dex_id),
            species_name=species_name,
            species=CanonicalSpecies(
                national_dex_id=int(national_dex_id),
                source_species_id=int(national_dex_id),
                source_species_id_space="national_dex" if gen == 2 else (f"gen{gen}_internal"),
                name=species_name,
            ),
            nickname=nickname or species_name.upper(),
            ot_name=ot_name,
            trainer_id=int(trainer_id),
            level=int(level),
            experience=int(level) ** 3,
            moves=moves_list,
        )

    return _build


@pytest.fixture(scope="session")
def cross_gen_pairs() -> list[tuple[int, int]]:
    """Pares (src, tgt) suportados por get_converter."""
    return [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]
