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
    def test_mew_cross_generation_species_compatibility(self) -> None:
        gen3_mew = canonical(source_generation=3, national_id=151, native_id=151, name="Mew")
        gen1_report = build_compatibility_report(gen3_mew, 1, cross_generation_enabled=True)
        self.assertTrue(gen1_report.compatible)
        self.assertEqual(gen1_report.normalized_species["target_species_id"], 21)
        self.assertEqual(gen1_report.normalized_species["target_species_id_space"], "gen1_internal")

        gen2_report = build_compatibility_report(gen3_mew, 2, cross_generation_enabled=True)
        self.assertTrue(gen2_report.compatible)
        self.assertEqual(gen2_report.normalized_species["target_species_id"], 151)
        self.assertEqual(gen2_report.normalized_species["target_species_id_space"], "national_dex")

        self.assertTrue(
            build_compatibility_report(
                canonical(source_generation=1, national_id=151, native_id=21, name="Mew"),
                3,
                cross_generation_enabled=True,
            ).compatible
        )
        self.assertTrue(
            build_compatibility_report(
                canonical(source_generation=2, national_id=151, name="Mew"),
                3,
                cross_generation_enabled=True,
            ).compatible
        )

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

    def test_gen3_treecko_blocks_when_target_is_gen1_or_gen2(self) -> None:
        candidate = canonical(source_generation=3, national_id=252, native_id=277, name="Treecko")
        for target_generation in (1, 2):
            with self.subTest(target_generation=target_generation):
                report = build_compatibility_report(candidate, target_generation, cross_generation_enabled=True)
                self.assertFalse(report.compatible)
                self.assertTrue(any("National Dex #252" in reason for reason in report.blocking_reasons))

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
        self.assertTrue(report.requires_user_confirmation)

    def test_mew_item_rules_for_downconvert(self) -> None:
        gen2_report = build_compatibility_report(
            canonical(
                source_generation=3,
                national_id=151,
                native_id=151,
                name="Mew",
                held_item=CanonicalItem(item_id=199, name="Metal Coat", source_generation=3),
            ),
            2,
            cross_generation_enabled=True,
        )
        self.assertTrue(gen2_report.compatible)
        self.assertTrue(any("ID 143" in item for item in gen2_report.transformations))
        self.assertNotIn("held_item", gen2_report.data_loss)

        gen1_report = build_compatibility_report(
            canonical(
                source_generation=3,
                national_id=151,
                native_id=151,
                name="Mew",
                held_item=CanonicalItem(item_id=199, name="Metal Coat", source_generation=3),
            ),
            1,
            cross_generation_enabled=True,
        )
        self.assertTrue(gen1_report.compatible)
        self.assertIn("held_item", gen1_report.data_loss)
        self.assertTrue(gen1_report.requires_user_confirmation)

        no_item = build_compatibility_report(
            canonical(source_generation=3, national_id=151, native_id=151, name="Mew"),
            1,
            cross_generation_enabled=True,
        )
        self.assertNotIn("held_item", no_item.data_loss)

        no_equivalent = build_compatibility_report(
            canonical(
                source_generation=3,
                national_id=151,
                native_id=151,
                name="Mew",
                held_item=CanonicalItem(item_id=999, name="Unknown Item", source_generation=3),
            ),
            2,
            cross_generation_enabled=True,
        )
        self.assertTrue(no_equivalent.compatible)
        self.assertIn("held_item", no_equivalent.data_loss)
        self.assertTrue(no_equivalent.requires_user_confirmation)

    def test_strict_blocks_held_item_and_trainer_id_data_loss(self) -> None:
        held_item_report = build_compatibility_report(
            canonical(
                source_generation=2,
                national_id=64,
                name="Kadabra",
                held_item=CanonicalItem(item_id=0x52, name="King's Rock", source_generation=2),
            ),
            1,
            cross_generation_enabled=True,
            policy="strict",
        )
        self.assertFalse(held_item_report.compatible)
        self.assertIn("held_item", held_item_report.data_loss)

        trainer_report_source = canonical(source_generation=3, national_id=64, native_id=64, name="Kadabra")
        trainer_report_source.trainer_id = 0x12345678
        trainer_report = build_compatibility_report(
            trainer_report_source,
            2,
            cross_generation_enabled=True,
            policy="strict",
        )
        self.assertFalse(trainer_report.compatible)
        self.assertIn("trainer_id_high_bits", trainer_report.data_loss)

    def test_mew_modern_fields_report_data_loss_to_gen1_and_gen2(self) -> None:
        for target_generation in (1, 2):
            with self.subTest(target_generation=target_generation):
                candidate = canonical(
                    source_generation=3,
                    national_id=151,
                    native_id=151,
                    name="Mew",
                    ability="Synchronize",
                    nature="Timid",
                )
                candidate.trainer_id = 0x12345678
                report = build_compatibility_report(candidate, target_generation, cross_generation_enabled=True)
                self.assertTrue(report.compatible)
                self.assertIn("ability", report.data_loss)
                self.assertIn("nature", report.data_loss)
                self.assertIn("trainer_id_high_bits", report.data_loss)
                self.assertTrue(any("16 bits" in item for item in report.transformations))

    def test_mew_gen1_or_gen2_to_gen3_reports_native_field_transformations(self) -> None:
        for source_generation, native_id in ((1, 21), (2, 151)):
            with self.subTest(source_generation=source_generation):
                report = build_compatibility_report(
                    canonical(source_generation=source_generation, national_id=151, native_id=native_id, name="Mew"),
                    3,
                    cross_generation_enabled=True,
                )
                self.assertTrue(report.compatible)
                self.assertTrue(any("Ability Gen 3" in item for item in report.transformations))
                self.assertTrue(any("Nature Gen 3" in item for item in report.transformations))

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

    def test_mew_move_policy_for_gen3_downconvert(self) -> None:
        compatible = build_compatibility_report(
            canonical(source_generation=3, national_id=151, native_id=151, name="Mew", moves=[CanonicalMove(33)]),
            1,
            cross_generation_enabled=True,
        )
        self.assertTrue(compatible.compatible)

        safe_default = build_compatibility_report(
            canonical(source_generation=3, national_id=151, native_id=151, name="Mew", moves=[CanonicalMove(252)]),
            1,
            cross_generation_enabled=True,
        )
        self.assertFalse(safe_default.compatible)
        self.assertTrue(any("Fake Out" in reason for reason in safe_default.blocking_reasons))

        permissive = build_compatibility_report(
            canonical(source_generation=3, national_id=151, native_id=151, name="Mew", moves=[CanonicalMove(252)]),
            1,
            cross_generation_enabled=True,
            policy="permissive",
        )
        self.assertTrue(permissive.compatible)
        self.assertEqual(permissive.removed_moves, [{"move_id": 252, "name": "Fake Out"}])
        self.assertIn("moves", permissive.data_loss)
        self.assertTrue(permissive.requires_user_confirmation)

        gen2 = build_compatibility_report(
            canonical(source_generation=3, national_id=151, native_id=151, name="Mew", moves=[CanonicalMove(33)]),
            2,
            cross_generation_enabled=True,
        )
        self.assertTrue(gen2.compatible)

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
        self.assertEqual(MOVE_DATA[94].name, "Psychic")
        self.assertEqual(MOVE_DATA[105].name, "Recover")
        self.assertEqual(MOVE_DATA[252].name, "Fake Out")
        self.assertEqual(MOVE_DATA[252].base_pp, 10)
        self.assertTrue(move_exists(200, 2))
        self.assertFalse(move_exists(252, 2))
        self.assertEqual(MOVE_DATA[250].name, "Move #250")


if __name__ == "__main__":
    unittest.main()
