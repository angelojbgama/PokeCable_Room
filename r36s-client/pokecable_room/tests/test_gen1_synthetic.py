from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.canonical import CanonicalPokemon, CanonicalSpecies
from pokecable_room.parsers.gen1 import (
    CHECKSUM_END,
    CHECKSUM_OFFSET,
    CHECKSUM_START,
    NAME_SIZE,
    PARTY_MON_OFFSET,
    PARTY_MON_SIZE,
    PARTY_NICK_OFFSET,
    PARTY_OFFSET,
    PARTY_OT_OFFSET,
    Gen1Parser,
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
    checksum = (~sum(data[CHECKSUM_START : CHECKSUM_END + 1])) & 0xFF
    data[CHECKSUM_OFFSET] = checksum


def synthetic_save() -> bytes:
    data = bytearray(0x8000)
    data[PARTY_OFFSET] = 2
    data[PARTY_OFFSET + 1] = 38
    data[PARTY_OFFSET + 2] = 41
    data[PARTY_OFFSET + 3] = 0xFF
    for index, (species, level, nickname) in enumerate([(38, 32, "KADABRA"), (41, 35, "MACHOKE")]):
        start = PARTY_MON_OFFSET + index * PARTY_MON_SIZE
        data[start] = species
        data[start + 0x0C : start + 0x0E] = (12345 + index).to_bytes(2, "big")
        data[start + 0x21] = level
        ot_start = PARTY_OT_OFFSET + index * NAME_SIZE
        nick_start = PARTY_NICK_OFFSET + index * NAME_SIZE
        data[ot_start : ot_start + NAME_SIZE] = encode_name("ASH")
        data[nick_start : nick_start + NAME_SIZE] = encode_name(nickname)
    write_checksum(data)
    return bytes(data)


class Gen1SyntheticParserTests(unittest.TestCase):
    def test_lists_and_replaces_party_pokemon(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save_a = Path(tempdir) / "a.sav"
            save_b = Path(tempdir) / "b.sav"
            save_a.write_bytes(synthetic_save())
            save_b.write_bytes(synthetic_save())

            parser_a = Gen1Parser()
            parser_b = Gen1Parser()
            parser_a.load(save_a)
            parser_b.load(save_b)

            self.assertEqual(parser_a.list_party()[0].species_name, "Kadabra")
            self.assertIn("#64 Kadabra", parser_a.list_party()[0].display_summary)
            self.assertIn("Sem item", parser_a.list_party()[0].display_summary)
            payload = parser_a.export_pokemon("party:0")
            parser_b.remove_or_replace_sent_pokemon("party:1", payload)
            parser_b.save(save_b)

            reloaded = Gen1Parser()
            reloaded.load(save_b)
            updated = reloaded.list_party()
            self.assertEqual(updated[1].species_name, "Kadabra")
            self.assertTrue(reloaded.validate())

    def test_import_canonical_mew_writes_internal_species_id(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            save = Path(tempdir) / "red.sav"
            save.write_bytes(synthetic_save())
            parser = Gen1Parser()
            parser.load(save)
            parser.import_canonical("party:1", canonical_mew(1, 21, "gen1_internal"))

            self.assertEqual(parser.get_species_id("party:1"), 21)
            self.assertEqual(parser.list_party()[1].species_name, "Mew")
            self.assertTrue(parser.validate())


def canonical_mew(source_generation: int, source_species_id: int, source_space: str) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=source_generation,
        source_game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[source_generation],
        species_national_id=151,
        species_name="Mew",
        nickname="MEW",
        level=30,
        ot_name="ASH",
        trainer_id=12345,
        species=CanonicalSpecies(
            national_dex_id=151,
            source_species_id=source_species_id,
            source_species_id_space=source_space,
            name="Mew",
        ),
    )


if __name__ == "__main__":
    unittest.main()
