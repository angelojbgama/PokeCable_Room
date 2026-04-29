from __future__ import annotations

import asyncio
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from app.battles import BattleManager
from app.showdown import LocalShowdownAdapter, ProcessShowdownAdapter


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
        self.manager = BattleManager(room_timeout_seconds=60, max_rooms=10, adapter=LocalShowdownAdapter())

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

    async def test_cross_generation_battle_uses_highest_generation_format(self) -> None:
        room, _slot = await self.manager.create_room(
            room_name="cross-battle",
            password="pw",
            client_id="a",
            generation=1,
            game="pokemon_yellow",
        )
        self.assertEqual(room.format_id, "gen1customgame")

        room, slot = await self.manager.join_room(
            room_name="cross-battle",
            password="pw",
            client_id="b",
            generation=3,
            game="pokemon_emerald",
        )

        self.assertEqual(slot, "B")
        self.assertTrue(room.is_ready())
        self.assertEqual(room.generation, 3)
        self.assertEqual(room.format_id, "gen3customgame")

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

    async def test_cleanup_expired_removes_battle_room(self) -> None:
        manager = BattleManager(room_timeout_seconds=0, max_rooms=10, adapter=LocalShowdownAdapter())
        await manager.create_room(room_name="expired", password="pw", client_id="a", generation=3, game="pokemon_emerald")
        expired = await manager.cleanup_expired()
        self.assertEqual(expired, ["expired"])
        self.assertNotIn("expired", manager.rooms)

    async def test_process_showdown_adapter_uses_persistent_json_lines_worker(self) -> None:
        worker_source = """
import json
import sys

battles = {}

for line in sys.stdin:
    request = json.loads(line)
    request_id = request.get("request_id")
    kind = request.get("type")
    if kind == "create_battle":
        battle_id = "worker-battle-1"
        battles[battle_id] = ["|worker_start|"]
        print(json.dumps({"request_id": request_id, "ok": True, "battle_id": battle_id, "logs": ["|worker_start|"], "finished": False}), flush=True)
    elif kind == "battle_action":
        battle_id = request["battle_id"]
        log = f"|worker_action|{request['client_id']}|{request['action']}"
        battles.setdefault(battle_id, []).append(log)
        print(json.dumps({"request_id": request_id, "ok": True, "battle_id": battle_id, "logs": [log], "finished": False}), flush=True)
    elif kind == "get_logs":
        battle_id = request["battle_id"]
        print(json.dumps({"request_id": request_id, "ok": True, "battle_id": battle_id, "logs": battles.get(battle_id, []), "finished": False}), flush=True)
    elif kind == "battle_forfeit":
        battle_id = request["battle_id"]
        log = f"|worker_forfeit|{request['client_id']}"
        battles.setdefault(battle_id, []).append(log)
        print(json.dumps({"request_id": request_id, "ok": True, "battle_id": battle_id, "logs": [log], "finished": True}), flush=True)
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            worker_path = Path(temp_dir) / "fake_showdown_worker.py"
            worker_path.write_text(textwrap.dedent(worker_source), encoding="utf-8")
            adapter = ProcessShowdownAdapter(f"{sys.executable} {worker_path}")
            try:
                result = await adapter.create_battle(
                    "gen3customgame",
                    canonical_team("Mew"),
                    canonical_team("Pikachu"),
                    player_a_id="a",
                    player_b_id="b",
                )
                self.assertEqual(result.battle_id, "worker-battle-1")
                self.assertEqual(result.logs, ["|worker_start|"])
                self.assertEqual(result.requests, {})

                action_result = await adapter.send_action("worker-battle-1", "a", "move 1")
                self.assertEqual(action_result.logs, ["|worker_action|a|move 1"])

                logs = await adapter.get_logs("worker-battle-1")
                self.assertEqual(logs, ["|worker_start|", "|worker_action|a|move 1"])

                forfeit_result = await adapter.forfeit("worker-battle-1", "b")
                self.assertEqual(forfeit_result.logs, ["|worker_forfeit|b"])
                self.assertTrue(forfeit_result.finished)
            finally:
                await adapter.close()

    async def test_process_showdown_adapter_ping_reports_worker(self) -> None:
        worker_source = """
import json
import sys
for line in sys.stdin:
    request = json.loads(line)
    if request.get('type') == 'ping':
        print(json.dumps({'request_id': request.get('request_id'), 'ok': True, 'pong': True}), flush=True)
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            worker_path = Path(temp_dir) / "fake_showdown_worker.py"
            worker_path.write_text(textwrap.dedent(worker_source), encoding="utf-8")
            adapter = ProcessShowdownAdapter(f"{sys.executable} {worker_path}")
            try:
                status = await adapter.ping()
                self.assertEqual(status.status, "process_worker")
            finally:
                await adapter.close()


if __name__ == "__main__":
    unittest.main()
