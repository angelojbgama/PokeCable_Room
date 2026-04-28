from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.parsers.gen2 import (
    CRYSTAL_PARTY_OFFSET,
    CRYSTAL_PRIMARY_CHECKSUM,
    CRYSTAL_PRIMARY_END,
    CRYSTAL_PRIMARY_START,
    CRYSTAL_SECONDARY_CHECKSUM,
    CRYSTAL_SECONDARY_END,
    CRYSTAL_SECONDARY_START,
    CRYSTAL_LAYOUT,
    GOLD_SILVER_PARTY_OFFSET,
    GOLD_SILVER_PRIMARY_CHECKSUM,
    GOLD_SILVER_PRIMARY_END,
    GOLD_SILVER_PRIMARY_START,
    NAME_SIZE,
    PARTY_HEADER_SIZE,
    PARTY_MON_SIZE,
    Gen2Parser,
)


def encode_name(value: str) -> bytes:
    encoded = bytearray([0x50] * NAME_SIZE)
    for index, char in enumerate(value[:10]):
        if "A" <= char <= "Z":
            encoded[index] = 0x80 + ord(char) - ord("A")
        elif "a" <= char <= "z":
            encoded[index] = 0xA0 + ord(char) - ord("a")
        elif char == " ":
            encoded[index] = 0x7F
    return bytes(encoded)


def write_checksum(data: bytearray) -> None:
    data[CRYSTAL_SECONDARY_START : CRYSTAL_SECONDARY_END + 1] = data[CRYSTAL_PRIMARY_START : CRYSTAL_PRIMARY_END + 1]
    primary = sum(data[CRYSTAL_PRIMARY_START : CRYSTAL_PRIMARY_END + 1]) & 0xFFFF
    secondary = sum(data[CRYSTAL_SECONDARY_START : CRYSTAL_SECONDARY_END + 1]) & 0xFFFF
    data[CRYSTAL_PRIMARY_CHECKSUM : CRYSTAL_PRIMARY_CHECKSUM + 2] = primary.to_bytes(2, "little")
    data[CRYSTAL_SECONDARY_CHECKSUM : CRYSTAL_SECONDARY_CHECKSUM + 2] = secondary.to_bytes(2, "little")


def synthetic_save() -> bytes:
    data = bytearray(0x8000)
    data[CRYSTAL_PARTY_OFFSET] = 2
    data[CRYSTAL_PARTY_OFFSET + 1] = 95
    data[CRYSTAL_PARTY_OFFSET + 2] = 156
    data[CRYSTAL_PARTY_OFFSET + 3] = 0xFF
    for index, (species, level, nick) in enumerate([(95, 11, "ROCKY"), (156, 18, "QUILAVA")]):
        start = CRYSTAL_LAYOUT.party_data_offset + index * PARTY_MON_SIZE
        data[start] = species
        data[start + 0x06 : start + 0x08] = (12345 + index).to_bytes(2, "big")
        data[start + 0x1F] = level
        ot_start = CRYSTAL_LAYOUT.party_ot_offset + index * NAME_SIZE
        nick_start = CRYSTAL_LAYOUT.party_nick_offset + index * NAME_SIZE
        data[ot_start : ot_start + NAME_SIZE] = encode_name("CHRIS")
        data[nick_start : nick_start + NAME_SIZE] = encode_name(nick)
    write_checksum(data)
    return bytes(data)


def write_gold_silver_checksum(data: bytearray) -> None:
    checksum = sum(data[GOLD_SILVER_PRIMARY_START : GOLD_SILVER_PRIMARY_END + 1]) & 0xFFFF
    data[GOLD_SILVER_PRIMARY_CHECKSUM : GOLD_SILVER_PRIMARY_CHECKSUM + 2] = checksum.to_bytes(2, "little")


def synthetic_gold_silver_save() -> bytes:
    data = bytearray(0x8030)
    data[GOLD_SILVER_PARTY_OFFSET] = 1
    data[GOLD_SILVER_PARTY_OFFSET + 1] = 160
    data[GOLD_SILVER_PARTY_OFFSET + 2] = 0xFF
    party_data = GOLD_SILVER_PARTY_OFFSET + PARTY_HEADER_SIZE
    ot_offset = party_data + 6 * PARTY_MON_SIZE
    nick_offset = ot_offset + 6 * NAME_SIZE
    data[party_data] = 160
    data[party_data + 0x06 : party_data + 0x08] = (555).to_bytes(2, "big")
    data[party_data + 0x1F] = 44
    data[ot_offset : ot_offset + NAME_SIZE] = encode_name("GOLD")
    data[nick_offset : nick_offset + NAME_SIZE] = encode_name("FERALIGATR")
    write_gold_silver_checksum(data)
    return bytes(data)


class Gen2ParserTests(unittest.TestCase):
    def test_lists_and_replaces_party_pokemon(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_a = Path(tempdir) / "a.srm"
            save_b = Path(tempdir) / "b.srm"
            save_a.write_bytes(synthetic_save())
            save_b.write_bytes(synthetic_save())
            parser_a = Gen2Parser()
            parser_b = Gen2Parser()
            parser_a.load(save_a)
            parser_b.load(save_b)
            party = parser_a.list_party()
            self.assertEqual(party[0].species_name, "Onix")
            self.assertEqual(party[1].species_name, "Quilava")

            payload = parser_a.export_pokemon("party:0")
            parser_b.remove_or_replace_sent_pokemon("party:1", payload)
            parser_b.save(save_b)

            parser_b_reloaded = Gen2Parser()
            parser_b_reloaded.load(save_b)
            updated = parser_b_reloaded.list_party()
            self.assertEqual(updated[1].species_name, "Onix")
            self.assertTrue(parser_b_reloaded.validate())

    def test_detects_gold_silver_layout_with_rtc_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "Pokemon Gold.sav"
            save.write_bytes(synthetic_gold_silver_save())
            parser = Gen2Parser()
            parser.load(save)
            party = parser.list_party()
            self.assertEqual(parser.get_game_id(), "pokemon_gold")
            self.assertEqual(party[0].species_name, "Feraligatr")
            self.assertEqual(party[0].level, 44)


if __name__ == "__main__":
    unittest.main()
