"""Utilitários de edição de save (hex), separados dos eventos oficiais.

Diferente dos tickets/eventos (que reproduzem distribuições oficiais), estes são
ajustes de conveniência aplicados diretamente no save. Por isso têm um caminho de
aplicação próprio, sem o preflight específico de tickets (pockets/item_id).
"""
from __future__ import annotations

SAVE_UTILITIES = [
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
        "id": "mystery_shiny_egg",
        "category": "utility",
        "name_key": "util_mystery_shiny_egg",
        "desc_key": "util_mystery_shiny_egg_desc",
        "generations": (2, 3, 4),
        "action": "mystery_shiny_egg",
    },
    {
        "id": "gen3_mystery_systems",
        "category": "utility",
        "name_key": "util_gen3_mystery_systems",
        "desc_key": "util_gen3_mystery_systems_desc",
        "generations": (3,),
        "action": "gen3_mystery_systems",
    },
    {
        "id": "gen3_altering_cave_reset",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_reset",
        "desc_key": "util_gen3_altering_cave_reset_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 0, "species_name": "Zubat"},
    },
    {
        "id": "gen3_altering_cave_mareep",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_mareep",
        "desc_key": "util_gen3_altering_cave_mareep_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 1, "species_name": "Mareep"},
    },
    {
        "id": "gen3_altering_cave_aipom",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_aipom",
        "desc_key": "util_gen3_altering_cave_aipom_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 2, "species_name": "Aipom"},
    },
    {
        "id": "gen3_altering_cave_pineco",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_pineco",
        "desc_key": "util_gen3_altering_cave_pineco_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 3, "species_name": "Pineco"},
    },
    {
        "id": "gen3_altering_cave_shuckle",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_shuckle",
        "desc_key": "util_gen3_altering_cave_shuckle_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 4, "species_name": "Shuckle"},
    },
    {
        "id": "gen3_altering_cave_teddiursa",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_teddiursa",
        "desc_key": "util_gen3_altering_cave_teddiursa_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 5, "species_name": "Teddiursa"},
    },
    {
        "id": "gen3_altering_cave_houndour",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_houndour",
        "desc_key": "util_gen3_altering_cave_houndour_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 6, "species_name": "Houndour"},
    },
    {
        "id": "gen3_altering_cave_stantler",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_stantler",
        "desc_key": "util_gen3_altering_cave_stantler_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 7, "species_name": "Stantler"},
    },
    {
        "id": "gen3_altering_cave_smeargle",
        "category": "utility",
        "name_key": "util_gen3_altering_cave_smeargle",
        "desc_key": "util_gen3_altering_cave_smeargle_desc",
        "generations": (3,),
        "games": ("pokemon_emerald",),
        "action": "gen3_altering_cave",
        "payload": {"wild_set": 8, "species_name": "Smeargle"},
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

# VAR_ALTERING_CAVE_WILD_SET (pokeemerald include/constants/vars.h = 0x403E).
# Antes estava 0x4024, que é VAR_MIRAGE_RND_H — escrevia na variável errada (RNG da
# Mirage Island), sem mudar o set de wild da Altering Cave. Confirmado na disassembly.
GEN3_ALTERING_CAVE_VAR_ID = 0x403E
GEN3_VARS_START = 0x4000
GEN3_VAR_BASE_BY_GROUP = {
    "emerald": 0x139C,
    "rs": 0x1340,
    "frlg": 0x1000,
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
    game = str(getattr(save_model, "game", "") or "")
    return [
        util
        for util in SAVE_UTILITIES
        if gen in util["generations"]
        and (not util.get("games") or game in tuple(util.get("games") or ()))
    ]


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
    skipped = []
    total_added = 0
    space_tokens = ("no space", "bag is full", "cheio", "excedeu", "stack")
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
            if any(token in message.lower() for token in space_tokens):
                # Melhor-esforço: a bag (sobretudo Gen 1, 20 slots) pode não comportar
                # o kit inteiro. Pula este item e tenta os próximos (itens já presentes
                # ainda recebem top-up mesmo com a bag cheia) em vez de abortar tudo.
                skipped.append(item_id)
                continue
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

    if not changed:
        # Nada coube (bag cheia e nenhum item do kit faltando).
        return {"success": False, "message": "extras_no_space"}

    if hasattr(parser, "data") and parser.data:
        save_model.bytes[:] = parser.data

    return {
        "success": True,
        "message": "extras_applied_partial" if skipped else "extras_applied",
        "changed_items": len(changed),
        "total_quantity_added": total_added,
        "kit_size": len(kit),
        "skipped_items": skipped,
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


def _apply_gen3_altering_cave(save_model, util):
    from .applicator import _read_gen3_saveblock1, _write_gen3_saveblock1

    if getattr(save_model, "generation", None) != 3 or str(getattr(save_model, "game", "") or "") != "pokemon_emerald":
        return {"success": False, "message": "extras_not_supported"}

    payload = dict(util.get("payload") or {})
    wild_set = int(payload.get("wild_set", 0))
    species_name = str(payload.get("species_name") or "")
    if wild_set < 0 or wild_set > 8:
        return {"success": False, "message": "extras_not_supported"}

    group = _gen3_game_group(save_model)
    var_base = GEN3_VAR_BASE_BY_GROUP.get(group)
    if var_base is None:
        return {"success": False, "message": "extras_not_supported"}

    var_index = GEN3_ALTERING_CAVE_VAR_ID - GEN3_VARS_START
    var_offset = var_base + var_index * 2
    current = int.from_bytes(_read_gen3_saveblock1(save_model, var_offset, 2), "little")
    if current == wild_set:
        return {
            "success": True,
            "message": "extras_already_active",
            "game_group": group,
            "var_id": GEN3_ALTERING_CAVE_VAR_ID,
            "var_value": wild_set,
            "species_name": species_name,
        }

    _write_gen3_saveblock1(save_model, var_offset, wild_set.to_bytes(2, "little"))
    return {
        "success": True,
        "message": "extras_applied",
        "game_group": group,
        "var_id": GEN3_ALTERING_CAVE_VAR_ID,
        "var_value": wild_set,
        "species_name": species_name,
    }


# Utilitários cujos efeitos têm um inverso bem definido (podem ser "destogglados").
# Os demais (complete_pokedex, gen1_money_coins, give_items_kit, gen3_national_dex)
# são edições one-way: não guardam o estado anterior, então não podem ser revertidos
# de forma confiável.
REVERSIBLE_UTILITY_ACTIONS = {"gen3_mystery_systems", "gen3_altering_cave"}


def is_utility_reversible(util_id) -> bool:
    util = get_save_utility(util_id)
    return bool(util and util["action"] in REVERSIBLE_UTILITY_ACTIONS)


def is_utility_active(save_model, util_id) -> bool:
    """Detecta se um utilitário reversível já está aplicado no save."""
    util = get_save_utility(util_id)
    if not util or util["action"] not in REVERSIBLE_UTILITY_ACTIONS:
        return False
    try:
        if util["action"] == "gen3_mystery_systems":
            return _gen3_mystery_systems_active(save_model)
        if util["action"] == "gen3_altering_cave":
            return _gen3_altering_cave_active(save_model, util)
    except Exception:
        return False
    return False


def _gen3_mystery_systems_active(save_model) -> bool:
    from .applicator import _get_event_flag_offset, _read_gen3_saveblock1

    if getattr(save_model, "generation", None) != 3:
        return False
    group = _gen3_game_group(save_model)
    flag_ids = GEN3_MYSTERY_SYSTEM_FLAGS.get(group)
    if not flag_ids:
        return False
    flag_block_offset = _get_event_flag_offset(save_model)
    for flag_id in flag_ids:
        byte_idx = flag_id // 8
        bit = flag_id % 8
        current = _read_gen3_saveblock1(save_model, flag_block_offset + byte_idx, 1)[0]
        if not (current & (1 << bit)):
            return False
    return True


def _gen3_altering_cave_active(save_model, util) -> bool:
    from .applicator import _read_gen3_saveblock1

    if getattr(save_model, "generation", None) != 3 or str(getattr(save_model, "game", "") or "") != "pokemon_emerald":
        return False
    group = _gen3_game_group(save_model)
    var_base = GEN3_VAR_BASE_BY_GROUP.get(group)
    if var_base is None:
        return False
    wild_set = int(dict(util.get("payload") or {}).get("wild_set", 0))
    var_index = GEN3_ALTERING_CAVE_VAR_ID - GEN3_VARS_START
    var_offset = var_base + var_index * 2
    current = int.from_bytes(_read_gen3_saveblock1(save_model, var_offset, 2), "little")
    # wild_set 0 (Zubat) é o estado padrão do jogo, não conta como "ativado".
    return current != 0 and current == wild_set


def revert_utility(save_model, util_id):
    """Reverte um utilitário reversível. Não faz backup nem grava em disco."""
    util = get_save_utility(util_id)
    if not util:
        return {"success": False, "message": "Utilitário não encontrado"}
    action = util["action"]
    if action not in REVERSIBLE_UTILITY_ACTIONS:
        return {"success": False, "message": "extras_not_reversible"}
    try:
        if action == "gen3_mystery_systems":
            return _revert_gen3_mystery_systems(save_model)
        if action == "gen3_altering_cave":
            return _revert_gen3_altering_cave(save_model, util)
        return {"success": False, "message": "extras_not_reversible"}
    except Exception as exc:  # noqa: BLE001 - reportar mensagem ao chamador
        return {"success": False, "message": str(exc)[:120]}


def _revert_gen3_mystery_systems(save_model):
    from .applicator import _clear_event_flags

    if getattr(save_model, "generation", None) != 3:
        return {"success": False, "message": "extras_not_supported"}
    group = _gen3_game_group(save_model)
    flag_ids = GEN3_MYSTERY_SYSTEM_FLAGS.get(group)
    if not flag_ids:
        return {"success": False, "message": "extras_not_supported"}
    _clear_event_flags(save_model, flag_ids)
    return {"success": True, "message": "extras_removed", "game_group": group, "flag_ids": list(flag_ids)}


def _revert_gen3_altering_cave(save_model, util):
    from .applicator import _read_gen3_saveblock1, _write_gen3_saveblock1

    if getattr(save_model, "generation", None) != 3 or str(getattr(save_model, "game", "") or "") != "pokemon_emerald":
        return {"success": False, "message": "extras_not_supported"}
    group = _gen3_game_group(save_model)
    var_base = GEN3_VAR_BASE_BY_GROUP.get(group)
    if var_base is None:
        return {"success": False, "message": "extras_not_supported"}
    var_index = GEN3_ALTERING_CAVE_VAR_ID - GEN3_VARS_START
    var_offset = var_base + var_index * 2
    _write_gen3_saveblock1(save_model, var_offset, (0).to_bytes(2, "little"))
    return {
        "success": True,
        "message": "extras_removed",
        "game_group": group,
        "var_id": GEN3_ALTERING_CAVE_VAR_ID,
        "var_value": 0,
    }


def apply_utility(save_model, util_id):
    """Aplica um utilitário no save_model (não faz backup nem grava em disco)."""
    util = get_save_utility(util_id)
    if not util:
        return {"success": False, "message": "Utilitário não encontrado"}
    if getattr(save_model, "generation", None) not in util["generations"]:
        return {"success": False, "message": "extras_not_supported"}
    if util.get("games") and str(getattr(save_model, "game", "") or "") not in tuple(util.get("games") or ()):
        return {"success": False, "message": "extras_not_supported"}

    action = util["action"]
    try:
        if action == "gen1_money_coins":
            result = save_model.give_gen1_money_coins()
            return {"success": True, "message": "extras_applied", **result}
        if action == "give_items_kit":
            return _apply_give_items_kit(save_model)
        if action == "mystery_shiny_egg":
            from .mystery_egg import apply_mystery_shiny_egg

            return apply_mystery_shiny_egg(save_model)
        if action == "gen3_mystery_systems":
            return _apply_gen3_mystery_systems(save_model)
        if action == "gen3_altering_cave":
            return _apply_gen3_altering_cave(save_model, util)
        return {"success": False, "message": f"Ação desconhecida: {action}"}
    except Exception as exc:  # noqa: BLE001 - reportar mensagem ao chamador
        return {"success": False, "message": str(exc)[:120]}
