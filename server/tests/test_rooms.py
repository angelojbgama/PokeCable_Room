from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from app.models import (
    CANONICAL_CROSS_GENERATION,
    FORWARD_TRANSFER_TO_GEN3,
    LEGACY_DOWNCONVERT_EXPERIMENTAL,
    RAW_SAME_GENERATION,
    SAME_GENERATION,
    TIME_CAPSULE_GEN1_GEN2,
    RoomError,
)
from app.rooms import RoomManager


PROTOCOLS = [RAW_SAME_GENERATION, CANONICAL_CROSS_GENERATION]
ALL_CROSS_MODES = [TIME_CAPSULE_GEN1_GEN2, FORWARD_TRANSFER_TO_GEN3, LEGACY_DOWNCONVERT_EXPERIMENTAL]


def game_for(generation: int) -> str:
    return {1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[generation]


def same_payload(generation: int) -> dict:
    return {
        "payload_version": 2,
        "generation": generation,
        "game": game_for(generation),
        "source_generation": generation,
        "source_game": game_for(generation),
        "target_generation": generation,
        "species_id": 64,
        "species_name": "Kadabra",
        "level": 32,
        "nickname": "KADABRA",
        "ot_name": "TEST",
        "trainer_id": 12345,
        "raw_data_base64": "ZmFrZQ==",
        "display_summary": "Kadabra Lv. 32",
        "summary": {"display_summary": "Kadabra Lv. 32"},
        "raw": {"format": f"gen{generation}-party-v1", "data_base64": "ZmFrZQ=="},
    }


def canonical_payload(generation: int, target_generation: int, *, raw: bool = False) -> dict:
    payload = same_payload(generation)
    payload["target_generation"] = target_generation
    if not raw:
        payload["raw_data_base64"] = ""
        payload["raw"] = {}
    payload["canonical"] = {
        "source_generation": generation,
        "source_game": game_for(generation),
        "species_national_id": 151,
        "species_name": "Mew",
        "species": {
            "national_dex_id": 151,
            "source_species_id": 151,
            "source_species_id_space": "national_dex",
            "name": "Mew",
        },
        "nickname": "MEW",
        "level": 30,
        "ot_name": "TEST",
        "trainer_id": 12345,
    }
    return payload


class RoomManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        asyncio.get_running_loop().slow_callback_duration = 10

    async def test_create_room_has_no_user_trade_mode(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        room, slot = await manager.create_room(
            room_name="room",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            trade_mode=FORWARD_TRANSFER_TO_GEN3,
            supported_protocols=PROTOCOLS,
        )
        self.assertEqual(slot, "A")
        self.assertEqual(room.trade_mode, SAME_GENERATION)
        self.assertEqual(room.derived_modes, {})

    async def test_join_different_generation_derives_two_direction_modes(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10, cross_generation_enabled=True, enabled_trade_modes=ALL_CROSS_MODES)
        await manager.create_room(
            room_name="room",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_red",
            supported_protocols=PROTOCOLS,
        )
        room, slot = await manager.join_room(
            room_name="room",
            password="pw",
            client_id="b",
            generation=3,
            game="pokemon_emerald",
            supported_protocols=PROTOCOLS,
        )
        self.assertEqual(slot, "B")
        self.assertEqual(room.derived_modes["A"], LEGACY_DOWNCONVERT_EXPERIMENTAL)
        self.assertEqual(room.derived_modes["B"], FORWARD_TRANSFER_TO_GEN3)

    async def test_join_cross_generation_requires_server_flags(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10, cross_generation_enabled=False)
        await manager.create_room(room_name="off", password="pw", client_id="a", generation=1, game="pokemon_red", supported_protocols=PROTOCOLS)
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(room_name="off", password="pw", client_id="b", generation=3, game="pokemon_emerald", supported_protocols=PROTOCOLS)
        self.assertEqual(raised.exception.code, "generation_mismatch")

        manager = RoomManager(
            room_timeout_seconds=60,
            max_rooms=10,
            cross_generation_enabled=True,
            enabled_trade_modes=[FORWARD_TRANSFER_TO_GEN3],
        )
        await manager.create_room(room_name="partial", password="pw", client_id="a", generation=1, game="pokemon_red", supported_protocols=PROTOCOLS)
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(room_name="partial", password="pw", client_id="b", generation=3, game="pokemon_emerald", supported_protocols=PROTOCOLS)
        self.assertEqual(raised.exception.code, "trade_mode_disabled")

    async def test_same_generation_does_not_require_cross_generation(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10, cross_generation_enabled=False)
        await manager.create_room(room_name="same", password="pw", client_id="a", generation=2, game="pokemon_crystal", supported_protocols=[RAW_SAME_GENERATION])
        room, slot = await manager.join_room(
            room_name="same",
            password="pw",
            client_id="b",
            generation=2,
            game="pokemon_crystal",
            supported_protocols=[RAW_SAME_GENERATION],
        )
        self.assertEqual(slot, "B")
        self.assertEqual(room.derived_modes, {"A": SAME_GENERATION, "B": SAME_GENERATION})

    async def test_offer_same_generation_requires_raw(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="same", password="pw", client_id="a", generation=2, game="pokemon_crystal", supported_protocols=[RAW_SAME_GENERATION])
        await manager.join_room(room_name="same", password="pw", client_id="b", generation=2, game="pokemon_crystal", supported_protocols=[RAW_SAME_GENERATION])
        payload = same_payload(2)
        payload["raw_data_base64"] = ""
        payload["raw"] = {}
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=payload)
        self.assertEqual(raised.exception.code, "invalid_payload")

    async def test_offer_cross_generation_requires_canonical(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10, cross_generation_enabled=True, enabled_trade_modes=ALL_CROSS_MODES)
        await manager.create_room(room_name="cross", password="pw", client_id="a", generation=1, game="pokemon_red", supported_protocols=PROTOCOLS)
        await manager.join_room(room_name="cross", password="pw", client_id="b", generation=3, game="pokemon_emerald", supported_protocols=PROTOCOLS)
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=same_payload(1))
        self.assertEqual(raised.exception.code, "invalid_payload")

    async def test_both_offers_start_preflight(self) -> None:
        manager, room = await self._cross_room()
        await manager.offer_pokemon(client_id="a", payload=canonical_payload(1, 3, raw=True))
        room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=canonical_payload(3, 1, raw=True))
        requests = manager.preflight_requests(room)
        self.assertEqual(set(requests), {"A", "B"})
        self.assertEqual(requests["A"]["derived_mode"], LEGACY_DOWNCONVERT_EXPERIMENTAL)
        self.assertEqual(requests["B"]["derived_mode"], FORWARD_TRANSFER_TO_GEN3)

    async def test_confirm_before_preflight_fails(self) -> None:
        manager, _room = await self._cross_room_with_offers()
        with self.assertRaises(RoomError) as raised:
            await manager.confirm_trade(client_id="a")
        self.assertEqual(raised.exception.code, "preflight_required")

    async def test_preflight_failed_blocks_trade(self) -> None:
        manager, _room = await self._cross_room_with_offers()
        report = {"compatible": False, "blocking_reasons": ["Treecko National Dex #252 nao existe na Gen 1."]}
        _room, _slot, blocked, ready, reports = await manager.submit_preflight_result(client_id="a", compatible=False, report=report)
        self.assertTrue(blocked)
        self.assertFalse(ready)
        self.assertFalse(reports["A"]["compatible"])
        with self.assertRaises(RoomError):
            await manager.confirm_trade(client_id="a")

    async def test_both_preflight_ok_then_commit(self) -> None:
        manager, _room = await self._cross_room_with_offers()
        await manager.submit_preflight_result(client_id="a", compatible=True, report={"compatible": True})
        _room, _slot, blocked, ready, _reports = await manager.submit_preflight_result(client_id="b", compatible=True, report={"compatible": True})
        self.assertFalse(blocked)
        self.assertTrue(ready)
        _room, _slot, committed = await manager.confirm_trade(client_id="a")
        self.assertFalse(committed)
        _room, _slot, committed = await manager.confirm_trade(client_id="b")
        self.assertTrue(committed)

    async def test_raw_cross_generation_never_commits(self) -> None:
        manager, _room = await self._cross_room()
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=same_payload(1))
        self.assertEqual(raised.exception.code, "invalid_payload")

    async def test_payload_generation_mismatch_fails(self) -> None:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10)
        await manager.create_room(room_name="same", password="pw", client_id="a", generation=1, game="pokemon_red", supported_protocols=[RAW_SAME_GENERATION])
        await manager.join_room(room_name="same", password="pw", client_id="b", generation=1, game="pokemon_red", supported_protocols=[RAW_SAME_GENERATION])
        with self.assertRaises(RoomError) as raised:
            await manager.offer_pokemon(client_id="a", payload=same_payload(3))
        self.assertEqual(raised.exception.code, "generation_mismatch")

    async def test_password_third_user_timeout_and_disconnect_basics(self) -> None:
        manager = RoomManager(room_timeout_seconds=1, max_rooms=10)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=1, game="pokemon_red")
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(room_name="room", password="bad", client_id="b", generation=1, game="pokemon_red")
        self.assertEqual(raised.exception.code, "invalid_password")
        await manager.join_room(room_name="room", password="pw", client_id="b", generation=1, game="pokemon_red")
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(room_name="room", password="pw", client_id="c", generation=1, game="pokemon_red")
        self.assertEqual(raised.exception.code, "room_full")
        await manager.disconnect("a")
        room = await manager.get_room("room")
        self.assertIsNotNone(room)
        await asyncio.sleep(1.1)
        self.assertEqual(await manager.cleanup_expired(), ["room"])

    async def test_env_allow_cross_generation_without_enabled_modes_does_not_release_mode(self) -> None:
        with patch.dict("os.environ", {"ALLOW_CROSS_GENERATION": "true", "ENABLED_TRADE_MODES": ""}):
            manager = RoomManager(room_timeout_seconds=60, max_rooms=10, cross_generation_enabled=None)
        await manager.create_room(room_name="room", password="pw", client_id="a", generation=1, game="pokemon_red", supported_protocols=PROTOCOLS)
        with self.assertRaises(RoomError) as raised:
            await manager.join_room(room_name="room", password="pw", client_id="b", generation=2, game="pokemon_crystal", supported_protocols=PROTOCOLS)
        self.assertEqual(raised.exception.code, "trade_mode_disabled")

    async def _cross_room(self) -> tuple[RoomManager, object]:
        manager = RoomManager(room_timeout_seconds=60, max_rooms=10, cross_generation_enabled=True, enabled_trade_modes=ALL_CROSS_MODES)
        await manager.create_room(room_name="cross", password="pw", client_id="a", generation=1, game="pokemon_red", supported_protocols=PROTOCOLS)
        room, _slot = await manager.join_room(
            room_name="cross",
            password="pw",
            client_id="b",
            generation=3,
            game="pokemon_emerald",
            supported_protocols=PROTOCOLS,
        )
        return manager, room

    async def _cross_room_with_offers(self) -> tuple[RoomManager, object]:
        manager, room = await self._cross_room()
        await manager.offer_pokemon(client_id="a", payload=canonical_payload(1, 3, raw=True))
        room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=canonical_payload(3, 1, raw=True))
        return manager, room


if __name__ == "__main__":
    unittest.main()
