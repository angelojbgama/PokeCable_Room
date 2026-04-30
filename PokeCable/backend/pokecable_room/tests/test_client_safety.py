from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pokecable_room.backups import (
    capture_save_signature,
    create_backup,
    create_forensic_failed_save_copy,
    restore_backup,
    restore_backup_checked,
    save_signature_matches,
    update_backup_metadata,
)
from pokecable_room.canonical import CanonicalPokemon, CanonicalMove, CanonicalSpecies
from pokecable_room.client import (
    SAVE_CHANGED_DURING_ROOM,
    _default_battle_action,
    _can_continue_with_report,
    _client_supported_protocols,
    _client_supported_trade_modes,
    _preflight_result_for_payload,
    _print_report,
    run_trade,
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
            restore_backup_checked(backup, save)
            self.assertEqual(save.read_bytes(), b"synthetic-save")
            restore_backup(backup, save)
            self.assertEqual(save.read_bytes(), b"synthetic-save")

    def test_save_signature_uses_sha256_and_detects_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "test.sav"
            save.write_bytes(b"first")
            signature = capture_save_signature(save)
            self.assertTrue(save_signature_matches(save, signature))
            save.write_bytes(b"second")
            self.assertFalse(save_signature_matches(save, signature))

    def test_update_backup_metadata_and_forensic_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            save = root / "Pokemon Yellow.sav"
            save.write_bytes(b"save-before")
            backup, metadata = create_backup(save, root / "backups", {"room": "audit"})
            update_backup_metadata(metadata, {"write_result": "pending", "nested": {"stage": "prepare"}})
            save.write_bytes(b"save-after")
            forensic = create_forensic_failed_save_copy(save, root / "backups")
            data = json.loads(metadata.read_text(encoding="utf-8"))
            self.assertEqual(data["write_result"], "pending")
            self.assertEqual(data["nested"]["stage"], "prepare")
            self.assertTrue(forensic.exists())
            self.assertEqual(forensic.read_bytes(), b"save-after")
            restore_backup_checked(backup, save)
            self.assertEqual(save.read_bytes(), b"save-before")

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

    def test_default_battle_action_prefers_first_available_move(self) -> None:
        request = {
            "active": [
                {
                    "moves": [
                        {"move": "Tackle", "pp": 35, "maxpp": 35, "disabled": False},
                        {"move": "Growl", "pp": 40, "maxpp": 40, "disabled": False},
                    ]
                }
            ]
        }
        self.assertEqual(_default_battle_action(request), "move 1")


class FakeParser:
    def __init__(self, save_bytes_after_write: bytes = b"modified-save") -> None:
        self._save_bytes_after_write = save_bytes_after_write
        self.saved_paths: list[Path] = []
        self.removed_payloads: list[PokemonPayload] = []

    def get_generation(self) -> int:
        return 1

    def get_game_id(self) -> str:
        return "pokemon_red"

    def export_pokemon(self, location: str) -> PokemonPayload:
        return PokemonPayload(
            generation=1,
            game="pokemon_red",
            species_id=25,
            species_name="Pikachu",
            level=30,
            nickname="PIKACHU",
            ot_name="ASH",
            trainer_id=123,
            raw_data_base64="ZmFrZQ==",
            display_summary="#25 Pikachu Lv. 30 — Sem item",
        )

    def export_canonical(self, location: str) -> CanonicalPokemon:
        return CanonicalPokemon(
            source_generation=1,
            source_game="pokemon_red",
            species_national_id=25,
            species_name="Pikachu",
            nickname="PIKACHU",
            level=30,
            ot_name="ASH",
            trainer_id=123,
            species=CanonicalSpecies(
                national_dex_id=25,
                source_species_id=84,
                source_species_id_space="gen1_internal",
                name="Pikachu",
            ),
            moves=[CanonicalMove(move_id=33, source_generation=1)],
        )

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        self.removed_payloads.append(received_payload)

    def save(self, save_path: str | Path) -> None:
        path = Path(save_path)
        path.write_bytes(self._save_bytes_after_write)
        self.saved_paths.append(path)


class FakeNetworkClient:
    def __init__(self, messages: list[dict]) -> None:
        self.messages = list(messages)
        self.sent: list[dict] = []
        self.client_id = "local-client"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def send(self, payload: dict) -> None:
        self.sent.append(payload)

    async def wait_for(self, accepted_types: set[str], error_types: set[str] | None = None) -> dict:
        if not self.messages:
            raise AssertionError(f"Sem mensagem para wait_for({accepted_types})")
        message = self.messages.pop(0)
        if message.get("type") not in accepted_types:
            raise AssertionError(f"Mensagem inesperada: {message} para accepted_types={accepted_types}")
        return message


class ClientTradeSafetyFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_failure_after_commit_restores_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            save_path = root / "Pokemon Red.sav"
            save_path.write_bytes(b"original-save")
            backup_dir = root / "backups"
            parser = FakeParser(save_bytes_after_write=b"written-save")
            initial_signature = capture_save_signature(save_path)
            peer_payload = parser.export_pokemon("party:0").to_dict()
            room = {
                "players": {
                    "A": {"client_id": "local-client", "generation": 1},
                    "B": {"client_id": "peer-client", "generation": 1},
                },
                "trade_mode": "same_generation",
            }
            network = FakeNetworkClient(
                [
                    {"type": "room_created"},
                    {"type": "room_ready", "room": room},
                    {"type": "preflight_required", "received_payload": peer_payload, "derived_mode": "same_generation"},
                    {"type": "preflight_ready"},
                    {"type": "prepare_write", "received_payload": peer_payload, "sent_payload": peer_payload, "room": room},
                    {"type": "trade_commit_write", "received_payload": peer_payload, "sent_payload": peer_payload, "room": room},
                    {"type": "trade_write_failed", "message": "Falha remota apos commit.", "error_code": "remote_write_failed"},
                ]
            )
            ui = FakeUI()
            with mock.patch("pokecable_room.client.PokeCableNetworkClient", return_value=network):
                with self.assertRaises(RuntimeError) as raised:
                    await run_trade(
                        server_url="ws://example",
                        action="create",
                        room_name="room",
                        password="pw",
                        parser=parser,
                        pokemon_location="party:0",
                        auto_confirm=True,
                        backup_dir=str(backup_dir),
                        save_path=save_path,
                        initial_save_signature=initial_signature,
                        ui=ui,
                        auto_trade_evolution=False,
                    )
            self.assertIn("revertida", str(raised.exception))
            self.assertEqual(save_path.read_bytes(), b"original-save")
            forensic = list(backup_dir.glob("*.failed-after-write.sav"))
            self.assertEqual(len(forensic), 1)
            self.assertEqual(forensic[0].read_bytes(), b"written-save")
            metadata_files = list(backup_dir.glob("*.metadata.json"))
            self.assertEqual(len(metadata_files), 1)
            metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
            self.assertEqual(metadata["write_result"], "rolled_back")
            self.assertEqual(metadata["error_code"], "remote_write_failed")
            self.assertEqual(metadata["species_sent"]["species_name"], "Pikachu")
            self.assertEqual(metadata["species_received"]["species_name"], "Pikachu")
            self.assertTrue(any(message["type"] == "write_done" for message in network.sent))
            self.assertIn("Falha remota após escrita local. Restaurando backup...", ui.messages)
            self.assertIn("Backup restaurado.", ui.messages)

    async def test_save_changed_before_write_ready_sends_standardized_error_and_does_not_save(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            save_path = root / "Pokemon Red.sav"
            save_path.write_bytes(b"original-save")
            initial_signature = capture_save_signature(save_path)
            save_path.write_bytes(b"changed-before-prepare")
            parser = FakeParser()
            peer_payload = parser.export_pokemon("party:0").to_dict()
            room = {
                "players": {
                    "A": {"client_id": "local-client", "generation": 1},
                    "B": {"client_id": "peer-client", "generation": 1},
                },
                "trade_mode": "same_generation",
            }
            network = FakeNetworkClient(
                [
                    {"type": "room_created"},
                    {"type": "room_ready", "room": room},
                    {"type": "preflight_required", "received_payload": peer_payload, "derived_mode": "same_generation"},
                    {"type": "preflight_ready"},
                    {"type": "prepare_write", "received_payload": peer_payload, "sent_payload": peer_payload, "room": room},
                ]
            )
            with mock.patch("pokecable_room.client.PokeCableNetworkClient", return_value=network):
                with self.assertRaises(RuntimeError) as raised:
                    await run_trade(
                        server_url="ws://example",
                        action="create",
                        room_name="room",
                        password="pw",
                        parser=parser,
                        pokemon_location="party:0",
                        auto_confirm=True,
                        backup_dir=str(root / "backups"),
                        save_path=save_path,
                        initial_save_signature=initial_signature,
                        ui=FakeUI(),
                        auto_trade_evolution=False,
                    )
            self.assertIn("modificado enquanto a sala estava aberta", str(raised.exception))
            self.assertEqual(parser.saved_paths, [])
            write_ready_messages = [message for message in network.sent if message["type"] == "write_ready"]
            self.assertEqual(len(write_ready_messages), 1)
            write_ready = write_ready_messages[0]
            self.assertFalse(write_ready["ready"])
            self.assertEqual(write_ready["error"], SAVE_CHANGED_DURING_ROOM)
            self.assertEqual(write_ready["metadata"]["error_code"], SAVE_CHANGED_DURING_ROOM)
            self.assertIn("expected_signature", write_ready["metadata"])
            self.assertIn("current_signature", write_ready["metadata"])

    async def test_normal_completion_does_not_roll_back(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            save_path = root / "Pokemon Red.sav"
            save_path.write_bytes(b"original-save")
            backup_dir = root / "backups"
            parser = FakeParser(save_bytes_after_write=b"written-save")
            initial_signature = capture_save_signature(save_path)
            peer_payload = parser.export_pokemon("party:0").to_dict()
            room = {
                "players": {
                    "A": {"client_id": "local-client", "generation": 1},
                    "B": {"client_id": "peer-client", "generation": 1},
                },
                "trade_mode": "same_generation",
            }
            network = FakeNetworkClient(
                [
                    {"type": "room_created"},
                    {"type": "room_ready", "room": room},
                    {"type": "preflight_required", "received_payload": peer_payload, "derived_mode": "same_generation"},
                    {"type": "preflight_ready"},
                    {"type": "prepare_write", "received_payload": peer_payload, "sent_payload": peer_payload, "room": room},
                    {"type": "trade_commit_write", "received_payload": peer_payload, "sent_payload": peer_payload, "room": room},
                    {"type": "trade_completed", "message": "ok"},
                ]
            )
            ui = FakeUI()
            with mock.patch("pokecable_room.client.PokeCableNetworkClient", return_value=network):
                await run_trade(
                    server_url="ws://example",
                    action="create",
                    room_name="room",
                    password="pw",
                    parser=parser,
                    pokemon_location="party:0",
                    auto_confirm=True,
                    backup_dir=str(backup_dir),
                    save_path=save_path,
                    initial_save_signature=initial_signature,
                    ui=ui,
                    auto_trade_evolution=False,
                )
            self.assertEqual(save_path.read_bytes(), b"written-save")
            self.assertEqual(list(backup_dir.glob("*.failed-after-write.sav")), [])
            metadata_files = list(backup_dir.glob("*.metadata.json"))
            metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
            self.assertEqual(metadata["write_result"], "completed")
            self.assertIsNotNone(metadata["save_signature_after_write"])
            self.assertIn("Troca concluída nos dois lados.", ui.messages)


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
