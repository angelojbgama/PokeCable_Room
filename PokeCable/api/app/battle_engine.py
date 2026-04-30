from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class BattleEngineResult:
    battle_id: str
    logs: list[str] = field(default_factory=list)
    finished: bool = False
    requests: dict[str, dict[str, Any]] = field(default_factory=dict)


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


class LocalBattleEngineAdapter:
    """Deterministic in-process battle adapter while the custom engine is built."""

    def __init__(self) -> None:
        self._battles: dict[str, dict[str, Any]] = {}

    async def create_battle(
        self,
        format_id: str,
        player_a_team: list[dict],
        player_b_team: list[dict],
        *,
        player_a_id: str | None = None,
        player_b_id: str | None = None,
    ) -> BattleEngineResult:
        battle_id = f"battle-{uuid.uuid4().hex[:12]}"
        logs = [
            "|init|battle",
            f"|title|PokeCable Room {format_id}",
            f"|poke|p1|{_team_label(player_a_team)}",
            f"|poke|p2|{_team_label(player_b_team)}",
            "|start|",
        ]
        self._battles[battle_id] = {
            "logs": logs[:],
            "finished": False,
            "turn": 1,
            "player_ids": {"p1": player_a_id, "p2": player_b_id},
            "requests": {
                str(player_a_id or "A"): {"active": [{"moves": [{"move": "Tackle", "id": "tackle", "pp": 35, "maxpp": 35, "disabled": False}]}]},
                str(player_b_id or "B"): {"active": [{"moves": [{"move": "Tackle", "id": "tackle", "pp": 35, "maxpp": 35, "disabled": False}]}]},
            },
        }
        return BattleEngineResult(
            battle_id=battle_id,
            logs=logs,
            finished=False,
            requests=dict(self._battles[battle_id]["requests"]),
        )

    async def send_action(self, battle_id: str, client_id: str, action: str) -> BattleEngineResult:
        battle = self._require_battle(battle_id)
        if battle["finished"]:
            return BattleEngineResult(battle_id=battle_id, logs=[], finished=True)
        clean_action = " ".join(str(action or "").strip().split()) or "pass"
        logs = [f"|turn|{battle['turn']}", f"|choice|{client_id}|{clean_action}"]
        battle["turn"] += 1
        if clean_action.lower() in {"forfeit", "ff", "desistir"}:
            logs.append(f"|win|opponent of {client_id}")
            battle["finished"] = True
            battle["requests"] = {}
        battle["logs"].extend(logs)
        return BattleEngineResult(
            battle_id=battle_id,
            logs=logs,
            finished=bool(battle["finished"]),
            requests={} if battle["finished"] else dict(battle["requests"]),
        )

    async def get_logs(self, battle_id: str) -> list[str]:
        return list(self._require_battle(battle_id)["logs"])

    async def forfeit(self, battle_id: str, client_id: str) -> BattleEngineResult:
        battle = self._require_battle(battle_id)
        if battle["finished"]:
            return BattleEngineResult(battle_id=battle_id, logs=[], finished=True)
        logs = [f"|forfeit|{client_id}", f"|win|opponent of {client_id}"]
        battle["finished"] = True
        battle["requests"] = {}
        battle["logs"].extend(logs)
        return BattleEngineResult(battle_id=battle_id, logs=logs, finished=True, requests={})

    async def ping(self) -> BattleEngineHealthStatus:
        return BattleEngineHealthStatus(status="local_engine")

    async def close(self) -> None:
        return None

    def _require_battle(self, battle_id: str) -> dict[str, Any]:
        try:
            return self._battles[battle_id]
        except KeyError as exc:
            raise ValueError("Batalha nao encontrada no adapter local.") from exc


def build_battle_engine() -> BattleEngineAdapter:
    return LocalBattleEngineAdapter()


async def battle_engine_health_status(adapter: BattleEngineAdapter) -> BattleEngineHealthStatus:
    try:
        return await adapter.ping()
    except Exception as exc:
        return BattleEngineHealthStatus(status="unavailable", detail=str(exc))


async def ensure_battle_engine_ready(adapter: BattleEngineAdapter) -> None:
    del adapter
    return None


def _team_label(team: list[dict[str, Any]]) -> str:
    if not team:
        return "MissingNo."
    leader = team[0]
    species = leader.get("species_name") or leader.get("species", {}).get("name") or "Pokemon"
    level = int(leader.get("level") or 1)
    return f"{species}, L{level}"
