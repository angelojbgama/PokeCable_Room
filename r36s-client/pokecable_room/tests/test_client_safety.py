from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.backups import create_backup, restore_backup
from pokecable_room.client import (
    _can_continue_with_report,
    _client_supported_protocols,
    _client_supported_trade_modes,
    _preflight_result_for_payload,
    _print_report,
)
from pokecable_room.compatibility.matrix import (
    FORWARD_TRANSFER_TO_GEN3,
    LEGACY_DOWNCONVERT_EXPERIMENTAL,
    SAME_GENERATION,
    TIME_CAPSULE_GEN1_GEN2,
)
from pokecable_room.compatibility.report import CompatibilityReport
from pokecable_room.parsers.base import PokemonPayload
from pokecable_room.trade import validate_payload_for_local_save


class FakeUI:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.confirm_response = True

    def print(self, message: str) -> None:
        self.messages.append(message)

    def confirm(self, message: str, default: bool = False) -> bool:
        self.messages.append(message)
        return self.confirm_response


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

    def test_client_announces_all_generation_modes_without_user_flag(self) -> None:
        modes = _client_supported_trade_modes(1)
        self.assertIn(SAME_GENERATION, modes)
        self.assertIn(TIME_CAPSULE_GEN1_GEN2, modes)
        self.assertIn(FORWARD_TRANSFER_TO_GEN3, modes)
        self.assertIn(LEGACY_DOWNCONVERT_EXPERIMENTAL, modes)

    def test_client_supported_protocols_always_include_raw_and_can_include_canonical(self) -> None:
        self.assertEqual(
            _client_supported_protocols(),
            ["raw_same_generation", "canonical_cross_generation"],
        )

    def test_preflight_has_no_local_cross_generation_flag_block(self) -> None:
        payload = canonical_payload(3, 1, 151, "Mew", native_id=151)
        ok, report = _preflight_result_for_payload(
            payload,
            1,
            cross_generation_policy="safe_default",
            auto_confirm=False,
            unsafe_auto_confirm_data_loss=False,
            ui=FakeUI(),
        )
        self.assertTrue(ok)
        self.assertTrue(report["compatible"])

    def test_preflight_mew_gen3_to_gen1_allows_with_manual_confirmation(self) -> None:
        payload = canonical_payload(3, 1, 151, "Mew", native_id=151)
        ok, report = _preflight_result_for_payload(
            payload,
            1,
            cross_generation_policy="safe_default",
            auto_confirm=False,
            unsafe_auto_confirm_data_loss=False,
            ui=FakeUI(),
        )
        self.assertTrue(ok)
        self.assertTrue(report["compatible"])

    def test_preflight_treecko_gen3_to_gen1_blocks(self) -> None:
        payload = canonical_payload(3, 1, 252, "Treecko", native_id=277)
        ok, report = _preflight_result_for_payload(
            payload,
            1,
            cross_generation_policy="safe_default",
            auto_confirm=False,
            unsafe_auto_confirm_data_loss=False,
            ui=FakeUI(),
        )
        self.assertFalse(ok)
        self.assertFalse(report["compatible"])

    def test_preflight_pikachu_gen1_to_gen3_allows(self) -> None:
        payload = canonical_payload(1, 3, 25, "Pikachu", native_id=84)
        ok, report = _preflight_result_for_payload(
            payload,
            3,
            cross_generation_policy="safe_default",
            auto_confirm=True,
            unsafe_auto_confirm_data_loss=False,
            ui=FakeUI(),
        )
        self.assertTrue(ok)
        self.assertTrue(report["compatible"])

    def test_preflight_data_loss_blocks_auto_confirm_without_unsafe_flag(self) -> None:
        payload = canonical_payload(3, 1, 151, "Mew", native_id=151, ability="Synchronize", nature="Timid")
        ok, report = _preflight_result_for_payload(
            payload,
            1,
            cross_generation_policy="safe_default",
            auto_confirm=True,
            unsafe_auto_confirm_data_loss=False,
            ui=FakeUI(),
        )
        self.assertFalse(ok)
        self.assertIn("confirmacao manual", " ".join(report["blocking_reasons"]))

    def test_preflight_auto_retrocompat_does_not_block_data_loss(self) -> None:
        payload = canonical_payload(3, 1, 151, "Mew", native_id=151, ability="Synchronize", nature="Timid")
        payload.canonical["held_item"] = {"item_id": 199, "name": "Metal Coat", "source_generation": 3}
        payload.canonical["moves"] = [{"move_id": 252, "name": "Fake Out", "source_generation": 3}]
        ok, report = _preflight_result_for_payload(
            payload,
            1,
            cross_generation_policy="auto_retrocompat",
            auto_confirm=True,
            unsafe_auto_confirm_data_loss=False,
            ui=FakeUI(),
        )
        self.assertTrue(ok)
        self.assertTrue(report["compatible"])
        self.assertIn("ability", report["data_loss"])
        self.assertIn("nature", report["data_loss"])
        self.assertIn("held_item", report["data_loss"])
        self.assertIn("moves", report["data_loss"])
        self.assertFalse(report["requires_user_confirmation"])

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


def canonical_payload(
    source_generation: int,
    target_generation: int,
    national_id: int,
    name: str,
    *,
    native_id: int,
    ability: str | None = None,
    nature: str | None = None,
) -> PokemonPayload:
    source_space = {1: "gen1_internal", 2: "national_dex", 3: "gen3_internal"}[source_generation]
    canonical = {
        "source_generation": source_generation,
        "source_game": {1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[source_generation],
        "species": {
            "national_dex_id": national_id,
            "source_species_id": native_id,
            "source_species_id_space": source_space,
            "name": name,
        },
        "species_national_id": national_id,
        "species_name": name,
        "nickname": name.upper(),
        "level": 30,
        "ot_name": "TEST",
        "trainer_id": 12345,
        "moves": [{"move_id": 33, "source_generation": source_generation}],
        "ability": ability,
        "nature": nature,
        "metadata": {},
    }
    return PokemonPayload(
        generation=source_generation,
        game=canonical["source_game"],
        species_id=national_id,
        species_name=name,
        level=30,
        nickname=name.upper(),
        ot_name="TEST",
        trainer_id=12345,
        raw_data_base64="",
        display_summary=f"{name} Lv. 30",
        source_generation=source_generation,
        source_game=canonical["source_game"],
        target_generation=target_generation,
        canonical=canonical,
        raw={},
    )


if __name__ == "__main__":
    unittest.main()
