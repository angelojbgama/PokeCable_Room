#!/usr/bin/env python3
"""
PokeCable R36S - Core logic for trade management
Handles state management, Pokémon loading, and WebSocket communication
"""

import os
import sys
import json
import asyncio
import logging
import threading
import queue
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests

DEBUG = os.getenv("POKECABLE_DEBUG", "0").lower() in ("1", "true", "yes")
logger = logging.getLogger(__name__)

if DEBUG:
    logger.setLevel(logging.DEBUG)

class PokecableState:
    """Gerencia o estado da aplicação"""

    def __init__(self, saves_dir: Path = None, backend_dir: Path = None):
        self.saves_dir = saves_dir or Path.home() / "saves"
        self.backend_dir = backend_dir or Path(__file__).parent.parent / "backend"
        self.config_dir = Path.home() / ".pokecable"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Add backend to sys.path immediately so parsers can be imported
        backend_str = str(self.backend_dir)
        if backend_str not in sys.path:
            sys.path.insert(0, backend_str)

        self.screen = "menu"
        self.menu_index = 0
        self.saves: List[Path] = []
        self.selected_save: Optional[Path] = None
        self.selected_pokemon: Optional[Dict[str, Any]] = None
        self.pokemon_list: List[Dict[str, Any]] = []
        self.room_name = ""
        self.room_password = ""
        self.server_url = self._load_server_url()
        self.pokemon_source = "party"

    def _load_server_url(self) -> str:
        """Load server URL from config"""
        config_file = self.config_dir / "server.conf"
        if config_file.exists():
            try:
                return config_file.read_text().strip()
            except Exception:
                pass
        return "wss://9kernel.vps-kinghost.net/ws"

    def save_server_url(self, url: str) -> None:
        """Save server URL to config"""
        config_file = self.config_dir / "server.conf"
        try:
            config_file.write_text(url)
        except Exception:
            pass

    def find_saves(self) -> List[Path]:
        """Find all available save files (search with 'pokemon' in name)"""
        self.saves = []

        # Diretórios a procurar (ordem de prioridade)
        search_dirs = [
            Path("/roms"),
            Path("/roms/gbc"),
            Path("/roms/gba"),
            Path("/opt/system"),
            Path("/opt/roms"),
            Path.home() / "saves",
            Path.home() / "roms",
            Path.home() / "Downloads",
            Path("/tmp"),
            Path("/home"),
        ]

        # Procurar por arquivos com 'pokemon' no nome ou .sav/.srm em geral
        for search_dir in search_dirs:
            if not search_dir.exists():
                logger.debug(f"Skip (not exist): {search_dir}")
                continue

            try:
                logger.debug(f"Searching in {search_dir}")

                # Padrão 1: arquivos com 'pokemon' no nome
                for pattern in ["*pokemon*.sav", "*pokemon*.srm", "*Pokemon*.sav", "*Pokemon*.srm"]:
                    for save_file in search_dir.glob(f"*/{pattern}"):
                        if save_file.is_file() and save_file not in self.saves:
                            self.saves.append(save_file)
                            logger.info(f"Found (pattern): {save_file}")
                    for save_file in search_dir.glob(pattern):
                        if save_file.is_file() and save_file not in self.saves:
                            self.saves.append(save_file)
                            logger.info(f"Found (pattern): {save_file}")

                # Padrão 2: qualquer .sav ou .srm em dirs conhecidos (gbc, gba, roms)
                if "gbc" in str(search_dir) or "gba" in str(search_dir) or "roms" in str(search_dir):
                    for pattern in ["*.sav", "*.srm"]:
                        for save_file in search_dir.glob(f"*/{pattern}"):
                            if save_file.is_file() and save_file not in self.saves:
                                self.saves.append(save_file)
                                logger.info(f"Found (generic): {save_file}")
                        for save_file in search_dir.glob(pattern):
                            if save_file.is_file() and save_file not in self.saves:
                                self.saves.append(save_file)
                                logger.info(f"Found (generic): {save_file}")

            except (PermissionError, OSError) as e:
                logger.debug(f"Cannot access {search_dir}: {e}")
            except Exception as e:
                logger.debug(f"Error in {search_dir}: {e}")

        self.saves.sort()
        logger.info(f"Saves found: {len(self.saves)} total")
        for save in self.saves:
            logger.info(f"  - {save}")
        return self.saves

    def detect_generation(self, save_path: Path) -> Optional[int]:
        """Detect generation by file size"""
        if not save_path.exists():
            return None

        size = save_path.stat().st_size
        if size == 32816:  # Gen 2
            return 2
        elif size == 32768:  # Gen 1
            return 1
        elif size == 131072:  # Gen 3
            return 3
        return None

    def load_pokemon(self, save_path: Path, source: str = "party") -> List[Dict[str, Any]]:
        """Load Pokémon by uploading save to backend (same as web frontend does)"""
        logger.debug(f"Loading {save_path} from backend (source={source})")
        return self._load_pokemon_remote(save_path, source)

    def _load_pokemon_remote(self, save_path: Path, source: str = "party") -> List[Dict[str, Any]]:
        """
        Upload save file to backend and retrieve Pokémon list

        This is the PRIMARY method - same as web frontend does.
        Uploads .sav/.srm to backend for analysis.

        Args:
            save_path: Path to .sav or .srm file
            source: "party" or "boxes"

        Returns:
            List of pokémon dicts from the specified source
        """
        try:
            if not save_path.exists():
                logger.error(f"Save file does not exist: {save_path}")
                return []

            logger.info(f"Uploading save to backend: {save_path.name} ({save_path.stat().st_size} bytes)")

            # Extract server URL (e.g., wss://9kernel.vps-kinghost.net/ws -> https://9kernel.vps-kinghost.net)
            server_base = self.server_url.replace("wss://", "https://").replace("ws://", "http://").replace("/ws", "")
            analyze_url = f"{server_base}/analyze-save"

            logger.info(f"Conectando a: {analyze_url}")
            with open(save_path, "rb") as f:
                files = {"file": (save_path.name, f)}
                logger.debug(f"Enviando POST com arquivo: {save_path.name}")
                response = requests.post(analyze_url, files=files, timeout=30)

            logger.info(f"Backend respondeu: HTTP {response.status_code}")

            if response.status_code != 200:
                logger.error(f"ERRO: Status {response.status_code}")
                logger.error(f"Response body: {response.text[:500]}")
                return []

            try:
                data = response.json()
            except Exception as json_err:
                logger.error(f"Erro ao fazer parse JSON: {json_err}")
                logger.error(f"Response text: {response.text[:500]}")
                return []

            logger.info(f"Backend retornou: Gen{data.get('generation')}, {data.get('game')}, {len(data.get('pokemon', []))} pokémon total")
            logger.debug(f"Pokemon list: {data.get('pokemon', [])[:3]}")  # Log first 3

            self.pokemon_list = []
            pokemon_count = 0

            # Filter by source (party or boxes)
            for pokemon in data.get("pokemon", []):
                if pokemon.get("source") == source:
                    pokemon_count += 1
                    self.pokemon_list.append({
                        "index": pokemon.get("index"),
                        "name": pokemon.get("species_name", "Unknown"),
                        "level": pokemon.get("level", 0),
                        "nickname": pokemon.get("nickname", ""),
                        "location": pokemon.get("location", f"{source}:{pokemon_count}"),
                        "display": pokemon.get("display_summary", f"Pokémon {pokemon_count}"),
                        "object": None,
                    })

            logger.info(f"✓ Carregou {len(self.pokemon_list)} Pokémon de {source}")
            if len(self.pokemon_list) == 0:
                logger.warning(f"⚠️  Nenhum pokémon encontrado em {source}. Total no arquivo: {len(data.get('pokemon', []))}")
                logger.debug(f"Sources disponíveis: {set(p.get('source') for p in data.get('pokemon', []))}")

            return self.pokemon_list

        except requests.ConnectionError as e:
            logger.error(f"ERRO DE CONEXÃO: {e}")
            logger.error(f"Verifique se o backend está disponível: {self.server_url}")
            return []
        except requests.Timeout:
            logger.error(f"TIMEOUT: Backend não respondeu em 30s")
            return []
        except requests.RequestException as e:
            logger.error(f"ERRO DE REDE: {e}")
            return []
        except Exception as e:
            logger.error(f"ERRO INESPERADO: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []


class PygameUI:
    """UI adapter for pygame to receive run_trade messages"""

    def __init__(self, ui_queue: queue.Queue, confirm_queue: queue.Queue):
        self.ui_queue = ui_queue
        self.confirm_queue = confirm_queue

    def print(self, msg: str):
        """Send status message to pygame"""
        self.ui_queue.put(("status", msg))
        logger.debug(f"UI: {msg}")

    def confirm(self, prompt: str, default: bool = True) -> bool:
        """Request user confirmation (blocks thread until pygame responds)"""
        self.ui_queue.put(("confirm_prompt", prompt))
        logger.debug(f"Waiting for user confirmation: {prompt}")
        result = self.confirm_queue.get()
        logger.debug(f"Confirmation result: {result}")
        return result

    def choose(self, prompt: str, items: list, labels: list = None):
        """Auto-select first item (no complex UI needed)"""
        logger.debug(f"Auto-select first of {len(items)} items")
        return items[0] if items else None


def _run_trade_bg(
    state: PokecableState,
    action: str,
    ui_queue: queue.Queue,
    confirm_queue: queue.Queue,
) -> None:
    """Background thread target for run_trade"""
    try:
        backend_dir = state.backend_dir
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

        from client import run_trade
        from saves import detect_parser, load_config

        ui_queue.put(("status", "Inicializando..."))

        save_path = state.selected_save
        parser = detect_parser(save_path)
        if not parser:
            ui_queue.put(("error", f"Não conseguiu detectar o arquivo de save: {save_path}"))
            return

        pokemon_to_trade = state.selected_pokemon
        if not pokemon_to_trade:
            ui_queue.put(("error", "Nenhum Pokémon selecionado"))
            return

        pokemon_location = f"party:{pokemon_to_trade['index']}"

        config = load_config()
        ui = PygameUI(ui_queue, confirm_queue)

        result = asyncio.run(
            run_trade(
                server_url=state.server_url,
                action=action,
                room_name=state.room_name,
                password=state.room_password,
                parser=parser,
                pokemon_location=pokemon_location,
                auto_confirm=False,
                backup_dir=str(config.get("backup_dir", state.config_dir / "backups")),
                save_path=save_path,
                initial_save_signature=None,
                ui=ui,
                trade_mode="same_generation",
                auto_trade_evolution=config.get("auto_trade_evolution", True),
                item_based_evolutions_enabled=config.get("item_based_evolutions_enabled", False),
                cross_generation_policy=config.get("cross_generation", {}).get("policy", "auto_retrocompat"),
                unsafe_auto_confirm_data_loss=False,
            )
        )

        ui_queue.put(("result", result))
        logger.info("Trade completed successfully")

    except ImportError as e:
        logger.error(f"Backend not available: {e}")
        ui_queue.put(("error", "Backend não disponível. Verifique a instalação."))
    except Exception as e:
        logger.exception(f"Trade failed: {e}")
        ui_queue.put(("error", str(e)))


def start_trade_thread(
    state: PokecableState, action: str, ui_queue: queue.Queue, confirm_queue: queue.Queue
) -> threading.Thread:
    """Start background thread for trading"""
    thread = threading.Thread(target=_run_trade_bg, args=(state, action, ui_queue, confirm_queue), daemon=False)
    thread.start()
    logger.info(f"Trade thread started for action={action}")
    return thread
