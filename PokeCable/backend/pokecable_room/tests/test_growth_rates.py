from __future__ import annotations

import unittest

from pokecable_room.data.growth_rates import (
    ERRATIC,
    FLUCTUATING,
    MEDIUM_SLOW,
    experience_for_level,
    growth_rate_id_for_national,
    level_from_experience,
    level_from_species_experience,
)


class GrowthRatesTests(unittest.TestCase):
    def test_growth_rate_lookup_covers_gen3_species(self) -> None:
        self.assertEqual(growth_rate_id_for_national(384), 1)
        self.assertEqual(growth_rate_id_for_national(290), ERRATIC)
        self.assertEqual(growth_rate_id_for_national(285), FLUCTUATING)
        self.assertEqual(growth_rate_id_for_national(64), MEDIUM_SLOW)

    def test_level_inverse_roundtrip_for_key_curves(self) -> None:
        for growth_rate_id, level in ((ERRATIC, 45), (FLUCTUATING, 28), (MEDIUM_SLOW, 32)):
            experience = experience_for_level(growth_rate_id, level)
            self.assertEqual(level_from_experience(growth_rate_id, experience), level)

    def test_species_level_from_experience_uses_species_curve(self) -> None:
        experience = experience_for_level(1, 70)
        self.assertEqual(level_from_species_experience(384, experience), 70)


if __name__ == "__main__":
    unittest.main()
