from __future__ import annotations

from app.runtime_services import build_trade_preflight, enrich_pokemon_payload


def test_enrich_pokemon_uses_backend_species_data() -> None:
    result = enrich_pokemon_payload(
        {
            "generation": 1,
            "game": "pokemon_red",
            "pokemon": [
                {
                    "location": "party:0",
                    "species_id": 38,
                    "level": 34,
                    "nickname": "KADABRA",
                    "moves": [93, 100],
                }
            ],
        }
    )
    pokemon = result["pokemon"][0]
    assert pokemon["species_name"] == "Kadabra"
    assert pokemon["national_dex_id"] == 64
    assert pokemon["types"] == ["psychic"]
    assert pokemon["move_names"][0] == "Confusion"


def test_trade_preflight_blocks_invalid_species() -> None:
    result = build_trade_preflight(
        {
            "target_generation": 2,
            "received_payload": {
                "generation": 2,
                "game": "pokemon_crystal",
                "species_id": 999,
                "level": 30,
                "nickname": "BAD",
                "raw_data_base64": "ZmFrZQ==",
            },
        }
    )
    assert result["compatible"] is False
    assert result["trade_evolution"]["reason"] == "invalid_species"
    assert result["blocking_reasons"]


def test_trade_preflight_reports_trade_evolution() -> None:
    result = build_trade_preflight(
        {
            "target_generation": 3,
            "received_payload": {
                "generation": 3,
                "game": "pokemon_emerald",
                "species_id": 64,
                "level": 34,
                "nickname": "KADABRA",
                "raw_data_base64": "ZmFrZQ==",
            },
        }
    )
    assert result["compatible"] is True
    assert result["trade_evolution"]["evolved"] is True
    assert result["trade_evolution"]["target_species_id"] == 65
    assert result["trade_evolution"]["target_name"] == "Alakazam"
