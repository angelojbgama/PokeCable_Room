#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEST_ROOT = ROOT / "assets" / "pokemon_sprites"
MANIFEST = DEST_ROOT / "manifest.json"
RAW_PREFIX = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
NATIONAL_DEX_MAX = 493
VARIANTS = {
    "normal": "",
    "shiny": "shiny",
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _read_manifest() -> dict[str, object]:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _is_valid_png(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > len(PNG_SIGNATURE) and path.read_bytes().startswith(PNG_SIGNATURE)
    except OSError:
        return False


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "PokeCable pokemon sprite downloader"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _sprite_url(variant: str, national_id: int) -> str:
    prefix = VARIANTS[variant]
    if prefix:
        return f"{RAW_PREFIX}/{prefix}/{national_id}.png"
    return f"{RAW_PREFIX}/{national_id}.png"


def _ensure_sprite(variant: str, national_id: int) -> tuple[bool, str]:
    target = DEST_ROOT / variant / f"{national_id}.png"
    if _is_valid_png(target):
        return True, ""

    target.parent.mkdir(parents=True, exist_ok=True)
    url = _sprite_url(variant, national_id)
    try:
        payload = _download(url)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        return False, str(exc)

    if not payload.startswith(PNG_SIGNATURE):
        return False, "downloaded payload is not a PNG"

    target.write_bytes(payload)
    return True, ""


def _valid_downloaded_paths() -> list[str]:
    paths: list[str] = []
    for variant in sorted(VARIANTS):
        variant_root = DEST_ROOT / variant
        if not variant_root.exists():
            continue
        for path in sorted(variant_root.glob("*.png")):
            if _is_valid_png(path):
                paths.append(f"{variant}/{path.name}")
    return paths


def main() -> int:
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    previous_manifest = _read_manifest()
    forms = previous_manifest.get("forms") if isinstance(previous_manifest.get("forms"), dict) else {}

    missing: list[dict[str, object]] = []
    total = len(VARIANTS) * NATIONAL_DEX_MAX
    processed = 0
    for variant in sorted(VARIANTS):
        for national_id in range(1, NATIONAL_DEX_MAX + 1):
            processed += 1
            ok, error = _ensure_sprite(variant, national_id)
            if not ok:
                missing.append(
                    {
                        "variant": variant,
                        "national_dex_id": national_id,
                        "path": f"{variant}/{national_id}.png",
                        "source_url": _sprite_url(variant, national_id),
                        "error": error,
                    }
                )
            if processed % 100 == 0:
                print(f"Checked/downloaded {processed}/{total}")

    manifest = {
        "source": RAW_PREFIX,
        "national_dex_max": NATIONAL_DEX_MAX,
        "variants": sorted(VARIANTS),
        "forms": forms,
        "downloaded": _valid_downloaded_paths(),
        "missing": missing,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    if missing:
        print(f"Wrote {MANIFEST} with {len(missing)} missing sprites.", file=sys.stderr)
        return 1
    print(f"Wrote {MANIFEST} with {len(manifest['downloaded'])} valid sprites.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
