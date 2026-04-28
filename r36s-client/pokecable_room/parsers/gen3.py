from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from pokecable_room.canonical import CanonicalItem, CanonicalMove, CanonicalOriginalData, CanonicalPokemon
from pokecable_room.compatibility import CompatibilityReport, build_compatibility_report
from pokecable_room.data.items import equivalent_item_id, item_exists
from pokecable_room.data.moves import move_exists
from pokecable_room.data.species import native_to_national, national_to_native

from .base import PokemonPayload, PokemonSummary, SaveData
from .gen2 import GEN2_SPECIES


SECTOR_DATA_SIZE = 3968
SECTOR_SIZE = 4096
SECTORS_PER_SLOT = 14
SECTOR_SIGNATURE = 0x08012025
SECTOR_ID_SAVEBLOCK1_START = 1
PARTY_CAPACITY = 6
PARTY_MON_SIZE = 100
BOX_MON_SIZE = 80
NICKNAME_SIZE = 10
OT_NAME_SIZE = 7
SECURE_OFFSET = 32
SECURE_SIZE = 48

SUBSTRUCT_ORDERS = (
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 2, 1, 3),
    (0, 3, 1, 2),
    (0, 2, 3, 1),
    (0, 3, 2, 1),
    (1, 0, 2, 3),
    (1, 0, 3, 2),
    (2, 0, 1, 3),
    (3, 0, 1, 2),
    (2, 0, 3, 1),
    (3, 0, 2, 1),
    (1, 2, 0, 3),
    (1, 3, 0, 2),
    (2, 1, 0, 3),
    (3, 1, 0, 2),
    (2, 3, 0, 1),
    (3, 2, 0, 1),
    (1, 2, 3, 0),
    (1, 3, 2, 0),
    (2, 1, 3, 0),
    (3, 1, 2, 0),
    (2, 3, 1, 0),
    (3, 2, 1, 0),
)

GEN3_EXTRA_SPECIES = {
    **{value: "Unown" for value in range(252, 277)},
    277: "Treecko",
    278: "Grovyle",
    279: "Sceptile",
    280: "Torchic",
    281: "Combusken",
    282: "Blaziken",
    283: "Mudkip",
    284: "Marshtomp",
    285: "Swampert",
    286: "Poochyena",
    287: "Mightyena",
    288: "Zigzagoon",
    289: "Linoone",
    290: "Wurmple",
    291: "Silcoon",
    292: "Beautifly",
    293: "Cascoon",
    294: "Dustox",
    295: "Lotad",
    296: "Lombre",
    297: "Ludicolo",
    298: "Seedot",
    299: "Nuzleaf",
    300: "Shiftry",
    301: "Nincada",
    302: "Ninjask",
    303: "Shedinja",
    304: "Taillow",
    305: "Swellow",
    306: "Shroomish",
    307: "Breloom",
    308: "Spinda",
    309: "Wingull",
    310: "Pelipper",
    311: "Surskit",
    312: "Masquerain",
    313: "Wailmer",
    314: "Wailord",
    315: "Skitty",
    316: "Delcatty",
    317: "Kecleon",
    318: "Baltoy",
    319: "Claydol",
    320: "Nosepass",
    321: "Torkoal",
    322: "Sableye",
    323: "Barboach",
    324: "Whiscash",
    325: "Luvdisc",
    326: "Corphish",
    327: "Crawdaunt",
    328: "Feebas",
    329: "Milotic",
    330: "Carvanha",
    331: "Sharpedo",
    332: "Trapinch",
    333: "Vibrava",
    334: "Flygon",
    335: "Makuhita",
    336: "Hariyama",
    337: "Electrike",
    338: "Manectric",
    339: "Numel",
    340: "Camerupt",
    341: "Spheal",
    342: "Sealeo",
    343: "Walrein",
    344: "Cacnea",
    345: "Cacturne",
    346: "Snorunt",
    347: "Glalie",
    348: "Lunatone",
    349: "Solrock",
    350: "Azurill",
    351: "Spoink",
    352: "Grumpig",
    353: "Plusle",
    354: "Minun",
    355: "Mawile",
    356: "Meditite",
    357: "Medicham",
    358: "Swablu",
    359: "Altaria",
    360: "Wynaut",
    361: "Duskull",
    362: "Dusclops",
    363: "Roselia",
    364: "Slakoth",
    365: "Vigoroth",
    366: "Slaking",
    367: "Gulpin",
    368: "Swalot",
    369: "Tropius",
    370: "Whismur",
    371: "Loudred",
    372: "Exploud",
    373: "Clamperl",
    374: "Huntail",
    375: "Gorebyss",
    376: "Absol",
    377: "Shuppet",
    378: "Banette",
    379: "Seviper",
    380: "Zangoose",
    381: "Relicanth",
    382: "Aron",
    383: "Lairon",
    384: "Aggron",
    385: "Castform",
    386: "Volbeat",
    387: "Illumise",
    388: "Lileep",
    389: "Cradily",
    390: "Anorith",
    391: "Armaldo",
    392: "Ralts",
    393: "Kirlia",
    394: "Gardevoir",
    395: "Bagon",
    396: "Shelgon",
    397: "Salamence",
    398: "Beldum",
    399: "Metang",
    400: "Metagross",
    401: "Regirock",
    402: "Regice",
    403: "Registeel",
    404: "Kyogre",
    405: "Groudon",
    406: "Rayquaza",
    407: "Latias",
    408: "Latios",
    409: "Jirachi",
    410: "Deoxys",
    411: "Chimecho",
    412: "Egg",
}
GEN3_SPECIES = {**GEN2_SPECIES, **GEN3_EXTRA_SPECIES}

GEN3_TEXT = {
    0x00: " ",
    0x2D: "&",
    0x2E: "+",
    0x35: "=",
    0x36: ";",
    0x51: "?",
    0x52: "!",
    0x5B: "%",
    0x5C: "(",
    0x5D: ")",
    0x85: "<",
    0x86: ">",
    0xA1: "0",
    0xA2: "1",
    0xA3: "2",
    0xA4: "3",
    0xA5: "4",
    0xA6: "5",
    0xA7: "6",
    0xA8: "7",
    0xA9: "8",
    0xAA: "9",
    0xAB: "!",
    0xAC: "?",
    0xAD: ".",
    0xAE: "-",
    0xB8: ",",
    0xBA: "/",
    0xF0: ":",
}
for _index in range(26):
    GEN3_TEXT[0xBB + _index] = chr(ord("A") + _index)
    GEN3_TEXT[0xD5 + _index] = chr(ord("a") + _index)


@dataclass(slots=True)
class SaveSlot:
    base: int
    counter: int
    section_offsets: dict[int, int]


@dataclass(slots=True)
class Gen3Layout:
    name: str
    game_id: str
    party_count_offset: int
    party_offset: int


LAYOUTS = (
    Gen3Layout("rse", "pokemon_emerald", 0x234, 0x238),
    Gen3Layout("frlg", "pokemon_firered", 0x34, 0x38),
)


class Gen3Parser:
    generation = 3
    game_id = "pokemon_emerald"

    def __init__(self) -> None:
        self.path: Path | None = None
        self.data: bytearray | None = None
        self.save_data: SaveData | None = None
        self.slot: SaveSlot | None = None
        self.layout: Gen3Layout | None = None

    def detect(self, save_path: str | Path) -> bool:
        path = Path(save_path)
        if path.suffix.lower() not in {".sav", ".srm"}:
            return False
        try:
            data = path.read_bytes()
        except OSError:
            return False
        return self._detect_slot_and_layout(data) is not None

    def load(self, save_path: str | Path) -> SaveData:
        path = Path(save_path)
        data = path.read_bytes()
        detected = self._detect_slot_and_layout(data)
        if detected is None:
            raise ValueError("Este save nao parece ser Gen 3 Ruby/Sapphire/Emerald/FireRed/LeafGreen suportado.")
        self.path = path
        self.data = bytearray(data)
        self.slot, self.layout = detected
        self.game_id = self._game_id_from_name(path.name, self.layout)
        self.save_data = SaveData(path, self.generation, self.game_id, self.list_party())
        return self.save_data

    def get_generation(self) -> int:
        return self.generation

    def get_game_id(self) -> str:
        return self.game_id

    def list_party(self) -> list[PokemonSummary]:
        data = self._require_data()
        count = self._party_count()
        if count > PARTY_CAPACITY:
            raise ValueError("Party Gen 3 invalida: count maior que 6.")
        party: list[PokemonSummary] = []
        for index in range(count):
            start = self._party_mon_offset(index)
            raw = bytes(data[start : start + PARTY_MON_SIZE])
            details = self._parse_pokemon(raw)
            species_name = "Egg" if details["is_egg"] else GEN3_SPECIES.get(details["species_id"], f"Species #{details['species_id']}")
            nickname = self._decode_text(raw[0x08 : 0x08 + NICKNAME_SIZE]) or species_name
            ot_name = self._decode_text(raw[0x14 : 0x14 + OT_NAME_SIZE])
            party.append(
                PokemonSummary(
                    location=f"party:{index}",
                    species_id=int(details["species_id"]),
                    species_name=species_name,
                    level=raw[0x54],
                    nickname=nickname,
                    ot_name=ot_name,
                    trainer_id=int(details["trainer_id"]),
                )
            )
        return party

    def list_boxes(self) -> list[PokemonSummary]:
        raise NotImplementedError("Boxes Gen 3 serao adicionadas depois da party.")

    def export_pokemon(self, location: str) -> PokemonPayload:
        index = self._party_index(location)
        if index >= self._party_count():
            raise ValueError("Localizacao de party fora da quantidade atual.")
        start = self._party_mon_offset(index)
        raw = bytes(self._require_data()[start : start + PARTY_MON_SIZE])
        details = self._parse_pokemon(raw)
        if details["is_egg"]:
            raise ValueError("Ovos ainda nao sao suportados para troca real.")
        summary = self.list_party()[index]
        raw_data_base64 = base64.b64encode(raw).decode("ascii")
        canonical = self.export_canonical(location)
        compatibility = self.compatibility_report_for(canonical)
        return PokemonPayload(
            generation=3,
            game=self.game_id,
            species_id=summary.species_id,
            species_name=summary.species_name,
            level=summary.level,
            nickname=summary.nickname,
            ot_name=summary.ot_name,
            trainer_id=summary.trainer_id,
            raw_data_base64=raw_data_base64,
            display_summary=summary.display_summary,
            checksum=f"{int(details['checksum']):04x}",
            metadata={"location": location, "format": "gen3-party-v1", "layout": self._require_layout().name},
            canonical=canonical.to_dict(),
            raw={"format": "gen3-party-v1", "data_base64": raw_data_base64, "checksum": f"{int(details['checksum']):04x}"},
            compatibility_report=compatibility.to_dict(),
        )

    def export_canonical(self, location: str) -> CanonicalPokemon:
        index = self._party_index(location)
        if index >= self._party_count():
            raise ValueError("Localizacao de party fora da quantidade atual.")
        start = self._party_mon_offset(index)
        raw = bytes(self._require_data()[start : start + PARTY_MON_SIZE])
        details = self._parse_pokemon(raw)
        summary = self.list_party()[index]
        secure = self._decrypt_secure(raw[:BOX_MON_SIZE])
        growth = self._substruct_offset(raw[:BOX_MON_SIZE], 0)
        attacks = self._substruct_offset(raw[:BOX_MON_SIZE], 1)
        held_item_id = int.from_bytes(secure[growth + 2 : growth + 4], "little") or None
        is_egg = bool(details["is_egg"])
        national_id = 0 if is_egg else native_to_national(3, summary.species_id)
        moves = []
        for offset in range(0, 8, 2):
            move_id = int.from_bytes(secure[attacks + offset : attacks + offset + 2], "little")
            if move_id:
                moves.append(CanonicalMove(move_id=move_id, source_generation=3))
        return CanonicalPokemon(
            source_generation=3,
            source_game=self.game_id,
            species_national_id=national_id,
            species_name=summary.species_name,
            nickname=summary.nickname,
            level=summary.level,
            ot_name=summary.ot_name,
            trainer_id=summary.trainer_id,
            experience=int.from_bytes(secure[growth + 4 : growth + 8], "little"),
            moves=moves,
            held_item=CanonicalItem(item_id=held_item_id, source_generation=3) if held_item_id is not None else None,
            original_data=CanonicalOriginalData(
                generation=3,
                game=self.game_id,
                format="gen3-party-v1",
                raw_data_base64=base64.b64encode(raw).decode("ascii"),
                checksum=f"{int(details['checksum']):04x}",
                location=location,
                metadata={"layout": self._require_layout().name},
            ),
            metadata={
                "source_species_id_space": "gen3_internal",
                "source_species_id": summary.species_id,
                "is_egg": is_egg,
            },
        )

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        self.remove_or_replace_sent_pokemon(location, payload)

    def import_canonical(self, location: str, canonical_pokemon: CanonicalPokemon) -> None:
        built = self.build_party_mon_from_canonical(canonical_pokemon)
        self.write_party_mon(location, built)

    def build_party_mon_from_canonical(self, canonical_pokemon: CanonicalPokemon) -> bytes:
        self.validate_can_write("party:0", canonical_pokemon)
        personality = self._deterministic_personality(canonical_pokemon)
        trainer_id = int(canonical_pokemon.trainer_id) & 0xFFFFFFFF
        species_id = national_to_native(3, canonical_pokemon.species.national_dex_id)
        secure = bytearray(SECURE_SIZE)
        growth = SUBSTRUCT_ORDERS[personality % 24][0] * 12
        attacks = SUBSTRUCT_ORDERS[personality % 24][1] * 12
        secure[growth : growth + 2] = species_id.to_bytes(2, "little")
        if canonical_pokemon.held_item and canonical_pokemon.held_item.item_id:
            item_id = canonical_pokemon.held_item.item_id
            if canonical_pokemon.held_item.source_generation and canonical_pokemon.held_item.source_generation != 3:
                item_id = equivalent_item_id(item_id, canonical_pokemon.held_item.source_generation, 3) or 0
            if item_exists(item_id, 3):
                secure[growth + 2 : growth + 4] = int(item_id).to_bytes(2, "little")
        secure[growth + 4 : growth + 8] = int(canonical_pokemon.experience or 0).to_bytes(4, "little", signed=False)
        for offset, move in enumerate(canonical_pokemon.moves[:4]):
            if move_exists(move.move_id, 3):
                secure[attacks + offset * 2 : attacks + offset * 2 + 2] = int(move.move_id).to_bytes(2, "little")
                secure[attacks + 8 + offset] = min(99, int(move.pp or move.max_pp or 0))
        checksum = self._box_checksum(bytes(secure))
        encrypted = self._encrypt_secure(bytes(secure), personality, trainer_id)
        raw = bytearray(PARTY_MON_SIZE)
        raw[0:4] = personality.to_bytes(4, "little")
        raw[4:8] = trainer_id.to_bytes(4, "little")
        raw[8:18] = self._encode_text(canonical_pokemon.nickname or canonical_pokemon.species.name, NICKNAME_SIZE)
        raw[18] = 2
        raw[20:27] = self._encode_text(canonical_pokemon.ot_name or "TRAINER", OT_NAME_SIZE)
        raw[28:30] = checksum.to_bytes(2, "little")
        raw[32:80] = encrypted
        raw[84] = max(1, min(100, canonical_pokemon.level))
        return bytes(raw)

    def write_party_mon(self, location: str, built_mon: bytes) -> None:
        if len(built_mon) != PARTY_MON_SIZE:
            raise ValueError("Struct Gen 3 canonico tem tamanho invalido.")
        index = self._party_index(location)
        if index >= self._party_count():
            raise ValueError("Localizacao de party fora da quantidade atual.")
        self._parse_pokemon(built_mon)
        offset = self._party_mon_offset(index)
        self._require_data()[offset : offset + PARTY_MON_SIZE] = built_mon
        self.recalculate_checksums()

    def validate_can_write(self, location: str, canonical_pokemon: CanonicalPokemon) -> None:
        self._party_index(location)
        if canonical_pokemon.metadata.get("is_egg"):
            raise ValueError("Egg nao pode ser importado para Gen 3.")
        national_to_native(3, canonical_pokemon.species.national_dex_id)
        invalid_moves = [move.move_id for move in canonical_pokemon.moves if not move_exists(move.move_id, 3)]
        if invalid_moves:
            raise ValueError(f"Moves incompatíveis com Gen 3: {invalid_moves}")

    def can_import_canonical(self, canonical_pokemon: CanonicalPokemon) -> bool:
        return self.compatibility_report_for(canonical_pokemon).compatible

    def compatibility_report_for(self, canonical_pokemon: CanonicalPokemon) -> CompatibilityReport:
        return build_compatibility_report(canonical_pokemon, self.generation, cross_generation_enabled=False)

    def get_species_id(self, location: str) -> int:
        index = self._party_index(location)
        start = self._party_mon_offset(index)
        raw = bytes(self._require_data()[start : start + PARTY_MON_SIZE])
        secure = self._decrypt_secure(raw[:BOX_MON_SIZE])
        growth = self._substruct_offset(raw[:BOX_MON_SIZE], 0)
        return int.from_bytes(secure[growth : growth + 2], "little")

    def set_species_id(self, location: str, species_id: int) -> None:
        species_id = int(species_id)
        if species_id < 1 or species_id > 412:
            raise ValueError("Species Gen 3 precisa estar no intervalo suportado 1..412.")
        self._edit_growth_field(location, 0, species_id.to_bytes(2, "little"))

    def get_held_item_id(self, location: str) -> int | None:
        index = self._party_index(location)
        start = self._party_mon_offset(index)
        raw = bytes(self._require_data()[start : start + PARTY_MON_SIZE])
        secure = self._decrypt_secure(raw[:BOX_MON_SIZE])
        growth = self._substruct_offset(raw[:BOX_MON_SIZE], 0)
        value = int.from_bytes(secure[growth + 2 : growth + 4], "little")
        return value or None

    def set_held_item_id(self, location: str, item_id: int) -> None:
        item_id = int(item_id)
        if item_id < 0 or item_id > 0xFFFF:
            raise ValueError("Held item Gen 3 precisa caber em 16 bits.")
        self._edit_growth_field(location, 2, item_id.to_bytes(2, "little"))

    def clear_held_item(self, location: str) -> None:
        self.set_held_item_id(location, 0)

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        if received_payload.generation != 3:
            raise ValueError(
                f"Payload recebido e Gen {received_payload.generation}, mas o save local e Gen 3. "
                "Cross-generation esta protegido por feature guard enquanto o conversor local Gen 3 esta em desenvolvimento."
            )
        index = self._party_index(location)
        if index >= self._party_count():
            raise ValueError("Localizacao de party fora da quantidade atual.")
        raw = base64.b64decode(received_payload.raw_data_base64)
        if len(raw) != PARTY_MON_SIZE:
            raise ValueError("Payload Gen 3 invalido: tamanho bruto inesperado.")
        details = self._parse_pokemon(raw)
        if int(details["species_id"]) <= 0 or int(details["species_id"]) > 412:
            raise ValueError("Payload Gen 3 invalido: species_id fora do intervalo suportado.")
        offset = self._party_mon_offset(index)
        self._require_data()[offset : offset + PARTY_MON_SIZE] = raw
        self.recalculate_checksums()

    def validate(self) -> bool:
        return self._detect_slot_and_layout(bytes(self._require_data())) is not None

    def recalculate_checksums(self) -> None:
        data = self._require_data()
        section_offset = self._section1_offset()
        section_data = bytes(data[section_offset : section_offset + SECTOR_DATA_SIZE])
        checksum = self._sector_checksum(section_data, SECTOR_DATA_SIZE)
        data[section_offset + 0xFF6 : section_offset + 0xFF8] = checksum.to_bytes(2, "little")

    def save(self, save_path: str | Path) -> None:
        if not self.validate():
            raise ValueError("Save Gen 3 nao passou na validacao antes da gravacao.")
        Path(save_path).write_bytes(bytes(self._require_data()))

    def _detect_slot_and_layout(self, data: bytes) -> tuple[SaveSlot, Gen3Layout] | None:
        if len(data) < SECTOR_SIZE * SECTORS_PER_SLOT:
            return None
        candidates: list[tuple[int, SaveSlot, Gen3Layout]] = []
        bases = [0]
        if len(data) >= SECTOR_SIZE * SECTORS_PER_SLOT * 2:
            bases.append(SECTOR_SIZE * SECTORS_PER_SLOT)
        for base in bases:
            slot = self._read_slot(data, base)
            if slot is None or SECTOR_ID_SAVEBLOCK1_START not in slot.section_offsets:
                continue
            for layout in LAYOUTS:
                score = self._layout_score(data, slot, layout)
                if score > 0:
                    candidates.append((score, slot, layout))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[1].counter, item[0]), reverse=True)
        return candidates[0][1], candidates[0][2]

    def _game_id_from_name(self, filename: str, layout: Gen3Layout) -> str:
        lower_name = filename.lower()
        if layout.name == "frlg":
            if "leaf" in lower_name or "leafgreen" in lower_name:
                return "pokemon_leafgreen"
            return "pokemon_firered"
        if "ruby" in lower_name:
            return "pokemon_ruby"
        if "sapphire" in lower_name:
            return "pokemon_sapphire"
        return "pokemon_emerald"

    def _read_slot(self, data: bytes, base: int) -> SaveSlot | None:
        section_offsets: dict[int, int] = {}
        counters: list[int] = []
        for physical in range(SECTORS_PER_SLOT):
            offset = base + physical * SECTOR_SIZE
            if offset + SECTOR_SIZE > len(data):
                continue
            section_id = int.from_bytes(data[offset + 0xFF4 : offset + 0xFF6], "little")
            signature = int.from_bytes(data[offset + 0xFF8 : offset + 0xFFC], "little")
            counter = int.from_bytes(data[offset + 0xFFC : offset + 0x1000], "little")
            if signature != SECTOR_SIGNATURE or section_id >= SECTORS_PER_SLOT:
                continue
            if section_id not in section_offsets:
                section_offsets[section_id] = offset
            counters.append(counter)
        if not section_offsets:
            return None
        return SaveSlot(base=base, counter=max(counters or [0]), section_offsets=section_offsets)

    def _layout_score(self, data: bytes, slot: SaveSlot, layout: Gen3Layout) -> int:
        section_offset = slot.section_offsets[SECTOR_ID_SAVEBLOCK1_START]
        if not self._sector_checksum_matches(data, section_offset):
            return 0
        count = data[section_offset + layout.party_count_offset]
        if count < 1 or count > PARTY_CAPACITY:
            return 0
        score = 10
        for index in range(count):
            start = section_offset + layout.party_offset + index * PARTY_MON_SIZE
            raw = data[start : start + PARTY_MON_SIZE]
            if len(raw) != PARTY_MON_SIZE:
                return 0
            try:
                details = self._parse_pokemon(raw)
            except ValueError:
                continue
            if 1 <= int(details["species_id"]) <= 412:
                score += 1
        return score if score > 10 else 0

    def _sector_checksum_matches(self, data: bytes, section_offset: int) -> bool:
        stored = int.from_bytes(data[section_offset + 0xFF6 : section_offset + 0xFF8], "little")
        actual = self._sector_checksum(data[section_offset : section_offset + SECTOR_DATA_SIZE], SECTOR_DATA_SIZE)
        return stored == actual

    def _sector_checksum(self, data: bytes, size: int) -> int:
        checksum = 0
        for offset in range(0, size, 4):
            checksum = (checksum + int.from_bytes(data[offset : offset + 4].ljust(4, b"\x00"), "little")) & 0xFFFFFFFF
        return ((checksum >> 16) + checksum) & 0xFFFF

    def _parse_pokemon(self, raw: bytes) -> dict[str, int | bool]:
        if len(raw) != PARTY_MON_SIZE:
            raise ValueError("Struct Pokemon Gen 3 precisa ter 100 bytes.")
        box = raw[:BOX_MON_SIZE]
        personality = int.from_bytes(box[0:4], "little")
        trainer_id = int.from_bytes(box[4:8], "little")
        checksum = int.from_bytes(box[0x1C:0x1E], "little")
        secure = self._decrypt_secure(box)
        calculated = self._box_checksum(secure)
        if calculated != checksum:
            raise ValueError("Checksum interno do Pokemon Gen 3 invalido.")
        growth_index = SUBSTRUCT_ORDERS[personality % 24][0]
        growth = secure[growth_index * 12 : growth_index * 12 + 12]
        species_id = int.from_bytes(growth[0:2], "little")
        is_egg = species_id == 412 or bool(box[0x13] & 0x04)
        return {
            "species_id": species_id,
            "trainer_id": trainer_id,
            "checksum": checksum,
            "is_egg": is_egg,
        }

    def _substruct_offset(self, box: bytes, logical_index: int) -> int:
        personality = int.from_bytes(box[0:4], "little")
        return SUBSTRUCT_ORDERS[personality % 24][logical_index] * 12

    def _edit_growth_field(self, location: str, relative_offset: int, value: bytes) -> None:
        index = self._party_index(location)
        if index >= self._party_count():
            raise ValueError("Localizacao de party fora da quantidade atual.")
        start = self._party_mon_offset(index)
        raw = bytearray(self._require_data()[start : start + PARTY_MON_SIZE])
        secure = bytearray(self._decrypt_secure(bytes(raw[:BOX_MON_SIZE])))
        growth = self._substruct_offset(bytes(raw[:BOX_MON_SIZE]), 0)
        secure[growth + relative_offset : growth + relative_offset + len(value)] = value
        self._write_secure_party_pokemon(index, raw, secure)

    def _write_secure_party_pokemon(self, index: int, raw: bytearray, secure: bytearray) -> None:
        box = bytearray(raw[:BOX_MON_SIZE])
        personality = int.from_bytes(box[0:4], "little")
        trainer_id = int.from_bytes(box[4:8], "little")
        checksum = self._box_checksum(bytes(secure))
        box[0x1C:0x1E] = checksum.to_bytes(2, "little")
        key = personality ^ trainer_id
        encrypted = bytearray(secure)
        for offset in range(0, SECURE_SIZE, 4):
            current = int.from_bytes(encrypted[offset : offset + 4], "little") ^ key
            encrypted[offset : offset + 4] = current.to_bytes(4, "little")
        box[SECURE_OFFSET : SECURE_OFFSET + SECURE_SIZE] = encrypted
        raw[:BOX_MON_SIZE] = box
        start = self._party_mon_offset(index)
        self._require_data()[start : start + PARTY_MON_SIZE] = raw
        self.recalculate_checksums()

    def _decrypt_secure(self, box: bytes) -> bytes:
        personality = int.from_bytes(box[0:4], "little")
        trainer_id = int.from_bytes(box[4:8], "little")
        key = personality ^ trainer_id
        secure = bytearray(box[SECURE_OFFSET : SECURE_OFFSET + SECURE_SIZE])
        for offset in range(0, SECURE_SIZE, 4):
            value = int.from_bytes(secure[offset : offset + 4], "little") ^ key
            secure[offset : offset + 4] = value.to_bytes(4, "little")
        return bytes(secure)

    def _encrypt_secure(self, secure: bytes, personality: int, trainer_id: int) -> bytes:
        key = personality ^ trainer_id
        encrypted = bytearray(secure)
        for offset in range(0, SECURE_SIZE, 4):
            value = int.from_bytes(encrypted[offset : offset + 4], "little") ^ key
            encrypted[offset : offset + 4] = value.to_bytes(4, "little")
        return bytes(encrypted)

    def _box_checksum(self, secure: bytes) -> int:
        value = 0
        for offset in range(0, SECURE_SIZE, 2):
            value = (value + int.from_bytes(secure[offset : offset + 2], "little")) & 0xFFFF
        return value

    def _party_count(self) -> int:
        data = self._require_data()
        layout = self._require_layout()
        return data[self._section1_offset() + layout.party_count_offset]

    def _party_mon_offset(self, index: int) -> int:
        layout = self._require_layout()
        return self._section1_offset() + layout.party_offset + index * PARTY_MON_SIZE

    def _section1_offset(self) -> int:
        return self._require_slot().section_offsets[SECTOR_ID_SAVEBLOCK1_START]

    def _party_index(self, location: str) -> int:
        if not location.startswith("party:"):
            raise ValueError("Gen 3 suporta apenas party:N nesta versao.")
        index = int(location.split(":", 1)[1])
        if index < 0 or index >= PARTY_CAPACITY:
            raise ValueError("Indice de party invalido.")
        return index

    def _decode_text(self, raw: bytes) -> str:
        chars = []
        for byte in raw:
            if byte == 0xFF:
                break
            chars.append(GEN3_TEXT.get(byte, "?"))
        return "".join(chars).strip()

    def _encode_text(self, value: str, size: int) -> bytes:
        reverse = {value: key for key, value in GEN3_TEXT.items()}
        encoded = bytearray([0xFF] * size)
        for index, char in enumerate(value[:size]):
            encoded[index] = reverse.get(char, 0xFF)
        return bytes(encoded)

    def _deterministic_personality(self, canonical_pokemon: CanonicalPokemon) -> int:
        seed = (
            f"{canonical_pokemon.source_generation}|{canonical_pokemon.source_game}|"
            f"{canonical_pokemon.species.national_dex_id}|{canonical_pokemon.nickname}|"
            f"{canonical_pokemon.trainer_id}|{canonical_pokemon.level}"
        ).encode("utf-8")
        value = 0xA5A5A5A5
        for byte in seed:
            value = ((value * 33) ^ byte) & 0xFFFFFFFF
        return value or 1

    def _require_data(self) -> bytearray:
        if self.data is None:
            raise RuntimeError("Parser Gen 3 ainda nao carregou um save.")
        return self.data

    def _require_slot(self) -> SaveSlot:
        if self.slot is None:
            raise RuntimeError("Parser Gen 3 ainda nao detectou o slot ativo.")
        return self.slot

    def _require_layout(self) -> Gen3Layout:
        if self.layout is None:
            raise RuntimeError("Parser Gen 3 ainda nao detectou o layout do jogo.")
        return self.layout
