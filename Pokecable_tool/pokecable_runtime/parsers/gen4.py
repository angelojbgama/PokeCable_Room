from __future__ import annotations

import base64
import binascii
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

from canonical import CanonicalItem, CanonicalMove, CanonicalOriginalData, CanonicalPokemon, CanonicalSpecies, CanonicalStats
from compatibility import CompatibilityReport, build_compatibility_report
from data.base_stats import get_base_stats
from data.gender_rates import gender_from_gen3_personality, gender_rate_for_species
from data.growth_rates import experience_for_level, growth_rate_id_for_national, level_from_species_experience
from data.items import equivalent_item_id, item_category, item_exists, item_name
from data.moves import default_move_pp, move_exists, move_name
from data.pid_traits import gen3_species_pid_traits, normalize_personality
from data.species import SPECIES_NAMES_BY_NATIONAL, native_to_national, national_to_native, species_exists_in_generation
from data.unown_forms import UNOWN_FORM_NAMES

from .base import InventoryEntry, InventoryStoreResult, PokemonPayload, PokemonSummary, SaveData


PARTITION_SIZE = 0x40000
SAVE_SIZE = 0x80000
PARTY_CAPACITY = 6
BOX_COUNT = 18
BOX_CAPACITY = 30
PK4_STORED_SIZE = 136
PK4_PARTY_SIZE = 236
GEN4_MAGIC_JAPAN_INTL = 0x20060623
GEN4_MAGIC_KOREAN = 0x20070903
NOCASH_MAGIC = b"NocashGbaBackupMediaSavDataFile\x1a"
NOCASH_HEADER_SIZE = 0x50

NATURE_NAMES = (
    "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
    "Bold", "Docile", "Relaxed", "Impish", "Lax",
    "Timid", "Hasty", "Serious", "Jolly", "Naive",
    "Modest", "Mild", "Quiet", "Bashful", "Rash",
    "Calm", "Gentle", "Sassy", "Careful", "Quirky",
)

BLOCK_POSITION_45 = (
    (0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 1, 3), (0, 3, 1, 2),
    (0, 2, 3, 1), (0, 3, 2, 1), (1, 0, 2, 3), (1, 0, 3, 2),
    (2, 0, 1, 3), (3, 0, 1, 2), (2, 0, 3, 1), (3, 0, 2, 1),
    (1, 2, 0, 3), (1, 3, 0, 2), (2, 1, 0, 3), (3, 1, 0, 2),
    (2, 3, 0, 1), (3, 2, 0, 1), (1, 2, 3, 0), (1, 3, 2, 0),
    (2, 1, 3, 0), (3, 1, 2, 0), (2, 3, 1, 0), (3, 2, 1, 0),
)

GEN4_DECODE_MAP = {0xFFFF: ""}
GEN4_ENCODE_MAP = {}
for idx, ch in enumerate("0123456789", start=0x121):
    GEN4_DECODE_MAP[idx] = ch
    GEN4_ENCODE_MAP[ch] = idx
for idx, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=0x12B):
    GEN4_DECODE_MAP[idx] = ch
    GEN4_ENCODE_MAP[ch] = idx
for idx, ch in enumerate("abcdefghijklmnopqrstuvwxyz", start=0x145):
    GEN4_DECODE_MAP[idx] = ch
    GEN4_ENCODE_MAP[ch] = idx
for value, ch in {
    0x1AB: "!",
    0x1AC: "?",
    0x1AD: ",",
    0x1AE: ".",
    0x1B1: "/",
    0x1B3: "'",
    0x1B8: "(",
    0x1B9: ")",
    0x1BA: "♂",
    0x1BB: "♀",
    0x1BD: "+",
    0x1BE: "-",
    0x1C0: "#",
    0x1C1: "=",
    0x1C2: "&",
    0x1C4: ":",
    0x1C5: ";",
    0x1D0: "@",
    0x1D2: "%",
    0x1DE: " ",
}.items():
    GEN4_DECODE_MAP[value] = ch
    GEN4_ENCODE_MAP[ch] = value


@dataclass(frozen=True, slots=True)
class Gen4Layout:
    name: str
    game_id: str
    label: str
    general_size: int
    storage_size: int
    storage_start: int
    footer_size: int
    trainer_name_offset: int
    trainer_name_chars: int
    trainer_id_offset: int
    party_offset: int
    bag_base_offset: int
    badge_offset: int | None = None
    box_mode: str = "sinnoh"


GEN4_LAYOUTS: tuple[Gen4Layout, ...] = (
    Gen4Layout("dp", "pokemon_diamond", "Gen 4 Diamond/Pearl", 0xC100, 0x121E0, 0xC100, 0x14, 0x64, 7, 0x78, 0x98, 0x624),
    Gen4Layout("platinum", "pokemon_platinum", "Gen 4 Platinum", 0xCF2C, 0x121E4, 0xCF2C, 0x14, 0x68, 7, 0x7C, 0xA0, 0x630, badge_offset=0x80),
    Gen4Layout("hgss", "pokemon_heartgold", "Gen 4 HG/SS", 0xF628, 0x12310, 0xF700, 0x10, 0x64, 7, 0x78, 0x98, 0x644, badge_offset=0x83, box_mode="hgss"),
)

GEN4_POCKET_OFFSETS: dict[str, int] = {
    "items": 0x000,
    "key_items": 0x294,
    "tm_hm": 0x35C,
    "mail": 0x4EC,
    "medicine": 0x51C,
    "berries": 0x5BC,
    "balls": 0x6BC,
    "battle_items": 0x6F8,
}

GEN4_HGSS_POCKET_OFFSETS: dict[str, int] = {
    **GEN4_POCKET_OFFSETS,
    "mail": 0x4F0,
    "medicine": 0x520,
    "berries": 0x5C0,
    "balls": 0x6C0,
    "battle_items": 0x720,
}

GEN4_POCKET_CAPACITIES: dict[str, int] = {
    "items": 165,
    "key_items": 50,
    "tm_hm": 100,
    "mail": 12,
    "medicine": 40,
    "berries": 64,
    "balls": 15,
    "battle_items": 13,
}

GEN4_HGSS_POCKET_CAPACITIES: dict[str, int] = {
    **GEN4_POCKET_CAPACITIES,
    "balls": 24,
}

GEN4_VERSION_IDS: dict[str, int] = {
    "pokemon_heartgold": 7,
    "pokemon_soulsilver": 8,
    "pokemon_diamond": 10,
    "pokemon_pearl": 11,
    "pokemon_platinum": 12,
}

NATURE_INCREASE_DECREASE: tuple[tuple[str | None, str | None], ...] = (
    (None, None), ("atk", "def"), ("atk", "spe"), ("atk", "spa"), ("atk", "spd"),
    ("def", "atk"), (None, None), ("def", "spe"), ("def", "spa"), ("def", "spd"),
    ("spe", "atk"), ("spe", "def"), (None, None), ("spe", "spa"), ("spe", "spd"),
    ("spa", "atk"), ("spa", "def"), ("spa", "spe"), (None, None), ("spa", "spd"),
    ("spd", "atk"), ("spd", "def"), ("spd", "spe"), ("spd", "spa"), (None, None),
)


def _u16(data: bytes | bytearray | memoryview, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes | bytearray | memoryview, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _w16(buf: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", buf, offset, int(value) & 0xFFFF)


def _w32(buf: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", buf, offset, int(value) & 0xFFFFFFFF)


def _crc16_ccitt(data: bytes) -> int:
    return binascii.crc_hqx(data, 0xFFFF) & 0xFFFF


def _footer_valid(data: bytes, start: int, size: int, footer_size: int) -> bool:
    block = data[start:start + size]
    if len(block) != size:
        return False
    if _u32(block, size - 0x0C) != size:
        return False
    magic = _u32(block, size - 0x08)
    return magic in {GEN4_MAGIC_JAPAN_INTL, GEN4_MAGIC_KOREAN}


def _compare_counters(counter1: int, counter2: int) -> int:
    if counter1 == 0xFFFFFFFF and counter2 != 0xFFFFFFFE:
        return 1
    if counter2 == 0xFFFFFFFF and counter1 != 0xFFFFFFFE:
        return 0
    if counter1 > counter2:
        return 0
    if counter1 < counter2:
        return 1
    return 2


def _compare_footers(data: bytes, footer1: int, footer2: int) -> int:
    major1 = _u32(data, footer1)
    major2 = _u32(data, footer2)
    result = _compare_counters(major1, major2)
    if result != 2:
        return result
    minor1 = _u32(data, footer1 + 4)
    minor2 = _u32(data, footer2 + 4)
    result = _compare_counters(minor1, minor2)
    return 0 if result == 2 else result


def _crypt_array(data: bytearray, seed: int) -> None:
    for offset in range(0, len(data), 2):
        seed = (0x41C64E6D * seed + 0x6073) & 0xFFFFFFFF
        value = _u16(data, offset) ^ ((seed >> 16) & 0xFFFF)
        _w16(data, offset, value)


def _unshuffle_45(block: bytes, sv: int) -> bytes:
    order = BLOCK_POSITION_45[sv % 24]
    chunks = [block[index * 32:(index + 1) * 32] for index in range(4)]
    restored = bytearray(128)
    for src_index, logical_index in enumerate(order):
        restored[logical_index * 32:(logical_index + 1) * 32] = chunks[src_index]
    return bytes(restored)


def _shuffle_45(block: bytes, sv: int) -> bytes:
    order = BLOCK_POSITION_45[sv % 24]
    chunks = [block[index * 32:(index + 1) * 32] for index in range(4)]
    shuffled = bytearray(128)
    for dst_index, logical_index in enumerate(order):
        shuffled[dst_index * 32:(dst_index + 1) * 32] = chunks[logical_index]
    return bytes(shuffled)


def decrypt_pk4(raw_data: bytes) -> bytes:
    data = bytearray(raw_data)
    pid = _u32(data, 0)
    checksum = _u16(data, 6)
    sv = (pid >> 13) & 31
    block = bytearray(data[8:PK4_STORED_SIZE])
    _crypt_array(block, checksum)
    data[8:PK4_STORED_SIZE] = _unshuffle_45(bytes(block), sv)
    if len(data) > PK4_STORED_SIZE:
        tail = bytearray(data[PK4_STORED_SIZE:])
        _crypt_array(tail, pid)
        data[PK4_STORED_SIZE:] = tail
    return bytes(data)


def _pk4_checksum(decrypted: bytes) -> int:
    total = 0
    for offset in range(8, PK4_STORED_SIZE, 2):
        total = (total + _u16(decrypted, offset)) & 0xFFFF
    return total


def _pk4_checksum_matches(decrypted: bytes) -> bool:
    return _u16(decrypted, 6) == _pk4_checksum(decrypted)


def _pk4_box_record_is_plausible(decrypted: bytes, national_dex_id: int) -> bool:
    if not _pk4_checksum_matches(decrypted):
        return False
    if not species_exists_in_generation(national_dex_id, 4):
        return False
    for slot_index in range(4):
        move_id = _u16(decrypted, 0x28 + (slot_index * 2))
        pp_ups = int(decrypted[0x34 + slot_index])
        if move_id and not move_exists(move_id, 4):
            return False
        if pp_ups > 3:
            return False
    return True


def _is_nocash_save(data: bytes) -> bool:
    return data.startswith(NOCASH_MAGIC) and len(data) >= NOCASH_HEADER_SIZE


def _unpack_nocash_payload(data: bytes) -> tuple[bytes, dict[str, object] | None]:
    if not _is_nocash_save(data):
        return data, None
    method = _u32(data, 0x44)
    first_size = _u32(data, 0x48)
    second_size = _u32(data, 0x4C)
    if method == 0:
        unpacked_size = first_size
        start_address = second_size
        payload = data[NOCASH_HEADER_SIZE:NOCASH_HEADER_SIZE + unpacked_size]
        raw_size = max(SAVE_SIZE, start_address + len(payload))
        raw = bytearray([0xFF]) * raw_size
        raw[start_address:start_address + len(payload)] = payload
        return bytes(raw), {
            "header": bytes(data[:NOCASH_HEADER_SIZE]),
            "method": method,
            "suffix": bytes(data[NOCASH_HEADER_SIZE + unpacked_size:]),
        }
    if method != 1:
        raise ValueError(f"Formato NO$GBA com compressao desconhecida: {method}.")

    packed_size = first_size
    unpacked_size = second_size
    payload = data[NOCASH_HEADER_SIZE:NOCASH_HEADER_SIZE + packed_size]
    output = bytearray()
    offset = 0
    while offset < len(payload) and len(output) < unpacked_size:
        control = payload[offset]
        offset += 1
        if control < 0x80:
            output.extend(payload[offset:offset + control])
            offset += control
        elif control > 0x80:
            if offset >= len(payload):
                break
            value = payload[offset]
            offset += 1
            output.extend([value] * (control - 0x80))
        else:
            if offset + 3 > len(payload):
                break
            value = payload[offset]
            count = _u16(payload, offset + 1)
            offset += 3
            output.extend([value] * count)
    if len(output) != unpacked_size:
        raise ValueError(f"NO$GBA incompleto: esperado {unpacked_size} bytes, obteve {len(output)}.")
    return bytes(output), {
        "header": bytes(data[:NOCASH_HEADER_SIZE]),
        "method": method,
        "suffix": bytes(data[NOCASH_HEADER_SIZE + packed_size:]),
    }


def _flush_nocash_literal(output: bytearray, literal: bytearray) -> None:
    while literal:
        chunk = bytes(literal[:0x7F])
        del literal[:0x7F]
        output.append(len(chunk))
        output.extend(chunk)


def _compress_nocash_payload(raw_data: bytes) -> bytes:
    output = bytearray()
    literal = bytearray()
    offset = 0
    while offset < len(raw_data):
        value = raw_data[offset]
        run = 1
        while offset + run < len(raw_data) and raw_data[offset + run] == value and run < 0xFFFF:
            run += 1
        if run >= 3:
            _flush_nocash_literal(output, literal)
            remaining = run
            while remaining:
                chunk = min(remaining, 0xFFFF)
                if chunk < 0x80:
                    output.extend((0x80 + chunk, value))
                else:
                    output.extend((0x80, value))
                    output.extend(int(chunk).to_bytes(2, "little"))
                remaining -= chunk
            offset += run
            continue
        literal.append(value)
        if len(literal) >= 0x7F:
            _flush_nocash_literal(output, literal)
        offset += 1
    _flush_nocash_literal(output, literal)
    return bytes(output)


def _pack_nocash_payload(raw_data: bytes, metadata: dict[str, object]) -> bytes:
    header = bytearray(metadata.get("header") or b"")
    if len(header) < NOCASH_HEADER_SIZE:
        header = bytearray(NOCASH_MAGIC)
        header.extend(b"\x00" * (NOCASH_HEADER_SIZE - len(header)))
        header[0x40:0x44] = b"SRAM"
    else:
        header = header[:NOCASH_HEADER_SIZE]
    method = int(metadata.get("method") or 1)
    suffix = bytes(metadata.get("suffix") or b"")
    if method == 0:
        _w32(header, 0x44, 0)
        _w32(header, 0x48, len(raw_data))
        _w32(header, 0x4C, 0)
        return bytes(header) + bytes(raw_data) + suffix

    packed = _compress_nocash_payload(raw_data)
    _w32(header, 0x44, 1)
    _w32(header, 0x48, len(packed))
    _w32(header, 0x4C, len(raw_data))
    return bytes(header) + packed + suffix


def encrypt_pk4(decrypted_data: bytes) -> bytes:
    data = bytearray(decrypted_data)
    checksum = _pk4_checksum(data)
    _w16(data, 6, checksum)
    pid = _u32(data, 0)
    sv = (pid >> 13) & 31
    block = bytearray(_shuffle_45(data[8:PK4_STORED_SIZE], sv))
    _crypt_array(block, checksum)
    data[8:PK4_STORED_SIZE] = block
    if len(data) > PK4_STORED_SIZE:
        tail = bytearray(data[PK4_STORED_SIZE:])
        _crypt_array(tail, pid)
        data[PK4_STORED_SIZE:] = tail
    return bytes(data)


def decode_gen4_string(raw_data: bytes) -> str:
    chars: list[str] = []
    for offset in range(0, len(raw_data), 2):
        value = _u16(raw_data, offset)
        if value == 0xFFFF:
            break
        chars.append(GEN4_DECODE_MAP.get(value, ""))
    return "".join(chars).strip()


def encode_gen4_string(value: str, char_count: int) -> bytes:
    text = str(value or "")[:char_count]
    buf = bytearray(char_count * 2)
    for index, ch in enumerate(text):
        _w16(buf, index * 2, GEN4_ENCODE_MAP.get(ch, GEN4_ENCODE_MAP.get(" ", 0x1DE)))
    term = len(text) * 2
    if term < len(buf):
        _w16(buf, term, 0xFFFF)
    return bytes(buf)


def _species_name(national_dex_id: int) -> str:
    return SPECIES_NAMES_BY_NATIONAL.get(int(national_dex_id), f"Species #{national_dex_id}")


def _gender_symbol(encoded_gender: int, national_dex_id: int | None = None) -> str | None:
    rate = gender_rate_for_species(national_dex_id)
    if rate is not None:
        if rate < 0:
            return None
        if rate == 0:
            return "♂"
        if rate >= 8:
            return "♀"
    return {0: "♂", 1: "♀", 2: None}.get(int(encoded_gender))


def _clamp(value: int | None, minimum: int, maximum: int, default: int = 0) -> int:
    try:
        numeric = int(value if value is not None else default)
    except (TypeError, ValueError):
        numeric = default
    return max(minimum, min(maximum, numeric))


def _canonical_personality(canonical_pokemon: CanonicalPokemon) -> int:
    metadata = canonical_pokemon.metadata if isinstance(canonical_pokemon.metadata, dict) else {}
    for field in ("personality", "pid", "forced_pid"):
        candidate = normalize_personality(metadata.get(field))
        if candidate is not None:
            return candidate or 1
    seed = (
        f"{canonical_pokemon.source_generation}|{canonical_pokemon.source_game}|"
        f"{canonical_pokemon.species_national_id}|{canonical_pokemon.nickname}|"
        f"{canonical_pokemon.trainer_id}|{canonical_pokemon.level}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.blake2s(seed, digest_size=4).digest(), "little") or 1


def _has_explicit_personality(canonical_pokemon: CanonicalPokemon) -> bool:
    metadata = canonical_pokemon.metadata if isinstance(canonical_pokemon.metadata, dict) else {}
    return any(normalize_personality(metadata.get(field)) is not None for field in ("personality", "pid", "forced_pid"))


def _adjust_personality_for_unown_form(personality: int, source_form: str | None) -> int:
    if not source_form:
        return int(personality) & 0xFFFFFFFF
    try:
        target_index = UNOWN_FORM_NAMES.index(str(source_form))
    except ValueError:
        return int(personality) & 0xFFFFFFFF
    value = target_index
    pid = int(personality) & 0xFFFFFFFF
    pid = (pid & ~0x03) | (value & 0x03)
    pid = (pid & ~0x0300) | (((value >> 2) & 0x03) << 8)
    pid = (pid & ~0x030000) | (((value >> 4) & 0x03) << 16)
    pid = (pid & ~0x03000000) | (((value >> 6) & 0x03) << 24)
    return pid or 1


def _adjust_personality_for_gender(personality: int, national_dex_id: int, source_gender: str | None) -> int:
    if source_gender not in ("♂", "♀"):
        return int(personality) & 0xFFFFFFFF
    rate = gender_rate_for_species(national_dex_id)
    if rate is None or rate <= 0 or rate >= 8:
        return int(personality) & 0xFFFFFFFF
    threshold = rate * 32
    wants_female = source_gender == "♀"
    low_byte = max(0, threshold - 1) if wants_female else min(255, threshold)
    return ((int(personality) & 0xFFFFFF00) | low_byte) or 1


def _gender_code(national_dex_id: int, personality: int, source_gender: str | None) -> int:
    rate = gender_rate_for_species(national_dex_id)
    if rate is not None and rate < 0:
        return 2
    gender = source_gender if source_gender in ("♂", "♀") else gender_from_gen3_personality(national_dex_id, personality)
    return 1 if gender == "♀" else 0


def _canonical_move_from_pk4(decrypted: bytes, slot_index: int) -> tuple[CanonicalMove | None, dict[str, int] | None]:
    move_id = _u16(decrypted, 0x28 + (slot_index * 2))
    raw_pp = int(decrypted[0x30 + slot_index])
    raw_pp_ups = int(decrypted[0x34 + slot_index])
    if move_id <= 0 or not move_exists(move_id, 4):
        if move_id > 0:
            return None, {"slot": slot_index, "move_id": move_id, "raw_pp": raw_pp, "raw_pp_ups": raw_pp_ups}
        return None, None
    pp_ups = _clamp(raw_pp_ups, 0, 3, 0)
    max_pp = default_move_pp(move_id, 4, pp_ups)
    pp = _clamp(raw_pp, 0, max_pp, max_pp)
    metadata = None
    if pp != raw_pp or pp_ups != raw_pp_ups:
        metadata = {"raw_pp": raw_pp, "raw_pp_ups": raw_pp_ups, "sanitized": True}
    return (
        CanonicalMove(
            move_id=move_id,
            name=move_name(move_id) or f"Move #{move_id}",
            pp=pp,
            pp_ups=pp_ups,
            max_pp=max_pp,
            source_generation=4,
            metadata=metadata,
        ),
        None,
    )


def _nature_index(nature: str | None, personality: int) -> int:
    if nature:
        normalized = str(nature).strip().lower()
        for index, name in enumerate(NATURE_NAMES):
            if name.lower() == normalized:
                return index
    return int(personality) % 25


def _nature_modified_stat(value: int, stat_key: str, nature_index: int) -> int:
    increased, decreased = NATURE_INCREASE_DECREASE[nature_index]
    if stat_key == increased:
        return max(1, (int(value) * 110) // 100)
    if stat_key == decreased:
        return max(1, (int(value) * 90) // 100)
    return int(value)


def _encoded_unown_form(canonical_pokemon: CanonicalPokemon) -> int:
    if int(canonical_pokemon.species_national_id or 0) != 201:
        return _clamp(canonical_pokemon.metadata.get("form"), 0, 31, 0) if isinstance(canonical_pokemon.metadata, dict) else 0
    source_form = canonical_pokemon.metadata.get("unown_form") if isinstance(canonical_pokemon.metadata, dict) else None
    try:
        return UNOWN_FORM_NAMES.index(str(source_form))
    except ValueError:
        return 0


class Gen4Parser:
    generation = 4

    def __init__(self) -> None:
        self.path: Path | None = None
        self.data = bytearray()
        self.layout: Gen4Layout | None = None
        self.general_partition = 0
        self.storage_partition = 0
        self.save_data: SaveData | None = None
        self._nocash_metadata: dict[str, object] | None = None

    def detect(self, save_path: str | Path) -> bool:
        path = Path(save_path)
        if not path.exists():
            return False
        try:
            data, _ = _unpack_nocash_payload(path.read_bytes())
        except Exception:
            return False
        return self._detect_layout(data) is not None

    def _detect_layout(self, data: bytes) -> Gen4Layout | None:
        if len(data) != SAVE_SIZE:
            return None
        for layout in GEN4_LAYOUTS:
            second_general = PARTITION_SIZE + layout.general_size
            if _footer_valid(data, PARTITION_SIZE, layout.general_size, layout.footer_size) and _footer_valid(
                data, PARTITION_SIZE + layout.storage_start, layout.storage_size, layout.footer_size
            ):
                return layout
            if _footer_valid(data, 0, layout.general_size, layout.footer_size) and _footer_valid(
                data, layout.storage_start, layout.storage_size, layout.footer_size
            ):
                return layout
        return None

    def load(self, save_path: str | Path) -> SaveData:
        self.path = Path(save_path)
        raw_data, nocash_metadata = _unpack_nocash_payload(self.path.read_bytes())
        self.data = bytearray(raw_data)
        self._nocash_metadata = nocash_metadata
        layout = self._detect_layout(bytes(self.data))
        if layout is None:
            raise ValueError("Save Gen 4 nao reconhecido.")
        self.layout = layout
        self.general_partition = self._active_partition(0, layout.general_size, layout.footer_size)
        self.storage_partition = self._active_partition(layout.storage_start, layout.storage_size, layout.footer_size)
        self.save_data = SaveData(self.path, self.generation, self.get_game_id(), self.list_party())
        return self.save_data

    def _active_partition(self, begin: int, length: int, footer_size: int) -> int:
        footer1 = begin + length - footer_size
        footer2 = footer1 + PARTITION_SIZE
        return _compare_footers(bytes(self.data), footer1, footer2)

    def _partition_offset(self, partition: int) -> int:
        return PARTITION_SIZE if partition else 0

    def _general_start(self) -> int:
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        return self._partition_offset(self.general_partition)

    def _storage_start(self) -> int:
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        return self._partition_offset(self.storage_partition) + self.layout.storage_start

    def _general_view(self) -> memoryview:
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        start = self._general_start()
        return memoryview(self.data)[start:start + self.layout.general_size]

    def _storage_view(self) -> memoryview:
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        start = self._storage_start()
        return memoryview(self.data)[start:start + self.layout.storage_size]

    def get_generation(self) -> int:
        return self.generation

    def get_game_id(self) -> str:
        if self.layout is None:
            return ""
        if self.layout.name == "hgss" and self.path is not None:
            lower = self.path.name.lower()
            if "soulsilver" in lower:
                return "pokemon_soulsilver"
            if "heartgold" in lower:
                return "pokemon_heartgold"
        if self.layout.name == "dp" and self.path is not None:
            lower = self.path.name.lower()
            if "pearl" in lower:
                return "pokemon_pearl"
            if "diamond" in lower:
                return "pokemon_diamond"
        return self.layout.game_id if self.layout else ""

    def get_player_name(self) -> str:
        if self.layout is None:
            return ""
        general = self._general_view()
        start = self.layout.trainer_name_offset
        end = start + (self.layout.trainer_name_chars * 2)
        return decode_gen4_string(bytes(general[start:end])) or "Player"

    def _trainer_id(self) -> int:
        if self.layout is None:
            return 0
        return _u16(self._general_view(), self.layout.trainer_id_offset)

    def _party_count(self) -> int:
        if self.layout is None:
            return 0
        count = self._general_view()[self.layout.party_offset - 4]
        return max(0, min(PARTY_CAPACITY, int(count)))

    def _party_slot_offset(self, slot: int) -> int:
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        return self.layout.party_offset + (slot * PK4_PARTY_SIZE)

    def _box_slot_offset(self, box_index: int, slot_index: int) -> int:
        storage = self._storage_view()
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        if self.layout.box_mode == "hgss":
            return (box_index * 0x1000) + (slot_index * PK4_STORED_SIZE)
        return 4 + (box_index * 0xFF0) + (slot_index * PK4_STORED_SIZE)

    def _box_name(self, box_index: int) -> str:
        if self.layout is None:
            return f"Box {box_index + 1}"
        storage = self._storage_view()
        if self.layout.box_mode == "hgss":
            start = 0x12008 + (box_index * 40)
        else:
            start = 4 + (BOX_COUNT * 0xFF0) + (box_index * 40)
        return decode_gen4_string(bytes(storage[start:start + 40])) or f"Box {box_index + 1}"

    def _read_party_raw(self, slot: int) -> bytes:
        offset = self._party_slot_offset(slot)
        return bytes(self._general_view()[offset:offset + PK4_PARTY_SIZE])

    def _write_party_raw(self, slot: int, raw_data: bytes) -> None:
        offset = self._party_slot_offset(slot)
        self._general_view()[offset:offset + PK4_PARTY_SIZE] = raw_data[:PK4_PARTY_SIZE]

    def _read_box_raw(self, box_index: int, slot_index: int) -> bytes:
        offset = self._box_slot_offset(box_index, slot_index)
        return bytes(self._storage_view()[offset:offset + PK4_STORED_SIZE])

    def _write_box_raw(self, box_index: int, slot_index: int, raw_data: bytes) -> None:
        offset = self._box_slot_offset(box_index, slot_index)
        self._storage_view()[offset:offset + PK4_STORED_SIZE] = raw_data[:PK4_STORED_SIZE]

    def _summary_from_raw(self, location: str, raw_data: bytes, *, is_party: bool) -> PokemonSummary | None:
        decrypted = decrypt_pk4(raw_data)
        species_id = _u16(decrypted, 0x08)
        if species_id <= 0:
            return None
        try:
            national_dex_id = native_to_national(4, species_id)
        except Exception:
            if not is_party:
                return None
            national_dex_id = species_id
        if not is_party and not _pk4_box_record_is_plausible(decrypted, national_dex_id):
            return None
        species_name = _species_name(national_dex_id)
        nickname = decode_gen4_string(decrypted[0x48:0x48 + 22]) or species_name
        ot_name = decode_gen4_string(decrypted[0x68:0x68 + 16]) or ""
        held_item_id = _u16(decrypted, 0x0A) or None
        held_name = item_name(held_item_id, 4) if held_item_id else None
        if is_party:
            level = int(decrypted[0x8C] or 1)
        else:
            experience = _u32(decrypted, 0x10)
            try:
                level = int(level_from_species_experience(national_dex_id, experience))
            except Exception:
                level = 1
        return PokemonSummary(
            location=location,
            species_id=species_id,
            species_name=species_name,
            level=max(1, min(100, level)),
            nickname=nickname,
            ot_name=ot_name,
            trainer_id=_u16(decrypted, 0x0C),
            national_dex_id=national_dex_id,
            held_item_id=held_item_id,
            held_item_name=held_name,
            gender=_gender_symbol((decrypted[0x40] >> 1) & 0x3, national_dex_id),
        )

    def list_party(self) -> list[PokemonSummary]:
        result: list[PokemonSummary] = []
        for slot in range(self._party_count()):
            summary = self._summary_from_raw(f"party:{slot}", self._read_party_raw(slot), is_party=True)
            if summary is not None:
                result.append(summary)
        return result

    def list_boxes(self) -> list[PokemonSummary]:
        result: list[PokemonSummary] = []
        for box_index in range(BOX_COUNT):
            for slot_index in range(BOX_CAPACITY):
                summary = self._summary_from_raw(
                    f"box:{box_index}:{slot_index}",
                    self._read_box_raw(box_index, slot_index),
                    is_party=False,
                )
                if summary is not None:
                    result.append(summary)
        return result

    def list_inventory(self) -> list[InventoryEntry]:
        result: list[InventoryEntry] = []
        for pocket_name in self._inventory_pocket_names():
            for item_id, quantity in self._read_inventory_pocket(pocket_name):
                if item_id <= 0 or quantity <= 0:
                    continue
                result.append(
                    InventoryEntry(
                        item_id=item_id,
                        item_name=item_name(item_id, 4) or f"Item #{item_id}",
                        quantity=quantity,
                        generation=4,
                        storage="bag",
                        pocket_name=pocket_name,
                        category=item_category(item_id, 4),
                    )
                )
        return result

    def _parse_location(self, location: str) -> tuple[str, int, int | None]:
        if location.startswith("party:"):
            return "party", int(location.split(":", 1)[1]), None
        if location.startswith("box:"):
            _, box_index, slot_index = location.split(":")
            return "box", int(slot_index), int(box_index)
        raise KeyError(f"Localizacao Gen4 invalida: {location}")

    def _get_raw_for_location(self, location: str) -> tuple[bytes, bool]:
        kind, slot, box = self._parse_location(location)
        if kind == "party":
            return self._read_party_raw(slot), True
        return self._read_box_raw(int(box), slot), False

    def export_pokemon(self, location: str) -> PokemonPayload:
        raw_data, is_party = self._get_raw_for_location(location)
        canonical = self.export_canonical(location)
        summary = self._summary_from_raw(location, raw_data, is_party=is_party)
        if summary is None:
            raise ValueError("Pokemon Gen4 ausente no slot.")
        return PokemonPayload(
            generation=4,
            game=self.get_game_id(),
            species_id=summary.species_id,
            species_name=summary.species_name,
            level=summary.level,
            nickname=summary.nickname,
            ot_name=summary.ot_name,
            trainer_id=summary.trainer_id,
            raw_data_base64=base64.b64encode(raw_data).decode("ascii"),
            display_summary=summary.display_summary,
            checksum=f"{_u16(decrypt_pk4(raw_data), 6):04X}",
            metadata={
                "format": "gen4-party-v1" if is_party else "gen4-box-v1",
                "gender": summary.gender,
            },
            source_generation=4,
            source_game=self.get_game_id(),
            target_generation=4,
            trade_mode="same_generation",
            summary={
                "species_id": summary.species_id,
                "species_name": summary.species_name,
                "level": summary.level,
                "nickname": summary.nickname,
                "gender": summary.gender,
                "held_item_id": summary.held_item_id,
                "held_item_name": summary.held_item_name,
                "moves": [move.move_id for move in canonical.moves],
                "move_names": [move.name for move in canonical.moves],
                "display_summary": summary.display_summary,
                "national_dex_id": summary.national_dex_id,
            },
            canonical=canonical.to_dict(),
            raw={
                "format": "gen4-party-v1" if is_party else "gen4-box-v1",
                "data_base64": base64.b64encode(raw_data).decode("ascii"),
            },
            compatibility_report=build_compatibility_report(canonical, 4, cross_generation_enabled=False).to_dict(),
        )

    def export_canonical(self, location: str) -> CanonicalPokemon:
        raw_data, is_party = self._get_raw_for_location(location)
        decrypted = decrypt_pk4(raw_data)
        species_id = _u16(decrypted, 0x08)
        national_dex_id = native_to_national(4, species_id)
        if not is_party and not _pk4_box_record_is_plausible(decrypted, national_dex_id):
            raise ValueError("Pokemon Gen4 ausente ou invalido no slot.")
        species_name = _species_name(national_dex_id)
        nickname = decode_gen4_string(decrypted[0x48:0x48 + 22]) or species_name
        ot_name = decode_gen4_string(decrypted[0x68:0x68 + 16]) or ""
        held_item_id = _u16(decrypted, 0x0A) or None
        if is_party:
            level = int(decrypted[0x8C] or 1)
        else:
            try:
                level = int(level_from_species_experience(national_dex_id, _u32(decrypted, 0x10)))
            except Exception:
                level = 1
        moves = []
        ignored_raw_moves = []
        for index in range(4):
            move, ignored = _canonical_move_from_pk4(decrypted, index)
            if move is not None:
                moves.append(move)
            if ignored is not None:
                ignored_raw_moves.append(ignored)
        personality = _u32(decrypted, 0)
        iv32 = _u32(decrypted, 0x38)
        form_index = int(decrypted[0x40] >> 3)
        metadata = {
            "gender": _gender_symbol((decrypted[0x40] >> 1) & 0x3, national_dex_id),
            "is_egg": bool((iv32 >> 30) & 1),
            "personality": personality,
            "ability_index": int(decrypted[0x15]),
            "form": form_index,
            "raw_gender_code": int((decrypted[0x40] >> 1) & 0x3),
        }
        if ignored_raw_moves:
            metadata["ignored_raw_moves"] = ignored_raw_moves
        metadata.update(gen3_species_pid_traits(national_dex_id, personality))
        if national_dex_id == 201 and 0 <= form_index < len(UNOWN_FORM_NAMES):
            metadata["unown_form"] = UNOWN_FORM_NAMES[form_index]
        return CanonicalPokemon(
            source_generation=4,
            source_game=self.get_game_id(),
            species_national_id=national_dex_id,
            species_name=species_name,
            nickname=nickname,
            level=max(1, min(100, level)),
            ot_name=ot_name,
            trainer_id=_u32(decrypted, 0x0C),
            experience=_u32(decrypted, 0x10),
            moves=moves,
            held_item=CanonicalItem(item_id=held_item_id, name=item_name(held_item_id, 4), source_generation=4) if held_item_id else None,
            ivs=CanonicalStats(
                hp=(iv32 >> 0) & 0x1F,
                attack=(iv32 >> 5) & 0x1F,
                defense=(iv32 >> 10) & 0x1F,
                speed=(iv32 >> 15) & 0x1F,
                special_attack=(iv32 >> 20) & 0x1F,
                special_defense=(iv32 >> 25) & 0x1F,
            ),
            evs=CanonicalStats(
                hp=decrypted[0x18],
                attack=decrypted[0x19],
                defense=decrypted[0x1A],
                speed=decrypted[0x1B],
                special_attack=decrypted[0x1C],
                special_defense=decrypted[0x1D],
            ),
            nature=NATURE_NAMES[personality % 25],
            ability=f"Index {int(decrypted[0x15])}",
            original_data=CanonicalOriginalData(
                generation=4,
                game=self.get_game_id(),
                format="gen4-party-v1" if is_party else "gen4-box-v1",
                raw_data_base64=base64.b64encode(raw_data).decode("ascii"),
                checksum=f"{_u16(decrypted, 6):04X}",
                location=location,
            ),
            metadata=metadata,
            species=CanonicalSpecies(
                national_dex_id=national_dex_id,
                source_species_id=species_id,
                source_species_id_space="gen4_native",
                name=species_name,
            ),
        )

    def import_pokemon(self, location: str, payload: PokemonPayload) -> None:
        raw_data = base64.b64decode(payload.raw_data_base64.encode("ascii"))
        kind, slot, box = self._parse_location(location)
        if kind == "party":
            if len(raw_data) == PK4_STORED_SIZE:
                promoted = bytearray(PK4_PARTY_SIZE)
                promoted[:PK4_STORED_SIZE] = raw_data
                promoted[0x8C] = max(1, min(100, int(payload.level or 1)))
                raw_data = encrypt_pk4(decrypt_pk4(bytes(promoted)))
            elif len(raw_data) != PK4_PARTY_SIZE:
                raise ValueError("Payload Gen4 party com tamanho invalido.")
            self._write_party_raw(slot, raw_data)
        else:
            if len(raw_data) == PK4_PARTY_SIZE:
                raw_data = raw_data[:PK4_STORED_SIZE]
            if len(raw_data) != PK4_STORED_SIZE:
                raise ValueError("Payload Gen4 box com tamanho invalido.")
            self._write_box_raw(int(box), slot, raw_data)

    def import_canonical(self, location: str, canonical_pokemon: CanonicalPokemon) -> None:
        original = canonical_pokemon.original_data
        if original and original.generation == 4 and original.raw_data_base64:
            summary = PokemonPayload(
                generation=4,
                game=self.get_game_id(),
                species_id=canonical_pokemon.species.source_species_id if canonical_pokemon.species else national_to_native(4, canonical_pokemon.species_national_id),
                species_name=canonical_pokemon.species_name,
                level=canonical_pokemon.level,
                nickname=canonical_pokemon.nickname,
                ot_name=canonical_pokemon.ot_name,
                trainer_id=canonical_pokemon.trainer_id,
                raw_data_base64=original.raw_data_base64,
                display_summary=f"{canonical_pokemon.nickname} Lv.{canonical_pokemon.level}",
            )
            self.import_pokemon(location, summary)
            return
        kind, slot, box = self._parse_location(location)
        raw_data = self._build_pk4_from_canonical(canonical_pokemon, is_party=kind == "party")
        if kind == "party":
            self._write_party_raw(slot, raw_data)
        else:
            self._write_box_raw(int(box), slot, raw_data[:PK4_STORED_SIZE])

    def can_import_canonical(self, canonical_pokemon: CanonicalPokemon) -> bool:
        return self.compatibility_report_for(canonical_pokemon).compatible

    def compatibility_report_for(self, canonical_pokemon: CanonicalPokemon) -> CompatibilityReport:
        return build_compatibility_report(canonical_pokemon, 4, cross_generation_enabled=True)

    def _build_pk4_from_canonical(self, canonical_pokemon: CanonicalPokemon, *, is_party: bool) -> bytes:
        if canonical_pokemon.metadata.get("is_egg"):
            raise ValueError("Egg nao pode ser importado para Gen 4.")
        national_id = int(canonical_pokemon.species_national_id or (canonical_pokemon.species.national_dex_id if canonical_pokemon.species else 0))
        if not species_exists_in_generation(national_id, 4):
            raise ValueError(f"National Dex #{national_id} nao existe na Gen 4.")
        invalid_moves = [move.move_id for move in canonical_pokemon.moves if move.move_id and not move_exists(move.move_id, 4)]
        if invalid_moves:
            raise ValueError(f"Moves incompativeis com Gen 4: {invalid_moves}")

        personality = _canonical_personality(canonical_pokemon)
        explicit_personality = _has_explicit_personality(canonical_pokemon)
        source_gender = canonical_pokemon.metadata.get("gender") if isinstance(canonical_pokemon.metadata, dict) else None
        if not explicit_personality:
            personality = _adjust_personality_for_gender(personality, national_id, source_gender)
        if national_id == 201 and not explicit_personality:
            personality = _adjust_personality_for_unown_form(personality, canonical_pokemon.metadata.get("unown_form"))
        nature_index = _nature_index(canonical_pokemon.nature, personality)
        species_id = national_to_native(4, national_id)
        level = _clamp(canonical_pokemon.level, 1, 100, 1)
        trainer_id = int(canonical_pokemon.trainer_id or self._trainer_id()) & 0xFFFFFFFF
        experience = canonical_pokemon.experience
        if experience is None:
            growth_rate_id = growth_rate_id_for_national(national_id)
            experience = experience_for_level(growth_rate_id, level) if growth_rate_id else 0

        decrypted = bytearray(PK4_PARTY_SIZE if is_party else PK4_STORED_SIZE)
        _w32(decrypted, 0x00, personality)
        _w16(decrypted, 0x04, 0)
        _w16(decrypted, 0x08, species_id)
        held_item_id = self._canonical_held_item_id(canonical_pokemon)
        _w16(decrypted, 0x0A, held_item_id)
        _w32(decrypted, 0x0C, trainer_id)
        _w32(decrypted, 0x10, int(experience or 0))
        decrypted[0x14] = 70
        decrypted[0x15] = self._canonical_ability_id(canonical_pokemon, personality)
        decrypted[0x17] = 2

        evs = self._canonical_evs(canonical_pokemon)
        for offset, key in enumerate(("hp", "attack", "defense", "speed", "special_attack", "special_defense")):
            decrypted[0x18 + offset] = evs[key]

        moves = self._canonical_moves(canonical_pokemon)
        for index, move in enumerate(moves[:4]):
            move_id = int(move.move_id)
            pp_ups = _clamp(move.pp_ups, 0, 3, 0)
            max_pp = int(move.max_pp or default_move_pp(move_id, 4, pp_ups))
            pp = _clamp(move.pp, 0, max_pp, max_pp or default_move_pp(move_id, 4, pp_ups))
            if pp <= 0:
                pp = default_move_pp(move_id, 4, pp_ups)
            _w16(decrypted, 0x28 + (index * 2), move_id)
            decrypted[0x30 + index] = pp
            decrypted[0x34 + index] = pp_ups

        ivs = self._canonical_ivs(canonical_pokemon)
        iv32 = (
            (ivs["hp"] & 0x1F)
            | ((ivs["attack"] & 0x1F) << 5)
            | ((ivs["defense"] & 0x1F) << 10)
            | ((ivs["speed"] & 0x1F) << 15)
            | ((ivs["special_attack"] & 0x1F) << 20)
            | ((ivs["special_defense"] & 0x1F) << 25)
        )
        if canonical_pokemon.nickname and canonical_pokemon.nickname.strip().lower() != _species_name(national_id).lower():
            iv32 |= 1 << 31
        _w32(decrypted, 0x38, iv32)

        gender_code = _gender_code(national_id, personality, source_gender)
        form = _encoded_unown_form(canonical_pokemon)
        fateful = 1 if canonical_pokemon.metadata.get("fateful_encounter") else 0
        decrypted[0x40] = ((form & 0x1F) << 3) | ((gender_code & 0x03) << 1) | fateful
        nickname = canonical_pokemon.nickname or canonical_pokemon.species_name or _species_name(national_id)
        decrypted[0x48:0x48 + 22] = encode_gen4_string(nickname, 11)
        ot_name = canonical_pokemon.ot_name or self.get_player_name() or "TRAINER"
        decrypted[0x68:0x68 + 16] = encode_gen4_string(ot_name, 8)
        decrypted[0x5F] = GEN4_VERSION_IDS.get(self.get_game_id(), 12)
        decrypted[0x83] = 4
        decrypted[0x84] = level & 0x7F

        if is_party:
            decrypted[0x8C] = level
            stats = self._calculate_stats(national_id, level, ivs, evs, nature_index)
            _w16(decrypted, 0x8E, stats["hp"])
            _w16(decrypted, 0x90, stats["hp"])
            _w16(decrypted, 0x92, stats["attack"])
            _w16(decrypted, 0x94, stats["defense"])
            _w16(decrypted, 0x96, stats["speed"])
            _w16(decrypted, 0x98, stats["special_attack"])
            _w16(decrypted, 0x9A, stats["special_defense"])

        return encrypt_pk4(bytes(decrypted))

    def _canonical_held_item_id(self, canonical_pokemon: CanonicalPokemon) -> int:
        if not canonical_pokemon.held_item or not canonical_pokemon.held_item.item_id:
            return 0
        source_id = int(canonical_pokemon.held_item.item_id)
        source_generation = int(canonical_pokemon.held_item.source_generation or canonical_pokemon.source_generation or 4)
        if source_generation != 4:
            mapped = equivalent_item_id(source_id, source_generation, 4)
            if mapped and item_exists(mapped, 4):
                return int(mapped)
        return source_id if item_exists(source_id, 4) else 0

    def _canonical_ability_id(self, canonical_pokemon: CanonicalPokemon, personality: int) -> int:
        if isinstance(canonical_pokemon.metadata, dict):
            value = canonical_pokemon.metadata.get("ability_index")
            if value is not None:
                return _clamp(value, 0, 255, int(personality) & 1)
        if canonical_pokemon.ability:
            match = str(canonical_pokemon.ability).strip().split()
            if match and match[-1].isdigit():
                return _clamp(match[-1], 0, 255, int(personality) & 1)
        return int(personality) & 1

    def _canonical_moves(self, canonical_pokemon: CanonicalPokemon) -> list[CanonicalMove]:
        moves = [move for move in canonical_pokemon.moves if move.move_id and move_exists(move.move_id, 4)]
        if moves:
            return moves[:4]
        pp = default_move_pp(1, 4)
        return [CanonicalMove(move_id=1, name=move_name(1) or "Pound", pp=pp, max_pp=pp, pp_ups=0, source_generation=4)]

    def _canonical_ivs(self, canonical_pokemon: CanonicalPokemon) -> dict[str, int]:
        source_generation = int(canonical_pokemon.source_generation or 4)
        ivs = canonical_pokemon.ivs or CanonicalStats()

        def convert(value: int | None, default: int = 15) -> int:
            numeric = _clamp(value, 0, 31 if source_generation >= 3 else 15, default)
            return min(31, numeric * 2) if source_generation in {1, 2} else numeric

        special = ivs.special
        return {
            "hp": convert(ivs.hp),
            "attack": convert(ivs.attack),
            "defense": convert(ivs.defense),
            "speed": convert(ivs.speed),
            "special_attack": convert(ivs.special_attack if ivs.special_attack is not None else special),
            "special_defense": convert(ivs.special_defense if ivs.special_defense is not None else special),
        }

    def _canonical_evs(self, canonical_pokemon: CanonicalPokemon) -> dict[str, int]:
        source_generation = int(canonical_pokemon.source_generation or 4)
        evs = canonical_pokemon.evs or CanonicalStats()

        def convert(value: int | None) -> int:
            numeric = _clamp(value, 0, 65535 if source_generation in {1, 2} else 252, 0)
            return min(252, numeric // 256) if source_generation in {1, 2} else min(252, numeric)

        special = evs.special
        return {
            "hp": convert(evs.hp),
            "attack": convert(evs.attack),
            "defense": convert(evs.defense),
            "speed": convert(evs.speed),
            "special_attack": convert(evs.special_attack if evs.special_attack is not None else special),
            "special_defense": convert(evs.special_defense if evs.special_defense is not None else special),
        }

    def _calculate_stats(
        self,
        national_id: int,
        level: int,
        ivs: dict[str, int],
        evs: dict[str, int],
        nature_index: int,
    ) -> dict[str, int]:
        base = get_base_stats(national_id) or {}
        stats = dict(base.get("stats") or {})
        if not stats:
            return {"hp": 1, "attack": 1, "defense": 1, "speed": 1, "special_attack": 1, "special_defense": 1}
        level = _clamp(level, 1, 100, 1)
        hp = ((2 * int(stats.get("hp", 1)) + ivs["hp"] + (evs["hp"] // 4)) * level) // 100 + level + 10
        if int(national_id) == 292:
            hp = 1

        def non_hp(stat_key: str, base_key: str) -> int:
            raw = ((2 * int(stats.get(base_key, 1)) + ivs[stat_key] + (evs[stat_key] // 4)) * level) // 100 + 5
            return _nature_modified_stat(raw, base_key, nature_index)

        return {
            "hp": _clamp(hp, 1, 999, 1),
            "attack": _clamp(non_hp("attack", "atk"), 1, 999, 1),
            "defense": _clamp(non_hp("defense", "def"), 1, 999, 1),
            "speed": _clamp(non_hp("speed", "spe"), 1, 999, 1),
            "special_attack": _clamp(non_hp("special_attack", "spa"), 1, 999, 1),
            "special_defense": _clamp(non_hp("special_defense", "spd"), 1, 999, 1),
        }

    def get_species_id(self, location: str) -> int:
        raw_data, _ = self._get_raw_for_location(location)
        return _u16(decrypt_pk4(raw_data), 0x08)

    def set_species_id(self, location: str, species_id: int) -> None:
        raw_data, is_party = self._get_raw_for_location(location)
        decrypted = bytearray(decrypt_pk4(raw_data))
        _w16(decrypted, 0x08, species_id)
        kind, slot, box = self._parse_location(location)
        encrypted = encrypt_pk4(bytes(decrypted))
        if kind == "party":
            self._write_party_raw(slot, encrypted)
        else:
            self._write_box_raw(int(box), slot, encrypted[:PK4_STORED_SIZE])

    def get_held_item_id(self, location: str) -> int | None:
        raw_data, _ = self._get_raw_for_location(location)
        value = _u16(decrypt_pk4(raw_data), 0x0A)
        return value or None

    def set_held_item_id(self, location: str, item_id: int | None) -> None:
        raw_data, _ = self._get_raw_for_location(location)
        decrypted = bytearray(decrypt_pk4(raw_data))
        _w16(decrypted, 0x0A, int(item_id or 0))
        kind, slot, box = self._parse_location(location)
        encrypted = encrypt_pk4(bytes(decrypted))
        if kind == "party":
            self._write_party_raw(slot, encrypted)
        else:
            self._write_box_raw(int(box), slot, encrypted[:PK4_STORED_SIZE])

    def clear_held_item(self, location: str) -> None:
        self.set_held_item_id(location, 0)

    def has_bag_space(self, item_id: int, quantity: int = 1) -> bool:
        try:
            return self._has_space_in_pocket(self._bag_pocket_for_item(item_id), item_id, quantity)
        except Exception:
            return False

    def has_pc_space(self, item_id: int, quantity: int = 1) -> bool:
        return False

    def store_item_in_bag(self, item_id: int, quantity: int = 1) -> InventoryStoreResult:
        pocket_name = self._bag_pocket_for_item(item_id)
        self._store_item_in_pocket(pocket_name, item_id, quantity)
        return InventoryStoreResult(
            item_id=int(item_id),
            item_name=item_name(item_id, 4) or f"Item #{item_id}",
            quantity_added=max(1, int(quantity or 1)),
            generation=4,
            storage="bag",
            pocket_name=pocket_name,
        )

    def store_item_in_pc(self, item_id: int, quantity: int = 1) -> InventoryStoreResult:
        raise NotImplementedError("Gen 4 nao possui PC de itens no formato principal do save.")

    def _inventory_pocket_names(self) -> tuple[str, ...]:
        return ("items", "key_items", "tm_hm", "mail", "medicine", "berries", "balls", "battle_items")

    def _inventory_offsets(self) -> dict[str, int]:
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        return GEN4_HGSS_POCKET_OFFSETS if self.layout.box_mode == "hgss" else GEN4_POCKET_OFFSETS

    def _inventory_capacities(self) -> dict[str, int]:
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        return GEN4_HGSS_POCKET_CAPACITIES if self.layout.box_mode == "hgss" else GEN4_POCKET_CAPACITIES

    def _pocket_absolute_offset(self, pocket_name: str, slot_index: int = 0) -> int:
        if self.layout is None:
            raise ValueError("Parser Gen4 nao carregado.")
        offsets = self._inventory_offsets()
        if pocket_name not in offsets:
            raise KeyError(f"Pocket Gen4 desconhecido: {pocket_name}")
        return self.layout.bag_base_offset + offsets[pocket_name] + (int(slot_index) * 4)

    def _read_inventory_pocket(self, pocket_name: str) -> list[tuple[int, int]]:
        general = self._general_view()
        capacity = self._inventory_capacities()[pocket_name]
        result: list[tuple[int, int]] = []
        for index in range(capacity):
            offset = self._pocket_absolute_offset(pocket_name, index)
            result.append((_u16(general, offset), _u16(general, offset + 2)))
        return result

    def _write_inventory_slot(self, pocket_name: str, slot_index: int, item_id: int, quantity: int) -> None:
        offset = self._general_start() + self._pocket_absolute_offset(pocket_name, slot_index)
        _w16(self.data, offset, int(item_id))
        _w16(self.data, offset + 2, int(quantity))

    def _bag_pocket_for_item(self, item_id: int) -> str:
        item_id = int(item_id)
        if 328 <= item_id <= 427:
            return "tm_hm"
        if 137 <= item_id <= 148:
            return "mail"
        if 17 <= item_id <= 54:
            return "medicine"
        if 149 <= item_id <= 212:
            return "berries"
        if item_id in set(range(1, 5)) | set(range(6, 17)) | set(range(492, 501)):
            return "balls"
        if 55 <= item_id <= 67:
            return "battle_items"
        if 428 <= item_id <= 536:
            return "key_items"
        return "items"

    def _max_item_quantity(self, pocket_name: str, item_id: int) -> int:
        item_id = int(item_id)
        if pocket_name == "key_items":
            return 1
        if pocket_name == "tm_hm" and 420 <= item_id <= 427:
            return 1
        if pocket_name == "tm_hm":
            return 99
        return 999

    def _has_space_in_pocket(self, pocket_name: str, item_id: int, quantity: int = 1) -> bool:
        if not item_exists(item_id, 4):
            return False
        quantity = max(1, int(quantity or 1))
        max_quantity = self._max_item_quantity(pocket_name, item_id)
        entries = self._read_inventory_pocket(pocket_name)
        for current_id, current_quantity in entries:
            if current_id == int(item_id):
                return current_quantity + quantity <= max_quantity
        return any(current_id == 0 for current_id, _ in entries)

    def _store_item_in_pocket(self, pocket_name: str, item_id: int, quantity: int = 1) -> None:
        if not item_exists(item_id, 4):
            raise ValueError(f"Item Gen4 invalido: {item_id}.")
        quantity = max(1, int(quantity or 1))
        max_quantity = self._max_item_quantity(pocket_name, item_id)
        entries = self._read_inventory_pocket(pocket_name)
        first_empty: int | None = None
        for index, (current_id, current_quantity) in enumerate(entries):
            if current_id == int(item_id):
                new_quantity = current_quantity + quantity
                if new_quantity > max_quantity:
                    raise ValueError(f"Quantidade maxima excedida para {item_name(item_id, 4) or item_id}.")
                self._write_inventory_slot(pocket_name, index, item_id, new_quantity)
                return
            if current_id == 0 and first_empty is None:
                first_empty = index
        if first_empty is None:
            raise ValueError(f"Pocket {pocket_name} esta cheio.")
        self._write_inventory_slot(pocket_name, first_empty, item_id, min(quantity, max_quantity))

    def mark_pokedex_seen(self, national_dex_id: int) -> None:
        return None

    def mark_pokedex_caught(self, national_dex_id: int) -> None:
        return None

    def is_pokedex_seen(self, national_dex_id: int) -> bool:
        return False

    def is_pokedex_caught(self, national_dex_id: int) -> bool:
        return False

    def remove_or_replace_sent_pokemon(self, location: str, received_payload: PokemonPayload) -> None:
        self.import_pokemon(location, received_payload)

    def validate(self) -> bool:
        if self.layout is None:
            return False
        general = bytes(self._general_view())
        storage = bytes(self._storage_view())
        return (
            _crc16_ccitt(general[:-self.layout.footer_size]) == _u16(general, len(general) - 2)
            and _crc16_ccitt(storage[:-self.layout.footer_size]) == _u16(storage, len(storage) - 2)
        )

    def recalculate_checksums(self) -> None:
        if self.layout is None:
            return
        general = self._general_view()
        storage = self._storage_view()
        _w16(self.data, self._general_start() + self.layout.general_size - 2, _crc16_ccitt(bytes(general[:-self.layout.footer_size])))
        _w16(self.data, self._storage_start() + self.layout.storage_size - 2, _crc16_ccitt(bytes(storage[:-self.layout.footer_size])))

    def save(self, save_path: str | Path) -> None:
        self.recalculate_checksums()
        data = bytes(self.data)
        if self._nocash_metadata is not None:
            data = _pack_nocash_payload(data, self._nocash_metadata)
        Path(save_path).write_bytes(data)
