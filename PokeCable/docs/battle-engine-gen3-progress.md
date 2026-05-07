# Battle Engine Gen 3 Progress

## Done

- Kept the Gen 3 battle path isolated from Gen 1 and Gen 2.
- Added `generate_request()` to the Gen 3 engine so the router and UI can consume battle state.
- Added compatibility helpers for the router path and active slot access.
- Added doubles request coverage and partner redirection support for `Helping Hand`, `Follow Me` and `Snatch`.
- Added targeted Gen 3 mechanics coverage for `Detect`, `Endure`, `Substitute`, `Whirlpool` and `Focus Punch`.
- Added real-save coverage for `Toxic`, `Recover` and `Fury Cutter`.
- Added real-save coverage for `Pressure`, `Foresight` and `Spikes`.
- Added real-save source-tracking coverage for `Counter`, `Mirror Coat`, `Bide`, and the `Follow Me` redirection path used by doubles.
- Added real-save coverage for `Triple Kick` power ramp and per-hit damage progression.
- Added mechanics coverage for `Leech Seed`, `Disable`, `Encore`, `Attract`, `Future Sight`, `Pursuit`, `Pain Split`, `Heal Bell`, `Refresh`, `Psych Up`, `Spite`, `Mimic`, `Metronome` and `Rollout`.
- Added mechanics coverage for `Stockpile`, `Spit Up`, `Swallow`, `Wish`, `Yawn`, `Nightmare`, `Mean Look`, `Torment`, `Lock On`, `Mind Reader`, `Conversion`, `Conversion 2`, `Role Play`, `Skill Swap`, `Curse`, `Belly Drum`, `Transform`, `Uproar`, `Growth`, `Calm Mind`, `Bulk Up`, `Dragon Dance`, `Razor Wind`, `Sky Attack`, `Skull Bash`, `Dive`, `Present`, `Pressure`, `Foresight` and `Spikes`.
- Added weather, ability, and field-state coverage for `Air Lock`, `Cloud Nine`, `Forecast`, `Natural Cure`, `Rain Dish`, `Mist`, `Haze`, `Double Team`, `Minimize`, `Swift`, and the other never-miss moves handled by the Gen 3 engine.
- Added synthetic `Forecast` coverage for Castform reverting to its original form when weather is suppressed.
- Added sound move coverage for `Soundproof` and the Gen 3 `Uproar` interaction.
- Added low-HP damage boost coverage for `Overgrow`, `Blaze`, `Torrent`, and `Swarm`.
- Added party-wide status cure coverage for `Heal Bell` and `Aromatherapy`, including the `Soundproof` exception on `Heal Bell`.
- Added turn-order and lock-state coverage for `Fake Out`, `Sleep Talk`, `Inner Focus`, `Perish Song`, `Suction Cups`, `Lightning Rod`, and `Damp`.
- Added synthetic Gen 3 mechanics regression coverage in `tests/test_gen3_mechanics.py`.
- Added real-save regressions for `Spite`, `Mimic` and `Metronome`.
- Added synthetic coverage for `Stockpile`, `Yawn`, `Nightmare`, `Lock On` and `Transform`.
- Added synthetic coverage for `Swarm`.
- Added real-save regressions for `Calm Mind` and `Dive`.
- Added real-save regressions for `Overgrow`, `Blaze`, `Torrent`, and `Soundproof`.
- Added real-save doubles request coverage for active-slot payloads and per-move target labels.
- Built a real-save 6v6 battle test with Gen 3 parser data from the local `save/gen 3` folder.
- Used deterministic RNG in the test harness so the battle resolves consistently.
- Validated that the battle reaches exhaustion, emits a win log, and keeps both teams at 6 members.
- Confirmed the targeted real-save regressions pass with the same isolated Gen 3 engine path.
- Added a real-save validation matrix for all team members and move sets in singles, plus a doubles-oriented validation matrix, with reports in `docs/battle-validation/gen3-matrix.txt` and `docs/battle-validation/gen3-doubles-matrix.txt`. The generated baseline reports are now free of internal `DEBUG` noise from the engine.
- Added a focused real-save validation report for `Counter`, `Mirror Coat`, and `Bide` source tracking in `docs/battle-validation/gen3-counter-mirrorcoat-bide.txt`.
- Added a focused real-save validation report for `Triple Kick` power progression in `docs/battle-validation/gen3-triple-kick.txt`.

## Validation

- `python3 -m pytest -q tests/test_gen3_mechanics.py tests/test_gen3_real_save_battle.py`
- Result: `59 passed`
- `python3 -m pytest -q tests/test_gen3_validation_matrix.py`
- Result: `2 passed`
- Matrix summaries: `pass=288 fail=0 total=288` and `pass=96 fail=0 total=96`
- `python3 -m pytest -q tests/test_battles.py tests/test_custom_battle_engine.py tests/test_gen1_battle_engine.py tests/test_gen1_real_save_battle.py tests/test_gen2_types.py tests/test_gen2_battle_engine.py tests/test_gen2_mechanics.py tests/test_gen2_real_save_battle.py tests/test_gen3_validation_matrix.py tests/test_gen3_mechanics.py tests/test_gen3_real_save_battle.py`
- Result: `141 passed`
- `python3 -m pytest -q tests/test_gen3_mechanics.py tests/test_gen3_real_save_battle.py tests/test_battles.py tests/test_custom_battle_engine.py`
- Result: `70 passed`

## Remaining Work

- Keep accepting new real-save regressions if future saves expose a new edge case.
- Capture any exotic Gen 3 edge cases that still surface in future saves.
