from __future__ import annotations

import unittest

from pokecable_room.data.unown_forms import (
    gen2_unown_form_from_dvs,
    gen3_unown_form,
    gen3_unown_form_from_personality,
)


class UnownFormTests(unittest.TestCase):
    def test_gen2_unown_form_from_dvs(self) -> None:
        self.assertEqual(gen2_unown_form_from_dvs(0, 0, 0, 0), "A")
        self.assertEqual(gen2_unown_form_from_dvs(15, 15, 15, 15), "Z")

    def test_gen3_unown_form_from_personality(self) -> None:
        self.assertEqual(gen3_unown_form_from_personality(0), "A")
        self.assertEqual(gen3_unown_form_from_personality(0x00010203), "?")

    def test_gen3_internal_form_mapping(self) -> None:
        self.assertEqual(gen3_unown_form(201, 0), "A")
        self.assertEqual(gen3_unown_form(252, 0), "B")
        self.assertEqual(gen3_unown_form(276, 0), "Z")
        self.assertIsNone(gen3_unown_form(277, 0))


if __name__ == "__main__":
    unittest.main()
