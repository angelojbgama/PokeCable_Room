#!/usr/bin/env python3
"""
Local save parsing and write support for PokeCable on R36S.

This module intentionally focuses on the safe, party-based trade path.
It parses party Pokemon from supported saves, exports same-generation raw
payloads compatible with the current websocket backend, and applies the
received payload back into the selected party slot with checksum updates.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class SaveError(Exception):
    """Raised when a local save cannot be parsed or updated safely."""


logger = logging.getLogger("pokecable_save")
SHINY_ATTACK_DVS = {2, 3, 6, 7, 10, 11, 14, 15}


def _ensure_backend_import_path() -> None:
    runtime_dir = Path(__file__).resolve().parent / "pokecable_runtime"
    runtime_path = str(runtime_dir)
    if runtime_dir.exists() and runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)


_ensure_backend_import_path()

from data.moves import default_move_pp  # noqa: E402
from data.gender_rates import gender_from_gen2_attack_dv, gender_from_gen3_personality  # noqa: E402


def _resolve_national_dex_id(generation: int, species_id: int, pokemon: Dict[str, Any]) -> int:
    national = int(pokemon.get("national_dex_id") or 0)
    if national > 0:
        return national
    if generation == 2 and species_id > 0:
        return species_id
    if species_id <= 0:
        return 0
    try:
        _ensure_backend_import_path()
        from data.species import native_to_national  # type: ignore

        return int(native_to_national(int(generation), int(species_id)))
    except Exception:
        return 0


def _level_from_experience(generation: int, species_id: int, experience: int) -> int:
    try:
        _ensure_backend_import_path()
        from data.growth_rates import level_from_species_experience  # type: ignore
        from data.species import native_to_national  # type: ignore

        national_dex_id = int(native_to_national(int(generation), int(species_id)) or 0)
        if national_dex_id:
            return max(1, min(100, int(level_from_species_experience(national_dex_id, int(experience)))))
    except Exception as exc:
        logger.debug("Level-from-exp Gen%s failed: %s", generation, exc)
    return 1


def _experience_progress_for_payload(national_dex_id: int, experience: int) -> Dict[str, Any]:
    if int(national_dex_id or 0) <= 0:
        return {}
    try:
        _ensure_backend_import_path()
        from data.growth_rates import experience_progress_for_species  # type: ignore

        return dict(experience_progress_for_species(int(national_dex_id), int(experience)))
    except Exception as exc:
        logger.debug("Experience progress failed for National Dex #%s: %s", national_dex_id, exc)
        return {}


def _legacy_shiny_dvs(attack_dv: int, defense_dv: int, speed_dv: int, special_dv: int) -> bool:
    return (
        int(attack_dv) in SHINY_ATTACK_DVS
        and int(defense_dv) == 10
        and int(speed_dv) == 10
        and int(special_dv) == 10
    )


def _legacy_shiny_from_mon(mon: bytes, offset: int) -> bool:
    if len(mon) <= offset + 1:
        return False
    dv1 = int(mon[offset])
    dv2 = int(mon[offset + 1])
    return _legacy_shiny_dvs(dv1 >> 4, dv1 & 0x0F, dv2 >> 4, dv2 & 0x0F)


def _gen3_is_shiny(personality: int, trainer_id: int) -> bool:
    personality = int(personality) & 0xFFFFFFFF
    trainer_id = int(trainer_id) & 0xFFFFFFFF
    shiny_value = (
        (trainer_id & 0xFFFF)
        ^ ((trainer_id >> 16) & 0xFFFF)
        ^ (personality & 0xFFFF)
        ^ ((personality >> 16) & 0xFFFF)
    )
    return shiny_value < 8


def _pokemon_is_shiny(pokemon: Dict[str, Any]) -> bool:
    metadata = pokemon.get("metadata") if isinstance(pokemon.get("metadata"), dict) else {}
    canonical = pokemon.get("canonical") if isinstance(pokemon.get("canonical"), dict) else {}
    canonical_metadata = canonical.get("metadata") if isinstance(canonical.get("metadata"), dict) else {}
    return bool(
        pokemon.get("is_shiny")
        or metadata.get("is_shiny")
        or canonical.get("is_shiny")
        or canonical_metadata.get("is_shiny")
    )


GEN1 = {
    "player_name_offset": 0x2598,
    "party_offset": 0x2F2C,
    "data_offset": 0x2F34,
    "ot_offset": 0x303C,
    "nick_offset": 0x307E,
    "current_box_offset": 0x284C,
    "current_box_data_offset": 0x30C0,
    "checksum_start": 0x2598,
    "checksum_end": 0x3522,
    "checksum_offset": 0x3523,
    "party_capacity": 6,
    "box_capacity": 20,
    "mon_size": 44,
    "box_mon_size": 33,
    "box_count": 12,
    "box_data_size": 0x462,
    "box_ot_offset": 0x2AA,
    "box_nick_offset": 0x386,
    "name_size": 11,
    "party_format": "gen1-party-v1",
    "box_format": "gen1-box-v1",
    "game_label": "Gen 1 Red/Blue/Yellow",
}
GEN1["stored_box_offsets"] = [((0x4000 if index < 6 else 0x6000) + (index % 6) * GEN1["box_data_size"]) for index in range(GEN1["box_count"])]

GEN2_CRYSTAL = {
    "player_name_offset": 0x200B,
    "party_offset": 0x2865,
    "primary_start": 0x2009,
    "primary_end": 0x2B82,
    "primary_checksum": 0x2D0D,
    "secondary_start": 0x1209,
    "secondary_end": 0x1D82,
    "secondary_checksum": 0x1F0D,
    "current_box_offset": 0x2700,
    "box_names_offset": 0x2703,
    "current_box_data_offset": 0x2D10,
    "party_capacity": 6,
    "box_capacity": 20,
    "mon_size": 48,
    "box_mon_size": 32,
    "box_count": 14,
    "box_name_size": 9,
    "box_ot_offset": 0x296,
    "box_nick_offset": 0x372,
    "name_size": 11,
    "party_format": "gen2-crystal-party-v1",
    "box_format": "gen2-crystal-box-v1",
    "game_label": "Gen 2 Crystal",
}
GEN2_CRYSTAL["header_size"] = 1 + GEN2_CRYSTAL["party_capacity"] + 1
GEN2_CRYSTAL["data_offset"] = GEN2_CRYSTAL["party_offset"] + GEN2_CRYSTAL["header_size"]
GEN2_CRYSTAL["ot_offset"] = GEN2_CRYSTAL["data_offset"] + GEN2_CRYSTAL["party_capacity"] * GEN2_CRYSTAL["mon_size"]
GEN2_CRYSTAL["nick_offset"] = GEN2_CRYSTAL["ot_offset"] + GEN2_CRYSTAL["party_capacity"] * GEN2_CRYSTAL["name_size"]
GEN2_CRYSTAL["stored_box_offsets"] = [0x4000 + index * 0x450 for index in range(7)] + [0x6000 + index * 0x450 for index in range(7)]

GEN2_GS = {
    "player_name_offset": 0x200B,
    "party_offset": 0x288A,
    "primary_start": 0x2009,
    "primary_end": 0x2D68,
    "primary_checksum": 0x2D69,
    "current_box_offset": 0x2724,
    "box_names_offset": 0x2727,
    "current_box_data_offset": 0x2D6C,
    "party_capacity": 6,
    "box_capacity": 20,
    "mon_size": 48,
    "box_mon_size": 32,
    "box_count": 14,
    "box_name_size": 9,
    "box_ot_offset": 0x296,
    "box_nick_offset": 0x372,
    "name_size": 11,
    "party_format": "gen2-gold-silver-party-v1",
    "box_format": "gen2-gold-silver-box-v1",
}
GEN2_GS["header_size"] = 1 + GEN2_GS["party_capacity"] + 1
GEN2_GS["data_offset"] = GEN2_GS["party_offset"] + GEN2_GS["header_size"]
GEN2_GS["ot_offset"] = GEN2_GS["data_offset"] + GEN2_GS["party_capacity"] * GEN2_GS["mon_size"]
GEN2_GS["nick_offset"] = GEN2_GS["ot_offset"] + GEN2_GS["party_capacity"] * GEN2_GS["name_size"]
GEN2_GS["stored_box_offsets"] = [0x4000 + index * 0x450 for index in range(7)] + [0x6000 + index * 0x450 for index in range(7)]

GEN3 = {
    "player_name_offset": 0x0000,
    "sector_data_size": 3968,
    "sector_size": 4096,
    "sectors_per_slot": 14,
    "signature": 0x08012025,
    "mon_size": 100,
    "secure_offset": 32,
    "secure_size": 48,
    "party_capacity": 6,
    "box_mon_size": 80,
    "box_count": 14,
    "box_capacity": 30,
    "pc_buffer_boxes_offset": 0x0004,
    "pc_buffer_names_offset": 0x8344,
    "box_name_size": 9,
    "layouts": [
        {"name": "rse", "game": "pokemon_emerald", "party_count_offset": 0x234, "party_offset": 0x238},
        {"name": "frlg", "game": "pokemon_firered", "party_count_offset": 0x34, "party_offset": 0x38},
    ],
    "substruct_orders": [
        [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2],
        [0, 2, 3, 1], [0, 3, 2, 1], [1, 0, 2, 3], [1, 0, 3, 2],
        [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
        [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2],
        [2, 3, 0, 1], [3, 2, 0, 1], [1, 2, 3, 0], [1, 3, 2, 0],
        [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0],
    ],
}

GEN3_NATURES = [
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
]

def clean_name(value: Any) -> str:
    return str(value or "").replace("\x00", "").strip()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_u16(data: bytes | bytearray, offset: int) -> int:
    return int(data[offset]) | (int(data[offset + 1]) << 8)


def write_u16(data: bytearray, offset: int, value: int) -> None:
    data[offset] = value & 0xFF
    data[offset + 1] = (value >> 8) & 0xFF


def read_u32(data: bytes | bytearray, offset: int) -> int:
    return (
        int(data[offset])
        | (int(data[offset + 1]) << 8)
        | (int(data[offset + 2]) << 16)
        | (int(data[offset + 3]) << 24)
    )


def write_u32(data: bytearray, offset: int, value: int) -> None:
    data[offset] = value & 0xFF
    data[offset + 1] = (value >> 8) & 0xFF
    data[offset + 2] = (value >> 16) & 0xFF
    data[offset + 3] = (value >> 24) & 0xFF


def decode_gbc_text(blob: bytes | bytearray) -> str:
    chars: List[str] = []
    for byte in blob:
        if byte in (0x50, 0xFF, 0x00):
            break
        if 0x80 <= byte <= 0x99:
            chars.append(chr(65 + byte - 0x80))
        elif 0xA0 <= byte <= 0xB9:
            chars.append(chr(97 + byte - 0xA0))
        elif byte == 0x7F:
            chars.append(" ")
        elif byte == 0xE3:
            chars.append("-")
        elif byte >= 0xF6:
            chars.append(str(byte - 0xF6))
        else:
            chars.append("?")
    return "".join(chars).strip()


def decode_gen3_text(blob: bytes | bytearray) -> str:
    chars: List[str] = []
    for byte in blob:
        if byte == 0xFF:
            break
        if 0xBB <= byte <= 0xD4:
            chars.append(chr(65 + byte - 0xBB))
        elif 0xD5 <= byte <= 0xEE:
            chars.append(chr(97 + byte - 0xD5))
        elif 0xA1 <= byte <= 0xAA:
            chars.append(str(byte - 0xA1))
        elif byte == 0x00:
            chars.append(" ")
        elif byte == 0xAD:
            chars.append(".")
        elif byte == 0xAE:
            chars.append("-")
        elif byte == 0xB8:
            chars.append(",")
        else:
            chars.append("?")
    return "".join(chars).strip()


def encode_gbc_text(value: str, size: int) -> bytes:
    encoded = bytearray([0x50] * size)
    for index, char in enumerate(str(value or "")[: max(0, size - 1)]):
        if "A" <= char <= "Z":
            encoded[index] = 0x80 + ord(char) - ord("A")
        elif "a" <= char <= "z":
            encoded[index] = 0xA0 + ord(char) - ord("a")
        elif "0" <= char <= "9":
            encoded[index] = 0xF6 + ord(char) - ord("0")
        elif char == " ":
            encoded[index] = 0x7F
        elif char == "-":
            encoded[index] = 0xE3
        else:
            encoded[index] = 0x7F
    return bytes(encoded)


def encode_gen3_text(value: str, size: int) -> bytes:
    encoded = bytearray([0xFF] * size)
    for index, char in enumerate(str(value or "")[: max(0, size - 1)]):
        if "A" <= char <= "Z":
            encoded[index] = 0xBB + ord(char) - ord("A")
        elif "a" <= char <= "z":
            encoded[index] = 0xD5 + ord(char) - ord("a")
        elif "0" <= char <= "9":
            encoded[index] = 0xA1 + ord(char) - ord("0")
        elif char == " ":
            encoded[index] = 0x00
        elif char == ".":
            encoded[index] = 0xAD
        elif char == "-":
            encoded[index] = 0xAE
        elif char == ",":
            encoded[index] = 0xB8
        else:
            encoded[index] = 0x00
    return bytes(encoded)


def nickname_matches_species(nickname: str, species_name: str) -> bool:
    left = clean_name(nickname).lower().replace(" ", "")
    right = clean_name(species_name).lower().replace(" ", "")
    return bool(left and right and left == right)


def sum_range(data: bytes | bytearray, start: int, end: int) -> int:
    total = 0
    for index in range(start, end + 1):
        total = (total + int(data[index])) & 0xFFFF
    return total


def gen1_checksum(data: bytes | bytearray) -> int:
    value = 0xFF
    for index in range(GEN1["checksum_start"], GEN1["checksum_end"] + 1):
        value = (value - int(data[index])) & 0xFF
    return value


def validate_gen1(data: bytes) -> bool:
    if len(data) != 0x8000:
        return False
    count = data[GEN1["party_offset"]]
    if count > GEN1["party_capacity"]:
        return False
    if data[GEN1["party_offset"] + 1 + count] != 0xFF:
        return False
    return gen1_checksum(data) == data[GEN1["checksum_offset"]]


def validate_gen2(data: bytes, constants: Dict[str, Any]) -> bool:
    if len(data) != 0x8000:
        return False
    count = data[constants["party_offset"]]
    if count > constants["party_capacity"]:
        return False
    if data[constants["party_offset"] + 1 + count] != 0xFF:
        return False
    primary = sum_range(data, constants["primary_start"], constants["primary_end"])
    if primary == read_u16(data, constants["primary_checksum"]):
        return True
    if "secondary_start" not in constants:
        return False
    secondary = sum_range(data, constants["secondary_start"], constants["secondary_end"])
    return secondary == read_u16(data, constants["secondary_checksum"])


def write_gen2_checksums(data: bytearray, constants: Dict[str, Any]) -> None:
    write_u16(data, constants["primary_checksum"], sum_range(data, constants["primary_start"], constants["primary_end"]))
    if "secondary_start" in constants:
        write_u16(data, constants["secondary_checksum"], sum_range(data, constants["secondary_start"], constants["secondary_end"]))


def gen3_sector_checksum(data: bytes | bytearray, offset: int) -> int:
    checksum = 0
    for cursor in range(0, GEN3["sector_data_size"], 4):
        checksum = (checksum + read_u32(data, offset + cursor)) & 0xFFFFFFFF
    return ((checksum >> 16) + checksum) & 0xFFFF


def gen3_box_checksum(secure: bytes | bytearray) -> int:
    checksum = 0
    for offset in range(0, GEN3["secure_size"], 2):
        checksum = (checksum + read_u16(secure, offset)) & 0xFFFF
    return checksum


def decrypt_gen3_secure(raw: bytes | bytearray) -> bytearray:
    key = (read_u32(raw, 0) ^ read_u32(raw, 4)) & 0xFFFFFFFF
    secure = bytearray(GEN3["secure_size"])
    for offset in range(0, GEN3["secure_size"], 4):
        write_u32(secure, offset, (read_u32(raw, GEN3["secure_offset"] + offset) ^ key) & 0xFFFFFFFF)
    return secure


def encrypt_gen3_secure(raw: bytearray, secure: bytes | bytearray) -> None:
    key = (read_u32(raw, 0) ^ read_u32(raw, 4)) & 0xFFFFFFFF
    for offset in range(0, GEN3["secure_size"], 4):
        write_u32(raw, GEN3["secure_offset"] + offset, (read_u32(secure, offset) ^ key) & 0xFFFFFFFF)


def set_gen3_raw_species(raw: bytes, species_id: int) -> bytes:
    updated = bytearray(raw)
    secure = decrypt_gen3_secure(updated)
    growth = GEN3["substruct_orders"][read_u32(updated, 0) % 24][0] * 12
    write_u16(secure, growth, int(species_id))
    write_u16(updated, 0x1C, gen3_box_checksum(secure))
    encrypt_gen3_secure(updated, secure)
    return bytes(updated)


def parse_location(location: str) -> Dict[str, Any]:
    parts = str(location or "").split(":")
    if len(parts) == 2 and parts[0] == "party":
        return {"kind": "party", "index": int(parts[1])}
    if len(parts) == 3 and parts[0] == "box":
        return {"kind": "box", "box_index": int(parts[1]), "slot_index": int(parts[2])}
    raise SaveError(f"Localização inválida: {location}")


def supports_party_only(location: str) -> None:
    parsed = parse_location(location)
    if parsed["kind"] != "party":
        raise SaveError("Troca via PC/box ainda não é suportada no R36S.")


def normalize_pokemon_display(pokemon: Dict[str, Any]) -> str:
    name = clean_name(pokemon.get("nickname")) or clean_name(pokemon.get("species_name")) or "Pokemon"
    level = int(pokemon.get("level", 0))
    return f"{name} Lv.{level}" if level else name


def safe_species_name(species_id: int, nickname: str) -> str:
    return clean_name(nickname) or (f"Pokemon #{species_id}" if species_id else "Pokemon")


def preflight_report(compatible: bool, generation: int, reasons: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "compatible": compatible,
        "mode": "same_generation",
        "source_generation": generation,
        "target_generation": generation,
        "blocking_reasons": reasons or [],
        "warnings": [],
        "data_loss": [],
        "suggested_actions": [],
    }


def read_gen3_slot(data: bytes, base: int) -> Optional[Dict[str, Any]]:
    section_offsets: Dict[int, int] = {}
    counters: List[int] = []
    for physical in range(GEN3["sectors_per_slot"]):
        offset = base + physical * GEN3["sector_size"]
        if offset + GEN3["sector_size"] > len(data):
            continue
        section_id = read_u16(data, offset + 0xFF4)
        signature = read_u32(data, offset + 0xFF8)
        counter = read_u32(data, offset + 0xFFC)
        if signature != GEN3["signature"] or section_id >= GEN3["sectors_per_slot"]:
            continue
        if section_id not in section_offsets:
            section_offsets[section_id] = offset
        counters.append(counter)
    if not section_offsets or 1 not in section_offsets:
        return None
    return {"base": base, "counter": max(counters), "section_offsets": section_offsets}


def parse_gen3_pokemon(raw: bytes) -> Dict[str, Any]:
    if len(raw) != GEN3["mon_size"]:
        raise SaveError("Struct Pokemon Gen 3 inválido.")
    personality = read_u32(raw, 0)
    trainer_id = read_u32(raw, 4)
    checksum = read_u16(raw, 0x1C)
    secure = decrypt_gen3_secure(raw)
    if gen3_box_checksum(secure) != checksum:
        raise SaveError("Checksum interno do Pokémon Gen 3 inválido.")
    growth_index = GEN3["substruct_orders"][personality % 24][0]
    attacks_index = GEN3["substruct_orders"][personality % 24][1]
    growth = growth_index * 12
    attacks = attacks_index * 12
    species_id = read_u16(secure, growth)
    moves = []
    for offset in range(4):
        move_id = read_u16(secure, attacks + offset * 2)
        if move_id:
            moves.append(move_id)
    is_egg = species_id == 412 or bool(raw[0x13] & 0x04)
    nickname = decode_gen3_text(raw[0x08:0x12])
    species_name = "Egg" if is_egg else safe_species_name(species_id, nickname)
    return {
        "species_id": species_id,
        "species_name": species_name,
        "types": [],
        "level": int(raw[0x54]),
        "nickname": nickname or species_name,
        "ot_name": decode_gen3_text(raw[0x14:0x1B]),
        "trainer_id": trainer_id,
        "nature": None if is_egg else GEN3_NATURES[personality % 25],
        "ability_index": None if is_egg else (personality & 1),
        "held_item_id": read_u16(secure, growth + 2) or None,
        "moves": moves,
        "is_egg": is_egg,
        "is_shiny": False if is_egg else _gen3_is_shiny(personality, trainer_id),
        "experience": read_u32(secure, growth + 4),
        "personality": personality,
        "gender": None if is_egg else gender_from_gen3_personality(_resolve_national_dex_id(3, species_id, {}), personality),
    }


def parse_gen3_box_pokemon(raw: bytes) -> Dict[str, Any]:
    if len(raw) != GEN3["box_mon_size"]:
        raise SaveError("Struct Box Pokemon Gen 3 inválido.")
    checksum = read_u16(raw, 0x1C)
    secure = decrypt_gen3_secure(raw)
    if gen3_box_checksum(secure) != checksum:
        raise SaveError("Checksum interno do Box Pokemon Gen 3 inválido.")
    personality = read_u32(raw, 0)
    trainer_id = read_u32(raw, 4)
    growth_index = GEN3["substruct_orders"][personality % 24][0]
    attacks_index = GEN3["substruct_orders"][personality % 24][1]
    growth = growth_index * 12
    attacks = attacks_index * 12
    species_id = read_u16(secure, growth)
    moves = []
    for offset in range(4):
        move_id = read_u16(secure, attacks + offset * 2)
        if move_id:
            moves.append(move_id)
    nickname = decode_gen3_text(raw[0x08:0x12])
    is_egg = species_id == 412 or bool(raw[0x13] & 0x04)
    species_name = "Egg" if is_egg else safe_species_name(species_id, nickname)
    experience = read_u32(secure, growth + 4)
    return {
        "species_id": species_id,
        "species_name": species_name,
        "types": [],
        "level": 1 if is_egg else _level_from_experience(3, species_id, experience),
        "nickname": nickname or species_name,
        "ot_name": decode_gen3_text(raw[0x14:0x1B]),
        "trainer_id": trainer_id,
        "nature": None if is_egg else GEN3_NATURES[personality % 25],
        "ability_index": None if is_egg else (personality & 1),
        "held_item_id": read_u16(secure, growth + 2) or None,
        "moves": moves,
        "is_egg": is_egg,
        "is_shiny": False if is_egg else _gen3_is_shiny(personality, trainer_id),
        "experience": experience,
        "personality": personality,
        "gender": None if is_egg else gender_from_gen3_personality(_resolve_national_dex_id(3, species_id, {}), personality),
    }


def gen3_layout_score(data: bytes, slot: Dict[str, Any], layout: Dict[str, Any]) -> int:
    section1 = slot["section_offsets"][1]
    if read_u16(data, section1 + 0xFF6) != gen3_sector_checksum(data, section1):
        return 0
    count = data[section1 + layout["party_count_offset"]]
    if count < 1 or count > GEN3["party_capacity"]:
        return 0
    score = 10
    for index in range(count):
        start = section1 + layout["party_offset"] + index * GEN3["mon_size"]
        try:
            details = parse_gen3_pokemon(data[start:start + GEN3["mon_size"]])
        except SaveError:
            continue
        if 1 <= details["species_id"] <= 412:
            score += 1
    return score if score > 10 else 0


def detect_gen3(data: bytes) -> Optional[Dict[str, Any]]:
    if len(data) < GEN3["sector_size"] * GEN3["sectors_per_slot"]:
        return None
    bases = [0]
    if len(data) >= GEN3["sector_size"] * GEN3["sectors_per_slot"] * 2:
        bases.append(GEN3["sector_size"] * GEN3["sectors_per_slot"])
    candidates = []
    for base in bases:
        slot = read_gen3_slot(data, base)
        if not slot:
            continue
        for layout in GEN3["layouts"]:
            score = gen3_layout_score(data, slot, layout)
            if score > 0:
                candidates.append({"score": score, "slot": slot, "layout": layout})
    candidates.sort(key=lambda item: (item["slot"]["counter"], item["score"]), reverse=True)
    return candidates[0] if candidates else None


@dataclass
class SaveModel:
    path: Path
    bytes: bytearray
    generation: int
    game: str
    label: str
    layout: Dict[str, Any]
    player_name: str
    slot: Optional[Dict[str, Any]] = None
    party: List[Dict[str, Any]] = field(default_factory=list)
    boxes: List[Dict[str, Any]] = field(default_factory=list)
    box_names: List[str] = field(default_factory=list)
    current_box: int = 0

    @property
    def name(self) -> str:
        return self.path.name

    def signature(self) -> Dict[str, Any]:
        blob = bytes(self.bytes)
        return {"size": len(blob), "sha256": sha256_hex(blob)}

    def trainer_id(self) -> int:
        """Return the player's visible Trainer ID (low 16 bits)."""
        try:
            data = self.bytes
            if self.generation == 1:
                if len(data) > 0x2606:
                    return ((data[0x2605] << 8) | data[0x2606]) & 0xFFFF
            elif self.generation == 2:
                if len(data) > 0x200A:
                    return ((data[0x2009] << 8) | data[0x200A]) & 0xFFFF
            elif self.generation == 3:
                return self._gen3_trainer_id()
        except Exception:
            return 0
        return 0

    def _gen3_trainer_id(self) -> int:
        SECTOR_SIGNATURE = 0x08012025
        SECTORS_PER_SLOT = 14
        data = bytes(self.bytes)
        best: dict[int, tuple[int, int]] = {}
        for base in (0, 0xE000):
            if base + 0x1000 * SECTORS_PER_SLOT > len(data):
                continue
            for i in range(SECTORS_PER_SLOT):
                off = base + i * 0x1000
                sig = int.from_bytes(data[off + 0xFF8: off + 0xFFC], "little")
                sid = int.from_bytes(data[off + 0xFF4: off + 0xFF6], "little")
                ctr = int.from_bytes(data[off + 0xFFC: off + 0x1000], "little")
                if sig != SECTOR_SIGNATURE or sid >= SECTORS_PER_SLOT:
                    continue
                cur = best.get(sid)
                if cur is None or ctr > cur[0]:
                    best[sid] = (ctr, off)
        entry = best.get(0)
        if entry is None:
            return 0
        off = entry[1]
        return int.from_bytes(data[off + 0x0A: off + 0x0C], "little") & 0xFFFF

    def badges_earned(self) -> int:
        """Return an 8-bit mask of earned region badges (Gen1/2/3 best-effort)."""
        try:
            data = self.bytes
            if self.generation == 1:
                if len(data) > 0x2602:
                    return data[0x2602] & 0xFF
            elif self.generation == 2:
                offset = 0x23E5 if (self.game or "").lower() == "pokemon_crystal" else 0x23E4
                if len(data) > offset:
                    return data[offset] & 0xFF
            elif self.generation == 3:
                return self._gen3_badges_mask()
        except Exception:
            return 0
        return 0

    def _gen3_badges_mask(self) -> int:
        """Read badges from Gen3 SaveBlock1 event flags. Returns 8-bit mask."""
        SECTOR_SIGNATURE = 0x08012025
        SECTORS_PER_SLOT = 14
        SAVEBLOCK1_START = 1
        data = bytes(self.bytes)
        # Choose, per section_id, the physical sector with highest counter across both slots
        best: dict[int, tuple[int, int]] = {}  # section_id -> (counter, offset)
        for base in (0, 0xE000):
            if base + 0x1000 * SECTORS_PER_SLOT > len(data):
                continue
            for i in range(SECTORS_PER_SLOT):
                off = base + i * 0x1000
                sig = int.from_bytes(data[off + 0xFF8: off + 0xFFC], "little")
                sid = int.from_bytes(data[off + 0xFF4: off + 0xFF6], "little")
                ctr = int.from_bytes(data[off + 0xFFC: off + 0x1000], "little")
                if sig != SECTOR_SIGNATURE or sid >= SECTORS_PER_SLOT:
                    continue
                cur = best.get(sid)
                if cur is None or ctr > cur[0]:
                    best[sid] = (ctr, off)
        block1 = bytearray()
        for sid in range(SAVEBLOCK1_START, SAVEBLOCK1_START + 4):
            entry = best.get(sid)
            if entry is None:
                return 0
            block1.extend(data[entry[1]: entry[1] + 0xF80])
        game = (self.game or "").lower()
        if "emerald" in game:
            flags_off = 0x1270
        elif "firered" in game or "leafgreen" in game:
            flags_off = 0xEE0
        else:
            flags_off = 0x1220
        if "firered" in game or "leafgreen" in game:
            badge_ids = list(range(0x820, 0x828))
        else:
            badge_ids = list(range(0x807, 0x80F))
        mask = 0
        for i, fid in enumerate(badge_ids):
            byte_idx = fid >> 3
            bit = fid & 7
            pos = flags_off + byte_idx
            if pos >= len(block1):
                continue
            if block1[pos] & (1 << bit):
                mask |= 1 << i
        return mask & 0xFF

    def refresh(self) -> None:
        logger.debug("Refreshing save model: path=%s generation=%s game=%s", self.path, self.generation, self.game)
        if self.generation == 1:
            self.party = self._parse_gen1_party()
            self.boxes = self._parse_gen1_boxes()
        elif self.generation == 2:
            self.party = self._parse_gen2_party()
            self.boxes = self._parse_gen2_boxes()
        elif self.generation == 3:
            self.party = self._parse_gen3_party()
            self.boxes = self._parse_gen3_boxes()
        else:
            raise SaveError(f"Geração não suportada: {self.generation}")
        logger.info(
            "Refresh complete: path=%s generation=%s party=%s boxes=%s current_box=%s",
            self.path,
            self.generation,
            len(self.party),
            len(self.boxes),
            self.current_box,
        )

    def write_to_disk(self) -> None:
        logger.info("Writing save to disk: path=%s size=%s", self.path, len(self.bytes))
        self.path.write_bytes(bytes(self.bytes))

    def pokemon_by_location(self, location: str) -> Optional[Dict[str, Any]]:
        for pokemon in self.party:
            if pokemon.get("location") == location:
                return pokemon
        for pokemon in self.boxes:
            if pokemon.get("location") == location:
                return pokemon
        return None

    def get_pokemon(self, source: str = "party") -> List[Dict[str, Any]]:
        if source == "party":
            return list(self.party)
        if source in ("boxes", "pc", "box"):
            return list(self.boxes)
        return []

    def _pokemon_move_entries(self, pokemon: Dict[str, Any]) -> List[Dict[str, Any]]:
        details = pokemon.get("move_details")
        if isinstance(details, list) and details:
            return [dict(move) for move in details if isinstance(move, dict) and move.get("move_id")]
        return [
            {"move_id": int(move_id), "source_generation": self.generation}
            for move_id in (pokemon.get("moves") or [])
            if int(move_id or 0)
        ]

    def export_payload(self, location: str) -> Dict[str, Any]:
        parsed = parse_location(location)
        pokemon = self.pokemon_by_location(location)
        if not pokemon:
            raise SaveError("Pokémon não encontrado.")
        if pokemon.get("is_egg"):
            raise SaveError("Ovos ainda não são suportados para troca real.")
        species_id = int(pokemon.get("species_id") or 0)
        if species_id <= 0:
            raise SaveError("Pokemon selecionado possui species_id invalido. Escolha outro slot.")
        national_dex_id = _resolve_national_dex_id(self.generation, species_id, pokemon)
        level = int(pokemon.get("level") or 0)
        # Box/PC entries in older generations may not carry a resolved level locally.
        # Keep payload valid for backend validation; enrichment can provide a more precise level.
        if level < 1:
            level = 1
        elif level > 100:
            level = 100
        if self.generation == 1:
            if parsed["kind"] == "party":
                mon, ot, nick = self._read_gen1_party_data(parsed["index"])
                raw_format = GEN1["party_format"]
            else:
                mon, ot, nick = self._read_gen1_box_data(parsed["box_index"], parsed["slot_index"])
                raw_format = GEN1["box_format"]
            raw = mon + ot + nick
            experience = (mon[0x0E] << 16) | (mon[0x0F] << 8) | mon[0x10]
        elif self.generation == 2:
            if parsed["kind"] == "party":
                mon, ot, nick = self._read_gen2_party_data(parsed["index"])
                raw_format = self.layout["party_format"]
                experience = (mon[0x08] << 16) | (mon[0x09] << 8) | mon[0x0A]
            else:
                mon, ot, nick = self._read_gen2_box_data(parsed["box_index"], parsed["slot_index"])
                raw_format = self.layout["box_format"]
                experience = (mon[0x08] << 16) | (mon[0x09] << 8) | mon[0x0A]
            raw = mon + ot + nick
        elif self.generation == 3:
            if parsed["kind"] == "party":
                mon = self._read_gen3_party_data(parsed["index"])
                raw_format = "gen3-party-v1"
            else:
                mon = self._read_gen3_box_data(parsed["box_index"], parsed["slot_index"])
                raw_format = "gen3-box-v1"
            raw = mon
            promoted = mon if parsed["kind"] == "party" else self._promote_gen3_box_to_party(mon, pokemon)
            secure = decrypt_gen3_secure(promoted)
            growth = GEN3["substruct_orders"][read_u32(promoted, 0) % 24][0] * 12
            experience = read_u32(secure, growth + 4)
        else:
            raise SaveError("Geração não suportada.")

        raw_b64 = base64.b64encode(raw).decode("ascii")
        display = pokemon.get("display_summary") or normalize_pokemon_display(pokemon)
        is_shiny = _pokemon_is_shiny(pokemon)
        experience_progress = _experience_progress_for_payload(national_dex_id, experience)
        logger.info(
            "Export payload: path=%s generation=%s location=%s species=%s source_kind=%s raw_format=%s raw_size=%s",
            self.path,
            self.generation,
            location,
            pokemon.get("species_name"),
            parsed["kind"],
            raw_format,
            len(raw),
        )
        return {
            "payload_version": 2,
            "generation": self.generation,
            "game": self.game,
            "source_generation": self.generation,
            "source_game": self.game,
            "target_generation": self.generation,
            "species_id": species_id,
            "species_name": pokemon.get("species_name", "Pokemon"),
            "types": pokemon.get("types", []),
            "level": level,
            "experience": experience,
            "experience_progress": experience_progress,
            "nickname": pokemon.get("nickname", pokemon.get("species_name", "")),
            "gender": pokemon.get("gender"),
            "ot_name": pokemon.get("ot_name", ""),
            "trainer_id": pokemon.get("trainer_id", 0),
            "held_item_id": pokemon.get("held_item_id"),
            "held_item_name": pokemon.get("held_item_name"),
            "held_item_category": pokemon.get("held_item_category"),
            "moves": pokemon.get("moves", []),
            "move_names": pokemon.get("move_names", []),
            "is_shiny": is_shiny,
            "raw_data_base64": raw_b64,
            "display_summary": display,
            "summary": {
                "species_id": species_id,
                "species_name": pokemon.get("species_name", "Pokemon"),
                "types": pokemon.get("types", []),
                "level": level,
                "experience": experience,
                "experience_progress": experience_progress,
                "nickname": pokemon.get("nickname", pokemon.get("species_name", "")),
                "gender": pokemon.get("gender"),
                "held_item_id": pokemon.get("held_item_id"),
                "held_item_name": pokemon.get("held_item_name"),
                "held_item_category": pokemon.get("held_item_category"),
                "moves": pokemon.get("moves", []),
                "move_names": pokemon.get("move_names", []),
                "is_shiny": is_shiny,
                "display_summary": display,
                "nature": pokemon.get("nature"),
                "ability": (
                    None if pokemon.get("ability_index") is None
                    else f"Index {pokemon['ability_index']}"
                ),
            },
            "canonical": {
                "source_generation": self.generation,
                "source_game": self.game,
                "species_national_id": national_dex_id if national_dex_id > 0 else species_id,
                "species_name": pokemon.get("species_name", "Pokemon"),
                "nickname": pokemon.get("nickname", pokemon.get("species_name", "")),
                "types": pokemon.get("types", []),
                "level": level,
                "experience": experience,
                "ot_name": pokemon.get("ot_name", ""),
                "trainer_id": pokemon.get("trainer_id", 0),
                "moves": self._pokemon_move_entries(pokemon),
                "held_item": {
                    "item_id": pokemon.get("held_item_id"),
                    "name": pokemon.get("held_item_name"),
                    "category": pokemon.get("held_item_category"),
                } if pokemon.get("held_item_id") else None,
                "nature": pokemon.get("nature"),
                "ability": (
                    None if pokemon.get("ability_index") is None
                    else f"Index {pokemon['ability_index']}"
                ),
                "metadata": {
                    "is_shiny": is_shiny,
                    "is_egg": bool(pokemon.get("is_egg")),
                    "gender": pokemon.get("gender"),
                    "source_species_id": species_id,
                    "source_species_id_space": "gen1_internal" if self.generation == 1 else ("national_dex" if self.generation == 2 else "gen3_internal"),
                    "experience_progress": experience_progress,
                },
                "species": {
                    "national_dex_id": national_dex_id if national_dex_id > 0 else species_id,
                    "source_species_id": species_id,
                    "source_species_id_space": "gen1_internal" if self.generation == 1 else ("national_dex" if self.generation == 2 else "gen3_internal"),
                    "name": pokemon.get("species_name", "Pokemon"),
                },
            },
            "raw": {"format": raw_format, "data_base64": raw_b64},
            "compatibility_report": preflight_report(True, self.generation),
            "metadata": {"format": raw_format, "source": "r36s-local-save", "location": location, "is_shiny": is_shiny, "gender": pokemon.get("gender")},
        }

    def _count_total_pokemon(self) -> int:
        return len(self.party) + len(self.boxes)

    def _restore_snapshot(self, snapshot: bytes) -> None:
        self.bytes = bytearray(snapshot)
        try:
            self.refresh()
        except Exception as exc:
            logger.exception("Failed to refresh after snapshot rollback: %s", exc)

    def deposit_party_to_pc(self, party_index: int) -> Dict[str, Any]:
        """Move o Pokemon da Party[party_index] para o primeiro slot livre do PC.

        Levanta SaveError quando a Party ficaria vazia ou o PC nao tem espaco.
        Retorna {"box_index", "slot_index", "species_name"}.
        Opera de forma atomica: em qualquer falha, restaura snapshot dos bytes.
        """
        if party_index < 0 or party_index >= len(self.party):
            raise SaveError("Slot da Party invalido.")
        if len(self.party) <= 1:
            raise SaveError("A Party nao pode ficar vazia. Adicione outro Pokemon antes de mover.")
        species_name = str(self.party[party_index].get("species_name") or "Pokemon")
        snapshot = bytes(self.bytes)
        before_total = self._count_total_pokemon()
        try:
            if self.generation == 1:
                box_index, slot_index = self._deposit_gen1_party_to_pc(party_index)
            elif self.generation == 2:
                box_index, slot_index = self._deposit_gen2_party_to_pc(party_index)
            elif self.generation == 3:
                box_index, slot_index = self._deposit_gen3_party_to_pc(party_index)
            else:
                raise SaveError(f"Geracao nao suportada para deposito: {self.generation}")
            self.refresh()
            after_total = self._count_total_pokemon()
            if after_total != before_total:
                raise SaveError(f"Inconsistencia pos-deposito: total mudou de {before_total} para {after_total}.")
        except Exception:
            self._restore_snapshot(snapshot)
            raise
        logger.info(
            "Deposit party[%s] -> box[%s]:slot[%s] (%s) total=%s",
            party_index,
            box_index,
            slot_index,
            species_name,
            after_total,
        )
        return {"box_index": box_index, "slot_index": slot_index, "species_name": species_name}

    def _sync_gen1_current_box_to_stored(self, box_index: int) -> None:
        if box_index != self.current_box:
            return
        if not (0 <= self.current_box < GEN1["box_count"]):
            return
        current = GEN1["current_box_data_offset"]
        stored = GEN1["stored_box_offsets"][self.current_box]
        size = GEN1["box_data_size"]
        self.bytes[stored:stored + size] = bytes(self.bytes[current:current + size])
        self.bytes[GEN1["checksum_offset"]] = gen1_checksum(self.bytes)

    def _sync_gen2_current_box_to_stored(self, box_index: int) -> None:
        if box_index != self.current_box:
            return
        if not (0 <= self.current_box < self.layout["box_count"]):
            return
        current = self.layout["current_box_data_offset"]
        stored = self.layout["stored_box_offsets"][self.current_box]
        size = 0x450
        self.bytes[stored:stored + size] = bytes(self.bytes[current:current + size])
        write_gen2_checksums(self.bytes, self.layout)

    def _find_empty_gen1_box_slot(self) -> Optional[tuple[int, int]]:
        for box_index in range(GEN1["box_count"]):
            count, _, _ = self._gen1_box_header(box_index)
            if count < GEN1["box_capacity"]:
                return box_index, count
        return None

    def _find_empty_gen2_box_slot(self) -> Optional[tuple[int, int]]:
        for box_index in range(self.layout["box_count"]):
            count, _, _ = self._gen2_box_header(box_index)
            if count < self.layout["box_capacity"]:
                return box_index, count
        return None

    def _find_empty_gen3_box_slot(self) -> Optional[tuple[int, int]]:
        for box_index in range(GEN3["box_count"]):
            for slot_index in range(GEN3["box_capacity"]):
                raw = self._read_gen3_box_data(box_index, slot_index)
                if not any(raw):
                    return box_index, slot_index
        return None

    def _deposit_gen1_party_to_pc(self, party_index: int) -> tuple[int, int]:
        target = self._find_empty_gen1_box_slot()
        if target is None:
            raise SaveError("PC sem espaco.")
        box_index, slot_index = target
        mon, ot, nick = self._read_gen1_party_data(party_index)
        truncated = mon[: GEN1["box_mon_size"]]
        # Increment box count + add species list + place terminator (do this before writing checksum)
        _, _, box_offset = self._gen1_box_header(box_index)
        old_count = int(self.bytes[box_offset])
        self.bytes[box_offset] = old_count + 1
        self.bytes[box_offset + 1 + (old_count + 1)] = 0xFF
        self._write_gen1_box_data(box_index, slot_index, truncated, ot, nick)
        self._sync_gen1_current_box_to_stored(box_index)
        self._compact_gen1_party(party_index)
        return box_index, slot_index

    def _deposit_gen2_party_to_pc(self, party_index: int) -> tuple[int, int]:
        target = self._find_empty_gen2_box_slot()
        if target is None:
            raise SaveError("PC sem espaco.")
        box_index, slot_index = target
        mon, ot, nick = self._read_gen2_party_data(party_index)
        truncated = mon[: self.layout["box_mon_size"]]
        _, _, box_offset = self._gen2_box_header(box_index)
        old_count = int(self.bytes[box_offset])
        self.bytes[box_offset] = old_count + 1
        self.bytes[box_offset + 1 + (old_count + 1)] = 0xFF
        self._write_gen2_box_data(box_index, slot_index, truncated, ot, nick)
        self._sync_gen2_current_box_to_stored(box_index)
        self._compact_gen2_party(party_index)
        return box_index, slot_index

    def _deposit_gen3_party_to_pc(self, party_index: int) -> tuple[int, int]:
        target = self._find_empty_gen3_box_slot()
        if target is None:
            raise SaveError("PC sem espaco.")
        box_index, slot_index = target
        raw = self._read_gen3_party_data(party_index)
        truncated = raw[: GEN3["box_mon_size"]]
        self._write_gen3_box_data(box_index, slot_index, truncated)
        self._compact_gen3_party(party_index)
        return box_index, slot_index

    def _compact_gen1_party(self, party_index: int) -> None:
        count = int(self.bytes[GEN1["party_offset"]])
        if count <= 0:
            return
        data_off = GEN1["data_offset"]
        ot_off = GEN1["ot_offset"]
        nick_off = GEN1["nick_offset"]
        mon_sz = GEN1["mon_size"]
        nm_sz = GEN1["name_size"]
        species_base = GEN1["party_offset"] + 1
        for j in range(party_index, count - 1):
            src = j + 1
            self.bytes[species_base + j] = self.bytes[species_base + src]
            self.bytes[data_off + j * mon_sz : data_off + (j + 1) * mon_sz] = bytes(
                self.bytes[data_off + src * mon_sz : data_off + (src + 1) * mon_sz]
            )
            self.bytes[ot_off + j * nm_sz : ot_off + (j + 1) * nm_sz] = bytes(
                self.bytes[ot_off + src * nm_sz : ot_off + (src + 1) * nm_sz]
            )
            self.bytes[nick_off + j * nm_sz : nick_off + (j + 1) * nm_sz] = bytes(
                self.bytes[nick_off + src * nm_sz : nick_off + (src + 1) * nm_sz]
            )
        last = count - 1
        self.bytes[species_base + last] = 0xFF
        self.bytes[data_off + last * mon_sz : data_off + (last + 1) * mon_sz] = b"\x00" * mon_sz
        self.bytes[ot_off + last * nm_sz : ot_off + (last + 1) * nm_sz] = b"\x00" * nm_sz
        self.bytes[nick_off + last * nm_sz : nick_off + (last + 1) * nm_sz] = b"\x00" * nm_sz
        self.bytes[GEN1["party_offset"]] = count - 1
        self.bytes[GEN1["checksum_offset"]] = gen1_checksum(self.bytes)

    def _compact_gen2_party(self, party_index: int) -> None:
        count = int(self.bytes[self.layout["party_offset"]])
        if count <= 0:
            return
        data_off = self.layout["data_offset"]
        ot_off = self.layout["ot_offset"]
        nick_off = self.layout["nick_offset"]
        mon_sz = self.layout["mon_size"]
        nm_sz = self.layout["name_size"]
        species_base = self.layout["party_offset"] + 1
        for j in range(party_index, count - 1):
            src = j + 1
            self.bytes[species_base + j] = self.bytes[species_base + src]
            self.bytes[data_off + j * mon_sz : data_off + (j + 1) * mon_sz] = bytes(
                self.bytes[data_off + src * mon_sz : data_off + (src + 1) * mon_sz]
            )
            self.bytes[ot_off + j * nm_sz : ot_off + (j + 1) * nm_sz] = bytes(
                self.bytes[ot_off + src * nm_sz : ot_off + (src + 1) * nm_sz]
            )
            self.bytes[nick_off + j * nm_sz : nick_off + (j + 1) * nm_sz] = bytes(
                self.bytes[nick_off + src * nm_sz : nick_off + (src + 1) * nm_sz]
            )
        last = count - 1
        self.bytes[species_base + last] = 0xFF
        self.bytes[data_off + last * mon_sz : data_off + (last + 1) * mon_sz] = b"\x00" * mon_sz
        self.bytes[ot_off + last * nm_sz : ot_off + (last + 1) * nm_sz] = b"\x00" * nm_sz
        self.bytes[nick_off + last * nm_sz : nick_off + (last + 1) * nm_sz] = b"\x00" * nm_sz
        self.bytes[self.layout["party_offset"]] = count - 1
        write_gen2_checksums(self.bytes, self.layout)

    def _compact_gen3_party(self, party_index: int) -> None:
        if not self.slot:
            raise SaveError("Slot Gen 3 nao detectado.")
        section_offsets = self.slot.get("section_offsets") or {}
        section1 = section_offsets.get(1)
        if section1 is None:
            raise SaveError("Save Gen 3 inválido: seção 1 ausente no slot ativo.")
        count_addr = section1 + self.layout["party_count_offset"]
        count = int(self.bytes[count_addr])
        if count <= 0:
            return
        base = section1 + self.layout["party_offset"]
        mon_sz = GEN3["mon_size"]
        for j in range(party_index, count - 1):
            src = j + 1
            self.bytes[base + j * mon_sz : base + (j + 1) * mon_sz] = bytes(
                self.bytes[base + src * mon_sz : base + (src + 1) * mon_sz]
            )
        last = count - 1
        self.bytes[base + last * mon_sz : base + (last + 1) * mon_sz] = b"\x00" * mon_sz
        self.bytes[count_addr] = count - 1
        write_u16(self.bytes, section1 + 0xFF6, gen3_sector_checksum(self.bytes, section1))

    def withdraw_box_to_party(self, box_index: int, slot_index: int) -> Dict[str, Any]:
        """Retira o Pokemon do PC[box_index][slot_index] para o primeiro slot livre da Party.

        Levanta SaveError quando a Party esta cheia ou o slot esta vazio.
        Retorna {"party_index", "species_name"}.
        """
        if self.generation == 1:
            party_capacity = GEN1["party_capacity"]
            party_count = int(self.bytes[GEN1["party_offset"]])
        elif self.generation == 2:
            party_capacity = self.layout["party_capacity"]
            party_count = int(self.bytes[self.layout["party_offset"]])
        elif self.generation == 3:
            party_capacity = GEN3["party_capacity"]
            if not self.slot:
                raise SaveError("Slot Gen 3 nao detectado.")
            section_offsets = self.slot.get("section_offsets") or {}
            section1 = section_offsets.get(1)
            if section1 is None:
                raise SaveError("Save Gen 3 inválido: seção 1 ausente no slot ativo.")
            party_count = int(self.bytes[section1 + self.layout["party_count_offset"]])
        else:
            raise SaveError(f"Geracao nao suportada para retirada: {self.generation}")
        if party_count >= party_capacity:
            raise SaveError("Party esta cheia. Mova um Pokemon para o PC antes de retirar.")
        target_pokemon = self.pokemon_by_location(f"box:{box_index}:{slot_index}")
        if not target_pokemon:
            raise SaveError("Slot do PC esta vazio.")
        species_name = str(target_pokemon.get("species_name") or "Pokemon")
        snapshot = bytes(self.bytes)
        before_total = self._count_total_pokemon()
        try:
            if self.generation == 1:
                self._withdraw_gen1_box_to_party(box_index, slot_index, party_count)
            elif self.generation == 2:
                self._withdraw_gen2_box_to_party(box_index, slot_index, party_count)
            else:
                self._withdraw_gen3_box_to_party(box_index, slot_index, party_count)
            self.refresh()
            after_total = self._count_total_pokemon()
            if after_total != before_total:
                raise SaveError(f"Inconsistencia pos-retirada: total mudou de {before_total} para {after_total}.")
        except Exception:
            self._restore_snapshot(snapshot)
            raise
        logger.info(
            "Withdraw box[%s]:slot[%s] -> party[%s] (%s) total=%s",
            box_index,
            slot_index,
            party_count,
            species_name,
            after_total,
        )
        return {"party_index": party_count, "species_name": species_name}

    def _compact_gen1_box(self, box_index: int, slot_index: int) -> None:
        _, _, offset = self._gen1_box_header(box_index)
        count = int(self.bytes[offset])
        if count <= 0:
            return
        mon_sz = GEN1["box_mon_size"]
        nm_sz = GEN1["name_size"]
        species_base = offset + 1
        data_base = offset + 0x16
        ot_base = offset + GEN1["box_ot_offset"]
        nick_base = offset + GEN1["box_nick_offset"]
        for j in range(slot_index, count - 1):
            src = j + 1
            self.bytes[species_base + j] = self.bytes[species_base + src]
            self.bytes[data_base + j * mon_sz : data_base + (j + 1) * mon_sz] = bytes(
                self.bytes[data_base + src * mon_sz : data_base + (src + 1) * mon_sz]
            )
            self.bytes[ot_base + j * nm_sz : ot_base + (j + 1) * nm_sz] = bytes(
                self.bytes[ot_base + src * nm_sz : ot_base + (src + 1) * nm_sz]
            )
            self.bytes[nick_base + j * nm_sz : nick_base + (j + 1) * nm_sz] = bytes(
                self.bytes[nick_base + src * nm_sz : nick_base + (src + 1) * nm_sz]
            )
        last = count - 1
        self.bytes[species_base + last] = 0xFF
        self.bytes[data_base + last * mon_sz : data_base + (last + 1) * mon_sz] = b"\x00" * mon_sz
        self.bytes[ot_base + last * nm_sz : ot_base + (last + 1) * nm_sz] = b"\x00" * nm_sz
        self.bytes[nick_base + last * nm_sz : nick_base + (last + 1) * nm_sz] = b"\x00" * nm_sz
        self.bytes[offset] = count - 1
        self.bytes[GEN1["checksum_offset"]] = gen1_checksum(self.bytes)
        self._sync_gen1_current_box_to_stored(box_index)

    def _compact_gen2_box(self, box_index: int, slot_index: int) -> None:
        _, _, offset = self._gen2_box_header(box_index)
        count = int(self.bytes[offset])
        if count <= 0:
            return
        mon_sz = self.layout["box_mon_size"]
        nm_sz = self.layout["name_size"]
        species_base = offset + 1
        data_base = offset + 0x16
        ot_base = offset + self.layout["box_ot_offset"]
        nick_base = offset + self.layout["box_nick_offset"]
        for j in range(slot_index, count - 1):
            src = j + 1
            self.bytes[species_base + j] = self.bytes[species_base + src]
            self.bytes[data_base + j * mon_sz : data_base + (j + 1) * mon_sz] = bytes(
                self.bytes[data_base + src * mon_sz : data_base + (src + 1) * mon_sz]
            )
            self.bytes[ot_base + j * nm_sz : ot_base + (j + 1) * nm_sz] = bytes(
                self.bytes[ot_base + src * nm_sz : ot_base + (src + 1) * nm_sz]
            )
            self.bytes[nick_base + j * nm_sz : nick_base + (j + 1) * nm_sz] = bytes(
                self.bytes[nick_base + src * nm_sz : nick_base + (src + 1) * nm_sz]
            )
        last = count - 1
        self.bytes[species_base + last] = 0xFF
        self.bytes[data_base + last * mon_sz : data_base + (last + 1) * mon_sz] = b"\x00" * mon_sz
        self.bytes[ot_base + last * nm_sz : ot_base + (last + 1) * nm_sz] = b"\x00" * nm_sz
        self.bytes[nick_base + last * nm_sz : nick_base + (last + 1) * nm_sz] = b"\x00" * nm_sz
        self.bytes[offset] = count - 1
        write_gen2_checksums(self.bytes, self.layout)
        self._sync_gen2_current_box_to_stored(box_index)

    def _level_from_experience_gen1(self, species_id: int, experience: int) -> int:
        return _level_from_experience(1, species_id, experience)

    def _level_from_experience_gen2(self, species_id: int, experience: int) -> int:
        return _level_from_experience(2, species_id, experience)

    def _withdraw_gen1_box_to_party(self, box_index: int, slot_index: int, party_index: int) -> None:
        box_mon, ot, nick = self._read_gen1_box_data(box_index, slot_index)
        experience = (box_mon[0x0E] << 16) | (box_mon[0x0F] << 8) | box_mon[0x10]
        level = self._level_from_experience_gen1(box_mon[0], experience)
        party_mon = bytearray(GEN1["mon_size"])
        party_mon[: GEN1["box_mon_size"]] = box_mon
        party_mon[0x21] = level
        party_count = int(self.bytes[GEN1["party_offset"]])
        self.bytes[GEN1["party_offset"]] = party_count + 1
        self.bytes[GEN1["party_offset"] + 1 + (party_count + 1)] = 0xFF
        self._write_gen1_party_data(party_index, bytes(party_mon), ot, nick)
        self._compact_gen1_box(box_index, slot_index)

    def _withdraw_gen2_box_to_party(self, box_index: int, slot_index: int, party_index: int) -> None:
        box_mon, ot, nick = self._read_gen2_box_data(box_index, slot_index)
        experience = (box_mon[0x08] << 16) | (box_mon[0x09] << 8) | box_mon[0x0A]
        level = self._level_from_experience_gen2(box_mon[0], experience)
        party_mon = bytearray(self.layout["mon_size"])
        party_mon[: self.layout["box_mon_size"]] = box_mon
        party_mon[0x1F] = level
        party_count = int(self.bytes[self.layout["party_offset"]])
        self.bytes[self.layout["party_offset"]] = party_count + 1
        self.bytes[self.layout["party_offset"] + 1 + (party_count + 1)] = 0xFF
        self._write_gen2_party_data(party_index, bytes(party_mon), ot, nick)
        self._compact_gen2_box(box_index, slot_index)

    def _withdraw_gen3_box_to_party(self, box_index: int, slot_index: int, party_index: int) -> None:
        raw = self._read_gen3_box_data(box_index, slot_index)
        target = self.pokemon_by_location(f"box:{box_index}:{slot_index}") or {}
        promoted = self._promote_gen3_box_to_party(raw, target)
        self._write_gen3_party_data(party_index, promoted)
        if not self.slot:
            raise SaveError("Slot Gen 3 nao detectado.")
        section_offsets = self.slot.get("section_offsets") or {}
        section1 = section_offsets.get(1)
        if section1 is None:
            raise SaveError("Save Gen 3 inválido: seção 1 ausente no slot ativo.")
        count_addr = section1 + self.layout["party_count_offset"]
        self.bytes[count_addr] = int(self.bytes[count_addr]) + 1
        write_u16(self.bytes, section1 + 0xFF6, gen3_sector_checksum(self.bytes, section1))
        # Clear box slot (Gen 3 boxes don't compact)
        empty = b"\x00" * GEN3["box_mon_size"]
        self._write_gen3_box_data(box_index, slot_index, empty)

    def apply_payload(
        self,
        location: str,
        payload: Dict[str, Any],
        trade_evolution: Optional[Dict[str, Any]] = None,
        cancel_trade_evolution: bool = False,
        resolved_moves: Optional[Dict[int, int]] = None,
    ) -> Dict[str, Any]:
        parsed = parse_location(location)
        payload_generation = int(payload.get("generation", 0))
        canonical_payload = payload.get("canonical") if isinstance(payload.get("canonical"), dict) else None
        is_cross_generation = payload_generation != self.generation
        if is_cross_generation:
            if not canonical_payload:
                raise SaveError("Payload cross-generation sem dados canonical.")
            if parsed["kind"] != "party":
                raise SaveError("Cross-generation no R36S exige destino local na Party.")
            try:
                _ensure_backend_import_path()
                from canonical import CanonicalPokemon
                from converters import get_converter
                from parsers import Gen1Parser, Gen2Parser, Gen3Parser
            except Exception as exc:
                raise SaveError(f"Conversores cross-generation indisponiveis localmente: {exc}") from exc
            try:
                canonical = CanonicalPokemon.from_dict(canonical_payload)
            except Exception as exc:
                raise SaveError(f"Canonical invalido para cross-generation: {exc}") from exc
            if self.generation == 1:
                national_id = int(getattr(canonical.species, "national_dex_id", 0) or 0)
                if national_id < 1 or national_id > 151:
                    raise SaveError(
                        f"Pokemon National Dex #{national_id} nao existe na Gen 1 e nao pode ser transferido para esse save."
                    )
            parser = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser}.get(self.generation)
            if parser is None:
                raise SaveError("Geração de destino não suportada para conversão.")
            # Pre-evoluir o canonical (se houver trade evolution) antes do converter escrever.
            # Isto resolve o bug de nicknames trocados em cross-gen: o converter+parser
            # cuidam de re-encodar nickname/species no charmap correto da gen destino.
            applied_evolution: Optional[Dict[str, Any]] = None
            if (
                trade_evolution
                and bool(trade_evolution.get("evolved"))
                and not cancel_trade_evolution
            ):
                try:
                    from data.species import native_to_national
                    evo_gen = int(trade_evolution.get("generation") or canonical.source_generation or 0)
                    target_native = int(trade_evolution.get("target_species_id") or 0)
                    target_national = int(native_to_national(evo_gen, target_native) or 0) if target_native else 0
                except Exception as exc:
                    logger.warning("Cross-gen evolution lookup failed: %s", exc)
                    target_national = 0
                source_name = str(trade_evolution.get("source_name") or "")
                target_name = str(trade_evolution.get("target_name") or "")
                if target_national > 0 and target_name:
                    old_species_name = getattr(canonical.species, "name", "") or ""
                    canonical.species.national_dex_id = target_national
                    canonical.species.name = target_name
                    if trade_evolution.get("consumed_item_id"):
                        canonical.held_item = None
                    nick_match = nickname_matches_species(canonical.nickname or "", old_species_name) or \
                        nickname_matches_species(canonical.nickname or "", source_name)
                    if nick_match:
                        canonical.nickname = target_name.upper()
                    applied_evolution = {
                        "evolved": True,
                        "source_name": source_name or old_species_name,
                        "target_name": target_name,
                        "generation": self.generation,
                        "source_species_id": trade_evolution.get("source_species_id"),
                        "target_species_id": target_national,
                    }
                    logger.info("Cross-gen pre-evolved canonical: %s -> %s", source_name, target_name)
            try:
                with tempfile.TemporaryDirectory(prefix="pokecable_xgen_") as tmpdir:
                    tmp_path = Path(tmpdir) / f"trade{self.path.suffix or '.sav'}"
                    tmp_path.write_bytes(bytes(self.bytes))
                    target_parser = parser()
                    target_parser.load(tmp_path)
                    converter = get_converter(int(canonical.source_generation), self.generation)
                    converter.apply_to_save(
                        target_parser,
                        location,
                        canonical,
                        policy="auto_retrocompat",
                        resolved_moves=resolved_moves,
                    )
                    target_parser.save(tmp_path)
                    self.bytes = bytearray(tmp_path.read_bytes())
                if applied_evolution is not None:
                    evolution = applied_evolution
                else:
                    evolution = self._apply_trade_evolution_decision(parsed, trade_evolution or {}, cancel_trade_evolution)
                self.refresh()
                result = self.pokemon_by_location(location) or {}
                if evolution:
                    result["trade_evolution"] = evolution
                logger.info(
                    "Apply payload complete (cross-generation): target=%s result=%s evolution=%s",
                    location,
                    result.get("display_summary"),
                    evolution,
                )
                return result
            except SaveError:
                raise
            except Exception as exc:
                raise SaveError(f"Falha ao converter/aplicar Pokemon cross-generation: {exc}") from exc
        raw_format = str(payload.get("raw", {}).get("format") or payload.get("metadata", {}).get("format") or "")
        source_kind = "box" if "-box-" in raw_format else "party" if "-party-" in raw_format else ""
        if source_kind not in ("party", "box"):
            raise SaveError("Payload sem formato de party reconhecido.")
        raw_b64 = payload.get("raw_data_base64") or payload.get("raw", {}).get("data_base64")
        if not raw_b64:
            raise SaveError("Payload same-generation sem raw data.")
        raw = base64.b64decode(raw_b64)
        logger.info(
            "Apply payload: path=%s generation=%s target=%s source_kind=%s raw_format=%s raw_size=%s species=%s",
            self.path,
            self.generation,
            location,
            source_kind,
            raw_format,
            len(raw),
            payload.get("species_name") or payload.get("nickname"),
        )
        if self.generation == 1:
            self._apply_gen1_payload(parsed, source_kind, raw)
        elif self.generation == 2:
            self._apply_gen2_payload(parsed, source_kind, raw)
        elif self.generation == 3:
            self._apply_gen3_payload(parsed, source_kind, raw, payload)
        else:
            raise SaveError("Geração não suportada.")
        evolution = self._apply_trade_evolution_decision(parsed, trade_evolution or {}, cancel_trade_evolution)
        self.refresh()
        result = self.pokemon_by_location(location) or {}
        if evolution:
            result["trade_evolution"] = evolution
        logger.info(
            "Apply payload complete: target=%s result=%s evolution=%s",
            location,
            result.get("display_summary"),
            evolution,
        )
        return result

    def target_requires_box_promotion_block(self, target_location: str, peer_payload: Dict[str, Any]) -> bool:
        parsed = parse_location(target_location)
        raw_format = str(peer_payload.get("raw", {}).get("format") or peer_payload.get("metadata", {}).get("format") or "")
        source_kind = "box" if "-box-" in raw_format else "party" if "-party-" in raw_format else ""
        return parsed["kind"] == "party" and source_kind == "box"

    def _apply_trade_evolution_decision(
        self,
        parsed: Dict[str, Any],
        evolution: Dict[str, Any],
        cancel_trade_evolution: bool,
    ) -> Optional[Dict[str, Any]]:
        if not evolution or not evolution.get("evolved"):
            return None
        if cancel_trade_evolution:
            return {
                **evolution,
                "evolved": False,
                "cancelled": True,
                "reason": "cancelled_by_user",
            }
        target_id = int(evolution.get("target_species_id") or 0)
        consume_item = bool(evolution.get("consumed_item_id"))
        if target_id <= 0:
            raise SaveError("API retornou evolução sem target_species_id válido.")
        source_name = str(evolution.get("source_name") or "")
        target_name = str(evolution.get("target_name") or "")
        if self.generation == 1:
            mon, ot, nick = (
                self._read_gen1_party_data(parsed["index"])
                if parsed["kind"] == "party"
                else self._read_gen1_box_data(parsed["box_index"], parsed["slot_index"])
            )
            updated = bytearray(mon)
            updated[0] = target_id
            if source_name and target_name and nickname_matches_species(decode_gbc_text(nick), source_name):
                nick = encode_gbc_text(target_name.upper(), GEN1["name_size"])
            if parsed["kind"] == "party":
                self._write_gen1_party_data(parsed["index"], bytes(updated), ot, nick)
            else:
                self._write_gen1_box_data(parsed["box_index"], parsed["slot_index"], bytes(updated), ot, nick)
        elif self.generation == 2:
            mon, ot, nick = (
                self._read_gen2_party_data(parsed["index"])
                if parsed["kind"] == "party"
                else self._read_gen2_box_data(parsed["box_index"], parsed["slot_index"])
            )
            updated = bytearray(mon)
            updated[0] = target_id
            if consume_item and len(updated) > 1:
                updated[1] = 0
            if source_name and target_name and nickname_matches_species(decode_gbc_text(nick), source_name):
                nick = encode_gbc_text(target_name.upper(), self.layout["name_size"])
            if parsed["kind"] == "party":
                self._write_gen2_party_data(parsed["index"], bytes(updated), ot, nick)
            else:
                self._write_gen2_box_data(parsed["box_index"], parsed["slot_index"], bytes(updated), ot, nick)
        elif self.generation == 3:
            raw = (
                self._read_gen3_party_data(parsed["index"])
                if parsed["kind"] == "party"
                else self._read_gen3_box_data(parsed["box_index"], parsed["slot_index"])
            )
            updated = bytearray(set_gen3_raw_species(raw, target_id))
            if consume_item:
                secure = decrypt_gen3_secure(updated)
                growth = GEN3["substruct_orders"][read_u32(updated, 0) % 24][0] * 12
                write_u16(secure, growth + 2, 0)
                write_u16(updated, 0x1C, gen3_box_checksum(secure))
                encrypt_gen3_secure(updated, secure)
            if source_name and target_name and nickname_matches_species(decode_gen3_text(updated[0x08:0x12]), source_name):
                updated[0x08:0x12] = encode_gen3_text(target_name.upper(), 10)
            updated = bytes(updated)
            if parsed["kind"] == "party":
                self._write_gen3_party_data(parsed["index"], updated)
            else:
                self._write_gen3_box_data(parsed["box_index"], parsed["slot_index"], updated)
        else:
            return None

        return evolution

    def _parse_gen1_party(self) -> List[Dict[str, Any]]:
        party = []
        count = int(self.bytes[GEN1["party_offset"]])
        for index in range(count):
            mon, ot, nick = self._read_gen1_party_data(index)
            species_id = int(mon[0])
            nickname = decode_gbc_text(nick)
            species_name = safe_species_name(species_id, nickname)
            move_details = []
            for offset, move_id in enumerate(mon[0x08:0x0C]):
                if move_id:
                    pp_byte = mon[0x1D + offset]
                    pp_ups = (pp_byte >> 6) & 0x03
                    move_details.append(
                        {
                            "move_id": int(move_id),
                            "pp": int(pp_byte & 0x3F),
                            "max_pp": int(default_move_pp(move_id, 1, pp_ups)),
                            "pp_ups": int(pp_ups),
                            "source_generation": 1,
                        }
                    )
            pokemon = {
                "location": f"party:{index}",
                "source": "party",
                "index": index,
                "generation": 1,
                "game": self.game,
                "source_generation": 1,
                "source_game": self.game,
                "species_id": species_id,
                "species_name": species_name,
                "types": [],
                "level": int(mon[0x21]),
                "experience": (mon[0x0E] << 16) | (mon[0x0F] << 8) | mon[0x10],
                "nickname": nickname or species_name,
                "ot_name": decode_gbc_text(ot),
                "trainer_id": (mon[0x0C] << 8) | mon[0x0D],
                "moves": [move for move in mon[0x08:0x0C] if move],
                "move_details": move_details,
                "is_egg": False,
                "is_shiny": _legacy_shiny_from_mon(mon, 0x1B),
            }
            pokemon["display_summary"] = normalize_pokemon_display(pokemon)
            party.append(pokemon)
        return party

    def _parse_gen1_boxes(self) -> List[Dict[str, Any]]:
        boxes = []
        self.current_box = int(self.bytes[GEN1["current_box_offset"]] & 0x7F)
        self.box_names = [f"Box {index + 1}" for index in range(GEN1["box_count"])]
        for box_index in range(GEN1["box_count"]):
            count, _, offset = self._gen1_box_header(box_index)
            for slot_index in range(count):
                mon, ot, nick = self._read_gen1_box_data(box_index, slot_index)
                species_id = int(mon[0])
                nickname = decode_gbc_text(nick)
                species_name = safe_species_name(species_id, nickname)
                experience = (mon[0x0E] << 16) | (mon[0x0F] << 8) | mon[0x10]
                move_details = []
                for offset, move_id in enumerate(mon[0x08:0x0C]):
                    if move_id:
                        pp_byte = mon[0x1D + offset]
                        pp_ups = (pp_byte >> 6) & 0x03
                        move_details.append(
                            {
                                "move_id": int(move_id),
                                "pp": int(pp_byte & 0x3F),
                                "max_pp": int(default_move_pp(move_id, 1, pp_ups)),
                                "pp_ups": int(pp_ups),
                                "source_generation": 1,
                            }
                        )
                pokemon = {
                    "location": f"box:{box_index}:{slot_index}",
                    "source": "boxes",
                    "generation": 1,
                    "game": self.game,
                    "source_generation": 1,
                    "source_game": self.game,
                    "species_id": species_id,
                    "species_name": species_name,
                    "types": [],
                    "level": self._level_from_experience_gen1(species_id, experience),
                    "experience": experience,
                    "nickname": nickname or species_name,
                    "ot_name": decode_gbc_text(ot),
                    "trainer_id": (mon[0x0C] << 8) | mon[0x0D] if len(mon) > 0x0D else 0,
                    "moves": [move for move in mon[0x08:0x0C] if move],
                    "move_details": move_details,
                    "is_egg": False,
                    "is_shiny": _legacy_shiny_from_mon(mon, 0x1B),
                    "box_index": box_index,
                    "slot_index": slot_index,
                    "box_name": self.box_names[box_index],
                }
                pokemon["display_summary"] = normalize_pokemon_display(pokemon)
                boxes.append(pokemon)
        return boxes

    def _parse_gen2_party(self) -> List[Dict[str, Any]]:
        party = []
        count = int(self.bytes[self.layout["party_offset"]])
        for index in range(count):
            mon, ot, nick = self._read_gen2_party_data(index)
            species_entry = int(self.bytes[self.layout["party_offset"] + 1 + index])
            species_id = int(mon[0])
            nickname = decode_gbc_text(nick)
            is_egg = species_entry == 0xFD
            species_name = "Egg" if is_egg else safe_species_name(species_id, nickname)
            move_details = []
            for offset, move_id in enumerate(mon[0x02:0x06]):
                if move_id:
                    pp_byte = mon[0x17 + offset]
                    pp_ups = (pp_byte >> 6) & 0x03
                    move_details.append(
                        {
                            "move_id": int(move_id),
                            "pp": int(pp_byte & 0x3F),
                            "max_pp": int(default_move_pp(move_id, 2, pp_ups)),
                            "pp_ups": int(pp_ups),
                            "source_generation": 2,
                        }
                    )
            pokemon = {
                "location": f"party:{index}",
                "source": "party",
                "index": index,
                "generation": 2,
                "game": self.game,
                "source_generation": 2,
                "source_game": self.game,
                "species_id": species_id,
                "species_name": species_name,
                "types": [],
                "level": int(mon[0x1F]),
                "experience": (mon[0x08] << 16) | (mon[0x09] << 8) | mon[0x0A],
                "nickname": nickname or species_name,
                "ot_name": decode_gbc_text(ot),
                "trainer_id": (mon[0x06] << 8) | mon[0x07],
                "held_item_id": int(mon[0x01]) or None,
                "moves": [move for move in mon[0x02:0x06] if move],
                "move_details": move_details,
                "is_egg": is_egg,
                "is_shiny": False if is_egg else _legacy_shiny_from_mon(mon, 0x15),
                "gender": None if is_egg else gender_from_gen2_attack_dv(species_id, mon[0x15] >> 4),
            }
            pokemon["display_summary"] = normalize_pokemon_display(pokemon)
            party.append(pokemon)
        return party

    def _parse_gen2_boxes(self) -> List[Dict[str, Any]]:
        boxes = []
        self.current_box = int(self.bytes[self.layout["current_box_offset"]] & 0x0F)
        self.box_names = []
        for index in range(self.layout["box_count"]):
            start = self.layout["box_names_offset"] + index * self.layout["box_name_size"]
            name = decode_gbc_text(self.bytes[start:start + self.layout["box_name_size"]]) or f"Box {index + 1}"
            self.box_names.append(name)

        for box_index in range(self.layout["box_count"]):
            count, _, _ = self._gen2_box_header(box_index)
            for slot_index in range(count):
                mon, ot, nick = self._read_gen2_box_data(box_index, slot_index)
                species_id = int(mon[0])
                nickname = decode_gbc_text(nick)
                species_name = safe_species_name(species_id, nickname)
                experience = (mon[0x08] << 16) | (mon[0x09] << 8) | mon[0x0A]
                move_details = []
                for offset, move_id in enumerate(mon[0x02:0x06]):
                    if move_id:
                        pp_byte = mon[0x17 + offset]
                        pp_ups = (pp_byte >> 6) & 0x03
                        move_details.append(
                            {
                                "move_id": int(move_id),
                                "pp": int(pp_byte & 0x3F),
                                "max_pp": int(default_move_pp(move_id, 2, pp_ups)),
                                "pp_ups": int(pp_ups),
                                "source_generation": 2,
                            }
                        )
                pokemon = {
                    "location": f"box:{box_index}:{slot_index}",
                    "source": "boxes",
                    "generation": 2,
                    "game": self.game,
                    "source_generation": 2,
                    "source_game": self.game,
                    "species_id": species_id,
                    "species_name": species_name,
                    "types": [],
                    "level": self._level_from_experience_gen2(species_id, experience),
                    "experience": experience,
                    "nickname": nickname or species_name,
                    "ot_name": decode_gbc_text(ot),
                    "trainer_id": (mon[0x06] << 8) | mon[0x07] if len(mon) > 0x07 else 0,
                    "held_item_id": int(mon[0x01]) or None,
                    "moves": [move for move in mon[0x02:0x06] if move],
                    "move_details": move_details,
                    "is_egg": False,
                    "is_shiny": _legacy_shiny_from_mon(mon, 0x15),
                    "gender": gender_from_gen2_attack_dv(species_id, mon[0x15] >> 4),
                    "box_index": box_index,
                    "slot_index": slot_index,
                    "box_name": self.box_names[box_index],
                }
                pokemon["display_summary"] = normalize_pokemon_display(pokemon)
                boxes.append(pokemon)
        return boxes

    def _parse_gen3_party(self) -> List[Dict[str, Any]]:
        if not self.slot:
            raise SaveError("Slot Gen 3 não detectado.")
        section_offsets = self.slot.get("section_offsets") or {}
        section1 = section_offsets.get(1)
        if section1 is None:
            raise SaveError("Save Gen 3 inválido: seção 1 ausente no slot ativo.")
        count = int(self.bytes[section1 + self.layout["party_count_offset"]])
        party = []
        for index in range(count):
            raw = self._read_gen3_party_data(index)
            details = parse_gen3_pokemon(raw)
            secure = decrypt_gen3_secure(raw)
            growth = GEN3["substruct_orders"][read_u32(raw, 0) % 24][0] * 12
            attacks = GEN3["substruct_orders"][read_u32(raw, 0) % 24][1] * 12
            pp_bonuses = secure[growth + 8]
            move_details = []
            for slot in range(4):
                move_id = int.from_bytes(secure[attacks + slot * 2:attacks + slot * 2 + 2], "little")
                if move_id:
                    pp_ups = (pp_bonuses >> (slot * 2)) & 0x03
                    move_details.append(
                        {
                            "move_id": move_id,
                            "pp": int(secure[attacks + 8 + slot]),
                            "max_pp": int(default_move_pp(move_id, 3, pp_ups)),
                            "pp_ups": int(pp_ups),
                            "source_generation": 3,
                        }
                    )
            pokemon = {
                "location": f"party:{index}",
                "source": "party",
                "index": index,
                "generation": 3,
                "game": self.game,
                "source_generation": 3,
                "source_game": self.game,
                "species_id": details["species_id"],
                "species_name": details["species_name"],
                "types": details["types"],
                "level": details["level"],
                "nickname": details["nickname"],
                "ot_name": details["ot_name"],
                "trainer_id": details["trainer_id"],
                "moves": details["moves"],
                "move_details": move_details,
                "held_item_id": details["held_item_id"],
                "nature": details["nature"],
                "ability_index": details["ability_index"],
                "experience": details["experience"],
                "is_egg": details["is_egg"],
                "is_shiny": details["is_shiny"],
                "gender": details.get("gender"),
                "personality": details.get("personality"),
            }
            pokemon["display_summary"] = normalize_pokemon_display(pokemon)
            party.append(pokemon)
        return party

    def _parse_gen3_boxes(self) -> List[Dict[str, Any]]:
        if not self.slot:
            raise SaveError("Slot Gen 3 não detectado.")
        boxes = []
        self.box_names = []
        self.current_box = 0
        buffer = self._gen3_pc_buffer()
        for box_index in range(GEN3["box_count"]):
            name_offset = GEN3["pc_buffer_names_offset"] + box_index * GEN3["box_name_size"]
            box_name = decode_gen3_text(buffer[name_offset:name_offset + GEN3["box_name_size"]]) or f"Box {box_index + 1}"
            self.box_names.append(box_name)
            for slot_index in range(GEN3["box_capacity"]):
                raw = self._read_gen3_box_data(box_index, slot_index)
                if not any(raw):
                    continue
                try:
                    details = parse_gen3_box_pokemon(raw)
                except SaveError:
                    continue
                if details["species_id"] == 0:
                    continue
                secure = decrypt_gen3_secure(raw)
                growth = GEN3["substruct_orders"][read_u32(raw, 0) % 24][0] * 12
                attacks = GEN3["substruct_orders"][read_u32(raw, 0) % 24][1] * 12
                pp_bonuses = secure[growth + 8]
                move_details = []
                for slot in range(4):
                    move_id = int.from_bytes(secure[attacks + slot * 2:attacks + slot * 2 + 2], "little")
                    if move_id:
                        pp_ups = (pp_bonuses >> (slot * 2)) & 0x03
                        move_details.append(
                            {
                                "move_id": move_id,
                                "pp": int(secure[attacks + 8 + slot]),
                                "max_pp": int(default_move_pp(move_id, 3, pp_ups)),
                                "pp_ups": int(pp_ups),
                                "source_generation": 3,
                            }
                        )
                pokemon = {
                    "location": f"box:{box_index}:{slot_index}",
                    "source": "boxes",
                    "generation": 3,
                    "game": self.game,
                    "source_generation": 3,
                    "source_game": self.game,
                    "species_id": details["species_id"],
                    "species_name": details["species_name"],
                    "types": details["types"],
                    "level": details["level"],
                    "nickname": details["nickname"],
                    "ot_name": details["ot_name"],
                    "trainer_id": details["trainer_id"],
                    "moves": details["moves"],
                    "move_details": move_details,
                    "held_item_id": details["held_item_id"],
                    "nature": details["nature"],
                    "ability_index": details["ability_index"],
                    "experience": details["experience"],
                    "is_egg": details["is_egg"],
                    "is_shiny": details["is_shiny"],
                    "gender": details.get("gender"),
                    "personality": details.get("personality"),
                    "box_index": box_index,
                    "slot_index": slot_index,
                    "box_name": box_name,
                }
                pokemon["display_summary"] = normalize_pokemon_display(pokemon)
                boxes.append(pokemon)
        return boxes

    def _read_gen1_party_data(self, index: int) -> tuple[bytes, bytes, bytes]:
        mon_start = GEN1["data_offset"] + index * GEN1["mon_size"]
        ot_start = GEN1["ot_offset"] + index * GEN1["name_size"]
        nick_start = GEN1["nick_offset"] + index * GEN1["name_size"]
        return (
            bytes(self.bytes[mon_start:mon_start + GEN1["mon_size"]]),
            bytes(self.bytes[ot_start:ot_start + GEN1["name_size"]]),
            bytes(self.bytes[nick_start:nick_start + GEN1["name_size"]]),
        )

    def _gen1_box_header(self, box_index: int) -> tuple[int, int, int]:
        offset = GEN1["current_box_data_offset"] if box_index == self.current_box else GEN1["stored_box_offsets"][box_index]
        count = int(self.bytes[offset])
        species_start = offset + 1
        return count, species_start, offset

    def _read_gen1_box_data(self, box_index: int, slot_index: int) -> tuple[bytes, bytes, bytes]:
        _, _, offset = self._gen1_box_header(box_index)
        mon_start = offset + 0x16 + slot_index * GEN1["box_mon_size"]
        ot_start = offset + GEN1["box_ot_offset"] + slot_index * GEN1["name_size"]
        nick_start = offset + GEN1["box_nick_offset"] + slot_index * GEN1["name_size"]
        return (
            bytes(self.bytes[mon_start:mon_start + GEN1["box_mon_size"]]),
            bytes(self.bytes[ot_start:ot_start + GEN1["name_size"]]),
            bytes(self.bytes[nick_start:nick_start + GEN1["name_size"]]),
        )

    def _write_gen1_party_data(self, index: int, mon: bytes, ot: bytes, nick: bytes) -> None:
        mon_start = GEN1["data_offset"] + index * GEN1["mon_size"]
        ot_start = GEN1["ot_offset"] + index * GEN1["name_size"]
        nick_start = GEN1["nick_offset"] + index * GEN1["name_size"]
        self.bytes[GEN1["party_offset"] + 1 + index] = mon[0]
        self.bytes[mon_start:mon_start + GEN1["mon_size"]] = mon
        self.bytes[ot_start:ot_start + GEN1["name_size"]] = ot
        self.bytes[nick_start:nick_start + GEN1["name_size"]] = nick
        self.bytes[GEN1["checksum_offset"]] = gen1_checksum(self.bytes)

    def _write_gen1_box_data(self, box_index: int, slot_index: int, mon: bytes, ot: bytes, nick: bytes) -> None:
        _, species_start, offset = self._gen1_box_header(box_index)
        mon_start = offset + 0x16 + slot_index * GEN1["box_mon_size"]
        ot_start = offset + GEN1["box_ot_offset"] + slot_index * GEN1["name_size"]
        nick_start = offset + GEN1["box_nick_offset"] + slot_index * GEN1["name_size"]
        self.bytes[species_start + slot_index] = mon[0]
        self.bytes[mon_start:mon_start + GEN1["box_mon_size"]] = mon
        self.bytes[ot_start:ot_start + GEN1["name_size"]] = ot
        self.bytes[nick_start:nick_start + GEN1["name_size"]] = nick
        self.bytes[GEN1["checksum_offset"]] = gen1_checksum(self.bytes)

    def _read_gen2_party_data(self, index: int) -> tuple[bytes, bytes, bytes]:
        mon_start = self.layout["data_offset"] + index * self.layout["mon_size"]
        ot_start = self.layout["ot_offset"] + index * self.layout["name_size"]
        nick_start = self.layout["nick_offset"] + index * self.layout["name_size"]
        return (
            bytes(self.bytes[mon_start:mon_start + self.layout["mon_size"]]),
            bytes(self.bytes[ot_start:ot_start + self.layout["name_size"]]),
            bytes(self.bytes[nick_start:nick_start + self.layout["name_size"]]),
        )

    def _gen2_box_header(self, box_index: int) -> tuple[int, int, int]:
        offset = self.layout["current_box_data_offset"] if box_index == self.current_box else self.layout["stored_box_offsets"][box_index]
        count = int(self.bytes[offset])
        species_start = offset + 1
        return count, species_start, offset

    def _read_gen2_box_data(self, box_index: int, slot_index: int) -> tuple[bytes, bytes, bytes]:
        _, _, offset = self._gen2_box_header(box_index)
        mon_start = offset + 0x16 + slot_index * self.layout["box_mon_size"]
        ot_start = offset + self.layout["box_ot_offset"] + slot_index * self.layout["name_size"]
        nick_start = offset + self.layout["box_nick_offset"] + slot_index * self.layout["name_size"]
        return (
            bytes(self.bytes[mon_start:mon_start + self.layout["box_mon_size"]]),
            bytes(self.bytes[ot_start:ot_start + self.layout["name_size"]]),
            bytes(self.bytes[nick_start:nick_start + self.layout["name_size"]]),
        )

    def _write_gen2_party_data(self, index: int, mon: bytes, ot: bytes, nick: bytes) -> None:
        mon_start = self.layout["data_offset"] + index * self.layout["mon_size"]
        ot_start = self.layout["ot_offset"] + index * self.layout["name_size"]
        nick_start = self.layout["nick_offset"] + index * self.layout["name_size"]
        self.bytes[self.layout["party_offset"] + 1 + index] = mon[0]
        self.bytes[mon_start:mon_start + self.layout["mon_size"]] = mon
        self.bytes[ot_start:ot_start + self.layout["name_size"]] = ot
        self.bytes[nick_start:nick_start + self.layout["name_size"]] = nick
        write_gen2_checksums(self.bytes, self.layout)

    def _write_gen2_box_data(self, box_index: int, slot_index: int, mon: bytes, ot: bytes, nick: bytes) -> None:
        _, species_start, offset = self._gen2_box_header(box_index)
        mon_start = offset + 0x16 + slot_index * self.layout["box_mon_size"]
        ot_start = offset + self.layout["box_ot_offset"] + slot_index * self.layout["name_size"]
        nick_start = offset + self.layout["box_nick_offset"] + slot_index * self.layout["name_size"]
        self.bytes[species_start + slot_index] = mon[0]
        self.bytes[mon_start:mon_start + self.layout["box_mon_size"]] = mon
        self.bytes[ot_start:ot_start + self.layout["name_size"]] = ot
        self.bytes[nick_start:nick_start + self.layout["name_size"]] = nick
        write_gen2_checksums(self.bytes, self.layout)

    def _read_gen3_party_data(self, index: int) -> bytes:
        if not self.slot:
            raise SaveError("Slot Gen 3 não detectado.")
        section_offsets = self.slot.get("section_offsets") or {}
        section1 = section_offsets.get(1)
        if section1 is None:
            raise SaveError("Save Gen 3 inválido: seção 1 ausente no slot ativo.")
        start = section1 + self.layout["party_offset"] + index * GEN3["mon_size"]
        return bytes(self.bytes[start:start + GEN3["mon_size"]])

    def _gen3_pc_buffer(self) -> bytearray:
        if not self.slot:
            raise SaveError("Slot Gen 3 não detectado.")
        section_offsets = self.slot.get("section_offsets") or {}
        required_sections = list(range(5, 13)) + [13]
        missing_sections = [section_id for section_id in required_sections if section_id not in section_offsets]
        if missing_sections:
            missing_str = ", ".join(str(section_id) for section_id in missing_sections)
            raise SaveError(
                "Save Gen 3 incompleto/corrompido no slot ativo: "
                f"faltam seções de PC ({missing_str})."
            )
        chunks = []
        for section_id in range(5, 13):
            offset = section_offsets[section_id]
            chunks.append(bytes(self.bytes[offset:offset + GEN3["sector_data_size"]]))
        section13 = section_offsets[13]
        chunks.append(bytes(self.bytes[section13:section13 + 2000]))
        merged = bytearray(sum(len(chunk) for chunk in chunks))
        cursor = 0
        for chunk in chunks:
            merged[cursor:cursor + len(chunk)] = chunk
            cursor += len(chunk)
        return merged

    def _write_gen3_pc_buffer(self, buffer: bytearray) -> None:
        if not self.slot:
            raise SaveError("Slot Gen 3 não detectado.")
        section_offsets = self.slot.get("section_offsets") or {}
        required_sections = list(range(5, 13)) + [13]
        missing_sections = [section_id for section_id in required_sections if section_id not in section_offsets]
        if missing_sections:
            missing_str = ", ".join(str(section_id) for section_id in missing_sections)
            raise SaveError(
                "Save Gen 3 incompleto/corrompido no slot ativo: "
                f"faltam seções de PC ({missing_str})."
            )
        cursor = 0
        for section_id in range(5, 13):
            offset = section_offsets[section_id]
            chunk = buffer[cursor:cursor + GEN3["sector_data_size"]]
            self.bytes[offset:offset + GEN3["sector_data_size"]] = chunk
            write_u16(self.bytes, offset + 0xFF6, gen3_sector_checksum(self.bytes, offset))
            cursor += GEN3["sector_data_size"]
        offset13 = section_offsets[13]
        tail = buffer[cursor:cursor + 2000]
        self.bytes[offset13:offset13 + 2000] = tail
        write_u16(self.bytes, offset13 + 0xFF6, gen3_sector_checksum(self.bytes, offset13))

    def _read_gen3_box_data(self, box_index: int, slot_index: int) -> bytes:
        buffer = self._gen3_pc_buffer()
        start = GEN3["pc_buffer_boxes_offset"] + (box_index * GEN3["box_capacity"] + slot_index) * GEN3["box_mon_size"]
        return bytes(buffer[start:start + GEN3["box_mon_size"]])

    def _write_gen3_party_data(self, index: int, raw: bytes) -> None:
        if not self.slot:
            raise SaveError("Slot Gen 3 não detectado.")
        section_offsets = self.slot.get("section_offsets") or {}
        section1 = section_offsets.get(1)
        if section1 is None:
            raise SaveError("Save Gen 3 inválido: seção 1 ausente no slot ativo.")
        start = section1 + self.layout["party_offset"] + index * GEN3["mon_size"]
        self.bytes[start:start + GEN3["mon_size"]] = raw
        write_u16(self.bytes, section1 + 0xFF6, gen3_sector_checksum(self.bytes, section1))

    def _write_gen3_box_data(self, box_index: int, slot_index: int, raw: bytes) -> None:
        buffer = self._gen3_pc_buffer()
        start = GEN3["pc_buffer_boxes_offset"] + (box_index * GEN3["box_capacity"] + slot_index) * GEN3["box_mon_size"]
        buffer[start:start + GEN3["box_mon_size"]] = raw
        self._write_gen3_pc_buffer(buffer)

    def _promote_gen3_box_to_party(self, raw: bytes, pokemon: Dict[str, Any]) -> bytes:
        from pokecable_runtime.data.base_stats import get_base_stats
        promoted = bytearray(GEN3["mon_size"])
        promoted[:GEN3["box_mon_size"]] = raw[:GEN3["box_mon_size"]]
        level = max(1, int(pokemon.get("level", 1)))
        promoted[0x54] = level

        # Extract IVs and EVs from raw box data and calculate stats
        personality = read_u32(raw, 0)
        species_id = pokemon.get("species_id", 0)
        if species_id > 0:
            base = get_base_stats(species_id)
            if base:
                bs = base["stats"]
                # Decrypt secure to extract IVs and EVs
                secure = decrypt_gen3_secure(raw)
                substruct_order = GEN3["substruct_orders"][personality % 24]
                evs_offset = substruct_order[2] * 12
                misc_offset = substruct_order[3] * 12

                # Extract IVs from misc substruct
                iv_raw = read_u32(secure, misc_offset)
                hp_iv = iv_raw & 0x1F
                atk_iv = (iv_raw >> 5) & 0x1F
                def_iv = (iv_raw >> 10) & 0x1F
                spe_iv = (iv_raw >> 15) & 0x1F
                spa_iv = (iv_raw >> 20) & 0x1F
                spd_iv = (iv_raw >> 25) & 0x1F

                # Extract EVs from evs substruct
                ev_hp = secure[evs_offset + 0]
                ev_atk = secure[evs_offset + 1]
                ev_def = secure[evs_offset + 2]
                ev_spe = secure[evs_offset + 3]
                ev_spa = secure[evs_offset + 4]
                ev_spd = secure[evs_offset + 5]

                # Calculate stats
                max_hp = (2 * bs["hp"] + hp_iv + ev_hp // 4) * level // 100 + level + 10
                stat_atk = (2 * bs["atk"] + atk_iv + ev_atk // 4) * level // 100 + 5
                stat_def = (2 * bs["def"] + def_iv + ev_def // 4) * level // 100 + 5
                stat_spe = (2 * bs["spe"] + spe_iv + ev_spe // 4) * level // 100 + 5
                stat_spa = (2 * bs["spa"] + spa_iv + ev_spa // 4) * level // 100 + 5
                stat_spd = (2 * bs["spd"] + spd_iv + ev_spd // 4) * level // 100 + 5

                # Write stat cache
                promoted[86:88] = max_hp.to_bytes(2, "little")
                promoted[88:90] = max_hp.to_bytes(2, "little")
                promoted[90:92] = stat_atk.to_bytes(2, "little")
                promoted[92:94] = stat_def.to_bytes(2, "little")
                promoted[94:96] = stat_spe.to_bytes(2, "little")
                promoted[96:98] = stat_spa.to_bytes(2, "little")
                promoted[98:100] = stat_spd.to_bytes(2, "little")

        return bytes(promoted)

    def _mark_pokedex_caught(self, national_dex_id: int) -> None:
        if national_dex_id <= 0:
            return
        dex_idx = national_dex_id - 1
        byte_off = dex_idx >> 3
        mask = 1 << (dex_idx & 7)
        if self.generation == 1:
            for base in [0x25A3, 0x25B6]:
                self.bytes[base + byte_off] |= mask
            self.bytes[GEN1["checksum_offset"]] = gen1_checksum(self.bytes)
        elif self.generation == 2:
            owned_offset = self.layout.get("pokedex_owned_offset")
            seen_offset = self.layout.get("pokedex_seen_offset")
            if owned_offset is None or seen_offset is None:
                return
            for base in [owned_offset, seen_offset]:
                self.bytes[base + byte_off] |= mask
            write_gen2_checksums(self.bytes, self.layout)
        elif self.generation == 3 and self.slot:
            section_offsets = self.slot.get("section_offsets") or {}
            sec0 = section_offsets.get(0)
            if sec0 is None:
                return
            self.bytes[sec0 + 0x0028 + byte_off] |= mask
            self.bytes[sec0 + 0x005C + byte_off] |= mask
            write_u16(self.bytes, sec0 + 0xFF6, gen3_sector_checksum(self.bytes, sec0))
            is_frlg = self.game in ("pokemon_firered", "pokemon_leafgreen")
            is_emerald = self.game == "pokemon_emerald"
            sec1 = self.slot["section_offsets"][1]
            seen_b = 0x05F8 if is_frlg else (0x0988 if is_emerald else 0x0938)
            self.bytes[sec1 + seen_b + byte_off] |= mask
            write_u16(self.bytes, sec1 + 0xFF6, gen3_sector_checksum(self.bytes, sec1))
            sec4 = self.slot["section_offsets"][4]
            seen_c = 0x0B98 if is_frlg else (0x0CA4 if is_emerald else 0x0C0C)
            self.bytes[sec4 + seen_c + byte_off] |= mask
            write_u16(self.bytes, sec4 + 0xFF6, gen3_sector_checksum(self.bytes, sec4))

    def _apply_gen1_payload(self, parsed: Dict[str, Any], source_kind: str, raw: bytes) -> None:
        party_len = GEN1["mon_size"] + GEN1["name_size"] * 2
        box_len = GEN1["box_mon_size"] + GEN1["name_size"] * 2
        if parsed["kind"] == "party":
            if source_kind != "party" or len(raw) != party_len:
                raise SaveError("Troca de box para party ainda não é suportada no R36S.")
            self._write_gen1_party_data(parsed["index"], raw[:GEN1["mon_size"]], raw[GEN1["mon_size"]:GEN1["mon_size"] + GEN1["name_size"]], raw[-GEN1["name_size"]:])
            self._mark_pokedex_caught(_resolve_national_dex_id(1, raw[0], {}))
            return
        if source_kind == "party" and len(raw) == party_len:
            mon = raw[:GEN1["box_mon_size"]]
            ot = raw[GEN1["mon_size"]:GEN1["mon_size"] + GEN1["name_size"]]
            nick = raw[-GEN1["name_size"]:]
            self._write_gen1_box_data(parsed["box_index"], parsed["slot_index"], mon, ot, nick)
            self._mark_pokedex_caught(_resolve_national_dex_id(1, raw[0], {}))
            return
        if source_kind == "box" and len(raw) == box_len:
            self._write_gen1_box_data(parsed["box_index"], parsed["slot_index"], raw[:GEN1["box_mon_size"]], raw[GEN1["box_mon_size"]:GEN1["box_mon_size"] + GEN1["name_size"]], raw[-GEN1["name_size"]:])
            self._mark_pokedex_caught(_resolve_national_dex_id(1, raw[0], {}))
            return
        raise SaveError("Payload Gen 1 com tamanho inválido.")

    def _apply_gen2_payload(self, parsed: Dict[str, Any], source_kind: str, raw: bytes) -> None:
        party_len = self.layout["mon_size"] + self.layout["name_size"] * 2
        box_len = self.layout["box_mon_size"] + self.layout["name_size"] * 2
        if parsed["kind"] == "party":
            if source_kind != "party" or len(raw) != party_len:
                raise SaveError("Troca de box para party ainda não é suportada no R36S.")
            self._write_gen2_party_data(parsed["index"], raw[:self.layout["mon_size"]], raw[self.layout["mon_size"]:self.layout["mon_size"] + self.layout["name_size"]], raw[-self.layout["name_size"]:])
            self._mark_pokedex_caught(_resolve_national_dex_id(2, raw[0], {}))
            return
        if source_kind == "party" and len(raw) == party_len:
            mon = raw[:self.layout["box_mon_size"]]
            ot = raw[self.layout["mon_size"]:self.layout["mon_size"] + self.layout["name_size"]]
            nick = raw[-self.layout["name_size"]:]
            self._write_gen2_box_data(parsed["box_index"], parsed["slot_index"], mon, ot, nick)
            self._mark_pokedex_caught(_resolve_national_dex_id(2, raw[0], {}))
            return
        if source_kind == "box" and len(raw) == box_len:
            self._write_gen2_box_data(parsed["box_index"], parsed["slot_index"], raw[:self.layout["box_mon_size"]], raw[self.layout["box_mon_size"]:self.layout["box_mon_size"] + self.layout["name_size"]], raw[-self.layout["name_size"]:])
            self._mark_pokedex_caught(_resolve_national_dex_id(2, raw[0], {}))
            return
        raise SaveError("Payload Gen 2 com tamanho inválido.")

    def _apply_gen3_payload(self, parsed: Dict[str, Any], source_kind: str, raw: bytes, payload: Dict[str, Any]) -> None:
        if parsed["kind"] == "party":
            if source_kind != "party" or len(raw) != GEN3["mon_size"]:
                raise SaveError("Troca de box para party ainda não é suportada no R36S.")
            poke_data = parse_gen3_pokemon(raw)
            species_id = poke_data.get("species_id", 0)
            self._write_gen3_party_data(parsed["index"], raw)
            self._mark_pokedex_caught(_resolve_national_dex_id(3, species_id, {}))
            return
        if source_kind == "party" and len(raw) == GEN3["mon_size"]:
            poke_data = parse_gen3_pokemon(raw)
            species_id = poke_data.get("species_id", 0)
            self._write_gen3_box_data(parsed["box_index"], parsed["slot_index"], raw[:GEN3["box_mon_size"]])
            self._mark_pokedex_caught(_resolve_national_dex_id(3, species_id, {}))
            return
        if source_kind == "box" and len(raw) == GEN3["box_mon_size"]:
            self._write_gen3_box_data(parsed["box_index"], parsed["slot_index"], raw)
            return
        raise SaveError("Payload Gen 3 com tamanho inválido.")


def load_save(path: Path) -> SaveModel:
    logger.info("Loading save: %s", path)
    data = path.read_bytes()

    if validate_gen2(data[:0x8000], GEN2_CRYSTAL):
        save = SaveModel(
            path=path,
            bytes=bytearray(data),
            generation=2,
            game="pokemon_crystal",
            label=GEN2_CRYSTAL["game_label"],
            layout=GEN2_CRYSTAL,
            player_name=decode_gbc_text(data[GEN2_CRYSTAL["player_name_offset"]:GEN2_CRYSTAL["player_name_offset"] + GEN2_CRYSTAL["name_size"]]) or "Player",
        )
        save.refresh()
        logger.info("Detected save: path=%s generation=2 game=%s label=%s", path, save.game, save.label)
        return save

    if validate_gen2(data[:0x8000], GEN2_GS):
        lower_name = path.name.lower()
        game = "pokemon_silver" if "silver" in lower_name else "pokemon_gold"
        label = "Gen 2 Silver" if game == "pokemon_silver" else "Gen 2 Gold"
        save = SaveModel(
            path=path,
            bytes=bytearray(data),
            generation=2,
            game=game,
            label=label,
            layout=GEN2_GS,
            player_name=decode_gbc_text(data[GEN2_GS["player_name_offset"]:GEN2_GS["player_name_offset"] + GEN2_GS["name_size"]]) or "Player",
        )
        save.refresh()
        logger.info("Detected save: path=%s generation=2 game=%s label=%s", path, save.game, save.label)
        return save

    if validate_gen1(data):
        lower_name = path.name.lower()
        if "yellow" in lower_name:
            game = "pokemon_yellow"
        elif "blue" in lower_name:
            game = "pokemon_blue"
        else:
            game = "pokemon_red"
        save = SaveModel(
            path=path,
            bytes=bytearray(data),
            generation=1,
            game=game,
            label=GEN1["game_label"],
            layout=GEN1,
            player_name=decode_gbc_text(data[GEN1["player_name_offset"]:GEN1["player_name_offset"] + GEN1["name_size"]]) or "Player",
        )
        save.refresh()
        logger.info("Detected save: path=%s generation=1 game=%s label=%s", path, save.game, save.label)
        return save

    gen3 = detect_gen3(data)
    if gen3:
        lower_name = path.name.lower()
        game = gen3["layout"]["game"]
        if gen3["layout"]["name"] == "frlg":
            game = "pokemon_leafgreen" if "leaf" in lower_name else "pokemon_firered"
            label = "Gen 3 FireRed/LeafGreen"
        else:
            if "ruby" in lower_name:
                game = "pokemon_ruby"
            elif "sapphire" in lower_name:
                game = "pokemon_sapphire"
            label = "Gen 3 Ruby/Sapphire/Emerald"
        section0 = gen3["slot"]["section_offsets"].get(0, gen3["slot"]["section_offsets"].get(1, 0))
        player_name = decode_gen3_text(data[section0 + GEN3["player_name_offset"]:section0 + GEN3["player_name_offset"] + 7]) or "Player"
        save = SaveModel(
            path=path,
            bytes=bytearray(data),
            generation=3,
            game=game,
            label=label,
            layout=gen3["layout"],
            player_name=player_name,
            slot=gen3["slot"],
        )
        save.refresh()
        logger.info("Detected save: path=%s generation=3 game=%s label=%s", path, save.game, save.label)
        return save

    logger.error("Unsupported save: %s", path)
    raise SaveError("Save não suportado. Use um .sav/.srm válido de Gen 1, Gen 2 ou Gen 3.")
