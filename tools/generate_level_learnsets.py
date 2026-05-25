#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat


REPO_ROOT = Path(__file__).resolve().parent.parent / "Pokecable_tool"
DATA_DIR = REPO_ROOT / "pokecable_runtime" / "data"
CACHE_DIR = REPO_ROOT / ".cache" / "pokeapi"
POKEAPI = "https://pokeapi.co/api/v2"
NATIONAL_DEX_LIMIT = 386
TARGET_VERSION_GROUPS = {
    "red-blue",
    "yellow",
    "gold-silver",
    "crystal",
    "ruby-sapphire",
    "emerald",
    "firered-leafgreen",
}
VERSION_GROUP_BY_GAME = {
    "pokemon_red": "red-blue",
    "pokemon_blue": "red-blue",
    "pokemon_yellow": "yellow",
    "pokemon_gold": "gold-silver",
    "pokemon_silver": "gold-silver",
    "pokemon_crystal": "crystal",
    "pokemon_ruby": "ruby-sapphire",
    "pokemon_sapphire": "ruby-sapphire",
    "pokemon_emerald": "emerald",
    "pokemon_firered": "firered-leafgreen",
    "pokemon_leafgreen": "firered-leafgreen",
}
VERSION_GROUPS_BY_GENERATION = {
    1: {"red-blue", "yellow"},
    2: {"gold-silver", "crystal"},
    3: {"ruby-sapphire", "emerald", "firered-leafgreen"},
}


def _cache_name(url: str) -> Path:
    key = re.sub(r"[^A-Za-z0-9_.-]+", "_", url.replace(POKEAPI, "").strip("/"))
    return CACHE_DIR / f"{key or 'root'}.json"


def fetch_json(url: str) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_name(url)
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": "PokeCable learnset generator"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            cache_path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            return data
        except Exception:
            if attempt == 3:
                raise
            time.sleep(0.75 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}")


def _id_from_url(url: str) -> int:
    return int(str(url).rstrip("/").rsplit("/", 1)[-1])


def _display_move_name(name: str, move_id: int) -> str:
    value = str(name or "").strip()
    if not value:
        return f"Move #{move_id}"
    return " ".join(part.capitalize() for part in value.replace("-", " ").split())


def fetch_pokemon_learnset(national_id: int) -> dict[tuple[str, int], dict[int, dict[str, object]]]:
    payload = fetch_json(f"{POKEAPI}/pokemon/{national_id}/")
    by_key: dict[tuple[str, int], dict[int, dict[str, object]]] = {}
    for move in payload.get("moves") or []:
        move_obj = move.get("move") or {}
        move_id = _id_from_url(move_obj.get("url") or "")
        move_name = _display_move_name(move_obj.get("name") or "", move_id)
        for detail in move.get("version_group_details") or []:
            method = (detail.get("move_learn_method") or {}).get("name")
            version_group = (detail.get("version_group") or {}).get("name")
            if method != "level-up" or version_group not in TARGET_VERSION_GROUPS:
                continue
            learned_at = max(1, int(detail.get("level_learned_at") or 0))
            bucket = by_key.setdefault((version_group, national_id), {})
            existing = bucket.get(move_id)
            if existing is None or learned_at < int(existing["learn_level"]):
                bucket[move_id] = {
                    "move_id": move_id,
                    "name": move_name,
                    "learn_level": learned_at,
                    "method": "level-up",
                }
    return by_key


def build_level_up_learnsets() -> dict[tuple[str, int], tuple[dict[str, object], ...]]:
    merged: dict[tuple[str, int], dict[int, dict[str, object]]] = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_pokemon_learnset, national_id): national_id for national_id in range(1, NATIONAL_DEX_LIMIT + 1)}
        for future in as_completed(futures):
            national_id = futures[future]
            for key, moves in future.result().items():
                merged.setdefault(key, {}).update(moves)
            if national_id % 25 == 0:
                print(f"pokemon {national_id}/{NATIONAL_DEX_LIMIT}", file=sys.stderr)
    result: dict[tuple[str, int], tuple[dict[str, object], ...]] = {}
    for key, moves in sorted(merged.items()):
        result[key] = tuple(
            sorted(
                moves.values(),
                key=lambda entry: (int(entry["learn_level"]), str(entry["name"]), int(entry["move_id"])),
            )
        )
    return result


def fetch_hm_moves() -> dict[str, tuple[int, ...]]:
    index = fetch_json(f"{POKEAPI}/machine/?limit=10000")
    urls = [entry.get("url") for entry in index.get("results") or [] if entry.get("url")]
    by_group: dict[str, set[int]] = {group: set() for group in TARGET_VERSION_GROUPS}
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(fetch_json, url): url for url in urls}
        for future in as_completed(futures):
            payload = future.result()
            version_group = (payload.get("version_group") or {}).get("name")
            if version_group not in TARGET_VERSION_GROUPS:
                continue
            item_name = str((payload.get("item") or {}).get("name") or "")
            if not item_name.startswith("hm"):
                continue
            move_url = (payload.get("move") or {}).get("url") or ""
            if move_url:
                by_group[version_group].add(_id_from_url(move_url))
    return {group: tuple(sorted(move_ids)) for group, move_ids in sorted(by_group.items())}


def write_generation_modules(
    level_up: dict[tuple[str, int], tuple[dict[str, object], ...]],
    hm_moves: dict[str, tuple[int, ...]],
) -> None:
    for generation, version_groups in sorted(VERSION_GROUPS_BY_GENERATION.items()):
        version_group_by_game = {
            game: version_group
            for game, version_group in VERSION_GROUP_BY_GAME.items()
            if version_group in version_groups
        }
        level_up_by_generation = {
            key: value
            for key, value in level_up.items()
            if key[0] in version_groups
        }
        hm_moves_by_generation = {
            version_group: move_ids
            for version_group, move_ids in hm_moves.items()
            if version_group in version_groups
        }
        body = [
            "from __future__ import annotations",
            "",
            "# Generated by tools/generate_level_learnsets.py from PokeAPI.",
            "# Source endpoints: /pokemon/{id}/ and /machine/?limit=10000.",
            "",
            f"VERSION_GROUP_BY_GAME = {pformat(version_group_by_game, sort_dicts=True, width=120)}",
            "",
            f"LEVEL_UP_LEARNSETS = {pformat(level_up_by_generation, sort_dicts=True, width=140)}",
            "",
            f"HM_MOVES_BY_VERSION_GROUP = {pformat(hm_moves_by_generation, sort_dicts=True, width=120)}",
            "",
        ]
        out_path = DATA_DIR / f"learnsets_gen{generation}.py"
        out_path.write_text("\n".join(body), encoding="utf-8")
        print(f"wrote {out_path.relative_to(REPO_ROOT)} with {len(level_up_by_generation)} learnset keys")


def main() -> int:
    level_up = build_level_up_learnsets()
    hm_moves = fetch_hm_moves()
    write_generation_modules(level_up, hm_moves)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
