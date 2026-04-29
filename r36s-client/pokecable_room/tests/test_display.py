from __future__ import annotations

import unittest

from pokecable_room.display import normalize_pokemon_display


class DisplayTests(unittest.TestCase):
    def test_species_placeholder_uses_real_name(self) -> None:
        self.assertEqual(
            normalize_pokemon_display(147, "Species #147", 26, nickname="DRATINI", held_item_name=None),
            "#147 Dratini Lv. 26 — Sem item",
        )

    def test_broken_legacy_summary_is_cleaned_when_dex_is_known(self) -> None:
        self.assertEqual(
            normalize_pokemon_display(147, 'Species #147 L". 26 (DRATINI)', 26, nickname="DRATINI"),
            "#147 Dratini Lv. 26 — Sem item",
        )

    def test_nickname_different_appears(self) -> None:
        self.assertEqual(
            normalize_pokemon_display(147, "Dratini", 26, nickname="Blue", held_item_name="Dragon Scale"),
            '#147 Dratini Lv. 26 — Item: Dragon Scale "Blue"',
        )

    def test_gender_appears_when_present(self) -> None:
        self.assertEqual(
            normalize_pokemon_display(147, "Dratini", 26, gender="♂", held_item_name=None),
            "#147 Dratini ♂ Lv. 26 — Sem item",
        )


if __name__ == "__main__":
    unittest.main()
