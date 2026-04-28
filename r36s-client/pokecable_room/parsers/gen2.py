from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from pokecable_room.canonical import CanonicalItem, CanonicalMove, CanonicalOriginalData, CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport, build_compatibility_report

from .base import PokemonPayload, PokemonSummary, SaveData


CRYSTAL_PARTY_OFFSET = 0x2865
CRYSTAL_PRIMARY_START = 0x2009
CRYSTAL_PRIMARY_END = 0x2B82
CRYSTAL_PRIMARY_CHECKSUM = 0x2D0D
CRYSTAL_SECONDARY_START = 0x1209
CRYSTAL_SECONDARY_END = 0x1D82
CRYSTAL_SECONDARY_CHECKSUM = 0x1F0D
GOLD_SILVER_PARTY_OFFSET = 0x288A
GOLD_SILVER_PRIMARY_START = 0x2009
GOLD_SILVER_PRIMARY_END = 0x2D68
GOLD_SILVER_PRIMARY_CHECKSUM = 0x2D69
PARTY_CAPACITY = 6
PARTY_MON_SIZE = 48
NAME_SIZE = 11
PARTY_HEADER_SIZE = 1 + PARTY_CAPACITY + 1
PARTY_DATA_OFFSET = CRYSTAL_PARTY_OFFSET + PARTY_HEADER_SIZE
PARTY_OT_OFFSET = PARTY_DATA_OFFSET + PARTY_CAPACITY * PARTY_MON_SIZE
PARTY_NICK_OFFSET = PARTY_OT_OFFSET + PARTY_CAPACITY * NAME_SIZE
RAW_PAYLOAD_SIZE = PARTY_MON_SIZE + NAME_SIZE + NAME_SIZE


@dataclass(slots=True)
class Gen2Layout:
    name: str
    game_id: str
    party_offset: int
    primary_start: int
    primary_end: int
    primary_checksum: int
    secondary_start: int | None = None
    secondary_end: int | None = None
    secondary_checksum: int | None = None

    @property
    def party_data_offset(self) -> int:
        return self.party_offset + PARTY_HEADER_SIZE

    @property
    def party_ot_offset(self) -> int:
        return self.party_data_offset + PARTY_CAPACITY * PARTY_MON_SIZE

    @property
    def party_nick_offset(self) -> int:
        return self.party_ot_offset + PARTY_CAPACITY * NAME_SIZE


CRYSTAL_LAYOUT = Gen2Layout(
    name="crystal",
    game_id="pokemon_crystal",
    party_offset=CRYSTAL_PARTY_OFFSET,
    primary_start=CRYSTAL_PRIMARY_START,
    primary_end=CRYSTAL_PRIMARY_END,
    primary_checksum=CRYSTAL_PRIMARY_CHECKSUM,
    secondary_start=CRYSTAL_SECONDARY_START,
    secondary_end=CRYSTAL_SECONDARY_END,
    secondary_checksum=CRYSTAL_SECONDARY_CHECKSUM,
)
GOLD_SILVER_LAYOUT = Gen2Layout(
    name="gold_silver",
    game_id="pokemon_gold",
    party_offset=GOLD_SILVER_PARTY_OFFSET,
    primary_start=GOLD_SILVER_PRIMARY_START,
    primary_end=GOLD_SILVER_PRIMARY_END,
    primary_checksum=GOLD_SILVER_PRIMARY_CHECKSUM,
)


GEN2_SPECIES = {
    1: "Bulbasaur",
    2: "Ivysaur",
    3: "Venusaur",
    4: "Charmander",
    5: "Charmeleon",
    6: "Charizard",
    7: "Squirtle",
    8: "Wartortle",
    9: "Blastoise",
    10: "Caterpie",
    11: "Metapod",
    12: "Butterfree",
    13: "Weedle",
    14: "Kakuna",
    15: "Beedrill",
    16: "Pidgey",
    17: "Pidgeotto",
    18: "Pidgeot",
    19: "Rattata",
    20: "Raticate",
    21: "Spearow",
    22: "Fearow",
    23: "Ekans",
    24: "Arbok",
    25: "Pikachu",
    26: "Raichu",
    27: "Sandshrew",
    28: "Sandslash",
    29: "Nidoran F",
    30: "Nidorina",
    31: "Nidoqueen",
    32: "Nidoran M",
    33: "Nidorino",
    34: "Nidoking",
    35: "Clefairy",
    36: "Clefable",
    37: "Vulpix",
    38: "Ninetales",
    39: "Jigglypuff",
    40: "Wigglytuff",
    41: "Zubat",
    42: "Golbat",
    43: "Oddish",
    44: "Gloom",
    45: "Vileplume",
    46: "Paras",
    47: "Parasect",
    48: "Venonat",
    49: "Venomoth",
    50: "Diglett",
    51: "Dugtrio",
    52: "Meowth",
    53: "Persian",
    54: "Psyduck",
    55: "Golduck",
    56: "Mankey",
    57: "Primeape",
    58: "Growlithe",
    59: "Arcanine",
    60: "Poliwag",
    61: "Poliwhirl",
    62: "Poliwrath",
    63: "Abra",
    64: "Kadabra",
    65: "Alakazam",
    66: "Machop",
    67: "Machoke",
    68: "Machamp",
    69: "Bellsprout",
    70: "Weepinbell",
    71: "Victreebel",
    72: "Tentacool",
    73: "Tentacruel",
    74: "Geodude",
    75: "Graveler",
    76: "Golem",
    77: "Ponyta",
    78: "Rapidash",
    79: "Slowpoke",
    80: "Slowbro",
    81: "Magnemite",
    82: "Magneton",
    83: "Farfetch'd",
    84: "Doduo",
    85: "Dodrio",
    86: "Seel",
    87: "Dewgong",
    88: "Grimer",
    89: "Muk",
    90: "Shellder",
    91: "Cloyster",
    92: "Gastly",
    93: "Haunter",
    94: "Gengar",
    95: "Onix",
    96: "Drowzee",
    97: "Hypno",
    98: "Krabby",
    99: "Kingler",
    100: "Voltorb",
    101: "Electrode",
    102: "Exeggcute",
    103: "Exeggutor",
    104: "Cubone",
    105: "Marowak",
    106: "Hitmonlee",
    107: "Hitmonchan",
    108: "Lickitung",
    109: "Koffing",
    110: "Weezing",
    111: "Rhyhorn",
    112: "Rhydon",
    113: "Chansey",
    114: "Tangela",
    115: "Kangaskhan",
    116: "Horsea",
    117: "Seadra",
    118: "Goldeen",
    119: "Seaking",
    120: "Staryu",
    121: "Starmie",
    122: "Mr. Mime",
    123: "Scyther",
    124: "Jynx",
    125: "Electabuzz",
    126: "Magmar",
    127: "Pinsir",
    128: "Tauros",
    129: "Magikarp",
    130: "Gyarados",
    131: "Lapras",
    132: "Ditto",
    133: "Eevee",
    134: "Vaporeon",
    135: "Jolteon",
    136: "Flareon",
    137: "Porygon",
    138: "Omanyte",
    139: "Omastar",
    140: "Kabuto",
    141: "Kabutops",
    142: "Aerodactyl",
    143: "Snorlax",
    144: "Articuno",
    145: "Zapdos",
    146: "Moltres",
    147: "Dratini",
    148: "Dragonair",
    149: "Dragonite",
    150: "Mewtwo",
    151: "Mew",
    152: "Chikorita",
    153: "Bayleef",
    154: "Meganium",
    155: "Cyndaquil",
    156: "Quilava",
    157: "Typhlosion",
    158: "Totodile",
    159: "Croconaw",
    160: "Feraligatr",
    161: "Sentret",
    162: "Furret",
    163: "Hoothoot",
    164: "Noctowl",
    165: "Ledyba",
    166: "Ledian",
    167: "Spinarak",
    168: "Ariados",
    169: "Crobat",
    170: "Chinchou",
    171: "Lanturn",
    172: "Pichu",
    173: "Cleffa",
    174: "Igglybuff",
    175: "Togepi",
    176: "Togetic",
    177: "Natu",
    178: "Xatu",
    179: "Mareep",
    180: "Flaaffy",
    181: "Ampharos",
    182: "Bellossom",
    183: "Marill",
    184: "Azumarill",
    185: "Sudowoodo",
    186: "Politoed",
    187: "Hoppip",
    188: "Skiploom",
    189: "Jumpluff",
    190: "Aipom",
    191: "Sunkern",
    192: "Sunflora",
    193: "Yanma",
    194: "Wooper",
    195: "Quagsire",
    196: "Espeon",
    197: "Umbreon",
    198: "Murkrow",
    199: "Slowking",
    200: "Misdreavus",
    201: "Unown",
    202: "Wobbuffet",
    203: "Girafarig",
    204: "Pineco",
    205: "Forretress",
    206: "Dunsparce",
    207: "Gligar",
    208: "Steelix",
    209: "Snubbull",
    210: "Granbull",
    211: "Qwilfish",
    212: "Scizor",
    213: "Shuckle",
    214: "Heracross",
    215: "Sneasel",
    216: "Teddiursa",
    217: "Ursaring",
    218: "Slugma",
    219: "Magcargo",
    220: "Swinub",
    221: "Piloswine",
    222: "Corsola",
    223: "Remoraid",
    224: "Octillery",
    225: "Delibird",
    226: "Mantine",
    227: "Skarmory",
    228: "Houndour",
    229: "Houndoom",
    230: "Kingdra",
    231: "Phanpy",
    232: "Donphan",
    233: "Porygon2",
    234: "Stantler",
    235: "Smeargle",
    236: "Tyrogue",
    237: "Hitmontop",
    238: "Smoochum",
    239: "Elekid",
    240: "Magby",
    241: "Miltank",
    242: "Blissey",
    243: "Raikou",
    244: "Entei",
    245: "Suicune",
    246: "Larvitar",
    247: "Pupitar",
    248: "Tyranitar",
    249: "Lugia",
    250: "Ho-Oh",
    251: "Celebi",
}


class Gen2Parser:
    generation = 2
    game_id = "pokemon_crystal"

    def __init__(self) -> None:
        self.path: Path | None = None
        self.data: bytearray | None = None
        self.save_data: SaveData | None = None
        self.layout: Gen2Layout = CRYSTAL_LAYOUT

    def detect(self, save_path: str | Path) -> bool:
        path = Path(save_path)
        if path.suffix.lower() not in {".sav", ".srm"}:
            return False
        try:
            data = path.read_bytes()
        except OSError:
            return False
        if len(data) < 0x8000:
            return False
        return self._detect_layout(data) is not None

    def load(self, save_path: str | Path) -> SaveData:
        path = Path(save_path)
        data = path.read_bytes()
        if len(data) < 0x8000:
            raise ValueError("Save Gen 2 precisa ter pelo menos 32768 bytes.")
        layout = self._detect_layout(data)
        if layout is None:
            raise ValueError("Este .sav/.srm nao parece ser um save Gold/Silver/Crystal Gen 2 suportado.")
        self.path = path
        self.data = bytearray(data)
        self.layout = layout
        if layout is GOLD_SILVER_LAYOUT and "silver" in path.name.lower():
            self.game_id = "pokemon_silver"
        else:
            self.game_id = layout.game_id
        self.save_data = SaveData(path, self.generation, self.game_id, self.list_party())
        return self.save_data

    def get_generation(self) -> int:
        return self.generation

    def get_game_id(self) -> str:
        return self.game_id

    def list_party(self) -> list[PokemonSummary]:
        data = self._require_data()
        layout = self._require_layout()
        count = data[layout.party_offset]
        if count > PARTY_CAPACITY:
            raise ValueError("Party Gen 2 invalida: count maior que 6.")
        party: list[PokemonSummary] = []
        for index in range(count):
            species_entry = data[layout.party_offset + 1 + index]
            mon = self._mon_bytes(index)
            species_id = mon[0]
            is_egg = species_entry == 0xFD
            species_name = "Egg" if is_egg else GEN2_SPECIES.get(species_id, f"Species #{species_id}")
            nickname = self._decode_text(self._nickname_bytes(index)) or species_name
            ot_name = self._decode_text(self._ot_bytes(index))
            trainer_id = int.from_bytes(mon[0x06:0x08], "big")
            level = mon[0x1F]
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
        raise NotImplementedError("Boxes Gen 2 serao adicionadas depois da party.")

    def export_pokemon(self, location: str) -> PokemonPayload:
        index = self._party_index(location)
        data = self._require_data()
        layout = self._require_layout()
        count = data[layout.party_offset]
        if index >= count:
            raise ValueError("Localizacao de party fora da quantidade atual.")
        species_entry = data[layout.party_offset + 1 + index]
        if species_entry == 0xFD:
            raise ValueError("Ovos ainda nao sao suportados para troca real.")
        mon = self._mon_bytes(index)
        raw = mon + self._ot_bytes(index) + self._nickname_bytes(index)
        summary = self.list_party()[index]
        raw_data_base64 = base64.b64encode(raw).decode("ascii")
        canonical = self.export_canonical(location)
        compatibility = self.compatibility_report_for(canonical)
        return PokemonPayload(
            generation=2,
            game=self.game_id,
            species_id=summary.species_id,
            species_name=summary.species_name,
            level=summary.level,
            nickname=summary.nickname,
            ot_name=summary.ot_name,
            trainer_id=summary.trainer_id,
            raw_data_base64=raw_data_base64,
            display_summary=summary.display_summary,
            checksum=f"{self._stored_checksum(layout.primary_checksum):04x}",
            metadata={"location": location, "format": f"gen2-{layout.name}-party-v1"},
            canonical=canonical.to_dict(),
            raw={
                "format": f"gen2-{layout.name}-party-v1",
                "data_base64": raw_data_base64,
                "checksum": f"{self._stored_checksum(layout.primary_checksum):04x}",
            },
            compatibility_report=compatibility.to_dict(),
        )

    def export_canonical(self, location: str) -> CanonicalPokemon:
        index = self._party_index(location)
        summary = self.list_party()[index]
        mon = self._mon_bytes(index)
        raw = mon + self._ot_bytes(index) + self._nickname_bytes(index)
        held_item_id = mon[0x01] or None
        moves = [CanonicalMove(move_id=move_id, source_generation=2) for move_id in mon[0x02:0x06] if move_id]
        return CanonicalPokemon(
            source_generation=2,
            source_game=self.game_id,
            species_national_id=summary.species_id,
            species_name=summary.species_name,
            nickname=summary.nickname,
            level=summary.level,
            ot_name=summary.ot_name,
            trainer_id=summary.trainer_id,
            experience=int.from_bytes(mon[0x08:0x0B], "big"),
            moves=moves,
            held_item=CanonicalItem(item_id=held_item_id, source_generation=2) if held_item_id is not None else None,
            original_data=CanonicalOriginalData(
                generation=2,
                game=self.game_id,
                format=f"gen2-{self._require_layout().name}-party-v1",
                raw_data_base64=base64.b64encode(raw).decode("ascii"),
                checksum=f"{self._stored_checksum(self._require_layout().primary_checksum):04x}",
                location=location,
            ),
            metadata={"source_species_id_space": "national_dex"},
        )

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        self.remove_or_replace_sent_pokemon(location, payload)

    def import_canonical(self, location: str, canonical_pokemon: CanonicalPokemon) -> None:
        if not self.can_import_canonical(canonical_pokemon):
            report = self.compatibility_report_for(canonical_pokemon)
            raise ValueError("; ".join(report.blocking_reasons) or "Pokemon canonico nao pode ser importado em Gen 2.")
        if canonical_pokemon.original_data is None or canonical_pokemon.original_data.raw_data_base64 is None:
            raise ValueError("Importacao canonica Gen 2 exige raw original enquanto conversor seguro nao esta habilitado.")
        payload = PokemonPayload(
            generation=2,
            game=canonical_pokemon.source_game,
            species_id=canonical_pokemon.species_national_id,
            species_name=canonical_pokemon.species_name,
            level=canonical_pokemon.level,
            nickname=canonical_pokemon.nickname,
            ot_name=canonical_pokemon.ot_name,
            trainer_id=canonical_pokemon.trainer_id,
            raw_data_base64=canonical_pokemon.original_data.raw_data_base64,
            display_summary=f"{canonical_pokemon.species_name} Lv. {canonical_pokemon.level}",
        )
        self.import_pokemon(location, payload)

    def can_import_canonical(self, canonical_pokemon: CanonicalPokemon) -> bool:
        return self.compatibility_report_for(canonical_pokemon).compatible

    def compatibility_report_for(self, canonical_pokemon: CanonicalPokemon) -> CompatibilityReport:
        return build_compatibility_report(canonical_pokemon, self.generation, cross_generation_enabled=False)

    def get_species_id(self, location: str) -> int:
        return self._mon_bytes(self._party_index(location))[0]

    def set_species_id(self, location: str, species_id: int) -> None:
        index = self._party_index(location)
        species_id = int(species_id)
        if species_id < 1 or species_id > 251:
            raise ValueError("Species Gen 2 precisa estar no intervalo 1..251.")
        mon = bytearray(self._mon_bytes(index))
        mon[0] = species_id
        self._require_data()[self._require_layout().party_offset + 1 + index] = species_id
        self._set_mon_bytes(index, bytes(mon))
        self.recalculate_checksums()

    def get_held_item_id(self, location: str) -> int | None:
        held_item_id = self._mon_bytes(self._party_index(location))[0x01]
        return held_item_id or None

    def set_held_item_id(self, location: str, item_id: int) -> None:
        index = self._party_index(location)
        item_id = int(item_id)
        if item_id < 0 or item_id > 255:
            raise ValueError("Held item Gen 2 precisa caber em um byte.")
        mon = bytearray(self._mon_bytes(index))
        mon[0x01] = item_id
        self._set_mon_bytes(index, bytes(mon))
        self.recalculate_checksums()

    def clear_held_item(self, location: str) -> None:
        self.set_held_item_id(location, 0)

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        if received_payload.generation != 2:
            raise ValueError(
                f"Payload recebido e Gen {received_payload.generation}, mas o save local e Gen 2. "
                "Cross-generation esta protegido por feature guard enquanto o conversor local Gen 2 esta em desenvolvimento."
            )
        index = self._party_index(location)
        data = self._require_data()
        layout = self._require_layout()
        count = data[layout.party_offset]
        if index >= count:
            raise ValueError("Localizacao de party fora da quantidade atual.")
        raw = base64.b64decode(received_payload.raw_data_base64)
        if len(raw) != RAW_PAYLOAD_SIZE:
            raise ValueError("Payload Gen 2 invalido: tamanho bruto inesperado.")
        mon = raw[:PARTY_MON_SIZE]
        ot_name = raw[PARTY_MON_SIZE : PARTY_MON_SIZE + NAME_SIZE]
        nickname = raw[PARTY_MON_SIZE + NAME_SIZE :]
        species_id = mon[0]
        if species_id <= 0 or species_id > 251:
            raise ValueError("Payload Gen 2 invalido: species_id fora do intervalo 1..251.")
        data[layout.party_offset + 1 + index] = species_id
        self._set_mon_bytes(index, mon)
        self._set_ot_bytes(index, ot_name)
        self._set_nickname_bytes(index, nickname)
        self.recalculate_checksums()

    def validate(self) -> bool:
        data = self._require_data()
        return self._looks_like(bytes(data), self._require_layout())

    def recalculate_checksums(self) -> None:
        data = self._require_data()
        layout = self._require_layout()
        if layout.secondary_start is not None and layout.secondary_end is not None and layout.secondary_checksum is not None:
            primary = data[layout.primary_start : layout.primary_end + 1]
            data[layout.secondary_start : layout.secondary_end + 1] = primary
            self._write_checksum(layout.secondary_checksum, self._sum_range(layout.secondary_start, layout.secondary_end))
        self._write_checksum(layout.primary_checksum, self._sum_range(layout.primary_start, layout.primary_end))

    def save(self, save_path: str | Path) -> None:
        data = self._require_data()
        if not self.validate():
            raise ValueError("Save Gen 2 nao passou na validacao antes da gravacao.")
        Path(save_path).write_bytes(bytes(data))

    def _detect_layout(self, data: bytes) -> Gen2Layout | None:
        for layout in (CRYSTAL_LAYOUT, GOLD_SILVER_LAYOUT):
            if self._looks_like(data, layout):
                return layout
        return None

    def _looks_like(self, data: bytes, layout: Gen2Layout) -> bool:
        count = data[layout.party_offset]
        if count > PARTY_CAPACITY:
            return False
        if data[layout.party_offset + 1 + count] != 0xFF:
            return False
        primary = sum(data[layout.primary_start : layout.primary_end + 1]) & 0xFFFF
        if primary == int.from_bytes(data[layout.primary_checksum : layout.primary_checksum + 2], "little"):
            return True
        if layout.secondary_start is None or layout.secondary_end is None or layout.secondary_checksum is None:
            return False
        secondary = sum(data[layout.secondary_start : layout.secondary_end + 1]) & 0xFFFF
        return secondary == int.from_bytes(data[layout.secondary_checksum : layout.secondary_checksum + 2], "little")

    def _sum_range(self, start: int, end: int) -> int:
        data = self._require_data()
        return sum(data[start : end + 1]) & 0xFFFF

    def _stored_checksum(self, offset: int) -> int:
        data = self._require_data()
        return int.from_bytes(data[offset : offset + 2], "little")

    def _write_checksum(self, offset: int, value: int) -> None:
        data = self._require_data()
        data[offset : offset + 2] = value.to_bytes(2, "little")

    def _mon_bytes(self, index: int) -> bytes:
        data = self._require_data()
        start = self._require_layout().party_data_offset + index * PARTY_MON_SIZE
        return bytes(data[start : start + PARTY_MON_SIZE])

    def _set_mon_bytes(self, index: int, value: bytes) -> None:
        data = self._require_data()
        start = self._require_layout().party_data_offset + index * PARTY_MON_SIZE
        data[start : start + PARTY_MON_SIZE] = value

    def _ot_bytes(self, index: int) -> bytes:
        data = self._require_data()
        start = self._require_layout().party_ot_offset + index * NAME_SIZE
        return bytes(data[start : start + NAME_SIZE])

    def _set_ot_bytes(self, index: int, value: bytes) -> None:
        data = self._require_data()
        start = self._require_layout().party_ot_offset + index * NAME_SIZE
        data[start : start + NAME_SIZE] = value

    def _nickname_bytes(self, index: int) -> bytes:
        data = self._require_data()
        start = self._require_layout().party_nick_offset + index * NAME_SIZE
        return bytes(data[start : start + NAME_SIZE])

    def _set_nickname_bytes(self, index: int, value: bytes) -> None:
        data = self._require_data()
        start = self._require_layout().party_nick_offset + index * NAME_SIZE
        data[start : start + NAME_SIZE] = value

    def _party_index(self, location: str) -> int:
        if not location.startswith("party:"):
            raise ValueError("Gen 2 real suporta apenas localizacao party:N nesta fase.")
        index = int(location.split(":", 1)[1])
        if index < 0 or index >= PARTY_CAPACITY:
            raise ValueError("Indice de party invalido.")
        return index

    def _decode_text(self, raw: bytes) -> str:
        chars = []
        for byte in raw:
            if byte in {0x50, 0xFF, 0x00}:
                break
            if 0x80 <= byte <= 0x99:
                chars.append(chr(ord("A") + byte - 0x80))
            elif 0xA0 <= byte <= 0xB9:
                chars.append(chr(ord("a") + byte - 0xA0))
            elif byte == 0x7F:
                chars.append(" ")
            elif byte == 0xE0:
                chars.append("'")
            elif byte == 0xE3:
                chars.append("-")
            elif byte == 0xF6:
                chars.append("0")
            elif 0xF7 <= byte <= 0xFF:
                chars.append(str(byte - 0xF6))
            else:
                chars.append("?")
        return "".join(chars).strip()

    def _require_data(self) -> bytearray:
        if self.data is None:
            raise RuntimeError("Parser Gen 2 ainda nao carregou um save.")
        return self.data

    def _require_layout(self) -> Gen2Layout:
        return self.layout
