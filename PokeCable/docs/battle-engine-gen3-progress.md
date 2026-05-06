# Battle Engine Gen 3 Progress

## Done

- Kept the Gen 3 battle path isolated from Gen 1 and Gen 2.
- Added `generate_request()` to the Gen 3 engine so the router and UI can consume battle state.
- Added compatibility helpers for the router path and active slot access.
- Added doubles request coverage and partner redirection support for `Helping Hand`, `Follow Me` and `Snatch`.
- Added targeted Gen 3 mechanics coverage for `Detect`, `Endure`, `Substitute`, `Whirlpool` and `Focus Punch`.
- Added real-save coverage for `Toxic`, `Recover` and `Fury Cutter`.
- Added real-save coverage for `Pressure`, `Foresight` and `Spikes`.
- Added mechanics coverage for `Leech Seed`, `Disable`, `Encore`, `Attract`, `Future Sight`, `Pursuit`, `Pain Split`, `Heal Bell`, `Refresh`, `Psych Up`, `Spite`, `Mimic`, `Metronome` and `Rollout`.
- Added mechanics coverage for `Stockpile`, `Spit Up`, `Swallow`, `Wish`, `Yawn`, `Nightmare`, `Mean Look`, `Torment`, `Lock On`, `Mind Reader`, `Conversion`, `Conversion 2`, `Role Play`, `Skill Swap`, `Curse`, `Belly Drum`, `Transform`, `Uproar`, `Growth`, `Calm Mind`, `Bulk Up`, `Dragon Dance`, `Razor Wind`, `Sky Attack`, `Skull Bash`, `Dive`, `Present`, `Pressure`, `Foresight` and `Spikes`.
- Added synthetic Gen 3 mechanics regression coverage in `tests/test_gen3_mechanics.py`.
- Added real-save regressions for `Spite`, `Mimic` and `Metronome`.
- Added synthetic coverage for `Stockpile`, `Yawn`, `Nightmare`, `Lock On` and `Transform`.
- Added real-save regressions for `Calm Mind` and `Dive`.
- Added real-save doubles request coverage for active-slot payloads and per-move target labels.
- Built a real-save 6v6 battle test with Gen 3 parser data from the local `save/gen 3` folder.
- Used deterministic RNG in the test harness so the battle resolves consistently.
- Validated that the battle reaches exhaustion, emits a win log, and keeps both teams at 6 members.
- Confirmed the targeted real-save regressions pass with the same isolated Gen 3 engine path.

## Validation

- `python3 -m pytest -q tests/test_gen3_mechanics.py tests/test_gen3_real_save_battle.py tests/test_battles.py tests/test_custom_battle_engine.py`
- Result: `49 passed`

## Remaining Work

- Add more real-save regression pairs for Gen 3 if we want broader coverage.
- Capture any exotic Gen 3 edge cases that still surface in future saves.
