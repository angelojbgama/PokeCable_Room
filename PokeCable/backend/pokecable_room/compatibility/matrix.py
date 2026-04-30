from __future__ import annotations


SAME_GENERATION = "same_generation"
TIME_CAPSULE_GEN1_GEN2 = "time_capsule_gen1_gen2"
FORWARD_TRANSFER_TO_GEN3 = "forward_transfer_to_gen3"
LEGACY_DOWNCONVERT_EXPERIMENTAL = "legacy_downconvert_experimental"
UNSUPPORTED = "unsupported"


TRADE_MODE_MATRIX: dict[tuple[int, int], str] = {
    (1, 1): SAME_GENERATION,
    (2, 2): SAME_GENERATION,
    (3, 3): SAME_GENERATION,
    (1, 2): TIME_CAPSULE_GEN1_GEN2,
    (2, 1): TIME_CAPSULE_GEN1_GEN2,
    (1, 3): FORWARD_TRANSFER_TO_GEN3,
    (2, 3): FORWARD_TRANSFER_TO_GEN3,
    (3, 1): LEGACY_DOWNCONVERT_EXPERIMENTAL,
    (3, 2): LEGACY_DOWNCONVERT_EXPERIMENTAL,
}


def get_trade_mode(source_generation: int, target_generation: int) -> str:
    return TRADE_MODE_MATRIX.get((int(source_generation), int(target_generation)), UNSUPPORTED)


def is_cross_generation(source_generation: int, target_generation: int) -> bool:
    return int(source_generation) != int(target_generation)


def supported_modes_for_generation(generation: int) -> list[str]:
    generation = int(generation)
    modes = {mode for (source, target), mode in TRADE_MODE_MATRIX.items() if source == generation or target == generation}
    return sorted(modes)
