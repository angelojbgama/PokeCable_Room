from __future__ import annotations

import asyncio
import os
from datetime import timedelta
from typing import Iterable

from .models import (
    CANONICAL_CROSS_GENERATION,
    Player,
    PlayerSlot,
    PokemonOffer,
    RAW_SAME_GENERATION,
    Room,
    RoomError,
    FORWARD_TRANSFER_TO_GEN3,
    LEGACY_DOWNCONVERT_EXPERIMENTAL,
    SAME_GENERATION,
    TIME_CAPSULE_GEN1_GEN2,
    game_family_for_generation,
    generation_mismatch_message,
    now_utc,
    parse_client_id,
    parse_game_id,
    parse_generation,
    parse_room_name,
    parse_trade_mode,
    supported_trade_modes_for_generation,
    trade_mode_for_generations,
)
from .security import hash_room_password, verify_room_password


class RoomManager:
    def __init__(
        self,
        room_timeout_seconds: int | None = None,
        max_rooms: int | None = None,
        cross_generation_enabled: bool | None = False,
        enabled_trade_modes: Iterable[str] | None = None,
    ) -> None:
        self.room_timeout_seconds = room_timeout_seconds or int(os.getenv("ROOM_TIMEOUT_SECONDS", "900"))
        self.max_rooms = max_rooms or int(os.getenv("MAX_ROOMS", "200"))
        if cross_generation_enabled is None:
            cross_generation_enabled = os.getenv("ALLOW_CROSS_GENERATION", "false").strip().lower() == "true"
        self.cross_generation_enabled = bool(cross_generation_enabled)
        env_modes = os.getenv("ENABLED_TRADE_MODES", "")
        configured_modes = enabled_trade_modes if enabled_trade_modes is not None else [item for item in env_modes.split(",") if item.strip()]
        self.enabled_trade_modes = {
            parse_trade_mode(mode)
            for mode in configured_modes
            if parse_trade_mode(mode) != SAME_GENERATION
        }
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
        trade_mode: str | None = None,
        supported_trade_modes: list[str] | None = None,
        supported_protocols: list[str] | None = None,
    ) -> tuple[Room, PlayerSlot]:
        async with self._lock:
            room_name = parse_room_name(room_name)
            client_id = parse_client_id(client_id)
            generation = parse_generation(generation)
            game = parse_game_id(game, generation)
            # trade_mode is accepted only for legacy/debug clients. Room mode is
            # derived after both players join.
            requested_trade_mode = SAME_GENERATION
            creator_supported_modes = (
                supported_trade_modes if supported_trade_modes is not None else supported_trade_modes_for_generation(generation)
            )
            creator_supported_protocols = self._normalize_supported_protocols(
                supported_protocols,
                creator_supported_modes,
            )
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
                trade_mode=requested_trade_mode,
                compatibility_status={
                    "compatible": True,
                    "mode": requested_trade_mode,
                    "source_generation": generation,
                    "target_generation": generation,
                    "blocking_reasons": [],
                    "warnings": [],
                    "data_loss": [],
                    "suggested_actions": [],
                },
                expires_at=expires_at,
            )
            slot: PlayerSlot = "A"
            room.players[slot] = Player(
                slot=slot,
                client_id=client_id,
                generation=generation,
                game=game,
                supported_trade_modes=creator_supported_modes,
                supported_protocols=creator_supported_protocols,
            )
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
        supported_trade_modes: list[str] | None = None,
        supported_protocols: list[str] | None = None,
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
            peer_slot = "A" if "A" in room.players else "B"
            peer = room.players.get(peer_slot)
            entrant_supported_modes = (
                supported_trade_modes if supported_trade_modes is not None else supported_trade_modes_for_generation(generation)
            )
            if room.is_full():
                raise RoomError("room_full", "A sala ja possui dois jogadores.")
            entrant_supported_protocols = self._normalize_supported_protocols(
                supported_protocols,
                entrant_supported_modes,
            )
            slot: PlayerSlot = "A" if "A" not in room.players else "B"
            room.players[slot] = Player(
                slot=slot,
                client_id=client_id,
                generation=generation,
                game=game,
                supported_trade_modes=entrant_supported_modes,
                supported_protocols=entrant_supported_protocols,
            )
            try:
                self._derive_and_validate_room_modes_locked(room)
            except Exception:
                room.players.pop(slot, None)
                room.scrub_sensitive_data()
                self.client_rooms.pop(client_id, None)
                raise
            self.client_rooms[client_id] = (room_name, slot)
            return room, slot

    async def offer_pokemon(self, *, client_id: str, payload: dict) -> tuple[Room, PlayerSlot, PokemonOffer]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            offer = PokemonOffer.from_message(payload)
            player = room.players.get(slot)
            if player is None:
                raise RoomError("client_not_in_room", "Client nao esta ativo na sala.")
            if offer.generation != player.generation:
                raise RoomError("generation_mismatch", generation_mismatch_message(player.generation, offer.generation))
            peer_slot = room.peer_slot(slot)
            peer = room.players.get(peer_slot)
            if peer is None:
                raise RoomError("peer_missing", "Aguardando segundo jogador.")
            receiver_mode = room.derived_modes.get(peer_slot) or trade_mode_for_generations(player.generation, peer.generation)
            if receiver_mode == SAME_GENERATION and not offer.raw_data_base64:
                raise RoomError("invalid_payload", "Troca same-generation exige payload raw.")
            if receiver_mode != SAME_GENERATION and not offer.canonical:
                raise RoomError("invalid_payload", "Troca cross-generation exige payload canonico.")
            if receiver_mode != SAME_GENERATION:
                if not self._trade_mode_enabled(receiver_mode):
                    raise RoomError("trade_mode_disabled", f"O modo {receiver_mode} nao esta habilitado no servidor.")
                if CANONICAL_CROSS_GENERATION not in player.supported_protocols or CANONICAL_CROSS_GENERATION not in peer.supported_protocols:
                    raise RoomError("game_mismatch", "Este client nao anunciou suporte a troca canonical cross-generation.")
                if offer.target_generation is not None and offer.target_generation != peer.generation:
                    raise RoomError(
                        "generation_mismatch",
                        f"Payload mira Gen {offer.target_generation}, mas o outro jogador e Gen {peer.generation}.",
                    )
                canonical_generation = offer.canonical.get("source_generation") if offer.canonical else None
                if canonical_generation is not None and parse_generation(canonical_generation) != offer.generation:
                    raise RoomError("generation_mismatch", "Canonical source_generation nao bate com a geracao do jogador.")
            elif RAW_SAME_GENERATION not in player.supported_protocols or RAW_SAME_GENERATION not in peer.supported_protocols:
                raise RoomError("game_mismatch", "Este client nao anunciou suporte a troca raw same-generation.")
            room.offers[slot] = offer
            room.reset_preflight()
            return room, slot, offer

    async def confirm_trade(self, *, client_id: str) -> tuple[Room, PlayerSlot, bool]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            if not room.has_both_offers():
                raise RoomError("offers_missing", "Aguardando os dois jogadores enviarem seus Pokemon.")
            if not room.has_both_preflight_ok():
                raise RoomError("preflight_required", "Aguardando validacao preflight dos dois jogadores.")
            room.confirmations[slot] = True
            return room, slot, room.is_committed()

    async def submit_preflight_result(
        self,
        *,
        client_id: str,
        compatible: bool,
        report: dict,
        error: str = "",
    ) -> tuple[Room, PlayerSlot, bool, bool, dict[str, dict]]:
        async with self._lock:
            room, slot = self._room_for_client_locked(client_id)
            if not room.has_both_offers():
                raise RoomError("offers_missing", "Aguardando ofertas antes do preflight.")
            room.preflight_reports[slot] = dict(report or {})
            room.preflight_ok[slot] = bool(compatible)
            room.preflight_errors[slot] = str(error or "")
            room.confirmations[slot] = False
            blocked = not bool(compatible)
            ready = not blocked and room.has_both_preflight_ok()
            reports = {key: dict(value or {}) for key, value in room.preflight_reports.items()}
            if blocked:
                room.reset_trade_state("preflight_failed")
            return room, slot, blocked, ready, reports

    def preflight_requests(self, room: Room) -> dict[PlayerSlot, dict]:
        if not room.has_both_offers() or not room.is_ready():
            return {}
        requests: dict[PlayerSlot, dict] = {}
        for slot, player in room.players.items():
            peer_slot = room.peer_slot(slot)
            peer = room.players[peer_slot]
            peer_offer = room.offers[peer_slot]
            if peer_offer is None:
                continue
            requests[slot] = {
                "type": "preflight_required",
                "received_payload": peer_offer.to_public_dict(),
                "source_generation": peer.generation,
                "target_generation": player.generation,
                "derived_mode": room.derived_modes.get(slot, trade_mode_for_generations(peer.generation, player.generation)),
                "room": room.to_public_dict(),
            }
        return requests

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

    def _trade_mode_enabled(self, trade_mode: str) -> bool:
        trade_mode = parse_trade_mode(trade_mode)
        if trade_mode == SAME_GENERATION:
            return True
        return self.cross_generation_enabled and trade_mode in self.enabled_trade_modes

    def _normalize_supported_protocols(
        self,
        supported_protocols: list[str] | None,
        supported_trade_modes: list[str],
    ) -> list[str]:
        protocols = set(supported_protocols or [])
        protocols.add(RAW_SAME_GENERATION)
        if not supported_protocols and any(mode != SAME_GENERATION for mode in supported_trade_modes):
            protocols.add(CANONICAL_CROSS_GENERATION)
        return sorted(protocols)

    def _derive_and_validate_room_modes_locked(self, room: Room) -> None:
        if not room.is_ready():
            room.derived_modes = {}
            return
        player_a = room.players["A"]
        player_b = room.players["B"]
        mode_for_a = trade_mode_for_generations(player_b.generation, player_a.generation)
        mode_for_b = trade_mode_for_generations(player_a.generation, player_b.generation)
        if mode_for_a == "unsupported" or mode_for_b == "unsupported":
            raise RoomError("generation_mismatch", "Este par de geracoes nao e suportado.")
        room.derived_modes = {"A": mode_for_a, "B": mode_for_b}
        required_cross_modes = {mode for mode in room.derived_modes.values() if mode != SAME_GENERATION}
        if required_cross_modes:
            if not self.cross_generation_enabled:
                raise RoomError("generation_mismatch", "Este servidor nao habilitou troca entre geracoes.")
            missing = sorted(mode for mode in required_cross_modes if mode not in self.enabled_trade_modes)
            if missing:
                raise RoomError(
                    "trade_mode_disabled",
                    f"O modo necessario {_human_trade_mode(missing[0])} nao esta habilitado no servidor.",
            )
            for player in room.players.values():
                if CANONICAL_CROSS_GENERATION not in player.supported_protocols:
                    raise RoomError(
                        "game_mismatch",
                        "O client nao anunciou protocolo canonical_cross_generation. Atualize o client ou habilite cross-generation nas configuracoes.",
                    )
        else:
            for player in room.players.values():
                if RAW_SAME_GENERATION not in player.supported_protocols:
                    raise RoomError("game_mismatch", "Este client nao anunciou suporte a troca raw same-generation.")
        room.trade_mode = SAME_GENERATION if not required_cross_modes else sorted(required_cross_modes)[0]
        room.compatibility_status = {
            "compatible": True,
            "mode": room.trade_mode,
            "derived_modes": room.derived_modes,
            "source_generation": player_a.generation,
            "target_generation": player_b.generation,
            "blocking_reasons": [],
            "warnings": ["Modos derivados automaticamente por direcao."],
            "data_loss": [],
            "suggested_actions": [],
        }


def _human_trade_mode(trade_mode: str) -> str:
    labels = {
        SAME_GENERATION: "Same-generation",
        TIME_CAPSULE_GEN1_GEN2: "Time Capsule Gen 1/2",
        FORWARD_TRANSFER_TO_GEN3: "Transfer para Gen 3",
        LEGACY_DOWNCONVERT_EXPERIMENTAL: "Downconvert experimental Gen 3 -> Gen 1/2",
    }
    return labels.get(trade_mode, trade_mode)
