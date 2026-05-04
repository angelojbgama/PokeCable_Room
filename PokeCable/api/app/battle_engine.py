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


from .battle_engine_core import CustomBattleEngine, BattleSide
from .battle_pokemon import BattlePokemon

class CustomBattleEngineAdapter:
    """Adapter that bridges BattleManager to our hardcore CustomBattleEngine."""

    def __init__(self) -> None:
        self._battles: dict[str, CustomBattleEngine] = {}

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
        
        # Converte times raw para BattlePokemon
        team_a = [BattlePokemon.from_canonical(p) for p in player_a_team]
        team_b = [BattlePokemon.from_canonical(p) for p in player_b_team]
        
        side_a = BattleSide(player_id=str(player_a_id or "A"), player_name="Jogador A", team=team_a)
        side_b = BattleSide(player_id=str(player_b_id or "B"), player_name="Jogador B", team=team_b)
        
        engine = CustomBattleEngine(battle_id, side_a, side_b)
        engine.start_battle()
        
        self._battles[battle_id] = engine
        
        return BattleEngineResult(
            battle_id=battle_id,
            logs=engine.logs[:],
            finished=False,
            requests={
                side_a.player_id: engine.generate_request(side_a.player_id),
                side_b.player_id: engine.generate_request(side_b.player_id),
            },
        )

    async def send_action(self, battle_id: str, client_id: str, action: str) -> BattleEngineResult:
        engine = self._require_battle(battle_id)
        if engine.finished:
            return BattleEngineResult(battle_id=battle_id, logs=[], finished=True)
            
        cmd = action.strip().lower().split()
        if not cmd:
            return BattleEngineResult(battle_id=battle_id, logs=[], finished=False)
            
        parsed_action = {}
        if cmd[0] == "move":
            parsed_action = {"type": "move", "move_index": int(cmd[1]) - 1}
        elif cmd[0] == "switch":
            parsed_action = {"type": "switch", "index": int(cmd[1]) - 1}
        else:
            parsed_action = {"type": "pass"}

        # Limpa logs anteriores da engine para coletar apenas o novo turno
        engine.logs = []
        # Envia acao para a engine
        engine.submit_action(client_id, parsed_action)

        item_resolutions = None
        if engine.finished:
            item_resolutions = self._collect_item_resolutions(engine)

        return BattleEngineResult(
            battle_id=battle_id,
            logs=engine.logs[:],
            finished=engine.finished,
            requests={
                engine.sides["p1"].player_id: engine.generate_request(engine.sides["p1"].player_id),
                engine.sides["p2"].player_id: engine.generate_request(engine.sides["p2"].player_id),
            } if not engine.finished else {},
            item_resolutions=item_resolutions,
        )

    async def get_logs(self, battle_id: str) -> list[str]:
        return list(self._require_battle(battle_id).logs)

    async def forfeit(self, battle_id: str, client_id: str) -> BattleEngineResult:
        engine = self._require_battle(battle_id)
        engine.add_log(f"|forfeit|{client_id}")
        engine.add_log(f"|win|oponente de {client_id}")
        engine.finished = True
        return BattleEngineResult(
            battle_id=battle_id, 
            logs=engine.logs, 
            finished=True, 
            requests={},
            item_resolutions=self._collect_item_resolutions(engine)
        )

    def _collect_item_resolutions(self, engine: CustomBattleEngine) -> dict[str, list[dict[str, Any]]]:
        resolutions = {}
        for side in engine.sides.values():
            player_id = side.player_id
            items = []
            for pkmn in side.team:
                if pkmn.held_item_id:
                    items.append({
                        "item_id": pkmn.held_item_id,
                        "consumed": pkmn.consumed_item
                    })
            resolutions[player_id] = items
        return resolutions

    async def ping(self) -> BattleEngineHealthStatus:
        return BattleEngineHealthStatus(status="custom_hardcore_engine")

    async def close(self) -> None:
        return None

    def _require_battle(self, battle_id: str) -> CustomBattleEngine:
        try:
            return self._battles[battle_id]
        except KeyError as exc:
            raise ValueError("Batalha nao encontrada na engine custom.") from exc

def build_battle_engine() -> BattleEngineAdapter:
    return CustomBattleEngineAdapter()


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
