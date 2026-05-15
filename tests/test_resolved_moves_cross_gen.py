"""Para cada par cross-gen × cada espécie comum, valida que o converter
retorna report.removed_moves e valid_replacements consistentes.
"""
from __future__ import annotations

import pytest


CROSS_PAIRS = [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]


def _all_cases() -> list[tuple[int, int, int]]:
    from data.species import species_exists_in_generation
    cases: list[tuple[int, int, int]] = []
    for src, tgt in CROSS_PAIRS:
        for ndex in range(1, 387):
            if species_exists_in_generation(ndex, src) and species_exists_in_generation(ndex, tgt):
                cases.append((src, tgt, ndex))
    return cases


@pytest.mark.parametrize("src_gen,tgt_gen,ndex", _all_cases())
def test_cross_gen_removed_moves_have_valid_replacements(
    src_gen: int, tgt_gen: int, ndex: int, canonical_factory, learnset_for
):
    from converters import get_converter

    source_moves = learnset_for(src_gen, ndex)[:4]
    if not source_moves:
        pytest.skip(f"Sem learnset Gen{src_gen}/#{ndex}")
    canonical = canonical_factory(src_gen, ndex, moves=source_moves)
    converter = get_converter(src_gen, tgt_gen)
    report = converter.can_convert(canonical, policy="auto_retrocompat")

    target_learnset = set(learnset_for(tgt_gen, ndex))
    for removed in report.removed_moves or []:
        valid = removed.get("valid_replacements") or []
        assert isinstance(valid, list)
        for entry in valid:
            mid = int(entry.get("move_id") or 0)
            assert mid > 0
            assert mid in target_learnset, (
                f"Substituto sugerido {mid} não está no learnset Gen{tgt_gen}/#{ndex}"
            )
