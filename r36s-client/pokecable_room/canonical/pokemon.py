from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .items import CanonicalItem
from .moves import CanonicalMove


@dataclass(slots=True)
class CanonicalStats:
    hp: int | None = None
    attack: int | None = None
    defense: int | None = None
    speed: int | None = None
    special: int | None = None
    special_attack: int | None = None
    special_defense: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "CanonicalStats | None":
        if value is None:
            return None
        return cls(**{key: value.get(key) for key in cls.__dataclass_fields__})


@dataclass(slots=True)
class CanonicalOriginalData:
    generation: int
    game: str
    format: str
    raw_data_base64: str | None = None
    checksum: str | None = None
    location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CanonicalOriginalData":
        return cls(
            generation=int(value["generation"]),
            game=str(value["game"]),
            format=str(value["format"]),
            raw_data_base64=str(value["raw_data_base64"]) if value.get("raw_data_base64") else None,
            checksum=str(value["checksum"]) if value.get("checksum") else None,
            location=str(value["location"]) if value.get("location") else None,
            metadata=dict(value.get("metadata") or {}),
        )


@dataclass(slots=True)
class CanonicalSpecies:
    national_dex_id: int
    source_species_id: int
    source_species_id_space: str
    name: str
    target_species_id: int | None = None
    target_species_id_space: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CanonicalSpecies":
        return cls(
            national_dex_id=int(value["national_dex_id"]),
            source_species_id=int(value["source_species_id"]),
            source_species_id_space=str(value["source_species_id_space"]),
            name=str(value["name"]),
            target_species_id=int(value["target_species_id"]) if value.get("target_species_id") is not None else None,
            target_species_id_space=str(value["target_species_id_space"]) if value.get("target_species_id_space") else None,
        )


@dataclass(slots=True)
class CanonicalPokemon:
    source_generation: int
    source_game: str
    species_national_id: int
    species_name: str
    nickname: str
    level: int
    ot_name: str
    trainer_id: int
    experience: int | None = None
    moves: list[CanonicalMove] = field(default_factory=list)
    held_item: CanonicalItem | None = None
    ivs: CanonicalStats | None = None
    evs: CanonicalStats | None = None
    nature: str | None = None
    ability: str | None = None
    original_data: CanonicalOriginalData | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    species: CanonicalSpecies | None = None

    def __post_init__(self) -> None:
        if self.species is None:
            source_species_id = int(self.metadata.get("source_species_id") or self.species_national_id)
            source_species_id_space = str(self.metadata.get("source_species_id_space") or "legacy_national_dex")
            self.species = CanonicalSpecies(
                national_dex_id=int(self.species_national_id),
                source_species_id=source_species_id,
                source_species_id_space=source_species_id_space,
                name=self.species_name,
            )
            self.metadata.setdefault("migration", "species_national_id_promoted_to_species")
        else:
            self.species_national_id = self.species.national_dex_id
            self.species_name = self.species.name

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CanonicalPokemon":
        species = CanonicalSpecies.from_dict(value["species"]) if value.get("species") else None
        species_national_id = int(value.get("species_national_id") or (species.national_dex_id if species else 0))
        species_name = str(value.get("species_name") or (species.name if species else ""))
        metadata = dict(value.get("metadata") or {})
        if species is None and "species_national_id" in value:
            metadata.setdefault("migration", "legacy_species_national_id_payload")
        return cls(
            source_generation=int(value["source_generation"]),
            source_game=str(value["source_game"]),
            species_national_id=species_national_id,
            species_name=species_name,
            nickname=str(value.get("nickname") or species_name),
            level=int(value["level"]),
            ot_name=str(value.get("ot_name") or ""),
            trainer_id=int(value.get("trainer_id") or 0),
            experience=int(value["experience"]) if value.get("experience") is not None else None,
            moves=[CanonicalMove.from_dict(item) for item in value.get("moves") or []],
            held_item=CanonicalItem.from_dict(value.get("held_item")),
            ivs=CanonicalStats.from_dict(value.get("ivs")),
            evs=CanonicalStats.from_dict(value.get("evs")),
            nature=str(value["nature"]) if value.get("nature") else None,
            ability=str(value["ability"]) if value.get("ability") else None,
            original_data=CanonicalOriginalData.from_dict(value["original_data"]) if value.get("original_data") else None,
            metadata=metadata,
            species=species,
        )
