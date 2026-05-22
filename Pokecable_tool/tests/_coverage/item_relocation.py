"""Battery U: item relocation across generations requires explicit user choice."""
from __future__ import annotations

import base64
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _p in (str(REPO_ROOT), str(RUNTIME)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from canonical import CanonicalItem, CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from converters.gen2_to_gen1 import Gen2ToGen1Converter  # noqa: E402
from converters.gen3_to_gen1 import Gen3ToGen1Converter  # noqa: E402
from converters.gen3_to_gen2 import Gen3ToGen2Converter  # noqa: E402
from data.items import item_category, item_exists, item_name  # noqa: E402
from data.inventory_layouts import inventory_layout_for_game  # noqa: E402
from parsers.gen1 import Gen1Parser  # noqa: E402
from parsers.gen2 import Gen2Parser  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402
from runtime_services import build_outgoing_item_relocation, build_trade_preflight  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"


def _can(src_gen: int, item_id: int, item_name_: str) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=src_gen,
        source_game={1: "pokemon_red", 2: "pokemon_crystal", 3: "pokemon_emerald"}[src_gen],
        species_national_id=1, species_name="Bulbasaur",
        nickname="BULBA", level=20, ot_name="STRESS", trainer_id=0x1234, experience=8000,
        moves=[CanonicalMove(move_id=33, pp=20, max_pp=20, pp_ups=0, source_generation=src_gen)],
        ivs=CanonicalStats(hp=10, attack=10, defense=10, speed=10, special=10, special_attack=10, special_defense=10),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={"is_shiny": False, "gender": "♂"},
        species=CanonicalSpecies(
            national_dex_id=1, source_species_id=1,
            source_species_id_space={1: "gen1_internal", 2: "national_dex", 3: "gen3_internal"}[src_gen],
            name="Bulbasaur",
        ),
        held_item=CanonicalItem(item_id=item_id, name=item_name_, source_generation=src_gen),
    )


class _FullInventoryParser:
    def get_game_id(self) -> str:
        return "pokemon_yellow"

    def has_bag_space(self, item_id: int, quantity: int) -> bool:
        del item_id, quantity
        return False

    def store_item_in_bag(self, item_id: int, quantity: int) -> None:
        raise AssertionError("Nao deveria tentar gravar na mochila quando ela esta cheia.")

    def has_pc_space(self, item_id: int, quantity: int) -> bool:
        del item_id, quantity
        return False

    def store_item_in_pc(self, item_id: int, quantity: int) -> None:
        raise AssertionError("Nao deveria tentar gravar no PC quando ele esta cheio.")


class _BothOpenParser:
    def __init__(self) -> None:
        self.stored = []

    def get_game_id(self) -> str:
        return "pokemon_yellow"

    def has_bag_space(self, item_id: int, quantity: int) -> bool:
        del item_id, quantity
        return True

    def store_item_in_bag(self, item_id: int, quantity: int) -> None:
        self.stored.append(("bag", item_id, quantity))

    def has_pc_space(self, item_id: int, quantity: int) -> bool:
        del item_id, quantity
        return True

    def store_item_in_pc(self, item_id: int, quantity: int) -> None:
        self.stored.append(("pc", item_id, quantity))


class _BagFullPcOpenParser:
    def get_game_id(self) -> str:
        return "pokemon_yellow"

    def has_bag_space(self, item_id: int, quantity: int) -> bool:
        del item_id, quantity
        return False

    def store_item_in_bag(self, item_id: int, quantity: int) -> None:
        raise AssertionError("Nao deveria tentar gravar na mochila quando ela esta cheia.")

    def has_pc_space(self, item_id: int, quantity: int) -> bool:
        del item_id, quantity
        return True

    def store_item_in_pc(self, item_id: int, quantity: int) -> None:
        raise AssertionError("Nao deveria gravar no PC sem decisao explicita do usuario.")


def run() -> BatteryReport:
    report = BatteryReport(name="U: item relocation on cross-gen transfer")

    # --- Case 1: Gen 2 Potion → Gen 1. With bag and PC available in the source save, the caller
    # must choose where the incompatible held item will be returned before transfer. ---
    source = _BothOpenParser()
    can = _can(2, 18, "Potion")  # Gen 2 Potion #18 → Gen 1 Potion #20
    converter = Gen2ToGen1Converter()
    result = converter.convert(can, source, "party:0", policy="auto_retrocompat")
    converter._relocate_dropped_item(can, result.canonical_after, source, result.compatibility_report, item_relocation_choice="bag")
    if source.stored == [("bag", 18, 1)] and result.compatibility_report.compatible:
        report.add_pass()
        report.note("Gen 2 Potion → Gen 1 devolve o item para a mochila do save de origem")
    else:
        report.add_fail(
            f"Gen 2 Potion → Gen 1 explicit bag choice failed: stored={source.stored} "
            f"compatible={result.compatibility_report.compatible}"
        )

    # --- Case 2: Gen 2 Potion → Gen 1 with explicit remove choice. Trade must proceed and
    # not store the item anywhere in the source save. ---
    source = _BothOpenParser()
    can = _can(2, 18, "Potion")
    converter = Gen2ToGen1Converter()
    result = converter.convert(can, source, "party:0", policy="auto_retrocompat")
    converter._relocate_dropped_item(can, result.canonical_after, source, result.compatibility_report, item_relocation_choice="remove")
    if source.stored == [] and result.compatibility_report.compatible:
        report.add_pass()
        report.note("Gen 2 Potion → Gen 1 explicit remove choice proceeds without storing the item")
    else:
        report.add_fail(
            f"Gen 2 Potion → Gen 1 explicit remove choice failed: stored={source.stored} "
            f"compatible={result.compatibility_report.compatible}"
        )

    # --- Case 3: Gen 3 King's Rock → Gen 1 with source bag/PC full must require manual remove
    # in the source save. ---
    can = _can(3, 187, "King's Rock")
    converter = Gen3ToGen1Converter()
    result = converter.convert(can, _FullInventoryParser(), "party:0", policy="auto_retrocompat")
    converter._relocate_dropped_item(can, result.canonical_after, _FullInventoryParser(), result.compatibility_report)
    report_obj = result.compatibility_report
    if not report_obj.compatible and any("remova o item" in r.lower() for r in report_obj.blocking_reasons):
        report.add_pass()
        report.note("Gen 3 King's Rock → Gen 1 with source inventory full blocks and asks manual remove")
    else:
        report.add_fail(
            f"Gen 3 King's Rock → Gen 1: expected manual remove guidance, got compatible={report_obj.compatible} "
            f"reasons={report_obj.blocking_reasons}"
        )

    # --- Case 4: Gen 3 Potion → Gen 2 (Potion exists in both, mapped to #18). Item should
    # stay ON the pokemon (no relocation needed). ---
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "crystal.sav"
        shutil.copy(TEST_SAVES_ROOT / "gen 2" / "Pokémon - Crystal Version.sav", work)
        target = Gen2Parser(); target.load(work)
        can = _can(3, 13, "Potion")  # Gen 3 Potion #13 → Gen 2 #18
        result = Gen3ToGen2Converter().convert(can, target, "party:0", policy="auto_retrocompat")
        target.import_canonical("party:0", result.canonical_after)
        summary = target.list_party()[0]
        if summary.held_item_id == 18:
            report.add_pass()
            report.note(f"Gen 3 Potion → Gen 2: item stayed on pokemon as #18")
        else:
            report.add_fail(f"Gen 3 Potion → Gen 2: expected mon to hold #18, got {summary.held_item_id}")

    # --- Case 5: Gen 3 unknown item without Gen 2 equivalent still allows source-side storage
    # because the item returns to the source save. ---
    source = _BothOpenParser()
    can = _can(3, 251, "Unknown Item 251")
    converter = Gen3ToGen2Converter()
    result = converter.convert(can, source, "party:0", policy="auto_retrocompat")
    plan = converter.inspect_item_relocation(can, source, result.compatibility_report) or {}
    if result.compatibility_report.compatible and plan.get("status") == "choose_destination" and plan.get("item_id") == 251:
        report.add_pass()
        report.note("Gen 3 item 251 → Gen 2 still prompts source-side storage even sem equivalente na Gen alvo")
    else:
        report.add_fail(
            f"Gen 3 item 251 → Gen 2: expected source-side relocation prompt, got "
            f"compatible={result.compatibility_report.compatible} plan={plan}"
        )

    # --- Case 6: Gen 2 Potion → Gen 1 with only one destination available. The source-side
    # plan must still require explicit choice instead of deciding automatically. ---
    can = _can(2, 18, "Potion")
    converter = Gen2ToGen1Converter()
    result = converter.convert(can, _BagFullPcOpenParser(), "party:0", policy="auto_retrocompat")
    plan = converter.inspect_item_relocation(can, _BagFullPcOpenParser(), result.compatibility_report) or {}
    if plan.get("status") == "choose_destination" and list(plan.get("options") or []) == ["pc", "remove"]:
        report.add_pass()
        report.note("Gen 2 Potion → Gen 1 bag full / PC open: trade waits for explicit choice instead of auto-deciding")
    else:
        report.add_fail(
            f"Gen 2 Potion → Gen 1 bag full / PC open: expected explicit choice prompt, got plan={plan}"
        )

    # --- Case 7: Gen 2 Potion → Gen 1 with bag and PC full. The source-side plan must instruct
    # the player to remove the item because there is no storage space left. ---
    can = _can(2, 18, "Potion")
    converter = Gen2ToGen1Converter()
    result = converter.convert(can, _FullInventoryParser(), "party:0", policy="auto_retrocompat")
    plan = converter.inspect_item_relocation(can, _FullInventoryParser(), result.compatibility_report) or {}
    if plan.get("status") == "manual_remove_required" and "remova o item" in str(plan.get("reason") or "").lower():
        report.add_pass()
        report.note("Gen 2 Potion → Gen 1 full bag/PC: trade REFUSED with explicit remove-item guidance")
    else:
        report.add_fail(
            f"Gen 2 Potion → Gen 1 full bag/PC: expected remove-item guidance, got plan={plan}"
        )

    # --- Case 8: Incoming preflight should not ask the receiver to store the sender's item. ---
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "yellow_runtime.sav"
        shutil.copy(TEST_SAVES_ROOT / "gen 1" / "Pokémon - Yellow Version.sav", work)
        payload = {
            "received_payload": {
                "generation": 2,
                "source_generation": 2,
                "canonical": _can(2, 18, "Potion").to_dict(),
                "species_id": 1,
                "species_name": "Bulbasaur",
                "held_item_id": 18,
                "held_item_name": "Potion",
            },
            "target_generation": 1,
            "target_game": "pokemon_yellow",
            "target_save_bytes_base64": base64.b64encode(work.read_bytes()).decode("ascii"),
            "target_save_suffix": ".sav",
        }
        preflight = build_trade_preflight(payload)
        relocation = dict(preflight.get("item_relocation") or {})
        if relocation == {}:
            report.add_pass()
            report.note("Runtime preflight no longer prompts the receiver to store the sender's item")
        else:
            report.add_fail(f"Runtime preflight should not expose receiver-side item relocation: {preflight}")

    # --- Case 9: Outgoing item relocation must use the source save. FireRed Meowth holding
    # Rawst Berry and targeting Gen 1 should offer bag/remove on the FireRed save. ---
    source_path = TEST_SAVES_ROOT / "gen 3" / "Pokémon - FireRed Version.sav"
    meowth_payload = None
    source = Gen3Parser(); source.load(source_path)
    for mon in source.list_party():
        if mon.species_name == "Meowth" and mon.held_item_id:
            meowth_payload = source.export_pokemon(mon.location).to_dict()
            break
    if not meowth_payload:
        report.add_fail("Failed to find FireRed Meowth with held item in real save.")
    else:
        relocation = build_outgoing_item_relocation(
            {
                "sent_payload": meowth_payload,
                "target_generation": 1,
                "source_save_bytes_base64": base64.b64encode(source_path.read_bytes()).decode("ascii"),
                "source_save_suffix": ".sav",
            }
        )
        if relocation.get("status") == "choose_destination" and "bag" in list(relocation.get("options") or []):
            report.add_pass()
            report.note("FireRed Meowth -> Gen 1 offers returning the Rawst Berry to the FireRed save bag")
        else:
            report.add_fail(f"FireRed Meowth outgoing relocation should offer bag/remove, got {relocation}")

    # --- Case 10: Gen 3 duplicate physical slots must not trick has_bag_space into reporting free
    # capacity when the pocket is physically full. ---
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "emerald_dup.sav"
        shutil.copy(TEST_SAVES_ROOT / "gen 3" / "Pokémon - Emerald Version.sav", work)
        target = Gen3Parser(); target.load(work)
        entries = target._read_item_slot_entries("items")
        if len(entries) != 30:
            report.add_fail(f"Emerald items pocket expected full (30 slots), got {len(entries)}")
        else:
            existing_ids = {item_id for item_id, _ in entries}
            new_item_id = 0
            for candidate in range(1, 512):
                if item_exists(candidate, 3) and item_category(candidate, 3) == "item" and candidate not in existing_ids:
                    new_item_id = candidate
                    break
            if new_item_id <= 0:
                report.add_fail("Failed to find a Gen 3 bag item absent from Emerald items pocket.")
            else:
                pocket = inventory_layout_for_game(target.game_id).pocket("items")
                base = target._section1_offset() + pocket.offset
                first_item_id, first_quantity = entries[0]
                last_slot_offset = base + (pocket.capacity - 1) * 4
                key = target._security_key() if pocket.quantity_xor_with_security_key else 0
                target.data[last_slot_offset : last_slot_offset + 2] = int(first_item_id).to_bytes(2, "little")
                target.data[last_slot_offset + 2 : last_slot_offset + 4] = (int(first_quantity) ^ key).to_bytes(2, "little")
                if target.has_bag_space(new_item_id, 1) is False:
                    report.add_pass()
                    report.note("Gen 3 duplicate occupied slot still blocks new bag item when pocket is physically full")
                else:
                    report.add_fail(
                        f"Gen 3 duplicate slot regression: has_bag_space({new_item_id}) returned True on full pocket."
                    )

    return report
