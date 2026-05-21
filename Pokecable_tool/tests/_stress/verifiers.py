"""Decode target-gen bytes back and assert retrocompatibility invariants."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from . import fixtures  # noqa: F401 -- sys.path bootstrap
from canonical import CanonicalPokemon
from data.gender_rates import gender_from_gen2_attack_dv, gender_from_gen3_personality, gender_rate_for_species
from data.items import equivalent_item_id
from data.moves import move_exists
from data.species import national_to_native
from parsers.gen3 import PARTY_MON_SIZE as G3_PARTY_SIZE, SECURE_SIZE as G3_SECURE_SIZE, SUBSTRUCT_ORDERS

GEN1_SHINY_ATTACK_DVS = {2, 3, 6, 7, 10, 11, 14, 15}


@dataclass(slots=True)
class Mismatch:
    field: str
    expected: Any
    actual: Any

    def __str__(self) -> str:
        return f"{self.field}: expected={self.expected!r} actual={self.actual!r}"


@dataclass(slots=True)
class Decoded:
    species: int = 0
    level: int = 0
    tid_low16: int = 0
    moves: list[int] = field(default_factory=list)
    pps: list[int] = field(default_factory=list)
    pp_ups: list[int] = field(default_factory=list)
    held_item: int = 0
    # Gen 1/2 layout
    dvs: tuple[int, int, int, int] | None = None  # atk,def,spd,spc
    stat_exp: tuple[int, int, int, int, int] | None = None  # hp,atk,def,spd,spc
    # Gen 3 layout
    pid: int = 0
    ivs: tuple[int, int, int, int, int, int] | None = None  # hp,atk,def,spe,spa,spd
    evs: tuple[int, int, int, int, int, int] | None = None
    # Derived
    gender: str | None = None
    is_shiny: bool = False


def decode_gen1(blob: bytes) -> Decoded:
    mon = blob
    species = mon[0]
    level = mon[0x21]
    tid = (mon[0x0C] << 8) | mon[0x0D]
    moves = [mon[0x08 + i] for i in range(4)]
    pp_bytes = [mon[0x1D + i] for i in range(4)]
    pps = [b & 0x3F for b in pp_bytes]
    pp_ups = [(b >> 6) & 0x03 for b in pp_bytes]
    dv1, dv2 = mon[0x1B], mon[0x1C]
    atk_dv, def_dv = dv1 >> 4, dv1 & 0xF
    spd_dv, spc_dv = dv2 >> 4, dv2 & 0xF
    stat_exp = (
        int.from_bytes(mon[0x11:0x13], "big"),
        int.from_bytes(mon[0x13:0x15], "big"),
        int.from_bytes(mon[0x15:0x17], "big"),
        int.from_bytes(mon[0x17:0x19], "big"),
        int.from_bytes(mon[0x19:0x1B], "big"),
    )
    shiny = atk_dv in GEN1_SHINY_ATTACK_DVS and def_dv == 10 and spd_dv == 10 and spc_dv == 10
    return Decoded(
        species=species,
        level=level,
        tid_low16=tid,
        moves=moves,
        pps=pps,
        pp_ups=pp_ups,
        held_item=0,
        dvs=(atk_dv, def_dv, spd_dv, spc_dv),
        stat_exp=stat_exp,
        gender=None,
        is_shiny=shiny,
    )


def decode_gen2(blob: bytes) -> Decoded:
    mon = blob
    species = mon[0]
    level = mon[0x1F]
    held = mon[0x01]
    tid = (mon[0x06] << 8) | mon[0x07]
    moves = [mon[0x02 + i] for i in range(4)]
    pp_bytes = [mon[0x17 + i] for i in range(4)]
    pps = [b & 0x3F for b in pp_bytes]
    pp_ups = [(b >> 6) & 0x03 for b in pp_bytes]
    dv1, dv2 = mon[0x15], mon[0x16]
    atk_dv, def_dv = dv1 >> 4, dv1 & 0xF
    spd_dv, spc_dv = dv2 >> 4, dv2 & 0xF
    stat_exp = (
        int.from_bytes(mon[0x0B:0x0D], "big"),
        int.from_bytes(mon[0x0D:0x0F], "big"),
        int.from_bytes(mon[0x0F:0x11], "big"),
        int.from_bytes(mon[0x11:0x13], "big"),
        int.from_bytes(mon[0x13:0x15], "big"),
    )
    gender = gender_from_gen2_attack_dv(species, atk_dv)
    shiny = atk_dv in GEN1_SHINY_ATTACK_DVS and def_dv == 10 and spd_dv == 10 and spc_dv == 10
    return Decoded(
        species=species,
        level=level,
        tid_low16=tid,
        moves=moves,
        pps=pps,
        pp_ups=pp_ups,
        held_item=held,
        dvs=(atk_dv, def_dv, spd_dv, spc_dv),
        stat_exp=stat_exp,
        gender=gender,
        is_shiny=shiny,
    )


def decode_gen3(blob: bytes, national_dex_id: int) -> Decoded:
    if len(blob) < G3_PARTY_SIZE:
        raise ValueError(f"Gen3 blob too short: {len(blob)}")
    pid = int.from_bytes(blob[0:4], "little")
    tid = int.from_bytes(blob[4:8], "little")
    level = blob[84]
    # Decrypt secure substructs
    key = pid ^ tid
    encrypted = blob[32 : 32 + G3_SECURE_SIZE]
    secure = bytearray(G3_SECURE_SIZE)
    for i in range(0, G3_SECURE_SIZE, 4):
        word = int.from_bytes(encrypted[i : i + 4], "little")
        secure[i : i + 4] = (word ^ key).to_bytes(4, "little")
    growth_idx, attacks_idx, evs_idx, misc_idx = SUBSTRUCT_ORDERS[pid % 24]
    growth_off = growth_idx * 12
    attacks_off = attacks_idx * 12
    evs_off = evs_idx * 12
    misc_off = misc_idx * 12
    species = int.from_bytes(secure[growth_off : growth_off + 2], "little")
    held = int.from_bytes(secure[growth_off + 2 : growth_off + 4], "little")
    moves = [int.from_bytes(secure[attacks_off + i * 2 : attacks_off + i * 2 + 2], "little") for i in range(4)]
    pp_ups_byte = secure[growth_off + 8]
    pp_ups = [(pp_ups_byte >> (i * 2)) & 3 for i in range(4)]
    pps = [secure[attacks_off + 8 + i] for i in range(4)]
    evs = tuple(secure[evs_off + i] for i in range(6))
    ivs_word = int.from_bytes(secure[misc_off : misc_off + 4], "little")
    ivs = tuple((ivs_word >> (i * 5)) & 0x1F for i in range(6))
    gender = gender_from_gen3_personality(national_dex_id, pid)
    shiny_val = (tid & 0xFFFF) ^ (tid >> 16) ^ (pid & 0xFFFF) ^ (pid >> 16)
    return Decoded(
        species=species,
        level=level,
        tid_low16=tid & 0xFFFF,
        moves=moves,
        pps=pps,
        pp_ups=pp_ups,
        held_item=held,
        pid=pid,
        ivs=ivs,
        evs=evs,
        gender=gender,
        is_shiny=shiny_val < 8,
    )


def _expected_iv_scaling(src_gen: int, target_gen: int, value: int) -> int:
    if src_gen == target_gen:
        return value
    if src_gen in (1, 2) and target_gen == 3:
        # DV (0..15) → IV (0..31): DV * 2
        return min(31, value * 2)
    if src_gen == 3 and target_gen in (1, 2):
        # IV (0..31) → DV (0..15): IV // 2
        return min(15, value // 2)
    # 1 ↔ 2 keep same DV semantic
    return value


def _expected_ev_scaling(src_gen: int, target_gen: int, value: int) -> int:
    if src_gen == target_gen:
        return value
    if src_gen in (1, 2) and target_gen == 3:
        # Stat Experience (0..65535) → EV (0..252): floor(StatExp / 256) capped 252
        return min(252, value // 256)
    if src_gen == 3 and target_gen in (1, 2):
        # EV (0..252) → Stat Experience: value * 256
        return min(65535, value * 256)
    return value


def verify(src_can: CanonicalPokemon, target_gen: int, blob: bytes, *, source_held_item: int | None) -> list[Mismatch]:
    """Verify a target-gen mon blob against the source canonical. Returns list of mismatches."""
    src_gen = int(src_can.source_generation)
    national_id = int(src_can.species_national_id)
    mismatches: list[Mismatch] = []

    if target_gen == 1:
        decoded = decode_gen1(blob)
    elif target_gen == 2:
        decoded = decode_gen2(blob)
    else:
        decoded = decode_gen3(blob, national_id)

    # 1. species byte
    expected_species = national_to_native(target_gen, national_id) or 0
    if decoded.species != expected_species:
        mismatches.append(Mismatch("species_byte", expected_species, decoded.species))

    # 2. level (clamped)
    expected_level = max(1, min(100, int(src_can.level)))
    if decoded.level != expected_level:
        mismatches.append(Mismatch("level", expected_level, decoded.level))

    # 3. TID low 16
    expected_tid = int(src_can.trainer_id) & 0xFFFF
    if decoded.tid_low16 != expected_tid:
        mismatches.append(Mismatch("tid_low16", expected_tid, decoded.tid_low16))

    # 4. moves: each non-zero move must exist in target gen
    src_move_ids = [m.move_id for m in (src_can.moves or [])]
    for slot, mv in enumerate(decoded.moves):
        if mv == 0:
            continue
        if not move_exists(mv, target_gen):
            mismatches.append(Mismatch(f"move[{slot}].in_target", True, False))

    # 5. moves dropped silently? After conversion, any src move that doesn't exist in target
    # AND wasn't dropped by report must be absent from blob.
    for src_mv in src_move_ids:
        if src_mv == 0:
            continue
        if not move_exists(src_mv, target_gen) and src_mv in decoded.moves:
            mismatches.append(Mismatch(f"incompatible_move_present", src_mv, "still present"))

    # 6. IVs / DVs scaling — check ATK as canonical representative
    if src_can.ivs is not None:
        src_atk = int(src_can.ivs.attack or 0)
        expected_atk = _expected_iv_scaling(src_gen, target_gen, src_atk)
        if target_gen == 3:
            actual_atk = decoded.ivs[1] if decoded.ivs else 0
        else:
            actual_atk = decoded.dvs[0] if decoded.dvs else 0
        # Gen 2 may intentionally nudge the ATK DV across the gender threshold
        # to honor metadata['gender'] (since Gen 2 stores no gender byte).
        gender_nudge_in_play = False
        if target_gen == 2 and src_can.metadata.get("gender") in ("♂", "♀"):
            rate = gender_rate_for_species(national_id)
            if rate is not None and 0 < rate < 8:
                gender_nudge_in_play = True
        if expected_atk != actual_atk and not gender_nudge_in_play:
            mismatches.append(Mismatch("iv_atk_scaling", expected_atk, actual_atk))
        elif gender_nudge_in_play and decoded.gender != src_can.metadata.get("gender"):
            # Shiny + variable-gender on rate-1/rate-7 species: no SHINY ATK DV satisfies the gender threshold.
            # Shiny preservation must win, so accept the gender mismatch in that scenario.
            shiny_conflict_ok = False
            if bool(src_can.metadata.get("is_shiny")):
                rate = gender_rate_for_species(national_id)
                if rate is not None and 0 < rate < 8:
                    threshold = rate * 2 - 1
                    shiny_set = {2, 3, 6, 7, 10, 11, 14, 15}
                    if src_can.metadata.get("gender") == "♀":
                        candidates = [dv for dv in shiny_set if dv <= threshold]
                    else:
                        candidates = [dv for dv in shiny_set if dv > threshold]
                    if not candidates:
                        shiny_conflict_ok = True
            if not shiny_conflict_ok:
                mismatches.append(Mismatch("gender_nudge_failed", src_can.metadata.get("gender"), decoded.gender))

    # 7. EVs / Stat Exp scaling — ATK channel
    if src_can.evs is not None:
        src_atk_ev = int(src_can.evs.attack or 0)
        expected_atk_ev = _expected_ev_scaling(src_gen, target_gen, src_atk_ev)
        if target_gen == 3:
            actual_atk_ev = decoded.evs[1] if decoded.evs else 0
        else:
            actual_atk_ev = decoded.stat_exp[1] if decoded.stat_exp else 0
        if expected_atk_ev != actual_atk_ev:
            mismatches.append(Mismatch("ev_atk_scaling", expected_atk_ev, actual_atk_ev))

    # 8. Held item
    if target_gen == 1:
        # Gen 1 doesn't store items — converter strips, expect 0
        if decoded.held_item != 0:
            mismatches.append(Mismatch("held_item_in_gen1", 0, decoded.held_item))
    else:
        if source_held_item:
            expected_item = equivalent_item_id(source_held_item, src_gen, target_gen) or 0
        else:
            expected_item = 0
        if decoded.held_item != expected_item:
            mismatches.append(Mismatch("held_item_mapped", expected_item, decoded.held_item))

    # 9. Gender preservation (target gen 2/3, species has variable gender)
    src_gender = src_can.metadata.get("gender") if src_can.metadata else None
    if target_gen in (2, 3) and src_gender in ("♂", "♀"):
        rate = gender_rate_for_species(national_id)
        if rate is not None and 0 < rate < 8:
            if decoded.gender != src_gender:
                # In Gen 2 target, shiny preservation may force ATK DV into SHINY set,
                # which can override gender on species with extreme gender rates.
                shiny_conflict_ok = False
                if target_gen == 2 and bool(src_can.metadata.get("is_shiny")):
                    threshold = rate * 2 - 1
                    shiny_set = {2, 3, 6, 7, 10, 11, 14, 15}
                    candidates = (
                        [dv for dv in shiny_set if dv <= threshold]
                        if src_gender == "♀" else [dv for dv in shiny_set if dv > threshold]
                    )
                    if not candidates:
                        shiny_conflict_ok = True
                if not shiny_conflict_ok:
                    mismatches.append(Mismatch("gender_preserved", src_gender, decoded.gender))

    # 10. Shiny preservation
    src_shiny = bool(src_can.metadata.get("is_shiny")) if src_can.metadata else False
    if src_shiny and not decoded.is_shiny:
        mismatches.append(Mismatch("shiny_preserved", True, False))

    return mismatches
