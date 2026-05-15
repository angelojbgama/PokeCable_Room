"""Para cada (gen, ndex), constrói CanonicalPokemon, serializa via to_dict
e deserializa via from_dict, verifica que campos críticos sobrevivem.
"""
from __future__ import annotations

import pytest


GEN_LIMITS = {1: 151, 2: 251, 3: 386}


def _all_cases() -> list[tuple[int, int]]:
    from data.species import species_exists_in_generation
    cases: list[tuple[int, int]] = []
    for gen, limit in GEN_LIMITS.items():
        for ndex in range(1, limit + 1):
            if species_exists_in_generation(ndex, gen):
                cases.append((gen, ndex))
    return cases


@pytest.mark.parametrize("gen,ndex", _all_cases())
def test_canonical_serialize_roundtrip(gen: int, ndex: int, canonical_factory, learnset_for):
    from canonical import CanonicalPokemon

    moves = learnset_for(gen, ndex)[:4]
    canonical = canonical_factory(gen, ndex, moves=moves, nickname="ASHTEST")
    blob = canonical.to_dict()
    restored = CanonicalPokemon.from_dict(blob)

    assert restored.species.national_dex_id == canonical.species.national_dex_id
    assert restored.species_national_id == canonical.species_national_id
    assert restored.nickname == canonical.nickname
    assert restored.ot_name == canonical.ot_name
    assert restored.trainer_id == canonical.trainer_id
    assert restored.level == canonical.level
    assert [m.move_id for m in restored.moves] == [m.move_id for m in canonical.moves]
