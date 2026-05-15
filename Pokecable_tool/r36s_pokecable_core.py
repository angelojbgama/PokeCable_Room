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
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import websockets

from pokecable_save import SaveError, SaveModel, _ensure_backend_import_path, load_save

DEBUG = os.getenv("POKECABLE_DEBUG", "0").lower() in ("1", "true", "yes")
logger = logging.getLogger("r36s_pokecable_core")

if DEBUG:
    logger.setLevel(logging.DEBUG)


DEFAULT_BACKEND_WS = "ws://127.0.0.1:8000/ws"
DEFAULT_LANGUAGE = "pt"
DEFAULT_THEME = "pokedex_dark"
SUPPORTED_LANGUAGES = {"pt", "en", "es"}
SUPPORTED_THEMES = {"pokedex_dark", "pokedex_white"}
SUPPORTED_TRADE_MODES = [
    "same_generation",
    "time_capsule_gen1_gen2",
    "forward_transfer_to_gen3",
    "legacy_downconvert_experimental",
]
SUPPORTED_PROTOCOLS = ["raw_same_generation", "canonical_cross_generation"]
CONNECT_ATTEMPTS = 8
CONNECT_OPEN_TIMEOUT = 20
RUNTIME_HTTP_TIMEOUT = 10


def _enabled(value: str | None) -> bool:
    return str(value or "").lower() in ("1", "true", "yes", "on")


def _runtime_http_base_url(server_url: str) -> str:
    candidate = str(server_url or "").strip()
    if not candidate:
        return ""
    if candidate.startswith("ws://"):
        candidate = "http://" + candidate[len("ws://"):]
    elif candidate.startswith("wss://"):
        candidate = "https://" + candidate[len("wss://"):]
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/")
    if path.endswith("/ws"):
        path = path[:-3]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/"), "", "", "")).rstrip("/")


def _runtime_candidate_urls(server_url: str, path: str) -> List[str]:
    base_url = _runtime_http_base_url(server_url)
    if not base_url:
        return []
    clean_path = "/" + str(path or "").lstrip("/")
    candidates = [f"{base_url}{clean_path}"]
    if clean_path.startswith("/runtime/"):
        candidates.append(f"{base_url}/api{clean_path}")
    return candidates


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

        self._ws = None
        self._ws_loop: Optional[asyncio.AbstractEventLoop] = None
        self.trade_phase: str = "idle"
        self.cancel_round_requested: bool = False
        self.leave_requested: bool = False
        self.expected_signature: Optional[Dict[str, Any]] = None

        self.save_analysis: Dict[str, Dict[str, Any]] = {}
        self.server_url = self._load_server_url()
        self.language = DEFAULT_LANGUAGE
        self.theme = DEFAULT_THEME
        self._load_ui_config()

    def _configured_save_dirs(self) -> List[Path]:
        value = os.getenv("POKECABLE_SAVE_DIRS", "").strip()
        if not value:
            return []
        return [Path(part).expanduser() for part in value.split(os.pathsep) if part.strip()]

    def _default_save_dirs(self) -> List[Path]:
        tool_dir = Path(__file__).resolve().parent
        project_dir = tool_dir.parent
        home = Path.home()
        production_dirs = [
            tool_dir / "saves",
            home / "saves",
            home / "roms",
            home / "Saved Games",
            Path("/roms"),
            Path("/roms/gbc"),
            Path("/roms/gba"),
            Path("/roms2"),
            Path("/roms2/gbc"),
            Path("/roms2/gba"),
            Path("/opt/system"),
            Path("/opt/roms"),
            Path("/storage/roms"),
        ]
        dev_dirs = []
        if _enabled(os.getenv("POKECABLE_DEV")):
            dev_dirs = [
                project_dir / "roms" / "test-saves",
                project_dir / "roms",
                tool_dir,
                project_dir,
                Path.cwd(),
                home / "Downloads",
                home / "Documents",
                home / "Desktop",
                Path("/tmp"),
            ]
        return self._dedupe_paths(self._configured_save_dirs() + dev_dirs + production_dirs)

    @staticmethod
    def _dedupe_paths(paths: List[Path]) -> List[Path]:
        deduped: List[Path] = []
        seen = set()
        for path in paths:
            try:
                key = str(path.expanduser().resolve())
            except OSError:
                key = str(path.expanduser().absolute())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path.expanduser())
        return deduped

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

    def _load_ui_config(self) -> None:
        config_file = self.config_dir / "ui.conf"
        if not config_file.exists():
            return
        try:
            payload = json.loads(config_file.read_text())
            language = str(payload.get("language", DEFAULT_LANGUAGE)).strip().lower()
            theme = str(payload.get("theme", DEFAULT_THEME)).strip().lower()
            if language in SUPPORTED_LANGUAGES:
                self.language = language
            if theme in SUPPORTED_THEMES:
                self.theme = theme
        except Exception as exc:
            logger.warning("Failed to read ui.conf: %s", exc)

    def save_ui_config(self, language: str, theme: str) -> None:
        language = str(language or "").strip().lower()
        theme = str(theme or "").strip().lower()
        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE
        if theme not in SUPPORTED_THEMES:
            theme = DEFAULT_THEME
        payload = {"language": language, "theme": theme}
        config_file = self.config_dir / "ui.conf"
        try:
            config_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2))
            self.language = language
            self.theme = theme
        except Exception as exc:
            logger.error("Failed to save ui.conf: %s", exc)

    def runtime_http_base_url(self) -> str:
        return _runtime_http_base_url(self.server_url)

    def _runtime_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        urls = _runtime_candidate_urls(self.server_url, path)
        if not urls:
            raise SaveError("URL HTTP da API indisponivel para validar dados.")
        body = json.dumps(payload).encode("utf-8")
        errors: List[str] = []
        for url in urls:
            request = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json", "User-Agent": "PokeCable-R36S/1.0"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=RUNTIME_HTTP_TIMEOUT) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                errors.append(f"{url} -> HTTP {exc.code}")
                continue
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                errors.append(f"{url} -> {exc}")
                continue
        detail = "; ".join(errors) if errors else "sem detalhes"
        raise SaveError(f"API indisponivel para validar Pokemon: {detail}")

    def enrich_pokemon(self, save: SaveModel, pokemon_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not pokemon_list:
            return []
        response = self._runtime_post(
            "/runtime/enrich-pokemon",
            {
                "generation": save.generation,
                "game": save.game,
                "pokemon": pokemon_list,
            },
        )
        enriched = response.get("pokemon")
        if not isinstance(enriched, list) or len(enriched) != len(pokemon_list):
            raise SaveError("API retornou enriquecimento de Pokemon invalido.")
        for original, remote in zip(pokemon_list, enriched):
            if isinstance(remote, dict):
                original.update(remote)
        return pokemon_list

    def find_saves(self) -> List[Path]:
        self.saves = []
        seen = set()
        search_dirs = self._default_save_dirs()
        patterns = ["*.sav", "*.srm", "*.SAV", "*.SRM"]
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            try:
                for pattern in patterns:
                    for scoped_pattern in (pattern, f"*/{pattern}", f"*/*/{pattern}"):
                        for save_file in search_dir.glob(scoped_pattern):
                            if save_file.is_file():
                                key = str(save_file.resolve())
                                if key not in seen:
                                    seen.add(key)
                                    self.saves.append(save_file)
            except (PermissionError, OSError) as exc:
                logger.debug(f"Cannot access {search_dir}: {exc}")
        self.saves.sort()
        logger.info("Found %s save file(s) in %s search dir(s)", len(self.saves), len(search_dirs))
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

        save: SaveModel = analysis["save"]
        source_pokemon = save.get_pokemon(source)
        self.enrich_pokemon(save, source_pokemon)

        self.pokemon_list = []
        for pokemon in source_pokemon:
            species_id = int(pokemon.get("species_id") or 0)
            if species_id <= 0:
                continue
            self.pokemon_list.append(
                {
                    "index": pokemon.get("index"),
                    "name": pokemon.get("species_name", "Pokemon"),
                    "species_id": species_id,
                    "species_name": pokemon.get("species_name", "Pokemon"),
                    "national_dex_id": pokemon.get("national_dex_id"),
                    "types": pokemon.get("types", []),
                    "held_item_id": pokemon.get("held_item_id"),
                    "held_item_name": pokemon.get("held_item_name"),
                    "held_item_category": pokemon.get("held_item_category"),
                    "moves": pokemon.get("moves", []),
                    "move_names": pokemon.get("move_names", []),
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


def _open_party_selection(state: "PokecableState", ui: "PygameUI") -> None:
    """Abre a tela de escolha de origem (Party ou PC) para o usuario."""
    del state  # unused, mantido para assinatura uniforme
    ui.screen("select_pokemon_source")


_BACKUP_RETENTION = 20


def _prune_backups(backup_dir: Path, stem: str) -> None:
    try:
        candidates = sorted(
            backup_dir.glob(f"{stem}.*.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for stale in candidates[_BACKUP_RETENTION:]:
            try:
                stale.unlink()
            except Exception as exc:
                logger.debug("Failed to prune backup %s: %s", stale, exc)
    except Exception as exc:
        logger.debug("Backup prune scan failed: %s", exc)


def _create_backup(save_path: Path) -> Path:
    backup_dir = Path.home() / ".pokecable" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{save_path.stem}.{timestamp}{save_path.suffix}.bak"
    shutil.copy2(save_path, backup_path)
    logger.info(f"Backup: {backup_path}")
    _prune_backups(backup_dir, save_path.stem)
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


def _build_preflight(
    state: PokecableState,
    peer_payload: Dict[str, Any],
    save: SaveModel,
    server_preflight: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    reasons: List[str] = []
    warnings: List[str] = []
    server_preflight = server_preflight or {}
    if server_preflight:
        reasons.extend(str(reason) for reason in server_preflight.get("blocking_reasons", []) if reason)
        warnings.extend(str(warning) for warning in server_preflight.get("warnings", []) if warning)
    if not peer_payload:
        reasons.append("Oferta remota ausente.")
    if not state.selected_pokemon:
        reasons.append("Nenhum Pokémon local selecionado.")
    return {
        "compatible": not reasons,
        "mode": str(server_preflight.get("mode") or "same_generation"),
        "source_generation": save.generation,
        "target_generation": save.generation,
        "blocking_reasons": reasons,
        "warnings": warnings,
        "data_loss": [],
        "suggested_actions": [],
        "server_preflight": server_preflight,
        "trade_evolution": server_preflight.get("trade_evolution") or {},
    }


_GAME_DISPLAY_NAMES = {
    "red": "Pokemon Red",
    "blue": "Pokemon Blue",
    "yellow": "Pokemon Yellow",
    "gold": "Pokemon Gold",
    "silver": "Pokemon Silver",
    "crystal": "Pokemon Crystal",
    "ruby": "Pokemon Ruby",
    "sapphire": "Pokemon Sapphire",
    "emerald": "Pokemon Emerald",
    "firered": "Pokemon FireRed",
    "leafgreen": "Pokemon LeafGreen",
}


def _game_display_name(game: str, generation: int) -> str:
    key = (game or "").strip().lower()
    if key in _GAME_DISPLAY_NAMES:
        return _GAME_DISPLAY_NAMES[key]
    if key:
        return f"Pokemon {key.title()}"
    if generation:
        return f"Geracao {generation}"
    return "jogo do parceiro"


def _peer_player_name(room: Dict[str, Any], client_id: str = "", slot: str = "") -> str:
    players = dict((room or {}).get("players") or {})
    if not players:
        return ""
    local_slot = ""
    for player_slot, player in players.items():
        if client_id and str(player.get("client_id", "")) == str(client_id):
            local_slot = str(player_slot)
            break
        if slot and str(player_slot) == str(slot):
            local_slot = str(player_slot)
            break
    if local_slot:
        for player_slot, player in players.items():
            if str(player_slot) != local_slot:
                return str(player.get("name") or player.get("player_name") or "").strip()
    if len(players) == 2:
        for player in players.values():
            name = str(player.get("name") or player.get("player_name") or "").strip()
            if name:
                return name
    return ""


def _same_generation_room_error(room: Dict[str, Any], local_generation: int) -> str:
    del room, local_generation
    return ""


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
    state.expected_signature = analysis["signature"]

    ui.screen("connecting")
    ui.status(f"Conectando a {state.server_url}...")
    logger.info(
        "Trade session start: action=%s room=%s save=%s selected=%s",
        action,
        state.room_name,
        state.selected_save,
        state.selected_pokemon.get("location") if state.selected_pokemon else None,
    )

    ws = None
    try:
        last_connect_error: Optional[BaseException] = None
        for attempt in range(1, CONNECT_ATTEMPTS + 1):
            try:
                if attempt > 1:
                    ui.status(f"Tentando reconectar ao servidor... ({attempt}/{CONNECT_ATTEMPTS})")
                    await asyncio.sleep(1.5)
                logger.info("Opening websocket attempt=%s/%s url=%s", attempt, CONNECT_ATTEMPTS, state.server_url)
                ws = await websockets.connect(
                    state.server_url,
                    ping_interval=20,
                    ping_timeout=10,
                    open_timeout=CONNECT_OPEN_TIMEOUT,
                    family=socket.AF_INET,
                )
                logger.info("WebSocket handshake completed attempt=%s", attempt)
                state._ws = ws
                state._ws_loop = asyncio.get_running_loop()
                state.trade_phase = "waiting"
                break
            except (asyncio.TimeoutError, OSError, websockets.exceptions.WebSocketException) as exc:
                last_connect_error = exc
                logger.warning("WebSocket connect failed attempt=%s/%s error=%s", attempt, CONNECT_ATTEMPTS, exc)

        if ws is None:
            detail = f"{type(last_connect_error).__name__}: {last_connect_error}" if last_connect_error else "sem detalhe"
            logger.error("WebSocket handshake failed after retries: %s", detail)
            ui.error("Servidor WebSocket inacessível. Verifique internet/VPN/firewall e tente novamente.")
            return

        try:
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

            try:
                connected = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
                logger.info(f"WS initial message: {connected}")
                if connected.get("type") not in ("connected", "heartbeat"):
                    logger.info("WS initial message before room join: %s", connected.get("type"))
            except asyncio.TimeoutError:
                logger.warning("WS initial connected message not received; continuing with room message")

            logger.debug("Sending room message: %s", room_msg)
            await ws.send(json.dumps(room_msg))
            ui.screen("waiting_partner")
            ui.status("Acessando sala..." if action == "access" else ("Criando sala..." if action == "create" else "Entrando na sala..."))

            peer_offer: Dict[str, Any] = {}
            saved_pokemon: Dict[str, Any] = {}
            backup_path: Optional[Path] = None
            our_offer_sent = False
            room_ready = False
            selection_opened = False
            peer_generation: int = 0
            peer_game: str = ""
            cancel_trade_evolution = False
            trade_evolution: Dict[str, Any] = {}
            client_id = ""
            local_slot = ""

            while True:
                try:
                    raw_msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg = json.loads(raw_msg)
                    mtype = msg.get("type")
                    if msg.get("client_id"):
                        client_id = str(msg.get("client_id"))
                    if msg.get("slot"):
                        local_slot = str(msg.get("slot"))
                    logger.info(f"WS recv: {mtype}")
                    logger.debug(f"WS payload: {json.dumps(msg)[:500]}")
                except asyncio.TimeoutError:
                    msg = None
                    mtype = None

                if state.cancel_round_requested and state.trade_phase == "writing":
                    logger.warning("Ignoring cancel_round_requested during writing phase")
                    state.cancel_round_requested = False
                elif state.cancel_round_requested:
                    state.cancel_round_requested = False
                    if our_offer_sent:
                        logger.info("Sending cancel_trade_round (user requested round cancel)")
                        try:
                            await ws.send(json.dumps({"type": "cancel_trade_round", "reason": "user_cancelled"}))
                        except Exception as exc:
                            logger.warning("Failed to send cancel_trade_round: %s", exc)
                    else:
                        logger.info("Cancel before offer: navigating back, keeping room alive")
                        state.selected_pokemon = None
                        ui.status("")
                        _open_party_selection(state, ui)

                if room_ready and not our_offer_sent and state.selected_pokemon:
                    state.refresh_selected_save()
                    save = state.get_selected_save_model() or save
                    selected = state.selected_pokemon
                    pokemon_location = selected.get("location", "party:0")
                    if peer_generation:
                        try:
                            _ensure_backend_import_path()
                            from data.species import species_exists_in_generation
                            ndex = int(
                                selected.get("national_dex_id")
                                or (selected.get("raw") or {}).get("national_dex_id")
                                or 0
                            )
                            if ndex and not species_exists_in_generation(ndex, peer_generation):
                                species_name = selected.get("species_name") or selected.get("name") or "Este Pokemon"
                                game_label = _game_display_name(peer_game, peer_generation)
                                modal_msg = f"{species_name} (#{ndex}) nao existe em {game_label}. Escolha outro Pokemon para a troca."
                                logger.info("Pre-offer block: %s", modal_msg)
                                ui.ui_queue.put((
                                    "info_modal",
                                    {"title": "Pokemon indisponivel no parceiro", "message": modal_msg},
                                ))
                                await asyncio.to_thread(confirm_queue.get)
                                state.selected_pokemon = None
                                ui.status("")
                                _open_party_selection(state, ui)
                                continue
                        except Exception as exc:
                            logger.warning("Pre-offer species check failed (allowing offer): %s", exc)
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
                    room_error = _same_generation_room_error(msg.get("room", {}), save.generation)
                    if room_error:
                        ui.error(room_error)
                        return
                    if not selection_opened:
                        _open_party_selection(state, ui)
                        selection_opened = True
                    ui.status("Sala criada. Escolha o Pokemon e aguarde outro treinador...")
                    continue

                if mtype == "room_joined":
                    room_error = _same_generation_room_error(msg.get("room", {}), save.generation)
                    if room_error:
                        ui.error(room_error)
                        return
                    if not selection_opened:
                        _open_party_selection(state, ui)
                        selection_opened = True
                    ui.status("Entrou na sala. Escolha o Pokemon para a troca...")
                    continue

                if mtype == "room_waiting":
                    ui.status(msg.get("message", "Aguardando outro jogador..."))
                    continue

                if mtype == "room_ready":
                    room_error = _same_generation_room_error(msg.get("room", {}), save.generation)
                    if room_error:
                        ui.error(room_error)
                        return
                    room_ready = True
                    room_info = msg.get("room", {}) or {}
                    for slot_name, player in (room_info.get("players") or {}).items():
                        if str(slot_name) == str(local_slot) or (client_id and str(player.get("client_id", "")) == str(client_id)):
                            continue
                        peer_generation = int(player.get("generation") or 0)
                        peer_game = str(player.get("game") or "")
                        break
                    if not selection_opened:
                        _open_party_selection(state, ui)
                        selection_opened = True
                    if not state.selected_pokemon:
                        peer_name = _peer_player_name(room_info, client_id, local_slot)
                        ui.status(f"{peer_name}: escolha Pokemon" if peer_name else "Escolha Pokemon")
                    continue

                if mtype == "offer_received":
                    ui.screen("trading")
                    ui.status("Oferta enviada. Aguardando o outro treinador...")
                    continue

                if mtype == "peer_offer_received":
                    peer_offer = msg.get("offer", {}) or {}
                    summary = peer_offer.get("display_summary") or peer_offer.get("nickname") or peer_offer.get("species_name") or "Pokémon"
                    if state.selected_pokemon:
                        ui.screen("trading")
                        ui.status(f"Oferta recebida: {summary}")
                    else:
                        if not selection_opened:
                            _open_party_selection(state, ui)
                            selection_opened = True
                        ui.status(f"{summary} recebido. Escolha o seu.")
                    continue

                if mtype == "offers_ready":
                    ui.screen("trading")
                    ui.status("Ofertas prontas. Validando compatibilidade...")
                    continue

                if mtype == "preflight_required":
                    server_preflight = msg.get("server_preflight") if isinstance(msg.get("server_preflight"), dict) else {}
                    if not server_preflight:
                        try:
                            server_preflight = state._runtime_post(
                                "/runtime/trade-preflight",
                                {
                                    "received_payload": msg.get("received_payload") or peer_offer,
                                    "target_generation": save.generation,
                                    "target_game": save.game,
                                },
                            )
                        except SaveError as exc:
                            ui.error(str(exc))
                            return
                    if server_preflight.get("trade_evolution"):
                        trade_evolution = dict(server_preflight.get("trade_evolution") or {})
                    report = _build_preflight(state, msg.get("received_payload") or peer_offer, save, server_preflight)
                    logger.debug("Preflight report: %s", report)
                    if not report["compatible"]:
                        reason_text = "; ".join(report["blocking_reasons"]) or "Troca incompativel."
                        logger.info("Preflight blocked locally: %s", reason_text)
                        ui.ui_queue.put((
                            "info_modal",
                            {"title": "Troca incompativel", "message": reason_text},
                        ))
                        await asyncio.to_thread(confirm_queue.get)
                        logger.info("User acknowledged preflight block")
                        try:
                            await ws.send(json.dumps({"type": "cancel_trade_round", "reason": "preflight_blocked"}))
                        except Exception as exc:
                            logger.warning("Failed to send cancel_trade_round after preflight block: %s", exc)
                        continue
                    await ws.send(
                        json.dumps(
                            {
                                "type": "preflight_result",
                                "compatible": True,
                                "requires_user_confirmation": False,
                                "report": report,
                                "error": "",
                            }
                        )
                    )
                    ui.status("Compatibilidade validada. Aguardando confirmação...")
                    continue

                if mtype == "preflight_ready":
                    incoming_payload = msg.get("received_payload") or peer_offer
                    summary = incoming_payload.get("display_summary") or incoming_payload.get("nickname") or incoming_payload.get("species_name") or "parceiro"
                    server_preflight = msg.get("server_preflight") if isinstance(msg.get("server_preflight"), dict) else {}
                    trade_evolution = dict(msg.get("trade_evolution") or server_preflight.get("trade_evolution") or trade_evolution or {})
                    if trade_evolution.get("evolved"):
                        ui.ui_queue.put(("evolution_cancel_prompt", trade_evolution))
                        logger.info("Waiting for evolution cancel decision: %s", trade_evolution)
                        cancel_trade_evolution = bool(await asyncio.to_thread(confirm_queue.get))
                        logger.info("Evolution cancel decision: %s", cancel_trade_evolution)
                    removed_moves = list(server_preflight.get("removed_moves") or [])
                    resolved_moves: Dict[int, int] = {}
                    if removed_moves:
                        ui.ui_queue.put(("resolve_moves_prompt", {"removed_moves": removed_moves}))
                        logger.info("Waiting for move resolution: %s removed moves", len(removed_moves))
                        choice = await asyncio.to_thread(confirm_queue.get)
                        if isinstance(choice, dict):
                            resolved_moves = {int(k): int(v) for k, v in choice.items() if v}
                        logger.info("Move resolution received: %s", resolved_moves)
                    ui.screen("trade_confirm")
                    ui.status(f"Pronto para trocar com {summary}")
                    ui.ui_queue.put(("confirm_prompt", incoming_payload))
                    logger.info("Waiting for local confirmation: peer=%s", summary)
                    user_confirmed = await asyncio.to_thread(confirm_queue.get)
                    logger.info("Local confirmation result: %s", user_confirmed)
                    if not user_confirmed:
                        await ws.send(json.dumps({"type": "cancel_trade_round", "reason": "user_cancelled"}))
                        ui.status("Troca cancelada")
                        return
                    ui.screen("trading")
                    ui.status("Confirmação enviada. Aguardando o outro treinador...")
                    await ws.send(json.dumps({"type": "confirm_trade", "resolved_moves": resolved_moves}))
                    continue

                if mtype == "trade_blocked":
                    reason_text = msg.get("message") or "Troca bloqueada pelo parceiro."
                    logger.info("Trade blocked by server/peer: %s", reason_text)
                    ui.ui_queue.put((
                        "info_modal",
                        {"title": "Troca incompativel", "message": reason_text},
                    ))
                    await asyncio.to_thread(confirm_queue.get)
                    our_offer_sent = False
                    state.selected_pokemon = None
                    ui.status("")
                    _open_party_selection(state, ui)
                    continue

                if mtype == "trade_confirmed":
                    ui.screen("trading")
                    ui.status("Confirmação registrada. Preparando gravação...")
                    continue

                if mtype == "prepare_write":
                    state.trade_phase = "writing"
                    server_preflight = msg.get("server_preflight") if isinstance(msg.get("server_preflight"), dict) else {}
                    trade_evolution = dict(msg.get("trade_evolution") or server_preflight.get("trade_evolution") or trade_evolution or {})
                    logger.info("Prepare write received for save=%s", state.selected_save)
                    if state.expected_signature is None or not _save_unchanged_on_disk(state.expected_signature, state.selected_save):
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "write_ready",
                                    "ready": False,
                                    "error": "save_changed_during_room",
                                    "metadata": {
                                        "message": "O save mudou em disco antes da gravação.",
                                        "expected_signature": state.expected_signature,
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
                    sig = state.expected_signature or {"size": 0, "sha256": ""}
                    await ws.send(
                        json.dumps(
                            {
                                "type": "write_ready",
                                "ready": True,
                                "metadata": {
                                    "save_name": state.selected_save.name,
                                    "size": sig.get("size", 0),
                                    "sha256": sig.get("sha256", ""),
                                },
                            }
                        )
                    )
                    continue

                if mtype == "trade_commit_write":
                    ui.screen("trading")
                    ui.status("Aplicando troca ao save...")
                    received_payload = msg.get("received_payload") or peer_offer
                    server_preflight = msg.get("server_preflight") if isinstance(msg.get("server_preflight"), dict) else {}
                    trade_evolution = dict(msg.get("trade_evolution") or server_preflight.get("trade_evolution") or trade_evolution or {})
                    try:
                        logger.info("Applying received payload to location=%s", pokemon_location)
                        saved_pokemon = save.apply_payload(
                            pokemon_location,
                            received_payload,
                            trade_evolution=trade_evolution,
                            cancel_trade_evolution=cancel_trade_evolution,
                        )
                        save.write_to_disk()
                        refreshed = state.refresh_selected_save()
                        if refreshed:
                            state.expected_signature = refreshed["signature"]
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
                        evolution = saved_pokemon.get("trade_evolution") or {}
                        logger.info("Write completed: %s", summary)
                        if evolution.get("evolved"):
                            ui.status(f"{evolution.get('source_name')} evoluiu para {evolution.get('target_name')}!")
                        elif evolution.get("cancelled"):
                            ui.status(f"Evolucao de {evolution.get('source_name', 'Pokemon')} cancelada.")
                        else:
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
                            "received": saved_pokemon,
                            "save": str(state.selected_save),
                            "backup": str(backup_path) if backup_path else "",
                        }
                    )
                    our_offer_sent = False
                    state.selected_pokemon = None
                    peer_offer = {}
                    saved_pokemon = {}
                    trade_evolution = {}
                    backup_path = None
                    state.trade_phase = "waiting"
                    continue

                if mtype == "trade_write_failed":
                    ui.error(msg.get("error", "Falha remota na gravação"))
                    return

                if mtype == "trade_round_cancelled":
                    logger.info("Server confirmed trade_round_cancelled: %s", msg.get("reason"))
                    our_offer_sent = False
                    state.selected_pokemon = None
                    ui.status("Troca cancelada. Escolha outro Pokemon.")
                    _open_party_selection(state, ui)
                    continue

                if mtype == "trade_cancelled":
                    ui.error(msg.get("message", "Troca cancelada"))
                    return
        finally:
            await ws.close()

    except websockets.exceptions.ConnectionClosed as exc:
        if state.leave_requested:
            logger.info("WebSocket closed by user leave request")
        else:
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
    finally:
        state._ws = None
        state._ws_loop = None
        state.trade_phase = "idle"
        state.cancel_round_requested = False
        state.leave_requested = False
        state.expected_signature = None
        # destrava qualquer asyncio.to_thread(confirm_queue.get) ainda pendente
        try:
            confirm_queue.put_nowait(None)
        except Exception:
            pass


def request_leave_room(state: PokecableState) -> bool:
    """Gracefully close the trade ws, ending the session and freeing the room."""
    ws = state._ws
    loop = state._ws_loop
    if ws is None or loop is None:
        return False
    if state.trade_phase == "writing":
        logger.warning("Leave ignored: save write in progress")
        return False
    state.leave_requested = True
    async def _close():
        try:
            await ws.close()
        except Exception as exc:
            logger.debug("Leave close failed (ignored): %s", exc)
    try:
        asyncio.run_coroutine_threadsafe(_close(), loop)
        return True
    except Exception as exc:
        logger.warning("Failed to schedule leave: %s", exc)
        return False


def request_trade_cancel(state: PokecableState) -> bool:
    """Safe cancel of the current round: keeps the room/ws alive so user can re-pick a Pokémon.

    Only honoured before the save write begins (phase != 'writing').
    The trade thread observes `cancel_round_requested` and sends `cancel_trade_round`.
    """
    phase = state.trade_phase
    if phase in ("idle", "writing", "done"):
        logger.warning("Cancel ignored in phase=%s", phase)
        return False
    if state._ws is None:
        logger.warning("Cancel requested but no active ws")
        return False
    state.cancel_round_requested = True
    logger.info("Round cancel flag set (phase=%s)", phase)
    return True


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
