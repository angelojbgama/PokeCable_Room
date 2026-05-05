# Battle Engine Gen 1

## Status

- Concluída e validada pela suíte `tests/test_gen1_battle_engine.py`.
- Nenhuma pendência conhecida dentro do escopo da Gen 1.

## Scope

- Red / Blue / Yellow only.
- Only accepts Gen 1 battle teams.
- No retrocompatibility in the battle layer.

## Implemented Core

- Gen 1 damage formula.
- Gen 1 critical hits.
- Gen 1 accuracy glitch behavior.
- Sleep and freeze handling.
- Partial trapping moves block actions and switches.
- Hyper Beam recharge handling.
- Disable, Leech Seed, Bide, Rage, Mimic, Mirror Move, Transform, Conversion, Metronome, Counter, OHKO, recoil, drain, and end-turn status damage.
- Targeted regression coverage for the implemented Gen 1 mechanics.
- Real-save 6v6 regression using Yellow vs Red with exhaustion flow.

## Validation

- `python3 -m pytest -q tests/test_gen1_battle_engine.py tests/test_gen1_real_save_battle.py` -> `37 passed`
- `python3 -m py_compile app/engines/gen1/models.py app/engines/gen1/utils.py app/engines/gen1/damage.py app/engines/gen1/engine.py tests/test_gen1_battle_engine.py`
