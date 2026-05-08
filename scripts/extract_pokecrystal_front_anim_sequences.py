#!/usr/bin/env python3
"""Extract Gen 2 frontpic animation frame order from pokecrystal ASM."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "PokeCable/reference/pret/pokecrystal/gfx/pokemon"
OUTPUT = ROOT / "PokeCable/frontend/generated/battle-assets/gen2/pokemon-front-anim-sequences.json"
FRAME_RE = re.compile(r"^\s*frame\s+(\d+),\s*([0-9a-fA-F$]+)")
SETREPEAT_RE = re.compile(r"^\s*setrepeat\s+(\d+)")
DOREPEAT_RE = re.compile(r"^\s*dorepeat\s+(\d+)")


def parse_number(value: str) -> int:
    value = value.strip()
    if value.startswith("$"):
        return int(value[1:], 16)
    return int(value, 10)


def read_commands(path: Path) -> list[dict[str, int | str]]:
    commands: list[dict[str, int | str]] = []
    if not path.exists():
        return commands
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue
        if match := FRAME_RE.match(line):
            commands.append({
                "command": "frame",
                "frame": int(match.group(1)),
                "duration": parse_number(match.group(2)),
            })
        elif match := SETREPEAT_RE.match(line):
            commands.append({"command": "setrepeat", "count": int(match.group(1))})
        elif match := DOREPEAT_RE.match(line):
            commands.append({"command": "dorepeat", "target": int(match.group(1))})
        elif line.startswith("endanim"):
            commands.append({"command": "endanim"})
    return commands


def expand_commands(commands: list[dict[str, int | str]], max_steps: int = 256) -> list[dict[str, int]]:
    sequence: list[dict[str, int]] = []
    repeat_timer = 0
    pointer = 0
    steps = 0
    while 0 <= pointer < len(commands) and steps < max_steps:
        steps += 1
        command = commands[pointer]
        pointer += 1
        name = command.get("command")
        if name == "frame":
            sequence.append({
                "frame": int(command["frame"]),
                "duration_frames": int(command["duration"]),
                "duration_ms": max(16, round(int(command["duration"]) * 1000 / 60)),
            })
        elif name == "setrepeat":
            repeat_timer = int(command["count"])
        elif name == "dorepeat":
            if repeat_timer <= 0:
                continue
            repeat_timer -= 1
            if repeat_timer > 0:
                pointer = int(command["target"])
        elif name == "endanim":
            break
    return sequence


def animation_entry(path: Path, species_name: str) -> dict[str, object] | None:
    commands = read_commands(path)
    sequence = expand_commands(commands)
    if not sequence:
        return None
    relative_name = path.name
    return {
        "anim": f"gfx/pokemon/{species_name}/{relative_name}",
        "sequence": [entry["frame"] for entry in sequence],
        "durations_frames": [entry["duration_frames"] for entry in sequence],
        "durations_ms": [entry["duration_ms"] for entry in sequence],
        "command_count": len(commands),
    }


def build() -> dict[str, object]:
    species: dict[str, object] = {}
    idle_species: dict[str, object] = {}
    for pokemon_dir in sorted(path for path in SOURCE_ROOT.iterdir() if path.is_dir()):
        species_name = pokemon_dir.name
        entry = animation_entry(pokemon_dir / "anim.asm", species_name)
        if entry:
            species[species_name] = entry
        idle_entry = animation_entry(pokemon_dir / "anim_idle.asm", species_name)
        if idle_entry:
            idle_species[species_name] = idle_entry
    return {
        "source": "reference/pret/pokecrystal/gfx/pokemon/*/{anim.asm,anim_idle.asm}",
        "semantics": "frame N,duration plus setrepeat/dorepeat as implemented by engine/gfx/pic_animation.asm",
        "species": species,
        "idle_species": idle_species,
    }


def main() -> None:
    data = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUTPUT} with {len(data['species'])} front animations "
        f"and {len(data['idle_species'])} idle animations"
    )


if __name__ == "__main__":
    main()
