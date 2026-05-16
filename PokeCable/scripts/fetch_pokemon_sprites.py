#!/usr/bin/env python3
"""Fetch local pixel Pokemon sprites used by the web UI and R36S tool."""
from __future__ import annotations

import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "PokeCable" / "frontend" / "sprites" / "pokemon"
TOOL_DIR = ROOT / "Pokecable_tool" / "assets" / "pokemon_sprites"
BASE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
NATIONAL_DEX_MAX = 386
UNOWN_FORMS = [chr(code) for code in range(ord("a"), ord("z") + 1)] + ["exclamation", "question"]
EXTRA_FORMS = {
    201: UNOWN_FORMS[1:],
}


def expected_sprite_names() -> list[str]:
    names = [f"{dex}.png" for dex in range(1, NATIONAL_DEX_MAX + 1)]
    for dex, forms in EXTRA_FORMS.items():
        names.extend(f"{dex}-{form}.png" for form in forms)
    return names


def download_png(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "PokeCable/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"not a png: {url}")
    return data


def write_manifest(target: Path, downloaded: list[str], missing: list[str]) -> None:
    manifest = {
        "source": BASE_URL,
        "national_dex_max": NATIONAL_DEX_MAX,
        "variants": ["normal", "shiny"],
        "forms": EXTRA_FORMS,
        "downloaded": sorted(downloaded),
        "missing": sorted(missing),
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_to_frontend() -> tuple[list[str], list[str]]:
    downloaded: list[str] = []
    missing: list[str] = []
    for variant in ("normal", "shiny"):
        variant_dir = FRONTEND_DIR / variant
        variant_dir.mkdir(parents=True, exist_ok=True)
        prefix = "shiny/" if variant == "shiny" else ""
        for name in expected_sprite_names():
            target = variant_dir / name
            if target.exists():
                downloaded.append(f"{variant}/{name}")
                continue
            url = f"{BASE_URL}/{prefix}{name}"
            try:
                target.write_bytes(download_png(url))
                downloaded.append(f"{variant}/{name}")
                print(f"ok {variant}/{name}")
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
                missing.append(f"{variant}/{name}")
                print(f"missing {variant}/{name}: {exc}", file=sys.stderr)
    write_manifest(FRONTEND_DIR, downloaded, missing)
    return downloaded, missing


def sync_tool_copy() -> None:
    if TOOL_DIR.exists():
        shutil.rmtree(TOOL_DIR)
    shutil.copytree(FRONTEND_DIR, TOOL_DIR)


def main() -> int:
    _downloaded, missing = fetch_to_frontend()
    sync_tool_copy()
    if missing:
        print(f"{len(missing)} sprites missing; see manifest.json", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
