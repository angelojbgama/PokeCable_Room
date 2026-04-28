from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True)
class PokemonSummary:
    location: str
    species_id: int
    species_name: str
    level: int
    nickname: str
    ot_name: str = ""
    trainer_id: int = 0

    @property
    def display_summary(self) -> str:
        return f"{self.species_name} Lv. {self.level}"


@dataclass(slots=True)
class PokemonPayload:
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PokemonPayload":
        return cls(
            generation=int(payload["generation"]),
            game=str(payload["game"]),
            species_id=int(payload["species_id"]),
            species_name=str(payload["species_name"]),
            level=int(payload["level"]),
            nickname=str(payload["nickname"]),
            ot_name=str(payload.get("ot_name") or ""),
            trainer_id=int(payload.get("trainer_id") or 0),
            raw_data_base64=str(payload["raw_data_base64"]),
            display_summary=str(payload.get("display_summary") or f"{payload['species_name']} Lv. {payload['level']}"),
            checksum=str(payload["checksum"]) if payload.get("checksum") else None,
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(slots=True)
class SaveData:
    path: Path
    generation: int
    game_id: str
    party: list[PokemonSummary]


class SaveParser(Protocol):
    def detect(self, save_path: str | Path) -> bool:
        ...

    def load(self, save_path: str | Path) -> SaveData:
        ...

    def get_generation(self) -> int:
        ...

    def get_game_id(self) -> str:
        ...

    def list_party(self) -> list[PokemonSummary]:
        ...

    def list_boxes(self) -> list[PokemonSummary]:
        ...

    def export_pokemon(self, location: str) -> PokemonPayload:
        ...

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        ...

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        ...

    def validate(self) -> bool:
        ...

    def recalculate_checksums(self) -> None:
        ...

    def save(self, save_path: str | Path) -> None:
        ...


class ParserNotImplemented:
    generation: int = 0
    game_id: str = "unknown"

    def __init__(self) -> None:
        self.save_data: SaveData | None = None

    def detect(self, save_path: str | Path) -> bool:
        return False

    def load(self, save_path: str | Path) -> SaveData:
        raise NotImplementedError("Parser real ainda nao implementado nesta fase.")

    def get_generation(self) -> int:
        return self.generation

    def get_game_id(self) -> str:
        return self.game_id

    def list_party(self) -> list[PokemonSummary]:
        raise NotImplementedError("Listagem de party sera implementada na fase da geracao correspondente.")

    def list_boxes(self) -> list[PokemonSummary]:
        raise NotImplementedError("Boxes serao adicionadas depois da party.")

    def export_pokemon(self, location: str) -> PokemonPayload:
        raise NotImplementedError("Exportacao real sera implementada na fase da geracao correspondente.")

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        raise NotImplementedError("Importacao real sera implementada na fase da geracao correspondente.")

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        raise NotImplementedError("Edicao real de save sera implementada na fase da geracao correspondente.")

    def validate(self) -> bool:
        return False

    def recalculate_checksums(self) -> None:
        raise NotImplementedError("Checksums reais serao implementados na fase da geracao correspondente.")

    def save(self, save_path: str | Path) -> None:
        raise NotImplementedError("Gravacao real sera implementada na fase da geracao correspondente.")

