from __future__ import annotations

import uuid
import logging
from typing import Any

from .engines.base.interfaces import (
    BattleEngineResult,
    BattleEngineHealthStatus,
    BattleEngineAdapter,
)

logger = logging.getLogger(__name__)


def _generation_from_format_id(format_id: str) -> int:
    format_lower = str(format_id or "").strip().lower()
    if format_lower.startswith("gen1"):
        return 1
    if format_lower.startswith("gen2"):
        return 2
    if format_lower.startswith("gen3"):
        return 3
    raise ValueError(f"Formato de batalha nao suportado: {format_id}.")


def _team_generation(team: list[dict[str, Any]]) -> int | None:
    generations: set[int] = set()
    for member in team:
        if not isinstance(member, dict):
            continue
        source_generation = member.get("source_generation")
        if source_generation is None:
            source_generation = member.get("generation")
        if source_generation is None:
            continue
        generations.add(int(source_generation))

    if len(generations) > 1:
        raise ValueError("Times de batalha nao podem misturar geracoes.")
    return next(iter(generations)) if generations else None


def _ensure_team_generation(team: list[dict[str, Any]], expected_generation: int) -> None:
    team_generation = _team_generation(team)
    if team_generation is not None and team_generation != expected_generation:
        raise ValueError(
            f"Time de batalha da Gen {team_generation} nao pode batalhar em formato Gen {expected_generation}."
        )


class BattleEngineRouter(BattleEngineAdapter):
    """Router that dispatches actions to the correct generation engine."""

    def __init__(self) -> None:
        self._battles: dict[str, Any] = {} # Armazena as engines reais
        self._battle_formats: dict[str, int] = {} # mapeia battle_id -> generation

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
        
        generation = _generation_from_format_id(format_id)

        _ensure_team_generation(player_a_team, generation)
        _ensure_team_generation(player_b_team, generation)
        self._battle_formats[battle_id] = generation
        
        if generation == 3:
            from .engines.gen3.battle_engine_core import CustomBattleEngine, BattleSide
            from .engines.gen3.battle_pokemon import BattlePokemon

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
        elif generation == 2:
            from .engines.gen2.engine import BattleEngineGen2, BattleSideGen2
            from .engines.gen2.models import PokemonGen2

            team_a = [PokemonGen2.from_canonical(p) for p in player_a_team]
            team_b = [PokemonGen2.from_canonical(p) for p in player_b_team]

            side_a = BattleSideGen2(player_id=str(player_a_id or "A"), player_name="Jogador A", team=team_a)
            side_b = BattleSideGen2(player_id=str(player_b_id or "B"), player_name="Jogador B", team=team_b)

            engine = BattleEngineGen2(battle_id, side_a, side_b)
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
        elif generation == 1:
            from .engines.gen1.engine import BattleEngineGen1, BattleSideGen1
            from .engines.gen1.models import PokemonGen1

            team_a = [PokemonGen1.from_canonical(p) for p in player_a_team]
            team_b = [PokemonGen1.from_canonical(p) for p in player_b_team]
            
            side_a = BattleSideGen1(player_id=str(player_a_id or "A"), player_name="Jogador A", team=team_a)
            side_b = BattleSideGen1(player_id=str(player_b_id or "B"), player_name="Jogador B", team=team_b)
            
            engine = BattleEngineGen1(battle_id, side_a, side_b)
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
        else:
            raise ValueError(f"Geração {generation} não suportada.")

    async def send_action(self, battle_id: str, client_id: str, action: str) -> BattleEngineResult:
        generation = self._battle_formats.get(battle_id)
        engine = self._battles.get(battle_id)
        
        if not engine:
            raise ValueError("Batalha não encontrada.")

        if generation in {1, 2, 3}:
            if engine.finished:
                return BattleEngineResult(battle_id=battle_id, logs=[], finished=True)
                
            cmd = action.strip().lower().split()
            if not cmd:
                return BattleEngineResult(battle_id=battle_id, logs=[], finished=False)

            engine.logs = []
            engine.add_log(f"|choice|{client_id}|{action}")
            parsed_action = {}
            if cmd[0] == "move":
                parsed_action = {"type": "move", "move_index": int(cmd[1]) - 1}
            elif cmd[0] == "switch":
                parsed_action = {"type": "switch", "index": int(cmd[1]) - 1}
            else:
                parsed_action = {"type": "pass"}

            engine.submit_action(client_id, parsed_action)

            item_resolutions = None
            if generation == 3 and engine.finished:
                item_resolutions = self._collect_item_resolutions_gen3(engine)

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
        
        raise NotImplementedError(f"Ação para geração {generation} não implementada.")

    async def get_logs(self, battle_id: str) -> list[str]:
        engine = self._battles.get(battle_id)
        if not engine: return []
        return list(engine.logs)

    async def forfeit(self, battle_id: str, client_id: str) -> BattleEngineResult:
        engine = self._battles.get(battle_id)
        if not engine:
            return BattleEngineResult(battle_id=battle_id, logs=[], finished=True)
            
        engine.add_log(f"|forfeit|{client_id}")
        engine.add_log(f"|win|oponente de {client_id}")
        engine.finished = True
        
        item_resolutions = None
        if self._battle_formats.get(battle_id) == 3:
            item_resolutions = self._collect_item_resolutions_gen3(engine)
            
        return BattleEngineResult(
            battle_id=battle_id, 
            logs=engine.logs, 
            finished=True, 
            requests={},
            item_resolutions=item_resolutions
        )

    def _collect_item_resolutions_gen3(self, engine: Any) -> dict[str, list[dict[str, Any]]]:
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
        return BattleEngineHealthStatus(status="router", detail="Gen 1, Gen 2 e Gen 3 locais")

    async def close(self) -> None:
        return None


class LocalBattleEngineAdapter(BattleEngineRouter):
    async def ping(self) -> BattleEngineHealthStatus:
        return BattleEngineHealthStatus(status="local_engine", detail="Battle engine local carregada.")


def build_battle_engine() -> BattleEngineAdapter:
    return LocalBattleEngineAdapter()


async def battle_engine_health_status(adapter: BattleEngineAdapter) -> BattleEngineHealthStatus:
    try:
        return await adapter.ping()
    except Exception as exc:
        return BattleEngineHealthStatus(status="unavailable", detail=str(exc))


async def ensure_battle_engine_ready(adapter: BattleEngineAdapter) -> None:
    return None
