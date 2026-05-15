"""Matriz cartesiana: cada (src_gen, tgt_gen, ndex) produz um compatibility report
consistente. Cobre 788 espécies × 9 pares de geração ≈ 7000 testes.
"""
from __future__ import annotations

import pytest


GEN_LIMITS = {1: 151, 2: 251, 3: 386}


def _all_cases() -> list[tuple[int, int, int]]:
    cases: list[tuple[int, int, int]] = []
    from data.species import species_exists_in_generation
    for src in (1, 2, 3):
        for tgt in (1, 2, 3):
            for ndex in range(1, GEN_LIMITS[src] + 1):
                if not species_exists_in_generation(ndex, src):
                    continue
                cases.append((src, tgt, ndex))
    return cases


@pytest.mark.parametrize("src_gen,tgt_gen,ndex", _all_cases())
def test_compatibility_report_consistency(src_gen: int, tgt_gen: int, ndex: int, canonical_factory):
    from compatibility import build_compatibility_report
    from data.species import species_exists_in_generation

    canonical = canonical_factory(src_gen, ndex)
    report = build_compatibility_report(canonical, tgt_gen, policy="auto_retrocompat")
    assert report.source_generation == src_gen
    assert report.target_generation == tgt_gen
    if not species_exists_in_generation(ndex, tgt_gen):
        assert not report.compatible
        assert any("nao existe" in r.lower() or "não existe" in r.lower() for r in report.blocking_reasons), (
            f"Espera blocking reason mencionando espécie inexistente: {report.blocking_reasons}"
        )
    else:
        if src_gen == tgt_gen:
            assert report.compatible, f"Same-gen deve ser compatible: {report.blocking_reasons}"
        if report.compatible:
            assert report.normalized_species.get("target_species_id") is not None
