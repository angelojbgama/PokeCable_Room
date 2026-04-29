from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pokecable_room.canonical import CanonicalPokemon
from pokecable_room.compatibility import build_compatibility_report, supported_modes_for_generation
from pokecable_room.compatibility.matrix import (
    SAME_GENERATION,
    UNSUPPORTED,
    get_trade_mode,
)
from pokecable_room.converters import get_converter
from pokecable_room.data.items import equivalent_item_id
from pokecable_room.data.species import national_to_native
from pokecable_room.evolutions import apply_trade_evolution_to_parser, preview_trade_evolution
from pokecable_room.logs import setup_logging
from pokecable_room.network import PokeCableNetworkClient
from pokecable_room.parsers.base import PokemonPayload
from pokecable_room.backups import capture_save_signature, create_backup, list_backups, restore_backup, save_signature_matches
from pokecable_room.saves import detect_parser, find_save_files, load_config, save_config
from pokecable_room.showdown import canonical_team_to_showdown_text, format_id_for_generation
from pokecable_room.trade import validate_payload_for_local_save
from pokecable_room.ui import TerminalUI


logger = logging.getLogger("pokecable.client")

RAW_SAME_GENERATION_PROTOCOL = "raw_same_generation"
CANONICAL_CROSS_GENERATION_PROTOCOL = "canonical_cross_generation"


async def run_trade(
    *,
    server_url: str,
    action: str,
    room_name: str,
    password: str,
    parser,
    pokemon_location: str,
    auto_confirm: bool,
    backup_dir: str,
    save_path: Path | None,
    initial_save_signature: dict[str, object] | None,
    ui: TerminalUI,
    trade_mode: str = SAME_GENERATION,
    auto_trade_evolution: bool = True,
    item_based_evolutions_enabled: bool = False,
    cross_generation_policy: str = "auto_retrocompat",
    unsafe_auto_confirm_data_loss: bool = False,
) -> PokemonPayload:
    local_generation = parser.get_generation()
    local_game = parser.get_game_id()
    announced_trade_modes = _client_supported_trade_modes(local_generation)
    announced_protocols = _client_supported_protocols()
    if trade_mode != SAME_GENERATION:
        ui.print(f"Aviso: --trade-mode={trade_mode} e legado/debug; o modo real sera derivado automaticamente.")
    async with PokeCableNetworkClient(server_url) as network:
        if action == "create":
            create_message = {
                "type": "create_room",
                "room_name": room_name,
                "password": password,
                "generation": local_generation,
                "game": local_game,
                "supported_trade_modes": announced_trade_modes,
                "supported_protocols": announced_protocols,
            }
            if trade_mode != SAME_GENERATION:
                create_message["trade_mode"] = trade_mode
            await network.send(create_message)
            await network.wait_for({"room_created"})
            ui.print("Sala criada. Aguardando segundo jogador.")
            ready = await network.wait_for({"room_ready"})
            room_info = dict(ready.get("room") or {})
        else:
            await network.send(
                {
                    "type": "join_room",
                    "room_name": room_name,
                    "password": password,
                    "generation": local_generation,
                    "game": local_game,
                    "supported_trade_modes": announced_trade_modes,
                    "supported_protocols": announced_protocols,
                }
            )
            joined = await network.wait_for({"room_joined"})
            ui.print("Sala encontrada. Aguardando ofertas.")
            room_info = dict(joined.get("room") or {})

        target_generation = _peer_generation(room_info, network.client_id)
        offer = _build_offer_payload(
            parser,
            pokemon_location,
            target_generation=target_generation,
            cross_generation_policy=cross_generation_policy,
        )
        ui.print(f"Pokemon selecionado: {offer.display_summary} ({local_game}, Gen {local_generation})")

        await network.send({"type": "offer_pokemon", "payload": offer.to_dict()})
        preflight_message = await _wait_for_preflight_required(network)
        received_preview = PokemonPayload.from_dict(preflight_message["received_payload"])
        ui.print(f"Pokemon do outro jogador: {received_preview.display_summary}")
        preflight_ok, received_report = _preflight_result_for_payload(
            received_preview,
            local_generation,
            cross_generation_policy=cross_generation_policy,
            auto_confirm=auto_confirm,
            unsafe_auto_confirm_data_loss=unsafe_auto_confirm_data_loss,
            ui=ui,
        )
        await network.send(
            {
                "type": "preflight_result",
                "compatible": preflight_ok,
                "report": received_report,
                "error": "" if preflight_ok else "; ".join(received_report.get("blocking_reasons") or []),
            }
        )
        preflight_status = await network.wait_for({"preflight_ready", "trade_blocked"})
        if preflight_status["type"] == "trade_blocked":
            raise RuntimeError(preflight_status.get("message") or "Troca bloqueada no preflight.")
        preview = preview_trade_evolution(
            local_generation,
            _preview_species_id_for_local_generation(received_preview, local_generation),
            held_item_id=_preview_held_item_id_for_local_generation(received_preview, local_generation),
            item_based_evolutions_enabled=item_based_evolutions_enabled,
        )
        if auto_trade_evolution and preview.evolved:
            message = f"Preview: {preview.source_name} evoluira para {preview.target_name} apos a troca."
            if preview.consumed_item_name:
                message += f" {preview.consumed_item_name} sera consumido."
            ui.print(message)
        elif auto_trade_evolution and preview.reason == "item_trade_evolution_disabled":
            ui.print("Evolucao por item esta desligada. Ative item_trade_evolutions_enabled para testar.")

        if not auto_confirm and not ui.confirm("Confirmar troca agora?", default=False):
            await network.send({"type": "cancel_trade"})
            raise RuntimeError("Troca cancelada pelo usuario.")

        await network.send({"type": "confirm_trade"})
        prepared = await network.wait_for({"prepare_write", "trade_write_failed"})
        if prepared["type"] == "trade_write_failed":
            raise RuntimeError(prepared.get("message") or "Falha na preparacao de escrita da troca.")
        received_payload = PokemonPayload.from_dict(prepared["received_payload"])
        _committed_ok, conversion_report_dict = _preflight_result_for_payload(
            received_payload,
            local_generation,
            cross_generation_policy=cross_generation_policy,
            auto_confirm=False,
            unsafe_auto_confirm_data_loss=True,
            ui=ui,
            prompt_user=False,
        )
        conversion_report = None
        backup_path = None
        metadata_path = None
        if save_path is not None:
            if initial_save_signature is not None and not save_signature_matches(save_path, initial_save_signature):
                await network.send(
                    {
                        "type": "write_ready",
                        "ready": False,
                        "error": "O save foi modificado enquanto a sala estava aberta. Feche o emulador e reinicie a troca.",
                    }
                )
                raise RuntimeError(
                    "O save foi modificado enquanto a sala estava aberta (hash diferente). "
                    "Feche o emulador e reinicie a troca para evitar sobrescrever dados novos."
                )
            backup_path, metadata_path = create_backup(
                save_path,
                backup_dir,
                {
                    "original_save": str(save_path),
                    "generation": local_generation,
                    "game": local_game,
                    "room": room_name,
                    "sent": {
                        "species": offer.species_name,
                        "level": offer.level,
                        "nickname": offer.nickname,
                    },
                    "received": {
                        "species": received_payload.species_name,
                        "level": received_payload.level,
                        "nickname": received_payload.nickname,
                    },
                    "save_signature_before_write": initial_save_signature,
                },
            )
        await network.send(
            {
                "type": "write_ready",
                "ready": True,
                "metadata": {
                    "backup_path": str(backup_path) if backup_path else None,
                    "metadata_path": str(metadata_path) if metadata_path else None,
                },
            }
        )
        commit_write = await network.wait_for({"trade_commit_write", "trade_write_failed"})
        if commit_write["type"] == "trade_write_failed":
            raise RuntimeError(commit_write.get("message") or "Falha na escrita da troca.")
        if save_path is not None:
            try:
                if received_payload.generation == local_generation:
                    parser.remove_or_replace_sent_pokemon(pokemon_location, received_payload)
                else:
                    if not received_payload.canonical:
                        raise RuntimeError("Payload cross-generation confirmado nao contem dados canonicos.")
                    canonical = CanonicalPokemon.from_dict(received_payload.canonical)
                    converter = get_converter(canonical.source_generation, local_generation)
                    conversion = converter.apply_to_save(
                        parser,
                        pokemon_location,
                        canonical,
                        policy=cross_generation_policy,
                    )
                    conversion_report = conversion.compatibility_report
                evolution_result = None
                if auto_trade_evolution:
                    evolution_result = apply_trade_evolution_to_parser(
                        parser,
                        pokemon_location,
                        item_based_evolutions_enabled=item_based_evolutions_enabled,
                    )
                parser.save(save_path)
            except Exception as exc:
                await network.send({"type": "write_failed", "stage": "commit_write", "error": str(exc)})
                raise
            await network.send({"type": "write_done", "success": True})
            completed = await network.wait_for({"trade_completed", "trade_write_failed"})
            if completed["type"] == "trade_write_failed":
                raise RuntimeError(completed.get("message") or "Falha remota apos a gravacao local.")
            ui.print(f"Troca aplicada no save: {save_path}")
            if conversion_report is not None:
                _print_report(ui, conversion_report.to_dict())
            elif received_payload.generation != local_generation:
                _print_report(ui, conversion_report_dict)
            if evolution_result is not None and evolution_result.evolved:
                ui.print(f"{evolution_result.source_name} evoluiu para {evolution_result.target_name}!")
                if evolution_result.consumed_item_name:
                    ui.print(f"{evolution_result.consumed_item_name} foi consumido.")
            ui.print(f"Backup: {backup_path}")
            ui.print(f"Metadata: {metadata_path}")
        else:
            await network.send({"type": "write_done", "success": True})
            completed = await network.wait_for({"trade_completed", "trade_write_failed"})
            if completed["type"] == "trade_write_failed":
                raise RuntimeError(completed.get("message") or "Falha remota apos a confirmacao da troca.")
        return received_payload


def _build_offer_payload(
    parser,
    location: str,
    *,
    trade_mode: str | None = None,
    target_generation: int,
    cross_generation_policy: str,
) -> PokemonPayload:
    local_generation = parser.get_generation()
    trade_mode = get_trade_mode(local_generation, target_generation)
    offer = parser.export_pokemon(location)
    canonical = parser.export_canonical(location)
    report = build_compatibility_report(
        canonical,
        target_generation,
        cross_generation_enabled=True,
        policy=cross_generation_policy,
    )
    offer.source_generation = canonical.source_generation
    offer.source_game = canonical.source_game
    offer.target_generation = target_generation
    offer.trade_mode = trade_mode
    offer.canonical = canonical.to_dict()
    offer.compatibility_report = report.to_dict()
    offer.summary = {
        "species_id": canonical.species.national_dex_id,
        "species_name": canonical.species.name,
        "level": canonical.level,
        "nickname": canonical.nickname,
        "display_summary": offer.display_summary,
    }
    return offer


async def _wait_for_preflight_required(network: PokeCableNetworkClient) -> dict:
    while True:
        message = await network.wait_for({"peer_offer_received", "offers_ready", "preflight_required", "trade_blocked"})
        message_type = message.get("type")
        if message_type == "preflight_required":
            return message
        if message_type == "trade_blocked":
            raise RuntimeError(message.get("message") or "Troca bloqueada no preflight.")


def _preflight_result_for_payload(
    payload: PokemonPayload,
    local_generation: int,
    *,
    cross_generation_policy: str,
    auto_confirm: bool,
    unsafe_auto_confirm_data_loss: bool,
    ui: TerminalUI,
    prompt_user: bool = True,
) -> tuple[bool, dict]:
    if payload.generation == local_generation:
        try:
            validate_payload_for_local_save(payload, local_generation)
        except Exception as exc:
            return False, _simple_preflight_report(
                compatible=False,
                mode=SAME_GENERATION,
                source_generation=payload.generation,
                target_generation=local_generation,
                blocking_reasons=[str(exc)],
            )
        return True, _simple_preflight_report(
            compatible=True,
            mode=SAME_GENERATION,
            source_generation=payload.generation,
            target_generation=local_generation,
        )
    if not payload.canonical:
        return False, _simple_preflight_report(
            compatible=False,
            mode=get_trade_mode(payload.generation, local_generation),
            source_generation=payload.generation,
            target_generation=local_generation,
            blocking_reasons=["Payload cross-generation recebido sem modelo canonico."],
        )
    canonical = CanonicalPokemon.from_dict(payload.canonical)
    conversion_mode = get_trade_mode(canonical.source_generation, local_generation)
    if conversion_mode == UNSUPPORTED:
        return False, _simple_preflight_report(
            compatible=False,
            mode=conversion_mode,
            source_generation=canonical.source_generation,
            target_generation=local_generation,
            blocking_reasons=[f"Par de geracoes nao suportado: Gen {canonical.source_generation} -> Gen {local_generation}."],
        )
    report = build_compatibility_report(
        canonical,
        local_generation,
        cross_generation_enabled=True,
        policy=cross_generation_policy,
    )
    report_dict = report.to_dict()
    _print_report(ui, report_dict)
    if not report.compatible:
        return False, report_dict
    if report.requires_user_confirmation and cross_generation_policy != "auto_retrocompat":
        if auto_confirm and not unsafe_auto_confirm_data_loss:
            report_dict.setdefault("blocking_reasons", []).append(
                "Esta conversao possui perda de dados e exige confirmacao manual."
            )
            return False, report_dict
        if prompt_user and not auto_confirm and not ui.confirm("A conversao tem avisos/perdas. Confirmar mesmo assim?", default=False):
            report_dict.setdefault("blocking_reasons", []).append("Troca recusada pelo usuario apos relatorio de compatibilidade.")
            return False, report_dict
    return True, report_dict


def _simple_preflight_report(
    *,
    compatible: bool,
    mode: str,
    source_generation: int,
    target_generation: int,
    blocking_reasons: list[str] | None = None,
) -> dict:
    return {
        "compatible": compatible,
        "mode": mode,
        "source_generation": source_generation,
        "target_generation": target_generation,
        "blocking_reasons": blocking_reasons or [],
        "warnings": [],
        "data_loss": [],
        "suggested_actions": [],
        "transformations": [],
        "removed_moves": [],
        "removed_items": [],
        "removed_fields": [],
        "normalized_species": {},
        "requires_user_confirmation": False,
    }


def _client_supported_trade_modes(generation: int) -> list[str]:
    return sorted(set(supported_modes_for_generation(generation)))


def _client_supported_protocols() -> list[str]:
    return [RAW_SAME_GENERATION_PROTOCOL, CANONICAL_CROSS_GENERATION_PROTOCOL]


def _can_continue_with_report(report, *, auto_confirm: bool, unsafe_auto_confirm_data_loss: bool) -> bool:
    if not report.requires_user_confirmation:
        return True
    return not auto_confirm or unsafe_auto_confirm_data_loss


def _peer_generation(room_info: dict, client_id: str | None) -> int:
    for player in dict(room_info.get("players") or {}).values():
        if str(player.get("client_id")) != str(client_id):
            return int(player["generation"])
    raise RuntimeError("Nao foi possivel detectar a geracao do outro jogador.")


def _preview_species_id_for_local_generation(payload: PokemonPayload, local_generation: int) -> int:
    if not payload.canonical:
        return payload.species_id
    canonical = CanonicalPokemon.from_dict(payload.canonical)
    return national_to_native(local_generation, canonical.species.national_dex_id)


def _preview_held_item_id_for_local_generation(payload: PokemonPayload, local_generation: int) -> int | None:
    if not payload.canonical:
        return None
    canonical = CanonicalPokemon.from_dict(payload.canonical)
    if canonical.held_item is None or canonical.held_item.item_id is None:
        return None
    source_generation = canonical.held_item.source_generation or canonical.source_generation
    if source_generation == local_generation:
        return canonical.held_item.item_id
    return equivalent_item_id(canonical.held_item.item_id, source_generation, local_generation)


def _print_report(ui: TerminalUI, report: dict) -> None:
    for warning in report.get("warnings") or []:
        ui.print(f"Aviso: {warning}")
    for data_loss in report.get("data_loss") or []:
        ui.print(f"Perda de dados: {data_loss}")
    for move in report.get("removed_moves") or []:
        ui.print(f"Move removido: {move.get('name') or move.get('move_id')}")
    for item in report.get("removed_items") or []:
        ui.print(f"Item removido: {item.get('name') or item.get('item_id')}")
    for field in report.get("removed_fields") or []:
        ui.print(f"Campo removido: {field}")
    for transformation in report.get("transformations") or []:
        ui.print(f"Conversao: {transformation}")


def build_parser_from_args(args: argparse.Namespace, ui: TerminalUI):
    if args.save:
        return detect_parser(args.save)

    config = load_config()
    saves = find_save_files(config["default_save_dirs"])
    if not saves:
        raise RuntimeError("Nenhum .sav/.srm encontrado. Informe --save com o caminho do save local.")
    selected = ui.choose("Escolha o save local:", saves, [str(path) for path in saves])
    args.save = str(selected)
    return detect_parser(selected)


def choose_pokemon(parser, ui: TerminalUI, requested_location: str | None) -> str:
    if requested_location:
        return requested_location
    party = parser.list_party()
    selected = ui.choose("Escolha o Pokemon para enviar:", party, [item.display_summary for item in party])
    return selected.location


def _battle_canonical_dict(parser, location: str) -> dict:
    canonical = parser.export_canonical(location).to_dict()
    original_data = dict(canonical.get("original_data") or {})
    if original_data:
        original_data["raw_data_base64"] = None
        canonical["original_data"] = original_data
    return canonical


def choose_battle_team(parser, ui: TerminalUI) -> list[dict]:
    party = parser.list_party()
    selected: list[dict] = []
    ui.print("Escolha o time de batalha. Confirme cada Pokemon que deseja incluir.")
    for item in party:
        if len(selected) >= 6:
            break
        if ui.confirm(f"Incluir {item.display_summary}?", default=True):
            selected.append(_battle_canonical_dict(parser, item.location))
    if not selected:
        raise RuntimeError("Escolha pelo menos um Pokemon para batalha.")
    return selected


async def run_battle(
    *,
    server_url: str,
    action: str,
    room_name: str,
    password: str,
    parser,
    team: list[dict],
    ui: TerminalUI,
    auto_confirm: bool = False,
) -> None:
    generation = parser.get_generation()
    game = parser.get_game_id()
    format_id = format_id_for_generation(generation)
    async with PokeCableNetworkClient(server_url) as network:
        await network.send(
            {
                "type": "create_battle_room" if action == "create" else "join_battle_room",
                "room_name": room_name,
                "password": password,
                "generation": generation,
                "game": game,
                "format_id": format_id,
            }
        )
        if action == "create":
            await network.wait_for({"battle_room_created"})
            ui.print("Sala de batalha criada. Aguardando segundo jogador.")
            await network.wait_for({"battle_room_ready"})
        else:
            await network.wait_for({"battle_room_joined"})
            ui.print("Entrou na sala de batalha.")
        await network.send({"type": "offer_battle_team", "team": team})
        await network.wait_for({"battle_ready"})
        ui.print("Os dois times estao prontos.")
        if not auto_confirm and not ui.confirm("Confirmar batalha agora?", default=True):
            await network.send({"type": "battle_forfeit"})
            raise RuntimeError("Batalha cancelada pelo usuario.")
        await network.send({"type": "confirm_battle"})
        while True:
            message = await network.wait_for({"battle_started", "battle_log", "battle_request_action", "battle_finished", "battle_confirmed"})
            message_type = message.get("type")
            if message_type in {"battle_started", "battle_log", "battle_finished"}:
                for line in message.get("logs") or []:
                    ui.print(str(line))
            if message_type == "battle_request_action":
                if auto_confirm:
                    await network.send({"type": "battle_action", "action": _default_battle_action(dict(message.get("request") or {}))})
                    continue
                _print_battle_request(ui, dict(message.get("request") or {}))
                action_text = ui.input_text("Acao Showdown (ex: move 1, switch 2, pass, forfeit)", "pass")
                if action_text.lower() in {"forfeit", "desistir"}:
                    await network.send({"type": "battle_forfeit"})
                else:
                    await network.send({"type": "battle_action", "action": action_text})
            elif message_type == "battle_finished":
                ui.print("Batalha finalizada.")
                return


async def automated_or_prompted_battle(args: argparse.Namespace) -> int:
    config = load_config()
    log_file = setup_logging(config["log_dir"])
    ui = TerminalUI()
    parser = build_parser_from_args(args, ui)
    try:
        team = choose_battle_team(parser, ui)
        canonical_objects = [CanonicalPokemon.from_dict(item) for item in team]
        ui.print("Time Showdown:")
        ui.print(canonical_team_to_showdown_text(canonical_objects, parser.get_generation()))
        room_name = args.room or ui.input_text("Nome da sala de batalha")
        password = args.password or ui.input_password("Senha da sala de batalha")
        server_url = args.server or config["server_url"]
        action = args.action or ui.choose("Escolha o fluxo:", ["create", "join"], ["Criar sala de batalha", "Entrar em sala de batalha"])
        await run_battle(
            server_url=server_url,
            action=action,
            room_name=room_name,
            password=password,
            parser=parser,
            team=team,
            ui=ui,
            auto_confirm=args.auto_confirm,
        )
    except Exception as exc:
        logger.exception("Battle failed")
        ui.print(f"Erro: {exc}")
        ui.print(f"Log: {log_file}")
        return 1
    return 0


async def automated_or_prompted_trade(args: argparse.Namespace) -> int:
    config = load_config()
    log_file = setup_logging(config["log_dir"])
    ui = TerminalUI()
    parser = build_parser_from_args(args, ui)
    location = choose_pokemon(parser, ui, args.pokemon_location)
    save_path = Path(args.save) if args.save else None
    initial_signature = None
    if save_path is not None:
        initial_signature = capture_save_signature(save_path)
    room_name = args.room or ui.input_text("Nome da sala")
    password = args.password or ui.input_password("Senha da sala")
    server_url = args.server or config["server_url"]
    action = args.action or ui.choose("Escolha o fluxo:", ["create", "join"], ["Criar sala", "Entrar em sala"])
    cross_generation_config = dict(config.get("cross_generation") or {})
    try:
        await run_trade(
            server_url=server_url,
            action=action,
            room_name=room_name,
            password=password,
            parser=parser,
            pokemon_location=location,
            auto_confirm=args.auto_confirm,
            backup_dir=config["backup_dir"],
            save_path=save_path,
            initial_save_signature=initial_signature,
            ui=ui,
            trade_mode=args.trade_mode,
            auto_trade_evolution=bool(config.get("auto_trade_evolution", True)),
            item_based_evolutions_enabled=bool(config.get("item_trade_evolutions_enabled", False)),
            cross_generation_policy=str(cross_generation_config.get("policy") or "auto_retrocompat"),
            unsafe_auto_confirm_data_loss=bool(cross_generation_config.get("unsafe_auto_confirm_data_loss", False)),
        )
    except Exception as exc:
        logger.exception("Trade failed")
        ui.print(f"Erro: {exc}")
        ui.print("A troca nao foi aplicada. Seu save original foi preservado.")
        ui.print(f"Log: {log_file}")
        return 1
    return 0


def configure_server(ui: TerminalUI) -> None:
    config = load_config()
    server_url = ui.input_text("URL WebSocket do servidor", config["server_url"])
    config["server_url"] = server_url
    config.setdefault("cross_generation", {"policy": "auto_retrocompat"})
    save_config(config)
    ui.print("Servidor configurado.")


def _print_battle_request(ui: TerminalUI, request: dict) -> None:
    active = request.get("active") or []
    if active and isinstance(active[0], dict):
        moves = active[0].get("moves") or []
        for index, move in enumerate(moves, start=1):
            if move.get("disabled"):
                continue
            ui.print(f"- move {index}: {move.get('move')} ({move.get('pp')}/{move.get('maxpp')})")
    if request.get("forceSwitch") and isinstance(request.get("side"), dict):
        for index, pokemon in enumerate(request["side"].get("pokemon") or [], start=1):
            if pokemon.get("active"):
                continue
            condition = str(pokemon.get("condition") or "")
            if "fnt" in condition:
                continue
            ui.print(f"- switch {index}: {pokemon.get('details') or pokemon.get('ident')}")


def _default_battle_action(request: dict) -> str:
    active = request.get("active") or []
    if active and isinstance(active[0], dict):
        moves = active[0].get("moves") or []
        for index, move in enumerate(moves, start=1):
            if not move.get("disabled"):
                return f"move {index}"
    if request.get("forceSwitch") and isinstance(request.get("side"), dict):
        for index, pokemon in enumerate(request["side"].get("pokemon") or [], start=1):
            if pokemon.get("active"):
                continue
            if "fnt" in str(pokemon.get("condition") or ""):
                continue
            return f"switch {index}"
    return "move 1"


def show_logs(ui: TerminalUI) -> None:
    config = load_config()
    log_file = Path(config["log_dir"]) / "client.log"
    if not log_file.exists():
        ui.print("Nenhum log encontrado.")
        return
    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
    ui.print("\n".join(lines))


def restore_backup_flow(ui: TerminalUI) -> None:
    config = load_config()
    backups = list_backups(config["backup_dir"])
    if not backups:
        ui.print("Nenhum backup encontrado.")
        return
    selected = ui.choose("Escolha o backup para restaurar:", backups, [str(path) for path in backups])
    destination = ui.input_text("Caminho do save de destino")
    if not destination:
        ui.print("Restore cancelado: destino vazio.")
        return
    if not ui.confirm(f"Restaurar {selected} para {destination}?", default=False):
        ui.print("Restore cancelado.")
        return
    restore_backup(selected, destination)
    ui.print(f"Backup restaurado em: {destination}")


def choose_save_flow(ui: TerminalUI) -> None:
    config = load_config()
    saves = find_save_files(config["default_save_dirs"])
    if not saves:
        ui.print("Nenhum .sav/.srm encontrado nos diretorios configurados.")
        return
    selected = ui.choose("Saves encontrados:", saves, [str(path) for path in saves])
    parser = detect_parser(selected)
    ui.print(f"Selecionado: {selected}")
    ui.print(f"Detectado: {parser.get_game_id()} Gen {parser.get_generation()}")
    for item in parser.list_party():
        ui.print(f"- {item.location}: {item.display_summary} ({item.nickname})")


def view_party(ui: TerminalUI) -> None:
    choose_save_flow(ui)


def test_compatibility(ui: TerminalUI) -> None:
    config = load_config()
    saves = find_save_files(config["default_save_dirs"])
    if not saves:
        ui.print("Nenhum .sav/.srm encontrado nos diretorios configurados.")
        return
    selected = ui.choose("Escolha o save local:", saves, [str(path) for path in saves])
    parser = detect_parser(selected)
    location = choose_pokemon(parser, ui, None)
    target_generation = ui.choose("Geracao destino:", [1, 2, 3], ["Gen 1", "Gen 2", "Gen 3"])
    canonical = parser.export_canonical(location)
    report = build_compatibility_report(canonical, target_generation, cross_generation_enabled=True)
    ui.print(f"Modo: {report.mode}")
    ui.print(f"Compatibilidade: {'ok' if report.compatible else 'bloqueada'}")
    normalized = report.normalized_species
    if normalized.get("target_species_id") is not None:
        ui.print(
            f"{canonical.species.name} existe na Gen {target_generation} e pode ser convertido para "
            f"{normalized.get('target_species_id_space')} {normalized.get('target_species_id')}."
        )
    elif report.blocking_reasons:
        ui.print(f"{canonical.species.name} nao existe na Gen {target_generation} e sera bloqueado.")
    for reason in report.blocking_reasons:
        ui.print(f"- Bloqueio: {reason}")
    for warning in report.warnings:
        ui.print(f"- Aviso: {warning}")
    for data_loss in report.data_loss:
        ui.print(f"- Perda de dados: {data_loss}")


def interactive_menu() -> int:
    ui = TerminalUI()
    config = load_config()
    setup_logging(config["log_dir"])
    while True:
        choice = ui.choose(
            "PokeCable Room",
            [
                "create",
                "join",
                "save",
                "party",
                "compatibility",
                "battle_create",
                "battle_join",
                "server",
                "restore",
                "logs",
                "exit",
            ],
            [
                "Criar sala",
                "Entrar em sala",
                "Escolher save",
                "Ver party",
                "Testar compatibilidade",
                "Criar sala de batalha",
                "Entrar em sala de batalha",
                "Configurar servidor VPS",
                "Restaurar backup",
                "Ver logs",
                "Sair",
            ],
        )
        if choice == "create":
            args = argparse.Namespace(
                action="create",
                server=None,
                room=None,
                password=None,
                save=None,
                pokemon_location=None,
                auto_confirm=False,
                trade_mode=SAME_GENERATION,
            )
            return asyncio.run(automated_or_prompted_trade(args))
        elif choice == "join":
            args = argparse.Namespace(
                action="join",
                server=None,
                room=None,
                password=None,
                save=None,
                pokemon_location=None,
                auto_confirm=False,
                trade_mode=SAME_GENERATION,
            )
            return asyncio.run(automated_or_prompted_trade(args))
        elif choice == "save":
            choose_save_flow(ui)
        elif choice == "party":
            view_party(ui)
        elif choice == "compatibility":
            test_compatibility(ui)
        elif choice == "battle_create":
            args = argparse.Namespace(
                action="create",
                server=None,
                room=None,
                password=None,
                save=None,
                pokemon_location=None,
                auto_confirm=False,
                trade_mode=SAME_GENERATION,
            )
            return asyncio.run(automated_or_prompted_battle(args))
        elif choice == "battle_join":
            args = argparse.Namespace(
                action="join",
                server=None,
                room=None,
                password=None,
                save=None,
                pokemon_location=None,
                auto_confirm=False,
                trade_mode=SAME_GENERATION,
            )
            return asyncio.run(automated_or_prompted_battle(args))
        elif choice == "server":
            configure_server(ui)
        elif choice == "restore":
            restore_backup_flow(ui)
        elif choice == "logs":
            show_logs(ui)
        else:
            return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PokeCable Room R36S client")
    parser.add_argument("--action", choices=["create", "join"], help="Fluxo de sala para rodar sem menu.")
    parser.add_argument("--mode", choices=["trade", "battle"], default="trade", help="Modo: troca por save ou batalha.")
    parser.add_argument("--server", help="URL WebSocket, exemplo ws://127.0.0.1:8000/ws")
    parser.add_argument("--room", help="Nome da sala.")
    parser.add_argument("--password", help="Senha da sala.")
    parser.add_argument("--save", help="Caminho para .sav/.srm local.")
    parser.add_argument("--pokemon-location", default="party:0", help="Localizacao do Pokemon, padrao party:0.")
    parser.add_argument("--trade-mode", default=SAME_GENERATION, help="Modo de troca. Cross-generation exige feature flag local e servidor habilitado para o modo.")
    parser.add_argument("--auto-confirm", action="store_true", help="Confirma automaticamente apos receber a oferta do outro jogador.")
    parser.add_argument("--list-party", action="store_true", help="Lista party do save em JSON e sai.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.list_party:
        if not args.save:
            print("[]")
            return 1
        parser = detect_parser(args.save)
        print(json.dumps([asdict(item) for item in parser.list_party()], ensure_ascii=False))
        return 0
    if args.action:
        if args.mode == "battle":
            return asyncio.run(automated_or_prompted_battle(args))
        return asyncio.run(automated_or_prompted_trade(args))
    return interactive_menu()


if __name__ == "__main__":
    raise SystemExit(main())
