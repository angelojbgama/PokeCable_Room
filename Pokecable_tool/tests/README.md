# Test Suite — Pokecable Tool

Three driver scripts cover the full retrocompatibility surface:

| Driver | Casos | Foco | Tempo |
|---|---|---|---|
| `stress_cross_gen.py` | ~127k | Conversão canônica entre formatos, all species × learnsets × extremes | ~8s |
| `test_save_roundtrip.py` | ~49 | Roundtrip real via save files: export → convert → import → list_party → verify | ~5s |
| `test_full_coverage.py` | ~1.8k | 14 baterias fechando os gaps (boxes, disk, forms, trade-evolution, eggs, fuzz, LAN, backup, fresh, Crystal layout, inventory, UI snapshot, PyBoy SRAM dump, Gen 3 emulator smoke) | ~10s |

```bash
# Rodar tudo
python tests/stress_cross_gen.py
python tests/test_save_roundtrip.py
python tests/test_full_coverage.py
```

## Dependências externas

| Bateria | Dependência | Como obter |
|---|---|---|
| S (PyBoy SRAM) | `pyboy` Python package | `pip install pyboy --break-system-packages` |
| T (libmgba SRAM Gen 3) | `libmgba-dev` + wrapper compilado | `sudo apt install libmgba-dev` então `cd tests/emulator && gcc -shared -fPIC -O2 mgba_wrapper.c -lmgba -o mgba_wrapper.so` |
| Todos | Saves de teste | `roms/test-saves/{gen 1,gen 2,gen 3}/*.sav` |
| Todos | ROMs (para bateria S e T) | `roms/test-saves/{gen 1,gen 2,gen 3}/*.gb*` |

## Estrutura

```
tests/
├── README.md                       # este arquivo
├── stress_cross_gen.py             # driver 1 (conversão canônica)
├── test_save_roundtrip.py          # driver 2 (saves reais)
├── test_full_coverage.py           # driver 3 (14 baterias)
│
├── _stress/                        # módulos do driver 1
│   ├── fixtures.py                 # parsers + holdable items + ROUTES/POLICIES
│   ├── scenarios.py                # synthetic CanonicalPokemon factories
│   ├── verifiers.py                # gen 1/2/3 byte decoders + Mismatch
│   └── runner.py                   # accumulator + report formatter
│
├── _roundtrip/                     # módulos do driver 2
│   ├── report.py                   # BatteryReport dataclass
│   ├── saves_inventory.py          # A
│   ├── roundtrip_real.py           # B
│   ├── quirks_unown.py             # C
│   ├── quirks_tid.py               # D
│   └── quirks_lan.py               # E
│
├── _coverage/                      # módulos do driver 3
│   ├── boxes_full.py               # F (boxes export+roundtrip todos)
│   ├── disk_persistence.py         # G (save+reload checksum)
│   ├── forms_quirks.py             # H (Spinda/Castform/Deoxys)
│   ├── trade_evolution.py          # I
│   ├── event_pokemon.py            # J (fateful_encounter)
│   ├── eggs.py                     # K (negative)
│   ├── glitched_inputs.py          # L (fuzz)
│   ├── lan_loopback.py             # M
│   ├── backup_restore.py           # N
│   ├── fresh_saves.py              # O
│   ├── crystal_layout.py           # P
│   ├── inventory.py                # Q
│   └── ui_snapshot.py              # R
│
├── emulator/                       # baterias S e T (emulador real)
│   ├── _libmgba.py                 # wrapper Python ctypes para libmgba
│   ├── mgba_wrapper.c              # C glue para chamar mCore->runFrame etc.
│   ├── mgba_wrapper.so             # compilado (gerado por gcc)
│   ├── test_rom_validation.py      # S — PyBoy SRAM dump (Gen 1/2)
│   ├── test_gen3_smoke.py          # T — libmgba SRAM dump (Gen 3, byte-perfect)
│   └── ram_dump.lua                # opcional (script Lua para mGBA via GUI)
│
├── _emu_dumps/                     # outputs JSON da bateria S
└── _snapshots/                     # PNGs da bateria R (UI smoke)
```

## Cobertura

- **Camada de conversão canônica**: 100% (stress test)
- **Roundtrip de save**: 100% party + 1731/1731 box slots
- **Emulador Gen 1/2**: 100% via PyBoy (SRAM byte-perfect)
- **Emulador Gen 3**: 100% via libmgba+ctypes — SRAM dump 100% byte-match com nosso .sav, 28/14+ sector signatures válidas

## Gaps conhecidos (atualizados)

| # | Gap | Status |
|---|---|---|
| 1 | Boxes export | ✅ implementado em `parsers/gen2.py` e `gen3.py` |
| 2 | Persistência em disco | ✅ Bateria G |
| 3 | Boot ROM | ✅ Bateria S (PyBoy Gen 1/2) + Bateria T (libmgba Gen 3 com SRAM dump byte-perfect) |
| 4 | Trade evolution | ✅ Bateria I |
| 5 | Fateful encounter | ✅ exposto + Bateria J |
| 6 | Forms (Spinda/Castform/Deoxys) | ✅ Bateria H |
| 7 | Eggs | ✅ Bateria K (negative test) |
| 8 | Glitched inputs | ✅ Bateria L |
| 9 | LAN loopback | ✅ Bateria M |
| 10 | UI snapshot | ✅ Bateria R |
| 11 | Backup + restore | ✅ Bateria N |
| 12 | Fresh saves | ✅ Bateria O |
| 13 | Crystal layout | ✅ Bateria P |
| 14 | Inventory | ✅ Bateria Q |
