from __future__ import annotations

import unittest

from pokecable_room.canonical import CanonicalItem, CanonicalMove, CanonicalPokemon, CanonicalSpecies
from pokecable_room.showdown import canonical_team_to_showdown_text, canonical_to_showdown_set


def dratini() -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=3,
        source_game="pokemon_emerald",
        species_national_id=147,
        species_name="Dratini",
        species=CanonicalSpecies(
            national_dex_id=147,
            source_species_id=147,
            source_species_id_space="gen3_internal",
            name="Dratini",
        ),
        nickname="BLUE",
        level=26,
        ot_name="MAY",
        trainer_id=12345,
        held_item=CanonicalItem(item_id=201, name="Dragon Scale", source_generation=3),
        moves=[
            CanonicalMove(move_id=86, name="Thunder Wave", source_generation=3),
            CanonicalMove(move_id=35, name="Wrap", source_generation=3),
            CanonicalMove(move_id=57, name="Surf", source_generation=3),
            CanonicalMove(move_id=21, name="Slam", source_generation=3),
            CanonicalMove(move_id=0, name=None, source_generation=3),
        ],
        ability="Shed Skin",
        nature="Serious",
        metadata={"gender": "M"},
    )


class ShowdownTeamTests(unittest.TestCase):
    def test_canonical_to_showdown_set(self) -> None:
        showdown_set = canonical_to_showdown_set(dratini(), 3)
        self.assertEqual(showdown_set["name"], "BLUE")
        self.assertEqual(showdown_set["species"], "Dratini")
        self.assertEqual(showdown_set["item"], "Dragon Scale")
        self.assertEqual(showdown_set["level"], 26)
        self.assertEqual(showdown_set["moves"], ["Thunder Wave", "Wrap", "Surf", "Slam"])

    def test_team_text(self) -> None:
        text = canonical_team_to_showdown_text([dratini()], 3)
        self.assertIn("BLUE (Dratini) (M) @ Dragon Scale", text)
        self.assertIn("Level: 26", text)
        self.assertIn("Ability: Shed Skin", text)
        self.assertIn("Serious Nature", text)
        self.assertIn("- Thunder Wave", text)

    def test_gen1_gets_normalized_battle_fields(self) -> None:
        pokemon = dratini()
        pokemon.ability = None
        pokemon.nature = None
        text = canonical_team_to_showdown_text([pokemon], 1)
        self.assertIn("Ability: No Ability", text)
        self.assertIn("Serious Nature", text)


if __name__ == "__main__":
    unittest.main()
