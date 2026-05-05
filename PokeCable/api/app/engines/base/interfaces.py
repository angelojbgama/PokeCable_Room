from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class BattleEngineResult:
    battle_id: str
    logs: list[str] = field(default_factory=list)
    finished: bool = False
    requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    item_resolutions: dict[str, list[dict[str, Any]]] | None = None # { client_id: [{item_id, consumed}] }


@dataclass(slots=True)
class BattleEngineHealthStatus:
    status: str
    detail: str = ""


class BattleEngineAdapter(Protocol):
    async def create_battle(
        self,
        format_id: str,
        player_a_team: list[dict],
        player_b_team: list[dict],
        *,
        player_a_id: str | None = None,
        player_b_id: str | None = None,
    ) -> BattleEngineResult:
        ...

    async def send_action(self, battle_id: str, client_id: str, action: str) -> BattleEngineResult:
        ...

    async def get_logs(self, battle_id: str) -> list[str]:
        ...

    async def forfeit(self, battle_id: str, client_id: str) -> BattleEngineResult:
        ...

    async def ping(self) -> BattleEngineHealthStatus:
        ...

    async def close(self) -> None:
        ...
