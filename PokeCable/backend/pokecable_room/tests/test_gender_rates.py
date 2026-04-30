from __future__ import annotations

import unittest

from pokecable_room.data.gender_rates import (
    gender_from_gen2_attack_dv,
    gender_from_gen3_personality,
    gender_rate_for_species,
)


class GenderRateTests(unittest.TestCase):
    def test_gender_rate_lookup_known_species(self) -> None:
        self.assertEqual(gender_rate_for_species(1), 1)
        self.assertEqual(gender_rate_for_species(29), 8)
        self.assertEqual(gender_rate_for_species(81), -1)

    def test_gen2_gender_from_attack_dv(self) -> None:
        self.assertEqual(gender_from_gen2_attack_dv(1, 0), "♀")
        self.assertEqual(gender_from_gen2_attack_dv(1, 2), "♂")
        self.assertEqual(gender_from_gen2_attack_dv(29, 15), "♀")
        self.assertIsNone(gender_from_gen2_attack_dv(81, 7))

    def test_gen3_gender_from_personality(self) -> None:
        self.assertEqual(gender_from_gen3_personality(1, 0), "♀")
        self.assertEqual(gender_from_gen3_personality(1, 250), "♂")
        self.assertEqual(gender_from_gen3_personality(32, 0), "♂")
        self.assertIsNone(gender_from_gen3_personality(81, 0))


if __name__ == "__main__":
    unittest.main()
