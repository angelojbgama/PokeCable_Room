from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _path in (str(REPO_ROOT), str(RUNTIME)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from frontend.sprites import SpriteLoader, pokemon_sprite_variant  # noqa: E402
from pokecable_save import load_save  # noqa: E402


TEST_SAVES = REPO_ROOT.parent / "roms" / "test-saves"


def _sprite_filename(pokemon: dict[str, object]) -> str:
    loader = SpriteLoader("")
    _, lookup = loader._identity(pokemon)
    path = loader._sprite_path(lookup)
    return path.name if path is not None else ""


def test_unown_sprite_identity_uses_letter_and_punctuation_forms():
    assert pokemon_sprite_variant({"national_dex_id": 201, "species_name": "Unown", "unown_form": "A"}) == ("normal", "")
    assert _sprite_filename({"generation": 3, "species_id": 201, "national_dex_id": 201, "species_name": "Unown", "unown_form": "B"}) == "201-b.png"
    assert _sprite_filename({"generation": 3, "species_id": 201, "national_dex_id": 201, "species_name": "Unown", "metadata": {"unown_form": "?"}}) == "201-question.png"
    assert _sprite_filename({"generation": 4, "species_id": 201, "national_dex_id": 201, "species_name": "Unown", "canonical": {"metadata": {"form": 21}}}) == "201-v.png"


@pytest.mark.skipif(not (TEST_SAVES / "gen 2" / "Pokémon - Crystal Version.sav").exists(), reason="save de Crystal nao disponivel")
def test_save_model_exposes_gen2_unown_form_for_sprite_loader():
    save = load_save(TEST_SAVES / "gen 2" / "Pokémon - Crystal Version.sav")
    unown = next(pokemon for pokemon in save.boxes + save.party if int(pokemon.get("species_id") or 0) == 201)

    assert unown.get("unown_form") in tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


@pytest.mark.skipif(not (TEST_SAVES / "gen 3" / "Pokémon - FireRed Version.sav").exists(), reason="save de FireRed nao disponivel")
def test_save_model_exposes_gen3_unown_form_for_sprite_loader():
    save = load_save(TEST_SAVES / "gen 3" / "Pokémon - FireRed Version.sav")
    unown = next(pokemon for pokemon in save.boxes + save.party if int(pokemon.get("species_id") or 0) == 201)

    assert unown.get("unown_form") in tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ("!", "?")


@pytest.mark.skipif(not (TEST_SAVES / "gen 4" / "POKEMON_D_SAVE.sav").exists(), reason="save de Diamond Gen4 nao disponivel")
def test_save_model_exposes_gen4_unown_form_at_top_level():
    save = load_save(TEST_SAVES / "gen 4" / "POKEMON_D_SAVE.sav")
    unown_b = next(pokemon for pokemon in save.boxes + save.party if pokemon.get("location") == "box:14:1")

    assert unown_b.get("unown_form") == "B"
    assert _sprite_filename(unown_b) == "201-b.png"
