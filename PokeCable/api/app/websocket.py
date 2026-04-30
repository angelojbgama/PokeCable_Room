from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .battles import BattleManager
from .models import PlayerSlot, Room, RoomError
from .rooms import RoomManager


logger = logging.getLogger("pokecable.websocket")


class ConnectionHub:
    def __init__(self, room_manager: RoomManager, battle_manager: BattleManager | None = None) -> None:
        self.room_manager = room_manager
        self.battle_manager = battle_manager or BattleManager()
        self.connections: dict[str, WebSocket] = {}
        self.room_clients: dict[str, dict[PlayerSlot, str]] = {}
        self.battle_clients: dict[str, dict[PlayerSlot, str]] = {}

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        client_id = str(uuid.uuid4())
        self.connections[client_id] = websocket
        await self._send(client_id, {"type": "connected", "client_id": client_id})
        try:
            while True:
                message = await websocket.receive_json()
                await self._handle_message(client_id, message)
        except WebSocketDisconnect:
            await self._disconnect(client_id)
        except Exception as exc:
            logger.exception("Unexpected websocket error for client_id=%s", client_id)
            await self._safe_send(client_id, {"type": "error", "code": "internal_error", "message": str(exc)})
            await self._disconnect(client_id)

    async def _handle_message(self, client_id: str, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        try:
            if message_type == "heartbeat":
                await self._send(client_id, {"type": "heartbeat", "status": "ok"})
            elif message_type == "create_room":
                await self._create_room(client_id, message)
            elif message_type == "join_room":
                await self._join_room(client_id, message)
            elif message_type == "offer_pokemon":
                await self._offer_pokemon(client_id, message)
            elif message_type == "preflight_result":
                await self._preflight_result(client_id, message)
            elif message_type == "confirm_trade":
                await self._confirm_trade(client_id)
            elif message_type == "write_ready":
                await self._write_ready(client_id, message)
            elif message_type == "write_done":
                await self._write_done(client_id, message)
            elif message_type == "write_failed":
                await self._write_failed(client_id, message)
            elif message_type == "cancel_trade_round":
                await self._cancel_trade_round(client_id, message)
            elif message_type == "update_player_context":
                await self._update_player_context(client_id, message)
            elif message_type == "cancel_trade":
                await self._cancel_trade(client_id, "cancelled")
            elif message_type == "create_battle_room":
                await self._create_battle_room(client_id, message)
            elif message_type == "join_battle_room":
                await self._join_battle_room(client_id, message)
            elif message_type == "offer_battle_team":
                await self._offer_battle_team(client_id, message)
            elif message_type == "confirm_battle":
                await self._confirm_battle(client_id)
            elif message_type == "battle_action":
                await self._battle_action(client_id, message)
            elif message_type == "battle_forfeit":
                await self._battle_forfeit(client_id)
            else:
                raise RoomError("unknown_message", f"Mensagem desconhecida: {message_type}")
        except RoomError as exc:
            error_type = exc.code if exc.code in {"generation_mismatch", "game_mismatch"} else "error"
            await self._send(client_id, {"type": error_type, "code": exc.code, "message": exc.message})

    async def _create_room(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot = await self.room_manager.create_room(
            room_name=message.get("room_name"),
            password=str(message.get("password") or ""),
            client_id=client_id,
            generation=message.get("generation"),
            game=message.get("game"),
            trade_mode=message.get("trade_mode"),
            supported_trade_modes=list(message.get("supported_trade_modes") or []),
            supported_protocols=list(message.get("supported_protocols") or []),
        )
        self._remember_client(room.room_name, slot, client_id)
        logger.info("room_created room=%s generation=%s trade_mode=%s slot=%s", room.room_name, room.generation, room.trade_mode, slot)
        await self._send(
            client_id,
            {
                "type": "room_created",
                "client_id": client_id,
                "slot": slot,
                "room": room.to_public_dict(),
            },
        )
        await self._send(client_id, {"type": "room_waiting", "message": "Aguardando segundo jogador."})

    async def _join_room(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot = await self.room_manager.join_room(
            room_name=message.get("room_name"),
            password=str(message.get("password") or ""),
            client_id=client_id,
            generation=message.get("generation"),
            game=message.get("game"),
            supported_trade_modes=list(message.get("supported_trade_modes") or []),
            supported_protocols=list(message.get("supported_protocols") or []),
        )
        self._remember_client(room.room_name, slot, client_id)
        logger.info("room_joined room=%s generation=%s trade_mode=%s slot=%s", room.room_name, room.generation, room.trade_mode, slot)
        await self._send(client_id, {"type": "room_joined", "client_id": client_id, "slot": slot, "room": room.to_public_dict()})
        peer_offer = room.offers.get(room.peer_slot(slot))
        if peer_offer is not None:
            await self._send(client_id, {"type": "peer_offer_received", "offer": peer_offer.to_public_dict()})
        await self._broadcast(room, {"type": "room_ready", "room": room.to_public_dict()})

    async def _offer_pokemon(self, client_id: str, message: dict[str, Any]) -> None:
        payload = message.get("payload")
        if not isinstance(payload, dict):
            raise RoomError("invalid_payload", "offer_pokemon precisa conter payload JSON.")
        room, slot, offer = await self.room_manager.offer_pokemon(client_id=client_id, payload=payload)
        logger.info("offer_received room=%s slot=%s offer=%s", room.room_name, slot, json.dumps(offer.log_summary()))
        await self._send(client_id, {"type": "offer_received", "slot": slot, "offer": offer.log_summary()})
        peer_slot = room.peer_slot(slot)
        peer_client_id = self.room_clients.get(room.room_name, {}).get(peer_slot)
        if peer_client_id:
            await self._send(peer_client_id, {"type": "peer_offer_received", "offer": offer.to_public_dict()})
        if room.has_both_offers():
            await self._broadcast(room, {"type": "offers_ready", "message": "Os dois Pokemon foram oferecidos."})
            await self._send_preflight_requests(room)

    async def _preflight_result(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot, blocked, ready, reports = await self.room_manager.submit_preflight_result(
            client_id=client_id,
            compatible=bool(message.get("compatible")),
            report=dict(message.get("report") or {}),
            error=str(message.get("error") or ""),
        )
        logger.info("preflight_result room=%s slot=%s compatible=%s blocked=%s ready=%s", room.room_name, slot, message.get("compatible"), blocked, ready)
        await self._send(client_id, {"type": "preflight_received", "slot": slot})
        if blocked:
            await self._broadcast(
                room,
                {
                    "type": "trade_blocked",
                    "message": "Troca bloqueada no preflight.",
                    "reports": reports,
                    "room": room.to_public_dict(),
                },
            )
        elif ready:
            await self._broadcast(room, {"type": "preflight_ready", "reports": reports, "room": room.to_public_dict()})

    async def _confirm_trade(self, client_id: str) -> None:
        room, slot, committed = await self.room_manager.confirm_trade(client_id=client_id)
        logger.info("trade_confirmed room=%s slot=%s committed=%s", room.room_name, slot, committed)
        await self._send(client_id, {"type": "trade_confirmed", "slot": slot})
        if committed:
            offers = {slot_name: offer.to_public_dict() for slot_name, offer in room.offers.items() if offer is not None}
            await self._send_prepare_write(room, offers)
        else:
            peer_slot = room.peer_slot(slot)
            peer_client_id = self.room_clients.get(room.room_name, {}).get(peer_slot)
            if peer_client_id:
                await self._send(peer_client_id, {"type": "peer_confirmed", "slot": slot})

    async def _send_prepare_write(self, room: Room, offers: dict[str, dict[str, Any]]) -> None:
        clients = self.room_clients.get(room.room_name, {})
        for slot, client_id in clients.items():
            peer_slot = room.peer_slot(slot)
            await self._send(
                client_id,
                {
                    "type": "prepare_write",
                    "received_payload": offers[peer_slot],
                    "sent_payload": offers[slot],
                    "message": "Troca confirmada pelos dois jogadores. Prepare o backup local antes da escrita.",
                    "room": room.to_public_dict(),
                },
            )

    async def _send_commit_write(self, room: Room, offers: dict[str, dict[str, Any]]) -> None:
        clients = self.room_clients.get(room.room_name, {})
        for slot, client_id in clients.items():
            peer_slot = room.peer_slot(slot)
            await self._send(
                client_id,
                {
                    "type": "trade_commit_write",
                    "received_payload": offers[peer_slot],
                    "sent_payload": offers[slot],
                    "message": "Os dois jogadores prepararam backup. Pode gravar o save local.",
                    "room": room.to_public_dict(),
                },
            )

    async def _write_ready(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot, blocked, ready = await self.room_manager.submit_write_ready(
            client_id=client_id,
            ready=bool(message.get("ready", True)),
            metadata=dict(message.get("metadata") or {}),
            error=str(message.get("error") or ""),
        )
        await self._send(client_id, {"type": "write_ready_received", "slot": slot})
        if blocked:
            error_message = room.write_errors.get(slot) or "Falha ao preparar backup/escrita local."
            await self._broadcast(
                room,
                {
                    "type": "trade_write_failed",
                    "stage": "prepare_write",
                    "slot": slot,
                    "message": error_message,
                    "error_code": str((room.write_metadata.get(slot) or {}).get("error_code") or room.write_errors.get(slot) or ""),
                    "error_metadata": self._safe_write_error_metadata(room, slot),
                    "room": room.to_public_dict(),
                },
            )
            await self.room_manager.reset_room_after_round(room.room_name, "prepare_write_failed")
            return
        if ready:
            offers = {slot_name: offer.to_public_dict() for slot_name, offer in room.offers.items() if offer is not None}
            await self._send_commit_write(room, offers)

    async def _write_done(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot, failed, completed = await self.room_manager.submit_write_done(
            client_id=client_id,
            success=bool(message.get("success", True)),
            error=str(message.get("error") or ""),
            metadata=dict(message.get("metadata") or {}),
        )
        await self._send(client_id, {"type": "write_done_received", "slot": slot})
        if failed:
            error_message = room.write_errors.get(slot) or "Falha ao gravar o save local."
            await self._broadcast(
                room,
                {
                    "type": "trade_write_failed",
                    "stage": "commit_write",
                    "slot": slot,
                    "message": error_message,
                    "error_code": str((room.write_metadata.get(slot) or {}).get("error_code") or room.write_errors.get(slot) or ""),
                    "error_metadata": self._safe_write_error_metadata(room, slot),
                    "room": room.to_public_dict(),
                },
            )
            await self.room_manager.reset_room_after_round(room.room_name, "commit_write_failed")
            return
        if completed:
            await self._broadcast(room, {"type": "trade_completed", "message": "Troca concluida e confirmada pelos dois jogadores.", "room": room.to_public_dict()})
            await self.room_manager.reset_room_after_round(room.room_name, "trade_completed")

    async def _write_failed(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot, _failed, _completed = await self.room_manager.submit_write_done(
            client_id=client_id,
            success=False,
            error=str(message.get("error") or "Falha local de escrita."),
            metadata=dict(message.get("metadata") or {}),
        )
        await self._broadcast(
            room,
            {
                "type": "trade_write_failed",
                "stage": str(message.get("stage") or "commit_write"),
                "slot": slot,
                "message": room.write_errors.get(slot) or "Falha local de escrita.",
                "error_code": str((room.write_metadata.get(slot) or {}).get("error_code") or message.get("error") or ""),
                "error_metadata": self._safe_write_error_metadata(room, slot),
                "room": room.to_public_dict(),
            },
        )
        await self.room_manager.reset_room_after_round(room.room_name, "write_failed")

    async def _send_preflight_requests(self, room: Room) -> None:
        requests = self.room_manager.preflight_requests(room)
        clients = self.room_clients.get(room.room_name, {})
        for slot, payload in requests.items():
            client_id = clients.get(slot)
            if client_id:
                await self._send(client_id, payload)

    async def _cancel_trade(self, client_id: str, reason: str) -> None:
        known = self.room_manager.client_rooms.get(client_id)
        room_name = known[0] if known else None
        room = await self.room_manager.cancel_room(client_id=client_id, reason=reason)
        if room_name:
            await self._broadcast_room_name(room_name, {"type": "trade_cancelled", "reason": reason})
            self.room_clients.pop(room_name, None)

    async def _cancel_trade_round(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot = await self.room_manager.cancel_trade_round(
            client_id=client_id,
            reason=str(message.get("reason") or "cancelled"),
        )
        await self._broadcast(
            room,
            {
                "type": "trade_round_cancelled",
                "slot": slot,
                "reason": str(message.get("reason") or "cancelled"),
                "room": room.to_public_dict(),
            },
        )

    async def _update_player_context(self, client_id: str, message: dict[str, Any]) -> None:
        generation = message.get("generation")
        game = message.get("game")
        supported_trade_modes = list(message.get("supported_trade_modes") or [])
        supported_protocols = list(message.get("supported_protocols") or [])
        trade_result = await self.room_manager.update_player_context(
            client_id=client_id,
            generation=generation,
            game=game,
            supported_trade_modes=supported_trade_modes,
            supported_protocols=supported_protocols,
        )
        battle_result = await self.battle_manager.update_player_context(
            client_id=client_id,
            generation=generation,
            game=game,
        )
        trade_room = trade_result[0] if trade_result else None
        trade_slot = trade_result[1] if trade_result else None
        battle_room = battle_result[0] if battle_result else None
        battle_slot = battle_result[1] if battle_result else None
        await self._send(
            client_id,
            {
                "type": "player_context_updated",
                "generation": generation,
                "game": game,
                "trade_room": trade_room.to_public_dict() if trade_room else None,
                "battle_room": battle_room.to_public_dict() if battle_room else None,
            },
        )
        if trade_room and trade_slot:
            await self._broadcast(
                trade_room,
                {
                    "type": "room_context_updated",
                    "slot": trade_slot,
                    "room": trade_room.to_public_dict(),
                },
            )
        if battle_room and battle_slot:
            await self._broadcast_battle(
                battle_room.room_name,
                {
                    "type": "battle_room_updated",
                    "slot": battle_slot,
                    "room": battle_room.to_public_dict(),
                },
            )

    async def _create_battle_room(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot = await self.battle_manager.create_room(
            room_name=message.get("room_name"),
            password=str(message.get("password") or ""),
            client_id=client_id,
            generation=message.get("generation"),
            game=message.get("game"),
            format_id=message.get("format_id"),
        )
        self._remember_battle_client(room.room_name, slot, client_id)
        await self._send(client_id, {"type": "battle_room_created", "client_id": client_id, "slot": slot, "room": room.to_public_dict()})
        await self._send(client_id, {"type": "battle_waiting", "message": "Aguardando segundo jogador para batalha."})

    async def _join_battle_room(self, client_id: str, message: dict[str, Any]) -> None:
        room, slot = await self.battle_manager.join_room(
            room_name=message.get("room_name"),
            password=str(message.get("password") or ""),
            client_id=client_id,
            generation=message.get("generation"),
            game=message.get("game"),
        )
        self._remember_battle_client(room.room_name, slot, client_id)
        await self._send(client_id, {"type": "battle_room_joined", "client_id": client_id, "slot": slot, "room": room.to_public_dict()})
        await self._broadcast_battle(room.room_name, {"type": "battle_room_ready", "room": room.to_public_dict()})

    async def _offer_battle_team(self, client_id: str, message: dict[str, Any]) -> None:
        team = message.get("team")
        if not isinstance(team, list):
            raise RoomError("invalid_team", "offer_battle_team precisa conter team JSON.")
        room, slot, ready = await self.battle_manager.offer_team(client_id=client_id, team=team)
        await self._send(client_id, {"type": "battle_team_received", "slot": slot, "team_size": len(team), "room": room.to_public_dict()})
        if ready:
            await self._broadcast_battle(room.room_name, {"type": "battle_ready", "room": room.to_public_dict()})

    async def _confirm_battle(self, client_id: str) -> None:
        room, slot, started, result = await self.battle_manager.confirm_battle(client_id=client_id)
        await self._send(client_id, {"type": "battle_confirmed", "slot": slot})
        if started:
            await self._broadcast_battle(
                room.room_name,
                {
                    "type": "battle_started",
                    "battle_id": room.battle_id,
                    "logs": result.logs,
                    "room": room.to_public_dict(),
                },
            )
            await self._send_battle_action_requests(room.room_name, room.battle_id, result.requests)

    async def _battle_action(self, client_id: str, message: dict[str, Any]) -> None:
        room, _slot, result = await self.battle_manager.send_action(client_id=client_id, action=str(message.get("action") or "pass"))
        await self._broadcast_battle(room.room_name, {"type": "battle_log", "battle_id": room.battle_id, "logs": result.logs})
        if result.finished:
            await self._broadcast_battle(room.room_name, {"type": "battle_finished", "battle_id": room.battle_id, "logs": result.logs})
        else:
            await self._send_battle_action_requests(room.room_name, room.battle_id, result.requests)

    async def _battle_forfeit(self, client_id: str) -> None:
        room, _slot, result = await self.battle_manager.forfeit(client_id=client_id)
        await self._broadcast_battle(room.room_name, {"type": "battle_log", "battle_id": room.battle_id, "logs": result.logs})
        await self._broadcast_battle(room.room_name, {"type": "battle_finished", "battle_id": room.battle_id, "logs": result.logs})

    async def _disconnect(self, client_id: str) -> None:
        self.connections.pop(client_id, None)
        known = self.room_manager.client_rooms.get(client_id)
        room_name = known[0] if known else None
        slot = known[1] if known else None
        room = await self.room_manager.disconnect(client_id)
        if room_name:
            clients = self.room_clients.get(room_name, {})
            if slot:
                clients.pop(slot, None)
            if room is None or not clients:
                self.room_clients.pop(room_name, None)
            else:
                await self._broadcast_room_name(room_name, {"type": "trade_cancelled", "reason": "peer_disconnected"})
                await self._broadcast_room_name(room_name, {"type": "room_waiting", "message": "Outro usuario desconectou. A sala continua aguardando."})
        battle_known = self.battle_manager.client_rooms.get(client_id)
        battle_room_name = battle_known[0] if battle_known else None
        battle_slot = battle_known[1] if battle_known else None
        battle_room = await self.battle_manager.disconnect(client_id)
        if battle_room_name:
            battle_clients = self.battle_clients.get(battle_room_name, {})
            if battle_slot:
                battle_clients.pop(battle_slot, None)
            if battle_room is None or not battle_clients:
                self.battle_clients.pop(battle_room_name, None)
            else:
                await self._broadcast_battle(battle_room_name, {"type": "battle_finished", "reason": "peer_disconnected"})
        logger.info("client_disconnected client_id=%s room=%s", client_id, room_name)

    def _remember_client(self, room_name: str, slot: PlayerSlot, client_id: str) -> None:
        self.room_clients.setdefault(room_name, {})[slot] = client_id

    def _remember_battle_client(self, room_name: str, slot: PlayerSlot, client_id: str) -> None:
        self.battle_clients.setdefault(room_name, {})[slot] = client_id

    def _safe_write_error_metadata(self, room: Room, slot: PlayerSlot) -> dict[str, Any]:
        metadata = dict(room.write_metadata.get(slot) or {})
        allowed = {
            "error_code",
            "message",
            "expected_signature",
            "current_signature",
            "save_signature_before_write",
            "save_signature_after_write",
            "write_result",
            "timestamp_before_write",
            "timestamp_after_write",
            "rollback_ok",
        }
        return {key: metadata[key] for key in allowed if key in metadata}

    async def _send_battle_action_requests(self, room_name: str, battle_id: str | None, requests: dict[str, dict[str, Any]]) -> None:
        if not battle_id:
            return
        room = self.battle_manager.rooms.get(room_name)
        if room is None:
            return
        clients = self.battle_clients.get(room_name, {})
        for slot, client_id in clients.items():
            request_payload = dict(requests.get(client_id) or {})
            if not request_payload:
                continue
            await self._send(
                client_id,
                {
                    "type": "battle_request_action",
                    "battle_id": battle_id,
                    "request": request_payload,
                    "slot": slot,
                },
            )

    async def _broadcast(self, room: Room, payload: dict[str, Any]) -> None:
        await self._broadcast_room_name(room.room_name, payload)

    async def _broadcast_room_name(self, room_name: str, payload: dict[str, Any]) -> None:
        tasks = [self._safe_send(client_id, payload) for client_id in self.room_clients.get(room_name, {}).values()]
        if tasks:
            await asyncio.gather(*tasks)

    async def _broadcast_battle(self, room_name: str, payload: dict[str, Any]) -> None:
        tasks = [self._safe_send(client_id, payload) for client_id in self.battle_clients.get(room_name, {}).values()]
        if tasks:
            await asyncio.gather(*tasks)

    async def _send(self, client_id: str, payload: dict[str, Any]) -> None:
        websocket = self.connections.get(client_id)
        if websocket is None:
            return
        await websocket.send_json(payload)

    async def _safe_send(self, client_id: str, payload: dict[str, Any]) -> None:
        try:
            await self._send(client_id, payload)
        except Exception:
            logger.debug("Failed to send websocket payload to client_id=%s", client_id, exc_info=True)
