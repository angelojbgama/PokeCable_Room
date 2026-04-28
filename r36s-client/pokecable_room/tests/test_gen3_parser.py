from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.parsers.gen3 import (
    LAYOUTS,
    PARTY_MON_SIZE,
    SECTOR_DATA_SIZE,
    SECTOR_SIGNATURE,
    SECTOR_SIZE,
    SECTORS_PER_SLOT,
    SECURE_SIZE,
    SUBSTRUCT_ORDERS,
    Gen3Parser,
)


def encode_text(value: str, size: int) -> bytes:
    encoded = bytearray([0xFF] * size)
    for index, char in enumerate(value[:size]):
        if "A" <= char <= "Z":
            encoded[index] = 0xBB + ord(char) - ord("A")
        elif "a" <= char <= "z":
            encoded[index] = 0xD5 + ord(char) - ord("a")
        elif "0" <= char <= "9":
            encoded[index] = 0xA1 + ord(char) - ord("0")
        elif char == " ":
            encoded[index] = 0x00
    return bytes(encoded)


def sector_checksum(data: bytes, size: int = SECTOR_DATA_SIZE) -> int:
    checksum = 0
    for offset in range(0, size, 4):
        checksum = (checksum + int.from_bytes(data[offset : offset + 4].ljust(4, b"\x00"), "little")) & 0xFFFFFFFF
    return ((checksum >> 16) + checksum) & 0xFFFF


def box_checksum(secure: bytes) -> int:
    value = 0
    for offset in range(0, SECURE_SIZE, 2):
        value = (value + int.from_bytes(secure[offset : offset + 2], "little")) & 0xFFFF
    return value


def make_pokemon(species: int, level: int, nickname: str, ot_name: str, personality: int) -> bytes:
    trainer_id = 0x12345678
    secure = bytearray(SECURE_SIZE)
    growth_index = SUBSTRUCT_ORDERS[personality % 24][0]
    growth = growth_index * 12
    secure[growth : growth + 2] = species.to_bytes(2, "little")
    secure[growth + 4 : growth + 8] = (1000).to_bytes(4, "little")
    secure[growth + 9] = 70
    checksum = box_checksum(bytes(secure))
    key = personality ^ trainer_id
    encrypted = bytearray(secure)
    for offset in range(0, SECURE_SIZE, 4):
        value = int.from_bytes(encrypted[offset : offset + 4], "little") ^ key
        encrypted[offset : offset + 4] = value.to_bytes(4, "little")

    raw = bytearray(PARTY_MON_SIZE)
    raw[0:4] = personality.to_bytes(4, "little")
    raw[4:8] = trainer_id.to_bytes(4, "little")
    raw[8:18] = encode_text(nickname, 10)
    raw[18] = 2
    raw[19] = 0x02
    raw[20:27] = encode_text(ot_name, 7)
    raw[28:30] = checksum.to_bytes(2, "little")
    raw[32:80] = encrypted
    raw[84] = level
    return bytes(raw)


def write_sector_footer(data: bytearray, offset: int, sector_id: int, counter: int) -> None:
    section = bytes(data[offset : offset + SECTOR_DATA_SIZE])
    data[offset + 0xFF4 : offset + 0xFF6] = sector_id.to_bytes(2, "little")
    data[offset + 0xFF6 : offset + 0xFF8] = sector_checksum(section).to_bytes(2, "little")
    data[offset + 0xFF8 : offset + 0xFFC] = SECTOR_SIGNATURE.to_bytes(4, "little")
    data[offset + 0xFFC : offset + 0x1000] = counter.to_bytes(4, "little")


def synthetic_save(layout_name: str = "rse") -> bytes:
    layout = next(layout for layout in LAYOUTS if layout.name == layout_name)
    data = bytearray(SECTOR_SIZE * SECTORS_PER_SLOT * 2)
    for sector_id in range(SECTORS_PER_SLOT):
        write_sector_footer(data, sector_id * SECTOR_SIZE, sector_id, 7)

    section1 = SECTOR_SIZE
    data[section1 + layout.party_count_offset] = 2
    data[section1 + layout.party_offset : section1 + layout.party_offset + PARTY_MON_SIZE] = make_pokemon(
        64, 32, "KADABRA", "BRENDAN", 0
    )
    second = section1 + layout.party_offset + PARTY_MON_SIZE
    data[second : second + PARTY_MON_SIZE] = make_pokemon(373, 30, "CLAMPERL", "MAY", 8)
    write_sector_footer(data, section1, 1, 8)
    return bytes(data)


class Gen3ParserTests(unittest.TestCase):
    def test_lists_and_replaces_party_pokemon(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_a = Path(tempdir) / "a.sav"
            save_b = Path(tempdir) / "b.sav"
            save_a.write_bytes(synthetic_save("rse"))
            save_b.write_bytes(synthetic_save("frlg"))

            parser_a = Gen3Parser()
            parser_b = Gen3Parser()
            parser_a.load(save_a)
            parser_b.load(save_b)

            self.assertEqual(parser_a.list_party()[0].species_name, "Kadabra")
            self.assertEqual(parser_a.list_party()[1].species_name, "Clamperl")

            payload = parser_a.export_pokemon("party:1")
            parser_b.remove_or_replace_sent_pokemon("party:0", payload)
            parser_b.save(save_b)

            reloaded = Gen3Parser()
            reloaded.load(save_b)
            updated = reloaded.list_party()
            self.assertEqual(updated[0].species_name, "Clamperl")
            self.assertTrue(reloaded.validate())

    def test_export_canonical_marks_egg_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "egg.sav"
            save.write_bytes(synthetic_save("rse"))
            parser = Gen3Parser()
            parser.load(save)
            parser.set_species_id("party:0", 412)

            canonical = parser.export_canonical("party:0")

            self.assertTrue(canonical.metadata["is_egg"])
            self.assertEqual(canonical.species.national_dex_id, 0)


if __name__ == "__main__":
    unittest.main()
