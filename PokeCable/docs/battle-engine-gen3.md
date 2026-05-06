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
- Targeted real-save regressions for `Detect`, `Endure`, `Substitute`, `Whirlpool` and `Focus Punch`.
- Targeted real-save regressions for `Toxic`, `Recover` and `Fury Cutter`.
- Targeted real-save regressions for `Pressure`, `Foresight` and `Spikes`.
- Targeted real-save regressions for `Spite`, `Mimic` and `Metronome`.
- Doubles request coverage and partner redirection support for `Helping Hand`, `Follow Me` and `Snatch`.
- Additional Gen 3 move coverage for `Leech Seed`, `Disable`, `Encore`, `Attract`, `Future Sight`, `Pursuit`, `Pain Split`, `Heal Bell`, `Refresh`, `Psych Up`, `Spite`, `Mimic`, `Metronome`, `Rollout`, `Stockpile`, `Spit Up`, `Swallow`, `Wish`, `Yawn`, `Nightmare`, `Mean Look`, `Torment`, `Lock On`, `Mind Reader`, `Conversion`, `Conversion 2`, `Role Play`, `Skill Swap`, `Curse`, `Belly Drum`, `Transform`, `Uproar`, `Growth`, `Calm Mind`, `Bulk Up`, `Dragon Dance`, `Razor Wind`, `Sky Attack`, `Skull Bash`, `Dive`, `Present`, `Pressure`, `Foresight` and `Spikes`.
- Item resolution on battle end.

## Remaining Work

- Keep the battle layer free of Gen 1/2 normalization logic.
- Add coverage for any remaining exotic Gen 3 move and ability edge cases discovered by future real saves.
