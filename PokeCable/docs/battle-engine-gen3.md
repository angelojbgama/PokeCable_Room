# Battle Engine Gen 3

## Scope

- Ruby / Sapphire / Emerald / FireRed / LeafGreen only.
- Only accepts Gen 3 battle teams.
- No cross-generation normalization inside the battle engine.

## Implemented Core

- Gen 3 battle math.
- Abilities, held items, natures, weather, and modern stat handling.
- Native request generation for the Gen 3 battle router and UI.
- Singles and doubles battle flow kept isolated from Gen 1/2 payloads.
- Real-save 6v6 battle coverage via `tests/test_gen3_real_save_battle.py`.
- Real-save validation matrices via `tests/test_gen3_validation_matrix.py`, with report text files under `docs/battle-validation/`.
- Weather suppression and form handling for `Air Lock`, `Cloud Nine`, and `Forecast`.
- Weather moves and weather-aware recovery for `Rain Dance`, `Sunny Day`, `Sandstorm`, `Hail`, `Morning Sun`, `Synthesis`, and `Moonlight`.
- Status and volatile immunity handling for ability-gated cases like `Natural Cure`, `Rain Dish`, `Own Tempo`, `Oblivious`, and the core Gen 3 status immunities.
- Side conditions and accuracy flow for `Mist`, `Haze`, `Double Team`, `Minimize`, `Swift`, and the other never-miss moves used by the Gen 3 battle path.
- Sound-based move blocking for `Soundproof`, including the Gen 3 `Uproar` interaction.
- Low-HP move boosts for `Overgrow`, `Blaze`, `Torrent`, and `Swarm`.
- Party-wide status curing for `Heal Bell` and `Aromatherapy`, including the `Soundproof` exception on `Heal Bell`.
- Turn-order and lock-state handling for `Fake Out`, `Sleep Talk`, `Inner Focus`, `Perish Song`, `Suction Cups`, `Lightning Rod`, and `Damp`.
- Targeted real-save regressions for `Detect`, `Endure`, `Substitute`, `Whirlpool` and `Focus Punch`.
- Targeted real-save regressions for `Toxic`, `Recover` and `Fury Cutter`.
- Targeted real-save regressions for `Pressure`, `Foresight`, `Spikes` and `Soundproof`.
- Targeted real-save regressions for `Spite`, `Mimic` and `Metronome`.
- Targeted real-save regressions for `Counter`, `Mirror Coat`, `Bide`, and the doubles `Follow Me` redirection path tied to source tracking.
- Targeted real-save regression for `Triple Kick` power ramp and per-hit damage progression.
- Doubles request coverage and partner redirection support for `Helping Hand`, `Follow Me` and `Snatch`.
- Additional Gen 3 move coverage for `Leech Seed`, `Disable`, `Encore`, `Attract`, `Future Sight`, `Pursuit`, `Pain Split`, `Heal Bell`, `Refresh`, `Psych Up`, `Spite`, `Mimic`, `Metronome`, `Rollout`, `Stockpile`, `Spit Up`, `Swallow`, `Wish`, `Yawn`, `Nightmare`, `Mean Look`, `Torment`, `Lock On`, `Mind Reader`, `Conversion`, `Conversion 2`, `Role Play`, `Skill Swap`, `Curse`, `Belly Drum`, `Transform`, `Uproar`, `Growth`, `Calm Mind`, `Bulk Up`, `Dragon Dance`, `Razor Wind`, `Sky Attack`, `Skull Bash`, `Dive`, `Present`, `Pressure`, `Foresight` and `Spikes`.
- Item resolution on battle end.

## Remaining Work

- Keep the battle layer free of Gen 1/2 normalization logic.
- Add coverage for any future exotic Gen 3 move and ability edge cases discovered by new real saves.
