from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent / "Pokecable_tool"
SPRITE_ROOT = ROOT / "assets" / "pokemon_sprites"
MANIFEST = SPRITE_ROOT / "manifest.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _is_valid_png(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > len(PNG_SIGNATURE) and path.read_bytes().startswith(PNG_SIGNATURE)


def test_pokemon_sprites_cover_national_dex_through_gen4():
    missing: list[str] = []
    for variant in ("normal", "shiny"):
        for national_id in range(1, 494):
            path = SPRITE_ROOT / variant / f"{national_id}.png"
            if not _is_valid_png(path):
                missing.append(f"{variant}/{national_id}.png")

    assert missing == []


def test_pokemon_sprite_manifest_tracks_gen4_coverage():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["national_dex_max"] == 493
    assert manifest["variants"] == ["normal", "shiny"]
    assert manifest["missing"] == []

    downloaded = set(manifest["downloaded"])
    for variant in ("normal", "shiny"):
        for national_id in range(1, 494):
            assert f"{variant}/{national_id}.png" in downloaded

    forms = manifest.get("forms")
    assert isinstance(forms, dict)
    assert "201" in forms
