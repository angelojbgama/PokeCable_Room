from __future__ import annotations

import asyncio
import logging

from .battles import BattleManager
from .rooms import RoomManager


logger = logging.getLogger("pokecable.cleanup")


async def cleanup_loop(room_manager: RoomManager, interval_seconds: int = 30) -> None:
    while True:
        expired = await room_manager.cleanup_expired()
        for room_name in expired:
            logger.info("room_expired room=%s", room_name)
        await asyncio.sleep(interval_seconds)


async def battle_cleanup_loop(battle_manager: BattleManager, interval_seconds: int = 30) -> None:
    while True:
        expired = await battle_manager.cleanup_expired()
        for room_name in expired:
            logger.info("battle_room_expired room=%s", room_name)
        await asyncio.sleep(interval_seconds)
