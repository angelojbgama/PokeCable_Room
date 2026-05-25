"""Utilitários de edição de save (hex), separados dos eventos oficiais.

Diferente dos tickets/eventos (que reproduzem distribuições oficiais), estes são
ajustes de conveniência aplicados diretamente no save. Por isso têm um caminho de
aplicação próprio, sem o preflight específico de tickets (pockets/item_id).
"""
from __future__ import annotations

SAVE_UTILITIES = [
    {
        "id": "pokedex_complete",
        "category": "utility",
        "name_key": "util_pokedex_complete",
        "desc_key": "util_pokedex_complete_desc",
        "generations": (1, 2, 3),
        "action": "complete_pokedex",
    },
    {
        "id": "gen1_money_coins",
        "category": "utility",
        "name_key": "util_gen1_money_coins",
        "desc_key": "util_gen1_money_coins_desc",
        "generations": (1,),
        "action": "gen1_money_coins",
    },
    {
        "id": "give_items_kit",
        "category": "utility",
        "name_key": "util_give_items_kit",
        "desc_key": "util_give_items_kit_desc",
        "generations": (1, 2),
        "action": "give_items_kit",
    },
    {
        "id": "gen3_national_dex",
        "category": "utility",
        "name_key": "util_gen3_national_dex",
        "desc_key": "util_gen3_national_dex_desc",
        "generations": (3,),
        "action": "gen3_national_dex",
    },
    {
        "id": "gen3_mystery_systems",
        "category": "utility",
        "name_key": "util_gen3_mystery_systems",
        "desc_key": "util_gen3_mystery_systems_desc",
        "generations": (3,),
        "action": "gen3_mystery_systems",
    },
]


GIVE_ITEMS_KIT_BY_GENERATION = {
    1: (
        {"item_id": 1, "quantity": 99},    # Master Ball
        {"item_id": 40, "quantity": 99},   # Rare Candy
        {"item_id": 16, "quantity": 50},   # Full Restore
        {"item_id": 54, "quantity": 50},   # Max Revive
        {"item_id": 57, "quantity": 50},   # Max Repel
        {"item_id": 35, "quantity": 10},   # HP Up
        {"item_id": 36, "quantity": 10},   # Protein
        {"item_id": 37, "quantity": 10},   # Iron
        {"item_id": 38, "quantity": 10},   # Carbos
        {"item_id": 39, "quantity": 10},   # Calcium
        {"item_id": 10, "quantity": 5},    # Moon Stone
        {"item_id": 32, "quantity": 5},    # Fire Stone
        {"item_id": 33, "quantity": 5},    # Thunderstone
        {"item_id": 34, "quantity": 5},    # Water Stone
        {"item_id": 47, "quantity": 5},    # Leaf Stone
        {"item_id": 196, "quantity": 1},   # HM01
        {"item_id": 197, "quantity": 1},   # HM02
        {"item_id": 198, "quantity": 1},   # HM03
        {"item_id": 199, "quantity": 1},   # HM04
        {"item_id": 200, "quantity": 1},   # HM05
    ),
    2: (
        {"item_id": 1, "quantity": 99},    # Master Ball
        {"item_id": 32, "quantity": 99},   # Rare Candy
        {"item_id": 14, "quantity": 50},   # Full Restore
        {"item_id": 40, "quantity": 50},   # Max Revive
        {"item_id": 43, "quantity": 50},   # Max Repel
        {"item_id": 19, "quantity": 20},   # Escape Rope
        {"item_id": 26, "quantity": 10},   # HP Up
        {"item_id": 27, "quantity": 10},   # Protein
        {"item_id": 28, "quantity": 10},   # Iron
        {"item_id": 29, "quantity": 10},   # Carbos
        {"item_id": 31, "quantity": 10},   # Calcium
        {"item_id": 8, "quantity": 5},     # Moon Stone
        {"item_id": 22, "quantity": 5},    # Fire Stone
        {"item_id": 23, "quantity": 5},    # Thunderstone
        {"item_id": 24, "quantity": 5},    # Water Stone
        {"item_id": 34, "quantity": 5},    # Leaf Stone
        {"item_id": 169, "quantity": 5},   # Sun Stone
        {"item_id": 82, "quantity": 5},    # King's Rock
        {"item_id": 143, "quantity": 5},   # Metal Coat
        {"item_id": 151, "quantity": 5},   # Dragon Scale
        {"item_id": 172, "quantity": 5},   # Up-Grade
        {"item_id": 243, "quantity": 1},   # HM01
        {"item_id": 244, "quantity": 1},   # HM02
        {"item_id": 245, "quantity": 1},   # HM03
        {"item_id": 246, "quantity": 1},   # HM04
        {"item_id": 247, "quantity": 1},   # HM05
        {"item_id": 248, "quantity": 1},   # HM06
        {"item_id": 249, "quantity": 1},   # HM07
    ),
}


GEN3_MYSTERY_SYSTEM_FLAGS = {
    "frlg": (
        0x839,  # FLAG_SYS_MYSTERY_GIFT_ENABLED
    ),
    "rs": (
        0x84C,  # FLAG_SYS_EXDATA_ENABLE / Mystery Event
    ),
    "emerald": (
        0x8AC,  # FLAG_SYS_MYSTERY_EVENT_ENABLE
        0x8DB,  # FLAG_SYS_MYSTERY_GIFT_ENABLE
    ),
}


def list_save_utilities():
    return list(SAVE_UTILITIES)


def get_save_utility(util_id):
    for util in SAVE_UTILITIES:
        if util["id"] == util_id:
            return util
    return None


def get_available_utilities_for_save(save_model):
    gen = getattr(save_model, "generation", None)
    return [util for util in SAVE_UTILITIES if gen in util["generations"]]


def _current_bag_quantities(parser):
    quantities = {}
    for entry in parser.list_inventory():
        if getattr(entry, "storage", "") != "bag":
            continue
        item_id = int(entry.item_id)
        quantities[item_id] = quantities.get(item_id, 0) + int(entry.quantity or 0)
    return quantities


def _apply_give_items_kit(save_model):
    from pokecable_save import _ensure_backend_import_path

    _ensure_backend_import_path()
    from ..data.items import item_exists, item_name
    from .applicator import _get_parser_for_save

    generation = int(getattr(save_model, "generation", 0) or 0)
    kit = GIVE_ITEMS_KIT_BY_GENERATION.get(generation)
    if not kit:
        return {"success": False, "message": "extras_not_supported"}

    parser = _get_parser_for_save(save_model)
    if not parser:
        return {"success": False, "message": "Não foi possível carregar parser"}

    for spec in kit:
        item_id = int(spec["item_id"])
        if not item_exists(item_id, generation):
            return {"success": False, "message": f"Item inválido Gen {generation}: {item_id}"}

    changed = []
    total_added = 0
    current_quantities = _current_bag_quantities(parser)
    for spec in kit:
        item_id = int(spec["item_id"])
        target_quantity = int(spec["quantity"])
        current_quantity = int(current_quantities.get(item_id, 0))
        missing_quantity = max(0, target_quantity - current_quantity)
        if missing_quantity <= 0:
            continue
        try:
            result = parser.store_item_in_bag(item_id, missing_quantity)
        except Exception as exc:  # noqa: BLE001 - surface user-facing save edit errors
            message = str(exc)
            lowered = message.lower()
            if any(token in lowered for token in ("no space", "bag is full", "cheio", "excedeu", "stack")):
                return {"success": False, "message": "extras_no_space", "item_id": item_id}
            return {"success": False, "message": message[:120], "item_id": item_id}
        current_quantities[item_id] = current_quantity + missing_quantity
        total_added += missing_quantity
        changed.append(
            {
                "item_id": item_id,
                "name": item_name(item_id, generation) or f"Item #{item_id}",
                "quantity": target_quantity,
                "quantity_added": missing_quantity,
                "pocket_name": getattr(result, "pocket_name", ""),
            }
        )

    if hasattr(parser, "data") and parser.data:
        save_model.bytes[:] = parser.data

    return {
        "success": True,
        "message": "extras_applied",
        "changed_items": len(changed),
        "total_quantity_added": total_added,
        "kit_size": len(kit),
        "items": changed,
    }


def _gen3_game_group(save_model):
    game = (getattr(save_model, "game", "") or "").lower()
    if "firered" in game or "leafgreen" in game:
        return "frlg"
    if "ruby" in game or "sapphire" in game:
        return "rs"
    return "emerald"


def _apply_gen3_mystery_systems(save_model):
    from .applicator import _set_event_flags

    if getattr(save_model, "generation", None) != 3:
        return {"success": False, "message": "extras_not_supported"}

    group = _gen3_game_group(save_model)
    flag_ids = GEN3_MYSTERY_SYSTEM_FLAGS.get(group)
    if not flag_ids:
        return {"success": False, "message": "extras_not_supported"}

    _set_event_flags(save_model, flag_ids)
    return {
        "success": True,
        "message": "extras_applied",
        "game_group": group,
        "flag_ids": list(flag_ids),
    }


def apply_utility(save_model, util_id):
    """Aplica um utilitário no save_model (não faz backup nem grava em disco)."""
    util = get_save_utility(util_id)
    if not util:
        return {"success": False, "message": "Utilitário não encontrado"}
    if getattr(save_model, "generation", None) not in util["generations"]:
        return {"success": False, "message": "extras_not_supported"}

    action = util["action"]
    try:
        if action == "complete_pokedex":
            count = save_model.complete_pokedex()
            return {"success": True, "message": "extras_applied", "count": count}
        if action == "gen1_money_coins":
            result = save_model.give_gen1_money_coins()
            return {"success": True, "message": "extras_applied", **result}
        if action == "give_items_kit":
            return _apply_give_items_kit(save_model)
        if action == "gen3_national_dex":
            result = save_model.enable_national_dex()
            return {"success": True, "message": "extras_applied", **result}
        if action == "gen3_mystery_systems":
            return _apply_gen3_mystery_systems(save_model)
        return {"success": False, "message": f"Ação desconhecida: {action}"}
    except Exception as exc:  # noqa: BLE001 - reportar mensagem ao chamador
        return {"success": False, "message": str(exc)[:120]}
