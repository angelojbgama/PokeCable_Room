#!/usr/bin/env python3
"""
PokeCable R36S - Core logic for local save parsing and websocket trading.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import websockets

from pokecable_save import SaveError, SaveModel, load_save

DEBUG = os.getenv("POKECABLE_DEBUG", "0").lower() in ("1", "true", "yes")
logger = logging.getLogger("r36s_pokecable_core")

if DEBUG:
    logger.setLevel(logging.DEBUG)


DEFAULT_BACKEND_WS = "wss://9kernel.vps-kinghost.net/ws"
SUPPORTED_TRADE_MODES = [
    "same_generation",
    "time_capsule_gen1_gen2",
    "forward_transfer_to_gen3",
    "legacy_downconvert_experimental",
]
SUPPORTED_PROTOCOLS = ["raw_same_generation", "canonical_cross_generation"]


class PokecableState:
    """Manages application state and local save cache."""

    def __init__(self):
        self.config_dir = Path.home() / ".pokecable"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.screen = "menu"
        self.menu_index = 0
        self.saves: List[Path] = []
        self.selected_save: Optional[Path] = None
        self.selected_pokemon: Optional[Dict[str, Any]] = None
        self.pokemon_list: List[Dict[str, Any]] = []
        self.room_name = ""
        self.room_password = ""
        self.pokemon_source = "party"
        self.action: str = "access"

        self.save_analysis: Dict[str, Dict[str, Any]] = {}
        self.server_url = self._load_server_url()

    def _load_server_url(self) -> str:
        config_file = self.config_dir / "server.conf"
        if config_file.exists():
            try:
                url = config_file.read_text().strip()
                if url:
                    logger.info("Loaded server URL from config: %s", url)
                    return url
            except Exception as exc:
                logger.warning(f"Failed to read server.conf: {exc}")
        return DEFAULT_BACKEND_WS

    def save_server_url(self, url: str) -> None:
        config_file = self.config_dir / "server.conf"
        try:
            config_file.write_text(url)
            self.server_url = url
        except Exception as exc:
            logger.error(f"Failed to save server.conf: {exc}")

    def find_saves(self) -> List[Path]:
        self.saves = []
        seen = set()
        search_dirs = [
            Path("/roms"),
            Path("/roms/gbc"),
            Path("/roms/gba"),
            Path("/roms2"),
            Path("/roms2/gbc"),
            Path("/roms2/gba"),
            Path("/opt/system"),
            Path("/opt/roms"),
            Path.home() / "saves",
            Path.home() / "roms",
            Path.home() / "Downloads",
            Path("/tmp"),
            Path("/storage/roms"),
        ]
        patterns = ["*.sav", "*.srm", "*.SAV", "*.SRM"]
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            try:
                for pattern in patterns:
                    for save_file in search_dir.glob(pattern):
                        if save_file.is_file():
                            key = str(save_file.resolve())
                            if key not in seen:
                                seen.add(key)
                                self.saves.append(save_file)
                    for save_file in search_dir.glob(f"*/{pattern}"):
                        if save_file.is_file():
                            key = str(save_file.resolve())
                            if key not in seen:
                                seen.add(key)
                                self.saves.append(save_file)
            except (PermissionError, OSError) as exc:
                logger.debug(f"Cannot access {search_dir}: {exc}")
        self.saves.sort()
        logger.info("Found %s save file(s)", len(self.saves))
        return self.saves

    def analyze_save(self, save_path: Path) -> Optional[Dict[str, Any]]:
        key = str(save_path.resolve())
        cached = self.save_analysis.get(key)
        try:
            stat = save_path.stat()
            current_sig = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        except FileNotFoundError:
            logger.error(f"Save file does not exist: {save_path}")
            return None

        if cached and cached.get("file_signature") == current_sig:
            logger.debug("Using cached analysis for %s", save_path)
            return cached

        try:
            save = load_save(save_path)
        except SaveError as exc:
            logger.error(f"Failed to analyze save {save_path.name}: {exc}")
            return None
        except Exception as exc:
            logger.exception(f"Unexpected save analysis error: {exc}")
            return None

        analysis = {
            "save": save,
            "generation": save.generation,
            "game": save.game,
            "label": save.label,
            "player_name": save.player_name,
            "pokemon": save.get_pokemon("party") + save.get_pokemon("boxes"),
            "party_count": len(save.party),
            "box_count": len(save.boxes),
            "supports_boxes": bool(save.boxes),
            "signature": save.signature(),
            "file_signature": current_sig,
        }
        self.save_analysis[key] = analysis
        logger.info(
            "Local analysis: %s, %s, party=%s boxes=%s file=%s",
            save.label,
            save.game,
            len(save.party),
            len(save.boxes),
            save_path,
        )
        return analysis

    def get_selected_save_model(self) -> Optional[SaveModel]:
        if not self.selected_save:
            return None
        analysis = self.analyze_save(self.selected_save)
        if not analysis:
            return None
        return analysis.get("save")

    def refresh_selected_save(self) -> Optional[Dict[str, Any]]:
        if not self.selected_save:
            return None
        key = str(self.selected_save.resolve())
        self.save_analysis.pop(key, None)
        return self.analyze_save(self.selected_save)

    def get_pokemon_list(self, source: str = "party") -> List[Dict[str, Any]]:
        if not self.selected_save:
            return []

        analysis = self.analyze_save(self.selected_save)
        if not analysis:
            self.pokemon_list = []
            return []

        self.pokemon_list = []
        for pokemon in analysis["save"].get_pokemon(source):
            self.pokemon_list.append(
                {
                    "index": pokemon.get("index"),
                    "name": pokemon.get("species_name", "Pokemon"),
                    "species_id": pokemon.get("species_id", 0),
                    "species_name": pokemon.get("species_name", "Pokemon"),
                    "level": pokemon.get("level", 0),
                    "nickname": pokemon.get("nickname", ""),
                    "location": pokemon.get("location", "party:0"),
                    "source": pokemon.get("source", source),
                    "box_name": pokemon.get("box_name", ""),
                    "display": pokemon.get("display_summary", "Pokemon"),
                    "generation": analysis.get("generation", 0),
                    "raw": pokemon,
                }
            )

        logger.info("Loaded %s pokemon from %s", len(self.pokemon_list), source)
        return self.pokemon_list


class PygameUI:
    """UI adapter that sends status messages to pygame via queue."""

    def __init__(self, ui_queue: queue.Queue, confirm_queue: queue.Queue):
        self.ui_queue = ui_queue
        self.confirm_queue = confirm_queue

    def status(self, msg: str) -> None:
        self.ui_queue.put(("status", msg))
        logger.info(f"STATUS: {msg}")

    def error(self, msg: str) -> None:
        self.ui_queue.put(("error", msg))
        logger.error(f"ERROR: {msg}")

    def result(self, data: Any) -> None:
        self.ui_queue.put(("result", data))
        logger.info(f"RESULT: {data}")

    def screen(self, screen: str) -> None:
        self.ui_queue.put(("screen", screen))


def _create_backup(save_path: Path) -> Path:
    backup_dir = Path.home() / ".pokecable" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{save_path.stem}.{timestamp}{save_path.suffix}.bak"
    shutil.copy2(save_path, backup_path)
    logger.info(f"Backup: {backup_path}")
    return backup_path


def _save_unchanged_on_disk(expected: Dict[str, Any], path: Path) -> bool:
    try:
        current = path.read_bytes()
    except FileNotFoundError:
        return False
    if expected.get("size") != len(current):
        return False
    import hashlib

    return expected.get("sha256") == hashlib.sha256(current).hexdigest()


def _build_preflight(state: PokecableState, peer_payload: Dict[str, Any], save: SaveModel) -> Dict[str, Any]:
    reasons: List[str] = []
    if not peer_payload:
        reasons.append("Oferta remota ausente.")
    if int(peer_payload.get("generation", 0)) != save.generation:
        reasons.append("Cross-generation ainda não é suportado no R36S.")
    raw_format = str(peer_payload.get("raw", {}).get("format") or peer_payload.get("metadata", {}).get("format") or "")
    if not (peer_payload.get("raw_data_base64") or peer_payload.get("raw", {}).get("data_base64")):
        reasons.append("Payload same-generation sem raw data.")
    if not state.selected_pokemon:
        reasons.append("Nenhum Pokémon local selecionado.")
    elif save.target_requires_box_promotion_block(state.selected_pokemon.get("location", "party:0"), peer_payload):
        reasons.append("Receber um Pokémon vindo do PC para a Party ainda não é suportado no R36S. Escolha um slot do PC como destino local para concluir a troca.")
    return {
        "compatible": not reasons,
        "mode": "same_generation",
        "source_generation": save.generation,
        "target_generation": save.generation,
        "blocking_reasons": reasons,
        "warnings": [],
        "data_loss": [],
        "suggested_actions": [],
    }


async def _websocket_trade(
    state: PokecableState,
    action: str,
    ui: PygameUI,
    confirm_queue: queue.Queue,
) -> None:
    if not state.selected_save:
        ui.error("Nenhum save selecionado")
        return

    analysis = state.analyze_save(state.selected_save)
    if not analysis:
        ui.error("Falha ao analisar o save local")
        return

    save: SaveModel = analysis["save"]
    expected_signature = analysis["signature"]

    ui.screen("connecting")
    ui.status(f"Conectando a {state.server_url}...")
    logger.info(
        "Trade session start: action=%s room=%s save=%s selected=%s",
        action,
        state.room_name,
        state.selected_save,
        state.selected_pokemon.get("location") if state.selected_pokemon else None,
    )

    try:
        async with websockets.connect(state.server_url, ping_interval=20, ping_timeout=10) as ws:
            connected = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            logger.info(f"WS connected: {connected}")

            room_msg = {
                "type": "join_room" if action == "access" else ("create_room" if action == "create" else "join_room"),
                "room_name": state.room_name,
                "password": state.room_password,
                "player_name": save.player_name or os.environ.get("USER", "Treinador"),
                "generation": save.generation,
                "game": save.game,
                "supported_trade_modes": SUPPORTED_TRADE_MODES,
                "supported_protocols": SUPPORTED_PROTOCOLS,
            }
            logger.debug("Sending room message: %s", room_msg)
            await ws.send(json.dumps(room_msg))
            ui.screen("waiting_partner")
            ui.status("Acessando sala..." if action == "access" else ("Criando sala..." if action == "create" else "Entrando na sala..."))

            peer_offer: Dict[str, Any] = {}
            backup_path: Optional[Path] = None
            our_offer_sent = False
            room_ready = False
            selection_opened = False

            while True:
                try:
                    raw_msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg = json.loads(raw_msg)
                    mtype = msg.get("type")
                    logger.info(f"WS recv: {mtype}")
                    logger.debug(f"WS payload: {json.dumps(msg)[:500]}")
                except asyncio.TimeoutError:
                    msg = None
                    mtype = None

                if room_ready and not our_offer_sent and state.selected_pokemon:
                    state.refresh_selected_save()
                    save = state.get_selected_save_model() or save
                    selected = state.selected_pokemon
                    pokemon_location = selected.get("location", "party:0")
                    try:
                        offer_payload = save.export_payload(pokemon_location)
                    except SaveError as exc:
                        ui.error(str(exc))
                        return
                    logger.info("Sending offer: location=%s species=%s", pokemon_location, offer_payload.get("species_name"))
                    ui.screen("trading")
                    ui.status("Sala pronta. Enviando oferta...")
                    await ws.send(json.dumps({"type": "offer_pokemon", "payload": offer_payload}))
                    our_offer_sent = True
                    continue

                if not msg:
                    continue

                if mtype == "heartbeat":
                    continue

                if mtype in ("generation_mismatch", "game_mismatch"):
                    ui.error(msg.get("message", mtype))
                    return

                if mtype in ("error", "room_not_found", "room_exists"):
                    code = str(msg.get("code", "") or mtype).lower()
                    message = str(msg.get("message", "") or msg.get("error", "")).lower()
                    logger.warning("Room flow response: type=%s code=%s message=%s", mtype, code, message)
                    room_not_found = code == "room_not_found" or "room_not_found" in message or "not found" in message
                    room_exists = code == "room_exists" or "room_exists" in message or "already exists" in message
                    invalid_password = code == "invalid_password" or "invalid password" in message
                    if action == "access" and room_not_found:
                        logger.warning("Room not found during access; creating automatically: room=%s", state.room_name)
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "create_room",
                                    "room_name": state.room_name,
                                    "password": state.room_password,
                                    "player_name": save.player_name or os.environ.get("USER", "Treinador"),
                                    "generation": save.generation,
                                    "game": save.game,
                                    "supported_trade_modes": SUPPORTED_TRADE_MODES,
                                    "supported_protocols": SUPPORTED_PROTOCOLS,
                                }
                            )
                        )
                        ui.status("Sala nao existe. Criando automaticamente...")
                        continue
                    if action == "access" and room_exists:
                        logger.warning("Room exists response during access; retrying join for room=%s", state.room_name)
                        await ws.send(json.dumps(room_msg))
                        continue
                    if invalid_password:
                        ui.error(msg.get("message", "Senha invalida"))
                        return
                    ui.error(msg.get("message", "Erro no servidor"))
                    return

                if mtype == "room_created":
                    if not selection_opened:
                        ui.screen("select_pokemon_source")
                        selection_opened = True
                    ui.status("Sala criada. Escolha o Pokemon e aguarde outro treinador...")
                    continue

                if mtype == "room_joined":
                    if not selection_opened:
                        ui.screen("select_pokemon_source")
                        selection_opened = True
                    ui.status("Entrou na sala. Escolha o Pokemon para a troca...")
                    continue

                if mtype == "room_waiting":
                    ui.status(msg.get("message", "Aguardando outro jogador..."))
                    continue

                if mtype == "room_ready":
                    room_ready = True
                    if not selection_opened:
                        ui.screen("select_pokemon_source")
                        selection_opened = True
                    if not state.selected_pokemon:
                        ui.status("Sala pronta. Agora escolha o Pokemon para enviar.")
                    continue

                if mtype == "offer_received":
                    ui.screen("trading")
                    ui.status("Oferta enviada. Aguardando o outro treinador...")
                    continue

                if mtype == "peer_offer_received":
                    peer_offer = msg.get("offer", {}) or {}
                    summary = peer_offer.get("display_summary") or peer_offer.get("nickname") or peer_offer.get("species_name") or "Pokémon"
                    ui.screen("trading")
                    ui.status(f"Oferta recebida: {summary}")
                    continue

                if mtype == "offers_ready":
                    ui.screen("trading")
                    ui.status("Ofertas prontas. Validando compatibilidade...")
                    continue

                if mtype == "preflight_required":
                    report = _build_preflight(state, msg.get("received_payload") or peer_offer, save)
                    logger.debug("Preflight report: %s", report)
                    await ws.send(
                        json.dumps(
                            {
                                "type": "preflight_result",
                                "compatible": report["compatible"],
                                "requires_user_confirmation": False,
                                "report": report,
                                "error": "; ".join(report["blocking_reasons"]),
                            }
                        )
                    )
                    if report["compatible"]:
                        ui.status("Compatibilidade validada. Aguardando confirmação...")
                    else:
                        ui.error("; ".join(report["blocking_reasons"]) or "Troca bloqueada")
                        return
                    continue

                if mtype == "preflight_ready":
                    summary = peer_offer.get("display_summary") or peer_offer.get("nickname") or peer_offer.get("species_name") or "parceiro"
                    ui.screen("trade_confirm")
                    ui.status(f"Pronto para trocar com {summary}")
                    ui.ui_queue.put(("confirm_prompt", peer_offer))
                    logger.info("Waiting for local confirmation: peer=%s", summary)
                    user_confirmed = confirm_queue.get()
                    logger.info("Local confirmation result: %s", user_confirmed)
                    if not user_confirmed:
                        await ws.send(json.dumps({"type": "cancel_trade_round", "reason": "user_cancelled"}))
                        ui.status("Troca cancelada")
                        return
                    ui.screen("trading")
                    ui.status("Confirmação enviada. Aguardando o outro treinador...")
                    await ws.send(json.dumps({"type": "confirm_trade"}))
                    continue

                if mtype == "trade_blocked":
                    ui.error(msg.get("message", "Troca bloqueada"))
                    return

                if mtype == "trade_confirmed":
                    ui.screen("trading")
                    ui.status("Confirmação registrada. Preparando gravação...")
                    continue

                if mtype == "prepare_write":
                    logger.info("Prepare write received for save=%s", state.selected_save)
                    if not _save_unchanged_on_disk(expected_signature, state.selected_save):
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "write_ready",
                                    "ready": False,
                                    "error": "save_changed_during_room",
                                    "metadata": {
                                        "message": "O save mudou em disco antes da gravação.",
                                        "expected_signature": expected_signature,
                                    },
                                }
                            )
                        )
                        ui.error("O save mudou em disco. Recarregue e tente novamente.")
                        return
                    backup_path = _create_backup(state.selected_save)
                    ui.screen("trading")
                    ui.status(f"Backup criado: {backup_path.name}")
                    logger.info("Write ready after backup: %s", backup_path)
                    await ws.send(
                        json.dumps(
                            {
                                "type": "write_ready",
                                "ready": True,
                                "metadata": {
                                    "save_name": state.selected_save.name,
                                    "size": expected_signature["size"],
                                    "sha256": expected_signature["sha256"],
                                },
                            }
                        )
                    )
                    continue

                if mtype == "trade_commit_write":
                    ui.screen("trading")
                    ui.status("Aplicando troca ao save...")
                    received_payload = msg.get("received_payload") or peer_offer
                    try:
                        logger.info("Applying received payload to location=%s", pokemon_location)
                        saved_pokemon = save.apply_payload(pokemon_location, received_payload)
                        save.write_to_disk()
                        refreshed = state.refresh_selected_save()
                        if refreshed:
                            expected_signature = refreshed["signature"]
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "write_done",
                                    "success": True,
                                    "metadata": {
                                        "backup": str(backup_path) if backup_path else "",
                                        "location": pokemon_location,
                                    },
                                }
                            )
                        )
                        summary = saved_pokemon.get("display_summary") or saved_pokemon.get("nickname") or saved_pokemon.get("species_name") or "Pokémon"
                        logger.info("Write completed: %s", summary)
                        ui.status(f"Save atualizado: {summary}")
                    except Exception as exc:
                        logger.exception(f"Failed to apply received payload: {exc}")
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "write_failed",
                                    "stage": "commit_write",
                                    "error": str(exc),
                                }
                            )
                        )
                        ui.error(f"Falha ao gravar o save: {exc}")
                        return
                    continue

                if mtype == "trade_completed":
                    logger.info("Trade completed successfully: room=%s backup=%s", state.room_name, backup_path)
                    ui.screen("trade_result")
                    ui.status("Troca concluída!")
                    ui.result(
                        {
                            "success": True,
                            "peer": peer_offer,
                            "save": str(state.selected_save),
                            "backup": str(backup_path) if backup_path else "",
                        }
                    )
                    return

                if mtype == "trade_write_failed":
                    ui.error(msg.get("error", "Falha remota na gravação"))
                    return

                if mtype == "trade_cancelled":
                    ui.error(msg.get("message", "Troca cancelada"))
                    return

    except websockets.exceptions.ConnectionClosed as exc:
        logger.error(f"WebSocket closed: {exc}")
        ui.error(f"Conexão fechada: {exc}")
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for server")
        ui.error("Timeout aguardando servidor")
    except Exception as exc:
        logger.exception(f"Trade error: {exc}")
        ui.error(f"Erro: {exc}")


def _run_trade_bg(state: PokecableState, action: str, ui_queue: queue.Queue, confirm_queue: queue.Queue) -> None:
    ui = PygameUI(ui_queue, confirm_queue)
    try:
        logger.info("Background trade thread starting: action=%s room=%s", action, state.room_name)
        asyncio.run(_websocket_trade(state, action, ui, confirm_queue))
    except Exception as exc:
        logger.exception(f"Trade thread failed: {exc}")
        ui.error(str(exc))


def start_trade_thread(
    state: PokecableState, action: str, ui_queue: queue.Queue, confirm_queue: queue.Queue
) -> threading.Thread:
    thread = threading.Thread(
        target=_run_trade_bg,
        args=(state, action, ui_queue, confirm_queue),
        daemon=True,
    )
    thread.start()
    logger.info(f"Trade thread started (action={action})")
    return thread
