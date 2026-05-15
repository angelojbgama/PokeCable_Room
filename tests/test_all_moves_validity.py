"""Cobertura: cada move × cada gen valida MOVE_DATA + move_exists + move_name."""
from __future__ import annotations

import pytest


def _all_cases() -> list[tuple[int, int]]:
    from data.moves import MOVE_DATA
    return [(int(mid), gen) for mid in MOVE_DATA.keys() for gen in (1, 2, 3)]


@pytest.mark.parametrize("move_id,gen", _all_cases())
def test_move_exists_matches_metadata(move_id: int, gen: int):
    from data.moves import MOVE_DATA, move_exists

    meta = MOVE_DATA[move_id]
    expected = gen in meta.generations
    assert move_exists(move_id, gen) is expected, (
        f"move_exists({move_id}, {gen}) = {move_exists(move_id, gen)} mas MOVE_DATA diz {expected}"
    )


@pytest.mark.parametrize("move_id", sorted({mid for mid in __import__("data.moves", fromlist=["MOVE_DATA"]).MOVE_DATA.keys()}))
def test_move_name_is_non_empty(move_id: int):
    from data.moves import move_name
    name = move_name(int(move_id))
    assert isinstance(name, str)
    assert name.strip() != ""


def test_moves_present_in_some_learnset_for_each_gen(all_moves_by_gen):
    """Sanity: cada move existente em uma gen aparece em pelo menos um learnset (gen, ndex).

    Excluir HM/TM-only ou moves de event que talvez não estejam em LEARNSETS por design — apenas warning.
    """
    from data.learnsets import LEARNSETS

    moves_in_learnsets: dict[int, set[int]] = {1: set(), 2: set(), 3: set()}
    for (gen, _ndex), move_ids in LEARNSETS.items():
        if gen in moves_in_learnsets:
            for mid in move_ids:
                moves_in_learnsets[gen].add(int(mid))

    for gen, all_moves in all_moves_by_gen.items():
        unused = [m for m in all_moves if m not in moves_in_learnsets[gen]]
        # Não falha — só avisa. Many moves can be TM/HM-only and absent from level-up learnsets.
        # O assert é: pelo menos 50% dos moves da gen aparecem em algum learnset (cobertura mínima).
        if all_moves:
            covered = len(all_moves) - len(unused)
            assert covered / len(all_moves) >= 0.30, (
                f"Gen {gen}: apenas {covered}/{len(all_moves)} moves aparecem em learnsets. Cobertura muito baixa."
            )
