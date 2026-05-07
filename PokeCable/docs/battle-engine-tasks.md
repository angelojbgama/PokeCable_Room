# Battle Engine Tasks

The battle layer is split by generation and does not allow cross-generation battles.
Battle normalization for saves stays in the conversion layer, not inside the battle engines.

## Scope

- [Gen 1 Engine](./battle-engine-gen1.md)
- [Gen 2 Engine](./battle-engine-gen2.md)
- [Gen 3 Engine](./battle-engine-gen3.md)

## Current Rules

- Gen 1 only battles Gen 1.
- Gen 2 only battles Gen 2.
- Gen 3 only battles Gen 3.
- Battle rooms must reject mixed-generation teams.
- The Gen 3 battle engine must not auto-normalize Gen 1/2 payloads.

## What Still Needs Work

- Gen 1: concluded and validated; keep only maintenance and future regressions if new mechanics are added. The exhaustive validation matrix lives in `docs/battle-validation/gen1-matrix.txt`.
- Gen 2: concluded for the current scope and validated with real saves; keep the engine isolated and extend coverage only when new Gen 2 edge cases are added. The exhaustive validation matrix lives in `docs/battle-validation/gen2-matrix.txt`.
- Gen 3: concluded and validated with real saves. Keep the battle path pure Gen 3 and keep conversion logic outside the engine; extend only through future regressions if new Gen 3 edge cases are discovered. The current engine covers the core singles move families, the doubles request/redirection path, weather suppression and Forecast, Mist/Haze field flow, Soundproof sound-move blocking, low-HP ability boosts, and the current Pressure / Foresight / Spikes / Heal Bell / Lightning Rod / Perish Song / Counter / Mirror Coat / Bide / Triple Kick regressions. The singles and doubles validation matrices live in `docs/battle-validation/gen3-matrix.txt` and `docs/battle-validation/gen3-doubles-matrix.txt`, and the focused source-tracking / power-progression reports live in `docs/battle-validation/gen3-counter-mirrorcoat-bide.txt` and `docs/battle-validation/gen3-triple-kick.txt`. These baseline reports are regenerated without internal `DEBUG` noise.

## Test Files

- [api/tests/test_gen1_battle_engine.py](../api/tests/test_gen1_battle_engine.py)
- [api/tests/test_gen2_battle_engine.py](../api/tests/test_gen2_battle_engine.py)
- [api/tests/test_custom_battle_engine.py](../api/tests/test_custom_battle_engine.py)
- [api/tests/test_gen3_mechanics.py](../api/tests/test_gen3_mechanics.py)
- [api/tests/test_gen3_real_save_battle.py](../api/tests/test_gen3_real_save_battle.py)
- [api/tests/test_battles.py](../api/tests/test_battles.py)
