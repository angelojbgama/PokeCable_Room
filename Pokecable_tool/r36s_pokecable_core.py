#!/usr/bin/env python3
"""
PokeCable R36S - Core logic for local save parsing and local/LAN trading.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import queue
import shutil
import ssl
import sys
import threading
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pokecable_save import SaveError, SaveModel, _ensure_backend_import_path, load_save
from save_curation import filter_dev_test_save_corpus

DEBUG = os.getenv("POKECABLE_DEBUG", "0").lower() in ("1", "true", "yes")
logger = logging.getLogger("r36s_pokecable_core")

if DEBUG:
    logger.setLevel(logging.DEBUG)


DEFAULT_LANGUAGE = "pt"
DEFAULT_THEME = "pokedex_white"
SUPPORTED_LANGUAGES = {"pt", "en", "es"}
SUPPORTED_THEMES = {
    "pokedex_red",
    "pokedex_dark",
    "pokedex_white",
    "ink_wash",
    "neutral_elegance",
    "jade_pebble_morning",
    "woodland",
    "driftwood_pearl_morning",
    "graphite",
    "urban_slate",
    "pearl",
    "vichy",
    "sorbet",
    "frozen_mist",
    "yacht_club",
    "amber_walnut_morning",
    "copper_aquamarine_dream",
    "cocoa_topaz_noonday",
    "sandstone_aquamarine_serenity",
    "honey_opal_sunset",
    "seashell_garnet_afternoon",
    "rose_quartz_evening",
    "calcite",
    "fireside",
    "terrazzo",
    "sapphire_nightfall_whisper",
    "lapis_velvet_evening",
    "marina",
    "emerald_lavender_lake",
    "sage_peridot_morning",
    "amethyst_dawn_haze",
    "moon_dust",
    "turquoise_amber_autumn",
    "sapphire_ash_morning",
    "frosted_aura",
    "royal_glimmer",
    "neptune",
    "tropical_jade_sunrise",
    "amethyst_mint_harmony",
    "hibiscus_aura",
    "ocean_ruby_radiance",
    "tropical_heat",
    "celestial",
    "festive_eve",
    "freshly_squeezed",
    "jelly_shoes",
    "opaline",
    "gossamer",
    "clockwork",
    "lemon_granite_morning",
    "arctic_reflection",
    "slate",
    "autumn_luxe",
    "inked",
    "wraith",
    "urban_nocturne",
}
SUPPORTED_TRADE_MODES = [
    "same_generation",
    "time_capsule_gen1_gen2",
    "forward_transfer_to_gen3",
    "legacy_downconvert_experimental",
]
SUPPORTED_PROTOCOLS = ["raw_same_generation", "canonical_cross_generation"]
_ITEM_LOOKUP_LOADED = False
_ITEM_LOOKUP_FAILED = False
_RUNTIME_ITEM_NAME = None
_RUNTIME_ITEM_CATEGORY = None


def _enabled(value: str | None) -> bool:
    return str(value or "").lower() in ("1", "true", "yes", "on")


def _ensure_tool_runtime_import_path() -> None:
    runtime_dir = Path(__file__).resolve().parent / "pokecable_runtime"
    runtime_path = str(runtime_dir)
    if runtime_dir.exists() and runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)


def _load_runtime_item_lookup() -> None:
    global _ITEM_LOOKUP_LOADED, _ITEM_LOOKUP_FAILED, _RUNTIME_ITEM_NAME, _RUNTIME_ITEM_CATEGORY
    if _ITEM_LOOKUP_LOADED or _ITEM_LOOKUP_FAILED:
        return
    try:
        _ensure_tool_runtime_import_path()
        from data.items import item_category, item_name  # type: ignore

        _RUNTIME_ITEM_NAME = item_name
        _RUNTIME_ITEM_CATEGORY = item_category
        _ITEM_LOOKUP_LOADED = True
    except Exception as exc:
        _ITEM_LOOKUP_FAILED = True
        logger.debug("Local item lookup unavailable: %s", exc)


def _resolve_local_item_metadata(item_id: Any, generation: Any) -> tuple[str | None, str | None]:
    try:
        normalized_id = int(item_id or 0)
    except (TypeError, ValueError):
        normalized_id = 0
    if normalized_id <= 0:
        return None, None
    try:
        normalized_generation = int(generation or 0)
    except (TypeError, ValueError):
        normalized_generation = 0
    _load_runtime_item_lookup()
    if not _ITEM_LOOKUP_LOADED or _RUNTIME_ITEM_NAME is None or _RUNTIME_ITEM_CATEGORY is None:
        return None, None
    try:
        name = _RUNTIME_ITEM_NAME(normalized_id, normalized_generation)
        category = _RUNTIME_ITEM_CATEGORY(normalized_id, normalized_generation)
        return (str(name) if name else None, str(category) if category else None)
    except Exception:
        return None, None


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
        self.lan_manual_endpoint = ""
        self.pokemon_source = "party"
        self.action: str = "access"

        self._lan_stop_event: Optional[threading.Event] = None
        self._lan_connection: Any = None
        self.trade_phase: str = "idle"
        self.cancel_round_requested: bool = False
        self.leave_requested: bool = False
        self.expected_signature: Optional[Dict[str, Any]] = None

        self.save_analysis: Dict[str, Dict[str, Any]] = {}
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

    def enrich_pokemon(self, save: SaveModel, pokemon_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not pokemon_list:
            return []
        payload = {
            "generation": save.generation,
            "game": save.game,
            "pokemon": pokemon_list,
        }
        try:
            _ensure_backend_import_path()
            from runtime_services import enrich_pokemon_payload  # type: ignore

            response = enrich_pokemon_payload(payload)
        except Exception as local_exc:
            raise SaveError(f"Falha ao enriquecer Pokemon localmente: {local_exc}") from local_exc
        enriched = response.get("pokemon")
        if not isinstance(enriched, list) or len(enriched) != len(pokemon_list):
            raise SaveError("Enriquecimento de Pokemon invalido.")
        for original, local in zip(pokemon_list, enriched):
            if isinstance(local, dict):
                original.update(local)
        return pokemon_list

    def find_saves(self) -> List[Path]:
        self.saves = []
        seen = set()
        search_dirs = self._default_save_dirs()
        patterns = ["*.sav", "*.srm", "*.SAV", "*.SRM"]
        discovered: List[Path] = []
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
                                    discovered.append(save_file)
            except (PermissionError, OSError) as exc:
                logger.debug(f"Cannot access {search_dir}: {exc}")
        self.saves = filter_dev_test_save_corpus(discovered)
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
            "badges_mask": save.badges_earned(),
            "trainer_id": save.trainer_id(),
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

    def get_pokemon_list(self, source: str = "party", enrich: bool = True) -> List[Dict[str, Any]]:
        if not self.selected_save:
            return []

        analysis = self.analyze_save(self.selected_save)
        if not analysis:
            self.pokemon_list = []
            return []

        save: SaveModel = analysis["save"]
        source_pokemon = save.get_pokemon(source)
        if enrich:
            self.enrich_pokemon(save, source_pokemon)

        self.pokemon_list = []
        for pokemon in source_pokemon:
            species_id = int(pokemon.get("species_id") or 0)
            if species_id <= 0:
                continue
            metadata = pokemon.get("metadata") if isinstance(pokemon.get("metadata"), dict) else {}
            canonical = pokemon.get("canonical") if isinstance(pokemon.get("canonical"), dict) else {}
            canonical_metadata = canonical.get("metadata") if isinstance(canonical.get("metadata"), dict) else {}
            generation_value = int(analysis.get("generation", 0) or pokemon.get("generation") or pokemon.get("source_generation") or 0)
            held_item_id = pokemon.get("held_item_id")
            held_item_name = pokemon.get("held_item_name")
            held_item_category = pokemon.get("held_item_category")
            if held_item_id and (not held_item_name or str(held_item_name).startswith("#")):
                local_item_name, local_item_category = _resolve_local_item_metadata(held_item_id, generation_value)
                if local_item_name:
                    held_item_name = local_item_name
                if local_item_category:
                    held_item_category = local_item_category
            is_shiny = bool(
                pokemon.get("is_shiny")
                or metadata.get("is_shiny")
                or canonical.get("is_shiny")
                or canonical_metadata.get("is_shiny")
            )
            self.pokemon_list.append(
                {
                    "index": pokemon.get("index"),
                    "name": pokemon.get("species_name", "Pokemon"),
                    "species_id": species_id,
                    "species_name": pokemon.get("species_name", "Pokemon"),
                    "national_dex_id": pokemon.get("national_dex_id"),
                    "types": pokemon.get("types", []),
                    "held_item_id": held_item_id,
                    "held_item_name": held_item_name,
                    "held_item_category": held_item_category,
                    "moves": pokemon.get("moves", []),
                    "move_details": pokemon.get("move_details", []),
                    "move_names": pokemon.get("move_names", []),
                    "is_shiny": is_shiny,
                    "level": pokemon.get("level", 0),
                    "experience": pokemon.get("experience"),
                    "experience_progress": pokemon.get("experience_progress"),
                    "nickname": pokemon.get("nickname", ""),
                    "gender": pokemon.get("gender") or metadata.get("gender") or canonical_metadata.get("gender"),
                    "location": pokemon.get("location", "party:0"),
                    "source": pokemon.get("source", source),
                    "box_name": pokemon.get("box_name", ""),
                    "display": pokemon.get("display_summary", "Pokemon"),
                    "generation": generation_value,
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
    """Vai direto para a tela de seleção de Pokemon (Party)."""
    try:
        state.pokemon_source = "party"
        state.get_pokemon_list("party", enrich=state.action != "lan")
        ui.status("")
    except Exception as exc:
        logger.debug("Failed to load party: %s", exc)
    ui.screen("select_pokemon")


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
    configured = os.getenv("POKECABLE_BACKUP_DIR", "").strip()
    backup_dir = Path(configured).expanduser() if configured else (Path.home() / ".pokecable" / "backups")
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
        "target_game": str(server_preflight.get("target_game") or save.game or ""),
        "blocking_reasons": reasons,
        "warnings": warnings,
        "data_loss": [],
        "suggested_actions": list(server_preflight.get("suggested_actions") or []),
        "server_preflight": server_preflight,
        "trade_evolution": server_preflight.get("trade_evolution") or {},
        "item_relocation": server_preflight.get("item_relocation") or {},
        "removed_moves": list(server_preflight.get("removed_moves") or []),
        "removed_items": list(server_preflight.get("removed_items") or []),
    }


def _local_trade_preflight(received_payload: Dict[str, Any], target_save: SaveModel) -> Dict[str, Any]:
    try:
        _ensure_tool_runtime_import_path()
        from runtime_services import build_trade_preflight  # type: ignore
    except Exception as exc:
        raise SaveError(f"Validador local da tool indisponivel: {exc}") from exc
    try:
        return build_trade_preflight(
            {
                "received_payload": received_payload,
                "target_generation": target_save.generation,
                "target_game": target_save.game,
                "target_save_bytes_base64": base64.b64encode(bytes(target_save.bytes)).decode("ascii"),
                "target_save_suffix": target_save.path.suffix or ".sav",
            }
        )
    except Exception as exc:
        raise SaveError(f"Falha no preflight local: {exc}") from exc


def _local_outgoing_item_relocation(
    sent_payload: Dict[str, Any],
    source_save: SaveModel,
    target_generation: int,
) -> Dict[str, Any]:
    try:
        _ensure_tool_runtime_import_path()
        from runtime_services import build_outgoing_item_relocation  # type: ignore
    except Exception as exc:
        raise SaveError(f"Validador local de item indisponivel: {exc}") from exc
    try:
        return build_outgoing_item_relocation(
            {
                "sent_payload": sent_payload,
                "target_generation": target_generation,
                "source_save_bytes_base64": base64.b64encode(bytes(source_save.bytes)).decode("ascii"),
                "source_save_suffix": source_save.path.suffix or ".sav",
            }
        )
    except Exception as exc:
        raise SaveError(f"Falha avaliando item do Pokemon que sai do save: {exc}") from exc


def _trade_preflight_for_target(
    state: PokecableState,
    received_payload: Dict[str, Any],
    target_save: SaveModel,
) -> Dict[str, Any]:
    del state
    return _local_trade_preflight(received_payload, target_save)


def _self_trade_evolution_preview_for_target(
    received_payload: Dict[str, Any],
    target_save: SaveModel,
) -> Dict[str, Any]:
    try:
        _ensure_tool_runtime_import_path()
        from evolutions import preview_trade_evolution  # type: ignore
        from data.items import equivalent_item_id  # type: ignore
        from data.species import national_to_native  # type: ignore
    except Exception as exc:
        logger.warning("Self-trade evolution preview unavailable: %s", exc)
        return {}

    target_generation = int(target_save.generation or 0)
    canonical = received_payload.get("canonical") if isinstance(received_payload.get("canonical"), dict) else {}
    source_generation = int(
        canonical.get("source_generation")
        or received_payload.get("source_generation")
        or received_payload.get("generation")
        or 0
    )
    national_dex_id = int(
        (canonical.get("species") or {}).get("national_dex_id")
        or canonical.get("species_national_id")
        or received_payload.get("national_dex_id")
        or 0
    )
    if national_dex_id <= 0:
        return {}
    try:
        target_species_id = int(national_to_native(target_generation, national_dex_id))
    except Exception:
        return {}

    held_item: Dict[str, Any] = canonical.get("held_item") if isinstance(canonical.get("held_item"), dict) else {}
    received_held_item_id = int(
        held_item.get("item_id")
        or received_payload.get("held_item_id")
        or (received_payload.get("summary") or {}).get("held_item_id")
        or 0
    )
    held_item_id_for_target: int | None = None
    if received_held_item_id > 0:
        item_source_generation = int(held_item.get("source_generation") or source_generation or 0)
        if item_source_generation and item_source_generation != target_generation:
            held_item_id_for_target = equivalent_item_id(received_held_item_id, item_source_generation, target_generation)
        else:
            held_item_id_for_target = received_held_item_id

    result = preview_trade_evolution(
        target_generation,
        target_species_id,
        held_item_id=held_item_id_for_target,
    )
    preview = {
        "generation": target_generation,
        "evolved": bool(result.evolved),
        "source_species_id": int(result.source_species_id),
        "target_species_id": int(result.target_species_id),
        "source_name": result.source_name,
        "target_name": result.target_name,
        "consumed_item_id": result.consumed_item_id,
        "consumed_item_name": result.consumed_item_name,
        "reason": result.reason,
    }
    logger.info(
        "Self-trade evolution preview: target_gen=%s source_gen=%s national=%s target_species=%s held_item_in=%s held_item_target=%s evolved=%s reason=%s",
        target_generation,
        source_generation,
        national_dex_id,
        target_species_id,
        received_held_item_id or None,
        held_item_id_for_target,
        preview["evolved"],
        preview["reason"],
    )
    return preview


def _preflight_block_message(preflight: Dict[str, Any]) -> str:
    reasons = [str(reason) for reason in preflight.get("blocking_reasons", []) if reason]
    if reasons:
        return "; ".join(reasons)
    if not preflight.get("compatible", True):
        return "Troca incompativel."
    return ""


def prepare_self_trade(
    state: PokecableState,
    save_a_path: Path,
    pokemon_a_location: str,
    save_b_path: Path,
    pokemon_b_location: str,
) -> Dict[str, Any]:
    """Builds both offers and runs the same preflight used by room trades."""
    save_a_path = Path(save_a_path)
    save_b_path = Path(save_b_path)
    try:
        if save_a_path.resolve() == save_b_path.resolve():
            raise SaveError("Escolha dois arquivos de save diferentes.")
    except OSError:
        if str(save_a_path.absolute()) == str(save_b_path.absolute()):
            raise SaveError("Escolha dois arquivos de save diferentes.")

    save_a = load_save(save_a_path)
    save_b = load_save(save_b_path)
    payload_a = save_a.export_payload(pokemon_a_location)
    payload_b = save_b.export_payload(pokemon_b_location)

    preflight_to_a = _trade_preflight_for_target(state, payload_b, save_a)
    preflight_to_b = _trade_preflight_for_target(state, payload_a, save_b)
    outgoing_item_relocation_a = _local_outgoing_item_relocation(payload_a, save_a, save_b.generation)
    outgoing_item_relocation_b = _local_outgoing_item_relocation(payload_b, save_b, save_a.generation)
    trade_evolution_to_a = _self_trade_evolution_preview_for_target(payload_b, save_a)
    trade_evolution_to_b = _self_trade_evolution_preview_for_target(payload_a, save_b)
    block_to_a = _preflight_block_message(preflight_to_a)
    block_to_b = _preflight_block_message(preflight_to_b)
    item_block_to_a = str(outgoing_item_relocation_a.get("reason") or "") if outgoing_item_relocation_a.get("status") == "manual_remove_required" else ""
    item_block_to_b = str(outgoing_item_relocation_b.get("reason") or "") if outgoing_item_relocation_b.get("status") == "manual_remove_required" else ""
    if block_to_a or block_to_b or item_block_to_a or item_block_to_b:
        messages = []
        if block_to_a:
            messages.append(f"{save_a_path.name} receberia troca invalida: {block_to_a}")
        if block_to_b:
            messages.append(f"{save_b_path.name} receberia troca invalida: {block_to_b}")
        if item_block_to_a:
            messages.append(f"{save_a_path.name} precisa tratar o item do Pokemon enviado: {item_block_to_a}")
        if item_block_to_b:
            messages.append(f"{save_b_path.name} precisa tratar o item do Pokemon enviado: {item_block_to_b}")
        raise SaveError(" ".join(messages))

    return {
        "save_a_path": save_a_path,
        "save_b_path": save_b_path,
        "pokemon_a_location": pokemon_a_location,
        "pokemon_b_location": pokemon_b_location,
        "payload_a": payload_a,
        "payload_b": payload_b,
        "preflight_to_a": preflight_to_a,
        "preflight_to_b": preflight_to_b,
        "outgoing_item_relocation_a": outgoing_item_relocation_a,
        "outgoing_item_relocation_b": outgoing_item_relocation_b,
        "trade_evolution_to_a": trade_evolution_to_a,
        "trade_evolution_to_b": trade_evolution_to_b,
        "signature_a": save_a.signature(),
        "signature_b": save_b.signature(),
        "save_a_name": save_a_path.name,
        "save_b_name": save_b_path.name,
    }


def validate_self_trade_candidate(
    state: PokecableState,
    *,
    source_save_path: Path,
    source_pokemon_location: str,
    target_save_path: Path,
) -> Dict[str, Any]:
    """Validate only one direction of a self trade candidate for UI filtering."""
    source_save = load_save(Path(source_save_path))
    target_save = load_save(Path(target_save_path))
    payload = source_save.export_payload(source_pokemon_location)
    preflight = _trade_preflight_for_target(state, payload, target_save)
    outgoing_item_relocation = _local_outgoing_item_relocation(payload, source_save, target_save.generation)
    outgoing_block = str(outgoing_item_relocation.get("reason") or "") if outgoing_item_relocation.get("status") == "manual_remove_required" else ""
    blocking_message = outgoing_block or _preflight_block_message(preflight)
    return {
        "compatible": not bool(blocking_message),
        "preflight": preflight,
        "blocking_message": blocking_message,
    }


def execute_self_trade(
    context: Dict[str, Any],
    *,
    cancel_evolution_to_a: bool = False,
    cancel_evolution_to_b: bool = False,
    resolved_moves_to_a: Optional[Dict[int, int]] = None,
    resolved_moves_to_b: Optional[Dict[int, int]] = None,
    item_relocation_choice_to_a: Optional[str] = None,
    item_relocation_choice_to_b: Optional[str] = None,
) -> Dict[str, Any]:
    """Applies a prepared local two-save trade with backups and rollback."""
    save_a_path = Path(context.get("save_a_path"))
    save_b_path = Path(context.get("save_b_path"))
    signature_a = context.get("signature_a") if isinstance(context.get("signature_a"), dict) else {}
    signature_b = context.get("signature_b") if isinstance(context.get("signature_b"), dict) else {}
    if not _save_unchanged_on_disk(signature_a, save_a_path):
        raise SaveError(f"{save_a_path.name} mudou em disco. Recarregue e tente novamente.")
    if not _save_unchanged_on_disk(signature_b, save_b_path):
        raise SaveError(f"{save_b_path.name} mudou em disco. Recarregue e tente novamente.")

    backup_a: Optional[Path] = None
    backup_b: Optional[Path] = None
    try:
        save_a = load_save(save_a_path)
        save_b = load_save(save_b_path)
        payload_a = context.get("payload_a") if isinstance(context.get("payload_a"), dict) else {}
        payload_b = context.get("payload_b") if isinstance(context.get("payload_b"), dict) else {}
        preflight_to_a = context.get("preflight_to_a") if isinstance(context.get("preflight_to_a"), dict) else {}
        preflight_to_b = context.get("preflight_to_b") if isinstance(context.get("preflight_to_b"), dict) else {}
        trade_evolution_to_a = context.get("trade_evolution_to_a") if isinstance(context.get("trade_evolution_to_a"), dict) else {}
        trade_evolution_to_b = context.get("trade_evolution_to_b") if isinstance(context.get("trade_evolution_to_b"), dict) else {}

        backup_a = _create_backup(save_a_path)
        backup_b = _create_backup(save_b_path)
        received_a = save_a.apply_payload(
            str(context.get("pokemon_a_location") or "party:0"),
            payload_b,
            outgoing_payload=payload_a,
            trade_evolution=trade_evolution_to_a or preflight_to_a.get("trade_evolution") or {},
            cancel_trade_evolution=cancel_evolution_to_a,
            resolved_moves=resolved_moves_to_a or {},
            item_relocation_choice=item_relocation_choice_to_a,
        )
        save_a.write_to_disk()
        received_b = save_b.apply_payload(
            str(context.get("pokemon_b_location") or "party:0"),
            payload_a,
            outgoing_payload=payload_b,
            trade_evolution=trade_evolution_to_b or preflight_to_b.get("trade_evolution") or {},
            cancel_trade_evolution=cancel_evolution_to_b,
            resolved_moves=resolved_moves_to_b or {},
            item_relocation_choice=item_relocation_choice_to_b,
        )
        save_b.write_to_disk()
        return {
            "success": True,
            "peer": payload_b,
            "received": received_a,
            "received_a": received_a,
            "received_b": received_b,
            "save_a": str(save_a_path),
            "save_b": str(save_b_path),
            "backup": str(backup_a) if backup_a else "",
            "backup_a": str(backup_a) if backup_a else "",
            "backup_b": str(backup_b) if backup_b else "",
        }
    except Exception:
        for backup_path, save_path in ((backup_a, save_a_path), (backup_b, save_b_path)):
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, save_path)
                    logger.warning("Restored %s from backup after self trade failure", save_path)
                except Exception as restore_exc:
                    logger.exception("Failed to restore %s from %s: %s", save_path, backup_path, restore_exc)
        raise


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


def _run_lan_trade_bg(state: PokecableState, ui_queue: queue.Queue, confirm_queue: queue.Queue, stop_event: threading.Event) -> None:
    ui = PygameUI(ui_queue, confirm_queue)
    try:
        logger.info("LAN trade thread starting: save=%s", state.selected_save)
        from pokecable_lan import run_lan_trade

        run_lan_trade(state, ui, confirm_queue, stop_event)
    except Exception as exc:
        logger.exception("LAN trade thread failed: %s", exc)
        ui.error(str(exc))
    finally:
        state._lan_stop_event = None
        state._lan_connection = None
        state.trade_phase = "idle"
        state.cancel_round_requested = False
        state.leave_requested = False
        state.expected_signature = None
        try:
            confirm_queue.put_nowait(None)
        except Exception:
            pass


def request_leave_room(state: PokecableState) -> bool:
    """Gracefully close the LAN trade, ending the session."""
    if state._lan_stop_event is not None:
        if state.trade_phase == "writing":
            logger.warning("LAN leave ignored: save write in progress")
            return False
        state.leave_requested = True
        state._lan_stop_event.set()
        connection = state._lan_connection
        if connection is not None:
            try:
                connection.close()
            except Exception as exc:
                logger.debug("LAN leave close failed (ignored): %s", exc)
        return True
    return False


def request_trade_cancel(state: PokecableState) -> bool:
    """Safe cancel of the current round: keeps the LAN trade alive so user can re-pick a Pokémon.

    Only honoured before the save write begins (phase != 'writing').
    The trade thread observes `cancel_round_requested`.
    """
    phase = state.trade_phase
    if phase in ("idle", "writing", "done"):
        logger.warning("Cancel ignored in phase=%s", phase)
        return False
    if state._lan_stop_event is None:
        logger.warning("Cancel requested but no active LAN trade")
        return False
    state.cancel_round_requested = True
    logger.info("Round cancel flag set (phase=%s)", phase)
    return True


def start_lan_trade_thread(
    state: PokecableState, ui_queue: queue.Queue, confirm_queue: queue.Queue
) -> threading.Thread:
    stop_event = threading.Event()
    state._lan_stop_event = stop_event
    thread = threading.Thread(
        target=_run_lan_trade_bg,
        args=(state, ui_queue, confirm_queue, stop_event),
        daemon=True,
    )
    thread.start()
    logger.info("LAN trade thread started")
    return thread


UPDATE_REPO_API = "https://api.github.com/repos/angelojbgama/PokeCable_Room/releases/latest"
UPDATE_ZIP_FALLBACK = "https://github.com/angelojbgama/PokeCable_Room/archive/refs/heads/main.zip"
UPDATE_TIMEOUT = 20


def _version_tuple(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in str(value or "").strip().lstrip("v").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts or [0])


def _urlopen_with_fallback(request_or_url, timeout: int = UPDATE_TIMEOUT):
    try:
        return urllib.request.urlopen(request_or_url, timeout=timeout)
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLError):
            logger.warning("HTTPS certificate validation failed; retrying update request without certificate validation: %s", reason)
            context = ssl._create_unverified_context()
            return urllib.request.urlopen(request_or_url, timeout=timeout, context=context)
        raise


def _download_file(url: str, destination: Path) -> int:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PokeCable-R36S/1.0", "Accept": "*/*"},
    )
    logger.info("Update download start: %s -> %s", url, destination)
    total = 0
    with _urlopen_with_fallback(request, timeout=UPDATE_TIMEOUT) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 64)
                if not chunk:
                    break
                handle.write(chunk)
                total += len(chunk)
    logger.info("Update download complete: bytes=%s file=%s", total, destination)
    return total


def _find_extracted_tool_root(extract_dir: Path) -> Path:
    candidates = [extract_dir / "Pokecable_tool"]
    candidates.extend(path / "Pokecable_tool" for path in extract_dir.iterdir() if path.is_dir())
    for candidate in candidates:
        if (candidate / "r36s_pokecable_core.py").exists() and (candidate / "pokecable.sh").exists():
            return candidate
    raise FileNotFoundError("Pokecable_tool nao encontrado dentro do pacote de atualizacao")


def _safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    destination_resolved = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if destination_resolved != target and destination_resolved not in target.parents:
            raise RuntimeError(f"entrada insegura no ZIP: {member.filename}")
    archive.extractall(destination)


def _copy_update_tree(source: Path, destination: Path) -> None:
    # "dependence" traz libs nativas (.so) em uso pelo processo; sobrescrever
    # mata o app (SIGSEGV). É gerenciada na instalacao, nao no update.
    skip_names = {"logs", ".git", "__pycache__", "dependence"}
    for item in source.iterdir():
        if item.name in skip_names:
            continue
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(item, target)
    launcher = destination / "pokecable.sh"
    if launcher.exists():
        launcher.chmod(launcher.stat().st_mode | 0o755)


def check_for_update() -> Dict[str, Any]:
    """Check GitHub Releases API for new version without external dependencies."""
    try:
        from version import APP_VERSION
    except ImportError:
        APP_VERSION = "1.0.0"

    try:
        url = UPDATE_REPO_API
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PokeCable-R36S/1.0", "Accept": "application/vnd.github.v3+json"},
        )

        logger.info("Update check start: %s", url)
        with _urlopen_with_fallback(req, timeout=UPDATE_TIMEOUT) as response:
            response_data = response.read().decode("utf-8")
            data = json.loads(response_data)
            latest_version = data.get("tag_name", "").lstrip("v")
            if not latest_version:
                raise RuntimeError(str(data.get("message") or "resposta sem tag_name")[:160])
            release_url = data.get("html_url", "")
            zipball_url = data.get("zipball_url") or UPDATE_ZIP_FALLBACK
            is_up_to_date = _version_tuple(APP_VERSION) >= _version_tuple(latest_version)

            result = {
                "current": APP_VERSION,
                "latest": latest_version,
                "up_to_date": is_up_to_date,
                "release_url": release_url,
                "zipball_url": zipball_url,
                "error": None,
            }
            logger.info("Update check result: %s", result)
            return result

    except urllib.error.URLError as e:
        logger.error(f"Update check connection error: {e} ({type(e).__name__})")
        return {
            "error": f"Connection error: {str(e)[:100]}",
            "current": APP_VERSION,
            "latest": None,
            "up_to_date": True,
            "release_url": None,
        }
    except Exception as e:
        logger.error(f"Update check error: {e} ({type(e).__name__})")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return {
            "error": f"Check error: {str(e)[:100]}",
            "current": APP_VERSION,
            "latest": None,
            "up_to_date": True,
            "release_url": None,
        }


def apply_update(zipball_url: str | None = None) -> Dict[str, Any]:
    """Apply update from a ZIP package using only Python standard library."""
    current_tool_dir = Path(__file__).resolve().parent
    url = str(zipball_url or "").strip() or UPDATE_ZIP_FALLBACK

    try:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="pokecable_update_") as tmp_name:
            tmp_dir = Path(tmp_name)
            zip_path = tmp_dir / "pokecable_update.zip"
            extract_dir = tmp_dir / "extract"
            backup_dir = current_tool_dir.parent / f"Pokecable_tool.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            size = _download_file(url, zip_path)
            if size <= 0:
                raise RuntimeError("download vazio")

            logger.info("Update extract start: %s", zip_path)
            with zipfile.ZipFile(zip_path) as archive:
                _safe_extract_zip(archive, extract_dir)
            source_tool_dir = _find_extracted_tool_root(extract_dir)
            logger.info("Update extracted tool root: %s", source_tool_dir)

            logger.info("Update backup start: %s -> %s", current_tool_dir, backup_dir)
            shutil.copytree(
                current_tool_dir,
                backup_dir,
                ignore=shutil.ignore_patterns("logs", "dependence", "__pycache__", "*.pyc", ".git"),
            )

            logger.info("Update copy start: %s -> %s", source_tool_dir, current_tool_dir)
            _copy_update_tree(source_tool_dir, current_tool_dir)
            logger.info("Update applied successfully; backup=%s", backup_dir)
            return {
                "success": True,
                "message": "Atualizacao aplicada. Reinicie o app.",
                "backup": str(backup_dir),
                "downloaded_bytes": size,
            }

    except urllib.error.URLError as e:
        logger.error("Update download connection error: %s (%s)", e, type(e).__name__)
        return {
            "success": False,
            "message": f"Erro de conexao: {str(e)[:120]}",
        }
    except zipfile.BadZipFile as e:
        logger.error("Update ZIP invalid: %s", e)
        return {
            "success": False,
            "message": "ZIP de atualizacao invalido ou incompleto.",
        }
    except Exception as e:
        logger.error(f"Update error: {e} ({type(e).__name__})")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return {
            "success": False,
            "message": f"Erro: {str(e)[:120]}",
        }


def get_available_events(save_path) -> dict:
    """Carrega save, detecta jogo, retorna lista de eventos disponíveis."""
    from pokecable_runtime.events.catalog import get_events_for_save
    from pokecable_runtime.events.official import profile_from_save

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "events": []}

        game_id = _get_game_id_from_save(save)
        if not game_id:
            return {"success": False, "events": []}

        profile = profile_from_save(save)
        events = get_events_for_save(save)
        return {
            "success": True,
            "events": events,
            "game_id": game_id,
            "profile": {
                "game_id": profile.game_id,
                "generation": profile.generation,
                "region": profile.region,
                "language": profile.language,
                "revision": profile.revision,
            },
        }

    except Exception as e:
        logger.error(f"Error loading events: {e}")
        return {"success": False, "events": []}


def apply_event_to_save(save_path, event_id: str) -> dict:
    """Backup → parser → apply_event → recalculate_checksums → save."""
    from pokecable_runtime.events.applicator import apply_event

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path

        save = load_save(save_path)
        if not save:
            return {"success": False, "message": "Could not load save"}

        result = apply_event(save, event_id)
        if not result.get("success"):
            return result

        backup_path = _create_backup(save_path)
        save.write_to_disk()
        return {
            "success": True,
            "message": result.get("message", "extras_applied"),
            "backup": backup_path,
        }

    except Exception as e:
        logger.error(f"Error applying event: {e}")
        return {"success": False, "message": str(e)[:100]}


def get_available_utilities(save_path) -> dict:
    """Lista utilitários de save (Pokédex completa, etc.) aplicáveis ao save."""
    from pokecable_runtime.events.save_utilities import get_available_utilities_for_save

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "utilities": []}
        return {"success": True, "utilities": get_available_utilities_for_save(save)}
    except Exception as e:
        logger.error(f"Error listing utilities: {e}")
        return {"success": False, "utilities": [], "message": str(e)[:100]}


def apply_utility_to_save(save_path, utility_id: str) -> dict:
    """Backup → aplica utilitário (edição direta) → grava no disco."""
    from pokecable_runtime.events.save_utilities import apply_utility

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "message": "Could not load save"}

        result = apply_utility(save, utility_id)
        if not result.get("success"):
            return result

        backup_path = _create_backup(save_path)
        save.write_to_disk()
        result["backup"] = backup_path
        return result
    except Exception as e:
        logger.error(f"Error applying utility: {e}")
        return {"success": False, "message": str(e)[:100]}


def preflight_extras_for_save(save_path, event_ids=None) -> dict:
    """Valida tickets de extras sem escrever no save."""
    from pokecable_runtime.events.applicator import preflight_events

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "can_apply": False, "message": "Could not load save", "events": [], "blockers": []}
        return preflight_events(save, event_ids)
    except Exception as e:
        logger.error(f"Error preflighting extras: {e}")
        return {"success": False, "can_apply": False, "message": str(e)[:100], "events": [], "blockers": []}


def apply_all_safe_events_to_save(save_path) -> dict:
    """Aplica todos os tickets oficiais seguros em lote, sem escrita parcial."""
    from pokecable_runtime.events.applicator import apply_event, preflight_events
    from pokecable_runtime.events.catalog import get_events_for_save

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "message": "Could not load save"}

        event_ids = [
            event["id"]
            for event in get_events_for_save(save)
            if event.get("category") == "ticket"
        ]
        if not event_ids:
            return {
                "success": True,
                "message": "extras_no_events",
                "applied_event_ids": [],
                "preflight": {"success": True, "can_apply": True, "events": [], "blockers": [], "event_ids_to_apply": []},
            }

        preflight = preflight_events(save, event_ids)
        if not preflight.get("can_apply"):
            return {
                "success": False,
                "message": preflight.get("message", "extras_preflight_failed"),
                "preflight": preflight,
            }

        event_ids_to_apply = list(preflight.get("event_ids_to_apply") or [])
        if not event_ids_to_apply:
            return {
                "success": True,
                "message": "extras_already_active",
                "applied_event_ids": [],
                "preflight": preflight,
            }

        applied_ids = []
        for event_id in event_ids_to_apply:
            result = apply_event(save, event_id)
            if not result.get("success"):
                return {
                    "success": False,
                    "message": result.get("message", "extras_preflight_failed"),
                    "applied_event_ids": applied_ids,
                    "preflight": preflight,
                }
            applied_ids.append(event_id)

        backup_path = _create_backup(save_path)
        save.write_to_disk()
        return {
            "success": True,
            "message": "extras_applied",
            "applied_event_ids": applied_ids,
            "backup": backup_path,
            "preflight": preflight,
        }

    except Exception as e:
        logger.error(f"Error applying all extras: {e}")
        return {"success": False, "message": str(e)[:100]}


def get_ereader_slots(save_path) -> dict:
    """Retorna os 5 slots e-Reader atuais do save (nome, pokémon)."""
    from pokecable_runtime.events.applicator import read_ereader_slots
    from pokecable_runtime.events.official import compatibility_for_save

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "slots": []}

        compatibility = compatibility_for_save(save, "ereader")
        if not compatibility.can_apply:
            return {"success": False, "slots": [], "message": compatibility.message or "e-Reader not available for this game"}

        slots = read_ereader_slots(save)
        return {"success": True, "slots": slots}

    except Exception as e:
        logger.error(f"Error reading e-Reader slots: {e}")
        return {"success": False, "slots": []}


def apply_ereader_to_save(save_path, slot: int, battle_id: str) -> dict:
    """Backup → parser → apply_ereader_battle → recalculate → save."""
    from pokecable_runtime.events.applicator import apply_ereader_battle

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        backup_path = _create_backup(save_path)

        save = load_save(save_path)
        if not save:
            return {"success": False, "message": "Could not load save"}

        result = apply_ereader_battle(save, slot, battle_id)
        if not result.get("success"):
            return result

        save.write_to_disk()
        return {
            "success": True,
            "message": result.get("message", "extras_applied"),
            "backup": backup_path,
        }

    except Exception as e:
        logger.error(f"Error applying e-Reader battle: {e}")
        return {"success": False, "message": str(e)[:100]}


def get_applied_events(save_path) -> dict:
    """Retorna set de event_ids já aplicados ao save."""
    try:
        from pokecable_runtime.events.applicator import read_ereader_slots
        from pokecable_runtime.events.catalog import get_events_for_save
        from pokecable_runtime.events.official import compatibility_for_save

        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "applied": set(), "applied_event_ids": set(), "applied_ereader_battles": set(), "occupied_ereader_slots": set(), "unknown_ereader_slots": set()}

        applied_event_ids = set()
        applied_ereader_battles = set()
        occupied_ereader_slots = set()
        unknown_ereader_slots = set()
        compatible_events = [event for event in get_events_for_save(save) if event.get("category") == "ticket"]

        parser = None
        if save._backend_parser:
            parser = save._backend_parser
        else:
            if save.generation == 1:
                _ensure_backend_import_path()
                from parsers import Gen1Parser
                p = Gen1Parser()
                if p.detect(save_path):
                    p.load(save_path)
                    parser = p
            elif save.generation == 2:
                _ensure_backend_import_path()
                from parsers import Gen2Parser
                p = Gen2Parser()
                if p.detect(save_path):
                    p.load(save_path)
                    parser = p
            elif save.generation == 3:
                _ensure_backend_import_path()
                from parsers import Gen3Parser
                p = Gen3Parser()
                if p.detect(save_path):
                    p.load(save_path)
                    parser = p

        if parser:
            try:
                inventory = parser.list_inventory()
                item_ids_in_bag = {entry.item_id for entry in inventory}
            except Exception:
                item_ids_in_bag = set()

            for event in compatible_events:
                if "item_id" in event and event["item_id"] in item_ids_in_bag:
                    applied_event_ids.add(event["id"])

        ereader_compatibility = compatibility_for_save(save, "ereader")
        if ereader_compatibility.can_apply:
            for slot_info in read_ereader_slots(save):
                if slot_info.get("is_empty"):
                    continue
                occupied_ereader_slots.add(int(slot_info["slot"]))
                battle_id = slot_info.get("battle_id")
                if battle_id:
                    applied_ereader_battles.add(battle_id)
                else:
                    unknown_ereader_slots.add(int(slot_info["slot"]))

        applied = set(applied_event_ids)
        applied.update(f"ereader:{battle_id}" for battle_id in applied_ereader_battles)
        return {
            "success": True,
            "applied": applied_event_ids,
            "applied_event_ids": applied_event_ids,
            "applied_ereader_battles": applied_ereader_battles,
            "occupied_ereader_slots": occupied_ereader_slots,
            "unknown_ereader_slots": unknown_ereader_slots,
            "applied_all": applied,
        }

    except Exception as e:
        logger.error(f"Error getting applied events: {e}")
        return {"success": False, "applied": set(), "applied_event_ids": set(), "applied_ereader_battles": set(), "occupied_ereader_slots": set(), "unknown_ereader_slots": set()}


def remove_event_from_save(save_path, event_id: str) -> dict:
    """Inverso de apply_event_to_save: remove o item do evento e limpa as flags."""
    from pokecable_runtime.events.applicator import revert_event

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path

        save = load_save(save_path)
        if not save:
            return {"success": False, "message": "Could not load save"}

        result = revert_event(save, event_id)
        if not result.get("success"):
            return result

        backup_path = _create_backup(save_path)
        save.write_to_disk()
        return {
            "success": True,
            "message": result.get("message", "extras_removed"),
            "backup": backup_path,
        }

    except Exception as e:
        logger.error(f"Error reverting event: {e}")
        return {"success": False, "message": str(e)[:100]}


def remove_ereader_from_save(save_path, slot: int) -> dict:
    """Inverso de apply_ereader_to_save: zera o slot e-Reader informado."""
    from pokecable_runtime.events.applicator import clear_ereader_slot

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path

        save = load_save(save_path)
        if not save:
            return {"success": False, "message": "Could not load save"}

        result = clear_ereader_slot(save, slot)
        if not result.get("success"):
            return result

        backup_path = _create_backup(save_path)
        save.write_to_disk()
        result["backup"] = backup_path
        return result

    except Exception as e:
        logger.error(f"Error clearing e-Reader slot: {e}")
        return {"success": False, "message": str(e)[:100]}


def remove_utility_from_save(save_path, utility_id: str) -> dict:
    """Inverso de apply_utility_to_save (apenas utilitários reversíveis)."""
    from pokecable_runtime.events.save_utilities import revert_utility

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path

        save = load_save(save_path)
        if not save:
            return {"success": False, "message": "Could not load save"}

        result = revert_utility(save, utility_id)
        if not result.get("success"):
            return result

        backup_path = _create_backup(save_path)
        save.write_to_disk()
        result["backup"] = backup_path
        return result

    except Exception as e:
        logger.error(f"Error reverting utility: {e}")
        return {"success": False, "message": str(e)[:100]}


def add_item_to_save(save_path, item_id: int, quantity: int = 1) -> dict:
    """Adiciona um item consumível à mochila (backup → store_item_in_bag → grava)."""
    from pokecable_runtime.events.applicator import _get_parser_for_save

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "message": "Could not load save"}

        parser = _get_parser_for_save(save)
        if not parser:
            return {"success": False, "message": "Não foi possível carregar parser"}

        quantity = max(1, int(quantity))
        try:
            result = parser.store_item_in_bag(int(item_id), quantity)
        except Exception as exc:  # noqa: BLE001 - mensagens de espaço/limite para o usuário
            message = str(exc)
            if any(token in message.lower() for token in ("no space", "bag is full", "cheio", "excedeu", "stack", "maxima")):
                return {"success": False, "message": "extras_no_space"}
            return {"success": False, "message": message[:120]}

        if hasattr(parser, "data") and parser.data:
            save.bytes[:] = parser.data

        backup_path = _create_backup(save_path)
        save.write_to_disk()
        return {
            "success": True,
            "message": "extras_applied",
            "backup": backup_path,
            "item_id": int(item_id),
            "quantity_added": quantity,
            "pocket_name": getattr(result, "pocket_name", ""),
        }
    except Exception as e:
        logger.error(f"Error adding item: {e}")
        return {"success": False, "message": str(e)[:100]}


def get_consumable_item_groups(save_path) -> dict:
    """Retorna os grupos de itens consumíveis aplicáveis ao save (por categoria)."""
    from pokecable_runtime.data.consumables import consumable_groups, max_item_stack

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "groups": [], "max_stack": 99}
        generation = int(getattr(save, "generation", 0) or 0)
        groups = consumable_groups(generation)
        return {"success": True, "groups": groups, "max_stack": max_item_stack(generation)}
    except Exception as e:
        logger.error(f"Error listing consumable items: {e}")
        return {"success": False, "groups": [], "max_stack": 99}


def get_applied_utilities(save_path) -> dict:
    """Retorna o estado dos utilitários reversíveis: ids ativos e ids reversíveis."""
    from pokecable_runtime.events.save_utilities import (
        get_available_utilities_for_save,
        is_utility_active,
        is_utility_reversible,
    )

    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        save = load_save(save_path)
        if not save:
            return {"success": False, "active": set(), "reversible": set()}

        active = set()
        reversible = set()
        for util in get_available_utilities_for_save(save):
            util_id = util["id"]
            if is_utility_reversible(util_id):
                reversible.add(util_id)
                if is_utility_active(save, util_id):
                    active.add(util_id)
        return {"success": True, "active": active, "reversible": reversible}

    except Exception as e:
        logger.error(f"Error getting applied utilities: {e}")
        return {"success": False, "active": set(), "reversible": set()}


def _get_game_id_from_save(save) -> Optional[str]:
    """Mapeia SaveModel para game_id."""
    if hasattr(save, "game"):
        return save.game
    return None
