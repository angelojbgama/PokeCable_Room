from __future__ import annotations

import sys
import tempfile
import unittest
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "server"))

from app.models import (
    CANONICAL_CROSS_GENERATION,
    FORWARD_TRANSFER_TO_GEN3,
    LEGACY_DOWNCONVERT_EXPERIMENTAL,
    RAW_SAME_GENERATION,
    TIME_CAPSULE_GEN1_GEN2,
)
from app.rooms import RoomManager

from pokecable_room.canonical import CanonicalItem, CanonicalMove, CanonicalPokemon
from pokecable_room.client import _build_offer_payload
from pokecable_room.compatibility import build_compatibility_report
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

    def _set_national_species(self, parser, national_id: int, location: str = "party:0"):
        native_by_generation = {
            1: {25: 84, 151: 21},
            2: {25: 25, 151: 151, 152: 152},
            3: {25: 25, 151: 151, 252: 277, 366: 373},
        }
        parser.set_species_id(location, native_by_generation[parser.get_generation()][national_id])
        if parser.get_generation() in {2, 3}:
            parser.clear_held_item(location)

    def _offer(self, parser, target_generation: int, trade_mode: str | None = None) -> dict:
        return _build_offer_payload(
            parser,
            "party:0",
            trade_mode=trade_mode,
            target_generation=target_generation,
            cross_generation_policy="safe_default",
        ).to_dict()

    async def _commit_room(self, manager: RoomManager, room_name: str, mode: str, creator_generation: int, join_generation: int) -> None:
        await manager.create_room(
            room_name=room_name,
            password="pw",
            client_id="a",
            generation=creator_generation,
            game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[creator_generation],
            supported_protocols=[RAW_SAME_GENERATION, CANONICAL_CROSS_GENERATION],
        )
        await manager.join_room(
            room_name=room_name,
            password="pw",
            client_id="b",
            generation=join_generation,
            game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[join_generation],
            supported_protocols=[RAW_SAME_GENERATION, CANONICAL_CROSS_GENERATION],
        )

    async def _submit_preflight_ok(self, manager: RoomManager, room) -> None:
        for slot, client_id in {"A": "a", "B": "b"}.items():
            peer_slot = "B" if slot == "A" else "A"
            peer_offer = room.offers[peer_slot]
            local_generation = room.players[slot].generation
            if peer_offer.generation == local_generation:
                report = {"compatible": True, "mode": "same_generation"}
            else:
                report = build_compatibility_report(
                    CanonicalPokemon.from_dict(peer_offer.canonical),
                    local_generation,
                    cross_generation_enabled=True,
                    policy="safe_default",
                ).to_dict()
            self.assertTrue(report["compatible"])
            await manager.submit_preflight_result(client_id=client_id, compatible=True, report=report)

    async def _submit_preflight_from_reports(self, manager: RoomManager, room) -> tuple[bool, dict]:
        blocked = False
        reports = {}
        for slot, client_id in {"A": "a", "B": "b"}.items():
            peer_slot = "B" if slot == "A" else "A"
            peer_offer = room.offers[peer_slot]
            local_generation = room.players[slot].generation
            if peer_offer.generation == local_generation:
                report = {"compatible": True, "mode": "same_generation"}
            else:
                report = build_compatibility_report(
                    CanonicalPokemon.from_dict(peer_offer.canonical),
                    local_generation,
                    cross_generation_enabled=True,
                    policy="safe_default",
                ).to_dict()
            reports[slot] = report
            _room, _slot, blocked, _ready, _reports = await manager.submit_preflight_result(
                client_id=client_id,
                compatible=bool(report["compatible"]),
                report=report,
            )
            if blocked:
                break
        return blocked, reports

    async def test_time_capsule_gen1_gen2_room_commits_and_converts_both_saves(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen1 = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            gen2 = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            manager = RoomManager(cross_generation_enabled=True, enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2])
            await self._commit_room(manager, "time", TIME_CAPSULE_GEN1_GEN2, 1, 2)

            await manager.offer_pokemon(client_id="a", payload=self._offer(gen1, 2, TIME_CAPSULE_GEN1_GEN2))
            room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen2, 1, TIME_CAPSULE_GEN1_GEN2))
            await self._submit_preflight_ok(manager, room)
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
                    room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen3, source_generation, FORWARD_TRANSFER_TO_GEN3))
                    await self._submit_preflight_ok(manager, room)
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
            room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen1, 3, LEGACY_DOWNCONVERT_EXPERIMENTAL))
            await self._submit_preflight_ok(manager, room)
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

    async def test_gen1_pikachu_gen3_mew_protocol_flow_converts_both_saves(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen1 = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            gen3 = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            self._set_national_species(gen1, 25)
            self._set_national_species(gen3, 151)
            manager = RoomManager(cross_generation_enabled=True, enabled_trade_modes=[FORWARD_TRANSFER_TO_GEN3, LEGACY_DOWNCONVERT_EXPERIMENTAL])
            await self._commit_room(manager, "pikachu-mew", FORWARD_TRANSFER_TO_GEN3, 1, 3)
            await manager.offer_pokemon(client_id="a", payload=self._offer(gen1, 3))
            room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen3, 1))
            blocked, reports = await self._submit_preflight_from_reports(manager, room)
            self.assertFalse(blocked)
            self.assertTrue(reports["A"]["compatible"])
            self.assertTrue(reports["B"]["compatible"])
            await manager.confirm_trade(client_id="a")
            room, _slot, committed = await manager.confirm_trade(client_id="b")
            self.assertTrue(committed)
            get_converter(3, 1).apply_to_save(gen1, "party:0", CanonicalPokemon.from_dict(room.offers["B"].canonical), policy="safe_default")
            get_converter(1, 3).apply_to_save(gen3, "party:0", CanonicalPokemon.from_dict(room.offers["A"].canonical), policy="safe_default")
            self.assertTrue(gen1.validate())
            self.assertTrue(gen3.validate())
            self.assertEqual(gen1.get_species_id("party:0"), 21)
            self.assertEqual(gen3.get_species_id("party:0"), 25)

    def test_gen1_pikachu_gen3_mew_auto_retrocompat_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen1_path = root / "red.sav"
            gen3_path = root / "emerald.sav"
            gen1 = self._parser(Gen1Parser, gen1_path, synthetic_gen1_save())
            gen3 = self._parser(Gen3Parser, gen3_path, synthetic_gen3_save("rse"))
            self._set_national_species(gen1, 25)
            self._set_national_species(gen3, 151)

            pikachu = gen1.export_canonical("party:0")
            mew = gen3.export_canonical("party:0")
            mew.ability = "Synchronize"
            mew.nature = "Timid"
            mew.held_item = CanonicalItem(item_id=199, name="Metal Coat", source_generation=3)
            mew.moves = [CanonicalMove(move_id=252, name="Fake Out", source_generation=3)]

            mew_to_gen1 = build_compatibility_report(mew, target_generation=1, cross_generation_enabled=True, policy="auto_retrocompat")
            pikachu_to_gen3 = build_compatibility_report(pikachu, target_generation=3, cross_generation_enabled=True, policy="auto_retrocompat")
            self.assertTrue(mew_to_gen1.compatible)
            self.assertFalse(mew_to_gen1.requires_user_confirmation)
            self.assertIn("ability", mew_to_gen1.data_loss)
            self.assertIn("nature", mew_to_gen1.data_loss)
            self.assertIn("held_item", mew_to_gen1.data_loss)
            self.assertIn("moves", mew_to_gen1.data_loss)
            self.assertTrue(mew_to_gen1.removed_moves)
            self.assertTrue(mew_to_gen1.removed_items)
            self.assertTrue(pikachu_to_gen3.compatible)

            result_gen1 = get_converter(3, 1).apply_to_save(gen1, "party:0", mew, policy="auto_retrocompat")
            result_gen3 = get_converter(1, 3).apply_to_save(gen3, "party:0", pikachu, policy="auto_retrocompat")
            self.assertIn("moves", result_gen1.data_loss)
            self.assertTrue(any("Pound" in item for item in result_gen1.transformations))
            self.assertTrue(result_gen3.wrote_to_save)
            gen1.save(gen1_path)
            gen3.save(gen3_path)

            reloaded_gen1 = Gen1Parser()
            reloaded_gen3 = Gen3Parser()
            reloaded_gen1.load(gen1_path)
            reloaded_gen3.load(gen3_path)
            self.assertTrue(reloaded_gen1.validate())
            self.assertTrue(reloaded_gen3.validate())
            self.assertEqual(reloaded_gen1.get_species_id("party:0"), 21)
            self.assertEqual(reloaded_gen3.get_species_id("party:0"), 25)

    async def test_gen1_pikachu_gen3_treecko_blocks_entire_trade(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen1 = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            gen3 = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            self._set_national_species(gen1, 25)
            self._set_national_species(gen3, 252)
            manager = RoomManager(cross_generation_enabled=True, enabled_trade_modes=[FORWARD_TRANSFER_TO_GEN3, LEGACY_DOWNCONVERT_EXPERIMENTAL])
            await self._commit_room(manager, "treecko-block", FORWARD_TRANSFER_TO_GEN3, 1, 3)
            await manager.offer_pokemon(client_id="a", payload=self._offer(gen1, 3))
            room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen3, 1))
            blocked, reports = await self._submit_preflight_from_reports(manager, room)
            self.assertTrue(blocked)
            self.assertFalse(reports["A"]["compatible"])
            self.assertIn("252", " ".join(reports["A"]["blocking_reasons"]))
            with self.assertRaises(Exception):
                await manager.confirm_trade(client_id="a")

    async def test_gen2_mew_gen3_mew_protocol_flow_converts_both_saves(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen2 = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            gen3 = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            self._set_national_species(gen2, 151)
            self._set_national_species(gen3, 151)
            manager = RoomManager(cross_generation_enabled=True, enabled_trade_modes=[FORWARD_TRANSFER_TO_GEN3, LEGACY_DOWNCONVERT_EXPERIMENTAL])
            await self._commit_room(manager, "mew-2-3", FORWARD_TRANSFER_TO_GEN3, 2, 3)
            await manager.offer_pokemon(client_id="a", payload=self._offer(gen2, 3))
            room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen3, 2))
            blocked, reports = await self._submit_preflight_from_reports(manager, room)
            self.assertFalse(blocked)
            self.assertTrue(reports["A"]["compatible"])
            self.assertTrue(reports["B"]["compatible"])

    async def test_gen2_chikorita_gen1_pikachu_blocks_entire_trade(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen2 = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            gen1 = self._parser(Gen1Parser, root / "red.sav", synthetic_gen1_save())
            self._set_national_species(gen2, 152)
            self._set_national_species(gen1, 25)
            manager = RoomManager(cross_generation_enabled=True, enabled_trade_modes=[TIME_CAPSULE_GEN1_GEN2])
            await self._commit_room(manager, "chikorita-block", TIME_CAPSULE_GEN1_GEN2, 2, 1)
            await manager.offer_pokemon(client_id="a", payload=self._offer(gen2, 1))
            room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen1, 2))
            blocked, reports = await self._submit_preflight_from_reports(manager, room)
            self.assertTrue(blocked)
            self.assertFalse(reports["B"]["compatible"])

    async def test_gen3_clamperl_gen2_mew_blocks_entire_trade(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen3 = self._parser(Gen3Parser, root / "emerald.sav", synthetic_gen3_save("rse"))
            gen2 = self._parser(Gen2Parser, root / "crystal.sav", synthetic_gen2_save())
            self._set_national_species(gen3, 366)
            self._set_national_species(gen2, 151)
            manager = RoomManager(cross_generation_enabled=True, enabled_trade_modes=[FORWARD_TRANSFER_TO_GEN3, LEGACY_DOWNCONVERT_EXPERIMENTAL])
            await self._commit_room(manager, "clamperl-block", LEGACY_DOWNCONVERT_EXPERIMENTAL, 3, 2)
            await manager.offer_pokemon(client_id="a", payload=self._offer(gen3, 2))
            room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen2, 3))
            blocked, reports = await self._submit_preflight_from_reports(manager, room)
            self.assertTrue(blocked)
            self.assertFalse(reports["B"]["compatible"])

    async def test_same_generation_gen2_raw_flow_still_commits_after_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gen2_a = self._parser(Gen2Parser, root / "a.sav", synthetic_gen2_save())
            gen2_b = self._parser(Gen2Parser, root / "b.sav", synthetic_gen2_save())
            manager = RoomManager(cross_generation_enabled=False)
            await manager.create_room(room_name="same-gen2", password="pw", client_id="a", generation=2, game="pokemon_crystal")
            await manager.join_room(room_name="same-gen2", password="pw", client_id="b", generation=2, game="pokemon_crystal")
            await manager.offer_pokemon(client_id="a", payload=self._offer(gen2_a, 2))
            room, _slot, _offer = await manager.offer_pokemon(client_id="b", payload=self._offer(gen2_b, 2))
            blocked, reports = await self._submit_preflight_from_reports(manager, room)
            self.assertFalse(blocked)
            self.assertTrue(reports["A"]["compatible"])
            self.assertTrue(reports["B"]["compatible"])
            await manager.confirm_trade(client_id="a")
            _room, _slot, committed = await manager.confirm_trade(client_id="b")
            self.assertTrue(committed)


if __name__ == "__main__":
    unittest.main()
