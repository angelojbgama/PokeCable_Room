from __future__ import annotations

import base64
from pathlib import Path

from pokecable_room.canonical import CanonicalMove, CanonicalOriginalData, CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport, build_compatibility_report

from .base import PokemonPayload, PokemonSummary, SaveData
from .gen2 import GEN2_SPECIES


SAVE_SIZE = 0x8000
PARTY_OFFSET = 0x2F2C
PARTY_MON_OFFSET = PARTY_OFFSET + 0x08
PARTY_OT_OFFSET = PARTY_OFFSET + 0x110
PARTY_NICK_OFFSET = PARTY_OFFSET + 0x152
PARTY_CAPACITY = 6
PARTY_MON_SIZE = 44
NAME_SIZE = 11
CHECKSUM_START = 0x2598
CHECKSUM_END = 0x3522
CHECKSUM_OFFSET = 0x3523
RAW_PAYLOAD_SIZE = PARTY_MON_SIZE + NAME_SIZE + NAME_SIZE
POKEDEX_OWNED_OFFSET = 0x25A3
POKEDEX_SEEN_OFFSET = 0x25B6
POKEDEX_SIZE = 0x13


GEN1_INTERNAL_NAMES = {
    1: "Rhydon",
    2: "Kangaskhan",
    3: "Nidoran M",
    4: "Clefairy",
    5: "Spearow",
    6: "Voltorb",
    7: "Nidoking",
    8: "Slowbro",
    9: "Ivysaur",
    10: "Exeggutor",
    11: "Lickitung",
    12: "Exeggcute",
    13: "Grimer",
    14: "Gengar",
    15: "Nidoran F",
    16: "Nidoqueen",
    17: "Cubone",
    18: "Rhyhorn",
    19: "Lapras",
    20: "Arcanine",
    21: "Mew",
    22: "Gyarados",
    23: "Shellder",
    24: "Tentacool",
    25: "Gastly",
    26: "Scyther",
    27: "Staryu",
    28: "Blastoise",
    29: "Pinsir",
    30: "Tangela",
    33: "Growlithe",
    34: "Onix",
    35: "Fearow",
    36: "Pidgey",
    37: "Slowpoke",
    38: "Kadabra",
    39: "Graveler",
    40: "Chansey",
    41: "Machoke",
    42: "Mr. Mime",
    43: "Hitmonlee",
    44: "Hitmonchan",
    45: "Arbok",
    46: "Parasect",
    47: "Psyduck",
    48: "Drowzee",
    49: "Golem",
    51: "Magmar",
    53: "Electabuzz",
    54: "Magneton",
    55: "Koffing",
    57: "Mankey",
    58: "Seel",
    59: "Diglett",
    60: "Tauros",
    64: "Farfetch'd",
    65: "Venonat",
    66: "Dragonite",
    70: "Doduo",
    71: "Poliwag",
    72: "Jynx",
    73: "Moltres",
    74: "Articuno",
    75: "Zapdos",
    76: "Ditto",
    77: "Meowth",
    78: "Krabby",
    82: "Vulpix",
    83: "Ninetales",
    84: "Pikachu",
    85: "Raichu",
    88: "Dratini",
    89: "Dragonair",
    90: "Kabuto",
    91: "Kabutops",
    92: "Horsea",
    93: "Seadra",
    96: "Sandshrew",
    97: "Sandslash",
    98: "Omanyte",
    99: "Omastar",
    100: "Jigglypuff",
    101: "Wigglytuff",
    102: "Eevee",
    103: "Flareon",
    104: "Jolteon",
    105: "Vaporeon",
    106: "Machop",
    107: "Zubat",
    108: "Ekans",
    109: "Paras",
    110: "Poliwhirl",
    111: "Poliwrath",
    112: "Weedle",
    113: "Kakuna",
    114: "Beedrill",
    116: "Dodrio",
    117: "Primeape",
    118: "Dugtrio",
    119: "Venomoth",
    120: "Dewgong",
    123: "Caterpie",
    124: "Metapod",
    125: "Butterfree",
    126: "Machamp",
    128: "Golduck",
    129: "Hypno",
    130: "Golbat",
    131: "Mewtwo",
    132: "Snorlax",
    133: "Magikarp",
    136: "Muk",
    138: "Kingler",
    139: "Cloyster",
    141: "Electrode",
    142: "Clefable",
    143: "Weezing",
    144: "Persian",
    145: "Marowak",
    147: "Haunter",
    148: "Abra",
    149: "Alakazam",
    150: "Pidgeotto",
    151: "Pidgeot",
    152: "Starmie",
    153: "Bulbasaur",
    154: "Venusaur",
    155: "Tentacruel",
    157: "Goldeen",
    158: "Seaking",
    163: "Ponyta",
    164: "Rapidash",
    165: "Rattata",
    166: "Raticate",
    167: "Nidorino",
    168: "Nidorina",
    169: "Geodude",
    170: "Porygon",
    171: "Aerodactyl",
    173: "Magnemite",
    176: "Charmander",
    177: "Squirtle",
    178: "Charmeleon",
    179: "Wartortle",
    180: "Charizard",
    185: "Oddish",
    186: "Gloom",
    187: "Vileplume",
    188: "Bellsprout",
    189: "Weepinbell",
    190: "Victreebel",
}
GEN1_NATIONAL_DEX_BY_NAME = {name: national_id for national_id, name in GEN2_SPECIES.items() if national_id <= 151}
GEN1_INTERNAL_TO_NATIONAL_DEX = {
    internal_id: GEN1_NATIONAL_DEX_BY_NAME[name]
    for internal_id, name in GEN1_INTERNAL_NAMES.items()
    if name in GEN1_NATIONAL_DEX_BY_NAME
}
NATIONAL_DEX_TO_GEN1_INTERNAL = {national_id: internal_id for internal_id, national_id in GEN1_INTERNAL_TO_NATIONAL_DEX.items()}


def gen1_internal_to_national(internal_id: int) -> int:
    try:
        return GEN1_INTERNAL_TO_NATIONAL_DEX[int(internal_id)]
    except KeyError as exc:
        raise ValueError(f"Species interno Gen 1 desconhecido: {internal_id}") from exc


def national_to_gen1_internal(national_id: int) -> int:
    try:
        return NATIONAL_DEX_TO_GEN1_INTERNAL[int(national_id)]
    except KeyError as exc:
        raise ValueError(f"National Dex #{national_id} nao existe como species interno Gen 1 suportado.") from exc


class Gen1Parser:
    generation = 1
    game_id = "pokemon_red"

    def __init__(self) -> None:
        self.path: Path | None = None
        self.data: bytearray | None = None
        self.save_data: SaveData | None = None

    def detect(self, save_path: str | Path) -> bool:
        path = Path(save_path)
        if path.suffix.lower() not in {".sav", ".srm"}:
            return False
        try:
            data = path.read_bytes()
        except OSError:
            return False
        return len(data) == SAVE_SIZE and self._looks_like_gen1(data)

    def load(self, save_path: str | Path) -> SaveData:
        path = Path(save_path)
        data = path.read_bytes()
        if len(data) != SAVE_SIZE or not self._looks_like_gen1(data):
            raise ValueError("Este save nao parece ser Gen 1 Red/Blue/Yellow suportado.")
        self.path = path
        self.data = bytearray(data)
        lower_name = path.name.lower()
        if "yellow" in lower_name:
            self.game_id = "pokemon_yellow"
        elif "blue" in lower_name:
            self.game_id = "pokemon_blue"
        else:
            self.game_id = "pokemon_red"
        self.save_data = SaveData(path, self.generation, self.game_id, self.list_party())
        return self.save_data

    def get_generation(self) -> int:
        return self.generation

    def get_game_id(self) -> str:
        return self.game_id

    def list_party(self) -> list[PokemonSummary]:
        data = self._require_data()
        count = data[PARTY_OFFSET]
        if count > PARTY_CAPACITY:
            raise ValueError("Party Gen 1 invalida.")
        party: list[PokemonSummary] = []
        for index in range(count):
            mon = self._mon_bytes(index)
            species_id = mon[0]
            species_name = GEN1_INTERNAL_NAMES.get(species_id, f"Species #{species_id}")
            nickname = self._decode_text(self._nickname_bytes(index)) or species_name
            ot_name = self._decode_text(self._ot_bytes(index))
            trainer_id = int.from_bytes(mon[0x0C:0x0E], "big")
            level = mon[0x21]
            party.append(
                PokemonSummary(
                    location=f"party:{index}",
                    species_id=species_id,
                    species_name=species_name,
                    level=level,
                    nickname=nickname,
                    ot_name=ot_name,
                    trainer_id=trainer_id,
                    national_dex_id=gen1_internal_to_national(species_id),
                )
            )
        return party

    def list_boxes(self) -> list[PokemonSummary]:
        raise NotImplementedError("Boxes Gen 1 serao implementadas depois da party.")

    def export_pokemon(self, location: str) -> PokemonPayload:
        index = self._party_index(location)
        summary = self.list_party()[index]
        raw = self._mon_bytes(index) + self._ot_bytes(index) + self._nickname_bytes(index)
        raw_data_base64 = base64.b64encode(raw).decode("ascii")
        canonical = self.export_canonical(location)
        compatibility = self.compatibility_report_for(canonical)
        return PokemonPayload(
            generation=1,
            game=self.game_id,
            species_id=summary.species_id,
            species_name=summary.species_name,
            level=summary.level,
            nickname=summary.nickname,
            ot_name=summary.ot_name,
            trainer_id=summary.trainer_id,
            raw_data_base64=raw_data_base64,
            display_summary=summary.display_summary,
            checksum=f"{self._checksum():02x}",
            metadata={"location": location, "format": "gen1-party-v1"},
            canonical=canonical.to_dict(),
            raw={"format": "gen1-party-v1", "data_base64": raw_data_base64, "checksum": f"{self._checksum():02x}"},
            compatibility_report=compatibility.to_dict(),
        )

    def export_canonical(self, location: str) -> CanonicalPokemon:
        index = self._party_index(location)
        summary = self.list_party()[index]
        mon = self._mon_bytes(index)
        raw = mon + self._ot_bytes(index) + self._nickname_bytes(index)
        moves = [CanonicalMove(move_id=move_id, source_generation=1) for move_id in mon[0x08:0x0C] if move_id]
        return CanonicalPokemon(
            source_generation=1,
            source_game=self.game_id,
            species_national_id=gen1_internal_to_national(summary.species_id),
            species_name=summary.species_name,
            nickname=summary.nickname,
            level=summary.level,
            ot_name=summary.ot_name,
            trainer_id=summary.trainer_id,
            experience=int.from_bytes(mon[0x0E:0x11], "big"),
            moves=moves,
            original_data=CanonicalOriginalData(
                generation=1,
                game=self.game_id,
                format="gen1-party-v1",
                raw_data_base64=base64.b64encode(raw).decode("ascii"),
                checksum=f"{self._checksum():02x}",
                location=location,
            ),
            metadata={"source_species_id_space": "gen1_internal", "source_species_id": summary.species_id},
        )

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        self.remove_or_replace_sent_pokemon(location, payload)

    def import_canonical(self, location: str, canonical_pokemon: CanonicalPokemon) -> None:
        built = self.build_party_mon_from_canonical(canonical_pokemon)
        self.write_party_mon(location, built)

    def build_party_mon_from_canonical(self, canonical_pokemon: CanonicalPokemon) -> bytes:
        self.validate_can_write("party:0", canonical_pokemon)
        mon = bytearray(PARTY_MON_SIZE)
        national_id = canonical_pokemon.species.national_dex_id
        mon[0] = national_to_gen1_internal(national_id)
        mon[0x03] = max(1, min(100, canonical_pokemon.level))
        for offset, move in enumerate(canonical_pokemon.moves[:4]):
            mon[0x08 + offset] = move.move_id if move.move_id <= 165 else 0
        mon[0x0C:0x0E] = (int(canonical_pokemon.trainer_id) & 0xFFFF).to_bytes(2, "big", signed=False)
        experience = int(canonical_pokemon.experience or 0)
        mon[0x0E:0x11] = max(0, min(0xFFFFFF, experience)).to_bytes(3, "big")
        mon[0x21] = max(1, min(100, canonical_pokemon.level))
        ot = self._encode_text(canonical_pokemon.ot_name or "TRAINER")
        nickname = self._encode_text(canonical_pokemon.nickname or canonical_pokemon.species.name)
        return bytes(mon) + ot + nickname

    def write_party_mon(self, location: str, built_mon: bytes) -> None:
        if len(built_mon) != RAW_PAYLOAD_SIZE:
            raise ValueError("Struct Gen 1 canonico tem tamanho invalido.")
        index = self._party_index(location)
        data = self._require_data()
        if index >= data[PARTY_OFFSET]:
            raise ValueError("Indice de party fora da quantidade atual.")
        mon = built_mon[:PARTY_MON_SIZE]
        data[PARTY_OFFSET + 1 + index] = mon[0]
        self._set_mon_bytes(index, mon)
        self._set_ot_bytes(index, built_mon[PARTY_MON_SIZE : PARTY_MON_SIZE + NAME_SIZE])
        self._set_nickname_bytes(index, built_mon[PARTY_MON_SIZE + NAME_SIZE :])
        self.mark_pokedex_caught(gen1_internal_to_national(mon[0]))

    def validate_can_write(self, location: str, canonical_pokemon: CanonicalPokemon) -> None:
        self._party_index(location)
        if canonical_pokemon.metadata.get("is_egg"):
            raise ValueError("Egg nao pode ser importado para Gen 1.")
        national_to_gen1_internal(canonical_pokemon.species.national_dex_id)
        invalid_moves = [move.move_id for move in canonical_pokemon.moves if move.move_id and move.move_id > 165]
        if invalid_moves:
            raise ValueError(f"Moves incompatíveis com Gen 1: {invalid_moves}")
        if canonical_pokemon.held_item is not None:
            raise ValueError("Gen 1 nao suporta held item.")

    def can_import_canonical(self, canonical_pokemon: CanonicalPokemon) -> bool:
        return self.compatibility_report_for(canonical_pokemon).compatible

    def compatibility_report_for(self, canonical_pokemon: CanonicalPokemon) -> CompatibilityReport:
        return build_compatibility_report(canonical_pokemon, self.generation, cross_generation_enabled=False)

    def get_species_id(self, location: str) -> int:
        return self._mon_bytes(self._party_index(location))[0]

    def set_species_id(self, location: str, species_id: int) -> None:
        index = self._party_index(location)
        species_id = int(species_id)
        if species_id not in GEN1_INTERNAL_TO_NATIONAL_DEX:
            raise ValueError("Species interno Gen 1 invalido.")
        data = self._require_data()
        mon = bytearray(self._mon_bytes(index))
        mon[0] = species_id
        data[PARTY_OFFSET + 1 + index] = species_id
        self._set_mon_bytes(index, bytes(mon))
        self.recalculate_checksums()

    def get_held_item_id(self, location: str) -> int | None:
        self._party_index(location)
        return None

    def set_held_item_id(self, location: str, item_id: int) -> None:
        self._party_index(location)
        raise ValueError("Gen 1 nao possui held item.")

    def clear_held_item(self, location: str) -> None:
        self._party_index(location)

    def mark_pokedex_seen(self, national_dex_id: int) -> None:
        self._set_pokedex_bit(POKEDEX_SEEN_OFFSET, national_dex_id)
        self.recalculate_checksums()

    def mark_pokedex_caught(self, national_dex_id: int) -> None:
        self._set_pokedex_bit(POKEDEX_OWNED_OFFSET, national_dex_id)
        self._set_pokedex_bit(POKEDEX_SEEN_OFFSET, national_dex_id)
        self.recalculate_checksums()

    def is_pokedex_seen(self, national_dex_id: int) -> bool:
        return self._get_pokedex_bit(POKEDEX_SEEN_OFFSET, national_dex_id)

    def is_pokedex_caught(self, national_dex_id: int) -> bool:
        return self._get_pokedex_bit(POKEDEX_OWNED_OFFSET, national_dex_id)

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        if received_payload.generation != 1:
            raise ValueError(
                "Payload recebido nao e Gen 1. Raw payload de outra geracao nao pode ser escrito neste save; "
                "cross-generation exige payload canonico e conversor local."
            )
        index = self._party_index(location)
        data = self._require_data()
        if index >= data[PARTY_OFFSET]:
            raise ValueError("Indice de party fora da quantidade atual.")
        raw = base64.b64decode(received_payload.raw_data_base64)
        if len(raw) != RAW_PAYLOAD_SIZE:
            raise ValueError("Payload Gen 1 invalido: tamanho inesperado.")
        mon = raw[:PARTY_MON_SIZE]
        species_id = mon[0]
        if species_id <= 0:
            raise ValueError("Payload Gen 1 invalido: species_id vazio.")
        data[PARTY_OFFSET + 1 + index] = species_id
        self._set_mon_bytes(index, mon)
        self._set_ot_bytes(index, raw[PARTY_MON_SIZE : PARTY_MON_SIZE + NAME_SIZE])
        self._set_nickname_bytes(index, raw[PARTY_MON_SIZE + NAME_SIZE :])
        self.mark_pokedex_caught(gen1_internal_to_national(species_id))

    def validate(self) -> bool:
        data = self._require_data()
        return self._looks_like_gen1(bytes(data))

    def recalculate_checksums(self) -> None:
        self._require_data()[CHECKSUM_OFFSET] = self._checksum()

    def save(self, save_path: str | Path) -> None:
        if not self.validate():
            raise ValueError("Save Gen 1 nao passou na validacao antes da gravacao.")
        Path(save_path).write_bytes(bytes(self._require_data()))

    def _looks_like_gen1(self, data: bytes) -> bool:
        count = data[PARTY_OFFSET]
        if count > PARTY_CAPACITY:
            return False
        if data[PARTY_OFFSET + 1 + count] != 0xFF:
            return False
        return self._calc_checksum(data) == data[CHECKSUM_OFFSET]

    def _checksum(self) -> int:
        return self._calc_checksum(bytes(self._require_data()))

    def _calc_checksum(self, data: bytes) -> int:
        value = 0xFF
        for byte in data[CHECKSUM_START : CHECKSUM_END + 1]:
            value = (value - byte) & 0xFF
        return value

    def _get_pokedex_bit(self, offset: int, national_dex_id: int) -> bool:
        byte_offset, mask = self._pokedex_byte_and_mask(national_dex_id)
        return bool(self._require_data()[offset + byte_offset] & mask)

    def _set_pokedex_bit(self, offset: int, national_dex_id: int) -> None:
        byte_offset, mask = self._pokedex_byte_and_mask(national_dex_id)
        self._require_data()[offset + byte_offset] |= mask

    def _pokedex_byte_and_mask(self, national_dex_id: int) -> tuple[int, int]:
        national_to_gen1_internal(national_dex_id)
        dex_index = int(national_dex_id) - 1
        byte_offset = dex_index >> 3
        if byte_offset < 0 or byte_offset >= POKEDEX_SIZE:
            raise ValueError("National Dex fora do intervalo da Pokédex Gen 1.")
        return byte_offset, 1 << (dex_index & 7)

    def _mon_bytes(self, index: int) -> bytes:
        start = PARTY_MON_OFFSET + index * PARTY_MON_SIZE
        return bytes(self._require_data()[start : start + PARTY_MON_SIZE])

    def _set_mon_bytes(self, index: int, value: bytes) -> None:
        start = PARTY_MON_OFFSET + index * PARTY_MON_SIZE
        self._require_data()[start : start + PARTY_MON_SIZE] = value

    def _ot_bytes(self, index: int) -> bytes:
        start = PARTY_OT_OFFSET + index * NAME_SIZE
        return bytes(self._require_data()[start : start + NAME_SIZE])

    def _set_ot_bytes(self, index: int, value: bytes) -> None:
        start = PARTY_OT_OFFSET + index * NAME_SIZE
        self._require_data()[start : start + NAME_SIZE] = value

    def _nickname_bytes(self, index: int) -> bytes:
        start = PARTY_NICK_OFFSET + index * NAME_SIZE
        return bytes(self._require_data()[start : start + NAME_SIZE])

    def _set_nickname_bytes(self, index: int, value: bytes) -> None:
        start = PARTY_NICK_OFFSET + index * NAME_SIZE
        self._require_data()[start : start + NAME_SIZE] = value

    def _party_index(self, location: str) -> int:
        if not location.startswith("party:"):
            raise ValueError("Gen 1 suporta apenas party:N nesta versao.")
        index = int(location.split(":", 1)[1])
        if index < 0 or index >= PARTY_CAPACITY:
            raise ValueError("Indice de party invalido.")
        return index

    def _decode_text(self, raw: bytes) -> str:
        chars = []
        for byte in raw:
            if byte in {0x50, 0x00, 0xFF}:
                break
            if 0x80 <= byte <= 0x99:
                chars.append(chr(ord("A") + byte - 0x80))
            elif 0xA0 <= byte <= 0xB9:
                chars.append(chr(ord("a") + byte - 0xA0))
            elif byte == 0x7F:
                chars.append(" ")
            elif byte == 0xE3:
                chars.append("-")
            elif 0xF6 <= byte <= 0xFF:
                chars.append(str(byte - 0xF6))
            else:
                chars.append("?")
        return "".join(chars).strip()

    def _encode_text(self, value: str) -> bytes:
        encoded = bytearray([0x50] * NAME_SIZE)
        for index, char in enumerate(value[:10]):
            if "A" <= char <= "Z":
                encoded[index] = 0x80 + ord(char) - ord("A")
            elif "a" <= char <= "z":
                encoded[index] = 0xA0 + ord(char) - ord("a")
            elif "0" <= char <= "9":
                encoded[index] = 0xF6 + int(char)
            elif char == " ":
                encoded[index] = 0x7F
            elif char == "-":
                encoded[index] = 0xE3
            else:
                encoded[index] = 0x50
        return bytes(encoded)

    def _require_data(self) -> bytearray:
        if self.data is None:
            raise RuntimeError("Parser Gen 1 ainda nao carregou um save.")
        return self.data
