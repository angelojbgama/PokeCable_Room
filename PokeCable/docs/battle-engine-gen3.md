# Battle Engine Gen 3

## Scope

- Ruby / Sapphire / Emerald only.
- Only accepts Gen 3 battle teams.
- No cross-generation normalization inside the battle engine.

## Implemented Core

- Gen 3 battle math.
- Abilities, held items, natures, and modern stat handling.
- Doubles support.
- Item resolution on battle end.

## Remaining Work

- Keep the battle layer free of Gen 1/2 normalization logic.
- Add coverage for any remaining Gen 3 move edge cases.
- Keep regression tests focused on native Gen 3 payloads only.
