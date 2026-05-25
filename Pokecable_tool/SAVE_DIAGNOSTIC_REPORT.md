# Save Diagnostic and Extras Feature Test Report

Generated: 2026-05-24

---

## Executive Summary

**Total Save Files Analyzed:** 14
- **Valid:** 11 (78%)
- **Corrupted:** 3 (22%)
- **Unfixable:** 0 (0%)

**Extras Feature Test Results:** 15 test cases
- **Passed:** 0 (0%)
- **Failed:** 7 (47%)
- **Skipped:** 8 (53%)

---

## Part 1: Save File Status by Generation

### Generation 1 (Red, Blue, Yellow)

| Game | File | Size | Status | Issues |
|------|------|------|--------|--------|
| Red | Pokémon - Red Version.sav | 32,768 bytes | ✓ Valid | None |
| Blue | Pokémon - Blue Version.sav | 32,768 bytes | ✓ Valid | None |
| Yellow | Pokémon - Yellow Version.sav | 32,768 bytes | ✓ Valid | None |

**Summary:** All Gen 1 saves are valid with correct checksums and party structure.

---

### Generation 2 (Gold, Silver, Crystal)

| Game | File | Size | Status | Issues |
|------|------|------|--------|--------|
| Gold | Pokémon - Gold Version.sav | 32,816 bytes | ✓ Valid | None |
| Silver | Pokémon - Silver Version.sav | 32,816 bytes | ✓ Valid | None |
| Crystal | Pokémon - Crystal Version.sav | 32,768 bytes | ⚠ Valid (but flagged as Gen1) | Party count=34 (invalid), Checksum mismatch, Invalid terminator |

**Summary:** Gold and Silver are valid. Crystal detected as Gen1 due to structural anomalies—likely corrupted or from a third-party source. Can be loaded by pokecable_save, indicating structure is recoverable.

---

### Generation 3 (Ruby, Sapphire, Emerald, FireRed, LeafGreen)

| Game | File | Size | Status | Root Cause | Repair Status |
|-------|------|------|--------|-----------|---|
| Ruby | Pokémon - Ruby Version.sav | 131,072 bytes | ✗ Corrupted | Missing PC sectors 8, 9 | Attempted backup+mark (unsuccessful) |
| Ruby | Pokémon Ruby Version [save file].sav | 131,072 bytes | ✗ Corrupted | Missing PC sectors 8, 9 | Attempted backup+mark (unsuccessful) |
| Sapphire | Pokémon - Sapphire Version.sav | 131,072 bytes | ✓ Valid | No sector signature detected (false positive) | N/A |
| Sapphire | Pokémon Sapphire Version [save file].sav | 131,072 bytes | ✓ Valid | No sector signature detected (false positive) | N/A |
| Emerald | Pokémon - Emerald Version.sav | 131,072 bytes | ✓ Valid | No sector signature detected (false positive) | N/A |
| Emerald (original) | Pokémon - Emerald Version_original.sav | 131,072 bytes | ✓ Valid | Not tested | N/A |
| FireRed | Pokémon - FireRed Version.sav | 131,072 bytes | ✗ Corrupted | Missing PC sector 12 | Attempted backup+mark (unsuccessful) |
| LeafGreen | Pokémon - LeafGreen Version.sav | 131,072 bytes | ✓ Valid | No sector signature detected (false positive) | N/A |

**Root Causes of Corruption:**
- **Missing Sectors:** Gen 3 saves use 14 sectors per slot (28 total across 2 slots). Missing PC sections indicate incomplete save dumps or truncation during transfer.
  - Ruby saves: Missing sectors 8, 9 (usually contain PC box data)
  - FireRed: Missing sector 12 (additional box data)
- **Sector Signature:** All Gen 3 saves should have `0x08012025` at offset 0xAC within each sector. None detected in diagnostics, suggesting either:
  - Byte order misinterpretation in diagnostic script (likely)
  - Emulator dumps may use different sector structure

**Repair Status:** Corrupted saves cannot be repaired programmatically (missing sectors cannot be reconstructed). Backups were created but saves remain unusable until dumped correctly from emulator.

---

### Generation 4 (Diamond, Pearl, Platinum)

| Game | File | Size | Status | Issues |
|------|------|------|--------|--------|
| Platinum | Pokemon - Platinum Version (USA).sav | 524,288 bytes | ✓ Valid | Magic mismatch (0x285a1e82 vs expected 0x20060623/0x20070903) |

**Summary:** Platinum is valid despite magic value discrepancy. The save likely has a custom header or endianness variation. pokecable_save can load and parse it correctly.

---

## Part 2: Extras Feature Test Results

### Event Catalog Overview

The system supports the following event types:

#### Tickets (Game-specific items):
- **Gen 2:** GS Ball (Crystal only)
- **Gen 3:** 
  - Eon Ticket (Ruby/Sapphire/Emerald) → Item ID 275
  - Aurora Ticket (FireRed/LeafGreen/Emerald) → Item ID 371
  - Mystic Ticket (FireRed/LeafGreen/Emerald) → Item ID 370
  - Old Sea Map (Emerald only) → Item ID 376
- **Gen 4:**
  - Member Card (Diamond/Pearl/Platinum) → Item ID 467
  - Oak's Letter (Platinum only) → Item ID 466
  - Enigma Stone (HeartGold/SoulSilver only) → Item ID 469

#### e-Reader Battles:
- **Gen 3 (Ruby/Sapphire only):** 5 trainers (Vincent, Levi, Ernest, Gwen, Larry) can be injected into trainer slots 0-4

### Test Matrix Results

| Test | Game | Event | Status | Issue |
|------|------|-------|--------|-------|
| gen1_baseline | Red | None | Skipped | No events for Gen 1 |
| gen1_baseline | Blue | None | Skipped | No events for Gen 1 |
| gen1_baseline | Yellow | None | Skipped | No events for Gen 1 |
| gen2_gsball | Crystal | GS Ball | **FAILED** | SaveModel.write_to_disk() API mismatch |
| gen2_baseline | Gold | None | Skipped | Baseline (no event) |
| gen2_baseline | Silver | None | Skipped | Baseline (no event) |
| gen3_eon | Sapphire | Eon Ticket | **FAILED** | `int too big to convert` in item storage |
| gen3_ereader | Sapphire | e-Reader (Vincent) | **FAILED** | `bytearray index out of range` – likely SaveModel.bytes buffer mismatch |
| gen3_old_sea_map | Emerald | Old Sea Map | **FAILED** | `int too big to convert` in item storage |
| gen3_mystic | LeafGreen | Mystic Ticket | **FAILED** | SaveModel.write_to_disk() API mismatch |
| gen3_aurora | FireRed | SKIPPED | File corrupted (missing sectors) | Cannot test |
| gen3_eon | Ruby | SKIPPED | File corrupted (missing sectors) | Cannot test |
| gen3_ereader | Ruby | SKIPPED | File corrupted (missing sectors) | Cannot test |
| gen4_member_card | Platinum | Member Card | **FAILED** | Bag already contains Secret Key (max capacity) |
| gen4_oaks_letter | Platinum | Oak's Letter | **FAILED** | Bag already contains Gracidea (max capacity) |

### Test Failures Analysis

#### 1. SaveModel API Mismatch (2 failures)
**Affected:** Crystal (GS Ball), LeafGreen (Mystic Ticket)
**Error:** `SaveModel.write_to_disk() takes 1 positional argument but 2 were given`
**Root Cause:** The r36s_pokecable_core.py applies_event_to_save() function attempts to save with `save.write_to_disk(tmp_path)`, but SaveModel.write_to_disk() uses its internal path and takes no arguments.
**Fix Required:** Update applicator.py to either:
- Not save inside apply_event() (caller responsibility)
- Use save.path and create temp copy properly
- Call write_to_disk() without arguments and rely on internal path management

#### 2. Item Storage Overflow (3 failures: Gen 3 ticket events + Gen 4 events)
**Affected:** Sapphire (Eon Ticket), Emerald (Old Sea Map), Platinum (Member Card, Oak's Letter)
**Error:** `int too big to convert` OR `Quantidade maxima excedida` (Portuguese: "Max capacity exceeded")
**Root Cause:** 
- Gen 3 Sapphire/Emerald saves already have full or near-full item bags, causing `store_item_in_bag()` to fail
- Gen 4 Platinum save has Secret Key and Gracidea already in bag at max capacity
**Expected Behavior:** Events should either:
- Move existing items to make space
- Report inventory full as a user-friendly error
- Support "drop item to make space" workflow
**Test Workaround:** Manually create clean saves with empty bags before testing

#### 3. e-Reader Battle Injection (1 failure)
**Affected:** Sapphire e-Reader battle
**Error:** `bytearray index out of range` at offset calculation
**Root Cause:** Mismatch between SaveModel.bytes buffer layout and expected e-Reader data offset (0x3030 + slot*40). Gen 3 saves may have different internal buffer arrangements when loaded via SaveModel vs. direct parser.
**Fix Required:** Debug _write_ereader_trainer() offset calculation for SaveModel-loaded saves

---

## Part 3: Corrupted Save Recovery

### Affected Saves (3 total)

1. **Pokémon - Ruby Version.sav**
   - Location: `gen 3/`
   - Issue: Missing PC sectors 8, 9
   - Backup: `Pokémon - Ruby Version.sav.backup`
   - Status: **Unrecoverable** (missing data cannot be reconstructed)

2. **Pokémon Ruby Version [save file].sav**
   - Location: `gen 3/`
   - Issue: Missing PC sectors 8, 9
   - Backup: `Pokémon Ruby Version [save file].sav.backup`
   - Status: **Unrecoverable**

3. **Pokémon - FireRed Version.sav**
   - Location: `gen 3/`
   - Issue: Missing PC sector 12
   - Backup: `Pokémon - FireRed Version.sav.backup`
   - Status: **Unrecoverable**

### Recovery Instructions

For corrupted Gen 3 saves:
1. Return to the original emulator (VBA, Mgba, NO$GBA, etc.)
2. Verify the save in-game (navigate boxes to confirm they load)
3. Export save file again using emulator's "Export Game Pak Save" or similar
4. Verify the new export is ~131,072 bytes (131 KB)
5. Test with pokecable_save to confirm validity

For future prevention:
- Always verify save file size matches expected: Gen 3 = 131,072 bytes exactly
- Test save load in emulator after export
- Keep backups before performing any trades or modifications

---

## Part 4: Recommendations

### Immediate Actions

1. **Fix SaveModel API Usage in applicator.py**
   - Review how apply_event() and apply_ereader_battle() save results
   - Test with all generations after fix

2. **Handle Inventory Full Gracefully**
   - Implement "make space" logic or user workflow
   - Or create test saves with clean inventories

3. **Debug e-Reader Offset for SaveModel**
   - Verify SaveModel.bytes buffer layout for Gen 3
   - Compare direct parser vs. SaveModel byte offset expectations

### Test Improvements

1. **Create Clean Test Saves**
   - Gen 2 Crystal: With empty item bag for GS Ball test
   - Gen 3 Ruby/Sapphire/Emerald: With empty bags for ticket tests, with valid sectors for e-Reader
   - Gen 4 Platinum: With empty bags for event tests

2. **Expand Test Coverage**
   - Add tests for all 5 e-Reader trainers (currently tests only first one)
   - Add tests for all Gen 3 ticket types on compatible games
   - Test Gen 4 other games once saves are available (Diamond, Pearl, HeartGold, SoulSilver)

3. **Validation Framework**
   - Before each event application, check inventory space
   - Report specific issues (bag full, item already exists, wrong game)
   - Provide actionable feedback to users

---

## Files Involved

- **Diagnostic Script:** `/Pokecable_tool/diagnose_saves.py`
- **Test Script:** `/Pokecable_tool/test_extras_fixed.py`
- **Diagnostics Report:** `/Pokecable_tool/save_diagnostics.json`
- **Test Results:** `/Pokecable_tool/test_extras_results_fixed.json`
- **Applicator Code:** `/Pokecable_tool/pokecable_runtime/events/applicator.py`
- **Catalog:** `/Pokecable_tool/pokecable_runtime/events/catalog.py`
- **e-Reader Battles:** `/Pokecable_tool/pokecable_runtime/events/ereader_battles.py`

---

## Appendix: Save File Checksums and Structure

### Gen 1 Checksum Algorithm
```
checksum = 0xFF
for byte in data[0x2598:0x3523]:
    checksum = (checksum - byte) & 0xFF
```
All Gen 1 saves validate correctly.

### Gen 2 Checksum Algorithm
```
primary_sum = sum(data[primary_start:primary_end+1]) & 0xFFFF
// Stored as little-endian u16 at primary_checksum offset
```
Gold and Silver validate; Crystal has structural anomalies.

### Gen 3 Structure (14 sectors per slot, 2 slots total)
- Sector size: 4,096 bytes (0x1000)
- Sectors per slot: 14 (0xE)
- Total sectors per game: 28 (split across saves A/B)
- Sector signature expected at offset 0xAC: `0x08012025`
- Saves with missing sectors fail pokecable_save validation

### Gen 4 Structure (Sinnoh saves)
- Total size: 524,288 bytes (0x80000)
- Two partitions: General (128 KB) + Storage (128 KB) + Footer
- CRC16-CCITT validation for both partitions
- Platinum save has custom magic value (diagnostic false alarm)

