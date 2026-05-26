import struct
from .ereader_battles import get_ereader_battle

from ..data.inventory_layouts import inventory_layout_for_game

GEN3_SECTOR_DATA_SIZE = 0xF80
GEN3_SAVEBLOCK1_SECTION_IDS = (1, 2, 3, 4)
GEN3_RS_EREADER_OFFSET = 0x3030
GEN3_EREADER_SLOT_SIZE = 40
GEN3_EREADER_SLOT_COUNT = 5
# Base do array wEventFlags do Crystal dentro do save (offset de arquivo).
# Confirmado contra a disassembly pret/pokecrystal: a SECTION "Save" é a primeira
# do banco SRAM 1 → arquivo 0x2000; sGameData = 0x2009 (= CRYSTAL_PRIMARY_START).
# wEventFlags fica no bloco wPlayerData; somando o storage do wram.asm de wNumPCItems
# (= pocket pc_items, arquivo 0x247F) até wEventFlags dá +0x181 → 0x2600. Está dentro
# da região com checksum primário (0x2009–0x2B82). (Antes era 0x25FD, 3 bytes
# adiantado, jogando todos os flags no byte errado.)
GEN2_EVENT_FLAGS_OFFSET = 0x2600
GEN2_EVENT_CAN_GIVE_GS_BALL_TO_KURT = 0x0BE
GEN2_EVENT_GAVE_GS_BALL_TO_KURT = 0x0BF
GEN2_EVENT_FOREST_IS_RESTLESS = 0x0C0
GEN2_EVENT_GOT_GS_BALL_FROM_POKECOM_CENTER = 0x340


def apply_event(save_model, event_id: str):
    """Aplica evento de ticket. Não faz backup nem save — responsabilidade do chamador."""
    from .catalog import get_event_by_id

    event = get_event_by_id(event_id)
    if not event:
        return {"success": False, "message": "Evento não encontrado"}

    preflight = preflight_events(save_model, [event_id])
    if not preflight.get("can_apply"):
        event_checks = preflight.get("events") or []
        first_check = event_checks[0] if event_checks else {}
        return {"success": False, "message": first_check.get("message") or preflight.get("message") or "extras_not_supported"}
    if not preflight.get("event_ids_to_apply"):
        return {"success": False, "message": "extras_already_active"}

    item_id = event["item_id"]

    # Obter parser (usar backend se disponível, senão carregar sob demanda)
    parser = _get_parser_for_save(save_model)
    if not parser:
        return {"success": False, "message": "Não foi possível carregar parser"}

    try:
        inventory = parser.list_inventory()
        if any(e.item_id == item_id for e in inventory):
            return {"success": False, "message": "extras_already_active"}
    except Exception:
        pass

    try:
        parser.store_item_in_bag(item_id, 1)
    except Exception as e:
        if "no space" in str(e).lower() or "bag is full" in str(e).lower():
            return {"success": False, "message": "extras_no_space"}
        if "excedeu" in str(e).lower() or "maxima" in str(e).lower():
            return {"success": False, "message": "extras_no_space"}
        return {"success": False, "message": str(e)}

    # Sincronizar dados modificados do parser de volta para SaveModel.bytes
    if hasattr(parser, 'data') and parser.data:
        save_model.bytes[:] = parser.data

    if "flags" in event:
        try:
            flag_ids = _resolve_event_flags(event["flags"], save_model.game)
            if flag_ids:
                _set_event_flags(save_model, flag_ids)
        except Exception as e:
            return {"success": False, "message": f"Erro ao setar flags: {str(e)}"}

    if event.get("target_system") == "gs_ball":
        try:
            _set_gsball_flags(save_model)
        except Exception as e:
            return {"success": False, "message": f"Erro ao setar GS Ball flags: {str(e)}"}

    return {"success": True, "message": "extras_applied"}


def revert_event(save_model, event_id: str):
    """Reverte um evento de ticket: remove o item dado e limpa as flags.

    Inverso de apply_event. Não faz backup nem grava — responsabilidade do chamador.
    """
    from .catalog import get_event_by_id

    event = get_event_by_id(event_id)
    if not event:
        return {"success": False, "message": "Evento não encontrado"}

    parser = _get_parser_for_save(save_model)
    if not parser:
        return {"success": False, "message": "Não foi possível carregar parser"}

    changed = False
    item_id = event.get("item_id")
    if item_id is not None and hasattr(parser, "remove_item_from_bag"):
        try:
            removed = bool(parser.remove_item_from_bag(int(item_id)))
        except Exception as e:
            return {"success": False, "message": str(e)}
        changed = changed or removed
        # Sincronizar dados modificados do parser de volta para SaveModel.bytes
        if hasattr(parser, "data") and parser.data:
            save_model.bytes[:] = parser.data

    if "flags" in event:
        try:
            flag_ids = _resolve_event_flags(event["flags"], save_model.game)
            if flag_ids:
                _clear_event_flags(save_model, flag_ids)
                changed = True
        except Exception as e:
            return {"success": False, "message": f"Erro ao limpar flags: {str(e)}"}

    if event.get("target_system") == "gs_ball":
        try:
            _clear_gsball_flags(save_model)
            changed = True
        except Exception as e:
            return {"success": False, "message": f"Erro ao limpar GS Ball flags: {str(e)}"}

    if not changed:
        return {"success": False, "message": "extras_not_active"}

    return {"success": True, "message": "extras_removed"}


def preflight_event(save_model, event_id: str) -> dict:
    """Valida um evento sem escrever no save."""
    return preflight_events(save_model, [event_id])


def preflight_events(save_model, event_ids=None) -> dict:
    """Valida um lote de tickets e simula uso de bolso antes de qualquer escrita."""
    from .catalog import get_event_by_id, get_events_for_save
    from .official import compatibility_for_save

    if event_ids is None:
        event_ids = [
            event["id"]
            for event in get_events_for_save(save_model)
            if event.get("category") == "ticket"
        ]

    requested_ids = [str(event_id) for event_id in event_ids]
    parser = None
    state = None
    checks = []
    blockers = []
    event_ids_to_apply = []

    for event_id in requested_ids:
        event = get_event_by_id(event_id)
        if not event:
            check = _preflight_block(event_id, "not_found", "Evento não encontrado")
            checks.append(check)
            blockers.append(check)
            continue

        compatibility = compatibility_for_save(save_model, event_id)
        if not compatibility.can_apply:
            check = _preflight_block(event_id, compatibility.reason, compatibility.message or compatibility.reason, event=event)
            checks.append(check)
            blockers.append(check)
            continue

        if event.get("category") != "ticket":
            check = _preflight_block(event_id, "unsupported_category", "Tipo de evento inválido", event=event)
            checks.append(check)
            blockers.append(check)
            continue

        item_id = event.get("item_id")
        if item_id is None:
            check = _preflight_block(event_id, "missing_item_payload", "Evento sem item_id", event=event)
            checks.append(check)
            blockers.append(check)
            continue

        if parser is None:
            parser = _get_parser_for_save(save_model)
            if not parser:
                check = _preflight_block(event_id, "parser_unavailable", "Não foi possível carregar parser", event=event)
                checks.append(check)
                blockers.append(check)
                continue
            state = _inventory_preflight_state(save_model, parser)

        check = _preflight_ticket_inventory(state, event)
        checks.append(check)
        if check["status"] == "will_apply":
            event_ids_to_apply.append(event_id)
        elif check["status"] == "blocked":
            blockers.append(check)

    can_apply = not blockers
    return {
        "success": True,
        "can_apply": can_apply,
        "message": "extras_preflight_ok" if can_apply else "extras_preflight_failed",
        "events": checks,
        "blockers": blockers,
        "event_ids_to_apply": event_ids_to_apply,
        "pockets": state.get("pockets", {}) if state else {},
    }


def _get_parser_for_save(save_model):
    """Obter parser para o save (usar backend ou carregar sob demanda)."""
    # Gen 4 já tem parser backend
    if save_model._backend_parser:
        return save_model._backend_parser

    # Para Gen 1, 2, 3 - carregar sob demanda
    if save_model.generation == 1:
        from pokecable_save import _ensure_backend_import_path
        _ensure_backend_import_path()
        from parsers import Gen1Parser
        parser = Gen1Parser()
        if parser.detect(save_model.path):
            parser.load(save_model.path)
            _sync_parser_from_save_model(parser, save_model)
            return parser

    elif save_model.generation == 2:
        from pokecable_save import _ensure_backend_import_path
        _ensure_backend_import_path()
        from parsers import Gen2Parser
        parser = Gen2Parser()
        if parser.detect(save_model.path):
            parser.load(save_model.path)
            _sync_parser_from_save_model(parser, save_model)
            return parser

    elif save_model.generation == 3:
        from pokecable_save import _ensure_backend_import_path
        _ensure_backend_import_path()
        from parsers import Gen3Parser
        parser = Gen3Parser()
        if parser.detect(save_model.path):
            parser.load(save_model.path)
            _sync_parser_from_save_model(parser, save_model)
            return parser

    return None


def _sync_parser_from_save_model(parser, save_model) -> None:
    if hasattr(parser, "data") and getattr(save_model, "bytes", None):
        parser.data = bytearray(save_model.bytes)


def _inventory_preflight_state(save_model, parser) -> dict:
    inventory = parser.list_inventory()
    item_ids = {int(entry.item_id) for entry in inventory}
    used_by_pocket: dict[str, int] = {}
    for entry in inventory:
        used_by_pocket[str(entry.pocket_name)] = used_by_pocket.get(str(entry.pocket_name), 0) + 1

    capacities = _inventory_capacities(save_model, parser)
    pockets = {
        pocket_name: {
            "used": used_by_pocket.get(pocket_name, 0),
            "capacity": capacity,
            "free": max(0, capacity - used_by_pocket.get(pocket_name, 0)),
        }
        for pocket_name, capacity in capacities.items()
    }
    return {
        "parser": parser,
        "item_ids": set(item_ids),
        "projected_item_ids": set(item_ids),
        "used_by_pocket": dict(used_by_pocket),
        "capacities": capacities,
        "pockets": pockets,
    }


def _inventory_capacities(save_model, parser) -> dict[str, int]:
    if hasattr(parser, "_inventory_capacities"):
        try:
            capacities = parser._inventory_capacities()
            return {str(name): int(capacity) for name, capacity in capacities.items()}
        except Exception:
            pass
    layout = inventory_layout_for_game(save_model.game)
    return {pocket.pocket_name: int(pocket.capacity) for pocket in layout.pockets}


def _preflight_ticket_inventory(state: dict, event: dict) -> dict:
    event_id = str(event["id"])
    item_id = int(event["item_id"])
    parser = state["parser"]
    pocket_name = _pocket_for_event_item(parser, event)

    if item_id in state["item_ids"]:
        return _preflight_ok(event_id, "already_active", "extras_already_active", event, pocket_name)
    if item_id in state["projected_item_ids"]:
        return _preflight_ok(event_id, "already_active", "extras_already_active", event, pocket_name)

    capacities = state["capacities"]
    used_by_pocket = state["used_by_pocket"]
    capacity = capacities.get(pocket_name)
    used = used_by_pocket.get(pocket_name, 0)

    if capacity is not None and used >= capacity:
        return _preflight_block(
            event_id,
            "missing_space",
            "extras_no_space",
            event=event,
            pocket_name=pocket_name,
            pocket_used=used,
            pocket_capacity=capacity,
        )

    if capacity is None:
        try:
            if not parser.has_bag_space(item_id, 1):
                return _preflight_block(event_id, "missing_space", "extras_no_space", event=event, pocket_name=pocket_name)
        except Exception:
            return _preflight_block(event_id, "space_check_failed", "extras_no_space", event=event, pocket_name=pocket_name)

    state["projected_item_ids"].add(item_id)
    used_by_pocket[pocket_name] = used + 1
    if pocket_name in state["pockets"]:
        state["pockets"][pocket_name]["used_after"] = used + 1
        state["pockets"][pocket_name]["free_after"] = max(0, int(capacity or 0) - (used + 1))
    return _preflight_ok(event_id, "will_apply", "extras_preflight_ok", event, pocket_name)


def _pocket_for_event_item(parser, event: dict) -> str:
    if hasattr(parser, "_bag_pocket_for_item"):
        return str(parser._bag_pocket_for_item(int(event["item_id"])))
    storage_target = str(event.get("storage_target") or "")
    if ":" in storage_target:
        return storage_target.split(":", 1)[1]
    return "key_items"


def _preflight_ok(event_id: str, status: str, message: str, event: dict, pocket_name: str | None = None) -> dict:
    result = {
        "event_id": event_id,
        "status": status,
        "can_apply": status == "will_apply",
        "message": message,
        "reason": status,
        "item_id": event.get("item_id"),
        "official_status": event.get("official_status"),
    }
    if pocket_name:
        result["pocket_name"] = pocket_name
    return result


def _preflight_block(
    event_id: str,
    reason: str,
    message: str,
    *,
    event: dict | None = None,
    pocket_name: str | None = None,
    pocket_used: int | None = None,
    pocket_capacity: int | None = None,
) -> dict:
    result = {
        "event_id": event_id,
        "status": "blocked",
        "can_apply": False,
        "reason": reason,
        "message": message,
    }
    if event:
        result["item_id"] = event.get("item_id")
        result["official_status"] = event.get("official_status")
        result["blocked_reason"] = event.get("blocked_reason", "")
    if pocket_name:
        result["pocket_name"] = pocket_name
    if pocket_used is not None:
        result["pocket_used"] = pocket_used
    if pocket_capacity is not None:
        result["pocket_capacity"] = pocket_capacity
    return result


def _game_flag_key(game):
    """Maps a save game id to the per-game flag group used in event payloads."""
    g = (game or "").lower()
    if "firered" in g or "leafgreen" in g:
        return "frlg"
    if "emerald" in g:
        return "emerald"
    if "ruby" in g or "sapphire" in g:
        return "rs"
    return ""


def _resolve_event_flags(flags, game):
    """Resolve event flags to a concrete id list.

    Gen 3 event flag numbers differ per game (FR/LG vs Emerald vs R/S), so a
    payload may provide either a flat list (same ids for every supported game)
    or a dict keyed by game group ('frlg', 'emerald', 'rs', or 'default').
    """
    if isinstance(flags, dict):
        key = _game_flag_key(game)
        selected = flags.get(key)
        if selected is None:
            selected = flags.get("default")
        return list(selected or [])
    return list(flags or [])


def _set_event_flags(save_model, flag_ids):
    """Seta event flags no SaveBlock1 de Gen 3."""
    flag_block_offset = _get_event_flag_offset(save_model)
    for flag_id in flag_ids:
        byte_idx = flag_id // 8
        bit = flag_id % 8
        current = _read_gen3_saveblock1(save_model, flag_block_offset + byte_idx, 1)[0]
        _write_gen3_saveblock1(save_model, flag_block_offset + byte_idx, bytes([current | (1 << bit)]))


def _clear_event_flags(save_model, flag_ids):
    """Limpa event flags no SaveBlock1 de Gen 3 (inverso de _set_event_flags)."""
    flag_block_offset = _get_event_flag_offset(save_model)
    for flag_id in flag_ids:
        byte_idx = flag_id // 8
        bit = flag_id % 8
        current = _read_gen3_saveblock1(save_model, flag_block_offset + byte_idx, 1)[0]
        _write_gen3_saveblock1(save_model, flag_block_offset + byte_idx, bytes([current & ~(1 << bit) & 0xFF]))


def _get_event_flag_offset(save_model):
    """Retorna offset do event flag block baseado no tipo de jogo."""
    game = save_model.game or ""

    if "firered" in game or "leafgreen" in game:
        return 0xEE0
    if "ruby" in game or "sapphire" in game:
        return 0x1220
    else:
        return 0x1270


def _set_gsball_flags(save_model):
    """Seta o estado do evento da GS Ball para o ponto "acabei de receber a bola"."""
    if (save_model.game or "") == "pokemon_crystal":
        _set_gen2_event_flag(save_model, GEN2_EVENT_GOT_GS_BALL_FROM_POKECOM_CENTER)
        _set_gen2_event_flag(save_model, GEN2_EVENT_CAN_GIVE_GS_BALL_TO_KURT)
        _clear_gen2_event_flag(save_model, GEN2_EVENT_GAVE_GS_BALL_TO_KURT)
        _clear_gen2_event_flag(save_model, GEN2_EVENT_FOREST_IS_RESTLESS)
        _recalculate_gen2_checksums(save_model)


def _clear_gsball_flags(save_model):
    """Reverte o estado do evento da GS Ball (inverso de _set_gsball_flags)."""
    if (save_model.game or "") == "pokemon_crystal":
        _clear_gen2_event_flag(save_model, GEN2_EVENT_GOT_GS_BALL_FROM_POKECOM_CENTER)
        _clear_gen2_event_flag(save_model, GEN2_EVENT_CAN_GIVE_GS_BALL_TO_KURT)
        _clear_gen2_event_flag(save_model, GEN2_EVENT_GAVE_GS_BALL_TO_KURT)
        _clear_gen2_event_flag(save_model, GEN2_EVENT_FOREST_IS_RESTLESS)
        _recalculate_gen2_checksums(save_model)


def _recalculate_gen2_checksums(save_model):
    """Recalcula os checksums Gen 2 após editar bytes diretamente em save_model.bytes.

    _set/_clear_gen2_event_flag escrevem direto nos bytes (dentro da região com
    checksum primário), sem recalcular. write_to_disk grava os bytes crus, então é
    aqui que precisamos atualizar o checksum primário e a cópia secundária — senão o
    jogo trata o save como corrompido.
    """
    parser = _get_parser_for_save(save_model)
    if not parser or not hasattr(parser, "recalculate_checksums"):
        return
    if hasattr(parser, "data") and parser.data is not None:
        parser.data[:] = save_model.bytes
    parser.recalculate_checksums()
    if hasattr(parser, "data") and parser.data is not None:
        save_model.bytes[:] = parser.data


def _set_gen2_event_flag(save_model, flag_id: int) -> None:
    byte_idx = flag_id // 8
    bit = flag_id % 8
    offset = GEN2_EVENT_FLAGS_OFFSET + byte_idx
    save_model.bytes[offset] |= 1 << bit


def _clear_gen2_event_flag(save_model, flag_id: int) -> None:
    byte_idx = flag_id // 8
    bit = flag_id % 8
    offset = GEN2_EVENT_FLAGS_OFFSET + byte_idx
    save_model.bytes[offset] &= ~(1 << bit) & 0xFF


def apply_ereader_battle(save_model, slot: int, battle_id: str):
    """Escreve um treinador e-Reader num dos 5 slots do save de Ruby/Sapphire."""
    from .official import compatibility_for_save

    if slot < 0 or slot >= GEN3_EREADER_SLOT_COUNT:
        return {"success": False, "message": "Slot inválido (0-4)"}

    compatibility = compatibility_for_save(save_model, "ereader")
    if not compatibility.can_apply:
        return {"success": False, "message": compatibility.message or "e-Reader só suporta Ruby/Sapphire"}

    battle_data = get_ereader_battle(battle_id)
    if not battle_data:
        return {"success": False, "message": "Batalha não encontrada"}

    try:
        slots = read_ereader_slots(save_model)
        for slot_info in slots:
            if slot_info.get("battle_id") == battle_id:
                return {"success": False, "message": "extras_already_active"}
        current = slots[slot]
        if not current.get("is_empty"):
            return {"success": False, "message": "Slot ocupado"}
        _write_ereader_trainer(save_model, slot, battle_data)
        return {"success": True, "message": "extras_applied", "slot": slot, "battle_id": battle_id}
    except Exception as e:
        return {"success": False, "message": f"Erro ao injetar batalha: {str(e)}"}


def clear_ereader_slot(save_model, slot: int):
    """Zera um slot e-Reader (inverso de apply_ereader_battle). Não faz backup nem grava."""
    from .official import compatibility_for_save

    if slot < 0 or slot >= GEN3_EREADER_SLOT_COUNT:
        return {"success": False, "message": "Slot inválido (0-4)"}

    compatibility = compatibility_for_save(save_model, "ereader")
    if not compatibility.can_apply:
        return {"success": False, "message": compatibility.message or "e-Reader só suporta Ruby/Sapphire"}

    try:
        current = read_ereader_slots(save_model)[slot]
        if current.get("is_empty"):
            return {"success": False, "message": "extras_not_active"}
        offset = GEN3_RS_EREADER_OFFSET + (slot * GEN3_EREADER_SLOT_SIZE)
        save_model.bytes[offset : offset + GEN3_EREADER_SLOT_SIZE] = bytes(GEN3_EREADER_SLOT_SIZE)
        return {"success": True, "message": "extras_removed", "slot": slot}
    except Exception as e:
        return {"success": False, "message": f"Erro ao limpar slot: {str(e)}"}


def _write_ereader_trainer(save_model, slot: int, trainer_data: dict):
    """Escreve struct de 40 bytes no slot e-Reader."""
    offset = GEN3_RS_EREADER_OFFSET + (slot * GEN3_EREADER_SLOT_SIZE)

    name_bytes = trainer_data["name"].encode("ascii", errors="replace")[:7]
    name_bytes = name_bytes + b"\x00" * (7 - len(name_bytes))

    trainer_class = trainer_data.get("trainer_class", 0)

    mons = trainer_data.get("mons", [])

    trainer_struct = bytearray(40)

    trainer_struct[0:7] = name_bytes
    trainer_struct[7] = 0
    trainer_struct[8:10] = struct.pack("<H", trainer_class)
    trainer_struct[10:12] = b"\x00\x00"

    for i in range(4):
        base_offset = 0x1C + (i * 3)
        if i < len(mons):
            species = mons[i].get("species", 0)
            level = mons[i].get("level", 0)
            trainer_struct[base_offset : base_offset + 2] = struct.pack("<H", species)
            trainer_struct[base_offset + 2] = level
        else:
            trainer_struct[base_offset : base_offset + 2] = b"\x00\x00"
            trainer_struct[base_offset + 2] = 0

    save_model.bytes[offset : offset + GEN3_EREADER_SLOT_SIZE] = trainer_struct


def read_ereader_slots(save_model):
    """Lê e interpreta os 5 slots e-Reader de Ruby/Sapphire."""
    slots = []
    for slot in range(GEN3_EREADER_SLOT_COUNT):
        offset = GEN3_RS_EREADER_OFFSET + (slot * GEN3_EREADER_SLOT_SIZE)
        raw = bytes(save_model.bytes[offset : offset + GEN3_EREADER_SLOT_SIZE])
        slot_info = _decode_ereader_slot(raw)
        slot_info["slot"] = slot
        slots.append(slot_info)
    return slots


def _decode_ereader_slot(raw: bytes):
    name = raw[0:7].split(b"\x00")[0].decode("ascii", errors="replace").strip()
    trainer_class = struct.unpack("<H", raw[8:10])[0]
    mons = []
    for idx in range(4):
        base_offset = 0x1C + (idx * 3)
        species = struct.unpack("<H", raw[base_offset : base_offset + 2])[0]
        level = raw[base_offset + 2]
        if species > 0:
            mons.append({"species": species, "level": level})
    is_empty = (
        not name
        and trainer_class == 0
        and not mons
        and (not any(raw) or all(byte in (0x00, 0xFF) for byte in raw))
    )
    battle_id = None
    if not is_empty:
        battle_id = _battle_id_for_slot(name, trainer_class, mons)
    return {
        "name": name if name else "[Empty]",
        "trainer_class": trainer_class,
        "mons_count": len(mons),
        "mons": mons,
        "is_empty": is_empty,
        "battle_id": battle_id,
        "recognized": battle_id is not None,
    }


def _battle_id_for_slot(name: str, trainer_class: int, mons: list[dict]):
    normalized_name = (name or "").upper()
    for battle in _iter_ereader_battles():
        if _battle_signature(battle["name"], battle.get("trainer_class", 0), battle.get("mons", [])) == _battle_signature(
            normalized_name,
            trainer_class,
            mons,
        ):
            return battle["id"]
    return None


def _battle_signature(name: str, trainer_class: int, mons: list[dict]):
    return (
        (name or "").upper()[:7],
        int(trainer_class or 0),
        tuple((int(mon.get("species", 0)), int(mon.get("level", 0))) for mon in mons[:4]),
    )


def _iter_ereader_battles():
    from .ereader_battles import list_ereader_battles

    return list_ereader_battles()


def _gen3_section_offsets(save_model):
    if getattr(save_model, "generation", None) != 3 or not getattr(save_model, "slot", None):
        raise ValueError("SaveModel Gen 3 com slot ativo é obrigatório.")
    section_offsets = save_model.slot.get("section_offsets") or {}
    missing = [section_id for section_id in GEN3_SAVEBLOCK1_SECTION_IDS if section_id not in section_offsets]
    if missing:
        raise ValueError(f"Save Gen 3 incompleto: faltam seções do SaveBlock1 ({', '.join(str(s) for s in missing)}).")
    return {section_id: int(section_offsets[section_id]) for section_id in GEN3_SAVEBLOCK1_SECTION_IDS}


def _read_gen3_saveblock1(save_model, offset: int, size: int) -> bytes:
    if offset < 0 or size < 0:
        raise ValueError("Offset/tamanho inválido.")
    section_offsets = _gen3_section_offsets(save_model)
    if offset + size > GEN3_SECTOR_DATA_SIZE * len(GEN3_SAVEBLOCK1_SECTION_IDS):
        raise ValueError("Leitura fora dos limites do SaveBlock1.")

    out = bytearray()
    remaining = size
    cursor = offset
    while remaining > 0:
        section_index = cursor // GEN3_SECTOR_DATA_SIZE
        local_offset = cursor % GEN3_SECTOR_DATA_SIZE
        chunk_size = min(remaining, GEN3_SECTOR_DATA_SIZE - local_offset)
        section_id = GEN3_SAVEBLOCK1_SECTION_IDS[section_index]
        physical = section_offsets[section_id]
        out.extend(save_model.bytes[physical + local_offset : physical + local_offset + chunk_size])
        remaining -= chunk_size
        cursor += chunk_size
    return bytes(out)


def _write_gen3_saveblock1(save_model, offset: int, payload: bytes) -> None:
    if offset < 0:
        raise ValueError("Offset inválido.")
    section_offsets = _gen3_section_offsets(save_model)
    if offset + len(payload) > GEN3_SECTOR_DATA_SIZE * len(GEN3_SAVEBLOCK1_SECTION_IDS):
        raise ValueError("Escrita fora dos limites do SaveBlock1.")

    from pokecable_save import gen3_sector_checksum, write_u16

    touched = set()
    remaining = len(payload)
    cursor = offset
    payload_cursor = 0
    while remaining > 0:
        section_index = cursor // GEN3_SECTOR_DATA_SIZE
        local_offset = cursor % GEN3_SECTOR_DATA_SIZE
        chunk_size = min(remaining, GEN3_SECTOR_DATA_SIZE - local_offset)
        section_id = GEN3_SAVEBLOCK1_SECTION_IDS[section_index]
        physical = section_offsets[section_id]
        save_model.bytes[physical + local_offset : physical + local_offset + chunk_size] = payload[payload_cursor : payload_cursor + chunk_size]
        touched.add(physical)
        remaining -= chunk_size
        cursor += chunk_size
        payload_cursor += chunk_size

    for physical in touched:
        write_u16(save_model.bytes, physical + 0xFF6, gen3_sector_checksum(save_model.bytes, physical))
