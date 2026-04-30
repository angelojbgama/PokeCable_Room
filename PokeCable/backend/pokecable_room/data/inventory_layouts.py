from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

InventoryEncoding = Literal[
    "counted_item_pairs_u8",
    "counted_item_ids",
    "tmhm_quantity_array",
    "item_slots_u16_quantity_u16",
    "pc_item_slots_u16_quantity_u16",
]


@dataclass(frozen=True, slots=True)
class InventoryPocketLayout:
    generation: int
    game_family: str
    pocket_name: str
    storage: Literal["bag", "pc"]
    offset: int
    size: int
    capacity: int
    encoding: InventoryEncoding
    quantity_xor_with_security_key: bool
    notes: str = ""


@dataclass(frozen=True, slots=True)
class GameInventoryLayout:
    generation: int
    game_family: str
    game_ids: tuple[str, ...]
    pockets: tuple[InventoryPocketLayout, ...]
    source_notes: tuple[str, ...]

    def pocket(self, pocket_name: str) -> InventoryPocketLayout:
        for pocket in self.pockets:
            if pocket.pocket_name == pocket_name:
                return pocket
        raise KeyError(f"Pocket desconhecido para {self.game_family}: {pocket_name}")


GEN1_RBY_LAYOUT = GameInventoryLayout(
    generation=1,
    game_family="gen1_rby",
    game_ids=("pokemon_red", "pokemon_blue", "pokemon_yellow"),
    pockets=(
        InventoryPocketLayout(
            generation=1,
            game_family="gen1_rby",
            pocket_name="bag_items",
            storage="bag",
            offset=0x25C9,
            size=0x2A,
            capacity=20,
            encoding="counted_item_pairs_u8",
            quantity_xor_with_security_key=False,
            notes="Lista de itens principal; formato count + pares item/quantidade + terminador.",
        ),
        InventoryPocketLayout(
            generation=1,
            game_family="gen1_rby",
            pocket_name="pc_items",
            storage="pc",
            offset=0x27E6,
            size=0x68,
            capacity=50,
            encoding="counted_item_pairs_u8",
            quantity_xor_with_security_key=False,
            notes="Itens do PC; Bulbapedia documenta capacidade 50. O bloco salvo ocupa 0x68 bytes.",
        ),
    ),
    source_notes=(
        "Bulbapedia: Save data structure (Generation I)",
        "pret/pokered ram/wram.asm (wNumBagItems/wBagItems, wNumBoxItems/wBoxItems)",
    ),
)


GEN2_GS_LAYOUT = GameInventoryLayout(
    generation=2,
    game_family="gen2_gold_silver",
    game_ids=("pokemon_gold", "pokemon_silver"),
    pockets=(
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_gold_silver",
            pocket_name="tm_hm",
            storage="bag",
            offset=0x23E6,
            size=57,
            capacity=57,
            encoding="tmhm_quantity_array",
            quantity_xor_with_security_key=False,
            notes="50 bytes de TM01..TM50 + 7 bytes de HM01..HM07.",
        ),
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_gold_silver",
            pocket_name="items",
            storage="bag",
            offset=0x241F,
            size=42,
            capacity=20,
            encoding="counted_item_pairs_u8",
            quantity_xor_with_security_key=False,
            notes="Pocket principal; count + pares item/quantidade + terminador.",
        ),
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_gold_silver",
            pocket_name="key_items",
            storage="bag",
            offset=0x2449,
            size=27,
            capacity=26,
            encoding="counted_item_ids",
            quantity_xor_with_security_key=False,
            notes="Key Items nao usam quantidade aqui; count + ids + terminador.",
        ),
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_gold_silver",
            pocket_name="balls",
            storage="bag",
            offset=0x2464,
            size=26,
            capacity=12,
            encoding="counted_item_pairs_u8",
            quantity_xor_with_security_key=False,
            notes="Ball pocket; count + pares item/quantidade + terminador.",
        ),
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_gold_silver",
            pocket_name="pc_items",
            storage="pc",
            offset=0x247E,
            size=102,
            capacity=50,
            encoding="counted_item_pairs_u8",
            quantity_xor_with_security_key=False,
            notes="Itens guardados no PC.",
        ),
    ),
    source_notes=(
        "Bulbapedia: Save data structure in Generation II",
        "pret/pokecrystal ram/wram.asm (wTMsHMs, wNumItems, wNumKeyItems, wNumBalls, wNumPCItems)",
    ),
)


GEN2_CRYSTAL_LAYOUT = GameInventoryLayout(
    generation=2,
    game_family="gen2_crystal",
    game_ids=("pokemon_crystal",),
    pockets=(
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_crystal",
            pocket_name="tm_hm",
            storage="bag",
            offset=0x23E7,
            size=57,
            capacity=57,
            encoding="tmhm_quantity_array",
            quantity_xor_with_security_key=False,
            notes="50 bytes de TM01..TM50 + 7 bytes de HM01..HM07.",
        ),
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_crystal",
            pocket_name="items",
            storage="bag",
            offset=0x2420,
            size=42,
            capacity=20,
            encoding="counted_item_pairs_u8",
            quantity_xor_with_security_key=False,
            notes="Pocket principal; count + pares item/quantidade + terminador.",
        ),
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_crystal",
            pocket_name="key_items",
            storage="bag",
            offset=0x244A,
            size=27,
            capacity=26,
            encoding="counted_item_ids",
            quantity_xor_with_security_key=False,
            notes="Key Items nao usam quantidade aqui; count + ids + terminador.",
        ),
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_crystal",
            pocket_name="balls",
            storage="bag",
            offset=0x2465,
            size=26,
            capacity=12,
            encoding="counted_item_pairs_u8",
            quantity_xor_with_security_key=False,
            notes="Ball pocket; count + pares item/quantidade + terminador.",
        ),
        InventoryPocketLayout(
            generation=2,
            game_family="gen2_crystal",
            pocket_name="pc_items",
            storage="pc",
            offset=0x247F,
            size=102,
            capacity=50,
            encoding="counted_item_pairs_u8",
            quantity_xor_with_security_key=False,
            notes="Itens guardados no PC.",
        ),
    ),
    source_notes=(
        "Bulbapedia: Save data structure in Generation II",
        "pret/pokecrystal ram/wram.asm (wTMsHMs, wNumItems, wNumKeyItems, wNumBalls, wNumPCItems)",
    ),
)


GEN3_RS_LAYOUT = GameInventoryLayout(
    generation=3,
    game_family="gen3_ruby_sapphire",
    game_ids=("pokemon_ruby", "pokemon_sapphire"),
    pockets=(
        InventoryPocketLayout(3, "gen3_ruby_sapphire", "pc_items", "pc", 0x0498, 200, 50, "pc_item_slots_u16_quantity_u16", False),
        InventoryPocketLayout(3, "gen3_ruby_sapphire", "items", "bag", 0x0560, 80, 20, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_ruby_sapphire", "key_items", "bag", 0x05B0, 80, 20, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_ruby_sapphire", "balls", "bag", 0x0600, 64, 16, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_ruby_sapphire", "tm_hm", "bag", 0x0640, 256, 64, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_ruby_sapphire", "berries", "bag", 0x0740, 184, 46, "item_slots_u16_quantity_u16", True),
    ),
    source_notes=(
        "Bulbapedia: Save data structure in Generation III",
        "pret/pokeemerald include/global.h (layout estrutural do SaveBlock1; offsets equivalentes em R/S para Section 1)",
    ),
)


GEN3_EMERALD_LAYOUT = GameInventoryLayout(
    generation=3,
    game_family="gen3_emerald",
    game_ids=("pokemon_emerald",),
    pockets=(
        InventoryPocketLayout(3, "gen3_emerald", "pc_items", "pc", 0x0498, 200, 50, "pc_item_slots_u16_quantity_u16", False),
        InventoryPocketLayout(3, "gen3_emerald", "items", "bag", 0x0560, 120, 30, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_emerald", "key_items", "bag", 0x05D8, 120, 30, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_emerald", "balls", "bag", 0x0650, 64, 16, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_emerald", "tm_hm", "bag", 0x0690, 256, 64, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_emerald", "berries", "bag", 0x0790, 184, 46, "item_slots_u16_quantity_u16", True),
    ),
    source_notes=(
        "Bulbapedia: Save data structure in Generation III",
        "pret/pokeemerald include/global.h struct SaveBlock1",
    ),
)


GEN3_FRLG_LAYOUT = GameInventoryLayout(
    generation=3,
    game_family="gen3_frlg",
    game_ids=("pokemon_firered", "pokemon_leafgreen"),
    pockets=(
        InventoryPocketLayout(3, "gen3_frlg", "pc_items", "pc", 0x0298, 120, 30, "pc_item_slots_u16_quantity_u16", False),
        InventoryPocketLayout(3, "gen3_frlg", "items", "bag", 0x0310, 168, 42, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_frlg", "key_items", "bag", 0x03B8, 120, 30, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_frlg", "balls", "bag", 0x0430, 52, 13, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_frlg", "tm_hm", "bag", 0x0464, 232, 58, "item_slots_u16_quantity_u16", True),
        InventoryPocketLayout(3, "gen3_frlg", "berries", "bag", 0x054C, 172, 43, "item_slots_u16_quantity_u16", True),
    ),
    source_notes=(
        "Bulbapedia: Save data structure in Generation III",
        "FRLG usa o mesmo formato de item entry de Gen 3, com offsets/capacidades especificos.",
    ),
)


ALL_GAME_INVENTORY_LAYOUTS: tuple[GameInventoryLayout, ...] = (
    GEN1_RBY_LAYOUT,
    GEN2_GS_LAYOUT,
    GEN2_CRYSTAL_LAYOUT,
    GEN3_RS_LAYOUT,
    GEN3_EMERALD_LAYOUT,
    GEN3_FRLG_LAYOUT,
)

INVENTORY_LAYOUTS_BY_GAME_ID: dict[str, GameInventoryLayout] = {
    game_id: layout
    for layout in ALL_GAME_INVENTORY_LAYOUTS
    for game_id in layout.game_ids
}


def inventory_layout_for_game(game_id: str) -> GameInventoryLayout:
    try:
        return INVENTORY_LAYOUTS_BY_GAME_ID[str(game_id)]
    except KeyError as exc:
        raise KeyError(f"Layout de inventario nao mapeado para {game_id!r}.") from exc


def inventory_pocket_for_game(game_id: str, pocket_name: str) -> InventoryPocketLayout:
    return inventory_layout_for_game(game_id).pocket(pocket_name)
