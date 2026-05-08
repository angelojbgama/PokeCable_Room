from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE_ROOT = PROJECT_ROOT / "reference" / "pret"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "PokeCable" / "frontend" / "generated" / "battle-assets"


@dataclass(frozen=True)
class GenerationSource:
    generation: int
    repo_name: str
    pokemon_root: Path
    front_glob: str
    back_glob: str
    battle_asset_dirs: tuple[Path, ...]
    optional_animation_dirs: tuple[Path, ...]
    behavior_dirs: tuple[Path, ...]
    behavior_files: tuple[Path, ...] = ()
    behavior_globs: tuple[str, ...] = ()


def _normalize_asset_key(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_").replace("'", "").replace(".", "")


def _normalize_move_key(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _strip_asm_comment(line: str) -> str:
    """Strip common pret asm comments while keeping quoted strings intact."""
    in_quote = False
    for index, char in enumerate(line):
        if char == '"':
            in_quote = not in_quote
        if not in_quote and char in {";", "@"}:
            return line[:index]
    return line


def _split_asm_args(value: str) -> list[str]:
    args: list[str] = []
    current: list[str] = []
    depth = 0
    in_quote = False
    for char in value:
        if char == '"':
            in_quote = not in_quote
        elif not in_quote and char == "(":
            depth += 1
        elif not in_quote and char == ")" and depth:
            depth -= 1
        if char == "," and not in_quote and depth == 0:
            item = "".join(current).strip()
            if item:
                args.append(item)
            current = []
            continue
        current.append(char)
    item = "".join(current).strip()
    if item:
        args.append(item)
    return args


def _parse_asm_statement(line: str) -> dict[str, Any] | None:
    stripped = _strip_asm_comment(line).strip()
    if not stripped or stripped.endswith(":"):
        return None
    parts = stripped.split(None, 1)
    command = parts[0]
    args = _split_asm_args(parts[1]) if len(parts) > 1 else []
    return {
        "command": command,
        "args": args,
        "raw": stripped,
    }


def _asm_int(value: str, default: int = 0) -> int:
    cleaned = value.strip().replace("$", "0x")
    try:
        return int(cleaned, 0)
    except ValueError:
        return default


def _asm_flags(value: str) -> dict[str, bool]:
    return {
        "xflip": "OAM_XFLIP" in value or "B_OAM_XFLIP" in value,
        "yflip": "OAM_YFLIP" in value or "B_OAM_YFLIP" in value,
    }


def _collect_constants(path: Path, prefix: str) -> dict[str, int]:
    constants: dict[str, int] = {}
    if not path.exists():
        return constants
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(rf"\bconst\s+({re.escape(prefix)}[A-Z0-9_]+)", line)
        if match:
            constants[match.group(1)] = len(constants)
    return constants


def _constant_hex_index(name: str, prefix: str) -> int | None:
    match = re.search(rf"{re.escape(prefix)}([0-9A-F]{{2}})$", name)
    return int(match.group(1), 16) if match else None


def _script_steps(body: str) -> list[dict[str, Any]]:
    ignored = {"db", "dw", "table_width", "assert_table_length", ".2byte", ".4byte", ".align"}
    steps: list[dict[str, Any]] = []
    for raw in body.splitlines():
        statement = _parse_asm_statement(raw)
        if not statement or statement["command"] in ignored:
            continue
        steps.append(statement)
    return steps


def _generated_asset_path(generation: int, repo_root: Path, source_path: Path) -> str | None:
    output_prefixes = {
        1: (repo_root / "gfx" / "battle", Path("gen1/ui/battle")),
        2: (repo_root / "gfx" / "battle_anims", Path("gen2/ui/battle_anims")),
        3: (repo_root / "graphics" / "battle_anims", Path("gen3/ui/battle_anims")),
    }
    source_base, output_base = output_prefixes[generation]
    try:
        return (output_base / source_path.relative_to(source_base)).as_posix()
    except ValueError:
        return None


def _asset_record(
    generation: int,
    repo_root: Path,
    source_path: Path,
    *,
    role: str,
    tag: str | None = None,
    symbol: str | None = None,
    source_symbol: str | None = None,
    size: str | None = None,
) -> dict[str, Any] | None:
    path = _generated_asset_path(generation, repo_root, source_path)
    if not path:
        return None
    record: dict[str, Any] = {
        "role": role,
        "path": path,
        "source": source_path.as_posix(),
    }
    if tag:
        record["tag"] = tag
    if symbol:
        record["symbol"] = symbol
    if source_symbol:
        record["source_symbol"] = source_symbol
    if size:
        record["vram_size"] = size
    _attach_png_metadata(record, source_path, Path(path), role=role)
    return record


def _dedupe_assets(records: list[dict[str, Any] | None]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    indexes: dict[tuple[str, str, str], int] = {}
    for record in records:
        if not record:
            continue
        key = (str(record.get("role", "")), str(record.get("tag", "")), str(record.get("path", "")))
        if key in indexes:
            existing = deduped[indexes[key]]
            if record.get("composites"):
                existing.setdefault("composites", []).extend(record["composites"])
            continue
        indexes[key] = len(deduped)
        deduped.append(record)
    return deduped


def _png_dimensions(path: Path) -> dict[str, int] | None:
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return {"width": int(width), "height": int(height)}


def _grid_frame_metadata(width: int, height: int, frame_width: int, frame_height: int, *, layout: str, frame_ms: int) -> dict[str, Any]:
    columns = max(1, width // frame_width)
    rows = max(1, height // frame_height)
    return {
        "layout": layout,
        "width": frame_width,
        "height": frame_height,
        "columns": columns,
        "rows": rows,
        "count": columns * rows,
        "frame_ms": frame_ms,
    }


def _infer_frame_metadata(path: Path, role: str, generated_path: str, dimensions: dict[str, int]) -> dict[str, Any]:
    width = dimensions["width"]
    height = dimensions["height"]
    name = path.name
    generated = generated_path.lower()

    if role == "gen3_anim_background" or "/backgrounds/" in generated:
        return _grid_frame_metadata(width, height, width, height, layout="static", frame_ms=140)

    if role == "pokemon_anim_front" or name == "anim_front.png":
        frame_width = 64 if width % 64 == 0 else width
        frame_height = 64 if height % 64 == 0 else min(width, height)
        return _grid_frame_metadata(width, height, frame_width, frame_height, layout="pokemon_front", frame_ms=150)

    if "/pokemon/" in generated:
        return _grid_frame_metadata(width, height, width, height, layout="static", frame_ms=160)

    if role in {"gen1_tileset", "gen2_anim_gfx"} or "move_anim_" in name:
        frame_width = 8 if width % 8 == 0 else width
        frame_height = 8 if height % 8 == 0 else height
        return _grid_frame_metadata(width, height, frame_width, frame_height, layout="gb_tile_sheet", frame_ms=70)

    if role == "gen3_anim_sprite" or "/sprites/" in generated:
        if height > width and width > 0 and height % width == 0:
            return _grid_frame_metadata(width, height, width, width, layout="vertical_strip", frame_ms=65)
        if width > height and height > 0 and width % height == 0:
            return _grid_frame_metadata(width, height, height, height, layout="horizontal_strip", frame_ms=65)
        if width % 32 == 0 and height % 32 == 0 and (width > 32 or height > 32):
            return _grid_frame_metadata(width, height, 32, 32, layout="grid_32", frame_ms=65)
        if width % 16 == 0 and height % 16 == 0 and (width > 16 or height > 16):
            return _grid_frame_metadata(width, height, 16, 16, layout="grid_16", frame_ms=65)
        if width % 8 == 0 and height % 8 == 0 and (width > 8 or height > 8):
            return _grid_frame_metadata(width, height, 8, 8, layout="grid_8", frame_ms=65)

    return _grid_frame_metadata(width, height, width, height, layout="static", frame_ms=100)


def _attach_png_metadata(record: dict[str, Any], source: Path, relative_output: Path, *, role: str = "") -> None:
    if source.suffix.lower() != ".png":
        return
    dimensions = _png_dimensions(source)
    if not dimensions:
        return
    generated_path = relative_output.as_posix()
    inferred_role = role
    if not inferred_role:
        if generated_path.endswith("/anim_front.png"):
            inferred_role = "pokemon_anim_front"
        elif "/pokemon/" in generated_path:
            inferred_role = "pokemon_sprite"
        elif "/backgrounds/" in generated_path:
            inferred_role = "gen3_anim_background"
        elif "/sprites/" in generated_path:
            inferred_role = "gen3_anim_sprite"
        elif "move_anim_" in source.name:
            inferred_role = "gen1_tileset"
    record["dimensions"] = dimensions
    record["frame"] = _infer_frame_metadata(source, inferred_role, generated_path, dimensions)


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file(source: Path, destination_root: Path, relative_output: Path, *, include_hash: bool = False) -> dict[str, Any]:
    destination = destination_root / relative_output
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.stat().st_size != source.stat().st_size:
        if destination.exists():
            destination.unlink()
        try:
            os.link(source, destination)
        except OSError:
            shutil.copy2(source, destination)
    record: dict[str, Any] = {
        "path": relative_output.as_posix(),
        "source": source.as_posix(),
        "bytes": source.stat().st_size,
    }
    _attach_png_metadata(record, source, relative_output)
    if include_hash:
        record["sha1"] = _sha1(source)
    return record


def _species_name_from_gen1_front(path: Path) -> str:
    return _normalize_asset_key(path.stem)


def _species_name_from_gen1_back(path: Path) -> str:
    stem = path.stem
    if stem.endswith("b"):
        stem = stem[:-1]
    return _normalize_asset_key(stem)


def _species_name_from_parent(path: Path) -> str:
    return _normalize_asset_key(path.parent.name)


def _source_config(reference_root: Path) -> list[GenerationSource]:
    pokered = reference_root / "pokered"
    pokecrystal = reference_root / "pokecrystal"
    pokeemerald = reference_root / "pokeemerald"
    return [
        GenerationSource(
            generation=1,
            repo_name="pokered",
            pokemon_root=pokered / "gfx" / "pokemon",
            front_glob="front/*.png",
            back_glob="back/*.png",
            battle_asset_dirs=(
                pokered / "gfx" / "battle",
                pokered / "gfx" / "font",
            ),
            optional_animation_dirs=(),
            behavior_dirs=(
                pokered / "constants",
                pokered / "data" / "battle",
                pokered / "data" / "battle_anims",
                pokered / "data" / "moves",
                pokered / "engine" / "battle",
            ),
        ),
        GenerationSource(
            generation=2,
            repo_name="pokecrystal",
            pokemon_root=pokecrystal / "gfx" / "pokemon",
            front_glob="*/front.png",
            back_glob="*/back.png",
            battle_asset_dirs=(
                pokecrystal / "gfx" / "battle",
                pokecrystal / "gfx" / "font",
                pokecrystal / "gfx" / "frames",
            ),
            optional_animation_dirs=(pokecrystal / "gfx" / "battle_anims",),
            behavior_dirs=(
                pokecrystal / "constants",
                pokecrystal / "data" / "battle",
                pokecrystal / "data" / "battle_anims",
                pokecrystal / "data" / "moves",
                pokecrystal / "engine" / "battle",
                pokecrystal / "engine" / "battle_anims",
            ),
            behavior_files=(pokecrystal / "docs" / "battle_anim_commands.md",),
        ),
        GenerationSource(
            generation=3,
            repo_name="pokeemerald",
            pokemon_root=pokeemerald / "graphics" / "pokemon",
            front_glob="*/front.png",
            back_glob="*/back.png",
            battle_asset_dirs=(
                pokeemerald / "graphics" / "battle_interface",
                pokeemerald / "graphics" / "battle_transitions",
            ),
            optional_animation_dirs=(pokeemerald / "graphics" / "battle_anims",),
            behavior_dirs=(
                pokeemerald / "data",
                pokeemerald / "src",
                pokeemerald / "src" / "data",
            ),
            behavior_files=(
                pokeemerald / "data" / "battle_ai_scripts.s",
                pokeemerald / "data" / "battle_anim_scripts.s",
                pokeemerald / "data" / "battle_scripts_1.s",
                pokeemerald / "data" / "battle_scripts_2.s",
            ),
            behavior_globs=(
                "data/battle*.s",
                "src/battle*.c",
                "src/battle_anim*.c",
                "src/anim_mon_front_pics.c",
                "src/pokemon_animation.c",
                "src/recorded_battle.c",
                "src/reshow_battle_screen.c",
                "src/data/battle*.h",
                "src/data/battle_anim.h",
                "src/data/battle_moves.h",
                "src/data/pokemon_graphics/*anim*.h",
                "src/data/trainer_graphics/*anim*.h",
                "include/battle*.h",
            ),
        ),
    ]


def _assert_sources_exist(sources: list[GenerationSource]) -> None:
    missing = []
    for source in sources:
        repo_root = source.pokemon_root.parents[1]
        if not repo_root.exists():
            missing.append(f"Gen {source.generation}: {repo_root}")
    if missing:
        joined = "\n".join(missing)
        raise FileNotFoundError(f"Repositorios pret ausentes. Rode o clone primeiro:\n{joined}")


def _collect_pokemon_sprites(source: GenerationSource, output_root: Path) -> dict[str, Any]:
    species: dict[str, dict[str, Any]] = {}

    if source.generation == 1:
        front_name = _species_name_from_gen1_front
        back_name = _species_name_from_gen1_back
    else:
        front_name = _species_name_from_parent
        back_name = _species_name_from_parent

    for side, pattern, namer in (
        ("front", source.front_glob, front_name),
        ("back", source.back_glob, back_name),
    ):
        for sprite in sorted(source.pokemon_root.glob(pattern)):
            species_name = namer(sprite)
            relative_output = Path(f"gen{source.generation}/pokemon/{species_name}/{side}.png")
            copied = _copy_file(sprite, output_root, relative_output)
            species.setdefault(species_name, {})[side] = copied

    if source.generation == 3:
        for sprite in sorted(source.pokemon_root.glob("*/anim_front.png")):
            species_name = _species_name_from_parent(sprite)
            relative_output = Path(f"gen{source.generation}/pokemon/{species_name}/anim_front.png")
            copied = _copy_file(sprite, output_root, relative_output)
            species.setdefault(species_name, {})["anim_front"] = copied

    return {
        "count": len(species),
        "species": species,
    }


def _collect_battle_assets(source: GenerationSource, output_root: Path, *, include_move_anims: bool) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    asset_dirs = list(source.battle_asset_dirs)
    if include_move_anims:
        asset_dirs.extend(source.optional_animation_dirs)
    for asset_dir in asset_dirs:
        if not asset_dir.exists():
            continue
        group_name = _normalize_asset_key(asset_dir.name)
        for asset in sorted(asset_dir.rglob("*.png")):
            relative_inside_group = asset.relative_to(asset_dir)
            relative_output = Path(f"gen{source.generation}/ui/{group_name}") / relative_inside_group
            groups.setdefault(group_name, []).append(_copy_file(asset, output_root, relative_output))
    return {
        "count": sum(len(items) for items in groups.values()),
        "groups": groups,
    }


def _behavior_file_allowed(path: Path, source: GenerationSource) -> bool:
    suffixes = {".asm", ".s", ".inc", ".c", ".h", ".md"}
    if path.suffix.lower() not in suffixes:
        return False
    lowered = path.as_posix().lower()
    if source.generation == 3:
        return "battle" in lowered or "move" in lowered or "anim" in lowered
    return True


def _collect_behavior_index(source: GenerationSource) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    candidates: set[Path] = set()
    repo_root = source.pokemon_root.parents[1]
    if source.behavior_globs:
        for pattern in source.behavior_globs:
            candidates.update(path for path in repo_root.glob(pattern) if path.is_file())
    else:
        for behavior_dir in source.behavior_dirs:
            if behavior_dir.exists():
                candidates.update(path for path in behavior_dir.rglob("*") if path.is_file())
    candidates.update(path for path in source.behavior_files if path.exists())

    for path in sorted(candidates):
        if not _behavior_file_allowed(path, source):
            continue
        relative = path.relative_to(repo_root).as_posix()
        files[relative] = {
            "source": path.as_posix(),
            "bytes": path.stat().st_size,
        }
    return {
        "count": len(files),
        "files": files,
    }


def _label_blocks(path: Path) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current_labels: list[str] = []
    current_lines: list[str] = []

    def flush() -> None:
        if not current_labels:
            return
        body = "\n".join(current_lines)
        for label in current_labels:
            blocks[label] = body

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not line.startswith((" ", "\t")) and stripped.endswith(":"):
            label = stripped[:-1]
            if current_lines:
                flush()
                current_labels = [label]
                current_lines = []
            else:
                current_labels.append(label)
            continue
        if current_labels:
            current_lines.append(line)
    flush()
    return blocks


def _pointer_labels(path: Path, table_label: str, pointer_directive: str, stop_markers: tuple[str, ...]) -> list[str]:
    labels: list[str] = []
    in_table = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith(table_label):
            in_table = True
            continue
        if not in_table:
            continue
        if any(marker in stripped for marker in stop_markers):
            break
        if stripped.startswith(pointer_directive):
            label = stripped.split(None, 1)[1].split()[0].split("@", 1)[0].strip()
            labels.append(label)
    return labels


def _move_key_from_label(label: str) -> str:
    value = label
    for prefix in ("BattleAnim_", "Move_"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    for suffix in ("Anim", "M"):
        if value.endswith(suffix) and len(value) > len(suffix):
            value = value[: -len(suffix)]
    return _normalize_move_key(value)


def _animation_family(label: str, body: str) -> str:
    text = f"{label}\n{body}".lower()
    checks = (
        ("electric", ("thunder", "spark", "electric", "zap", "lightning")),
        ("fire", ("fire", "flame", "ember", "burn")),
        ("water", ("water", "surf", "bubble", "hydro", "whirlpool", "clamp")),
        ("ice", ("ice", "blizzard", "powder_snow", "powdersnow")),
        ("grass", ("leaf", "vine", "petal", "spore", "seed", "powder")),
        ("psychic", ("psychic", "psy", "confusion", "hypnosis", "dream", "kinesis")),
        ("poison", ("poison", "toxic", "sludge", "smog", "acid")),
        ("ground", ("earthquake", "fissure", "dig", "mud", "sand")),
        ("rock", ("rock", "rollout", "bone")),
        ("wind", ("gust", "wind", "fly", "wing", "aeroblast", "sky")),
        ("explosion", ("explosion", "selfdestruct", "self_destruct")),
        ("status", ("recover", "heal", "reflect", "screen", "barrier", "protect", "detect", "harden", "dance")),
        ("drain", ("drain", "absorb", "leech")),
        ("impact", ("impact", "hitsplat", "pound", "scratch", "punch", "kick", "slam", "tackle")),
        ("flash", ("flash", "light", "blend", "palette", "invert")),
    )
    for family, needles in checks:
        if any(needle in text for needle in needles):
            return family
    return "impact"


def _summarize_animation(label: str, body: str) -> dict[str, Any]:
    script = _script_steps(body)
    commands = [step["command"] for step in script]
    return {
        "label": label,
        "family": _animation_family(label, body),
        "command_count": len(commands),
        "commands": commands[:16],
        "script": script,
    }


def _frame_with_bounds(tiles: list[dict[str, Any]], *, duration_frames: int = 1, label: str = "") -> dict[str, Any]:
    if not tiles:
        return {
            "label": label,
            "duration_frames": duration_frames,
            "bounds": {"x": 0, "y": 0, "width": 8, "height": 8},
            "tiles": [],
        }
    min_x = min(tile["x"] for tile in tiles)
    min_y = min(tile["y"] for tile in tiles)
    max_x = max(tile["x"] + 8 for tile in tiles)
    max_y = max(tile["y"] + 8 for tile in tiles)
    return {
        "label": label,
        "duration_frames": duration_frames,
        "bounds": {"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y},
        "tiles": tiles,
    }


def _composite_sequence(label: str, frames: list[dict[str, Any]], *, source: str) -> dict[str, Any]:
    if not frames:
        frames = [_frame_with_bounds([], label=label)]
    min_x = min(frame["bounds"]["x"] for frame in frames)
    min_y = min(frame["bounds"]["y"] for frame in frames)
    max_x = max(frame["bounds"]["x"] + frame["bounds"]["width"] for frame in frames)
    max_y = max(frame["bounds"]["y"] + frame["bounds"]["height"] for frame in frames)
    return {
        "source": source,
        "label": label,
        "tile_size": 8,
        "frame_ms": 70,
        "bounds": {"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y},
        "frames": frames,
    }


def _parse_dbsprite(statement: dict[str, Any], *, tile_offset: int = 0) -> dict[str, Any] | None:
    args = statement.get("args", [])
    if statement.get("command") != "dbsprite" or len(args) < 6:
        return None
    flags = _asm_flags(args[5])
    return {
        "x": _asm_int(args[0]) * 8 + _asm_int(args[2]),
        "y": _asm_int(args[1]) * 8 + _asm_int(args[3]),
        "tile": tile_offset + _asm_int(args[4]),
        **flags,
    }


def _collect_gen1_frame_blocks(reference_root: Path) -> dict[str, dict[str, Any]]:
    path = reference_root / "pokered" / "data" / "battle_anims" / "frame_blocks.asm"
    constants_path = reference_root / "pokered" / "constants" / "move_animation_constants.asm"
    frame_constants = _collect_constants(constants_path, "FRAMEBLOCK_")
    if not path.exists():
        return {}
    labels = _pointer_labels(path, "FrameBlockPointers:", "dw", ("assert_table_length NUM_FRAMEBLOCKS",))
    blocks = _label_blocks(path)
    frame_blocks: dict[str, dict[str, Any]] = {}
    for index, label in enumerate(labels):
        tiles = []
        for line in blocks.get(label, "").splitlines():
            statement = _parse_asm_statement(line)
            tile = _parse_dbsprite(statement or {})
            if tile:
                tiles.append(tile)
        frame = _frame_with_bounds(tiles, label=label)
        constant = next((name for name, value in frame_constants.items() if value == index), f"FRAMEBLOCK_{index:02X}")
        frame_blocks[constant] = frame
    return frame_blocks


def _collect_gen1_subanimations(reference_root: Path) -> dict[str, list[dict[str, Any]]]:
    path = reference_root / "pokered" / "data" / "battle_anims" / "subanimations.asm"
    constants_path = reference_root / "pokered" / "constants" / "move_animation_constants.asm"
    subanim_constants = _collect_constants(constants_path, "SUBANIM_")
    if not path.exists():
        return {}
    labels = _pointer_labels(path, "SubanimationPointers:", "dw", ("assert_table_length NUM_SUBANIMS",))
    blocks = _label_blocks(path)
    frame_blocks = _collect_gen1_frame_blocks(reference_root)
    subanimations: dict[str, list[dict[str, Any]]] = {}
    for index, label in enumerate(labels):
        frames = []
        for line in blocks.get(label, "").splitlines():
            statement = _parse_asm_statement(line)
            if not statement or statement["command"] != "db" or len(statement["args"]) < 3:
                continue
            block = frame_blocks.get(statement["args"][0])
            if not block:
                continue
            frame = {
                **block,
                "label": statement["args"][0],
                "base_coord": statement["args"][1],
                "mode": statement["args"][2],
            }
            frames.append(frame)
        constant = next((name for name, value in subanim_constants.items() if value == index), label)
        subanimations[constant] = frames
    return subanimations


def _collect_gen1_composites(reference_root: Path) -> dict[str, dict[str, Any]]:
    return {
        name: _composite_sequence(name, frames, source="pokered.frame_blocks")
        for name, frames in _collect_gen1_subanimations(reference_root).items()
        if frames
    }


def _collect_gen1_move_assets(reference_root: Path, body: str) -> list[dict[str, Any]]:
    repo_root = reference_root / "pokered"
    composites = _collect_gen1_composites(reference_root)
    assets: list[dict[str, Any] | None] = []
    for step in _script_steps(body):
        if step["command"] != "battle_anim" or len(step["args"]) < 4:
            continue
        tileset = step["args"][2]
        subanim = step["args"][1]
        if tileset not in {"0", "1"}:
            continue
        source_path = repo_root / "gfx" / "battle" / f"move_anim_{tileset}.png"
        record = _asset_record(
            1,
            repo_root,
            source_path,
            role="gen1_tileset",
            tag=f"MOVE_ANIM_TILESET_{tileset}",
            symbol=f"move_anim_{tileset}",
        )
        if record and subanim in composites:
            record["composites"] = [{**composites[subanim], "tileset": int(tileset)}]
        assets.append(record)
    return _dedupe_assets(assets)


def _collect_gen1_animation_map(reference_root: Path) -> dict[str, Any]:
    path = reference_root / "pokered" / "data" / "moves" / "animations.asm"
    if not path.exists():
        return {"source": path.as_posix(), "count": 0, "moves": {}}
    labels = _pointer_labels(path, "AttackAnimationPointers:", "dw", ("assert_table_length NUM_ATTACKS",))
    blocks = _label_blocks(path)
    moves = {}
    for index, label in enumerate(labels, start=1):
        body = blocks.get(label, "")
        moves[_move_key_from_label(label)] = {
            "move_id": index,
            **_summarize_animation(label, body),
            "assets": _collect_gen1_move_assets(reference_root, body),
        }
    return {"source": path.as_posix(), "count": len(moves), "moves": moves}


def _collect_gen2_gfx_label_sources(repo_root: Path) -> dict[str, Path]:
    path = repo_root / "gfx" / "battle_anims.asm"
    labels: dict[str, Path] = {}
    if not path.exists():
        return labels
    pattern = re.compile(r'^(AnimObj\w+GFX):\s+INCBIN\s+"gfx/battle_anims/([^"]+)\.2bpp\.lz"')
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(line.strip())
        if not match:
            continue
        labels[match.group(1)] = repo_root / "gfx" / "battle_anims" / f"{match.group(2)}.png"
    return labels


def _collect_gen2_gfx_constants(repo_root: Path) -> list[str]:
    path = repo_root / "constants" / "battle_anim_constants.asm"
    constants: list[str] = []
    if not path.exists():
        return constants
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.search(r"\bconst\s+(BATTLE_ANIM_GFX_[A-Z0-9_]+)", line)
        if match:
            constants.append(match.group(1))
        elif constants and "NUM_BATTLE_ANIM_GFX" in line:
            break
    return constants


def _collect_gen2_gfx_assets(repo_root: Path) -> dict[str, dict[str, Any]]:
    gfx_label_sources = _collect_gen2_gfx_label_sources(repo_root)
    gfx_constants = _collect_gen2_gfx_constants(repo_root)
    table_path = repo_root / "data" / "battle_anims" / "object_gfx.asm"
    assets: dict[str, dict[str, Any]] = {}
    if not table_path.exists():
        return assets
    entries = []
    for line in table_path.read_text(encoding="utf-8", errors="replace").splitlines():
        statement = _parse_asm_statement(line)
        if not statement or statement["command"] != "anim_obj_gfx" or len(statement["args"]) < 2:
            continue
        entries.append(statement["args"][1])
    for entry_index, label in enumerate(entries):
        if entry_index == 0 or entry_index - 1 >= len(gfx_constants):
            continue
        constant = gfx_constants[entry_index - 1]
        source_path = gfx_label_sources.get(label)
        if not source_path:
            continue
        record = _asset_record(
            2,
            repo_root,
            source_path,
            role="gen2_anim_gfx",
            tag=constant,
            symbol=label,
        )
        if record:
            assets[constant] = record
    return assets


def _collect_gen2_oamsets(repo_root: Path) -> dict[str, dict[str, Any]]:
    path = repo_root / "data" / "battle_anims" / "oam.asm"
    if not path.exists():
        return {}
    blocks = _label_blocks(path)
    oamsets: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        statement = _parse_asm_statement(line)
        if not statement or statement["command"] != "battleanimoam" or len(statement["args"]) < 3:
            continue
        comment_match = re.search(r";\s*(BATTLE_ANIM_OAMSET_[A-Z0-9_]+)", line)
        if not comment_match:
            continue
        offset = _asm_int(statement["args"][0])
        length = _asm_int(statement["args"][1])
        label = statement["args"][2]
        tiles = []
        for raw in blocks.get(label, "").splitlines():
            tile_statement = _parse_asm_statement(raw)
            tile = _parse_dbsprite(tile_statement or {}, tile_offset=offset)
            if tile:
                tiles.append(tile)
        oamsets[comment_match.group(1)] = {
            "label": label,
            "tile_offset": offset,
            "length": length,
            "tiles": tiles[:length],
        }
    return oamsets


def _collect_gen2_framesets(repo_root: Path) -> dict[str, dict[str, Any]]:
    path = repo_root / "data" / "battle_anims" / "framesets.asm"
    constants_path = repo_root / "constants" / "battle_anim_constants.asm"
    frameset_constants = _collect_constants(constants_path, "BATTLE_ANIM_FRAMESET_")
    if not path.exists():
        return {}
    labels = _pointer_labels(path, "BattleAnimFrameData:", "dw", ("assert_table_length NUM_BATTLE_ANIM_FRAMESETS",))
    blocks = _label_blocks(path)
    framesets: dict[str, dict[str, Any]] = {}
    for index, label in enumerate(labels):
        frames = []
        for raw in blocks.get(label, "").splitlines():
            statement = _parse_asm_statement(raw)
            if not statement:
                continue
            if statement["command"] == "oamframe" and len(statement["args"]) >= 2:
                flags = _asm_flags(" ".join(statement["args"][2:]))
                frames.append({
                    "oamset": statement["args"][0],
                    "duration_frames": _asm_int(statement["args"][1], 1),
                    **flags,
                })
            elif statement["command"] == "oamwait" and statement["args"]:
                frames.append({
                    "wait": True,
                    "duration_frames": _asm_int(statement["args"][0], 1),
                })
            elif statement["command"] in {"oamdelete", "oamrestart"}:
                break
        constant = next((name for name, value in frameset_constants.items() if value == index), label)
        framesets[constant] = {"label": label, "frames": frames}
    return framesets


def _collect_gen2_objects(repo_root: Path) -> dict[str, dict[str, Any]]:
    path = repo_root / "data" / "battle_anims" / "objects.asm"
    constants_path = repo_root / "constants" / "battle_anim_constants.asm"
    object_constants = [
        name
        for name, _value in sorted(
            _collect_constants(constants_path, "BATTLE_ANIM_OBJ_").items(),
            key=lambda item: item[1],
        )
    ]
    objects: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return objects
    pending_comment: str | None = None
    entry_index = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        comment_match = re.search(r";\s*(BATTLE_ANIM_OBJ_[A-Z0-9_]+)", line)
        if comment_match:
            pending_comment = comment_match.group(1)
            continue
        statement = _parse_asm_statement(line)
        if not statement or statement["command"] != "battleanimobj":
            continue
        canonical_object = object_constants[entry_index] if entry_index < len(object_constants) else pending_comment
        entry_index += 1
        if not canonical_object:
            pending_comment = None
            continue
        args = statement["args"]
        if len(args) >= 6:
            data = {
                "flags": args[0],
                "yfix": args[1],
                "frameset": args[2],
                "callback": args[3],
                "palette": args[4],
                "gfx": args[5],
                "comment_object": pending_comment or "",
            }
            if pending_comment and pending_comment != canonical_object:
                data["aliases"] = [pending_comment]
            objects[canonical_object] = data
            if pending_comment and pending_comment != canonical_object:
                objects.setdefault(pending_comment, data)
        pending_comment = None
    return objects


def _gen2_object_composite(object_name: str, object_data: dict[str, Any], framesets: dict[str, dict[str, Any]], oamsets: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    frameset = framesets.get(object_data.get("frameset", ""))
    if not frameset:
        return None
    frames = []
    for frame_ref in frameset.get("frames", []):
        if frame_ref.get("wait"):
            if frames:
                frames.append({**frames[-1], "duration_frames": frame_ref.get("duration_frames", 1)})
            continue
        oamset = oamsets.get(frame_ref.get("oamset", ""))
        if not oamset:
            continue
        tiles = []
        for tile in oamset.get("tiles", []):
            tiles.append({
                **tile,
                "xflip": bool(tile.get("xflip")) ^ bool(frame_ref.get("xflip")),
                "yflip": bool(tile.get("yflip")) ^ bool(frame_ref.get("yflip")),
            })
        frames.append(_frame_with_bounds(tiles, duration_frames=frame_ref.get("duration_frames", 1), label=frame_ref.get("oamset", "")))
    if not frames:
        return None
    return {
        **_composite_sequence(object_name, frames, source="pokecrystal.oam"),
        "object": object_name,
        "frameset": object_data.get("frameset", ""),
        "callback": object_data.get("callback", ""),
        "palette": object_data.get("palette", ""),
        "gfx": object_data.get("gfx", ""),
    }


def _gen2_logic(body: str, objects_meta: dict[str, dict[str, Any]], framesets: dict[str, dict[str, Any]], oamsets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    waits: list[int] = []
    objects: list[dict[str, Any]] = []
    bg_effects: list[dict[str, Any]] = []
    direct_gfx: list[str] = []
    for step in _script_steps(body):
        command = step["command"]
        args = step["args"]
        if command.startswith("anim_") and command.endswith("gfx"):
            direct_gfx.extend(arg for arg in args if arg.startswith("BATTLE_ANIM_GFX_"))
        elif command == "anim_obj" and args:
            object_data = objects_meta.get(args[0], {})
            objects.append({
                "object": args[0],
                "gfx": object_data.get("gfx", ""),
                "frameset": object_data.get("frameset", ""),
                "callback": object_data.get("callback", ""),
                "args": args[1:],
                "composite": _gen2_object_composite(args[0], object_data, framesets, oamsets),
            })
        elif command == "anim_bgeffect" and args:
            bg_effects.append({"effect": args[0], "args": args[1:]})
        elif command == "anim_wait" and args:
            try:
                waits.append(int(args[0], 0))
            except ValueError:
                pass
    return {
        "direct_gfx": direct_gfx,
        "objects": objects,
        "bg_effects": bg_effects,
        "wait_frames": waits,
        "total_wait_frames": sum(waits),
    }


def _collect_gen2_animation_map(reference_root: Path) -> dict[str, Any]:
    path = reference_root / "pokecrystal" / "data" / "moves" / "animations.asm"
    if not path.exists():
        return {"source": path.as_posix(), "count": 0, "moves": {}}
    repo_root = reference_root / "pokecrystal"
    gfx_assets = _collect_gen2_gfx_assets(repo_root)
    objects_meta = _collect_gen2_objects(repo_root)
    framesets = _collect_gen2_framesets(repo_root)
    oamsets = _collect_gen2_oamsets(repo_root)
    labels = _pointer_labels(path, "BattleAnimations::", "dw", ("assert_table_length",))
    blocks = _label_blocks(path)
    moves = {}
    for index, label in enumerate(labels):
        if index == 0:
            continue
        body = blocks.get(label, "")
        logic = _gen2_logic(body, objects_meta, framesets, oamsets)
        asset_tags = logic["direct_gfx"] + [item["gfx"] for item in logic["objects"] if item.get("gfx")]
        asset_records = []
        for tag in asset_tags:
            record = gfx_assets.get(tag)
            if not record:
                continue
            composites = [item["composite"] for item in logic["objects"] if item.get("gfx") == tag and item.get("composite")]
            if composites:
                record = {**record, "composites": composites}
            asset_records.append(record)
        moves[_move_key_from_label(label)] = {
            "move_id": index,
            **_summarize_animation(label, body),
            "assets": _dedupe_assets(asset_records),
            "logic": logic,
        }
    return {"source": path.as_posix(), "count": len(moves), "moves": moves}


def _resolve_gen3_png(repo_root: Path, source_text: str) -> Path | None:
    source_path = repo_root / source_text
    if source_path.suffix == ".png":
        return source_path
    parent = source_path.parent
    stem = source_path.stem
    candidates = sorted(parent.glob(f"{stem}*.png"))
    return candidates[0] if candidates else None


def _collect_gen3_graphics_symbols(repo_root: Path) -> dict[str, Path]:
    path = repo_root / "src" / "graphics.c"
    symbols: dict[str, Path] = {}
    if not path.exists():
        return symbols
    pattern = re.compile(r'const\s+u32\s+(gBattleAnim(?:Sprite|Bg)Gfx_[A-Za-z0-9_]+)\[\]\s*=\s+INCGFX_U32\("([^"]+)"')
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(line)
        if not match:
            continue
        resolved = _resolve_gen3_png(repo_root, match.group(2))
        if resolved:
            symbols[match.group(1)] = resolved
    return symbols


def _collect_gen3_anim_tags(repo_root: Path) -> dict[str, dict[str, Any]]:
    table_path = repo_root / "src" / "data" / "battle_anim.h"
    symbols = _collect_gen3_graphics_symbols(repo_root)
    tags: dict[str, dict[str, Any]] = {}
    if not table_path.exists():
        return tags
    pattern = re.compile(r"\{(gBattleAnim[A-Za-z0-9_]+),\s*([^,]+),\s*(ANIM_TAG_[A-Z0-9_]+)\}")
    for line in table_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(line)
        if not match:
            continue
        source_path = symbols.get(match.group(1))
        if not source_path:
            continue
        record = _asset_record(
            3,
            repo_root,
            source_path,
            role="gen3_anim_sprite",
            tag=match.group(3),
            symbol=match.group(3),
            source_symbol=match.group(1),
            size=match.group(2),
        )
        if record:
            tags[match.group(3)] = record
    return tags


def _gen3_background_asset(repo_root: Path, bg_constant: str) -> dict[str, Any] | None:
    slug = bg_constant.removeprefix("BG_").lower()
    source_path = repo_root / "graphics" / "battle_anims" / "backgrounds" / f"{slug}.png"
    if not source_path.exists():
        return None
    return _asset_record(
        3,
        repo_root,
        source_path,
        role="gen3_anim_background",
        tag=bg_constant,
        symbol=bg_constant,
    )


def _gen3_logic_and_assets(body: str, tags: dict[str, dict[str, Any]], repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    loaded_tags: list[str] = []
    sprites: list[dict[str, Any]] = []
    visual_tasks: list[dict[str, Any]] = []
    backgrounds: list[str] = []
    delays: list[int] = []
    assets: list[dict[str, Any] | None] = []
    for step in _script_steps(body):
        command = step["command"]
        args = step["args"]
        if command == "loadspritegfx" and args:
            loaded_tags.append(args[0])
            assets.append(tags.get(args[0]))
        elif command in {"createsprite", "create_basic_hitsplat_sprite", "create_claw_slash_sprite"} and args:
            sprites.append({"template": args[0], "args": args[1:]})
        elif command == "createvisualtask" and args:
            visual_tasks.append({"task": args[0], "args": args[1:]})
        elif command == "fadetobg" and args:
            backgrounds.append(args[0])
            assets.append(_gen3_background_asset(repo_root, args[0]))
        elif command == "create_surf_wave":
            backgrounds.append("BG_WATER")
            assets.append(_gen3_background_asset(repo_root, "BG_WATER"))
        elif command == "delay" and args:
            try:
                delays.append(int(args[0], 0))
            except ValueError:
                pass
    return (
        {
            "loaded_tags": loaded_tags,
            "sprites": sprites,
            "visual_tasks": visual_tasks,
            "backgrounds": backgrounds,
            "delay_frames": delays,
            "total_delay_frames": sum(delays),
        },
        _dedupe_assets(assets),
    )


def _collect_gen3_animation_map(reference_root: Path) -> dict[str, Any]:
    path = reference_root / "pokeemerald" / "data" / "battle_anim_scripts.s"
    if not path.exists():
        return {"source": path.as_posix(), "count": 0, "moves": {}}
    repo_root = reference_root / "pokeemerald"
    tags = _collect_gen3_anim_tags(repo_root)
    labels = _pointer_labels(path, "gBattleAnims_Moves::", ".4byte", (".align", "gBattleAnims_StatusConditions::"))
    blocks = _label_blocks(path)
    moves = {}
    for index, label in enumerate(labels):
        if label == "Move_NONE":
            continue
        body = blocks.get(label, "")
        logic, assets = _gen3_logic_and_assets(body, tags, repo_root)
        moves[_move_key_from_label(label)] = {
            "move_id": index,
            **_summarize_animation(label, body),
            "assets": assets,
            "logic": logic,
        }
    return {"source": path.as_posix(), "count": len(moves), "moves": moves}


def _collect_animation_map(reference_root: Path) -> dict[str, Any]:
    return {
        "schema": 1,
        "note": "Intermediate browser animation catalog generated from pret battle animation pointer tables.",
        "generations": {
            "1": _collect_gen1_animation_map(reference_root),
            "2": _collect_gen2_animation_map(reference_root),
            "3": _collect_gen3_animation_map(reference_root),
        },
    }


def export_assets(
    reference_root: Path = DEFAULT_REFERENCE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    include_move_anims: bool = True,
    clean: bool = False,
) -> Path:
    sources = _source_config(reference_root)
    _assert_sources_exist(sources)

    if clean and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "schema": 1,
        "note": "Generated from local pret repositories. Do not commit generated assets unless licensing is reviewed.",
        "generations": {},
    }

    for source in sources:
        manifest["generations"][str(source.generation)] = {
            "repo": source.repo_name,
            "pokemon": _collect_pokemon_sprites(source, output_root),
            "battle_assets": _collect_battle_assets(source, output_root, include_move_anims=include_move_anims),
            "behavior_sources": _collect_behavior_index(source),
        }

    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    animation_map_path = output_root / "animation-map.json"
    animation_map_path.write_text(json.dumps(_collect_animation_map(reference_root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export local pret battle sprites and behavior source manifest.")
    parser.add_argument("--reference-root", type=Path, default=DEFAULT_REFERENCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--include-move-anims",
        action="store_true",
        help="Copy raw move animation PNG sheets. Kept for compatibility; this is now the default.",
    )
    parser.add_argument(
        "--skip-move-anims",
        action="store_true",
        help="Skip raw move animation PNG sheets and only export battle UI/pokemon sprites.",
    )
    parser.add_argument("--clean", action="store_true", help="Remove the output directory before exporting.")
    args = parser.parse_args()
    manifest_path = export_assets(
        args.reference_root,
        args.output_root,
        include_move_anims=args.include_move_anims or not args.skip_move_anims,
        clean=args.clean,
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
