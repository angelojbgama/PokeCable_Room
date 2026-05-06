# Battle Engine Gen 2

## Scope

- Gold / Silver / Crystal only.
- Only accepts Gen 2 battle teams.
- No retrocompatibility in the battle layer.

## Implemented Core

- Gen 2 type chart.
- Gen 2 damage formula.
- Split Special Attack / Special Defense.
- Major status handling: sleep, paralysis, burn, poison, toxic, freeze, confusion and flinch.
- PP consumption with Struggle fallback when the selected move is empty.
- Partial trapping moves block actions and switches.
- Recharge handling for Hyper Beam style moves.
- Drain, recoil, screens and common status move effects used by the current battle flow.
- Charge-turn families for Fly, Dig, Razor Wind, Solar Beam, Sky Attack and Skull Bash.
- Leech Seed, Disable, Encore, Counter, Mirror Coat, Bide, Metronome, Mimic, Mirror Move, Transform and Conversion.
- Protect / Detect, Endure, Future Sight, Pursuit, Spikes, Pain Split, Heal Bell, Attract, Swagger / Charm, Belly Drum, Foresight, Lock On / Mind Reader, Dream Eater, Substitute, Selfdestruct / Explosion and Baton Pass support used by the current battle flow.
- Rollout, Fury Cutter and weather-based damage / healing interactions.
- Real-save 6v6 battle coverage for Gold / Silver / Crystal saves.

## Remaining Work

- Keep adding regression tests whenever a new Gen 2 move family or trace exposes a new quirk.
- Preserve generation isolation and keep any future normalization outside the battle engine.
