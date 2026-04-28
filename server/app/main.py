from __future__ import annotations

import asyncio
import logging
import os

from fastapi import FastAPI, WebSocket

from .cleanup import cleanup_loop
from .rooms import RoomManager
from .websocket import ConnectionHub


def build_app() -> FastAPI:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    app = FastAPI(title="PokeCable Room", version="0.1.0")
    room_manager = RoomManager()
    hub = ConnectionHub(room_manager)
    app.state.room_manager = room_manager
    app.state.hub = hub

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.handle(websocket)

    @app.on_event("startup")
    async def startup() -> None:
        app.state.cleanup_task = asyncio.create_task(cleanup_loop(room_manager))

    @app.on_event("shutdown")
    async def shutdown() -> None:
        cleanup_task = getattr(app.state, "cleanup_task", None)
        if cleanup_task:
            cleanup_task.cancel()

    return app


app = build_app()

