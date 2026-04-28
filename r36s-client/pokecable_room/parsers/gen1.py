from __future__ import annotations

import base64
from pathlib import Path

from .base import PokemonPayload, PokemonSummary, SaveData


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
                )
            )
        return party

    def list_boxes(self) -> list[PokemonSummary]:
        raise NotImplementedError("Boxes Gen 1 serao implementadas depois da party.")

    def export_pokemon(self, location: str) -> PokemonPayload:
        index = self._party_index(location)
        summary = self.list_party()[index]
        raw = self._mon_bytes(index) + self._ot_bytes(index) + self._nickname_bytes(index)
        return PokemonPayload(
            generation=1,
            game=self.game_id,
            species_id=summary.species_id,
            species_name=summary.species_name,
            level=summary.level,
            nickname=summary.nickname,
            ot_name=summary.ot_name,
            trainer_id=summary.trainer_id,
            raw_data_base64=base64.b64encode(raw).decode("ascii"),
            display_summary=summary.display_summary,
            checksum=f"{self._checksum():02x}",
            metadata={"location": location, "format": "gen1-party-v1"},
        )

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        self.remove_or_replace_sent_pokemon(location, payload)

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        if received_payload.generation != 1:
            raise ValueError("Payload recebido nao e Gen 1.")
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
        self.recalculate_checksums()

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

    def _require_data(self) -> bytearray:
        if self.data is None:
            raise RuntimeError("Parser Gen 1 ainda nao carregou um save.")
        return self.data
