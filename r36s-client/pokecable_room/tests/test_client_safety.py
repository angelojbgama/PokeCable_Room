from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.backups import create_backup, restore_backup
from pokecable_room.client import _can_continue_with_report, _client_supported_trade_modes, _print_report
from pokecable_room.compatibility.matrix import SAME_GENERATION, TIME_CAPSULE_GEN1_GEN2
from pokecable_room.compatibility.report import CompatibilityReport
from pokecable_room.parsers.base import PokemonPayload
from pokecable_room.trade import validate_payload_for_local_save


class FakeUI:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        self.messages.append(message)


class ClientSafetyTests(unittest.TestCase):
    def test_client_rejects_payload_from_other_generation(self) -> None:
        payload = PokemonPayload(
            generation=3,
            game="pokemon_emerald",
            species_id=64,
            species_name="Kadabra",
            level=32,
            nickname="KADABRA",
            ot_name="TEST",
            trainer_id=1,
            raw_data_base64="ZmFrZQ==",
            display_summary="Kadabra Lv. 32",
        )
        with self.assertRaises(ValueError):
            validate_payload_for_local_save(payload, local_generation=2)

    def test_backup_and_restore_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            save = root / "Pokemon Crystal.sav"
            save.write_bytes(b"synthetic-save")
            backup_dir = root / "backups"
            backup, metadata = create_backup(
                save,
                backup_dir,
                {
                    "original_save": str(save),
                    "generation": 2,
                    "game": "pokemon_crystal",
                    "room": "room",
                    "sent": {"species": "Kadabra", "level": 32, "nickname": "KADABRA"},
                    "received": {"species": "Machoke", "level": 35, "nickname": "MACHOKE"},
                },
            )
            self.assertTrue(backup.exists())
            self.assertTrue(metadata.exists())
            save.write_bytes(b"changed")
            restore_backup(backup, save)
            self.assertEqual(save.read_bytes(), b"synthetic-save")

    def test_auto_confirm_does_not_pass_data_loss_without_unsafe_flag(self) -> None:
        report = CompatibilityReport(
            compatible=True,
            mode="legacy_downconvert_experimental",
            source_generation=3,
            target_generation=1,
            data_loss=["held_item"],
            requires_user_confirmation=True,
        )
        self.assertFalse(
            _can_continue_with_report(report, auto_confirm=True, unsafe_auto_confirm_data_loss=False)
        )
        self.assertTrue(
            _can_continue_with_report(report, auto_confirm=True, unsafe_auto_confirm_data_loss=True)
        )
        self.assertTrue(
            _can_continue_with_report(report, auto_confirm=False, unsafe_auto_confirm_data_loss=False)
        )

    def test_client_announces_only_enabled_cross_generation_modes(self) -> None:
        self.assertEqual(
            _client_supported_trade_modes(1, cross_generation_enabled=False, enabled_cross_generation_modes=[TIME_CAPSULE_GEN1_GEN2]),
            [SAME_GENERATION],
        )
        modes = _client_supported_trade_modes(
            1,
            cross_generation_enabled=True,
            enabled_cross_generation_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        self.assertIn(SAME_GENERATION, modes)
        self.assertIn(TIME_CAPSULE_GEN1_GEN2, modes)

    def test_print_report_includes_data_loss_and_removed_entries(self) -> None:
        ui = FakeUI()
        _print_report(
            ui,
            {
                "warnings": ["Held item sera removido."],
                "data_loss": ["held_item"],
                "removed_moves": [{"move_id": 252, "name": "Fake Out"}],
                "removed_items": [{"item_id": 187, "name": "King's Rock"}],
                "removed_fields": ["ability", "nature"],
                "transformations": ["Trainer ID sera reduzido para 16 bits."],
            },
        )
        output = "\n".join(ui.messages)
        self.assertIn("Perda de dados: held_item", output)
        self.assertIn("Move removido: Fake Out", output)
        self.assertIn("Item removido: King's Rock", output)
        self.assertIn("Campo removido: ability", output)
        self.assertIn("Conversao: Trainer ID sera reduzido para 16 bits.", output)


if __name__ == "__main__":
    unittest.main()
