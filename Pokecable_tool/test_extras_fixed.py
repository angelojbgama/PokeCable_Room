#!/usr/bin/env python3
"""
Fixed comprehensive test for Extras feature across all generations (Gen 1-4).
Tests all event types: tickets and e-Reader battles.
"""

import sys
import json
import tempfile
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Ensure imports
try:
    from pokecable_save import load_save, SaveError
except ImportError as e:
    print(f"ERROR: Could not import pokecable_save: {e}")
    sys.exit(1)


class SaveTestResult:
    """Result of a single test."""

    def __init__(self, test_name: str, save_name: str, generation: int, event_id: Optional[str], status: str, message: str):
        self.test_name = test_name
        self.save_name = save_name
        self.generation = generation
        self.event_id = event_id
        self.status = status
        self.message = message
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "test": self.test_name,
            "save": self.save_name,
            "generation": self.generation,
            "event": self.event_id,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class ExtrasTestRunnerFixed:
    """Run Extras tests on saves."""

    def __init__(self, test_saves_dir: Path):
        self.test_saves_dir = test_saves_dir
        self.results: List[SaveTestResult] = []
        self.summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "by_generation": {},
        }

    def run_all_tests(self) -> Dict:
        """Run all Extras tests."""
        print("=" * 120)
        print("COMPREHENSIVE EXTRAS FEATURE TEST (FIXED)")
        print("=" * 120)

        # First, diagnose all saves
        save_status = {}
        for save_file in sorted(self.test_saves_dir.rglob("*.sav")):
            if "original" in save_file.name.lower():
                continue
            try:
                save = load_save(save_file)
                save_status[save_file.name] = {
                    "path": save_file,
                    "game": save.game,
                    "generation": save.generation,
                    "status": "valid",
                }
            except SaveError as e:
                save_status[save_file.name] = {
                    "path": save_file,
                    "game": None,
                    "generation": None,
                    "status": f"corrupted: {e}",
                }

        # Define test matrix
        test_cases = [
            # Gen 1 - No extras available
            ("Pokémon - Red Version.sav", None, "gen1_baseline"),
            ("Pokémon - Blue Version.sav", None, "gen1_baseline"),
            ("Pokémon - Yellow Version.sav", None, "gen1_baseline"),
            # Gen 2 - GS Ball ticket (Crystal only)
            ("Pokémon - Crystal Version.sav", "gen2_gsball", "gen2_gsball"),
            ("Pokémon - Gold Version.sav", None, "gen2_baseline"),
            ("Pokémon - Silver Version.sav", None, "gen2_baseline"),
            # Gen 3 - Multiple ticket types
            ("Pokémon - Ruby Version.sav", "gen3_eon_ticket", "gen3_eon"),
            ("Pokémon - Ruby Version.sav", "ereader", "gen3_ereader"),
            ("Pokémon - Sapphire Version.sav", "gen3_eon_ticket", "gen3_eon"),
            ("Pokémon - Sapphire Version.sav", "ereader", "gen3_ereader"),
            ("Pokémon - Emerald Version.sav", "gen3_old_sea_map", "gen3_old_sea_map"),
            ("Pokémon - FireRed Version.sav", "gen3_aurora", "gen3_aurora"),
            ("Pokémon - LeafGreen Version.sav", "gen3_mystic", "gen3_mystic"),
            # Gen 4 - Platinum events
            ("Pokemon - Platinum Version (USA).sav", "gen4_member_card", "gen4_member_card"),
            ("Pokemon - Platinum Version (USA).sav", "gen4_oaks_letter", "gen4_oaks_letter"),
        ]

        for save_name, event_id, test_label in test_cases:
            # Find this save
            matching_saves = [s for name, s in save_status.items() if s["path"].name == save_name]

            if not matching_saves:
                self._record_skipped(save_name, event_id, "Save file not found", test_label)
                continue

            save_info = matching_saves[0]
            save_path = save_info["path"]

            if save_info["status"] != "valid":
                self._record_skipped(save_name, event_id, f"Save is {save_info['status']}", test_label)
                continue

            if event_id is None:
                self._record_skipped(save_name, event_id, "Baseline test (no event)", test_label)
                continue

            # Run test
            if event_id == "ereader":
                self._test_ereader(save_path, event_id, test_label)
            else:
                self._test_ticket(save_path, event_id, test_label)

        return self._finalize_results()

    def _test_ticket(self, save_path: Path, event_id: str, test_label: str):
        """Test applying a ticket event."""
        try:
            save = load_save(save_path)

            from pokecable_runtime.events.catalog import get_event_by_id
            event = get_event_by_id(event_id)

            if not event:
                self._record_failed(save_path.name, event_id, "Event not found in catalog", test_label)
                return

            if save.game not in event.get("games", []):
                self._record_failed(
                    save_path.name,
                    event_id,
                    f"Event not available for {save.game}",
                    test_label,
                )
                return

            print(f"\n[{test_label}] Testing {event_id} on {save_path.name}")
            print(f"  Game: {save.game} (Gen {save.generation})")

            # Use public API which handles save/backup properly
            try:
                from r36s_pokecable_core import apply_event_to_save

                # Copy save to temp and apply event
                with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    tmp_path.write_bytes(save_path.read_bytes())

                try:
                    result = apply_event_to_save(tmp_path, event_id)

                    if result.get("success"):
                        self._record_passed(
                            save_path.name,
                            event_id,
                            f"Event '{event['name_key']}' applied successfully",
                            test_label,
                        )
                    else:
                        msg = result.get("message", "Unknown error")
                        self._record_failed(save_path.name, event_id, f"Event failed: {msg}", test_label)

                finally:
                    tmp_path.unlink(missing_ok=True)

            except Exception as e:
                self._record_failed(save_path.name, event_id, f"Applicator error: {e}", test_label)

        except SaveError as e:
            self._record_failed(save_path.name, event_id, f"SaveError: {e}", test_label)
        except Exception as e:
            self._record_failed(save_path.name, event_id, f"Unexpected error: {e}", test_label)

    def _test_ereader(self, save_path: Path, event_id: str, test_label: str):
        """Test applying e-Reader battles."""
        try:
            save = load_save(save_path)

            if "ruby" not in save.game.lower() and "sapphire" not in save.game.lower():
                self._record_skipped(save_path.name, event_id, "e-Reader only for Ruby/Sapphire", test_label)
                return

            print(f"\n[{test_label}] Testing {event_id} (e-Reader) on {save_path.name}")
            print(f"  Game: {save.game} (Gen {save.generation})")

            from pokecable_runtime.events.ereader_battles import list_ereader_battles
            from pokecable_runtime.events.applicator import apply_ereader_battle

            battles = list_ereader_battles()
            if not battles:
                self._record_failed(save_path.name, event_id, "No e-Reader battles found", test_label)
                return

            # Test first battle using public API
            battle = battles[0]
            slot = 0

            try:
                from r36s_pokecable_core import apply_ereader_to_save

                # Copy save to temp and apply e-Reader battle
                with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    tmp_path.write_bytes(save_path.read_bytes())

                try:
                    result = apply_ereader_to_save(tmp_path, slot, battle["id"])
                    if result.get("success"):
                        self._record_passed(
                            save_path.name,
                            f"ereader_{battle['id']}",
                            f"e-Reader '{battle['name']}' applied to slot {slot}",
                            test_label,
                        )
                    else:
                        msg = result.get("message", "Unknown error")
                        self._record_failed(save_path.name, event_id, f"e-Reader failed: {msg}", test_label)

                finally:
                    tmp_path.unlink(missing_ok=True)

            except Exception as e:
                self._record_failed(save_path.name, event_id, f"e-Reader error: {e}", test_label)

        except SaveError as e:
            self._record_failed(save_path.name, event_id, f"SaveError: {e}", test_label)
        except Exception as e:
            self._record_failed(save_path.name, event_id, f"Unexpected error: {e}", test_label)

    def _record_passed(self, save_name: str, event_id: str, message: str, test_label: str):
        """Record passed test."""
        result = SaveTestResult(test_label, save_name, self._get_gen_from_name(save_name), event_id, "PASSED", message)
        self.results.append(result)

        gen_key = f"gen{result.generation}"
        if gen_key not in self.summary["by_generation"]:
            self.summary["by_generation"][gen_key] = {"passed": 0, "failed": 0, "skipped": 0}

        self.summary["by_generation"][gen_key]["passed"] += 1
        self.summary["total_tests"] += 1
        self.summary["passed"] += 1

        print(f"  ✓ PASSED: {message}")

    def _record_failed(self, save_name: str, event_id: str, message: str, test_label: str):
        """Record failed test."""
        result = SaveTestResult(test_label, save_name, self._get_gen_from_name(save_name), event_id, "FAILED", message)
        self.results.append(result)

        gen_key = f"gen{result.generation}"
        if gen_key not in self.summary["by_generation"]:
            self.summary["by_generation"][gen_key] = {"passed": 0, "failed": 0, "skipped": 0}

        self.summary["by_generation"][gen_key]["failed"] += 1
        self.summary["total_tests"] += 1
        self.summary["failed"] += 1

        print(f"  ✗ FAILED: {message}")

    def _record_skipped(self, save_name: str, event_id: Optional[str], message: str, test_label: str):
        """Record skipped test."""
        result = SaveTestResult(test_label, save_name, self._get_gen_from_name(save_name), event_id, "SKIPPED", message)
        self.results.append(result)

        gen_key = f"gen{result.generation}"
        if gen_key not in self.summary["by_generation"]:
            self.summary["by_generation"][gen_key] = {"passed": 0, "failed": 0, "skipped": 0}

        self.summary["by_generation"][gen_key]["skipped"] += 1
        self.summary["total_tests"] += 1
        self.summary["skipped"] += 1

        print(f"  ⊘ SKIPPED: {message}")

    def _get_gen_from_name(self, save_name: str) -> int:
        """Extract generation from save name."""
        if "gen 1" in save_name or "gen1" in save_name:
            return 1
        elif "gen 2" in save_name or "gen2" in save_name or "crystal" in save_name.lower() or "gold" in save_name.lower():
            return 2
        elif "gen 3" in save_name or "gen3" in save_name or any(x in save_name.lower() for x in ["ruby", "sapphire", "emerald", "firered", "leafgreen"]):
            return 3
        elif "gen 4" in save_name or "gen4" in save_name or "platinum" in save_name.lower():
            return 4
        return 0

    def _finalize_results(self) -> Dict:
        """Finalize and print summary."""
        print("\n" + "=" * 120)
        print("TEST RESULTS SUMMARY")
        print("=" * 120)

        print(f"\nTotal tests:  {self.summary['total_tests']}")
        print(f"Passed:       {self.summary['passed']} ({100 * self.summary['passed'] // max(1, self.summary['total_tests'])}%)")
        print(f"Failed:       {self.summary['failed']}")
        print(f"Skipped:      {self.summary['skipped']}")

        print("\nBy Generation:")
        for gen_key in sorted(self.summary["by_generation"].keys()):
            stats = self.summary["by_generation"][gen_key]
            print(
                f"  {gen_key}: "
                f"{stats['passed']} passed, "
                f"{stats['failed']} failed, "
                f"{stats['skipped']} skipped"
            )

        # Failures
        failures = [r for r in self.results if r.status == "FAILED"]
        if failures:
            print("\nFailed Tests:")
            for result in failures:
                print(f"  - {result.test_name}: {result.save_name} ({result.event_id})")
                print(f"    {result.message}")

        return {
            "summary": self.summary,
            "results": [r.to_dict() for r in self.results],
        }


def main():
    """Main test runner."""
    test_saves_dir = Path(__file__).parent.parent / "roms" / "test-saves"

    if not test_saves_dir.exists():
        print(f"ERROR: Test saves directory not found: {test_saves_dir}")
        sys.exit(1)

    runner = ExtrasTestRunnerFixed(test_saves_dir)
    test_results = runner.run_all_tests()

    # Save report
    report_path = Path(__file__).parent / "test_extras_results_fixed.json"
    with open(report_path, "w") as f:
        json.dump(test_results, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")

    sys.exit(0 if test_results["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
