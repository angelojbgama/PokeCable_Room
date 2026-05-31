from __future__ import annotations

import random
import tempfile
from pathlib import Path
from typing import Any

from ..canonical import CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats
from ..data.moves import default_move_pp, move_exists, move_name
from ..data.species import SPECIES_NAMES_BY_NATIONAL, national_to_native, species_exists_in_generation


EGG_NICKNAME = "Ovo Misterioso"
EGG_DISPLAY_NAME = "Ovo Misterioso"
EGG_HATCH_CYCLES = 10
SHINY_CHANCE = 0.30

LEGENDARY_OR_MYTHICAL = {
    144, 145, 146, 150, 151,
    243, 244, 245, 249, 250, 251,
    377, 378, 379, 380, 381, 382, 383, 384, 385, 386,
    480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493,
}

NON_BASE_COMMON = {
    2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18, 20, 22, 24, 26, 28, 30, 31,
    33, 34, 36, 38, 40, 42, 44, 45, 47, 49, 51, 53, 55, 57, 59, 61, 62, 64,
    65, 67, 68, 70, 71, 73, 75, 76, 78, 80, 82, 85, 87, 89, 91, 93, 94, 97,
    99, 101, 103, 105, 110, 112, 117, 119, 121, 130, 134, 135, 136, 139,
    141, 148, 149,
    153, 154, 156, 157, 159, 160, 162, 164, 166, 168, 169, 171, 176, 178,
    180, 181, 182, 184, 186, 188, 189, 192, 195, 196, 197, 199, 205, 208,
    210, 212, 217, 219, 221, 224, 226, 229, 230, 232, 233, 247, 248,
    253, 254, 256, 257, 259, 260, 262, 264, 266, 267, 268, 269, 271, 272,
    274, 275, 277, 279, 281, 282, 284, 286, 288, 289, 291, 292, 294, 295,
    297, 301, 305, 306, 308, 310, 317, 319, 321, 323, 326, 329, 330, 332,
    334, 340, 342, 344, 346, 348, 350, 354, 356, 362, 364, 365, 367, 368,
    372, 373, 375, 376,
    388, 389, 391, 392, 394, 395, 397, 398, 400, 402, 404, 405, 407, 409,
    411, 413, 414, 416, 419, 421, 423, 424, 426, 428, 429, 430, 432, 435,
    437, 444, 445, 448, 450, 452, 454, 457, 460, 461, 462, 463, 464, 465,
    466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478,
}

GEN2_BABY_REPLACED = {25, 35, 39, 106, 107, 124, 125, 126, 143, 175, 237}
GEN3_BABY_REPLACED = GEN2_BABY_REPLACED | {183, 202}
GEN4_BABY_REPLACED = GEN3_BABY_REPLACED | {113, 122, 143, 185, 226, 315}

RARE_BASE_SPECIES = {
    1, 4, 7, 25, 35, 37, 54, 58, 63, 66, 79, 83, 90, 95, 102, 108, 111,
    113, 115, 123, 127, 128, 131, 132, 133, 137, 138, 140, 142, 147,
    152, 155, 158, 172, 173, 174, 175, 179, 190, 193, 200, 203, 207, 214,
    215, 216, 222, 227, 228, 234, 236, 238, 239, 240, 246,
    252, 255, 258, 280, 285, 287, 290, 302, 303, 304, 307, 309, 315, 320,
    324, 325, 333, 335, 336, 337, 338, 339, 345, 347, 349, 351, 352, 353,
    355, 357, 359, 360, 361, 366, 369, 370, 371, 374,
    387, 390, 393, 408, 410, 415, 417, 425, 427, 431, 433, 436, 438, 439,
    440, 441, 442, 443, 446, 447, 449, 451, 453, 455, 456, 458, 459, 479,
}


def apply_mystery_shiny_egg(save_model) -> dict[str, Any]:
    generation = int(getattr(save_model, "generation", 0) or 0)
    if generation not in {2, 3, 4}:
        return {"success": False, "message": "extras_not_supported"}

    from .applicator import _get_parser_for_save

    parser = _get_parser_for_save(save_model)
    if not parser:
        return {"success": False, "message": "Nao foi possivel carregar parser"}

    species_id = _choose_species(generation)
    shiny = random.random() < SHINY_CHANCE
    trainer_id = _trainer_full_id(save_model, parser, generation)
    canonical = _build_canonical(generation, getattr(save_model, "game", ""), species_id, shiny, trainer_id, parser)

    if generation == 2:
        result = _insert_gen2(save_model, parser, canonical, shiny)
    elif generation == 3:
        result = _insert_gen3(save_model, parser, canonical)
    else:
        result = _insert_gen4(save_model, parser, canonical)

    if not result.get("success"):
        return result

    try:
        save_model.refresh()
    except Exception:
        pass
    return {
        "success": True,
        "message": "extras_mystery_egg_party" if result.get("destination") == "party" else "extras_mystery_egg_pc",
        "species_id": species_id,
        "species_name": SPECIES_NAMES_BY_NATIONAL.get(species_id, f"Pokemon #{species_id}"),
        "egg_name": EGG_DISPLAY_NAME,
        "is_shiny": shiny,
        **result,
    }


def _choose_species(generation: int) -> int:
    max_id = {2: 251, 3: 386, 4: 493}[generation]
    replaced = {
        2: GEN2_BABY_REPLACED,
        3: GEN3_BABY_REPLACED,
        4: GEN4_BABY_REPLACED,
    }[generation]
    blocked = LEGENDARY_OR_MYTHICAL | NON_BASE_COMMON | replaced
    candidates = [
        species_id
        for species_id in range(1, max_id + 1)
        if species_id not in blocked and species_exists_in_generation(species_id, generation)
    ]
    weights = [1 if species_id in RARE_BASE_SPECIES else 6 for species_id in candidates]
    return int(random.choices(candidates, weights=weights, k=1)[0])


def _build_canonical(generation: int, game: str, species_id: int, shiny: bool, trainer_id: int, parser) -> CanonicalPokemon:
    native_id = national_to_native(generation, species_id)
    move_id = _default_move(generation)
    pp = default_move_pp(move_id, generation)
    metadata: dict[str, Any] = {
        "source_species_id": native_id,
        "source_species_id_space": f"gen{generation}_native",
        "is_shiny": shiny,
    }
    if generation in {3, 4}:
        metadata["forced_pid"] = _random_pid(trainer_id, shiny)
    return CanonicalPokemon(
        source_generation=generation,
        source_game=game or getattr(parser, "game_id", "") or f"gen{generation}",
        species_national_id=species_id,
        species_name=SPECIES_NAMES_BY_NATIONAL.get(species_id, f"Pokemon #{species_id}"),
        nickname=EGG_NICKNAME,
        level=1,
        ot_name=_player_name(parser) or "TRAINER",
        trainer_id=trainer_id,
        experience=0,
        moves=[CanonicalMove(move_id=move_id, name=move_name(move_id), pp=pp, max_pp=pp, source_generation=generation)],
        ivs=CanonicalStats(hp=20, attack=20, defense=20, speed=20, special=10, special_attack=20, special_defense=20),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata=metadata,
        species=CanonicalSpecies(
            national_dex_id=species_id,
            source_species_id=native_id,
            source_species_id_space=f"gen{generation}_native",
            name=SPECIES_NAMES_BY_NATIONAL.get(species_id, f"Pokemon #{species_id}"),
        ),
    )


def _default_move(generation: int) -> int:
    for move_id in (33, 1):
        if move_exists(move_id, generation):
            return move_id
    return 0


def _player_name(parser) -> str:
    getter = getattr(parser, "get_player_name", None)
    if callable(getter):
        try:
            return str(getter() or "")
        except Exception:
            return ""
    return ""


def _trainer_full_id(save_model, parser, generation: int) -> int:
    if generation == 3 and getattr(save_model, "slot", None):
        section0 = (save_model.slot.get("section_offsets") or {}).get(0)
        if section0 is not None:
            return int.from_bytes(save_model.bytes[section0 + 0x0A:section0 + 0x0E], "little") & 0xFFFFFFFF
    if generation == 4 and getattr(parser, "layout", None) is not None:
        try:
            from ..parsers.gen4 import _u32

            return int(_u32(parser._general_view(), parser.layout.trainer_id_offset)) & 0xFFFFFFFF
        except Exception:
            pass
    try:
        return int(save_model.trainer_id()) & 0xFFFFFFFF
    except Exception:
        return 0


def _random_pid(trainer_id: int, shiny: bool) -> int:
    pid_low = random.getrandbits(16)
    pid_high = random.getrandbits(16)
    trainer_low = trainer_id & 0xFFFF
    trainer_high = (trainer_id >> 16) & 0xFFFF
    if shiny:
        pid_high = trainer_low ^ trainer_high ^ pid_low ^ random.randint(0, 7)
    else:
        shiny_value = trainer_low ^ trainer_high ^ pid_low ^ pid_high
        if shiny_value < 8:
            pid_high ^= 0x1000
    return ((pid_high & 0xFFFF) << 16) | (pid_low & 0xFFFF)


def _insert_gen2(save_model, parser, canonical: CanonicalPokemon, shiny: bool) -> dict[str, Any]:
    built = bytearray(parser.build_party_mon_from_canonical(canonical))
    mon = bytearray(built[:48])
    ot = bytes(built[48:59])
    nick = bytes(built[59:70])
    mon[0x1F] = EGG_HATCH_CYCLES

    data = save_model.bytes
    layout = save_model.layout
    party_count = int(data[layout["party_offset"]])
    if party_count < layout["party_capacity"]:
        index = party_count
        data[layout["party_offset"]] = party_count + 1
        data[layout["party_offset"] + 1 + index] = 0xFD
        data[layout["party_offset"] + 1 + index + 1] = 0xFF
        save_model._write_gen2_party_data(index, bytes(mon), ot, nick)
        data[layout["party_offset"] + 1 + index] = 0xFD
        _write_gen2_checksums(save_model)
        return {"success": True, "destination": "party", "slot": index}

    target = save_model._find_empty_gen2_box_slot()
    if target is None:
        return {"success": False, "message": "extras_party_pc_full"}
    box_index, slot_index = target
    _, species_start, box_offset = save_model._gen2_box_header(box_index)
    old_count = int(data[box_offset])
    data[box_offset] = old_count + 1
    data[box_offset + 1 + old_count + 1] = 0xFF
    save_model._write_gen2_box_data(box_index, slot_index, bytes(mon[:32]), ot, nick)
    data[species_start + slot_index] = 0xFD
    save_model._sync_gen2_current_box_to_stored(box_index)
    _write_gen2_checksums(save_model)
    return {"success": True, "destination": "pc", "box": box_index, "slot": slot_index, "is_shiny": shiny}


def _write_gen2_checksums(save_model) -> None:
    from pokecable_save import write_gen2_checksums

    write_gen2_checksums(save_model.bytes, save_model.layout)


def _insert_gen3(save_model, parser, canonical: CanonicalPokemon) -> dict[str, Any]:
    raw = _mark_gen3_egg(parser, parser.build_party_mon_from_canonical(canonical))
    section1 = save_model.slot["section_offsets"].get(1) if getattr(save_model, "slot", None) else None
    if section1 is None:
        return {"success": False, "message": "extras_not_supported"}

    party_count_offset = section1 + save_model.layout["party_count_offset"]
    party_count = int(save_model.bytes[party_count_offset])
    if party_count < 6:
        save_model.bytes[party_count_offset] = party_count + 1
        save_model._write_gen3_party_data(party_count, raw)
        return {"success": True, "destination": "party", "slot": party_count}

    target = save_model._find_empty_gen3_box_slot()
    if target is None:
        return {"success": False, "message": "extras_party_pc_full"}
    box_index, slot_index = target
    save_model._write_gen3_box_data(box_index, slot_index, raw[:80])
    return {"success": True, "destination": "pc", "box": box_index, "slot": slot_index}


def _mark_gen3_egg(parser, raw_data: bytes) -> bytes:
    from ..parsers.gen3 import SUBSTRUCT_ORDERS

    raw = bytearray(raw_data)
    personality = int.from_bytes(raw[0:4], "little")
    trainer_id = int.from_bytes(raw[4:8], "little")
    secure = bytearray(parser._decrypt_secure(bytes(raw[:80])))
    order = SUBSTRUCT_ORDERS[personality % 24]
    growth = order[0] * 12
    misc = order[3] * 12
    secure[growth + 9] = EGG_HATCH_CYCLES
    iv_data = int.from_bytes(secure[misc:misc + 4], "little") | (1 << 30)
    secure[misc:misc + 4] = iv_data.to_bytes(4, "little")
    raw[28:30] = parser._box_checksum(bytes(secure)).to_bytes(2, "little")
    raw[32:80] = parser._encrypt_secure(bytes(secure), personality, trainer_id)
    raw[84] = 1
    return bytes(raw)


def _insert_gen4(save_model, parser, canonical: CanonicalPokemon) -> dict[str, Any]:
    party_raw = _mark_gen4_egg(parser._build_pk4_from_canonical(canonical, is_party=True))
    box_raw = _mark_gen4_egg(parser._build_pk4_from_canonical(canonical, is_party=False))

    party_count = parser._party_count()
    if party_count < 6:
        parser._general_view()[parser.layout.party_offset - 4] = party_count + 1
        parser._write_party_raw(party_count, party_raw)
        _sync_gen4_parser_to_save_model(save_model, parser)
        return {"success": True, "destination": "party", "slot": party_count}

    for box_index in range(18):
        for slot_index in range(30):
            current = parser._read_box_raw(box_index, slot_index)
            if not any(current) or parser._summary_from_raw(f"box:{box_index}:{slot_index}", current, is_party=False) is None:
                parser._write_box_raw(box_index, slot_index, box_raw)
                _sync_gen4_parser_to_save_model(save_model, parser)
                return {"success": True, "destination": "pc", "box": box_index, "slot": slot_index}

    return {"success": False, "message": "extras_party_pc_full"}


def _mark_gen4_egg(raw_data: bytes) -> bytes:
    from ..parsers.gen4 import _u32, _w32, decrypt_pk4, encrypt_pk4

    decrypted = bytearray(decrypt_pk4(raw_data))
    decrypted[0x14] = EGG_HATCH_CYCLES
    _w32(decrypted, 0x38, _u32(decrypted, 0x38) | (1 << 30))
    return encrypt_pk4(bytes(decrypted))


def _sync_gen4_parser_to_save_model(save_model, parser) -> None:
    with tempfile.TemporaryDirectory(prefix="pokecable_egg_") as tmpdir:
        tmp_path = Path(tmpdir) / (save_model.path.name or "save.sav")
        parser.save(tmp_path)
        save_model.bytes[:] = tmp_path.read_bytes()
