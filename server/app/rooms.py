from __future__ import annotations

import asyncio
import os
from datetime import timedelta

from .models import (
    Player,
    PlayerSlot,
    PokemonOffer,
    Room,
    RoomError,
    game_family_for_generation,
    generation_mismatch_message,
    now_utc,
    parse_client_id,
    parse_game_id,
    parse_generation,
    parse_room_name,
)
from .security import hash_room_password, verify_room_password


class RoomManager:
    def __init__(self, room_timeout_seconds: int | None = None, max_rooms: int | None = None) -> None:
        self.room_timeout_seconds = room_timeout_seconds or int(os.getenv("ROOM_TIMEOUT_SECONDS", "900"))
        self.max_rooms = max_rooms or int(os.getenv("MAX_ROOMS", "200"))
        self.rooms: dict[str, Room] = {}
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
    ) -> tuple[Room, PlayerSlot]:
        async with self._lock:
            room_name = parse_room_name(room_name)
            client_id = parse_client_id(client_id)
            generation = parse_generation(generation)
            game = parse_game_id(game, generation)
            if not password:
                raise RoomError("invalid_password", "Senha da sala e obrigatoria.")
            if room_name in self.rooms:
                raise RoomError("room_exists", "Ja existe uma sala com esse nome.")
            if len(self.rooms) >= self.max_rooms:
                raise RoomError("server_full", "Limite de salas atingido no servidor.")
            expires_at = now_utc() + timedelta(seconds=self.room_timeout_seconds)
            room = Room(
                room_name=room_name,
                password_hash=hash_room_password(password),
                generation=generation,
                game_family=game_family_for_generation(generation),
                expires_at=expires_at,
            )
            slot: PlayerSlot = "A"
            room.players[slot] = Player(slot=slot, client_id=client_id, generation=generation, game=game)
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
    ) -> tuple[Room, PlayerSlot]:
        async with self._lock:
            room_name = parse_room_name(room_name)
            client_id = parse_client_id(client_id)
            generation = parse_generation(generation)
            game = parse_game_id(game, generation)
            room = self.rooms.get(room_name)
            if room is None:
                raise RoomError("room_not_found", "Sala nao encontrada.")
            if now_utc() >= room.expires_at:
                self._remove_room_locked(room_name)
                raise RoomError("room_expired", "Sala expirada.")
            if not verify_room_password(password, room.password_hash):
                raise RoomError("invalid_password", "Senha incorreta.")
            if generation != room.generation:
                raise RoomError("generation_mismatch", generation_mismatch_message(room.generation, generation))
            if room.is_full():
                raise RoomError("room_full", "A sala ja possui dois jogadores.")
            slot: PlayerSlot = "A" if "A" not in room.players else "B"
            room.players[slot] = Player(slot=slot, client_id=client_id, generation=generation, game=game)
            self.client_rooms[client_id] = (room_name, slot)
            return room, slot

    async def offer_pokemon(self, *, client_id: str, payload: dict) -> tuple[Room, PlayerSlot, PokemonOffer]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            offer = PokemonOffer.from_message(payload)
            if offer.generation != room.generation:
                raise RoomError("generation_mismatch", generation_mismatch_message(room.generation, offer.generation))
            room.offers[slot] = offer
            room.confirmations[slot] = False
            return room, slot, offer

    async def confirm_trade(self, *, client_id: str) -> tuple[Room, PlayerSlot, bool]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            if not room.has_both_offers():
                raise RoomError("offers_missing", "Aguardando os dois jogadores enviarem seus Pokemon.")
            room.confirmations[slot] = True
            return room, slot, room.is_committed()

    async def cancel_room(self, *, client_id: str, reason: str = "cancelled") -> Room | None:
        async with self._lock:
            known = self.client_rooms.get(client_id)
            if not known:
                return None
            room_name, _slot = known
            room = self.rooms.get(room_name)
            if room is not None:
                room.scrub_sensitive_data()
                room.players = {}
            self._remove_room_locked(room_name)
            return room

    async def disconnect(self, client_id: str) -> Room | None:
        async with self._lock:
            known = self.client_rooms.pop(client_id, None)
            if not known:
                return None
            room_name, slot = known
            room = self.rooms.get(room_name)
            if room is None:
                return None
            room.players.pop(slot, None)
            room.scrub_sensitive_data()
            if not room.players:
                self._remove_room_locked(room_name)
                return None
            return room

    async def cleanup_expired(self) -> list[str]:
        async with self._lock:
            expired = [name for name, room in self.rooms.items() if now_utc() >= room.expires_at]
            for room_name in expired:
                room = self.rooms.get(room_name)
                if room:
                    room.scrub_sensitive_data()
                self._remove_room_locked(room_name)
            return expired

    async def remove_room_after_commit(self, room_name: str) -> None:
        async with self._lock:
            room = self.rooms.get(room_name)
            if room:
                room.scrub_sensitive_data()
            self._remove_room_locked(room_name)

    async def get_room(self, room_name: str) -> Room | None:
        async with self._lock:
            return self.rooms.get(room_name)

    def _room_for_client_locked(self, client_id: str) -> tuple[Room, PlayerSlot]:
        client_id = parse_client_id(client_id)
        known = self.client_rooms.get(client_id)
        if not known:
            raise RoomError("client_not_in_room", "Client nao esta em uma sala.")
        room_name, slot = known
        room = self.rooms.get(room_name)
        if room is None:
            raise RoomError("room_not_found", "Sala nao encontrada.")
        if now_utc() >= room.expires_at:
            self._remove_room_locked(room_name)
            raise RoomError("room_expired", "Sala expirada.")
        return room, slot

    def _remove_room_locked(self, room_name: str) -> None:
        room = self.rooms.pop(room_name, None)
        if room is None:
            return
        for player in room.players.values():
            self.client_rooms.pop(player.client_id, None)
