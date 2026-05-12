import asyncio
import logging
import os

from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from .cleanup import cleanup_loop
from .rooms import RoomManager
from .websocket import ConnectionHub
from .save_analyzer import analyze_save_file


def build_app() -> FastAPI:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    app = FastAPI(title="PokeCable Room", version="0.2.0")
    room_manager = RoomManager()
    hub = ConnectionHub(room_manager)
    app.state.room_manager = room_manager
    app.state.hub = hub

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/analyze-save")
    async def analyze_save(file: UploadFile = File(...)) -> dict:
        """
        Analyze a Pokemon save file and return pokemon list

        Request: POST /analyze-save with multipart/form-data containing 'file'
        Response: {
            "generation": int,
            "game": str,
            "pokemon": [{...}, ...],
            "party_count": int,
            "box_count": int
        }
        """
        try:
            # Validate file extension
            if not file.filename or not file.filename.lower().endswith(('.sav', '.srm')):
                raise HTTPException(status_code=400, detail="File must be .sav or .srm")

            # Read file
            contents = await file.read()
            if len(contents) == 0:
                raise HTTPException(status_code=400, detail="File is empty")

            # Analyze
            result = analyze_save_file(contents, file.filename)
            if result is None:
                raise HTTPException(status_code=422, detail="Could not analyze save file")

            return result

        except HTTPException:
            raise
        except Exception as e:
            logging.exception(f"Error analyzing save: {e}")
            raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

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
