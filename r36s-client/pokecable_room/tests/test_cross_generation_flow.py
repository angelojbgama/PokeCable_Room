from __future__ import annotations

import sys
import tempfile
import unittest
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "server"))

from app.models import FORWARD_TRANSFER_TO_GEN3, LEGACY_DOWNCONVERT_EXPERIMENTAL, TIME_CAPSULE_GEN1_GEN2
from app.rooms import RoomManager

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.client import _build_offer_payload
from pokecable_room.converters import get_converter
from pokecable_room.parsers.gen1 import Gen1Parser
from pokecable_room.parsers.gen2 import Gen2Parser
from pokecable_room.parsers.gen3 import Gen3Parser

from test_gen1_synthetic import synthetic_save as synthetic_gen1_save
from test_gen2_parser import synthetic_save as synthetic_gen2_save
from test_gen3_parser import synthetic_save as synthetic_gen3_save


class CrossGenerationRoomFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        asyncio.get_running_loop().slow_callback_duration = 10

    def _parser(self, parser_cls, path: Path, data: bytes):
        path.write_bytes(data)
        parser = parser_cls()
        parser.load(path)
        return parser

    def _set_mew(self, parser, location: str = "party:0"):
        parser.set_species_id(location, {1: 21, 2: 151, 3: 151}[parser.get_generation()])
        if parser.get_generation() in {2, 3}:
            parser.clear_held_item(location)
        canonical = parser.export_canonical(location)
        canonical.moves = []
        return canonical

    def _offer(self, parser, target_generation: int, trade_mode: str) -> dict:
        return _build_offer_payload(
            parser,
            "party:0",
            trade_mode=trade_mode,
            target_generation=target_generation,
            cross_generation_policy="safe_default",
            enabled_cross_generation_modes=[
                TIME_CAPSULE_GEN1_GEN2,
                FORWARD_TRANSFER_TO_GEN3,
                LEGACY_DOWNCONVERT_EXPERIMENTAL,
            ],
        ).to_dict()

    async def _commit_room(self, manager: RoomManager, room_name: str, mode: str, creator_generation: int, join_generation: int) -> None:
        await manager.create_room(
            room_name=room_name,
            password="pw",
            client_id="a",
            generation=creator_generation,
            game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[creator_generation],
            trade_mode=mode,
            supported_trade_modes=[
                mode,
                TIME_CAPSULE_GEN1_GEN2,
                FORWARD_TRANSFER_TO_GEN3,
                LEGACY_DOWNCONVERT_EXPERIMENTAL,
            ],
        )
        await manager.join_room(
            room_name=room_name,
            password="pw",
            client_id="b",
            generation=join_generation,
            game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[join_generation],
            supported_trade_modes=[
                mode,
                TIME_CAPSULE_GEN1_GEN2,
                FORWARD_TRANSFER_TO_GEN3,
                LEGACY_DOWNCONVERT_EXPERIMENTAL,
            ],
        )

    async def test_time_capsule_gen1_gen2_room_commits_and_converts_both_saves(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen1 = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            gen2 = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            manager = RoomManager(cross_generation_enabled=True, enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2])
            await self._commit_room(manager, "time", TIME_CAPSULE_GEN1_GEN2, 1, 2)

            await manager.offer_pokemon(client_id="a", payload=self._offer(gen1, 2, TIME_CAPSULE_GEN1_GEN2))
            await manager.offer_pokemon(client_id="b", payload=self._offer(gen2, 1, TIME_CAPSULE_GEN1_GEN2))
            await manager.confirm_trade(client_id="a")
            room, _slot, committed = await manager.confirm_trade(client_id="b")

            self.assertTrue(committed)
            get_converter(2, 1).apply_to_save(gen1, "party:0", CanonicalPokemon.from_dict(room.offers["B"].canonical))
            get_converter(1, 2).apply_to_save(gen2, "party:0", CanonicalPokemon.from_dict(room.offers["A"].canonical))
            self.assertTrue(gen1.validate())
            self.assertTrue(gen2.validate())
            self.assertEqual(gen1.list_party()[0].species_name, "Onix")
            self.assertEqual(gen2.list_party()[0].species_name, "Kadabra")

    def test_mew_gen1_gen2_time_capsule_local_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen1_path = root / "red.sav"
            gen2_path = root / "crystal.sav"
            gen1 = self._parser(Gen1Parser, gen1_path, synthetic_gen1_save())
            gen2 = self._parser(Gen2Parser, gen2_path, synthetic_gen2_save())

            gen1_offer = self._set_mew(gen1)
            gen2_offer = self._set_mew(gen2)
            get_converter(2, 1).apply_to_save(gen1, "party:0", gen2_offer)
            get_converter(1, 2).apply_to_save(gen2, "party:0", gen1_offer)
            gen1.save(gen1_path)
            gen2.save(gen2_path)

            reloaded_gen1 = Gen1Parser()
            reloaded_gen2 = Gen2Parser()
            reloaded_gen1.load(gen1_path)
            reloaded_gen2.load(gen2_path)
            self.assertTrue(reloaded_gen1.validate())
            self.assertTrue(reloaded_gen2.validate())
            self.assertEqual(reloaded_gen1.get_species_id("party:0"), 21)
            self.assertEqual(reloaded_gen2.get_species_id("party:0"), 151)

    async def test_forward_transfer_rooms_commit_and_apply_older_payload_to_gen3(self) -> None:
        for source_generation, parser_cls, data, filename in [
            (1, Gen1Parser, synthetic_gen1_save(), "red.sav"),
            (2, Gen2Parser, synthetic_gen2_save(), "crystal.sav"),
        ]:
            with self.subTest(source_generation=source_generation):
                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    source = self._parser(parser_cls, root / filename, data)
                    gen3 = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
                    manager = RoomManager(
                        cross_generation_enabled=True,
                        enabled_trade_modes=[FORWARD_TRANSFER_TO_GEN3, LEGACY_DOWNCONVERT_EXPERIMENTAL],
                    )
                    await self._commit_room(manager, f"forward-{source_generation}", FORWARD_TRANSFER_TO_GEN3, source_generation, 3)

                    await manager.offer_pokemon(client_id="a", payload=self._offer(source, 3, FORWARD_TRANSFER_TO_GEN3))
                    await manager.offer_pokemon(client_id="b", payload=self._offer(gen3, source_generation, FORWARD_TRANSFER_TO_GEN3))
                    await manager.confirm_trade(client_id="a")
                    room, _slot, committed = await manager.confirm_trade(client_id="b")

                    self.assertTrue(committed)
                    get_converter(source_generation, 3).apply_to_save(gen3, "party:1", CanonicalPokemon.from_dict(room.offers["A"].canonical))
                    self.assertTrue(source.validate())
                    self.assertTrue(gen3.validate())

    def test_mew_forward_and_downconvert_local_flows(self) -> None:
        cases = [
            (Gen1Parser, synthetic_gen1_save(), "red.sav", Gen3Parser, synthetic_gen3_save("rse"), "emerald.sav", 1, 3, 151),
            (Gen2Parser, synthetic_gen2_save(), "crystal.sav", Gen3Parser, synthetic_gen3_save("rse"), "emerald.sav", 2, 3, 151),
            (Gen3Parser, synthetic_gen3_save("rse"), "emerald.sav", Gen1Parser, synthetic_gen1_save(), "red.sav", 3, 1, 21),
            (Gen3Parser, synthetic_gen3_save("rse"), "emerald.sav", Gen2Parser, synthetic_gen2_save(), "crystal.sav", 3, 2, 151),
        ]
        for source_cls, source_data, source_name, target_cls, target_data, target_name, source_generation, target_generation, expected in cases:
            with self.subTest(source_generation=source_generation, target_generation=target_generation):
                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    source = self._parser(source_cls, root / source_name, source_data)
                    target_path = root / target_name
                    target = self._parser(target_cls, target_path, target_data)

                    get_converter(source_generation, target_generation).apply_to_save(
                        target,
                        "party:1",
                        self._set_mew(source),
                    )
                    target.save(target_path)

                    reloaded = target_cls()
                    reloaded.load(target_path)
                    self.assertTrue(reloaded.validate())
                    self.assertEqual(reloaded.get_species_id("party:1"), expected)
                    self.assertEqual(reloaded.list_party()[1].species_name, "Mew")

    async def test_legacy_downconvert_converts_compatible_and_blocks_incompatible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen3 = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            gen1 = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            gen2 = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            manager = RoomManager(
                cross_generation_enabled=True,
                enabled_trade_modes=[LEGACY_DOWNCONVERT_EXPERIMENTAL, FORWARD_TRANSFER_TO_GEN3],
            )
            await self._commit_room(manager, "legacy", LEGACY_DOWNCONVERT_EXPERIMENTAL, 3, 1)

            await manager.offer_pokemon(client_id="a", payload=self._offer(gen3, 1, LEGACY_DOWNCONVERT_EXPERIMENTAL))
            await manager.offer_pokemon(client_id="b", payload=self._offer(gen1, 3, LEGACY_DOWNCONVERT_EXPERIMENTAL))
            await manager.confirm_trade(client_id="a")
            room, _slot, committed = await manager.confirm_trade(client_id="b")

            self.assertTrue(committed)
            get_converter(3, 1).apply_to_save(gen1, "party:0", CanonicalPokemon.from_dict(room.offers["A"].canonical))
            self.assertTrue(gen1.validate())
            self.assertEqual(gen1.list_party()[0].species_name, "Kadabra")

            get_converter(3, 2).apply_to_save(gen2, "party:0", gen3.export_canonical("party:0"))
            self.assertTrue(gen2.validate())
            self.assertEqual(gen2.list_party()[0].species_name, "Kadabra")

            incompatible = gen3.export_canonical("party:1")
            self.assertFalse(get_converter(3, 1).can_convert(incompatible).compatible)
            self.assertFalse(get_converter(3, 2).can_convert(incompatible).compatible)

            gen2.set_species_id("party:0", 152)
            self.assertFalse(get_converter(2, 1).can_convert(gen2.export_canonical("party:0")).compatible)


if __name__ == "__main__":
    unittest.main()
