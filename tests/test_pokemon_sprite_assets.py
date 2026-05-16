from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SPRITES = ROOT / "PokeCable" / "frontend" / "sprites" / "pokemon"
TOOL_SPRITES = ROOT / "Pokecable_tool" / "assets" / "pokemon_sprites"


def test_local_pokemon_sprite_packs_cover_core_and_forms() -> None:
    expected = [
        "normal/1.png",
        "normal/25.png",
        "normal/386.png",
        "normal/201-question.png",
        "shiny/25.png",
        "shiny/201-exclamation.png",
    ]

    for relative in expected:
        assert (FRONTEND_SPRITES / relative).exists()
        assert (TOOL_SPRITES / relative).exists()


def test_pokemon_sprite_rendering_has_no_remote_or_svg_fallbacks() -> None:
    files = [
        ROOT / "Pokecable_tool" / "r36s_pokecable_ui.py",
        ROOT / "PokeCable" / "frontend" / "app.js",
        ROOT / "PokeCable" / "frontend" / "trade-preview.js",
    ]
    forbidden = [
        "raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon",
        "pokemondb",
        "sprites/home",
        "pokemon-fallback.svg",
    ]

    for path in files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text
