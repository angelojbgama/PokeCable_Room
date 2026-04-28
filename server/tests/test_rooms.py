from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from app.models import RoomError
from app.models import FORWARD_TRANSFER_TO_GEN3, LEGACY_DOWNCONVERT_EXPERIMENTAL, SAME_GENERATION, TIME_CAPSULE_GEN1_GEN2
from app.rooms import RoomManager


def synthetic_payload(generation: int, game: str | None = None) -> dict:
    default_games = {1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}
    return {
        "generation": generation,
        "game": game or default_games[generation],
        "species_id": 64,
        "species_name": "Kadabra",
        "level": 32,
        "nickname": "KADABRA",
        "ot_name": "TEST",
        "trainer_id": 12345,
        "raw_data_base64": "ZmFrZQ==",
        "display_summary": "Kadabra Lv. 32",
    }


def synthetic_payload_v2(generation: int, game: str | None = None) -> dict:
    payload = synthetic_payload(generation, game)
    payload.update(
        {
            "payload_version": 2,
            "source_generation": generation,
            "source_game": payload["game"],
            "target_generation": generation,
            "trade_mode": SAME_GENERATION,
            "summary": {"display_summary": payload["display_summary"]},
            "canonical": {
                "source_generation": generation,
                "source_game": payload["game"],
                "species_national_id": payload["species_id"],
                "species_name": payload["species_name"],
                "nickname": payload["nickname"],
                "level": payload["level"],
                "ot_name": payload["ot_name"],
                "trainer_id": payload["trainer_id"],
            },
            "raw": {"format": f"gen{generation}-party-v1", "data_base64": payload["raw_data_base64"]},
            "compatibility_report": {
                "compatible": True,
                "mode": SAME_GENERATION,
                "source_generation": generation,
                "target_generation": generation,
            },
        }
    )
    return payload


def synthetic_cross_payload_v2(generation: int, target_generation: int, trade_mode: str, game: str | None = None) -> dict:
    payload = synthetic_payload_v2(generation, game)
    payload["raw_data_base64"] = ""
    payload["raw"] = {}
    payload["target_generation"] = target_generation
    payload["trade_mode"] = trade_mode
    payload["canonical"]["species"] = {
        "national_dex_id": payload["species_id"],
        "source_species_id": payload["species_id"],
        "source_species_id_space": "national_dex",
        "name": payload["species_name"],
    }
    payload["compatibility_report"]["mode"] = trade_mode
    payload["compatibility_report"]["target_generation"] = target_generation
    return payload


class RoomManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        asyncio.get_running_loop().slow_callback_duration = 10

    async def test_create_and_join_room(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        room, slot = await manager.create_room(
            room_name="crystal-paqueta",
            password="secret",
            client_id="client-a",
            generation=2,
            game="pokemon_crystal",
        )
        self.assertEqual(slot, "A")
        self.assertEqual(room.generation, 2)
        self.assertEqual(room.trade_mode, SAME_GENERATION)
        self.assertIn(TIME_CAPSULE_GEN1_GEN2, room.players["A"].supported_trade_modes)

        room, slot = await manager.join_room(
            room_name="crystal-paqueta",
            password="secret",
            client_id="client-b",
            generation=2,
            game="pokemon_crystal",
        )
        self.assertEqual(slot, "B")
        self.assertTrue(room.is_ready())

    async def test_rejects_third_user(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=1, game="pokemon_red")
        await manager.join_room(room_name="room", password="pw", client_id="b", generation=1, game="pokemon_red")
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(room_name="room", password="pw", client_id="c", generation=1, game="pokemon_red")
        self.assertEqual(raised.exception.code, "room_full")

    async def test_rejects_wrong_password(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=1, game="pokemon_red")
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(room_name="room", password="bad", client_id="b", generation=1, game="pokemon_red")
        self.assertEqual(raised.exception.code, "invalid_password")

    async def test_rejects_generation_mismatch_on_join(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=2, game="pokemon_crystal")
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(room_name="room", password="pw", client_id="b", generation=3, game="pokemon_emerald")
        self.assertEqual(raised.exception.code, "generation_mismatch")
        self.assertIn("Esta sala e Gen 2", raised.exception.message)
        self.assertIn("Cross-generation", raised.exception.message)
        room = await manager.get_room("room")
        self.assertIsNotNone(room)
        self.assertFalse(room.compatibility_status["compatible"])
        self.assertEqual(room.compatibility_status["mode"], "forward_transfer_to_gen3")

    async def test_exchanges_synthetic_payloads_when_generation_matches(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        room, _ = await manager.create_room(room_name="room", password="pw", client_id="a", generation=2, game="pokemon_crystal")
        await manager.join_room(room_name="room", password="pw", client_id="b", generation=2, game="pokemon_crystal")

        await manager.offer_pokemon(client_id="a", payload=synthetic_payload(2))
        await manager.offer_pokemon(client_id="b", payload=synthetic_payload(2))
        room, _slot, committed = await manager.confirm_trade(client_id="a")
        self.assertFalse(committed)
        room, _slot, committed = await manager.confirm_trade(client_id="b")
        self.assertTrue(committed)
        self.assertEqual(room.offers["A"].generation, 2)
        self.assertEqual(room.offers["B"].generation, 2)

    async def test_accepts_payload_version_2_for_same_generation(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=2, game="pokemon_crystal")
        await manager.join_room(room_name="room", password="pw", client_id="b", generation=2, game="pokemon_crystal")

        room, slot, offer = await manager.offer_pokemon(client_id="a", payload=synthetic_payload_v2(2))
        self.assertEqual(slot, "A")
        self.assertEqual(room.trade_mode, SAME_GENERATION)
        self.assertEqual(offer.payload_version, 2)
        self.assertEqual(offer.raw["format"], "gen2-party-v1")

    async def test_rejects_generation_mismatch_payload(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=2, game="pokemon_crystal")
        await manager.join_room(room_name="room", password="pw", client_id="b", generation=2, game="pokemon_crystal")
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=synthetic_payload(3, "pokemon_emerald"))
        self.assertEqual(raised.exception.code, "generation_mismatch")

    async def test_cross_generation_requires_enabled_mode(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        await manager.create_room(
            room_name="time",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            trade_mode=TIME_CAPSULE_GEN1_GEN2,
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        room, slot = await manager.join_room(
            room_name="time",
            password="pw",
            client_id="b",
            generation=2,
            game="pokemon_crystal",
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        self.assertEqual(slot, "B")
        self.assertEqual(room.trade_mode, TIME_CAPSULE_GEN1_GEN2)
        self.assertTrue(room.compatibility_status["compatible"])

        with self.assertRaises(RoomError) as raised:
            await manager.create_room(
                room_name="forward",
                password="pw",
                client_id="c",
                generation=1,
                game="pokemon_red",
                trade_mode=FORWARD_TRANSFER_TO_GEN3,
            )
        self.assertEqual(raised.exception.code, "trade_mode_disabled")

    async def test_time_capsule_enabled_mode_only_allows_gen1_gen2_pair(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        await manager.create_room(
            room_name="time",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            trade_mode=TIME_CAPSULE_GEN1_GEN2,
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(
                room_name="time",
                password="pw",
                client_id="b",
                generation=3,
                game="pokemon_emerald",
                supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
            )
        self.assertEqual(raised.exception.code, "game_mismatch")

    async def test_forward_transfer_enabled_mode_only_allows_gen1_or_gen2_to_gen3(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
        )
        await manager.create_room(
            room_name="forward",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            trade_mode=FORWARD_TRANSFER_TO_GEN3,
            supported_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
        )
        room, slot = await manager.join_room(
            room_name="forward",
            password="pw",
            client_id="b",
            generation=3,
            game="pokemon_emerald",
            supported_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
        )
        self.assertEqual(slot, "B")
        self.assertEqual(room.trade_mode, FORWARD_TRANSFER_TO_GEN3)

        with self.assertRaises(RoomError) as raised:
            await manager.create_room(
                room_name="bad-forward-source",
                password="pw",
                client_id="c",
                generation=3,
                game="pokemon_emerald",
                trade_mode=FORWARD_TRANSFER_TO_GEN3,
                supported_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
            )
        self.assertEqual(raised.exception.code, "game_mismatch")

    async def test_forward_room_rejects_reverse_offer_when_legacy_mode_is_not_enabled(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
        )
        await manager.create_room(
            room_name="forward",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            trade_mode=FORWARD_TRANSFER_TO_GEN3,
            supported_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
        )
        await manager.join_room(
            room_name="forward",
            password="pw",
            client_id="b",
            generation=3,
            game="pokemon_emerald",
            supported_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
        )

        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(
                client_id="b",
                payload=synthetic_cross_payload_v2(3, 1, FORWARD_TRANSFER_TO_GEN3, "pokemon_emerald"),
            )
        self.assertEqual(raised.exception.code, "trade_mode_disabled")

    async def test_legacy_downconvert_enabled_mode_only_allows_gen3_to_gen1_or_gen2(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[LEGACY_DOWNCONVERT_EXPERIMENTAL],
        )
        await manager.create_room(
            room_name="legacy",
            password="pw",
            client_id="a",
            generation=3,
            game="pokemon_emerald",
            trade_mode=LEGACY_DOWNCONVERT_EXPERIMENTAL,
            supported_trade_modes=[LEGACY_DOWNCONVERT_EXPERIMENTAL],
        )
        room, slot = await manager.join_room(
            room_name="legacy",
            password="pw",
            client_id="b",
            generation=2,
            game="pokemon_crystal",
            supported_trade_modes=[LEGACY_DOWNCONVERT_EXPERIMENTAL],
        )
        self.assertEqual(slot, "B")
        self.assertEqual(room.trade_mode, LEGACY_DOWNCONVERT_EXPERIMENTAL)

        with self.assertRaises(RoomError) as raised:
            await manager.create_room(
                room_name="bad-legacy-source",
                password="pw",
                client_id="c",
                generation=1,
                game="pokemon_red",
                trade_mode=LEGACY_DOWNCONVERT_EXPERIMENTAL,
                supported_trade_modes=[LEGACY_DOWNCONVERT_EXPERIMENTAL],
            )
        self.assertEqual(raised.exception.code, "game_mismatch")

    async def test_cross_generation_create_and_join_require_announced_supported_mode(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        with self.assertRaises(RoomError) as raised:
            await manager.create_room(
                room_name="missing-create-support",
                password="pw",
                client_id="a",
                generation=1,
                game="pokemon_red",
                trade_mode=TIME_CAPSULE_GEN1_GEN2,
                supported_trade_modes=[SAME_GENERATION],
            )
        self.assertEqual(raised.exception.code, "game_mismatch")

        await manager.create_room(
            room_name="missing-join-support",
            password="pw",
            client_id="b",
            generation=1,
            game="pokemon_red",
            trade_mode=TIME_CAPSULE_GEN1_GEN2,
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(
                room_name="missing-join-support",
                password="pw",
                client_id="c",
                generation=2,
                game="pokemon_crystal",
                supported_trade_modes=[SAME_GENERATION],
            )
        self.assertEqual(raised.exception.code, "game_mismatch")

    async def test_cross_generation_global_flag_without_enabled_modes_does_not_release_mode(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[],
        )
        with self.assertRaises(RoomError) as raised:
            await manager.create_room(
                room_name="time",
                password="pw",
                client_id="a",
                generation=1,
                game="pokemon_red",
                trade_mode=TIME_CAPSULE_GEN1_GEN2,
            )
        self.assertEqual(raised.exception.code, "trade_mode_disabled")

    async def test_env_allow_cross_generation_without_enabled_modes_does_not_release_mode(self) -> None:
        with patch.dict("os.environ", {"ALLOW_CROSS_GENERATION": "true", "ENABLED_TRADE_MODES": ""}):
            manager = RoomManager(room_timeout_seconds=60, max_rooms=10, cross_generation_enabled=None)
        with self.assertRaises(RoomError) as raised:
            await manager.create_room(
                room_name="time",
                password="pw",
                client_id="a",
                generation=1,
                game="pokemon_red",
                trade_mode=TIME_CAPSULE_GEN1_GEN2,
            )
        self.assertEqual(raised.exception.code, "trade_mode_disabled")

    async def test_trade_mode_mismatch_blocks_cross_generation_join(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        await manager.create_room(
            room_name="time",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            trade_mode=TIME_CAPSULE_GEN1_GEN2,
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(
                room_name="time",
                password="pw",
                client_id="b",
                generation=3,
                game="pokemon_emerald",
                supported_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
            )
        self.assertEqual(raised.exception.code, "game_mismatch")

    async def test_cross_generation_offer_requires_canonical_payload(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        await manager.create_room(
            room_name="time",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            trade_mode=TIME_CAPSULE_GEN1_GEN2,
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        await manager.join_room(
            room_name="time",
            password="pw",
            client_id="b",
            generation=2,
            game="pokemon_crystal",
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=synthetic_payload(1, "pokemon_red") | {"trade_mode": TIME_CAPSULE_GEN1_GEN2})
        self.assertEqual(raised.exception.code, "invalid_payload")

        room, slot, offer = await manager.offer_pokemon(
            client_id="a",
            payload=synthetic_cross_payload_v2(1, 2, TIME_CAPSULE_GEN1_GEN2, "pokemon_red"),
        )
        self.assertEqual(slot, "A")
        self.assertIsNotNone(offer.canonical)
        self.assertEqual(room.trade_mode, TIME_CAPSULE_GEN1_GEN2)

    async def test_cross_generation_offer_rejects_trade_mode_target_and_canonical_generation_mismatch(self) -> None:
        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        await manager.create_room(
            room_name="time",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            trade_mode=TIME_CAPSULE_GEN1_GEN2,
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )
        await manager.join_room(
            room_name="time",
            password="pw",
            client_id="b",
            generation=2,
            game="pokemon_crystal",
            supported_trade_modes=[TIME_CAPSULE_GEN1_GEN2],
        )

        wrong_mode = synthetic_cross_payload_v2(1, 2, TIME_CAPSULE_GEN1_GEN2, "pokemon_red")
        wrong_mode["trade_mode"] = FORWARD_TRANSFER_TO_GEN3
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=wrong_mode)
        self.assertEqual(raised.exception.code, "trade_mode_mismatch")

        wrong_target = synthetic_cross_payload_v2(1, 3, TIME_CAPSULE_GEN1_GEN2, "pokemon_red")
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=wrong_target)
        self.assertEqual(raised.exception.code, "generation_mismatch")

        wrong_canonical = synthetic_cross_payload_v2(1, 2, TIME_CAPSULE_GEN1_GEN2, "pokemon_red")
        wrong_canonical["canonical"]["source_generation"] = 2
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=wrong_canonical)
        self.assertEqual(raised.exception.code, "generation_mismatch")

    async def test_same_generation_offer_requires_raw_even_with_canonical_payload(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=2, game="pokemon_crystal")
        await manager.join_room(room_name="room", password="pw", client_id="b", generation=2, game="pokemon_crystal")
        payload = synthetic_payload_v2(2)
        payload["raw_data_base64"] = ""
        payload["raw"] = {}
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=payload)
        self.assertEqual(raised.exception.code, "invalid_payload")

    async def test_timeout_cleanup(self) -> None:
        manager = RoomManager(room_timeout_seconds=1, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=1, game="pokemon_red")
        await asyncio.sleep(1.1)
        expired = await manager.cleanup_expired()
        self.assertEqual(expired, ["room"])
        self.assertIsNone(await manager.get_room("room"))

    async def test_disconnect_keeps_room_for_remaining_player(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=1, game="pokemon_red")
        await manager.join_room(room_name="room", password="pw", client_id="b", generation=1, game="pokemon_red")
        await manager.disconnect("a")
        room = await manager.get_room("room")
        self.assertIsNotNone(room)
        self.assertEqual(list(room.players), ["B"])
        self.assertFalse(room.has_both_offers())

        room, slot = await manager.join_room(
            room_name="room",
            password="pw",
            client_id="c",
            generation=1,
            game="pokemon_red",
        )
        self.assertEqual(slot, "A")
        self.assertTrue(room.is_ready())


if __name__ == "__main__":
    unittest.main()
