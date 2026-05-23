from __future__ import annotations

import json
import logging
import os
import queue
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from pokecable_save import SaveError, SaveModel

logger = logging.getLogger("r36s_pokecable_core")

LAN_PORT = int(os.getenv("POKECABLE_LAN_PORT", "8765"))
LAN_DISCOVERY_PORT = int(os.getenv("POKECABLE_LAN_DISCOVERY_PORT", "8766"))
LAN_DISCOVERY_SECONDS = float(os.getenv("POKECABLE_LAN_DISCOVERY_SECONDS", "2.8"))
LAN_MAGIC = "pokecable-lan-v1"


class JsonLineConnection:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.sock.settimeout(0.35)
        self._send_lock = threading.Lock()
        self._buffer = b""

    def close(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def send(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8") + b"\n"
        with self._send_lock:
            self.sock.sendall(data)

    def recv(self) -> Optional[Dict[str, Any]]:
        while b"\n" not in self._buffer:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                return None
            if not chunk:
                raise ConnectionError("peer disconnected")
            self._buffer += chunk
        raw, self._buffer = self._buffer.split(b"\n", 1)
        if not raw.strip():
            return None
        return json.loads(raw.decode("utf-8"))


def _local_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return str(probe.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        probe.close()


def _local_ip_candidates() -> set[str]:
    candidates = {"127.0.0.1", "localhost", _local_ip()}
    try:
        candidates.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return {candidate for candidate in candidates if candidate}


def _parse_endpoint(value: str) -> tuple[str, int]:
    endpoint = str(value or "").strip()
    if not endpoint:
        raise ValueError("endpoint vazio")
    if ":" in endpoint:
        host, port_text = endpoint.rsplit(":", 1)
        port = int(port_text.strip())
    else:
        host = endpoint
        port = LAN_PORT
    host = host.strip()
    if not host or port <= 0 or port > 65535:
        raise ValueError("endpoint invalido")
    return host, port


def _open_party_selection(state, ui) -> None:
    from r36s_pokecable_core import _open_party_selection as open_selection

    open_selection(state, ui)


def _same_generation_precheck(selected: Dict[str, Any], peer_generation: int, peer_game: str, ui, confirm_queue) -> bool:
    if not peer_generation:
        return True
    try:
        from pokecable_save import _ensure_backend_import_path

        _ensure_backend_import_path()
        from data.species import species_exists_in_generation  # type: ignore
        from r36s_pokecable_core import _game_display_name

        ndex = int(selected.get("national_dex_id") or (selected.get("raw") or {}).get("national_dex_id") or 0)
        if ndex and not species_exists_in_generation(ndex, peer_generation):
            species_name = selected.get("species_name") or selected.get("name") or "Este Pokemon"
            game_label = _game_display_name(peer_game, peer_generation)
            msg = f"{species_name} (#{ndex}) nao existe em {game_label}. Escolha outro Pokemon para a troca."
            ui.ui_queue.put(("info_modal", {"title": "Pokemon indisponivel no parceiro", "message": msg}))
            confirm_queue.get()
            return False
    except Exception as exc:
        logger.warning("LAN pre-offer species check failed; allowing offer: %s", exc)
    return True


def _load_selected_save(state) -> tuple[SaveModel, Dict[str, Any]]:
    if not state.selected_save:
        raise SaveError("Nenhum save selecionado")
    analysis = state.analyze_save(state.selected_save)
    if not analysis:
        raise SaveError("Falha ao analisar o save local")
    return analysis["save"], analysis["signature"]


def _discover_room(local_token: str, stop_event: threading.Event | None = None) -> Optional[Dict[str, Any]]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", LAN_DISCOVERY_PORT))
        sock.settimeout(0.25)
        deadline = time.monotonic() + LAN_DISCOVERY_SECONDS
        while time.monotonic() < deadline:
            if stop_event is not None and stop_event.is_set():
                return None
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                msg = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if msg.get("magic") != LAN_MAGIC or msg.get("token") == local_token:
                continue
            host = str(msg.get("host") or addr[0])
            port = int(msg.get("port") or 0)
            if port <= 0:
                continue
            msg["host"] = host
            msg["addr"] = addr[0]
            return msg
    finally:
        sock.close()
    return None


def _open_discovery_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", LAN_DISCOVERY_PORT))
    sock.settimeout(0.05)
    return sock


def _recv_room_advert(sock: socket.socket, local_token: str) -> Optional[Dict[str, Any]]:
    try:
        data, addr = sock.recvfrom(4096)
    except socket.timeout:
        return None
    try:
        msg = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if msg.get("magic") != LAN_MAGIC or msg.get("token") == local_token:
        return None
    host = str(msg.get("host") or addr[0])
    port = int(msg.get("port") or 0)
    if port <= 0:
        return None
    msg["host"] = host
    msg["addr"] = addr[0]
    return msg


def _announce_room(stop_event: threading.Event, room: Dict[str, Any]) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        payload = json.dumps(room, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        while not stop_event.is_set():
            try:
                sock.sendto(payload, ("255.255.255.255", LAN_DISCOVERY_PORT))
            except OSError as exc:
                logger.debug("LAN announce failed: %s", exc)
            stop_event.wait(0.75)
    finally:
        sock.close()


def _bind_server() -> tuple[socket.socket, int]:
    last_error: Optional[BaseException] = None
    for port in range(LAN_PORT, LAN_PORT + 10):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", port))
            sock.listen(1)
            sock.settimeout(0.35)
            return sock, port
        except OSError as exc:
            last_error = exc
            sock.close()
    raise OSError(f"Nao foi possivel abrir porta LAN: {last_error}")


def _connect_or_host(state, save: SaveModel, ui, stop_event: threading.Event) -> Optional[tuple[JsonLineConnection, str]]:
    local_token = uuid.uuid4().hex
    ui.screen("connecting")
    ui.status("Procurando sala local na rede...")
    found = _discover_room(local_token, stop_event)
    if stop_event.is_set():
        return None
    if found and not stop_event.is_set():
        host = str(found["host"])
        port = int(found["port"])
        ui.status(f"Conectando na sala LAN {host}:{port}...")
        sock = socket.create_connection((host, port), timeout=8)
        state.room_name = "Sala LAN"
        state.room_password = f"{host}:{port}"
        return JsonLineConnection(sock), "client"

    server, port = _bind_server()
    ip = _local_ip()
    state.room_name = "Sala LAN"
    state.room_password = f"{ip}:{port}"
    ui.status(f"Sala local criada em {ip}:{port}. Aguardando outro R36S...")
    _open_party_selection(state, ui)

    announce_stop = threading.Event()
    room = {
        "magic": LAN_MAGIC,
        "token": local_token,
        "room_id": local_token,
        "host": ip,
        "port": port,
        "player_name": save.player_name or os.environ.get("USER", "Treinador"),
        "generation": save.generation,
        "game": save.game,
    }
    announcer = threading.Thread(target=_announce_room, args=(announce_stop, room), daemon=True)
    announcer.start()
    discovery_sock = _open_discovery_socket()
    try:
        while not stop_event.is_set():
            if state.cancel_round_requested:
                state.cancel_round_requested = False
                state.selected_pokemon = None
                ui.status("")
                _open_party_selection(state, ui)
            manual_endpoint = str(getattr(state, "lan_manual_endpoint", "") or "").strip()
            if manual_endpoint:
                state.lan_manual_endpoint = ""
                try:
                    host, peer_port = _parse_endpoint(manual_endpoint)
                    if peer_port == port and host in _local_ip_candidates():
                        raise ValueError("este e o IP desta sala")
                    ui.status(f"Conectando em {host}:{peer_port}...")
                    sock = socket.create_connection((host, peer_port), timeout=8)
                    server.close()
                    state.room_password = f"{host}:{peer_port}"
                    return JsonLineConnection(sock), "client"
                except Exception as exc:
                    logger.warning("Manual LAN endpoint failed: %s", exc)
                    ui.screen("waiting_partner")
                    ui.status(f"Nao foi possivel conectar em {manual_endpoint}. Confira IP/porta.")
            advert = _recv_room_advert(discovery_sock, local_token)
            if advert and str(advert.get("room_id") or advert.get("token") or "") < local_token:
                host = str(advert["host"])
                peer_port = int(advert["port"])
                ui.status(f"Sala LAN encontrada em {host}:{peer_port}. Entrando...")
                server.close()
                sock = socket.create_connection((host, peer_port), timeout=8)
                state.room_password = f"{host}:{peer_port}"
                return JsonLineConnection(sock), "client"
            try:
                client, addr = server.accept()
                logger.info("LAN client connected from %s", addr)
                return JsonLineConnection(client), "host"
            except socket.timeout:
                continue
    finally:
        announce_stop.set()
        discovery_sock.close()
        try:
            server.close()
        except OSError:
            pass
    return None


def _preflight_for_incoming(state, incoming_payload: Dict[str, Any], save: SaveModel) -> tuple[Dict[str, Any], Dict[str, Any]]:
    from r36s_pokecable_core import _self_trade_evolution_preview_for_target, _trade_preflight_for_target

    preflight = _trade_preflight_for_target(state, incoming_payload, save)
    evolution = dict(preflight.get("trade_evolution") or {})
    if not evolution:
        evolution = _self_trade_evolution_preview_for_target(incoming_payload, save)
        if evolution:
            preflight["trade_evolution"] = evolution
    return preflight, evolution


def _blocking_message(preflight: Dict[str, Any]) -> str:
    from r36s_pokecable_core import _preflight_block_message

    return _preflight_block_message(preflight)


def _confirm_incoming_trade(
    ui,
    confirm_queue: queue.Queue,
    incoming_payload: Dict[str, Any],
    preflight: Dict[str, Any],
    evolution: Dict[str, Any],
    outgoing_item_relocation: Dict[str, Any],
    outgoing_pokemon: Dict[str, Any],
) -> tuple[bool, bool, Dict[int, int], str | None]:
    cancel_evolution = False
    resolved_moves: Dict[int, int] = {}
    item_relocation_choice: str | None = None
    if evolution.get("evolved"):
        ui.ui_queue.put(("evolution_cancel_prompt", evolution))
        cancel_evolution = bool(confirm_queue.get())

    item_relocation = dict(outgoing_item_relocation or {})
    if item_relocation.get("status") == "choose_destination":
        ui.ui_queue.put(("resolve_item_prompt", {"item_relocation": item_relocation, "pokemon": dict(outgoing_pokemon or {})}))
        choice = confirm_queue.get()
        if isinstance(choice, str) and choice.strip().lower() in {"bag", "pc", "remove"}:
            item_relocation_choice = choice.strip().lower()

    removed_moves = list(preflight.get("removed_moves") or [])
    if removed_moves:
        ui.ui_queue.put(
            (
                "resolve_moves_prompt",
                {
                    "removed_moves": removed_moves,
                    "pokemon": dict(incoming_payload or {}),
                    "target_generation": int(preflight.get("target_generation") or 0),
                    "target_game": str(preflight.get("target_game") or ""),
                    "trade_evolution": dict(evolution or {}),
                    "cancel_evolution": bool(cancel_evolution),
                },
            )
        )
        choice = confirm_queue.get()
        if isinstance(choice, dict):
            resolved_moves = {int(k): int(v) for k, v in choice.items() if v}

    summary = incoming_payload.get("display_summary") or incoming_payload.get("nickname") or incoming_payload.get("species_name") or "parceiro"
    ui.screen("trade_confirm")
    ui.status(f"Pronto para trocar com {summary}")
    ui.ui_queue.put(("confirm_prompt", incoming_payload))
    confirmed = bool(confirm_queue.get())
    return confirmed, cancel_evolution, resolved_moves, item_relocation_choice


def run_lan_trade(state, ui, confirm_queue: queue.Queue, stop_event: threading.Event) -> None:
    from r36s_pokecable_core import _create_backup, _local_outgoing_item_relocation, _save_unchanged_on_disk

    save, signature = _load_selected_save(state)
    state.expected_signature = signature
    state.trade_phase = "waiting"

    connected = _connect_or_host(state, save, ui, stop_event)
    if not connected:
        return
    conn, role = connected
    state._lan_connection = conn
    logger.info("LAN trade connected as %s", role)

    hello = {
        "type": "hello",
        "player_name": save.player_name or os.environ.get("USER", "Treinador"),
        "generation": save.generation,
        "game": save.game,
    }
    conn.send(hello)
    peer_generation = 0
    peer_game = ""

    peer_offer: Dict[str, Any] = {}
    local_offer: Dict[str, Any] = {}
    local_location = ""
    local_offer_sent = False
    local_preflight_sent = False
    local_preflight: Dict[str, Any] = {}
    local_evolution: Dict[str, Any] = {}
    peer_preflight: Dict[str, Any] = {}
    local_confirm_sent = False
    peer_confirm: Dict[str, Any] = {}
    cancel_evolution = False
    resolved_moves: Dict[int, int] = {}
    item_relocation_choice: str | None = None
    local_item_relocation: Dict[str, Any] = {}
    local_write_ready = False
    peer_write_ready = False
    wrote_local = False
    peer_write_done = False
    backup_path: Optional[Path] = None
    saved_pokemon: Dict[str, Any] = {}

    def reset_round(message: str = "", open_selection: bool = True) -> None:
        nonlocal peer_offer, local_offer, local_location, local_offer_sent, local_preflight_sent
        nonlocal local_preflight, local_evolution, peer_preflight, local_confirm_sent, peer_confirm
        nonlocal cancel_evolution, resolved_moves, item_relocation_choice, local_item_relocation, local_write_ready, peer_write_ready
        nonlocal wrote_local, peer_write_done, backup_path, saved_pokemon
        peer_offer = {}
        local_offer = {}
        local_location = ""
        local_offer_sent = False
        local_preflight_sent = False
        local_preflight = {}
        local_evolution = {}
        peer_preflight = {}
        local_confirm_sent = False
        peer_confirm = {}
        cancel_evolution = False
        resolved_moves = {}
        item_relocation_choice = None
        local_item_relocation = {}
        local_write_ready = False
        peer_write_ready = False
        wrote_local = False
        peer_write_done = False
        backup_path = None
        saved_pokemon = {}
        state.selected_pokemon = None
        state.trade_phase = "waiting"
        if message:
            ui.status(message)
        if open_selection:
            _open_party_selection(state, ui)

    try:
        _open_party_selection(state, ui)
        while not stop_event.is_set():
            if state.leave_requested:
                conn.send({"type": "leave_room"})
                return

            if state.cancel_round_requested and state.trade_phase != "writing":
                state.cancel_round_requested = False
                conn.send({"type": "cancel_trade_round", "reason": "user_cancelled"})
                reset_round("Troca cancelada. Escolha outro Pokemon.")
                continue

            if peer_generation and state.selected_pokemon and not local_offer_sent:
                state.refresh_selected_save()
                save = state.get_selected_save_model() or save
                selected = state.selected_pokemon
                if not _same_generation_precheck(selected, peer_generation, peer_game, ui, confirm_queue):
                    reset_round("")
                    continue
                local_location = str(selected.get("location") or "party:0")
                local_offer = save.export_payload(local_location)
                conn.send({"type": "offer_pokemon", "payload": local_offer})
                local_offer_sent = True
                ui.screen("trading")
                ui.status("Oferta enviada. Aguardando o outro R36S...")

            try:
                msg = conn.recv()
            except (OSError, ConnectionError) as exc:
                if stop_event.is_set() or state.leave_requested:
                    return
                raise SaveError(f"Conexao LAN fechada: {exc}") from exc
            if msg:
                mtype = str(msg.get("type") or "")
                logger.info("LAN recv: %s", mtype)
                if mtype == "hello":
                    peer_generation = int(msg.get("generation") or 0)
                    peer_game = str(msg.get("game") or "")
                    ui.status("Conectado por LAN. Escolha o Pokemon para a troca.")
                    _open_party_selection(state, ui)
                elif mtype == "offer_pokemon":
                    peer_offer = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                    summary = peer_offer.get("display_summary") or peer_offer.get("nickname") or peer_offer.get("species_name") or "Pokemon"
                    if state.selected_pokemon:
                        ui.screen("trading")
                        ui.status(f"Oferta recebida: {summary}")
                    else:
                        ui.status(f"{summary} recebido. Escolha o seu.")
                        _open_party_selection(state, ui)
                elif mtype == "preflight_result":
                    peer_preflight = msg if isinstance(msg, dict) else {}
                    if not peer_preflight.get("compatible", False):
                        reason = str(peer_preflight.get("error") or "Troca bloqueada pelo outro R36S.")
                        ui.ui_queue.put(("info_modal", {"title": "Troca incompativel", "message": reason}))
                        confirm_queue.get()
                        reset_round("Troca cancelada. Escolha outro Pokemon.")
                elif mtype == "confirm_trade":
                    peer_confirm = msg if isinstance(msg, dict) else {}
                    if not peer_confirm.get("confirmed", False):
                        reset_round("Troca cancelada pelo outro R36S.")
                elif mtype == "write_ready":
                    peer_write_ready = bool(msg.get("ready"))
                    if not peer_write_ready:
                        raise SaveError(str(msg.get("error") or "Outro R36S nao conseguiu preparar a gravacao."))
                elif mtype == "write_done":
                    peer_write_done = bool(msg.get("success", True))
                elif mtype == "write_failed":
                    if wrote_local and backup_path and backup_path.exists() and state.selected_save:
                        import shutil

                        shutil.copy2(backup_path, state.selected_save)
                    raise SaveError(str(msg.get("error") or "Falha remota na gravacao."))
                elif mtype == "cancel_trade_round":
                    reset_round("Troca cancelada pelo outro R36S.")
                elif mtype == "leave_room":
                    ui.error("O outro R36S saiu da sala.")
                    return
                elif mtype == "error":
                    raise SaveError(str(msg.get("message") or "Erro na sala LAN."))

            if peer_offer and local_offer_sent and not local_preflight_sent:
                local_preflight, local_evolution = _preflight_for_incoming(state, peer_offer, save)
                block = _blocking_message(local_preflight)
                if block:
                    conn.send({"type": "preflight_result", "compatible": False, "error": block})
                    ui.ui_queue.put(("info_modal", {"title": "Troca incompativel", "message": block}))
                    confirm_queue.get()
                    reset_round("Troca cancelada. Escolha outro Pokemon.")
                    continue
                conn.send(
                    {
                        "type": "preflight_result",
                        "compatible": True,
                        "preflight": local_preflight,
                        "trade_evolution": local_evolution,
                    }
                )
                local_preflight_sent = True
                ui.status("Compatibilidade validada. Aguardando confirmacao...")

            if (
                local_preflight_sent
                and peer_preflight.get("compatible") is True
                and not local_confirm_sent
                and peer_offer
            ):
                local_item_relocation = _local_outgoing_item_relocation(local_offer, save, int(peer_generation or 0))
                if local_item_relocation.get("status") == "manual_remove_required":
                    reason = str(local_item_relocation.get("reason") or "Remova o item do Pokemon antes de transferir.")
                    ui.ui_queue.put(("info_modal", {"title": "Item incompatível", "message": reason}))
                    confirm_queue.get()
                    conn.send({"type": "cancel_trade_round", "reason": "item_relocation_blocked"})
                    reset_round("Troca cancelada. Escolha outro Pokemon.")
                    continue
                confirmed, cancel_evolution, resolved_moves, item_relocation_choice = _confirm_incoming_trade(
                    ui,
                    confirm_queue,
                    peer_offer,
                    local_preflight,
                    local_evolution,
                    local_item_relocation,
                    local_offer,
                )
                local_confirm_sent = True
                conn.send(
                    {
                        "type": "confirm_trade",
                        "confirmed": bool(confirmed),
                        "cancel_evolution": bool(cancel_evolution),
                        "resolved_moves": resolved_moves,
                        "item_relocation_choice": item_relocation_choice or "",
                    }
                )
                if not confirmed:
                    ui.status("Troca cancelada.")
                    return
                ui.screen("trading")
                ui.status("Confirmacao enviada. Aguardando o outro R36S...")

            if local_confirm_sent and peer_confirm.get("confirmed") and not local_write_ready:
                state.trade_phase = "writing"
                if state.expected_signature is None or not _save_unchanged_on_disk(state.expected_signature, state.selected_save):
                    conn.send({"type": "write_ready", "ready": False, "error": "O save mudou em disco."})
                    raise SaveError("O save mudou em disco. Recarregue e tente novamente.")
                backup_path = _create_backup(state.selected_save)
                conn.send({"type": "write_ready", "ready": True, "backup": str(backup_path)})
                local_write_ready = True
                ui.status(f"Backup criado: {backup_path.name}")

            if local_write_ready and peer_write_ready and not wrote_local:
                try:
                    ui.status("Aplicando troca ao save...")
                    saved_pokemon = save.apply_payload(
                        local_location,
                        peer_offer,
                        outgoing_payload=local_offer,
                        trade_evolution=local_evolution or local_preflight.get("trade_evolution") or {},
                        cancel_trade_evolution=cancel_evolution,
                        resolved_moves=resolved_moves,
                        item_relocation_choice=item_relocation_choice,
                    )
                    save.write_to_disk()
                    refreshed = state.refresh_selected_save()
                    if refreshed:
                        state.expected_signature = refreshed["signature"]
                    wrote_local = True
                    conn.send({"type": "write_done", "success": True})
                except Exception as exc:
                    logger.exception("LAN write failed: %s", exc)
                    conn.send({"type": "write_failed", "error": str(exc)})
                    raise

            if wrote_local and peer_write_done:
                ui.screen("trade_result")
                ui.status("Troca LAN concluida!")
                ui.result(
                    {
                        "success": True,
                        "peer": peer_offer,
                        "received": saved_pokemon,
                        "save": str(state.selected_save),
                        "backup": str(backup_path) if backup_path else "",
                    }
                )
                reset_round(open_selection=False)
    finally:
        conn.close()
