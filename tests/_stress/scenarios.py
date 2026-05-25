"""Scenario factories: synthetic CanonicalPokemon per (gen, dex_id, scenario_idx)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import fixtures  # noqa: F401 -- ensures sys.path is set
from canonical import CanonicalItem, CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats
from data.gender_rates import gender_from_gen2_attack_dv, gender_rate_for_species
from data.learnsets import get_learnable_moves
from data.moves import default_move_pp
from data.species import national_to_native, species_exists_in_generation

# Per-stat caps used when building canonical from src gen
DV_MAX = 15
IV_MAX = 31
STATEXP_MAX = 65535
EV_MAX = 252

# Trainer ID used everywhere for determinism
STRESS_TID = 0x1234


@dataclass(slots=True)
class Scenario:
    idx: int
    level: int
    dv_value: int  # 0..15 (for gen 1/2 sources) or scaled accordingly
    iv_value: int  # 0..31 (for gen 3 sources)
    stat_exp: int  # 0..65535 (gen 1/2)
    ev_value: int  # 0..252 (gen 3)
    has_item: bool
    gender: str | None  # "♂", "♀", or None
    is_shiny: bool
    move_chunk_idx: int


def _gender_options_for(dex_id: int) -> list[str | None]:
    rate = gender_rate_for_species(dex_id)
    if rate is None or rate == -1:
        return [None]
    if rate == 0:
        return ["♂"]
    if rate >= 8:
        return ["♀"]
    return ["♂", "♀"]


def _move_chunks(moves: list[int], chunk_size: int = 4) -> list[list[int]]:
    if not moves:
        return [[]]
    chunks: list[list[int]] = []
    for i in range(0, len(moves), chunk_size):
        chunks.append(moves[i : i + chunk_size])
    return chunks


def iter_scenarios(src_gen: int, dex_id: int) -> Iterator[Scenario]:
    """Yield deterministic Scenario descriptors covering the species' learnset.

    For every chunk of 4 moves in the learnset, yields ~4 scenario variants
    (extreme low / extreme high / shiny variant / alt-gender variant).
    """
    if not species_exists_in_generation(dex_id, src_gen):
        return
    learnset = get_learnable_moves(src_gen, dex_id) or []
    chunks = _move_chunks(learnset, 4)
    genders = _gender_options_for(dex_id)
    base_variants = [
        # (level, dv, iv, stat_exp, ev, has_item, shiny)
        (100, DV_MAX, IV_MAX, STATEXP_MAX, EV_MAX, True, False),
        (1, 0, 0, 0, 0, False, False),
        (100, DV_MAX, IV_MAX, STATEXP_MAX, EV_MAX, True, True),
        (50, 8, 16, 32768, 128, True, False),
    ]
    idx = 0
    for chunk_idx, _chunk in enumerate(chunks):
        for variant_idx, (level, dv, iv, stat_exp, ev, has_item, shiny) in enumerate(base_variants):
            # Pick gender deterministically — alternate when species has both
            gender = genders[(chunk_idx + variant_idx) % len(genders)]
            yield Scenario(
                idx=idx,
                level=level,
                dv_value=dv,
                iv_value=iv,
                stat_exp=stat_exp,
                ev_value=ev,
                has_item=has_item,
                gender=gender,
                is_shiny=shiny,
                move_chunk_idx=chunk_idx,
            )
            idx += 1


def _build_stats(src_gen: int, scenario: Scenario) -> tuple[CanonicalStats, CanonicalStats]:
    """Return (ivs, evs) populated for the scenario in the src gen's natural units."""
    if src_gen == 3:
        ivs = CanonicalStats(
            hp=scenario.iv_value,
            attack=scenario.iv_value,
            defense=scenario.iv_value,
            speed=scenario.iv_value,
            special=scenario.iv_value,
            special_attack=scenario.iv_value,
            special_defense=scenario.iv_value,
        )
        evs = CanonicalStats(
            hp=scenario.ev_value,
            attack=scenario.ev_value,
            defense=scenario.ev_value,
            speed=scenario.ev_value,
            special=scenario.ev_value,
            special_attack=scenario.ev_value,
            special_defense=scenario.ev_value,
        )
    else:
        # Gen 1/2: DVs (0..15) and Stat Experience (0..65535)
        ivs = CanonicalStats(
            hp=((scenario.dv_value & 1) << 3)
            | ((scenario.dv_value & 1) << 2)
            | ((scenario.dv_value & 1) << 1)
            | (scenario.dv_value & 1),  # placeholder; written byte will recompute
            attack=scenario.dv_value,
            defense=scenario.dv_value,
            speed=scenario.dv_value,
            special=scenario.dv_value,
            special_attack=scenario.dv_value,
            special_defense=scenario.dv_value,
        )
        evs = CanonicalStats(
            hp=scenario.stat_exp,
            attack=scenario.stat_exp,
            defense=scenario.stat_exp,
            speed=scenario.stat_exp,
            special=scenario.stat_exp,
            special_attack=scenario.stat_exp,
            special_defense=scenario.stat_exp,
        )
    return ivs, evs


def build_canonical(src_gen: int, dex_id: int, scenario: Scenario) -> CanonicalPokemon:
    """Synthesize a CanonicalPokemon representing the (gen, dex, scenario)."""
    learnset = get_learnable_moves(src_gen, dex_id) or []
    chunks = _move_chunks(learnset, 4)
    chunk = chunks[scenario.move_chunk_idx] if chunks and scenario.move_chunk_idx < len(chunks) else []
    moves: list[CanonicalMove] = []
    for move_id in chunk:
        max_pp = default_move_pp(move_id, src_gen, 0) or 1
        moves.append(
            CanonicalMove(
                move_id=int(move_id),
                pp=max_pp,
                max_pp=max_pp,
                pp_ups=0,
                source_generation=src_gen,
            )
        )
    ivs, evs = _build_stats(src_gen, scenario)
    source_species_id = national_to_native(src_gen, dex_id) or dex_id
    space = {1: "gen1_internal", 2: "national_dex", 3: "gen3_internal"}[src_gen]
    species = CanonicalSpecies(
        national_dex_id=int(dex_id),
        source_species_id=int(source_species_id),
        source_species_id_space=space,
        name=f"Mon{dex_id}",
    )
    # Gender must reflect what the source gen could realistically have produced:
    # - Gen 1: no gender at all (was added in Gen 2)
    # - Gen 2: derived from ATK DV
    # - Gen 3: free choice (target uses _adjust_personality_for_gender to honor it)
    if src_gen == 1:
        gender_for_metadata = None
    elif src_gen == 2:
        gender_for_metadata = gender_from_gen2_attack_dv(dex_id, scenario.dv_value)
    else:
        gender_for_metadata = scenario.gender
    metadata: dict = {
        "is_shiny": bool(scenario.is_shiny),
        "gender": gender_for_metadata,
        "source_species_id": source_species_id,
        "source_species_id_space": space,
    }
    held_item: CanonicalItem | None = None
    if scenario.has_item and src_gen in (2, 3):
        item_id = fixtures.representative_held_item(src_gen)
        if item_id:
            held_item = CanonicalItem(item_id=item_id, source_generation=src_gen)
    # Experience: derive from level using a constant growth rate placeholder.
    # Real exp is overwritten by parser/build logic only when needed; we set a stable value.
    experience = max(1, scenario.level) ** 3
    can = CanonicalPokemon(
        source_generation=src_gen,
        source_game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[src_gen],
        species_national_id=dex_id,
        species_name=species.name,
        nickname=species.name.upper()[:10],
        level=scenario.level,
        ot_name="STRESS",
        trainer_id=STRESS_TID,
        experience=experience,
        moves=moves,
        held_item=held_item,
        ivs=ivs,
        evs=evs,
        metadata=metadata,
        species=species,
    )
    return can
