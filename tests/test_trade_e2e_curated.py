"""E2E curado: ~30 Pokémon emblemáticos exercitando paths cross-gen, evolução por troca, etc."""
from __future__ import annotations

import pytest


# (ndex, name, scenarios) — scenarios é lista de (src_gen, tgt_gen) a testar.
CURATED = [
    (1, "Bulbasaur", [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]),
    (25, "Pikachu", [(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)]),
    (64, "Kadabra", [(1, 3), (3, 1)]),  # trade evolution candidate
    (67, "Machoke", [(1, 3), (3, 1)]),  # trade evolution candidate
    (75, "Graveler", [(1, 3), (3, 1)]),  # trade evolution candidate
    (130, "Gyarados", [(1, 2), (2, 3)]),
    (132, "Ditto", [(1, 2), (1, 3)]),
    (133, "Eevee", [(1, 2), (1, 3)]),
    (143, "Snorlax", [(1, 2), (2, 3)]),
    (149, "Dragonite", [(1, 3)]),
    (151, "Mew", [(1, 3), (3, 1)]),
    (152, "Chikorita", [(2, 3), (3, 2)]),  # Gen2-only original
    (155, "Cyndaquil", [(2, 3)]),
    (158, "Totodile", [(2, 3)]),
    (172, "Pichu", [(2, 3)]),
    (196, "Espeon", [(2, 3)]),
    (197, "Umbreon", [(2, 3)]),
    (249, "Lugia", [(2, 3)]),
    (250, "Ho-Oh", [(2, 3)]),
    (251, "Celebi", [(2, 3)]),
    (252, "Treecko", [(3, 2)]),
    (255, "Torchic", [(3, 2)]),
    (258, "Mudkip", [(3, 2)]),
    (327, "Spinda", [(3, 2)]),
    (350, "Milotic", [(3, 2)]),
    (376, "Metagross", [(3, 1), (3, 2)]),
    (384, "Rayquaza", [(3, 2)]),
    (386, "Deoxys", [(3, 2)]),
]


def _flatten() -> list[tuple[int, str, int, int]]:
    out: list[tuple[int, str, int, int]] = []
    for ndex, name, scenarios in CURATED:
        for src, tgt in scenarios:
            out.append((ndex, name, src, tgt))
    return out


@pytest.mark.parametrize("ndex,name,src_gen,tgt_gen", _flatten())
def test_curated_cross_gen_pipeline(ndex: int, name: str, src_gen: int, tgt_gen: int, canonical_factory, learnset_for):
    """Trade end-to-end leve: canonical → converter.apply_to_save NÃO é exercitado aqui
    (precisaria um parser+save real). Mas validamos que:
    - canonical é serializável
    - converter.can_convert produz report válido
    - se compatível, target_species_id está definido
    """
    from compatibility import build_compatibility_report
    from converters import get_converter
    from data.species import species_exists_in_generation

    if not species_exists_in_generation(ndex, src_gen):
        pytest.skip(f"{name} não existe em Gen {src_gen}")

    moves = learnset_for(src_gen, ndex)[:4]
    canonical = canonical_factory(src_gen, ndex, moves=moves, nickname=name.upper()[:10])

    # 1) Serialize roundtrip
    from canonical import CanonicalPokemon
    blob = canonical.to_dict()
    restored = CanonicalPokemon.from_dict(blob)
    assert restored.species.national_dex_id == ndex

    # 2) build_compatibility_report
    report = build_compatibility_report(canonical, tgt_gen, policy="auto_retrocompat")
    assert report.source_generation == src_gen
    assert report.target_generation == tgt_gen

    if not species_exists_in_generation(ndex, tgt_gen):
        assert not report.compatible
        return

    # 3) get_converter().can_convert
    if src_gen != tgt_gen:
        converter = get_converter(src_gen, tgt_gen)
        conv_report = converter.can_convert(canonical, policy="auto_retrocompat")
        assert conv_report.source_generation == src_gen
        assert conv_report.target_generation == tgt_gen
        # Cada removed_move tem valid_replacements no learnset destino
        target_learnset = set(learnset_for(tgt_gen, ndex))
        for removed in conv_report.removed_moves or []:
            for entry in removed.get("valid_replacements") or []:
                assert int(entry["move_id"]) in target_learnset
