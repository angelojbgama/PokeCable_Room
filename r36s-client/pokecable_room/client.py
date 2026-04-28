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

from pokecable_room.logs import setup_logging
from pokecable_room.network import PokeCableNetworkClient
from pokecable_room.parsers.base import PokemonPayload
from pokecable_room.backups import create_backup, list_backups, restore_backup
from pokecable_room.saves import detect_parser, find_save_files, load_config, save_config
from pokecable_room.trade import maybe_apply_trade_evolution, validate_payload_for_local_save
from pokecable_room.ui import TerminalUI


logger = logging.getLogger("pokecable.client")


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
    initial_save_signature: tuple[int, int] | None,
    ui: TerminalUI,
) -> PokemonPayload:
    local_generation = parser.get_generation()
    local_game = parser.get_game_id()
    offer = parser.export_pokemon(pokemon_location)
    ui.print(f"Pokemon selecionado: {offer.display_summary} ({local_game}, Gen {local_generation})")
    async with PokeCableNetworkClient(server_url) as network:
        if action == "create":
            await network.send(
                {
                    "type": "create_room",
                    "room_name": room_name,
                    "password": password,
                    "generation": local_generation,
                    "game": local_game,
                }
            )
            await network.wait_for({"room_created"})
            ui.print("Sala criada. Aguardando segundo jogador.")
            await network.wait_for({"room_ready"})
        else:
            await network.send(
                {
                    "type": "join_room",
                    "room_name": room_name,
                    "password": password,
                    "generation": local_generation,
                    "game": local_game,
                }
            )
            await network.wait_for({"room_joined"})
            ui.print("Sala encontrada. Aguardando ofertas.")

        await network.send({"type": "offer_pokemon", "payload": offer.to_dict()})
        peer_offer_message = await network.wait_for({"peer_offer_received"})
        received_preview = PokemonPayload.from_dict(peer_offer_message["offer"])
        validate_payload_for_local_save(received_preview, local_generation)
        ui.print(f"Pokemon do outro jogador: {received_preview.display_summary}")

        if not auto_confirm and not ui.confirm("Confirmar troca agora?", default=False):
            await network.send({"type": "cancel_trade"})
            raise RuntimeError("Troca cancelada pelo usuario.")

        await network.send({"type": "confirm_trade"})
        committed = await network.wait_for({"trade_committed"})
        received_payload = PokemonPayload.from_dict(committed["received_payload"])
        validate_payload_for_local_save(received_payload, local_generation)
        received_payload = maybe_apply_trade_evolution(received_payload, enabled=False)
        if save_path is not None:
            current_signature = (save_path.stat().st_size, int(save_path.stat().st_mtime))
            if initial_save_signature is not None and current_signature != initial_save_signature:
                raise RuntimeError(
                    "O save foi modificado enquanto a sala estava aberta. "
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
                },
            )
            parser.remove_or_replace_sent_pokemon(pokemon_location, received_payload)
            parser.save(save_path)
            ui.print(f"Troca aplicada no save: {save_path}")
            ui.print(f"Backup: {backup_path}")
            ui.print(f"Metadata: {metadata_path}")
        return received_payload


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


async def automated_or_prompted_trade(args: argparse.Namespace) -> int:
    config = load_config()
    log_file = setup_logging(config["log_dir"])
    ui = TerminalUI()
    parser = build_parser_from_args(args, ui)
    location = choose_pokemon(parser, ui, args.pokemon_location)
    save_path = Path(args.save) if args.save else None
    initial_signature = None
    if save_path is not None:
        stat = save_path.stat()
        initial_signature = (stat.st_size, int(stat.st_mtime))
    room_name = args.room or ui.input_text("Nome da sala")
    password = args.password or ui.input_password("Senha da sala")
    server_url = args.server or config["server_url"]
    action = args.action or ui.choose("Escolha o fluxo:", ["create", "join"], ["Criar sala", "Entrar em sala"])
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
        )
    except Exception as exc:
        logger.exception("Trade failed")
        ui.print(f"Erro: {exc}")
        ui.print(f"Log: {log_file}")
        return 1
    return 0


def configure_server(ui: TerminalUI) -> None:
    config = load_config()
    server_url = ui.input_text("URL WebSocket do servidor", config["server_url"])
    config["server_url"] = server_url
    config["allow_cross_generation"] = False
    save_config(config)
    ui.print("Servidor configurado. Cross-generation permanece desativado.")


def show_logs(ui: TerminalUI) -> None:
    config = load_config()
    log_file = Path(config["log_dir"]) / "client.log"
    if not log_file.exists():
        ui.print("Nenhum log encontrado.")
        return
    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
    ui.print("\n".join(lines))


def restore_backup_placeholder(ui: TerminalUI) -> None:
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


def choose_save_placeholder(ui: TerminalUI) -> None:
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


def interactive_menu() -> int:
    ui = TerminalUI()
    config = load_config()
    setup_logging(config["log_dir"])
    while True:
        choice = ui.choose(
            "PokeCable Room",
            ["create", "join", "save", "server", "restore", "logs", "exit"],
            [
                "Criar sala",
                "Entrar em sala",
                "Escolher save",
                "Configurar servidor VPS",
                "Restaurar backup",
                "Ver logs",
                "Sair",
            ],
        )
        if choice in {"create", "join"}:
            args = argparse.Namespace(
                action=choice,
                server=None,
                room=None,
                password=None,
                save=None,
                pokemon_location=None,
                auto_confirm=False,
            )
            return asyncio.run(automated_or_prompted_trade(args))
        if choice == "save":
            choose_save_placeholder(ui)
        elif choice == "server":
            configure_server(ui)
        elif choice == "restore":
            restore_backup_placeholder(ui)
        elif choice == "logs":
            show_logs(ui)
        else:
            return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PokeCable Room R36S client")
    parser.add_argument("--action", choices=["create", "join"], help="Fluxo de sala para rodar sem menu.")
    parser.add_argument("--server", help="URL WebSocket, exemplo ws://127.0.0.1:8000/ws")
    parser.add_argument("--room", help="Nome da sala.")
    parser.add_argument("--password", help="Senha da sala.")
    parser.add_argument("--save", help="Caminho para .sav/.srm local.")
    parser.add_argument("--pokemon-location", default="party:0", help="Localizacao do Pokemon, padrao party:0.")
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
        return asyncio.run(automated_or_prompted_trade(args))
    return interactive_menu()


if __name__ == "__main__":
    raise SystemExit(main())
