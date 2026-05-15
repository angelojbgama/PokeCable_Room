"""Cobre cada (gen, species, move_id) no LEARNSETS. ~24k testes."""
from __future__ import annotations

import pytest


def _all_cases() -> list[tuple[int, int, int]]:
    from data.learnsets import LEARNSETS
    cases: list[tuple[int, int, int]] = []
    for (gen, ndex), move_ids in LEARNSETS.items():
        for mid in move_ids:
            cases.append((int(gen), int(ndex), int(mid)))
    return cases


@pytest.mark.parametrize("gen,ndex,move_id", _all_cases())
def test_learnset_move_is_valid_in_generation(gen: int, ndex: int, move_id: int):
    from data.moves import move_exists
    from data.species import species_exists_in_generation

    assert move_id > 0, f"Learnset gen{gen}/{ndex} contém move_id inválido 0"
    assert move_exists(move_id, gen), (
        f"Learnset gen{gen}/#{ndex} declara move {move_id} mas move_exists diz que não existe em Gen {gen}"
    )
    assert species_exists_in_generation(ndex, gen), (
        f"Learnset declara (gen{gen}, #{ndex}) mas a espécie não existe naquela gen"
    )
