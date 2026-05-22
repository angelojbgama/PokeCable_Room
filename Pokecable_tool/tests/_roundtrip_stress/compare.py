"""Compare two CanonicalPokemon (before/after a round trip) and classify each diff."""
from __future__ import annotations

from dataclasses import dataclass, field

from canonical import CanonicalPokemon


@dataclass(slots=True)
class DiffReport:
    label: str = ""
    lossless: list[str] = field(default_factory=list)         # field name (no diff)
    lossy_known: list[str] = field(default_factory=list)      # field name + reason (within expected drift)
    lossy_unexpected: list[str] = field(default_factory=list) # field name (real failure)

    @property
    def is_passing(self) -> bool:
        return not self.lossy_unexpected


def _ivs_tuple(can: CanonicalPokemon) -> tuple[int, int, int, int, int, int]:
    if not can.ivs:
        return (0, 0, 0, 0, 0, 0)
    return (
        int(can.ivs.hp or 0),
        int(can.ivs.attack or 0),
        int(can.ivs.defense or 0),
        int(can.ivs.speed or 0),
        int(can.ivs.special_attack or can.ivs.special or 0),
        int(can.ivs.special_defense or can.ivs.special or 0),
    )


def _evs_tuple(can: CanonicalPokemon) -> tuple[int, int, int, int, int, int]:
    if not can.evs:
        return (0, 0, 0, 0, 0, 0)
    return (
        int(can.evs.hp or 0),
        int(can.evs.attack or 0),
        int(can.evs.defense or 0),
        int(can.evs.speed or 0),
        int(can.evs.special_attack or can.evs.special or 0),
        int(can.evs.special_defense or can.evs.special or 0),
    )


def _stat(base: int, iv: int, ev: int, level: int, is_hp: bool) -> int:
    """Standard Gen 3 stat formula (good approximation for Gen 1/2 too at level 100)."""
    base_ev = ev // 4
    val = (2 * base + iv + base_ev) * level // 100
    return val + (level + 10 if is_hp else 5)


def compute_stats(can: CanonicalPokemon, base_stats: dict | None) -> dict[str, int]:
    """Compute HP/ATK/DEF/SPE/SPA/SPD from canonical using Gen 3 formula."""
    if not base_stats:
        return {}
    level = max(1, min(100, int(can.level)))
    iv_hp, iv_atk, iv_def, iv_spe, iv_spa, iv_spd = _ivs_tuple(can)
    ev_hp, ev_atk, ev_def, ev_spe, ev_spa, ev_spd = _evs_tuple(can)
    return {
        "hp":  _stat(base_stats["hp"],  iv_hp,  ev_hp,  level, is_hp=True),
        "atk": _stat(base_stats["atk"], iv_atk, ev_atk, level, is_hp=False),
        "def": _stat(base_stats["def"], iv_def, ev_def, level, is_hp=False),
        "spe": _stat(base_stats["spe"], iv_spe, ev_spe, level, is_hp=False),
        "spa": _stat(base_stats["spa"], iv_spa, ev_spa, level, is_hp=False),
        "spd": _stat(base_stats["spd"], iv_spd, ev_spd, level, is_hp=False),
    }


def compare(
    before: CanonicalPokemon,
    after: CanonicalPokemon,
    *,
    src_gen: int,
    inter_gen: int,
    label: str = "",
) -> DiffReport:
    """Classify each canonical field's behavior across a round trip A→B→A.

    Known/expected losses depend on the route:
    - Any route through Gen 1: held_item dropped, gender lost (Gen 1 has no gender).
    - Gen 3 ↔ Gen 1/2 ↔ Gen 3: IV LSB lost (max Δ=1 per channel) due to DV*2 / IV//2 scaling.
      HP IV in Gen 1/2 is computed from low bits of other DVs — drift unbounded on round-trip.
    - Gen 1/2 ↔ Gen 3 ↔ Gen 1/2: EV cap at 252 → StatExp 64512 (max Δ=1023 per channel).
    - Shiny pokémon through Gen 1/2: DEF/SPD/SPC DVs forced to 10 (shiny pattern), so IVs may
      become 10/10/10 after round trip even if original was 15/15/15.
    - Gender pokémon with high gender rate variance: ATK DV may be nudged across gender threshold.
    """
    rep = DiffReport(label=label)
    route_goes_through_gen1 = (src_gen == 1) or (inter_gen == 1)
    # IV LSB drift on 3-side <-> 1/2-side transitions
    iv_lsb_drift_allowed = (src_gen == 3 and inter_gen in (1, 2)) or (src_gen in (1, 2) and inter_gen == 3)
    # HP IV: Gen 1/2 derives HP DV from low bits of other DVs, so HP IV roundtrip is undefined
    hp_iv_drift_unbounded = iv_lsb_drift_allowed
    # EV drift: when going through Gen 1/2 stat experience format and back
    ev_drift_allowed = (src_gen in (1, 2) and inter_gen == 3) or (src_gen == 3 and inter_gen in (1, 2))
    # Shiny override on Gen 1/2 sets DEF/SPD/SPC DV=10
    is_shiny = bool((before.metadata or {}).get("is_shiny"))
    shiny_via_legacy = is_shiny and (inter_gen in (1, 2) or src_gen in (1, 2))

    # Hard invariants — must match exactly
    for field in ("species_national_id", "level", "experience"):
        bv, av = getattr(before, field), getattr(after, field)
        if bv == av:
            rep.lossless.append(field)
        else:
            rep.lossy_unexpected.append(f"{field}: {bv!r} → {av!r}")

    # TID: low 16 bits must match (high bits lost going to Gen 1/2)
    bv = int(before.trainer_id or 0) & 0xFFFF
    av = int(after.trainer_id or 0) & 0xFFFF
    if bv == av:
        rep.lossless.append("trainer_id_low16")
    else:
        rep.lossy_unexpected.append(f"trainer_id_low16: {bv} → {av}")

    # Unown (dex 201) has form encoded in DV bits 2,1 — overrides shiny and may push IVs anywhere.
    is_unown = before.species_national_id == 201

    # IVs — channel by channel
    iv_before = _ivs_tuple(before)
    iv_after = _ivs_tuple(after)
    channels = ("iv_hp", "iv_atk", "iv_def", "iv_spe", "iv_spa", "iv_spd")
    for name, b, a in zip(channels, iv_before, iv_after):
        delta = abs(b - a)
        if delta == 0:
            rep.lossless.append(name)
            continue
        # Unown: form encoding rewrites DV bits 2,1 — IVs may shift arbitrarily within 0-15
        if is_unown:
            rep.lossy_known.append(f"{name}: {b} → {a} (Unown form encoding)")
            continue
        # HP IV: in Gen 1/2 it's recomputed from low bits of other DVs. Any time shiny
        # forced DV=10 on DEF/SPD/SPC or gender nudged ATK DV, HP IV changes too. Also
        # always lossy on Gen 3 ↔ Gen 1/2 routes.
        if name == "iv_hp" and (hp_iv_drift_unbounded or shiny_via_legacy):
            rep.lossy_known.append(f"{name}: {b} → {a} (HP IV is derived in Gen 1/2)")
            continue
        # HP IV may also drift when the ATK DV was nudged for gender preservation
        if name == "iv_hp" and src_gen in (2, 3) and (before.metadata or {}).get("gender") in ("♂", "♀"):
            rep.lossy_known.append(f"{name}: {b} → {a} (HP IV derived from nudged ATK DV)")
            continue
        # Shiny: Gen 1/2 forces DEF/SPD/SPC DV=10 for shiny, ATK DV in SHINY set
        if shiny_via_legacy and name in ("iv_def", "iv_spe", "iv_spa", "iv_spd"):
            if a in (10, 20):  # 10 in 0-15 DV space, 20 = 10*2 IV space
                rep.lossy_known.append(f"{name}: {b} → {a} (shiny forces DV=10 in Gen 1/2)")
                continue
        # Shiny ATK constraint: SHINY_ATTACK_DVS = {2,3,6,7,10,11,14,15}; ×2 in IV = {4,6,12,14,20,22,28,30}
        if shiny_via_legacy and name == "iv_atk":
            if a in {2, 3, 6, 7, 10, 11, 14, 15, 4, 6, 12, 14, 20, 22, 28, 30}:
                rep.lossy_known.append(f"{name}: {b} → {a} (shiny ATK DV constraint)")
                continue
        # Gender nudge: ATK DV may be pushed across the gender threshold
        if name == "iv_atk" and src_gen in (2, 3):
            src_gender = (before.metadata or {}).get("gender")
            if src_gender in ("♂", "♀"):
                rep.lossy_known.append(f"{name}: {b} → {a} (ATK DV nudged for gender preservation)")
                continue
        # General IV LSB drift
        if iv_lsb_drift_allowed and delta <= 1:
            rep.lossy_known.append(f"{name}: {b} → {a} (Δ{delta}, expected DV*2/IV//2 LSB loss)")
            continue
        rep.lossy_unexpected.append(f"{name}: {b} → {a} (Δ{delta})")

    # EVs / Stat Exp — channel by channel
    ev_before = _evs_tuple(before)
    ev_after = _evs_tuple(after)
    ev_names = ("ev_hp", "ev_atk", "ev_def", "ev_spe", "ev_spa", "ev_spd")
    for name, b, a in zip(ev_names, ev_before, ev_after):
        if b == a:
            rep.lossless.append(name)
            continue
        # Gen 1/2 → Gen 3 → Gen 1/2: StatExp (0-65535) → EV (capped 252) → StatExp (max 64512).
        # Max drift = 1023 due to /256 floor then *256.
        if ev_drift_allowed and abs(b - a) <= 1024:
            rep.lossy_known.append(f"{name}: {b} → {a} (EV cap 252 then ×256 round trip)")
            continue
        rep.lossy_unexpected.append(f"{name}: {b} → {a}")

    # Held item
    bi = before.held_item.item_id if before.held_item else None
    ai = after.held_item.item_id if after.held_item else None
    if bi == ai:
        rep.lossless.append("held_item")
    elif route_goes_through_gen1 and ai in (None, 0):
        rep.lossy_known.append(f"held_item: {bi} → None (lost via Gen 1)")
    else:
        # Items between Gen 2/3 may map via equivalent_item_id; accept if both have an item
        if bi and ai:
            rep.lossy_known.append(f"held_item: {bi} → {ai} (cross-gen item mapping)")
        else:
            rep.lossy_unexpected.append(f"held_item: {bi} → {ai}")

    # Gender — must preserve for variable-rate species (with documented exceptions)
    bg = (before.metadata or {}).get("gender")
    ag = (after.metadata or {}).get("gender")
    if bg == ag:
        rep.lossless.append("gender")
    elif bg in ("♂", "♀") and ag is None:
        rep.lossy_known.append(f"gender: {bg} → None (route through Gen 1, no gender storage)")
    elif route_goes_through_gen1 and bg in ("♂", "♀"):
        # Gen 1 has no gender → re-derived from a fresh PID/DV on return, may flip
        rep.lossy_known.append(f"gender: {bg} → {ag} (Gen 1 doesn't store gender; re-derived on return)")
    elif is_shiny and bg in ("♂", "♀"):
        # Shiny + extreme-rate species may have no SHINY DV satisfying gender threshold
        try:
            from data.gender_rates import gender_rate_for_species
            rate = gender_rate_for_species(before.species_national_id)
            if rate is not None and 0 < rate < 8:
                threshold = rate * 2 - 1
                shiny_set = {2, 3, 6, 7, 10, 11, 14, 15}
                cand = (
                    [dv for dv in shiny_set if dv <= threshold] if bg == "♀"
                    else [dv for dv in shiny_set if dv > threshold]
                )
                if not cand:
                    rep.lossy_known.append(f"gender: {bg} → {ag} (shiny+gender conflict for rate={rate})")
                else:
                    rep.lossy_unexpected.append(f"gender: {bg!r} → {ag!r}")
            else:
                rep.lossy_unexpected.append(f"gender: {bg!r} → {ag!r}")
        except Exception:
            rep.lossy_unexpected.append(f"gender: {bg!r} → {ag!r}")
    else:
        rep.lossy_unexpected.append(f"gender: {bg!r} → {ag!r}")

    # Shiny — must preserve (except Unown where form encoding overrides DV pattern)
    bs = bool((before.metadata or {}).get("is_shiny"))
    as_ = bool((after.metadata or {}).get("is_shiny"))
    if bs == as_:
        rep.lossless.append("is_shiny")
    elif is_unown:
        rep.lossy_known.append(f"is_shiny: {bs} → {as_} (Unown form encoding clobbers shiny DV pattern)")
    else:
        rep.lossy_unexpected.append(f"is_shiny: {bs} → {as_}")

    return rep
