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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class SaveError(Exception):
    """Raised when a local save cannot be parsed or updated safely."""


logger = logging.getLogger("pokecable_save")


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
        "experience": read_u32(secure, growth + 4),
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
        "level": 1 if is_egg else 0,
        "nickname": nickname or species_name,
        "ot_name": decode_gen3_text(raw[0x14:0x1B]),
        "trainer_id": trainer_id,
        "nature": None if is_egg else GEN3_NATURES[personality % 25],
        "ability_index": None if is_egg else (personality & 1),
        "held_item_id": read_u16(secure, growth + 2) or None,
        "moves": moves,
        "is_egg": is_egg,
        "experience": experience,
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

    def export_payload(self, location: str) -> Dict[str, Any]:
        parsed = parse_location(location)
        pokemon = self.pokemon_by_location(location)
        if not pokemon:
            raise SaveError("Pokémon não encontrado.")
        if pokemon.get("is_egg"):
            raise SaveError("Ovos ainda não são suportados para troca real.")
        if self.generation == 1:
            if parsed["kind"] == "party":
                mon, ot, nick = self._read_gen1_party_data(parsed["index"])
                raw_format = GEN1["party_format"]
            else:
                mon, ot, nick = self._read_gen1_box_data(parsed["box_index"], parsed["slot_index"])
                raw_format = GEN1["box_format"]
            raw = mon + ot + nick
            if parsed["kind"] == "party":
                experience = (mon[0x0E] << 16) | (mon[0x0F] << 8) | mon[0x10]
            else:
                experience = 0
        elif self.generation == 2:
            if parsed["kind"] == "party":
                mon, ot, nick = self._read_gen2_party_data(parsed["index"])
                raw_format = self.layout["party_format"]
                experience = (mon[0x08] << 16) | (mon[0x09] << 8) | mon[0x0A]
            else:
                mon, ot, nick = self._read_gen2_box_data(parsed["box_index"], parsed["slot_index"])
                raw_format = self.layout["box_format"]
                experience = 0
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
            "species_id": pokemon.get("species_id", 0),
            "species_name": pokemon.get("species_name", "Pokemon"),
            "types": pokemon.get("types", []),
            "level": pokemon.get("level", 0),
            "nickname": pokemon.get("nickname", pokemon.get("species_name", "")),
            "ot_name": pokemon.get("ot_name", ""),
            "trainer_id": pokemon.get("trainer_id", 0),
            "held_item_id": pokemon.get("held_item_id"),
            "held_item_name": pokemon.get("held_item_name"),
            "held_item_category": pokemon.get("held_item_category"),
            "moves": pokemon.get("moves", []),
            "move_names": pokemon.get("move_names", []),
            "raw_data_base64": raw_b64,
            "display_summary": display,
            "summary": {
                "species_id": pokemon.get("species_id", 0),
                "species_name": pokemon.get("species_name", "Pokemon"),
                "types": pokemon.get("types", []),
                "level": pokemon.get("level", 0),
                "nickname": pokemon.get("nickname", pokemon.get("species_name", "")),
                "held_item_id": pokemon.get("held_item_id"),
                "held_item_name": pokemon.get("held_item_name"),
                "held_item_category": pokemon.get("held_item_category"),
                "moves": pokemon.get("moves", []),
                "move_names": pokemon.get("move_names", []),
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
                "species_name": pokemon.get("species_name", "Pokemon"),
                "nickname": pokemon.get("nickname", pokemon.get("species_name", "")),
                "types": pokemon.get("types", []),
                "level": pokemon.get("level", 0),
                "experience": experience,
                "ot_name": pokemon.get("ot_name", ""),
                "trainer_id": pokemon.get("trainer_id", 0),
                "moves": [{"move_id": move_id, "source_generation": self.generation} for move_id in pokemon.get("moves", [])],
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
                "metadata": {"is_shiny": bool(pokemon.get("is_shiny"))},
            },
            "raw": {"format": raw_format, "data_base64": raw_b64},
            "compatibility_report": preflight_report(True, self.generation),
            "metadata": {"format": raw_format, "source": "r36s-local-save", "location": location},
        }

    def apply_payload(
        self,
        location: str,
        payload: Dict[str, Any],
        trade_evolution: Optional[Dict[str, Any]] = None,
        cancel_trade_evolution: bool = False,
    ) -> Dict[str, Any]:
        parsed = parse_location(location)
        if int(payload.get("generation", 0)) != self.generation:
            raise SaveError("Cross-generation ainda não é suportado no R36S.")
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
                "is_egg": False,
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
                    "level": 0,
                    "experience": experience,
                    "nickname": nickname or species_name,
                    "ot_name": decode_gbc_text(ot),
                    "trainer_id": (mon[0x0C] << 8) | mon[0x0D] if len(mon) > 0x0D else 0,
                    "moves": [move for move in mon[0x08:0x0C] if move],
                    "is_egg": False,
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
                "is_egg": is_egg,
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
                    "level": 0,
                    "experience": experience,
                    "nickname": nickname or species_name,
                    "ot_name": decode_gbc_text(ot),
                    "trainer_id": (mon[0x06] << 8) | mon[0x07] if len(mon) > 0x07 else 0,
                    "held_item_id": int(mon[0x01]) or None,
                    "moves": [move for move in mon[0x02:0x06] if move],
                    "is_egg": False,
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
        section1 = self.slot["section_offsets"][1]
        count = int(self.bytes[section1 + self.layout["party_count_offset"]])
        party = []
        for index in range(count):
            raw = self._read_gen3_party_data(index)
            details = parse_gen3_pokemon(raw)
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
                "held_item_id": details["held_item_id"],
                "nature": details["nature"],
                "ability_index": details["ability_index"],
                "experience": details["experience"],
                "is_egg": details["is_egg"],
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
                    "held_item_id": details["held_item_id"],
                    "nature": details["nature"],
                    "ability_index": details["ability_index"],
                    "experience": details["experience"],
                    "is_egg": details["is_egg"],
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
        section1 = self.slot["section_offsets"][1]
        start = section1 + self.layout["party_offset"] + index * GEN3["mon_size"]
        return bytes(self.bytes[start:start + GEN3["mon_size"]])

    def _gen3_pc_buffer(self) -> bytearray:
        if not self.slot:
            raise SaveError("Slot Gen 3 não detectado.")
        chunks = []
        for section_id in range(5, 13):
            offset = self.slot["section_offsets"][section_id]
            chunks.append(bytes(self.bytes[offset:offset + GEN3["sector_data_size"]]))
        section13 = self.slot["section_offsets"][13]
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
        cursor = 0
        for section_id in range(5, 13):
            offset = self.slot["section_offsets"][section_id]
            chunk = buffer[cursor:cursor + GEN3["sector_data_size"]]
            self.bytes[offset:offset + GEN3["sector_data_size"]] = chunk
            write_u16(self.bytes, offset + 0xFF6, gen3_sector_checksum(self.bytes, offset))
            cursor += GEN3["sector_data_size"]
        offset13 = self.slot["section_offsets"][13]
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
        section1 = self.slot["section_offsets"][1]
        start = section1 + self.layout["party_offset"] + index * GEN3["mon_size"]
        self.bytes[start:start + GEN3["mon_size"]] = raw
        write_u16(self.bytes, section1 + 0xFF6, gen3_sector_checksum(self.bytes, section1))

    def _write_gen3_box_data(self, box_index: int, slot_index: int, raw: bytes) -> None:
        buffer = self._gen3_pc_buffer()
        start = GEN3["pc_buffer_boxes_offset"] + (box_index * GEN3["box_capacity"] + slot_index) * GEN3["box_mon_size"]
        buffer[start:start + GEN3["box_mon_size"]] = raw
        self._write_gen3_pc_buffer(buffer)

    def _promote_gen3_box_to_party(self, raw: bytes, pokemon: Dict[str, Any]) -> bytes:
        promoted = bytearray(GEN3["mon_size"])
        promoted[:GEN3["box_mon_size"]] = raw[:GEN3["box_mon_size"]]
        promoted[0x54] = max(1, int(pokemon.get("level", 1)))
        return bytes(promoted)

    def _apply_gen1_payload(self, parsed: Dict[str, Any], source_kind: str, raw: bytes) -> None:
        party_len = GEN1["mon_size"] + GEN1["name_size"] * 2
        box_len = GEN1["box_mon_size"] + GEN1["name_size"] * 2
        if parsed["kind"] == "party":
            if source_kind != "party" or len(raw) != party_len:
                raise SaveError("Troca de box para party ainda não é suportada no R36S.")
            self._write_gen1_party_data(parsed["index"], raw[:GEN1["mon_size"]], raw[GEN1["mon_size"]:GEN1["mon_size"] + GEN1["name_size"]], raw[-GEN1["name_size"]:])
            return
        if source_kind == "party" and len(raw) == party_len:
            mon = raw[:GEN1["box_mon_size"]]
            ot = raw[GEN1["mon_size"]:GEN1["mon_size"] + GEN1["name_size"]]
            nick = raw[-GEN1["name_size"]:]
            self._write_gen1_box_data(parsed["box_index"], parsed["slot_index"], mon, ot, nick)
            return
        if source_kind == "box" and len(raw) == box_len:
            self._write_gen1_box_data(parsed["box_index"], parsed["slot_index"], raw[:GEN1["box_mon_size"]], raw[GEN1["box_mon_size"]:GEN1["box_mon_size"] + GEN1["name_size"]], raw[-GEN1["name_size"]:])
            return
        raise SaveError("Payload Gen 1 com tamanho inválido.")

    def _apply_gen2_payload(self, parsed: Dict[str, Any], source_kind: str, raw: bytes) -> None:
        party_len = self.layout["mon_size"] + self.layout["name_size"] * 2
        box_len = self.layout["box_mon_size"] + self.layout["name_size"] * 2
        if parsed["kind"] == "party":
            if source_kind != "party" or len(raw) != party_len:
                raise SaveError("Troca de box para party ainda não é suportada no R36S.")
            self._write_gen2_party_data(parsed["index"], raw[:self.layout["mon_size"]], raw[self.layout["mon_size"]:self.layout["mon_size"] + self.layout["name_size"]], raw[-self.layout["name_size"]:])
            return
        if source_kind == "party" and len(raw) == party_len:
            mon = raw[:self.layout["box_mon_size"]]
            ot = raw[self.layout["mon_size"]:self.layout["mon_size"] + self.layout["name_size"]]
            nick = raw[-self.layout["name_size"]:]
            self._write_gen2_box_data(parsed["box_index"], parsed["slot_index"], mon, ot, nick)
            return
        if source_kind == "box" and len(raw) == box_len:
            self._write_gen2_box_data(parsed["box_index"], parsed["slot_index"], raw[:self.layout["box_mon_size"]], raw[self.layout["box_mon_size"]:self.layout["box_mon_size"] + self.layout["name_size"]], raw[-self.layout["name_size"]:])
            return
        raise SaveError("Payload Gen 2 com tamanho inválido.")

    def _apply_gen3_payload(self, parsed: Dict[str, Any], source_kind: str, raw: bytes, payload: Dict[str, Any]) -> None:
        if parsed["kind"] == "party":
            if source_kind != "party" or len(raw) != GEN3["mon_size"]:
                raise SaveError("Troca de box para party ainda não é suportada no R36S.")
            parse_gen3_pokemon(raw)
            self._write_gen3_party_data(parsed["index"], raw)
            return
        if source_kind == "party" and len(raw) == GEN3["mon_size"]:
            self._write_gen3_box_data(parsed["box_index"], parsed["slot_index"], raw[:GEN3["box_mon_size"]])
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
