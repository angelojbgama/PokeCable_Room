from __future__ import annotations

import asyncio
import logging
import os

from fastapi import FastAPI, WebSocket

from .cleanup import battle_cleanup_loop, cleanup_loop
from .battles import BattleManager
from .rooms import RoomManager
from .battle_engine import battle_engine_health_status, build_battle_engine, ensure_battle_engine_ready
from .websocket import ConnectionHub


def build_app() -> FastAPI:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    app = FastAPI(title="PokeCable Room", version="0.2.0")
    room_manager = RoomManager()
    battle_manager = BattleManager(adapter=build_battle_engine())
    hub = ConnectionHub(room_manager, battle_manager)
    app.state.room_manager = room_manager
    app.state.battle_manager = battle_manager
    app.state.hub = hub

    @app.get("/health")
    async def health() -> dict[str, str]:
        engine_status = await battle_engine_health_status(battle_manager.adapter)
        return {"status": "ok", "battle_engine": engine_status.status, "battle_engine_detail": engine_status.detail}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.handle(websocket)

    @app.on_event("startup")
    async def startup() -> None:
        await ensure_battle_engine_ready(battle_manager.adapter)
        app.state.cleanup_task = asyncio.create_task(cleanup_loop(room_manager))
        app.state.battle_cleanup_task = asyncio.create_task(battle_cleanup_loop(battle_manager))

    @app.on_event("shutdown")
    async def shutdown() -> None:
        cleanup_task = getattr(app.state, "cleanup_task", None)
        if cleanup_task:
            cleanup_task.cancel()
        battle_cleanup_task = getattr(app.state, "battle_cleanup_task", None)
        if battle_cleanup_task:
            battle_cleanup_task.cancel()
        await battle_manager.adapter.close()

    return app


app = build_app()
