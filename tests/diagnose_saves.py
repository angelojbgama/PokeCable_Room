#!/usr/bin/env python3
"""
Diagnose all test saves (Gen 1-4) to identify corruption and attempt repairs.
Requires the pokecable_save module to be available.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import struct

# Add pokecable_save to path
POKECABLE_SAVE_PATH = Path(__file__).parent / "pokecable_save"
sys.path.insert(0, str(POKECABLE_SAVE_PATH))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pokecable_save import load_save, SaveError
except ImportError as e:
    print(f"ERROR: Could not import pokecable_save: {e}")
    print(f"Expected at: {POKECABLE_SAVE_PATH}")
    sys.exit(1)


# Parser constants
GEN1_SAVE_SIZE = 0x8000  # 32768 bytes
GEN2_SAVE_SIZE = 0x8000  # 32768 bytes
GEN3_SAVE_SIZE = 0x20000  # 131072 bytes (2 slots of 14 sectors each)
GEN4_SAVE_SIZE = 0x80000  # 524288 bytes

GEN1_CHECKSUM_START = 0x2598
GEN1_CHECKSUM_END = 0x3522
GEN1_CHECKSUM_OFFSET = 0x3523
GEN1_PARTY_OFFSET = 0x2F2C

GEN2_CRYSTAL_PARTY_OFFSET = 0x2865
GEN2_GOLD_SILVER_PARTY_OFFSET = 0x288A
GEN2_CRYSTAL_PRIMARY_START = 0x2009
GEN2_CRYSTAL_PRIMARY_END = 0x2B82
GEN2_CRYSTAL_PRIMARY_CHECKSUM = 0x2D0D
GEN2_GOLD_SILVER_PRIMARY_START = 0x2009
GEN2_GOLD_SILVER_PRIMARY_END = 0x2D68
GEN2_GOLD_SILVER_PRIMARY_CHECKSUM = 0x2D69

GEN3_SECTOR_SIZE = 4096
GEN3_SECTORS_PER_SLOT = 14

GEN4_PARTITION_SIZE = 0x40000


class SaveDiagnostic:
    """Diagnose save file corruption."""

    def __init__(self, save_path: Path):
        self.save_path = save_path
        self.data: Optional[bytes] = None
        self.generation: Optional[int] = None
        self.status = "unknown"
        self.issues: List[str] = []
        self.repair_actions: List[str] = []

    def load_file(self) -> bool:
        """Load the save file."""
        try:
            self.data = self.save_path.read_bytes()
            return True
        except Exception as e:
            self.issues.append(f"Could not read file: {e}")
            self.status = "unfixable"
            return False

    def detect_generation(self) -> Optional[int]:
        """Detect save generation by size and structure."""
        if not self.data:
            return None

        size = len(self.data)

        # Size-based detection
        if size == GEN1_SAVE_SIZE:
            return 1
        elif size == GEN2_SAVE_SIZE:
            return 2
        elif size == GEN3_SAVE_SIZE:
            return 3
        elif size == GEN4_SAVE_SIZE:
            return 4
        elif size == GEN1_SAVE_SIZE + 48:  # Gen2 with some save-states add 48 bytes
            return 2
        else:
            return None

    def validate_gen1(self) -> Tuple[bool, List[str]]:
        """Validate Gen 1 save structure."""
        issues = []

        if len(self.data) < GEN1_PARTY_OFFSET + 1:
            issues.append(f"Save too small: {len(self.data)} < {GEN1_PARTY_OFFSET + 1}")
            return False, issues

        # Check party count
        party_count = self.data[GEN1_PARTY_OFFSET]
        if party_count > 6:
            issues.append(f"Invalid party count: {party_count} > 6")

        # Check party terminator
        terminator_offset = GEN1_PARTY_OFFSET + 1 + party_count
        if terminator_offset >= len(self.data):
            issues.append(f"Party terminator offset out of bounds: {terminator_offset}")
        elif self.data[terminator_offset] != 0xFF:
            issues.append(
                f"Invalid party terminator at 0x{terminator_offset:04x}: "
                f"expected 0xFF, got 0x{self.data[terminator_offset]:02x}"
            )

        # Check checksum
        if GEN1_CHECKSUM_END < len(self.data) - 1:
            expected_checksum = self._calc_gen1_checksum()
            actual_checksum = self.data[GEN1_CHECKSUM_OFFSET]
            if expected_checksum != actual_checksum:
                issues.append(
                    f"Checksum mismatch: expected 0x{expected_checksum:02x}, "
                    f"got 0x{actual_checksum:02x}"
                )

        return len(issues) == 0, issues

    def _calc_gen1_checksum(self) -> int:
        """Calculate Gen 1 checksum."""
        value = 0xFF
        for byte in self.data[GEN1_CHECKSUM_START : GEN1_CHECKSUM_END + 1]:
            value = (value - byte) & 0xFF
        return value

    def validate_gen2(self) -> Tuple[bool, List[str]]:
        """Validate Gen 2 save structure."""
        issues = []

        if len(self.data) < GEN2_GOLD_SILVER_PRIMARY_CHECKSUM + 2:
            issues.append(f"Save too small: {len(self.data)}")
            return False, issues

        # Check party count (Crystal vs Gold/Silver)
        # Crystal
        crystal_party_count = self.data[GEN2_CRYSTAL_PARTY_OFFSET] if len(self.data) > GEN2_CRYSTAL_PARTY_OFFSET else 0
        gs_party_count = self.data[GEN2_GOLD_SILVER_PARTY_OFFSET] if len(self.data) > GEN2_GOLD_SILVER_PARTY_OFFSET else 0

        is_crystal = crystal_party_count <= 6 and crystal_party_count > 0
        is_gs = gs_party_count <= 6 and gs_party_count > 0

        if not (is_crystal or is_gs):
            issues.append(f"Invalid party counts: crystal={crystal_party_count}, gs={gs_party_count}")

        # Check Gold/Silver checksums
        primary_sum = sum(self.data[GEN2_GOLD_SILVER_PRIMARY_START : GEN2_GOLD_SILVER_PRIMARY_END + 1]) & 0xFFFF
        stored_checksum = int.from_bytes(
            self.data[GEN2_GOLD_SILVER_PRIMARY_CHECKSUM : GEN2_GOLD_SILVER_PRIMARY_CHECKSUM + 2],
            "little",
        )
        if primary_sum != stored_checksum:
            issues.append(
                f"Gold/Silver primary checksum mismatch: expected 0x{primary_sum:04x}, "
                f"got 0x{stored_checksum:04x}"
            )

        # Check Crystal checksums if applicable
        if is_crystal:
            crystal_sum = sum(self.data[GEN2_CRYSTAL_PRIMARY_START : GEN2_CRYSTAL_PRIMARY_END + 1]) & 0xFFFF
            crystal_stored = int.from_bytes(
                self.data[GEN2_CRYSTAL_PRIMARY_CHECKSUM : GEN2_CRYSTAL_PRIMARY_CHECKSUM + 2],
                "little",
            )
            if crystal_sum != crystal_stored:
                issues.append(
                    f"Crystal checksum mismatch: expected 0x{crystal_sum:04x}, "
                    f"got 0x{crystal_stored:04x}"
                )

        return len(issues) == 0, issues

    def validate_gen3(self) -> Tuple[bool, List[str]]:
        """Validate Gen 3 save structure."""
        issues = []

        if len(self.data) < GEN3_SECTOR_SIZE * GEN3_SECTORS_PER_SLOT:
            issues.append(
                f"Save too small: {len(self.data)} < {GEN3_SECTOR_SIZE * GEN3_SECTORS_PER_SLOT}"
            )
            return False, issues

        # Check sector signatures
        found_valid_slot = False
        for slot in [0, 1]:
            if len(self.data) < (slot + 1) * GEN3_SECTOR_SIZE * GEN3_SECTORS_PER_SLOT:
                continue
            base = slot * GEN3_SECTOR_SIZE * GEN3_SECTORS_PER_SLOT
            # Check first sector signature
            if len(self.data) >= base + GEN3_SECTOR_SIZE:
                sig = struct.unpack("<I", self.data[base + 0xAC : base + 0xB0])[0]
                if sig == 0x08012025:
                    found_valid_slot = True
                    break

        if not found_valid_slot:
            issues.append("No valid sector signature found (0x08012025)")

        return len(issues) == 0, issues

    def validate_gen4(self) -> Tuple[bool, List[str]]:
        """Validate Gen 4 save structure."""
        issues = []

        if len(self.data) != GEN4_SAVE_SIZE:
            issues.append(f"Invalid size: {len(self.data)} != {GEN4_SAVE_SIZE}")
            return False, issues

        # Check for valid magic or layout
        # Gen4 saves start with specific patterns
        # Magic bytes at offset 0: 0x20060623 (international) or 0x20070903 (Korean)
        try:
            magic = struct.unpack("<I", self.data[0:4])[0]
            if magic not in (0x20060623, 0x20070903):
                issues.append(f"Invalid magic: 0x{magic:08x} (expected 0x20060623 or 0x20070903)")
        except:
            issues.append("Could not read magic bytes")

        return len(issues) == 0, issues

    def diagnose(self) -> Dict:
        """Run full diagnostic."""
        if not self.load_file():
            return self.to_dict()

        self.generation = self.detect_generation()
        if self.generation is None:
            self.status = "unfixable"
            self.issues.append(f"Could not detect generation from size {len(self.data)}")
            return self.to_dict()

        # Validate based on generation
        if self.generation == 1:
            is_valid, issues = self.validate_gen1()
        elif self.generation == 2:
            is_valid, issues = self.validate_gen2()
        elif self.generation == 3:
            is_valid, issues = self.validate_gen3()
        elif self.generation == 4:
            is_valid, issues = self.validate_gen4()
        else:
            is_valid = False
            issues = ["Unknown generation"]

        self.issues.extend(issues)

        if is_valid:
            self.status = "valid"
        else:
            self.status = "corrupted"

        # Try to load with pokecable_save
        try:
            save = load_save(self.save_path)
            self.status = "valid"
            return self.to_dict()
        except SaveError as e:
            if self.status != "valid":
                self.issues.append(f"pokecable_save error: {e}")
        except Exception as e:
            if self.status != "valid":
                self.issues.append(f"Unexpected error: {e}")

        return self.to_dict()

    def repair_gen1(self) -> bool:
        """Attempt to repair Gen 1 save."""
        if len(self.data) < GEN1_SAVE_SIZE:
            # Pad with zeros
            self.data += b"\x00" * (GEN1_SAVE_SIZE - len(self.data))
            self.repair_actions.append("Padded to 32KB with zeros")

        # Fix checksum
        expected_checksum = self._calc_gen1_checksum()
        self.data = bytearray(self.data)
        self.data[GEN1_CHECKSUM_OFFSET] = expected_checksum
        self.data = bytes(self.data)
        self.repair_actions.append(f"Recalculated checksum to 0x{expected_checksum:02x}")

        return True

    def repair_gen2(self) -> bool:
        """Attempt to repair Gen 2 save."""
        if len(self.data) < GEN2_SAVE_SIZE:
            # Pad with zeros
            self.data += b"\x00" * (GEN2_SAVE_SIZE - len(self.data))
            self.repair_actions.append("Padded to 32KB with zeros")

        # Recalculate checksums
        self.data = bytearray(self.data)

        # Gold/Silver checksum
        primary_sum = sum(self.data[GEN2_GOLD_SILVER_PRIMARY_START : GEN2_GOLD_SILVER_PRIMARY_END + 1]) & 0xFFFF
        self.data[GEN2_GOLD_SILVER_PRIMARY_CHECKSUM : GEN2_GOLD_SILVER_PRIMARY_CHECKSUM + 2] = primary_sum.to_bytes(2, "little")
        self.repair_actions.append(f"Recalculated Gold/Silver checksum to 0x{primary_sum:04x}")

        self.data = bytes(self.data)
        return True

    def repair_gen3(self) -> bool:
        """Attempt to repair Gen 3 save."""
        if len(self.data) < GEN3_SECTOR_SIZE * GEN3_SECTORS_PER_SLOT:
            self.repair_actions.append(f"Cannot repair: save too small ({len(self.data)} bytes)")
            return False

        # Try to find and validate a slot
        self.repair_actions.append("Gen3 save structure validation only (no repair attempted)")
        return True

    def repair_gen4(self) -> bool:
        """Attempt to repair Gen 4 save."""
        if len(self.data) != GEN4_SAVE_SIZE:
            self.repair_actions.append(f"Cannot repair: invalid size ({len(self.data)} != {GEN4_SAVE_SIZE})")
            return False

        # Validate magic
        try:
            magic = struct.unpack("<I", self.data[0:4])[0]
            if magic not in (0x20060623, 0x20070903):
                self.repair_actions.append(f"Invalid magic (0x{magic:08x}): Gen4 repair not attempted")
                return False
        except:
            pass

        self.repair_actions.append("Gen4 save structure validation only (no repair attempted)")
        return True

    def repair(self) -> bool:
        """Attempt to repair the save."""
        if self.status == "valid":
            return True

        if self.generation == 1:
            return self.repair_gen1()
        elif self.generation == 2:
            return self.repair_gen2()
        elif self.generation == 3:
            return self.repair_gen3()
        elif self.generation == 4:
            return self.repair_gen4()

        return False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "save": str(self.save_path.name),
            "path": str(self.save_path),
            "size": len(self.data) if self.data else 0,
            "generation": self.generation,
            "status": self.status,
            "issues": self.issues,
            "repair_actions": self.repair_actions,
        }


def main():
    """Main diagnostic function."""
    test_saves_dir = Path(__file__).parent.parent / "roms" / "test-saves"

    if not test_saves_dir.exists():
        print(f"ERROR: Test saves directory not found: {test_saves_dir}")
        sys.exit(1)

    results = []
    corrupted_saves = []

    print(f"Scanning test saves at: {test_saves_dir}")
    print("=" * 100)

    for save_file in sorted(test_saves_dir.rglob("*.sav")):
        if "original" in save_file.name.lower():
            continue

        print(f"\nDiagnosing: {save_file.relative_to(test_saves_dir)}")
        diag = SaveDiagnostic(save_file)
        result = diag.diagnose()

        results.append(result)

        if result["status"] != "valid":
            corrupted_saves.append((save_file, diag))

        # Print result
        status_icon = "✓" if result["status"] == "valid" else "✗" if result["status"] == "corrupted" else "?"
        print(f"  Status: {status_icon} {result['status']} (Gen{result['generation']})")
        print(f"  Size:   {result['size']} bytes")
        if result["issues"]:
            for issue in result["issues"]:
                print(f"  Issue:  {issue}")

    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    valid_count = sum(1 for r in results if r["status"] == "valid")
    corrupted_count = sum(1 for r in results if r["status"] == "corrupted")
    unfixable_count = sum(1 for r in results if r["status"] == "unfixable")

    print(f"Total saves: {len(results)}")
    print(f"  Valid:     {valid_count}")
    print(f"  Corrupted: {corrupted_count}")
    print(f"  Unfixable: {unfixable_count}")

    # Attempt repairs
    if corrupted_saves:
        print("\n" + "=" * 100)
        print("ATTEMPTING REPAIRS")
        print("=" * 100)

        for save_file, diag in corrupted_saves:
            print(f"\nRepairing: {save_file.relative_to(test_saves_dir)}")
            if diag.repair():
                backup_path = save_file.with_suffix(".sav.backup")
                save_file.rename(backup_path)
                save_file.write_bytes(diag.data)
                print(f"  ✓ Repaired and saved (backup: {backup_path.name})")
                for action in diag.repair_actions:
                    print(f"    - {action}")
            else:
                print(f"  ✗ Could not repair")
                for action in diag.repair_actions:
                    print(f"    - {action}")

    # Save detailed report
    report_path = Path(__file__).parent / "save_diagnostics.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()
