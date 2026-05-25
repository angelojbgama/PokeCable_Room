#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent / "Pokecable_tool"
DEST_ROOT = ROOT / "assets" / "item_sprites"
ITEMS_DIR = DEST_ROOT / "items"
MANIFEST = DEST_ROOT / "manifest.json"
OVERVIEW_URL = "https://msikma.github.io/pokesprite/overview/inventory.html"
RAW_PREFIX = "https://raw.githubusercontent.com/msikma/pokesprite/master/items/"


def _slug(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("'", "").replace(".", "").replace(":", "").replace(",", "")
    value = value.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def _aliases_for(group: str, stem: str) -> list[str]:
    aliases = {_slug(stem)}
    if group == "berry":
        aliases.add(_slug(f"{stem}-berry"))
    elif group == "ball":
        aliases.add(_slug(f"{stem}-ball"))
    elif group == "flute":
        aliases.add(_slug(f"{stem}-flute"))
    return sorted(alias for alias in aliases if alias)


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "PokeCable item asset downloader"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def _asset_urls(html: str) -> list[str]:
    urls = re.findall(r"https://raw\.githubusercontent\.com/msikma/pokesprite/master/items/[^\"'\s<>]+?\.png", html)
    return sorted(set(urls))


def main() -> int:
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    html = _download(OVERVIEW_URL).decode("utf-8", errors="replace")
    urls = _asset_urls(html)
    if not urls:
        print("No item sprite URLs found.", file=sys.stderr)
        return 1

    assets: dict[str, dict[str, object]] = {}
    aliases: dict[str, list[str]] = {}
    for index, url in enumerate(urls, start=1):
        rel = url.removeprefix(RAW_PREFIX)
        if rel.startswith("../") or not rel.endswith(".png"):
            continue
        target = ITEMS_DIR / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(_download(url))
        group = rel.split("/", 1)[0]
        stem = Path(rel).stem
        entry_aliases = _aliases_for(group, stem)
        assets[rel] = {
            "group": group,
            "slug": _slug(stem),
            "aliases": entry_aliases,
            "source_url": url,
        }
        for alias in entry_aliases:
            aliases.setdefault(alias, [])
            if rel not in aliases[alias]:
                aliases[alias].append(rel)
        if index % 100 == 0:
            print(f"Downloaded/indexed {index}/{len(urls)}")

    manifest = {
        "source": OVERVIEW_URL,
        "raw_prefix": RAW_PREFIX,
        "style": "items",
        "asset_count": len(assets),
        "assets": assets,
        "aliases": aliases,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {MANIFEST} with {len(assets)} item sprites.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
