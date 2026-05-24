from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pokecable_runtime"))

from frontend.app import enrich_pokemon_experience_for_display, move_display_entries, pokemon_xp_bar  # noqa: E402
from frontend.screens.trade import _apply_moves_display  # noqa: E402
from pokecable_save import SaveError, SaveModel  # noqa: E402
from r36s_pokecable_core import PokecableState  # noqa: E402


def test_move_display_entries_reads_summary_moves_without_top_level_moves():
    pokemon = {
        "generation": 4,
        "summary": {
            "moves": [33, 44],
            "move_names": ["Tackle", "Bite"],
        },
    }

    entries = move_display_entries(pokemon)

    assert [entry["move_id"] for entry in entries] == [33, 44]
    assert [entry["name"] for entry in entries] == ["Tackle", "Bite"]
    assert entries[0]["pp"] == entries[0]["max_pp"] > 0


def test_move_display_entries_reads_canonical_moves_without_summary_moves():
    pokemon = {
        "canonical": {
            "source_generation": 4,
            "moves": [
                {"move_id": 33, "name": "Tackle", "pp": 12, "max_pp": 35, "pp_ups": 0},
                {"move_id": 44, "name": "Bite", "pp": 20, "max_pp": 25, "pp_ups": 0},
            ],
        },
    }

    entries = move_display_entries(pokemon)

    assert [entry["move_id"] for entry in entries] == [33, 44]
    assert entries[0]["name"] == "Tackle"
    assert entries[0]["pp"] == 12
    assert entries[0]["max_pp"] == 35


def test_apply_moves_display_updates_summary_and_canonical_payloads():
    pokemon = {
        "generation": 4,
        "summary": {
            "moves": [467, 33],
            "move_names": ["Shadow Force", "Tackle"],
        },
        "canonical": {
            "source_generation": 4,
            "moves": [
                {"move_id": 467, "name": "Shadow Force", "pp": 5, "max_pp": 5, "pp_ups": 0},
                {"move_id": 33, "name": "Tackle", "pp": 35, "max_pp": 35, "pp_ups": 0},
            ],
        },
    }

    preview = _apply_moves_display(
        pokemon,
        {467: 44},
        {467: "Bite"},
        target_generation=4,
    )

    assert preview["moves"][0] == 44
    assert preview["move_names"][0] == "Bite"
    assert preview["summary"]["moves"][0] == 44
    assert preview["summary"]["move_names"][0] == "Bite"
    assert preview["canonical"]["moves"][0]["move_id"] == 44
    assert preview["canonical"]["moves"][0]["name"] == "Bite"
    assert preview["canonical"]["moves"][0]["pp"] == preview["canonical"]["moves"][0]["max_pp"] > 0
    assert move_display_entries(preview)[0]["name"] == "Bite"


def test_pokemon_xp_bar_reads_top_level_experience():
    pokemon = {
        "generation": 1,
        "species_id": 4,
        "national_dex_id": 4,
        "experience": 105986,
    }

    fill, current_xp, next_xp = pokemon_xp_bar(pokemon)

    assert 0.0 < fill <= 1.0
    assert current_xp == 105986
    assert next_xp > current_xp


def test_pokemon_xp_bar_reads_canonical_experience():
    pokemon = {
        "canonical": {
            "source_generation": 4,
            "species_national_id": 395,
            "experience": 98087,
        },
    }

    fill, current_xp, next_xp = pokemon_xp_bar(pokemon)

    assert 0.0 < fill < 1.0
    assert current_xp == 98087
    assert next_xp > current_xp


def test_pokemon_xp_bar_reads_raw_canonical_experience():
    pokemon = {
        "generation": 4,
        "raw": {
            "canonical": {
                "source_generation": 4,
                "species_national_id": 395,
                "experience": 98087,
            },
        },
    }

    fill, current_xp, next_xp = pokemon_xp_bar(pokemon)

    assert 0.0 < fill < 1.0
    assert current_xp == 98087
    assert next_xp > current_xp


def test_enrich_pokemon_experience_for_display_adds_progress_from_canonical():
    pokemon = {
        "canonical": {
            "source_generation": 4,
            "species_national_id": 395,
            "experience": 98087,
        },
    }

    enriched = enrich_pokemon_experience_for_display(pokemon)

    assert enriched["experience"] == 98087
    assert enriched["experience_progress"]["experience"] == 98087
    assert 0.0 < enriched["experience_progress"]["fill_ratio"] < 1.0


def test_gen4_summary_to_local_pokemon_copies_experience_progress():
    model = SaveModel(
        path=Path("dummy.sav"),
        bytes=bytearray(),
        generation=4,
        game="pokemon_soulsilver",
        label="dummy",
        layout={},
        player_name="",
    )
    summary = SimpleNamespace(
        location="party:0",
        species_id=395,
        species_name="Empoleon",
        national_dex_id=395,
        level=47,
        nickname="Empoleon",
        ot_name="",
        trainer_id=1,
        held_item_id=None,
        held_item_name=None,
        gender=None,
        display_summary="Empoleon Lv.47",
    )
    payload = {
        "summary": {"moves": [33], "move_names": ["Tackle"]},
        "canonical": {
            "source_generation": 4,
            "species_national_id": 395,
            "experience": 98087,
            "moves": [{"move_id": 33, "name": "Tackle", "pp": 35, "max_pp": 35, "pp_ups": 0}],
        },
    }

    pokemon = model._summary_to_local_pokemon(summary, source="party", generation=4, game="pokemon_soulsilver", payload=payload)

    assert pokemon["experience"] == 98087
    assert pokemon["experience_progress"]["experience"] == 98087
    assert 0.0 < pokemon["experience_progress"]["fill_ratio"] < 1.0
    assert pokemon_xp_bar(pokemon)[0] == pokemon["experience_progress"]["fill_ratio"]


def test_state_enrich_pokemon_falls_back_to_local_runtime(monkeypatch):
    state = PokecableState()

    def fail_remote(*_args, **_kwargs):
        raise SaveError("offline")

    monkeypatch.setattr(state, "_runtime_post", fail_remote)
    save = SimpleNamespace(generation=4, game="pokemon_soulsilver")
    pokemon = [
        {
            "generation": 4,
            "game": "pokemon_soulsilver",
            "species_id": 395,
            "experience": 98087,
            "level": 47,
            "nickname": "Empoleon",
        }
    ]

    state.enrich_pokemon(save, pokemon)

    assert pokemon[0]["experience_progress"]["experience"] == 98087
    assert 0.0 < pokemon[0]["experience_progress"]["fill_ratio"] < 1.0
