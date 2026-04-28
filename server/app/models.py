from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


PlayerSlot = Literal["A", "B"]
VALID_GENERATIONS = {1, 2, 3}
SUPPORTED_GAME_IDS = {
    "pokemon_red": 1,
    "pokemon_blue": 1,
    "pokemon_yellow": 1,
    "pokemon_gold": 2,
    "pokemon_silver": 2,
    "pokemon_crystal": 2,
    "pokemon_ruby": 3,
    "pokemon_sapphire": 3,
    "pokemon_emerald": 3,
    "pokemon_firered": 3,
    "pokemon_leafgreen": 3,
}
MAX_ROOM_NAME_LENGTH = 64
MAX_GAME_ID_LENGTH = 64
MAX_CLIENT_ID_LENGTH = 80
MAX_PAYLOAD_JSON_BYTES = 32 * 1024


class RoomError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(slots=True)
class PokemonOffer:
    generation: int
    game: str
    species_id: int
    species_name: str
    level: int
    nickname: str
    ot_name: str
    trainer_id: int
    raw_data_base64: str
    display_summary: str
    checksum: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_message(cls, payload: dict[str, Any]) -> "PokemonOffer":
        required = [
            "generation",
            "game",
            "species_id",
            "species_name",
            "level",
            "nickname",
            "ot_name",
            "trainer_id",
            "raw_data_base64",
            "display_summary",
        ]
        missing = [key for key in required if key not in payload]
        if missing:
            raise RoomError("invalid_payload", f"Payload sem campos obrigatorios: {', '.join(missing)}")
        generation = parse_generation(payload["generation"])
        game = parse_game_id(payload["game"], generation)
        species_id = int(payload["species_id"])
        level = int(payload["level"])
        trainer_id = int(payload["trainer_id"])
        if species_id < 1 or level < 1 or level > 100:
            raise RoomError("invalid_payload", "Pokemon oferecido tem species_id ou level invalido.")
        raw_data = str(payload["raw_data_base64"])
        if len(raw_data.encode("utf-8")) > MAX_PAYLOAD_JSON_BYTES:
            raise RoomError("payload_too_large", "Payload do Pokemon excede o limite permitido.")
        return cls(
            generation=generation,
            game=game,
            species_id=species_id,
            species_name=str(payload["species_name"])[:80],
            level=level,
            nickname=str(payload["nickname"])[:32],
            ot_name=str(payload["ot_name"])[:32],
            trainer_id=trainer_id,
            raw_data_base64=raw_data,
            display_summary=str(payload["display_summary"])[:120],
            checksum=str(payload["checksum"])[:128] if payload.get("checksum") else None,
            metadata=dict(payload.get("metadata") or {}),
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "game": self.game,
            "species_id": self.species_id,
            "species_name": self.species_name,
            "level": self.level,
            "nickname": self.nickname,
            "ot_name": self.ot_name,
            "trainer_id": self.trainer_id,
            "raw_data_base64": self.raw_data_base64,
            "checksum": self.checksum,
            "metadata": self.metadata,
            "display_summary": self.display_summary,
        }

    def log_summary(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "game": self.game,
            "species_id": self.species_id,
            "level": self.level,
            "display_summary": self.display_summary,
            "raw_data_base64": "<redacted>",
        }


@dataclass(slots=True)
class Player:
    slot: PlayerSlot
    client_id: str
    generation: int
    game: str
    status: str = "connected"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "generation": self.generation,
            "game": self.game,
            "status": self.status,
        }


@dataclass(slots=True)
class Room:
    room_name: str
    password_hash: str
    generation: int
    game_family: str
    players: dict[PlayerSlot, Player] = field(default_factory=dict)
    offers: dict[PlayerSlot, PokemonOffer | None] = field(default_factory=lambda: {"A": None, "B": None})
    confirmations: dict[PlayerSlot, bool] = field(default_factory=lambda: {"A": False, "B": False})
    max_players: int = 2
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def peer_slot(self, slot: PlayerSlot) -> PlayerSlot:
        return "B" if slot == "A" else "A"

    def is_full(self) -> bool:
        return len(self.players) >= self.max_players

    def is_ready(self) -> bool:
        return len(self.players) == self.max_players

    def has_both_offers(self) -> bool:
        return self.offers["A"] is not None and self.offers["B"] is not None

    def is_committed(self) -> bool:
        return self.confirmations["A"] and self.confirmations["B"] and self.has_both_offers()

    def scrub_sensitive_data(self) -> None:
        self.offers = {"A": None, "B": None}
        self.confirmations = {"A": False, "B": False}

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "room_name": self.room_name,
            "max_players": self.max_players,
            "generation": self.generation,
            "game_family": self.game_family,
            "players": {slot: player.to_public_dict() for slot, player in self.players.items()},
            "offers": {slot: offer.log_summary() if offer else None for slot, offer in self.offers.items()},
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_room_name(value: Any) -> str:
    room_name = str(value or "").strip()
    if not room_name:
        raise RoomError("invalid_room", "Nome da sala e obrigatorio.")
    if len(room_name) > MAX_ROOM_NAME_LENGTH:
        raise RoomError("invalid_room", f"Nome da sala deve ter no maximo {MAX_ROOM_NAME_LENGTH} caracteres.")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. ")
    if any(ch not in allowed for ch in room_name):
        raise RoomError("invalid_room", "Nome da sala contem caracteres nao suportados.")
    return room_name


def parse_client_id(value: Any) -> str:
    client_id = str(value or "").strip()
    if not client_id:
        raise RoomError("invalid_client", "client_id e obrigatorio.")
    if len(client_id) > MAX_CLIENT_ID_LENGTH:
        raise RoomError("invalid_client", "client_id excede o limite permitido.")
    return client_id


def parse_generation(value: Any) -> int:
    try:
        generation = int(value)
    except (TypeError, ValueError) as exc:
        raise RoomError("invalid_generation", "Geracao precisa ser 1, 2 ou 3.") from exc
    if generation not in VALID_GENERATIONS:
        raise RoomError("invalid_generation", "Geracao precisa ser 1, 2 ou 3.")
    return generation


def game_family_for_generation(generation: int) -> str:
    return f"gen{generation}"


def parse_game_id(value: Any, generation: int) -> str:
    game = str(value or "").strip().lower()
    if not game:
        raise RoomError("invalid_game", "game e obrigatorio.")
    if len(game) > MAX_GAME_ID_LENGTH:
        raise RoomError("invalid_game", "game excede o limite permitido.")
    expected_generation = SUPPORTED_GAME_IDS.get(game)
    if expected_generation is not None and expected_generation != generation:
        raise RoomError(
            "game_mismatch",
            f"O jogo {game} pertence a Gen {expected_generation}, mas o client informou Gen {generation}.",
        )
    return game


def generation_mismatch_message(room_generation: int, client_generation: int) -> str:
    return (
        f"Esta sala e Gen {room_generation}. Seu save e Gen {client_generation}. "
        "Trocas entre geracoes diferentes ainda nao sao suportadas."
    )
