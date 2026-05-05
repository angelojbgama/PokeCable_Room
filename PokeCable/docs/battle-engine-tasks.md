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

- Gen 1: concluded and validated; keep only maintenance and future regressions if new mechanics are added.
- Gen 2: concluded for the current scope and validated with real saves; keep the engine isolated and extend coverage only when new Gen 2 edge cases are added.
- Gen 3: keep the battle path pure Gen 3, keep the conversion logic outside the engine, and add coverage.

## Test Files

- [api/tests/test_gen1_battle_engine.py](../api/tests/test_gen1_battle_engine.py)
- [api/tests/test_gen2_battle_engine.py](../api/tests/test_gen2_battle_engine.py)
- [api/tests/test_custom_battle_engine.py](../api/tests/test_custom_battle_engine.py)
- [api/tests/test_battles.py](../api/tests/test_battles.py)
