from __future__ import annotations

import asyncio
import json
import os
import shlex
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib import request as urlrequest
from urllib.parse import urlencode


@dataclass(slots=True)
class ShowdownBattleResult:
    battle_id: str
    logs: list[str] = field(default_factory=list)
    finished: bool = False


class ShowdownAdapter(Protocol):
    async def create_battle(
        self,
        format_id: str,
        player_a_team: list[dict],
        player_b_team: list[dict],
        *,
        player_a_id: str | None = None,
        player_b_id: str | None = None,
    ) -> ShowdownBattleResult:
        ...

    async def send_action(self, battle_id: str, client_id: str, action: str) -> ShowdownBattleResult:
        ...

    async def get_logs(self, battle_id: str) -> list[str]:
        ...

    async def forfeit(self, battle_id: str, client_id: str) -> ShowdownBattleResult:
        ...


class LocalShowdownAdapter:
    """Small deterministic adapter used when a real Pokemon Showdown process is not configured."""

    def __init__(self) -> None:
        self._battles: dict[str, dict] = {}

    async def create_battle(
        self,
        format_id: str,
        player_a_team: list[dict],
        player_b_team: list[dict],
        *,
        player_a_id: str | None = None,
        player_b_id: str | None = None,
    ) -> ShowdownBattleResult:
        battle_id = f"battle-{uuid.uuid4().hex[:12]}"
        logs = [
            f"|init|battle",
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
        }
        return ShowdownBattleResult(battle_id=battle_id, logs=logs, finished=False)

    async def send_action(self, battle_id: str, client_id: str, action: str) -> ShowdownBattleResult:
        battle = self._require_battle(battle_id)
        if battle["finished"]:
            return ShowdownBattleResult(battle_id=battle_id, logs=[], finished=True)
        clean_action = " ".join(str(action or "").strip().split()) or "pass"
        logs = [f"|turn|{battle['turn']}", f"|choice|{client_id}|{clean_action}"]
        battle["turn"] += 1
        if clean_action.lower() in {"forfeit", "ff", "desistir"}:
            logs.append(f"|win|opponent of {client_id}")
            battle["finished"] = True
        battle["logs"].extend(logs)
        return ShowdownBattleResult(battle_id=battle_id, logs=logs, finished=bool(battle["finished"]))

    async def get_logs(self, battle_id: str) -> list[str]:
        return list(self._require_battle(battle_id)["logs"])

    async def forfeit(self, battle_id: str, client_id: str) -> ShowdownBattleResult:
        battle = self._require_battle(battle_id)
        if battle["finished"]:
            return ShowdownBattleResult(battle_id=battle_id, logs=[], finished=True)
        logs = [f"|forfeit|{client_id}", f"|win|opponent of {client_id}"]
        battle["finished"] = True
        battle["logs"].extend(logs)
        return ShowdownBattleResult(battle_id=battle_id, logs=logs, finished=True)

    def _require_battle(self, battle_id: str) -> dict:
        try:
            return self._battles[battle_id]
        except KeyError as exc:
            raise ValueError("Batalha nao encontrada no adapter Showdown.") from exc


class ProcessShowdownAdapter(LocalShowdownAdapter):
    """Optional bridge for a persistent local Node/Pokemon Showdown worker.

    The worker speaks JSON-lines: one request per line on stdin and one response
    per line on stdout. If it is unavailable or returns an error, this adapter
    mirrors enough state into LocalShowdownAdapter to keep rooms usable instead
    of blocking FastAPI startup.
    """

    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command
        self._process: asyncio.subprocess.Process | None = None
        self._process_lock = asyncio.Lock()
        self._timeout_seconds = float(os.getenv("SHOWDOWN_PROCESS_TIMEOUT_SECONDS", "20"))

    async def create_battle(
        self,
        format_id: str,
        player_a_team: list[dict],
        player_b_team: list[dict],
        *,
        player_a_id: str | None = None,
        player_b_id: str | None = None,
    ) -> ShowdownBattleResult:
        request = {
            "type": "create_battle",
            "format_id": format_id,
            "player_a_team": player_a_team,
            "player_b_team": player_b_team,
            "player_a_id": player_a_id,
            "player_b_id": player_b_id,
        }
        response = await self._request_worker(request)
        if response:
            result = ShowdownBattleResult(
                battle_id=str(response.get("battle_id") or f"battle-{uuid.uuid4().hex[:12]}"),
                logs=[str(item) for item in response.get("logs") or []],
                finished=bool(response.get("finished")),
            )
            self._mirror_result(result, player_a_id=player_a_id, player_b_id=player_b_id)
            return result
        return await super().create_battle(
            format_id,
            player_a_team,
            player_b_team,
            player_a_id=player_a_id,
            player_b_id=player_b_id,
        )

    async def send_action(self, battle_id: str, client_id: str, action: str) -> ShowdownBattleResult:
        response = await self._request_worker(
            {"type": "battle_action", "battle_id": battle_id, "client_id": client_id, "action": action}
        )
        if response:
            result = ShowdownBattleResult(
                battle_id=battle_id,
                logs=[str(item) for item in response.get("logs") or []],
                finished=bool(response.get("finished")),
            )
            self._mirror_result(result)
            return result
        return await self._local_or_finished_error(battle_id, client_id, action)

    async def get_logs(self, battle_id: str) -> list[str]:
        response = await self._request_worker({"type": "get_logs", "battle_id": battle_id})
        if response:
            logs = [str(item) for item in response.get("logs") or []]
            battle = self._battles.get(battle_id)
            if battle is not None:
                battle["logs"] = logs[:]
            return logs
        return await super().get_logs(battle_id)

    async def forfeit(self, battle_id: str, client_id: str) -> ShowdownBattleResult:
        response = await self._request_worker({"type": "battle_forfeit", "battle_id": battle_id, "client_id": client_id})
        if response:
            result = ShowdownBattleResult(
                battle_id=battle_id,
                logs=[str(item) for item in response.get("logs") or []],
                finished=True,
            )
            self._mirror_result(result)
            return result
        return await super().forfeit(battle_id, client_id)

    async def _request_worker(self, request: dict[str, Any]) -> dict[str, Any] | None:
        if not self.command:
            return None
        async with self._process_lock:
            process = await self._ensure_process_locked()
            if process is None or process.stdin is None or process.stdout is None:
                return None
            request_id = uuid.uuid4().hex
            payload = dict(request)
            payload["request_id"] = request_id
            try:
                process.stdin.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
                await asyncio.wait_for(process.stdin.drain(), timeout=self._timeout_seconds)
                line = await asyncio.wait_for(process.stdout.readline(), timeout=self._timeout_seconds)
                if not line:
                    await self._stop_process_locked()
                    return None
                response = json.loads(line.decode("utf-8"))
                if response.get("request_id") != request_id or response.get("ok") is False:
                    return None
                return response
            except Exception:
                await self._stop_process_locked()
                return None

    async def _ensure_process_locked(self) -> asyncio.subprocess.Process | None:
        if self._process is not None and self._process.returncode is None:
            return self._process
        args = shlex.split(self.command)
        if not args:
            return None
        try:
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return self._process
        except Exception:
            self._process = None
            return None

    async def _stop_process_locked(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except Exception:
            process.kill()
            try:
                await process.wait()
            except Exception:
                pass

    def _mirror_result(self, result: ShowdownBattleResult, *, player_a_id: str | None = None, player_b_id: str | None = None) -> None:
        battle = self._battles.setdefault(
            result.battle_id,
            {"logs": [], "finished": False, "turn": 1, "player_ids": {"p1": player_a_id, "p2": player_b_id}},
        )
        battle["logs"].extend(result.logs)
        battle["finished"] = result.finished

    async def _local_or_finished_error(self, battle_id: str, client_id: str, action: str) -> ShowdownBattleResult:
        try:
            return await super().send_action(battle_id, client_id, action)
        except ValueError:
            logs = ["|error|Pokemon Showdown worker indisponivel; batalha encerrada pelo servidor."]
            return ShowdownBattleResult(battle_id=battle_id, logs=logs, finished=True)


class HttpShowdownAdapter(LocalShowdownAdapter):
    """Optional HTTP bridge for deployments that run Showdown as a separate service."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")

    async def create_battle(
        self,
        format_id: str,
        player_a_team: list[dict],
        player_b_team: list[dict],
        *,
        player_a_id: str | None = None,
        player_b_id: str | None = None,
    ) -> ShowdownBattleResult:
        response = await self._post(
            "/create_battle",
            {
                "format_id": format_id,
                "player_a_team": player_a_team,
                "player_b_team": player_b_team,
                "player_a_id": player_a_id,
                "player_b_id": player_b_id,
            },
        )
        if response:
            return ShowdownBattleResult(
                battle_id=str(response.get("battle_id") or f"battle-{uuid.uuid4().hex[:12]}"),
                logs=[str(item) for item in response.get("logs") or []],
                finished=bool(response.get("finished")),
            )
        return await super().create_battle(
            format_id,
            player_a_team,
            player_b_team,
            player_a_id=player_a_id,
            player_b_id=player_b_id,
        )

    async def send_action(self, battle_id: str, client_id: str, action: str) -> ShowdownBattleResult:
        response = await self._post("/battle_action", {"battle_id": battle_id, "client_id": client_id, "action": action})
        if response:
            return ShowdownBattleResult(
                battle_id=battle_id,
                logs=[str(item) for item in response.get("logs") or []],
                finished=bool(response.get("finished")),
            )
        return await super().send_action(battle_id, client_id, action)

    async def get_logs(self, battle_id: str) -> list[str]:
        response = await self._get(f"/logs?{urlencode({'battle_id': battle_id})}")
        if response:
            return [str(item) for item in response.get("logs") or []]
        return await super().get_logs(battle_id)

    async def forfeit(self, battle_id: str, client_id: str) -> ShowdownBattleResult:
        response = await self._post("/forfeit", {"battle_id": battle_id, "client_id": client_id})
        if response:
            return ShowdownBattleResult(
                battle_id=battle_id,
                logs=[str(item) for item in response.get("logs") or []],
                finished=True,
            )
        return await super().forfeit(battle_id, client_id)

    async def _post(self, path: str, payload: dict) -> dict | None:
        return await asyncio.to_thread(self._request, path, payload)

    async def _get(self, path: str) -> dict | None:
        return await asyncio.to_thread(self._request, path, None)

    def _request(self, path: str, payload: dict | None) -> dict | None:
        try:
            data = None if payload is None else json.dumps(payload).encode("utf-8")
            request = urlrequest.Request(
                f"{self.base_url}{path}",
                data=data,
                headers={"Content-Type": "application/json"},
                method="GET" if payload is None else "POST",
            )
            with urlrequest.urlopen(request, timeout=20) as response:  # nosec: configured deployment URL
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None


def build_showdown_adapter() -> ShowdownAdapter:
    if os.getenv("SHOWDOWN_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
        return LocalShowdownAdapter()
    server_url = os.getenv("SHOWDOWN_SERVER_URL", "").strip()
    if server_url:
        return HttpShowdownAdapter(server_url)
    command = os.getenv("SHOWDOWN_PROCESS_CMD", "").strip()
    if command:
        return ProcessShowdownAdapter(command)
    return LocalShowdownAdapter()


def _team_label(team: list[dict]) -> str:
    names = []
    for pokemon in team[:6]:
        species = dict(pokemon.get("species") or {})
        names.append(str(species.get("name") or pokemon.get("species_name") or "Pokemon"))
    return ", ".join(names) if names else "empty team"
