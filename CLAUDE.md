# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Guidelines

- **Responda de forma objetiva** (respond objectively). Keep messages concise.
- **Antes de editar, leia apenas os arquivos necessários** (read only necessary files before editing). Don't scan the entire project without cause.
- **Não faça varredura completa do projeto sem necessidade** (don't sweep the entire project without need).
- **Evite explicações longas** (avoid long explanations). One sentence per update is usually enough.
- **Ao modificar código, mostre somente o resumo e arquivos alterados** (when modifying code, show only the summary and changed files).
- **Não rode testes longos sem eu pedir** (don't run long tests without being asked). The complete coverage test takes several minutes.
- **Prefira mudanças pequenas e incrementais** (prefer small, incremental changes). Avoid large refactors unless requested.
- **Remova qualquer referencia que diz que foi construido com Claude, Codex ou qualquer outro agent de ia**

## Project Overview

**PokeCable Room**: A tool for cross-generation Pokémon trading over the internet via a central WebSocket server. Trades are performed by safely editing local save files with automatic backups. The system supports Gen 1, Gen 2 (Gold/Silver/Crystal), and Gen 3 (Ruby/Sapphire/Emerald/FireRed/LeafGreen) with both same-generation and cross-generation trading modes.

**Key Components**:
- **API Server** (`PokeCable/api/`): FastAPI + WebSocket for trade rooms, battle rooms, and room orchestration.
- **Backend** (`PokeCable/backend/`): Python client, save parsers, Pokémon conversion logic, and compatibility validation.
- **Frontend** (`PokeCable/frontend/`): Web UI for trading and battling.
- **Tests** (`tests/`): Integration tests for compatibility coverage.

## Architecture

### Backend Core (`PokeCable/backend/`)

The backend is organized as a single Python package with these key submodules:

- **Parsers** (`parsers/`): Extract party data from binary save files. Each generation has its own parser (gen1, gen2, gen3).
- **Canonical** (`canonical/`): Unified Pokémon data model using National Dex numbers, independent of generation internals.
- **Converters** (`converters/`): Bi-directional conversion between generations:
  - `gen1_to_gen2.py`, `gen2_to_gen1.py`: Time Capsule (Gen1 ↔ Gen2)
  - `gen1_to_gen3.py`, `gen2_to_gen3.py`: Forward Transfer (Gen1/2 → Gen3)
  - Reverse converters: Downconvert from Gen3 to Gen1/2 (experimental)
- **Compatibility** (`compatibility/`): Validates cross-generation trades, tracking data loss and transformations.
- **Evolutions** (`evolutions/`): Applies trade-triggered evolutions after receiving a Pokémon.
- **Network** (`network.py`): WebSocket client for room communication.
- **Trade** (`trade.py`): Orchestrates the full trade flow (same-gen and cross-gen).
- **Client** (`client.py`): CLI entry point for R36S handheld and PC testing; handles room creation/join, Pokémon selection, and save file management.

### API Server (`PokeCable/api/`)

- **Rooms** (`app/rooms.py`): Private trade and battle room management (max 2 players per room).
- **WebSocket** (`app/websocket.py`): Event handling for trade and battle lifecycles.
- **Main** (`app/main.py`): FastAPI setup with `/health` endpoint and feature flags.
- Feature flags: `ALLOW_CROSS_GENERATION`, `ENABLED_TRADE_MODES`, `BATTLE_ENGINE`.

### Cross-Generation Trade Protocol

**Single Room Design**: Users create/join one room and select their save + Pokémon; the system auto-detects generations and routes through the correct converter.

**Trade Modes** (feature-gated):
- `time_capsule_gen1_gen2`: Gen1 ↔ Gen2
- `forward_transfer_to_gen3`: Gen1/2 → Gen3
- `legacy_downconvert_experimental`: Gen3 → Gen1/2 (lossy)

**Preflight Protocol**: Before commit, each client validates locally that the incoming Pokémon is compatible. If either side fails, the trade is blocked with no file writes. Success triggers a two-phase commit.

**Data Loss Policy** (`config.json`):
- `auto_retrocompat` (default): Auto-remove incompatible moves/held items; register losses in logs.
- `strict`: Block any data loss.
- `safe_default`: Allow removable losses with user confirmation.
- `permissive`: Remove everything possible, confirm once.

## Common Commands

### Setup

**API Server**:
```bash
cd PokeCable/api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Running

**API Server** (uvicorn):
```bash
cd PokeCable/api
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**API Server** (Docker):
```bash
cd PokeCable/api
docker compose up -d --build
```

**Healthcheck**:
```bash
curl http://127.0.0.1:8000/health
```

**Backend Client** (PC testing):
```bash
PYTHONPATH=PokeCable/backend python3 PokeCable/backend/client.py \
  --action create \
  --server ws://127.0.0.1:8000/ws \
  --room test_room \
  --password 123 \
  --save /path/to/save.sav \
  --pokemon-location party:0
```

### Testing

**All backend tests**:
```bash
PYTHONPATH=PokeCable/backend python3 -m pytest PokeCable/backend/tests -v
```

**Single test file**:
```bash
PYTHONPATH=PokeCable/backend python3 -m pytest PokeCable/backend/tests/test_converters.py -v
```

**Single test**:
```bash
PYTHONPATH=PokeCable/backend python3 -m pytest PokeCable/backend/tests/test_converters.py::TestConvertGen1ToGen2::test_pikachu -v
```

**All API tests**:
```bash
cd PokeCable/api
python3 -m pytest tests -v
```

**Complete coverage test** (all 251 Pokémon × generation combinations):
```bash
cd tests
python3 test_complete_pokemon_coverage.py
```
Results saved to `tests/test_results/`.

**Test scripts** (cross-platform):
```bash
# Linux/macOS
./tests/test_complete_coverage.sh

# Windows (batch)
tests\test_complete_coverage.bat

# Windows (PowerShell)
.\tests\test_complete_coverage.ps1
```

### Code Quality

No linter is currently configured. The project prioritizes working code over style enforcement.

## Save File Paths

Test saves are located at:
```
PokeCable/test-saves/
  gen 1/
    Pokémon - Red Version.sav
    Pokémon - Blue Version.sav
    Pokémon - Yellow Version.sav
  gen 2/
    ...
  gen 3/
    Pokémon - Ruby Version.sav
    Pokémon - Emerald Version.sav
    ...
```

Test results are saved to `tests/test_results/`.

## Feature Flags

**Server** (environment variables):
- `ALLOW_CROSS_GENERATION`: Enable cross-generation trading (default: false).
- `ENABLED_TRADE_MODES`: Comma-separated list of trade modes.
- `BATTLE_ENGINE`: Currently only `local` is supported.

**Client** (`PokeCable/backend/config.json`):
- `auto_trade_evolution`: Auto-apply simple trade evolutions (default: true).
- `item_trade_evolutions_enabled`: Allow item-triggered evolutions (default: false).
- `cross_generation.policy`: Data loss policy.

## Key Files to Know

| File | Purpose |
|------|---------|
| `PokeCable/backend/parsers/` | Save file parsing for each generation |
| `PokeCable/backend/canonical/` | Canonical Pokémon data model |
| `PokeCable/backend/converters/` | Cross-generation conversion logic |
| `PokeCable/backend/compatibility/rules.py` | Compatibility validation rules |
| `PokeCable/backend/client.py` | CLI client (R36S and PC) |
| `PokeCable/api/app/rooms.py` | Room orchestration |
| `PokeCable/api/app/websocket.py` | WebSocket event handling |
| `tests/test_complete_pokemon_coverage.py` | Integration test (all Pokémon) |

## Known Limitations

- Boxes are not yet implemented; current flow is party-only.
- Gen 3 → Gen 1/2 downconversion may lose ability, nature, trainer ID, held item, and modern moves.
- The game/emulator must be closed before the client can safely write to the save file.
- The battle engine is currently local and deterministic.
