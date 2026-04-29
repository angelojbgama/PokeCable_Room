from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from .battle_models import BATTLE_FORMATS_BY_GENERATION, BattlePlayer, BattleRoom
from .models import PlayerSlot, RoomError, now_utc, parse_client_id, parse_game_id, parse_generation, parse_room_name
from .security import hash_room_password, verify_room_password
from .showdown import ShowdownAdapter, build_showdown_adapter


class BattleManager:
    def __init__(self, *, room_timeout_seconds: int = 900, max_rooms: int = 100, adapter: ShowdownAdapter | None = None) -> None:
        self.room_timeout_seconds = room_timeout_seconds
        self.max_rooms = max_rooms
        self.adapter = adapter or build_showdown_adapter()
        self.rooms: dict[str, BattleRoom] = {}
        self.client_rooms: dict[str, tuple[str, PlayerSlot]] = {}
        self._lock = asyncio.Lock()

    async def create_room(
        self,
        *,
        room_name: str,
        password: str,
        client_id: str,
        generation: int,
        game: str,
        format_id: str | None = None,
    ) -> tuple[BattleRoom, PlayerSlot]:
        async with self._lock:
            room_name = parse_room_name(room_name)
            client_id = parse_client_id(client_id)
            generation = parse_generation(generation)
            game = parse_game_id(game, generation)
            if not password:
                raise RoomError("invalid_password", "Senha da sala de batalha e obrigatoria.")
            if room_name in self.rooms:
                raise RoomError("room_exists", "Ja existe uma sala de batalha com esse nome.")
            if len(self.rooms) >= self.max_rooms:
                raise RoomError("server_full", "Limite de salas de batalha atingido.")
            format_id = str(format_id or BATTLE_FORMATS_BY_GENERATION[generation])
            room = BattleRoom(
                room_name=room_name,
                password_hash=hash_room_password(password),
                generation=generation,
                format_id=format_id,
                expires_at=now_utc() + timedelta(seconds=self.room_timeout_seconds),
            )
            slot: PlayerSlot = "A"
            room.players[slot] = BattlePlayer(slot=slot, client_id=client_id, generation=generation, game=game)
            self.rooms[room_name] = room
            self.client_rooms[client_id] = (room_name, slot)
            return room, slot

    async def join_room(
        self,
        *,
        room_name: str,
        password: str,
        client_id: str,
        generation: int,
        game: str,
    ) -> tuple[BattleRoom, PlayerSlot]:
        async with self._lock:
            room_name = parse_room_name(room_name)
            client_id = parse_client_id(client_id)
            generation = parse_generation(generation)
            game = parse_game_id(game, generation)
            room = self.rooms.get(room_name)
            if room is None:
                raise RoomError("room_not_found", "Sala de batalha nao encontrada.")
            if now_utc() >= room.expires_at:
                self._remove_room_locked(room_name)
                raise RoomError("room_expired", "Sala de batalha expirada.")
            if room.is_full():
                raise RoomError("room_full", "A sala de batalha ja possui dois jogadores.")
            if not verify_room_password(password, room.password_hash):
                raise RoomError("invalid_password", "Senha incorreta.")
            slot: PlayerSlot = "A" if "A" not in room.players else "B"
            room.players[slot] = BattlePlayer(slot=slot, client_id=client_id, generation=generation, game=game)
            room.generation = max(player.generation for player in room.players.values())
            room.format_id = BATTLE_FORMATS_BY_GENERATION[room.generation]
            room.status = "ready"
            self.client_rooms[client_id] = (room_name, slot)
            return room, slot

    async def offer_team(self, *, client_id: str, team: list[dict[str, Any]]) -> tuple[BattleRoom, PlayerSlot, bool]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            player = room.players[slot]
            player.team = _sanitize_team(team)
            player.ready = True
            player.confirmed = False
            room.status = "teams_ready" if room.has_both_teams() else "waiting_for_teams"
            return room, slot, room.has_both_teams()

    async def confirm_battle(self, *, client_id: str) -> tuple[BattleRoom, PlayerSlot, bool, list[str]]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            if not room.has_both_teams():
                raise RoomError("teams_missing", "Aguardando os dois times antes de iniciar a batalha.")
            room.players[slot].confirmed = True
            if not room.has_both_confirmations():
                return room, slot, False, []
            result = await self.adapter.create_battle(
                room.format_id,
                room.players["A"].team,
                room.players["B"].team,
                player_a_id=room.players["A"].client_id,
                player_b_id=room.players["B"].client_id,
            )
            room.battle_id = result.battle_id
            room.status = "started"
            return room, slot, True, result.logs

    async def send_action(self, *, client_id: str, action: str) -> tuple[BattleRoom, PlayerSlot, list[str], bool]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            if not room.battle_id:
                raise RoomError("battle_not_started", "Batalha ainda nao iniciou.")
            result = await self.adapter.send_action(room.battle_id, client_id, action)
            if result.finished:
                room.status = "finished"
            return room, slot, result.logs, result.finished

    async def forfeit(self, *, client_id: str) -> tuple[BattleRoom, PlayerSlot, list[str]]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            if not room.battle_id:
                raise RoomError("battle_not_started", "Batalha ainda nao iniciou.")
            result = await self.adapter.forfeit(room.battle_id, client_id)
            room.status = "finished"
            return room, slot, result.logs

    async def disconnect(self, client_id: str) -> BattleRoom | None:
        async with self._lock:
            known = self.client_rooms.pop(client_id, None)
            if not known:
                return None
            room_name, slot = known
            room = self.rooms.get(room_name)
            if room is None:
                return None
            room.players.pop(slot, None)
            if not room.players or room.status == "finished":
                self._remove_room_locked(room_name)
                return None
            room.status = "waiting"
            return room

    def _room_for_client_locked(self, client_id: str) -> tuple[BattleRoom, PlayerSlot]:
        client_id = parse_client_id(client_id)
        known = self.client_rooms.get(client_id)
        if not known:
            raise RoomError("client_not_in_room", "Client nao esta em uma sala de batalha.")
        room_name, slot = known
        room = self.rooms.get(room_name)
        if room is None:
            raise RoomError("room_not_found", "Sala de batalha nao encontrada.")
        return room, slot

    def _remove_room_locked(self, room_name: str) -> None:
        room = self.rooms.pop(room_name, None)
        if room is None:
            return
        for player in room.players.values():
            self.client_rooms.pop(player.client_id, None)


def _sanitize_team(team: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(team, list) or not team:
        raise RoomError("invalid_team", "Time de batalha precisa conter pelo menos um Pokemon.")
    if len(team) > 6:
        raise RoomError("invalid_team", "Time de batalha pode ter no maximo 6 Pokemon.")
    sanitized: list[dict[str, Any]] = []
    for item in team:
        if not isinstance(item, dict):
            raise RoomError("invalid_team", "Cada Pokemon do time precisa ser JSON.")
        pokemon = dict(item)
        original_data = dict(pokemon.get("original_data") or {})
        if original_data:
            original_data["raw_data_base64"] = None
            pokemon["original_data"] = original_data
        sanitized.append(pokemon)
    return sanitized
