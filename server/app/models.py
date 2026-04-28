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
SAME_GENERATION = "same_generation"
TIME_CAPSULE_GEN1_GEN2 = "time_capsule_gen1_gen2"
FORWARD_TRANSFER_TO_GEN3 = "forward_transfer_to_gen3"
LEGACY_DOWNCONVERT_EXPERIMENTAL = "legacy_downconvert_experimental"
UNSUPPORTED = "unsupported"
TRADE_MODE_MATRIX = {
    (1, 1): SAME_GENERATION,
    (2, 2): SAME_GENERATION,
    (3, 3): SAME_GENERATION,
    (1, 2): TIME_CAPSULE_GEN1_GEN2,
    (2, 1): TIME_CAPSULE_GEN1_GEN2,
    (1, 3): FORWARD_TRANSFER_TO_GEN3,
    (2, 3): FORWARD_TRANSFER_TO_GEN3,
    (3, 1): LEGACY_DOWNCONVERT_EXPERIMENTAL,
    (3, 2): LEGACY_DOWNCONVERT_EXPERIMENTAL,
}
VALID_TRADE_MODES = set(TRADE_MODE_MATRIX.values())


class RoomError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(slots=True)
class PokemonOffer:
    payload_version: int
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
    source_generation: int | None = None
    source_game: str | None = None
    target_generation: int | None = None
    trade_mode: str = SAME_GENERATION
    summary: dict[str, Any] = field(default_factory=dict)
    canonical: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    compatibility_report: dict[str, Any] | None = None

    @classmethod
    def from_message(cls, payload: dict[str, Any]) -> "PokemonOffer":
        payload_bytes = len(json_dumps_compact(payload).encode("utf-8"))
        if payload_bytes > MAX_PAYLOAD_JSON_BYTES:
            raise RoomError("payload_too_large", "Payload do Pokemon excede o limite permitido.")
        raw = dict(payload.get("raw") or {})
        summary = dict(payload.get("summary") or {})
        canonical = dict(payload.get("canonical") or {})
        canonical_species = dict(canonical.get("species") or {})
        generation = parse_generation(payload.get("generation") or payload.get("source_generation") or canonical.get("source_generation"))
        game = parse_game_id(payload.get("game") or payload.get("source_game") or canonical.get("source_game"), generation)
        species_id = int(
            payload.get("species_id")
            or summary.get("species_id")
            or canonical.get("species_national_id")
            or canonical_species.get("national_dex_id")
            or 0
        )
        species_name = str(
            payload.get("species_name")
            or summary.get("species_name")
            or canonical.get("species_name")
            or canonical_species.get("name")
            or ""
        )
        level = int(payload.get("level") or summary.get("level") or canonical.get("level") or 0)
        nickname = str(payload.get("nickname") or summary.get("nickname") or canonical.get("nickname") or species_name)
        trainer_id = int(payload.get("trainer_id") or canonical.get("trainer_id") or 0)
        if species_id < 1 or level < 1 or level > 100:
            raise RoomError("invalid_payload", "Pokemon oferecido tem species_id ou level invalido.")
        raw_data = str(payload.get("raw_data_base64") or raw.get("data_base64") or "")
        if not raw_data and not canonical:
            raise RoomError("invalid_payload", "Payload sem dados raw ou canonical utilizaveis.")
        trade_mode = parse_trade_mode(payload.get("trade_mode") or SAME_GENERATION)
        return cls(
            payload_version=int(payload.get("payload_version") or 1),
            generation=generation,
            game=game,
            species_id=species_id,
            species_name=species_name[:80],
            level=level,
            nickname=nickname[:32],
            ot_name=str(payload.get("ot_name") or summary.get("ot_name") or "")[:32],
            trainer_id=trainer_id,
            raw_data_base64=raw_data,
            display_summary=str(payload.get("display_summary") or summary.get("display_summary") or f"{species_name} Lv. {level}")[:120],
            checksum=str(payload["checksum"])[:128] if payload.get("checksum") else None,
            metadata=dict(payload.get("metadata") or {}),
            source_generation=int(payload["source_generation"]) if payload.get("source_generation") is not None else generation,
            source_game=str(payload["source_game"]) if payload.get("source_game") is not None else game,
            target_generation=int(payload["target_generation"]) if payload.get("target_generation") is not None else None,
            trade_mode=trade_mode,
            summary=summary,
            canonical=canonical or None,
            raw=raw,
            compatibility_report=dict(payload["compatibility_report"]) if payload.get("compatibility_report") else None,
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "payload_version": self.payload_version,
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
            "source_generation": self.source_generation or self.generation,
            "source_game": self.source_game or self.game,
            "target_generation": self.target_generation,
            "trade_mode": self.trade_mode,
            "summary": self.summary,
            "canonical": self.canonical,
            "raw": self.raw or {"format": self.metadata.get("format"), "data_base64": self.raw_data_base64, "checksum": self.checksum},
            "compatibility_report": self.compatibility_report,
        }

    def log_summary(self) -> dict[str, Any]:
        return {
            "payload_version": self.payload_version,
            "generation": self.generation,
            "game": self.game,
            "species_id": self.species_id,
            "level": self.level,
            "trade_mode": self.trade_mode,
            "display_summary": self.display_summary,
            "raw_data_base64": "<redacted>",
            "raw": "<redacted>",
            "canonical": "<redacted>" if self.canonical else None,
        }


@dataclass(slots=True)
class Player:
    slot: PlayerSlot
    client_id: str
    generation: int
    game: str
    supported_trade_modes: list[str] = field(default_factory=list)
    status: str = "connected"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "generation": self.generation,
            "game": self.game,
            "supported_trade_modes": self.supported_trade_modes,
            "status": self.status,
        }


@dataclass(slots=True)
class Room:
    room_name: str
    password_hash: str
    generation: int
    game_family: str
    trade_mode: str = SAME_GENERATION
    compatibility_status: dict[str, Any] = field(default_factory=dict)
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
            "trade_mode": self.trade_mode,
            "compatibility_status": self.compatibility_status,
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


def trade_mode_for_generations(source_generation: int, target_generation: int) -> str:
    return TRADE_MODE_MATRIX.get((int(source_generation), int(target_generation)), UNSUPPORTED)


def supported_trade_modes_for_generation(generation: int) -> list[str]:
    generation = int(generation)
    modes = {mode for pair, mode in TRADE_MODE_MATRIX.items() if generation in pair}
    return sorted(modes)


def parse_trade_mode(value: Any) -> str:
    trade_mode = str(value or SAME_GENERATION).strip().lower()
    if trade_mode not in VALID_TRADE_MODES:
        raise RoomError("invalid_trade_mode", f"Modo de troca nao suportado: {trade_mode}.")
    return trade_mode


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
        "Cross-generation esta protegido por bloqueio de seguranca enquanto a camada de conversao local "
        "esta em desenvolvimento."
    )


def json_dumps_compact(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
