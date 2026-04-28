from __future__ import annotations

import asyncio
import unittest

from app.models import RoomError
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

    async def test_rejects_generation_mismatch_payload(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=2, game="pokemon_crystal")
        await manager.join_room(room_name="room", password="pw", client_id="b", generation=2, game="pokemon_crystal")
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=synthetic_payload(3, "pokemon_emerald"))
        self.assertEqual(raised.exception.code, "generation_mismatch")

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
