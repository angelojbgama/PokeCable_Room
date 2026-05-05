# Battle Engines Roadmap

The battle layer is split by generation and must stay generation-pure.
Cross-generation normalization belongs to save conversion and compatibility code, not to battle execution.

## Current Architecture

- Gen 1 engine: [docs/battle-engine-gen1.md](./battle-engine-gen1.md)
- Gen 2 engine: [docs/battle-engine-gen2.md](./battle-engine-gen2.md)
- Gen 3 engine: [docs/battle-engine-gen3.md](./battle-engine-gen3.md)

## Rules

- Gen 1 battles only Gen 1.
- Gen 2 battles only Gen 2.
- Gen 3 battles only Gen 3.
- Battle rooms reject mixed-generation teams.
- The Gen 3 battle engine must not auto-normalize Gen 1/2 payloads.

## Focus

- Finish Gen 1 edge-case fidelity.
- Keep Gen 2 battle coverage aligned with real-save regressions and future edge cases.
- Keep Gen 3 battle execution native to Gen 3 data only.
