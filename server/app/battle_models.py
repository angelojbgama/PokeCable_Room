from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .models import PlayerSlot


BATTLE_FORMATS_BY_GENERATION = {
    1: "gen1customgame",
    2: "gen2customgame",
    3: "gen3customgame",
}


@dataclass(slots=True)
class BattlePlayer:
    slot: PlayerSlot
    client_id: str
    generation: int
    game: str
    team: list[dict[str, Any]] = field(default_factory=list)
    ready: bool = False
    confirmed: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "generation": self.generation,
            "game": self.game,
            "team_size": len(self.team),
            "ready": self.ready,
            "confirmed": self.confirmed,
        }


@dataclass(slots=True)
class BattleRoom:
    room_name: str
    password_hash: str
    generation: int
    format_id: str
    players: dict[PlayerSlot, BattlePlayer] = field(default_factory=dict)
    battle_id: str | None = None
    status: str = "waiting"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    max_players: int = 2

    def peer_slot(self, slot: PlayerSlot) -> PlayerSlot:
        return "B" if slot == "A" else "A"

    def is_full(self) -> bool:
        return len(self.players) >= self.max_players

    def is_ready(self) -> bool:
        return len(self.players) == self.max_players

    def has_both_teams(self) -> bool:
        return self.is_ready() and all(player.ready for player in self.players.values())

    def has_both_confirmations(self) -> bool:
        return self.has_both_teams() and all(player.confirmed for player in self.players.values())

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "room_name": self.room_name,
            "generation": self.generation,
            "format_id": self.format_id,
            "battle_id": self.battle_id,
            "status": self.status,
            "players": {slot: player.to_public_dict() for slot, player in self.players.items()},
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
