from __future__ import annotations

import asyncio
import unittest

from app.battles import BattleManager
from app.battle_engine import LocalBattleEngineAdapter
from app.models import RoomError


def canonical_team(species: str = "Mew") -> list[dict]:
    return [
        {
            "source_generation": 3,
            "source_game": "pokemon_emerald",
            "species_national_id": 151,
            "species_name": species,
            "species": {
                "national_dex_id": 151,
                "source_species_id": 151,
                "source_species_id_space": "gen3_internal",
                "name": species,
            },
            "nickname": species.upper(),
            "level": 50,
            "ot_name": "TEST",
            "trainer_id": 12345,
            "original_data": {"generation": 3, "game": "pokemon_emerald", "format": "gen3-party-v1", "raw_data_base64": "SHOULD_NOT_SURVIVE"},
        }
    ]


class BattleManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        asyncio.get_running_loop().slow_callback_duration = 10
        self.manager = BattleManager(room_timeout_seconds=60, max_rooms=10, adapter=LocalBattleEngineAdapter())

    async def test_create_join_offer_confirm_and_action(self) -> None:
        room, slot = await self.manager.create_room(
            room_name="battle",
            password="pw",
            client_id="a",
            generation=3,
            game="pokemon_emerald",
        )
        self.assertEqual(slot, "A")
        room, slot = await self.manager.join_room(
            room_name="battle",
            password="pw",
            client_id="b",
            generation=3,
            game="pokemon_ruby",
        )
        self.assertEqual(slot, "B")
        self.assertTrue(room.is_ready())

        room, _slot, ready = await self.manager.offer_team(client_id="a", team=canonical_team("Mew"))
        self.assertFalse(ready)
        room, _slot, ready = await self.manager.offer_team(client_id="b", team=canonical_team("Pikachu"))
        self.assertTrue(ready)
        self.assertIsNone(room.players["A"].team[0]["original_data"]["raw_data_base64"])

        _room, _slot, started, result = await self.manager.confirm_battle(client_id="a")
        self.assertFalse(started)
        room, _slot, started, result = await self.manager.confirm_battle(client_id="b")
        self.assertTrue(started)
        self.assertTrue(room.battle_id)
        self.assertIn("|start|", result.logs)
        self.assertTrue(result.requests)

        _room, _slot, result = await self.manager.send_action(client_id="a", action="move 1")
        self.assertFalse(result.finished)
        self.assertTrue(any("|choice|a|move 1" == line for line in result.logs))

    async def test_cross_generation_battle_rejects_mixed_generation_join(self) -> None:
        room, _slot = await self.manager.create_room(
            room_name="cross-battle",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_yellow",
        )
        self.assertEqual(room.format_id, "gen1customgame")

        with self.assertRaises(RoomError) as ctx:
            await self.manager.join_room(
                room_name="cross-battle",
                password="pw",
                client_id="b",
                generation=3,
                game="pokemon_emerald",
            )

        self.assertEqual(ctx.exception.code, "generation_mismatch")
        self.assertEqual(room.generation, 1)
        self.assertEqual(room.format_id, "gen1customgame")

    async def test_forfeit_finishes_battle(self) -> None:
        await self.manager.create_room(room_name="ff", password="pw", client_id="a", generation=3, game="pokemon_emerald")
        await self.manager.join_room(room_name="ff", password="pw", client_id="b", generation=3, game="pokemon_ruby")
        await self.manager.offer_team(client_id="a", team=canonical_team("Mew"))
        await self.manager.offer_team(client_id="b", team=canonical_team("Pikachu"))
        await self.manager.confirm_battle(client_id="a")
        room, _slot, _started, _result = await self.manager.confirm_battle(client_id="b")

        room, _slot, result = await self.manager.forfeit(client_id="a")

        self.assertEqual(room.status, "finished")
        self.assertTrue(any("|forfeit|a" == line for line in result.logs))

    async def test_finished_battle_room_can_be_reused_for_new_match(self) -> None:
        await self.manager.create_room(room_name="reuse", password="pw", client_id="a", generation=3, game="pokemon_emerald")
        await self.manager.join_room(room_name="reuse", password="pw", client_id="b", generation=3, game="pokemon_ruby")
        await self.manager.offer_team(client_id="a", team=canonical_team("Mew"))
        await self.manager.offer_team(client_id="b", team=canonical_team("Pikachu"))
        await self.manager.confirm_battle(client_id="a")
        room, _slot, _started, _result = await self.manager.confirm_battle(client_id="b")
        self.assertTrue(room.battle_id)

        room, _slot, result = await self.manager.forfeit(client_id="a")
        self.assertTrue(result.finished)
        self.assertEqual(room.status, "finished")

        room, _slot, ready = await self.manager.offer_team(client_id="a", team=canonical_team("Mew"))
        self.assertFalse(ready)
        self.assertIsNone(room.battle_id)
        self.assertEqual(room.status, "waiting_for_teams")
        self.assertFalse(room.players["B"].ready)

    async def test_update_player_context_rejects_generation_mismatch(self) -> None:
        await self.manager.create_room(room_name="ctx", password="pw", client_id="a", generation=1, game="pokemon_red")
        room, _slot = await self.manager.join_room(room_name="ctx", password="pw", client_id="b", generation=1, game="pokemon_blue")
        self.assertEqual(room.format_id, "gen1customgame")

        with self.assertRaises(RoomError) as ctx:
            await self.manager.update_player_context(client_id="b", generation=3, game="pokemon_emerald")

        self.assertEqual(ctx.exception.code, "generation_mismatch")
        self.assertEqual(room.generation, 1)
        self.assertEqual(room.format_id, "gen1customgame")
        self.assertEqual(room.status, "ready")

    async def test_cleanup_expired_removes_battle_room(self) -> None:
        manager = BattleManager(room_timeout_seconds=0, max_rooms=10, adapter=LocalBattleEngineAdapter())
        await manager.create_room(room_name="expired", password="pw", client_id="a", generation=3, game="pokemon_emerald")
        expired = await manager.cleanup_expired()
        self.assertEqual(expired, ["expired"])
        self.assertNotIn("expired", manager.rooms)

    async def test_local_adapter_ping_reports_local_engine(self) -> None:
        status = await self.manager.adapter.ping()
        self.assertEqual(status.status, "local_engine")


if __name__ == "__main__":
    unittest.main()
