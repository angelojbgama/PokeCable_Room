from __future__ import annotations

import math
import random


STAT_STAGE_MODIFIERS: dict[int, float] = {
    -6: 2 / 8,
    -5: 2 / 7,
    -4: 2 / 6,
    -3: 2 / 5,
    -2: 2 / 4,
    -1: 2 / 3,
    0: 2 / 2,
    1: 3 / 2,
    2: 4 / 2,
    3: 5 / 2,
    4: 6 / 2,
    5: 7 / 2,
    6: 8 / 2,
}

ACCURACY_EVASION_STAGE_MODIFIERS: dict[int, float] = {
    -6: 3 / 9,
    -5: 3 / 8,
    -4: 3 / 7,
    -3: 3 / 6,
    -2: 3 / 5,
    -1: 3 / 4,
    0: 3 / 3,
    1: 4 / 3,
    2: 5 / 3,
    3: 6 / 3,
    4: 7 / 3,
    5: 8 / 3,
    6: 9 / 3,
}

CRIT_CHANCE_STAGES_GEN2: dict[int, float] = {
    0: 1 / 15,
    1: 1 / 8,
    2: 1 / 4,
    3: 1 / 3,
    4: 1 / 2,
    5: 1 / 2,
    6: 1 / 2,
}


def determine_critical_gen2(crit_stage: int = 0, high_crit: bool = False) -> bool:
    stage = crit_stage + (1 if high_crit else 0)
    stage = max(0, min(6, stage))
    chance = CRIT_CHANCE_STAGES_GEN2.get(stage, 1 / 2)
    return random.random() < chance


def calculate_hit_gen2(accuracy: int, user_acc_stage: int, target_eva_stage: int) -> bool:
    if accuracy == 0:
        return True

    stage_diff = user_acc_stage - target_eva_stage
    stage_diff = max(-6, min(6, stage_diff))
    threshold = math.floor(accuracy * ACCURACY_EVASION_STAGE_MODIFIERS[stage_diff] * 255 / 100)
    if threshold > 255:
        threshold = 255
    return random.randint(0, 255) < threshold
