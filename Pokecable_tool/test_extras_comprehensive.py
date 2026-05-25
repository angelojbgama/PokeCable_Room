#!/usr/bin/env python3
"""
Comprehensive test for Extras feature across all generations (Gen 1-4).
Tests all event types: tickets and e-Reader battles.
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add paths
POKECABLE_SAVE_PATH = Path(__file__).parent / "pokecable_save"
sys.path.insert(0, str(POKECABLE_SAVE_PATH))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pokecable_save import load_save, SaveError
except ImportError as e:
    print(f"ERROR: Could not import pokecable_save: {e}")
    sys.exit(1)


class ExtrasTestRunner:
    """Run Extras tests on saves."""

    def __init__(self, test_saves_dir: Path):
        self.test_saves_dir = test_saves_dir
        self.results = []
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
        print("COMPREHENSIVE EXTRAS FEATURE TEST")
        print("=" * 120)

        # Define test matrix
        test_matrix = [
            # Gen 1 - No extras
            ("gen 1", "Pokémon - Red Version.sav", None, "gen1"),
            ("gen 1", "Pokémon - Blue Version.sav", None, "gen1"),
            ("gen 1", "Pokémon - Yellow Version.sav", None, "gen1"),
            # Gen 2 - GS Ball ticket
            ("gen 2", "Pokémon - Gold Version.sav", None, "gen2"),
            ("gen 2", "Pokémon - Silver Version.sav", None, "gen2"),
            ("gen 2", "Pokémon - Crystal Version.sav", "gen2_gsball", "gen2_with_extras"),
            # Gen 3 - Multiple tickets and e-Reader
            ("gen 3", "Pokémon - Ruby Version.sav", "gen3_eon_ticket", "gen3_with_extras"),
            ("gen 3", "Pokémon - Ruby Version.sav", "ereader", "gen3_ereader"),
            ("gen 3", "Pokémon - Sapphire Version.sav", "gen3_eon_ticket", "gen3_with_extras"),
            ("gen 3", "Pokémon - Sapphire Version.sav", "ereader", "gen3_ereader"),
            ("gen 3", "Pokémon - Emerald Version.sav", "gen3_eon_ticket", "gen3_with_extras"),
            ("gen 3", "Pokémon - Emerald Version.sav", "gen3_old_sea_map", "gen3_with_extras"),
            ("gen 3", "Pokémon - FireRed Version.sav", "gen3_aurora", "gen3_with_extras"),
            ("gen 3", "Pokémon - LeafGreen Version.sav", "gen3_mystic", "gen3_with_extras"),
            # Gen 4 - Member card, Oak's letter, Enigma stone (only Platinum has two)
            ("gen 4", "Pokemon - Platinum Version (USA).sav", "gen4_member_card", "gen4_with_extras"),
            ("gen 4", "Pokemon - Platinum Version (USA).sav", "gen4_oaks_letter", "gen4_with_extras"),
        ]

        for gen_dir, save_name, event_id, test_label in test_matrix:
            save_path = self.test_saves_dir / gen_dir / save_name

            # Check if file exists
            if not save_path.exists():
                self._record_skipped(
                    save_path,
                    event_id,
                    f"Save file not found: {save_path}",
                    test_label,
                )
                continue

            if event_id is None:
                self._record_skipped(save_path, None, "No events for this game", test_label)
                continue

            # Determine if it's a ticket or e-Reader battle
            if event_id == "ereader":
                self._test_ereader_battle(save_path, event_id, test_label)
            else:
                self._test_ticket_event(save_path, event_id, test_label)

        return self._finalize_results()

    def _test_ticket_event(self, save_path: Path, event_id: str, test_label: str):
        """Test applying a ticket event to a save."""
        try:
            # Load save
            save = load_save(save_path)
            print(f"\n[{test_label}] Testing {event_id} on {save_path.name}")
            print(f"  Game: {save.game} (Gen {save.generation})")

            # Get events for this game
            from pokecable_runtime.events.catalog import get_events_for_game, get_event_by_id

            event = get_event_by_id(event_id)
            if not event:
                self._record_failed(
                    save_path,
                    event_id,
                    "Event not found in catalog",
                    test_label,
                )
                return

            if save.game not in event.get("games", []):
                self._record_failed(
                    save_path,
                    event_id,
                    f"Event not available for {save.game}",
                    test_label,
                )
                return

            # Create temporary save for testing
            with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
                tmp.write(save.bytes)
                tmp_path = Path(tmp.name)

            try:
                # Apply event
                from pokecable_runtime.events.applicator import apply_event

                result = apply_event(save, event_id)

                if result.get("success"):
                    # Save it
                    save.save(tmp_path)
                    # Verify by loading again
                    save_verify = load_save(tmp_path)
                    self._record_passed(
                        save_path,
                        event_id,
                        f"Successfully applied {event['name_key']}",
                        test_label,
                    )
                else:
                    msg = result.get("message", "Unknown error")
                    self._record_failed(
                        save_path,
                        event_id,
                        f"Event application failed: {msg}",
                        test_label,
                    )
            finally:
                tmp_path.unlink(missing_ok=True)

        except SaveError as e:
            self._record_failed(
                save_path,
                event_id,
                f"SaveError: {e}",
                test_label,
            )
        except Exception as e:
            self._record_failed(
                save_path,
                event_id,
                f"Unexpected error: {e}",
                test_label,
            )

    def _test_ereader_battle(self, save_path: Path, event_id: str, test_label: str):
        """Test applying e-Reader battle to a save."""
        try:
            save = load_save(save_path)
            print(f"\n[{test_label}] Testing {event_id} (e-Reader battles) on {save_path.name}")
            print(f"  Game: {save.game} (Gen {save.generation})")

            # e-Reader only for Ruby/Sapphire
            if "ruby" not in save.game.lower() and "sapphire" not in save.game.lower():
                self._record_skipped(
                    save_path,
                    event_id,
                    "e-Reader only available for Ruby/Sapphire",
                    test_label,
                )
                return

            from pokecable_runtime.events.ereader_battles import list_ereader_battles
            from pokecable_runtime.events.applicator import apply_ereader_battle

            battles = list_ereader_battles()
            if not battles:
                self._record_failed(
                    save_path,
                    event_id,
                    "No e-Reader battles found",
                    test_label,
                )
                return

            # Test first battle in first slot
            battle = battles[0]
            slot = 0

            with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
                tmp.write(save.bytes)
                tmp_path = Path(tmp.name)

            try:
                result = apply_ereader_battle(save, slot, battle["id"])

                if result.get("success"):
                    save.save(tmp_path)
                    save_verify = load_save(tmp_path)
                    self._record_passed(
                        save_path,
                        f"ereader_{battle['id']}_slot{slot}",
                        f"Successfully applied e-Reader battle '{battle['name']}' in slot {slot}",
                        test_label,
                    )
                else:
                    msg = result.get("message", "Unknown error")
                    self._record_failed(
                        save_path,
                        event_id,
                        f"e-Reader application failed: {msg}",
                        test_label,
                    )
            finally:
                tmp_path.unlink(missing_ok=True)

        except SaveError as e:
            self._record_failed(
                save_path,
                event_id,
                f"SaveError: {e}",
                test_label,
            )
        except Exception as e:
            self._record_failed(
                save_path,
                event_id,
                f"Unexpected error: {e}",
                test_label,
            )

    def _record_passed(self, save_path: Path, event_id: str, message: str, test_label: str):
        """Record a passed test."""
        gen = self._get_generation_from_save(save_path)
        gen_key = f"gen{gen}"

        if gen_key not in self.summary["by_generation"]:
            self.summary["by_generation"][gen_key] = {"passed": 0, "failed": 0, "skipped": 0}

        self.summary["by_generation"][gen_key]["passed"] += 1
        self.summary["total_tests"] += 1
        self.summary["passed"] += 1

        self.results.append(
            {
                "test": test_label,
                "save": save_path.name,
                "generation": gen,
                "event": event_id,
                "status": "PASSED",
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )
        print(f"  ✓ PASSED: {message}")

    def _record_failed(self, save_path: Path, event_id: str, message: str, test_label: str):
        """Record a failed test."""
        gen = self._get_generation_from_save(save_path)
        gen_key = f"gen{gen}"

        if gen_key not in self.summary["by_generation"]:
            self.summary["by_generation"][gen_key] = {"passed": 0, "failed": 0, "skipped": 0}

        self.summary["by_generation"][gen_key]["failed"] += 1
        self.summary["total_tests"] += 1
        self.summary["failed"] += 1

        self.results.append(
            {
                "test": test_label,
                "save": save_path.name,
                "generation": gen,
                "event": event_id,
                "status": "FAILED",
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )
        print(f"  ✗ FAILED: {message}")

    def _record_skipped(self, save_path: Path, event_id: Optional[str], message: str, test_label: str):
        """Record a skipped test."""
        gen = self._get_generation_from_save(save_path)
        gen_key = f"gen{gen}"

        if gen_key not in self.summary["by_generation"]:
            self.summary["by_generation"][gen_key] = {"passed": 0, "failed": 0, "skipped": 0}

        self.summary["by_generation"][gen_key]["skipped"] += 1
        self.summary["total_tests"] += 1
        self.summary["skipped"] += 1

        self.results.append(
            {
                "test": test_label,
                "save": save_path.name,
                "generation": gen,
                "event": event_id,
                "status": "SKIPPED",
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )
        print(f"  ⊘ SKIPPED: {message}")

    def _get_generation_from_save(self, save_path: Path) -> int:
        """Extract generation from path."""
        parent = save_path.parent.name
        if "gen 1" in parent or "gen1" in parent:
            return 1
        elif "gen 2" in parent or "gen2" in parent:
            return 2
        elif "gen 3" in parent or "gen3" in parent:
            return 3
        elif "gen 4" in parent or "gen4" in parent:
            return 4
        return 0

    def _finalize_results(self) -> Dict:
        """Finalize results and print summary."""
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

        # Print detailed failures
        failures = [r for r in self.results if r["status"] == "FAILED"]
        if failures:
            print("\nFailed Tests:")
            for result in failures:
                print(f"  - {result['test']}: {result['save']} - {result['message']}")

        return {
            "summary": self.summary,
            "results": self.results,
        }


def main():
    """Main test function."""
    test_saves_dir = Path(__file__).parent.parent / "roms" / "test-saves"

    if not test_saves_dir.exists():
        print(f"ERROR: Test saves directory not found: {test_saves_dir}")
        sys.exit(1)

    runner = ExtrasTestRunner(test_saves_dir)
    test_results = runner.run_all_tests()

    # Save report
    report_path = Path(__file__).parent / "test_extras_results.json"
    with open(report_path, "w") as f:
        json.dump(test_results, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")

    # Exit with appropriate code
    sys.exit(0 if test_results["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
