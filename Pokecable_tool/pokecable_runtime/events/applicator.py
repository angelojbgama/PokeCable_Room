import struct
from .ereader_battles import get_ereader_battle, list_ereader_battles


def apply_event(save_model, event_id: str):
    """Aplica evento de ticket. Não faz backup nem save — responsabilidade do chamador."""
    from .catalog import get_event_by_id

    event = get_event_by_id(event_id)
    if not event:
        return {"success": False, "message": "Evento não encontrado"}

    if event["category"] != "ticket":
        return {"success": False, "message": "Tipo de evento inválido"}

    parser = save_model._backend_parser
    if not parser:
        return {"success": False, "message": "Parser não disponível"}

    item_id = event["item_id"]

    try:
        parser.store_item_in_bag(item_id, 1)
    except Exception as e:
        if "already in bag" in str(e).lower():
            return {"success": False, "message": "extras_already_active"}
        if "no space" in str(e).lower() or "bag is full" in str(e).lower():
            return {"success": False, "message": "extras_no_space"}
        return {"success": False, "message": str(e)}

    if "flags" in event:
        try:
            _set_event_flags(parser, event["flags"])
        except Exception as e:
            return {"success": False, "message": f"Erro ao setar flags: {str(e)}"}

    if event_id == "gen2_gsball":
        try:
            _set_gsball_flags(parser)
        except Exception as e:
            return {"success": False, "message": f"Erro ao setar GS Ball flags: {str(e)}"}

    return {"success": True, "message": "extras_applied"}


def _set_event_flags(parser, flag_ids):
    """Seta event flags no SaveBlock1 de Gen 3."""
    data = parser._require_data()

    flag_block_offset = _get_event_flag_offset(parser)

    for flag_id in flag_ids:
        byte_idx = flag_id // 8
        bit = flag_id % 8
        data[flag_block_offset + byte_idx] |= 1 << bit


def _get_event_flag_offset(parser):
    """Retorna offset do event flag block baseado no tipo de jogo."""
    game_code = parser.game_code if hasattr(parser, "game_code") else None

    if game_code in ["BPEE", "BPRE"]:
        return 0xEE0

    if game_code in ["AXPE", "AXVE"]:
        return 0xEE0

    if game_code in ["BPSE", "BPGE"]:
        return 0x12B8

    return 0x1270


def _set_gsball_flags(parser):
    """Seta GS Ball flags específicos do Crystal."""
    data = parser._require_data()
    data[0x3E3C] = 0x0B
    data[0x3E44] = 0x0B


def apply_ereader_battle(save_model, slot: int, battle_id: str):
    """Escreve um treinador e-Reader num dos 5 slots do save de Ruby/Sapphire."""
    if slot < 0 or slot > 4:
        return {"success": False, "message": "Slot inválido (0-4)"}

    battle_data = get_ereader_battle(battle_id)
    if not battle_data:
        return {"success": False, "message": "Batalha não encontrada"}

    parser = save_model._backend_parser
    if not parser:
        return {"success": False, "message": "Parser não disponível"}

    try:
        _write_ereader_trainer(parser, slot, battle_data)
        return {"success": True, "message": "extras_applied"}
    except Exception as e:
        return {"success": False, "message": f"Erro ao injetar batalha: {str(e)}"}


def _write_ereader_trainer(parser, slot: int, trainer_data: dict):
    """Escreve struct de 40 bytes no slot e-Reader."""
    data = parser._require_data()

    offset = 0x3030 + (slot * 40)

    name_bytes = trainer_data["name"].encode("ascii", errors="replace")[:7]
    name_bytes = name_bytes + b"\x00" * (7 - len(name_bytes))

    trainer_class = trainer_data.get("trainer_class", 0)

    mons = trainer_data.get("mons", [])

    trainer_struct = bytearray(40)

    trainer_struct[0:7] = name_bytes
    trainer_struct[7] = 0
    trainer_struct[8:10] = struct.pack("<H", trainer_class)
    trainer_struct[10:12] = b"\x00\x00"

    for i in range(6):
        base_offset = 0x1C + (i * 3)
        if i < len(mons):
            species = mons[i].get("species", 0)
            level = mons[i].get("level", 0)
            trainer_struct[base_offset : base_offset + 2] = struct.pack("<H", species)
            trainer_struct[base_offset + 2] = level
        else:
            trainer_struct[base_offset : base_offset + 2] = b"\x00\x00"
            trainer_struct[base_offset + 2] = 0

    data[offset : offset + 40] = trainer_struct
