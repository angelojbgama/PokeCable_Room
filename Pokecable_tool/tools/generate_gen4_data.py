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
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "pokecable_runtime" / "data"
CACHE_DIR = REPO_ROOT / ".cache" / "pokeapi"
POKEAPI = "https://pokeapi.co/api/v2"

GEN4_SPECIES_RANGE = range(387, 494)
GEN4_MOVE_RANGE = range(1, 468)
GEN4_LEARNSET_RANGE = range(1, 494)
GEN4_VERSION_GROUPS = {"diamond-pearl", "platinum", "heartgold-soulsilver"}
GEN4_VERSION_GROUP_BY_GAME = {
    "pokemon_diamond": "diamond-pearl",
    "pokemon_pearl": "diamond-pearl",
    "pokemon_platinum": "platinum",
    "pokemon_heartgold": "heartgold-soulsilver",
    "pokemon_soulsilver": "heartgold-soulsilver",
}

GROWTH_RATE_IDS = {
    "slow": 1,
    "medium": 2,
    "medium-fast": 2,
    "fast": 3,
    "medium-slow": 4,
    "erratic": 5,
    "slow-then-very-fast": 5,
    "fluctuating": 6,
    "fast-then-very-slow": 6,
}

VERSION_GROUP_ORDER = {
    "red-blue": 1,
    "yellow": 2,
    "gold-silver": 3,
    "crystal": 4,
    "ruby-sapphire": 5,
    "emerald": 6,
    "firered-leafgreen": 7,
    "diamond-pearl": 8,
    "platinum": 9,
    "heartgold-soulsilver": 10,
    "black-white": 11,
    "colosseum": 12,
    "xd": 13,
    "black-2-white-2": 14,
    "x-y": 15,
    "omega-ruby-alpha-sapphire": 16,
    "sun-moon": 17,
    "ultra-sun-ultra-moon": 18,
    "lets-go-pikachu-lets-go-eevee": 19,
    "sword-shield": 20,
    "brilliant-diamond-and-shining-pearl": 21,
    "legends-arceus": 22,
    "scarlet-violet": 23,
}
GEN4_LAST_VERSION_GROUP_ORDER = VERSION_GROUP_ORDER["heartgold-soulsilver"]

ITEM_CATEGORY_MAP = {
    "all-mail": "mail",
    "all-machines": "tmhm",
    "apricorn-balls": "ball",
    "bad-held-items": "held_item",
    "baking-only": "item",
    "catching-bonus": "held_item",
    "choice": "held_item",
    "collectibles": "collectible",
    "dex-completion": "key_item",
    "dynamax-crystals": "key_item",
    "effort-drop": "medicine",
    "effort-training": "held_item",
    "event-items": "key_item",
    "evolution": "evolution_item",
    "gameplay": "key_item",
    "healing": "medicine",
    "held-items": "held_item",
    "in-a-pinch": "berry",
    "jewels": "held_item",
    "loot": "valuable",
    "medicine": "medicine",
    "mega-stones": "held_item",
    "memories": "held_item",
    "miracle-shooter": "battle_item",
    "mulch": "item",
    "other": "item",
    "other-bags": "key_item",
    "picky-healing": "berry",
    "plates": "held_item",
    "plot-advancement": "key_item",
    "pp-recovery": "medicine",
    "scarves": "held_item",
    "species-candies": "item",
    "species-specific": "held_item",
    "spelunking": "key_item",
    "standard-balls": "ball",
    "stat-boosts": "medicine",
    "status-cures": "medicine",
    "training": "held_item",
    "type-enhancement": "held_item",
    "unused": "unused",
    "vitamins": "medicine",
    "z-crystals": "held_item",
}


def _cache_name(url: str) -> Path:
    key = re.sub(r"[^A-Za-z0-9_.-]+", "_", url.replace(POKEAPI, "").strip("/"))
    return CACHE_DIR / f"{key or 'root'}.json"


def fetch_json(url: str) -> dict[str, Any]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_name(url)
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    request = urllib.request.Request(url, headers={"User-Agent": "PokeCable Gen4 data generator"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
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


def _display_name(raw: str | None, fallback_id: int, *, fallback_prefix: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return f"{fallback_prefix} #{fallback_id}"
    return " ".join(part.capitalize() for part in value.replace("-", " ").split())


def _english_name(payload: dict[str, Any], fallback_id: int, *, fallback_prefix: str) -> str:
    english_name = next(
        (
            str(entry.get("name") or "")
            for entry in payload.get("names") or []
            if (entry.get("language") or {}).get("name") == "en"
        ),
        "",
    )
    return english_name or _display_name(payload.get("name"), fallback_id, fallback_prefix=fallback_prefix)


def fetch_species_static(national_id: int) -> tuple[int, str, dict[str, Any], int, int | None]:
    pokemon = fetch_json(f"{POKEAPI}/pokemon/{national_id}/")
    species = fetch_json(f"{POKEAPI}/pokemon-species/{national_id}/")
    english_name = next(
        (
            str(entry.get("name") or "")
            for entry in species.get("names") or []
            if (entry.get("language") or {}).get("name") == "en"
        ),
        "",
    )
    name = english_name or _display_name(pokemon.get("name"), national_id, fallback_prefix="Species")
    stats_by_name = {entry["stat"]["name"]: int(entry["base_stat"]) for entry in pokemon.get("stats") or []}
    base_stats = {
        "stats": {
            "hp": stats_by_name.get("hp", 1),
            "atk": stats_by_name.get("attack", 1),
            "def": stats_by_name.get("defense", 1),
            "spa": stats_by_name.get("special-attack", 1),
            "spd": stats_by_name.get("special-defense", 1),
            "spe": stats_by_name.get("speed", 1),
        },
        "types": [str((entry.get("type") or {}).get("name") or "") for entry in pokemon.get("types") or []],
    }
    growth_name = str(((species.get("growth_rate") or {}).get("name")) or "")
    growth_rate_id = GROWTH_RATE_IDS[growth_name]
    gender_rate = species.get("gender_rate")
    return national_id, name, base_stats, growth_rate_id, int(gender_rate) if gender_rate is not None else None


def build_gen4_static() -> tuple[dict[int, str], dict[int, dict[str, Any]], dict[int, int], dict[int, int | None]]:
    species_names: dict[int, str] = {}
    base_stats: dict[int, dict[str, Any]] = {}
    growth_rates: dict[int, int] = {}
    gender_rates: dict[int, int | None] = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_species_static, national_id): national_id for national_id in GEN4_SPECIES_RANGE}
        for future in as_completed(futures):
            national_id, name, stats, growth_rate_id, gender_rate = future.result()
            species_names[national_id] = name
            base_stats[national_id] = stats
            growth_rates[national_id] = growth_rate_id
            gender_rates[national_id] = gender_rate
            if national_id % 25 == 0:
                print(f"species {national_id}/493", file=sys.stderr)
    return species_names, base_stats, growth_rates, gender_rates


def fetch_move_static(move_id: int) -> tuple[int, dict[str, Any]]:
    payload = fetch_json(f"{POKEAPI}/move/{move_id}/")
    pp = payload.get("pp")
    post_gen4_past_values = []
    for entry in payload.get("past_values") or []:
        past_pp = entry.get("pp")
        version_group_name = str(((entry.get("version_group") or {}).get("name")) or "")
        version_order = VERSION_GROUP_ORDER.get(version_group_name, 999)
        if past_pp is not None and version_order > GEN4_LAST_VERSION_GROUP_ORDER:
            post_gen4_past_values.append((version_order, int(past_pp)))
    if post_gen4_past_values:
        pp = sorted(post_gen4_past_values, key=lambda item: item[0])[0][1]
    return move_id, {
        "name": _english_name(payload, move_id, fallback_prefix="Move"),
        "pp": int(pp or 1),
    }


def build_move_static() -> dict[int, dict[str, Any]]:
    moves: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_move_static, move_id): move_id for move_id in GEN4_MOVE_RANGE}
        for future in as_completed(futures):
            move_id, data = future.result()
            moves[move_id] = data
    return moves


def _gen4_game_index(payload: dict[str, Any]) -> int | None:
    for entry in payload.get("game_indices") or []:
        generation_name = str(((entry.get("generation") or {}).get("name")) or "")
        if generation_name == "generation-iv":
            try:
                return int(entry.get("game_index"))
            except (TypeError, ValueError):
                return None
    return None


def fetch_item_static(url: str) -> tuple[int, dict[str, Any]] | None:
    payload = fetch_json(url)
    game_index = _gen4_game_index(payload)
    if game_index is None or game_index <= 0:
        return None
    category_name = str(((payload.get("category") or {}).get("name")) or "")
    category = ITEM_CATEGORY_MAP.get(category_name, "item")
    name = _english_name(payload, game_index, fallback_prefix="Item")
    return game_index, {
        "name": name,
        "category": category,
        "pokeapi_id": int(payload.get("id") or 0),
        "pokeapi_name": str(payload.get("name") or ""),
        "pokeapi_category": category_name,
    }


def build_item_static() -> dict[int, dict[str, Any]]:
    index = fetch_json(f"{POKEAPI}/item/?limit=10000")
    urls = [str(entry.get("url") or "") for entry in index.get("results") or [] if entry.get("url")]
    items: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(fetch_item_static, url): url for url in urls}
        for count, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            if result is not None:
                item_id, data = result
                existing = items.get(item_id)
                if existing is None or int(data.get("pokeapi_id") or 0) < int(existing.get("pokeapi_id") or 999999):
                    items[item_id] = data
            if count % 250 == 0:
                print(f"items {count}/{len(urls)}", file=sys.stderr)
    return items


def fetch_pokemon_learnset(national_id: int) -> dict[tuple[str, int], dict[int, dict[str, Any]]]:
    payload = fetch_json(f"{POKEAPI}/pokemon/{national_id}/")
    by_key: dict[tuple[str, int], dict[int, dict[str, Any]]] = {}
    for move in payload.get("moves") or []:
        move_obj = move.get("move") or {}
        move_id = _id_from_url(move_obj.get("url") or "")
        move_name = _display_name(move_obj.get("name"), move_id, fallback_prefix="Move")
        for detail in move.get("version_group_details") or []:
            method = (detail.get("move_learn_method") or {}).get("name")
            version_group = (detail.get("version_group") or {}).get("name")
            if method != "level-up" or version_group not in GEN4_VERSION_GROUPS:
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


def build_level_up_learnsets() -> dict[tuple[str, int], tuple[dict[str, Any], ...]]:
    merged: dict[tuple[str, int], dict[int, dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_pokemon_learnset, national_id): national_id for national_id in GEN4_LEARNSET_RANGE}
        for future in as_completed(futures):
            national_id = futures[future]
            for key, moves in future.result().items():
                merged.setdefault(key, {}).update(moves)
            if national_id % 25 == 0:
                print(f"learnsets {national_id}/493", file=sys.stderr)
    return {
        key: tuple(sorted(moves.values(), key=lambda entry: (int(entry["learn_level"]), str(entry["name"]), int(entry["move_id"]))))
        for key, moves in sorted(merged.items())
    }


def fetch_hm_moves() -> dict[str, tuple[int, ...]]:
    index = fetch_json(f"{POKEAPI}/machine/?limit=10000")
    urls = [entry.get("url") for entry in index.get("results") or [] if entry.get("url")]
    by_group: dict[str, set[int]] = {group: set() for group in GEN4_VERSION_GROUPS}
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(fetch_json, url): url for url in urls}
        for future in as_completed(futures):
            payload = future.result()
            version_group = (payload.get("version_group") or {}).get("name")
            if version_group not in GEN4_VERSION_GROUPS:
                continue
            item_name = str((payload.get("item") or {}).get("name") or "")
            if not item_name.startswith("hm"):
                continue
            move_url = (payload.get("move") or {}).get("url") or ""
            if move_url:
                by_group[version_group].add(_id_from_url(move_url))
    return {group: tuple(sorted(move_ids)) for group, move_ids in sorted(by_group.items())}


def write_static_module(
    species_names: dict[int, str],
    move_data: dict[int, dict[str, Any]],
    item_data: dict[int, dict[str, Any]],
    base_stats: dict[int, dict[str, Any]],
    growth_rates: dict[int, int],
    gender_rates: dict[int, int | None],
) -> None:
    body = [
        "from __future__ import annotations",
        "",
        "# Generated by tools/generate_gen4_data.py from PokeAPI.",
        "",
        f"GEN4_SPECIES_NAMES = {pformat(dict(sorted(species_names.items())), sort_dicts=True, width=120)}",
        "",
        f"GEN4_MOVE_DATA = {pformat(dict(sorted(move_data.items())), sort_dicts=True, width=120)}",
        "",
        f"GEN4_ITEM_DATA = {pformat(dict(sorted(item_data.items())), sort_dicts=True, width=140)}",
        "",
        f"GEN4_BASE_STATS = {pformat(dict(sorted(base_stats.items())), sort_dicts=True, width=140)}",
        "",
        f"GEN4_GROWTH_RATE_IDS_BY_NATIONAL = {pformat(dict(sorted(growth_rates.items())), sort_dicts=True, width=120)}",
        "",
        f"GEN4_GENDER_RATES_BY_NATIONAL = {pformat(dict(sorted(gender_rates.items())), sort_dicts=True, width=120)}",
        "",
    ]
    path = DATA_DIR / "gen4_static.py"
    path.write_text("\n".join(body), encoding="utf-8")
    print(f"wrote {path.relative_to(REPO_ROOT)}")


def write_learnsets_module(
    level_up: dict[tuple[str, int], tuple[dict[str, Any], ...]],
    hm_moves: dict[str, tuple[int, ...]],
) -> None:
    body = [
        "from __future__ import annotations",
        "",
        "# Generated by tools/generate_gen4_data.py from PokeAPI.",
        "# Source endpoints: /pokemon/{id}/ and /machine/?limit=10000.",
        "",
        f"VERSION_GROUP_BY_GAME = {pformat(GEN4_VERSION_GROUP_BY_GAME, sort_dicts=True, width=120)}",
        "",
        f"LEVEL_UP_LEARNSETS = {pformat(level_up, sort_dicts=True, width=140)}",
        "",
        f"HM_MOVES_BY_VERSION_GROUP = {pformat(hm_moves, sort_dicts=True, width=120)}",
        "",
    ]
    path = DATA_DIR / "learnsets_gen4.py"
    path.write_text("\n".join(body), encoding="utf-8")
    print(f"wrote {path.relative_to(REPO_ROOT)} with {len(level_up)} learnset keys")


def main() -> int:
    species_names, base_stats, growth_rates, gender_rates = build_gen4_static()
    move_data = build_move_static()
    item_data = build_item_static()
    level_up = build_level_up_learnsets()
    hm_moves = fetch_hm_moves()
    write_static_module(species_names, move_data, item_data, base_stats, growth_rates, gender_rates)
    write_learnsets_module(level_up, hm_moves)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
