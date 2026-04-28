from __future__ import annotations

import unittest

from pokecable_room.data.species import native_to_national, national_to_native


class SpeciesMappingTests(unittest.TestCase):
    def test_gen3_unown_internal_forms_map_to_national_unown(self) -> None:
        for species_id in range(252, 277):
            with self.subTest(species_id=species_id):
                self.assertEqual(native_to_national(3, species_id), 201)

    def test_gen3_national_unown_maps_to_canonical_base_internal_id(self) -> None:
        # Gen 3 save data can represent Unown through internal 201 and extra
        # internal form IDs 252..276. New conversions target base Unown.
        self.assertEqual(national_to_native(3, 201), 201)

    def test_gen3_hoenn_internal_species_map_to_national_dex(self) -> None:
        cases = [
            (373, 366),
            (374, 367),
            (375, 368),
            (411, 358),
        ]
        for native_id, national_id in cases:
            with self.subTest(native_id=native_id):
                self.assertEqual(native_to_national(3, native_id), national_id)
                self.assertEqual(national_to_native(3, national_id), native_id)

    def test_round_trip_species_when_single_native_id_exists(self) -> None:
        cases = [
            (1, 38),
            (1, 149),
            (2, 64),
            (2, 251),
            (3, 64),
            (3, 373),
            (3, 411),
        ]
        for generation, native_id in cases:
            with self.subTest(generation=generation, native_id=native_id):
                national_id = native_to_national(generation, native_id)
                self.assertEqual(national_to_native(generation, national_id), native_id)


if __name__ == "__main__":
    unittest.main()
