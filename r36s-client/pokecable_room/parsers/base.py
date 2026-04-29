from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport
from pokecable_room.display import normalize_pokemon_display


@dataclass(slots=True)
class PokemonSummary:
    location: str
    species_id: int
    species_name: str
    level: int
    nickname: str
    ot_name: str = ""
    trainer_id: int = 0
    national_dex_id: int | None = None
    held_item_id: int | None = None
    held_item_name: str | None = None
    gender: str | None = None

    @property
    def display_summary(self) -> str:
        return normalize_pokemon_display(
            self.national_dex_id,
            self.species_name,
            self.level,
            nickname=self.nickname,
            gender=self.gender,
            held_item_name=self.held_item_name,
        )


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
    payload_version: int = 2
    source_generation: int | None = None
    source_game: str | None = None
    target_generation: int | None = None
    trade_mode: str = "same_generation"
    summary: dict[str, Any] = field(default_factory=dict)
    canonical: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    compatibility_report: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_generation"] = self.source_generation or self.generation
        payload["source_game"] = self.source_game or self.game
        if not payload["summary"]:
            payload["summary"] = {
                "species_id": self.species_id,
                "species_name": self.species_name,
                "level": self.level,
                "nickname": self.nickname,
                "display_summary": self.display_summary,
                "national_dex_id": self.canonical.get("species", {}).get("national_dex_id") if self.canonical else None,
            }
        if not payload["raw"]:
            payload["raw"] = {
                "format": self.metadata.get("format", f"gen{self.generation}-party-v1"),
                "data_base64": self.raw_data_base64,
                "checksum": self.checksum,
            }
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PokemonPayload":
        canonical = dict(payload.get("canonical") or {})
        canonical_species = dict(canonical.get("species") or {})
        summary = dict(payload.get("summary") or {})
        generation = int(payload.get("generation") or payload.get("source_generation") or canonical.get("source_generation"))
        game = str(payload.get("game") or payload.get("source_game") or canonical.get("source_game"))
        raw = dict(payload.get("raw") or {})
        raw_data_base64 = str(payload.get("raw_data_base64") or raw.get("data_base64") or "")
        species_id = int(
            payload.get("species_id")
            or summary.get("species_id")
            or canonical.get("species_national_id")
            or canonical_species.get("national_dex_id")
        )
        species_name = str(
            payload.get("species_name")
            or summary.get("species_name")
            or canonical.get("species_name")
            or canonical_species.get("name")
        )
        level = int(payload.get("level") or summary.get("level") or canonical.get("level"))
        nickname = str(payload.get("nickname") or summary.get("nickname") or canonical.get("nickname") or species_name)
        return cls(
            generation=generation,
            game=game,
            species_id=species_id,
            species_name=species_name,
            level=level,
            nickname=nickname,
            ot_name=str(payload.get("ot_name") or canonical.get("ot_name") or ""),
            trainer_id=int(payload.get("trainer_id") or canonical.get("trainer_id") or 0),
            raw_data_base64=raw_data_base64,
            display_summary=str(payload.get("display_summary") or summary.get("display_summary") or f"{species_name} Lv. {level}"),
            checksum=str(payload["checksum"]) if payload.get("checksum") else None,
            metadata=dict(payload.get("metadata") or {}),
            payload_version=int(payload.get("payload_version") or 1),
            source_generation=int(payload["source_generation"]) if payload.get("source_generation") is not None else generation,
            source_game=str(payload["source_game"]) if payload.get("source_game") is not None else game,
            target_generation=int(payload["target_generation"]) if payload.get("target_generation") is not None else None,
            trade_mode=str(payload.get("trade_mode") or "same_generation"),
            summary=summary,
            canonical=canonical or None,
            raw=raw,
            compatibility_report=dict(payload["compatibility_report"]) if payload.get("compatibility_report") else None,
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

    def export_canonical(self, location: str) -> CanonicalPokemon:
        ...

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        ...

    def import_canonical(self, location: str, canonical_pokemon: CanonicalPokemon) -> None:
        ...

    def can_import_canonical(self, canonical_pokemon: CanonicalPokemon) -> bool:
        ...

    def compatibility_report_for(self, canonical_pokemon: CanonicalPokemon) -> CompatibilityReport:
        ...

    def get_species_id(self, location: str) -> int:
        ...

    def set_species_id(self, location: str, species_id: int) -> None:
        ...

    def get_held_item_id(self, location: str) -> int | None:
        ...

    def set_held_item_id(self, location: str, item_id: int) -> None:
        ...

    def clear_held_item(self, location: str) -> None:
        ...

    def mark_pokedex_seen(self, national_dex_id: int) -> None:
        ...

    def mark_pokedex_caught(self, national_dex_id: int) -> None:
        ...

    def is_pokedex_seen(self, national_dex_id: int) -> bool:
        ...

    def is_pokedex_caught(self, national_dex_id: int) -> bool:
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

    def export_canonical(self, location: str) -> CanonicalPokemon:
        raise NotImplementedError("Exportacao canonica sera implementada na fase da geracao correspondente.")

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        raise NotImplementedError("Importacao real sera implementada na fase da geracao correspondente.")

    def import_canonical(self, location: str, canonical_pokemon: CanonicalPokemon) -> None:
        raise NotImplementedError("Importacao canonica sera implementada com os conversores seguros.")

    def can_import_canonical(self, canonical_pokemon: CanonicalPokemon) -> bool:
        return False

    def compatibility_report_for(self, canonical_pokemon: CanonicalPokemon) -> CompatibilityReport:
        return CompatibilityReport(
            compatible=False,
            mode="unsupported",
            source_generation=canonical_pokemon.source_generation,
            target_generation=self.generation,
            blocking_reasons=["Parser nao implementou compatibilidade canonica."],
        )

    def get_species_id(self, location: str) -> int:
        raise NotImplementedError("Leitura de species_id ainda nao implementada.")

    def set_species_id(self, location: str, species_id: int) -> None:
        raise NotImplementedError("Escrita de species_id ainda nao implementada.")

    def get_held_item_id(self, location: str) -> int | None:
        return None

    def set_held_item_id(self, location: str, item_id: int) -> None:
        raise NotImplementedError("Held item nao existe ou ainda nao foi implementado neste parser.")

    def clear_held_item(self, location: str) -> None:
        raise NotImplementedError("Held item nao existe ou ainda nao foi implementado neste parser.")

    def mark_pokedex_seen(self, national_dex_id: int) -> None:
        raise NotImplementedError("Pokédex ainda nao foi implementado neste parser.")

    def mark_pokedex_caught(self, national_dex_id: int) -> None:
        raise NotImplementedError("Pokédex ainda nao foi implementado neste parser.")

    def is_pokedex_seen(self, national_dex_id: int) -> bool:
        raise NotImplementedError("Pokédex ainda nao foi implementado neste parser.")

    def is_pokedex_caught(self, national_dex_id: int) -> bool:
        raise NotImplementedError("Pokédex ainda nao foi implementado neste parser.")

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        raise NotImplementedError("Edicao real de save sera implementada na fase da geracao correspondente.")

    def validate(self) -> bool:
        return False

    def recalculate_checksums(self) -> None:
        raise NotImplementedError("Checksums reais serao implementados na fase da geracao correspondente.")

    def save(self, save_path: str | Path) -> None:
        raise NotImplementedError("Gravacao real sera implementada na fase da geracao correspondente.")
