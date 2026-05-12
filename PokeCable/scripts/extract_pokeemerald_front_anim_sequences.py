#!/usr/bin/env python3
"""Extract Gen 3 Pokemon front sprite frame sequences from pret/pokeemerald."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "PokeCable/reference/pret/pokeemerald/src/data/pokemon_graphics/front_pic_anims.h"
POKEMON_SOURCE = ROOT / "PokeCable/reference/pret/pokeemerald/src/pokemon.c"
OUTPUT = ROOT / "PokeCable/frontend/generated/battle-assets/gen3/pokemon-front-anim-sequences.json"
FRAME_MS = 1000 / 60


def normalize_species(value: str) -> str:
    name = value.lower()
    name = name.replace("nidoran_f", "nidoran_f").replace("nidoran_m", "nidoran_m")
    name = name.replace("ho_oh", "ho_oh").replace("mr_mime", "mr_mime")
    return re.sub(r"[^a-z0-9]+", "_", name).strip("_")


def symbol_to_species(symbol: str) -> str:
    value = symbol.replace("SPECIES_", "").lower()
    replacements = {
        "nidoran_f": "nidoran_f",
        "nidoran_m": "nidoran_m",
        "farfetchd": "farfetchd",
        "mr_mime": "mr_mime",
        "ho_oh": "ho_oh",
        "unown_emark": "unown_emark",
        "unown_qmark": "unown_qmark",
    }
    return replacements.get(value, normalize_species(value))


def parse_anim_blocks(text: str) -> dict[str, list[dict[str, int]]]:
    blocks: dict[str, list[dict[str, int]]] = {}
    block_pattern = re.compile(
        r"static const union AnimCmd\s+(sAnim_[A-Za-z0-9_]+)\[\]\s*=\s*\{(?P<body>.*?)\};",
        re.S,
    )
    frame_pattern = re.compile(r"ANIMCMD_FRAME\((\d+),\s*(\d+)\)")
    for match in block_pattern.finditer(text):
        name = match.group(1)
        frames = [
            {"frame": int(frame), "duration_frames": int(duration)}
            for frame, duration in frame_pattern.findall(match.group("body"))
        ]
        if frames:
            blocks[name] = frames
    return blocks


def parse_anim_pointer_sets(text: str) -> dict[str, str]:
    sets: dict[str, str] = {}
    for macro in ("SINGLE_ANIMATION", "DOUBLE_ANIMATION"):
        macro_pattern = re.compile(rf"{macro}\((\w+)\);")
        for name in macro_pattern.findall(text):
            sets[f"sAnims_{name}"] = f"sAnim_{name}_1"

    set_pattern = re.compile(
        r"static const union AnimCmd \*const\s+(sAnims_[A-Za-z0-9_]+)\[\]\s*=\s*\{(?P<body>.*?)\};",
        re.S,
    )
    pointer_pattern = re.compile(r"(sAnim_[A-Za-z0-9_]+)")
    for match in set_pattern.finditer(text):
        pointers = [
            pointer
            for pointer in pointer_pattern.findall(match.group("body"))
            if pointer != "sAnim_GeneralFrame0"
        ]
        if pointers:
            sets[match.group(1)] = pointers[0]
    return sets


def parse_species_table(text: str) -> dict[str, str]:
    table_match = re.search(r"gMonFrontAnimsPtrTable\[\]\s*=\s*\{(?P<body>.*?)\};", text, re.S)
    if not table_match:
        raise SystemExit("Could not find gMonFrontAnimsPtrTable in front_pic_anims.h")
    entry_pattern = re.compile(r"\[(SPECIES_[A-Z0-9_]+)\]\s*=\s*(sAnims_[A-Za-z0-9_]+)")
    return {
        symbol_to_species(species): anim_set
        for species, anim_set in entry_pattern.findall(table_match.group("body"))
    }


def parse_front_motion_table(text: str) -> dict[str, str]:
    table_match = re.search(
        r"sMonFrontAnimIdsTable\[NUM_SPECIES - 1\]\s*=\s*\{(?P<body>.*?)\};",
        text,
        re.S,
    )
    if not table_match:
        return {}
    entry_pattern = re.compile(r"\[(SPECIES_[A-Z0-9_]+)\s*-\s*1\]\s*=\s*(ANIM_[A-Z0-9_]+)")
    return {
        symbol_to_species(species): motion
        for species, motion in entry_pattern.findall(table_match.group("body"))
    }


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8-sig")
    pokemon_text = POKEMON_SOURCE.read_text(encoding="utf-8")
    blocks = parse_anim_blocks(text)
    sets = parse_anim_pointer_sets(text)
    species_table = parse_species_table(text)
    motion_table = parse_front_motion_table(pokemon_text)
    species: dict[str, dict[str, object]] = {}
    for species_key, anim_set in sorted(species_table.items()):
        block_name = sets.get(anim_set)
        frames = blocks.get(block_name or "")
        if not frames:
            continue
        sequence = [frame["frame"] for frame in frames]
        durations_ms = [max(16, round(frame["duration_frames"] * FRAME_MS)) for frame in frames]
        species[species_key] = {
            "anim_set": anim_set,
            "anim": block_name,
            "sequence": sequence,
            "durations_frames": [frame["duration_frames"] for frame in frames],
            "durations_ms": durations_ms,
            "motion": motion_table.get(species_key, "ANIM_V_SQUISH_AND_BOUNCE"),
        }

    payload = {
        "generation": 3,
        "source": "reference/pret/pokeemerald/src/data/pokemon_graphics/front_pic_anims.h",
        "motion_source": "reference/pret/pokeemerald/src/pokemon.c",
        "frame_rate": 60,
        "count": len(species),
        "species": species,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
