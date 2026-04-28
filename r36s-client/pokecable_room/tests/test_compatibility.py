from __future__ import annotations

import unittest

from pokecable_room.canonical import CanonicalItem, CanonicalMove, CanonicalPokemon, CanonicalSpecies
from pokecable_room.compatibility import build_compatibility_report
from pokecable_room.data.moves import MOVE_DATA, move_exists


def canonical(
    *,
    source_generation: int,
    national_id: int,
    name: str,
    native_id: int | None = None,
    moves: list[CanonicalMove] | None = None,
    held_item: CanonicalItem | None = None,
    ability: str | None = None,
    nature: str | None = None,
    metadata: dict | None = None,
) -> CanonicalPokemon:
    source_spaces = {1: "gen1_internal", 2: "national_dex", 3: "gen3_internal"}
    return CanonicalPokemon(
        source_generation=source_generation,
        source_game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[source_generation],
        species_national_id=national_id,
        species_name=name,
        nickname=name.upper()[:10],
        level=32,
        ot_name="ASH",
        trainer_id=12345,
        moves=moves or [],
        held_item=held_item,
        ability=ability,
        nature=nature,
        metadata=metadata or {},
        species=CanonicalSpecies(
            national_dex_id=national_id,
            source_species_id=native_id if native_id is not None else national_id,
            source_species_id_space=source_spaces[source_generation],
            name=name,
        ),
    )


class CompatibilityTests(unittest.TestCase):
    def test_gen2_species_152_to_gen1_blocks(self) -> None:
        report = build_compatibility_report(canonical(source_generation=2, national_id=152, name="Chikorita"), 1, cross_generation_enabled=True)
        self.assertFalse(report.compatible)
        self.assertTrue(any("National Dex #152" in reason for reason in report.blocking_reasons))

    def test_gen3_clamperl_to_gen2_blocks(self) -> None:
        report = build_compatibility_report(
            canonical(source_generation=3, national_id=366, native_id=373, name="Clamperl"),
            2,
            cross_generation_enabled=True,
        )
        self.assertFalse(report.compatible)
        self.assertTrue(any("National Dex #366" in reason for reason in report.blocking_reasons))

    def test_gen3_kadabra_to_gen2_and_gen1_allowed(self) -> None:
        candidate = canonical(source_generation=3, national_id=64, native_id=64, name="Kadabra")
        for target_generation in (2, 1):
            with self.subTest(target_generation=target_generation):
                report = build_compatibility_report(candidate, target_generation, cross_generation_enabled=True)
                self.assertTrue(report.compatible)
                self.assertEqual(report.normalized_species["target_species_id_space"], {1: "gen1_internal", 2: "national_dex"}[target_generation])

    def test_gen3_ability_nature_to_gen2_reports_data_loss(self) -> None:
        report = build_compatibility_report(
            canonical(source_generation=3, national_id=64, native_id=64, name="Kadabra", ability="Synchronize", nature="Timid"),
            2,
            cross_generation_enabled=True,
        )
        self.assertTrue(report.compatible)
        self.assertIn("ability", report.data_loss)
        self.assertIn("nature", report.data_loss)
        self.assertIn("ability", report.removed_fields)
        self.assertIn("nature", report.removed_fields)

    def test_gen3_ability_nature_to_gen1_reports_data_loss(self) -> None:
        report = build_compatibility_report(
            canonical(source_generation=3, national_id=64, native_id=64, name="Kadabra", ability="Synchronize", nature="Timid"),
            1,
            cross_generation_enabled=True,
        )
        self.assertTrue(report.compatible)
        self.assertIn("ability", report.data_loss)
        self.assertIn("nature", report.data_loss)

    def test_held_item_to_gen1_reports_data_loss(self) -> None:
        report = build_compatibility_report(
            canonical(
                source_generation=2,
                national_id=64,
                name="Kadabra",
                held_item=CanonicalItem(item_id=0x52, name="King's Rock", source_generation=2),
            ),
            1,
            cross_generation_enabled=True,
        )
        self.assertTrue(report.compatible)
        self.assertIn("held_item", report.data_loss)
        self.assertTrue(report.removed_items)

    def test_safe_default_blocks_moves_missing_from_target(self) -> None:
        gen1_report = build_compatibility_report(
            canonical(source_generation=2, national_id=64, name="Kadabra", moves=[CanonicalMove(166)]),
            1,
            cross_generation_enabled=True,
        )
        self.assertFalse(gen1_report.compatible)
        self.assertTrue(any("Sketch" in reason for reason in gen1_report.blocking_reasons))

        gen2_report = build_compatibility_report(
            canonical(source_generation=3, national_id=64, native_id=64, name="Kadabra", moves=[CanonicalMove(252)]),
            2,
            cross_generation_enabled=True,
        )
        self.assertFalse(gen2_report.compatible)
        self.assertTrue(any("Fake Out" in reason for reason in gen2_report.blocking_reasons))

    def test_permissive_records_removed_moves_and_requires_confirmation(self) -> None:
        report = build_compatibility_report(
            canonical(source_generation=3, national_id=64, native_id=64, name="Kadabra", moves=[CanonicalMove(252)]),
            2,
            cross_generation_enabled=True,
            policy="permissive",
        )
        self.assertTrue(report.compatible)
        self.assertEqual(report.removed_moves, [{"move_id": 252, "name": "Fake Out"}])
        self.assertIn("moves", report.data_loss)
        self.assertTrue(report.requires_user_confirmation)

    def test_egg_blocks_any_target_generation(self) -> None:
        candidate = canonical(source_generation=3, national_id=64, native_id=64, name="Egg", metadata={"is_egg": True})
        for target_generation in (1, 2, 3):
            with self.subTest(target_generation=target_generation):
                report = build_compatibility_report(candidate, target_generation, cross_generation_enabled=True)
                self.assertFalse(report.compatible)
                self.assertTrue(any("Egg" in reason for reason in report.blocking_reasons))

    def test_normalized_species_contains_target_fields_when_compatible(self) -> None:
        report = build_compatibility_report(
            canonical(source_generation=3, national_id=64, native_id=64, name="Kadabra"),
            1,
            cross_generation_enabled=True,
        )
        self.assertTrue(report.compatible)
        self.assertEqual(report.normalized_species["target_species_id"], 38)
        self.assertEqual(report.normalized_species["target_species_id_space"], "gen1_internal")

    def test_known_move_names_pp_and_existence_fallback(self) -> None:
        self.assertEqual(MOVE_DATA[33].name, "Tackle")
        self.assertEqual(MOVE_DATA[33].base_pp, 35)
        self.assertEqual(MOVE_DATA[252].name, "Fake Out")
        self.assertEqual(MOVE_DATA[252].base_pp, 10)
        self.assertTrue(move_exists(200, 2))
        self.assertFalse(move_exists(252, 2))
        self.assertEqual(MOVE_DATA[250].name, "Move #250")


if __name__ == "__main__":
    unittest.main()
