from __future__ import annotations

import base64
import tempfile
import sys
from pathlib import Path
from typing import Any


def _ensure_backend_path() -> None:
    here = Path(__file__).resolve()
    runtime_dir = here.parent
    if (runtime_dir / "data").exists() and str(runtime_dir) not in sys.path:
        sys.path.insert(0, str(runtime_dir))


_ensure_backend_path()

from data.base_stats import BASE_STATS  # noqa: E402
from data.growth_rates import experience_progress_for_species, level_from_species_experience  # noqa: E402
from data.items import item_category, item_exists, item_name  # noqa: E402
from data.moves import move_exists, move_name  # noqa: E402
from data.species import SPECIES_NAMES_BY_NATIONAL, native_to_national  # noqa: E402
from evolutions import preview_trade_evolution  # noqa: E402
from canonical import CanonicalPokemon  # noqa: E402
from converters import get_converter  # noqa: E402
from parsers import Gen1Parser, Gen2Parser, Gen3Parser, Gen4Parser  # noqa: E402


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _native_species(generation: int, species_id: int) -> tuple[int | None, str | None]:
    if species_id <= 0:
        return None, "species_id ausente."
    try:
        national_dex_id = native_to_national(generation, species_id)
    except Exception:
        return None, f"Species #{species_id} nao existe na Gen {generation}."
    return national_dex_id, None


def _species_name(national_dex_id: int | None, fallback: str = "") -> str:
    if national_dex_id:
        return SPECIES_NAMES_BY_NATIONAL.get(int(national_dex_id), f"Species #{national_dex_id}")
    return fallback or "Pokemon"


def _types_for_national(national_dex_id: int | None) -> list[str]:
    if not national_dex_id:
        return []
    stats = BASE_STATS.get(int(national_dex_id)) or {}
    return [str(type_name) for type_name in stats.get("types", [])]


def _level_for_pokemon(pokemon: dict[str, Any], national_dex_id: int | None) -> int:
    level = _as_int(pokemon.get("level"), 0)
    if 1 <= level <= 100:
        return level
    if not national_dex_id:
        return max(0, level)
    experience = pokemon.get("experience")
    if experience in (None, ""):
        summary = pokemon.get("summary") if isinstance(pokemon.get("summary"), dict) else {}
        canonical = pokemon.get("canonical") if isinstance(pokemon.get("canonical"), dict) else {}
        experience = summary.get("experience")
        if experience in (None, ""):
            experience = canonical.get("experience")
    if experience in (None, ""):
        return max(0, level)
    try:
        return level_from_species_experience(int(national_dex_id), _as_int(experience, 0))
    except Exception:
        return max(0, level)


def _experience_for_pokemon(
    pokemon: dict[str, Any],
    summary: dict[str, Any],
    canonical: dict[str, Any],
) -> int | None:
    for value in (pokemon.get("experience"), summary.get("experience"), canonical.get("experience")):
        if value not in (None, ""):
            return _as_int(value, 0)
    return None


def enrich_one_pokemon(pokemon: dict[str, Any], default_generation: int = 0, default_game: str = "") -> dict[str, Any]:
    enriched = dict(pokemon or {})
    summary = dict(enriched.get("summary") or {})
    canonical = dict(enriched.get("canonical") or {})
    generation = _as_int(enriched.get("generation") or enriched.get("source_generation") or default_generation, 0)
    species_id = _as_int(enriched.get("species_id") or summary.get("species_id"), 0)
    is_egg = bool(enriched.get("is_egg"))

    national_dex_id, species_error = (None, None) if is_egg else _native_species(generation, species_id)
    species_name = "Egg" if is_egg else _species_name(national_dex_id, str(enriched.get("species_name") or ""))
    level = 1 if is_egg and not _as_int(enriched.get("level"), 0) else _level_for_pokemon(enriched, national_dex_id)
    experience = _experience_for_pokemon(enriched, summary, canonical)
    if experience is not None and national_dex_id:
        try:
            experience_progress = experience_progress_for_species(int(national_dex_id), experience)
        except Exception:
            experience_progress = {}
    else:
        existing_progress = enriched.get("experience_progress")
        experience_progress = dict(existing_progress) if isinstance(existing_progress, dict) else {}

    held_item_id = _as_int(enriched.get("held_item_id") or summary.get("held_item_id"), 0)
    item_valid = item_exists(held_item_id or None, generation)
    held_name = item_name(held_item_id or None, generation) if item_valid else None
    held_category = item_category(held_item_id or None, generation) if item_valid else None

    move_ids = [_as_int(move_id, 0) for move_id in (enriched.get("moves") or summary.get("moves") or []) if _as_int(move_id, 0)]
    move_labels = [move_name(move_id) or f"Move #{move_id}" for move_id in move_ids]
    invalid_moves = [move_id for move_id in move_ids if not move_exists(move_id, generation)]

    nickname = str(enriched.get("nickname") or species_name)
    display_name = nickname or species_name
    display_summary = str(enriched.get("display_summary") or (f"{display_name} Lv.{level}" if level else display_name))

    enriched.update(
        {
            "generation": generation,
            "game": str(enriched.get("game") or enriched.get("source_game") or default_game or ""),
            "species_id": species_id,
            "species_name": species_name,
            "national_dex_id": national_dex_id,
            "species_valid": species_error is None,
            "species_error": species_error or "",
            "types": [] if is_egg else _types_for_national(national_dex_id),
            "level": level,
            "experience": experience if experience is not None else enriched.get("experience"),
            "experience_progress": experience_progress,
            "nickname": nickname,
            "held_item_id": held_item_id or None,
            "held_item_name": held_name,
            "held_item_category": held_category or "item",
            "held_item_valid": bool(item_valid),
            "moves": move_ids,
            "move_names": move_labels,
            "invalid_moves": invalid_moves,
            "display_summary": display_summary,
            "sprite": {
                "national_dex_id": national_dex_id,
                "species_name": species_name,
            },
        }
    )
    return enriched


def enrich_pokemon_payload(payload: dict[str, Any]) -> dict[str, Any]:
    generation = _as_int(payload.get("generation") or payload.get("source_generation"), 0)
    game = str(payload.get("game") or payload.get("source_game") or "")
    pokemon = payload.get("pokemon") or []
    return {
        "generation": generation,
        "game": game,
        "pokemon": [
            enrich_one_pokemon(entry, default_generation=generation, default_game=game)
            for entry in pokemon
            if isinstance(entry, dict)
        ],
    }


def trade_evolution_dict(payload: dict[str, Any]) -> dict[str, Any]:
    generation = _as_int(payload.get("generation") or payload.get("source_generation"), 0)
    species_id = _as_int(payload.get("species_id"), 0)
    held_item_id = _as_int(payload.get("held_item_id") or (payload.get("summary") or {}).get("held_item_id"), 0) or None
    national_dex_id, species_error = _native_species(generation, species_id)
    if species_error:
        return {
            "generation": generation,
            "evolved": False,
            "source_species_id": species_id,
            "target_species_id": species_id,
            "source_name": f"Species #{species_id}",
            "target_name": f"Species #{species_id}",
            "reason": "invalid_species",
        }
    result = preview_trade_evolution(
        generation,
        species_id,
        held_item_id=held_item_id,
    )
    return {
        "generation": generation,
        "evolved": bool(result.evolved),
        "source_species_id": int(result.source_species_id),
        "target_species_id": int(result.target_species_id),
        "source_name": result.source_name or _species_name(national_dex_id),
        "target_name": result.target_name or _species_name(national_dex_id),
        "consumed_item_id": result.consumed_item_id,
        "consumed_item_name": result.consumed_item_name,
        "reason": result.reason,
    }


def _build_target_parser(payload: dict[str, Any], target_generation: int):
    save_blob = str(payload.get("target_save_bytes_base64") or "").strip()
    if not save_blob:
        return None
    parser_cls = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser, 4: Gen4Parser}.get(int(target_generation))
    if parser_cls is None:
        return None
    suffix = str(payload.get("target_save_suffix") or ".sav")
    raw = base64.b64decode(save_blob.encode("ascii"))
    tmpdir = tempfile.TemporaryDirectory(prefix="pokecable_runtime_preflight_")
    tmp_path = Path(tmpdir.name) / f"target{suffix if suffix.startswith('.') else '.sav'}"
    tmp_path.write_bytes(raw)
    parser = parser_cls()
    parser.load(tmp_path)
    return tmpdir, parser


def _build_source_parser(payload: dict[str, Any], source_generation: int):
    save_blob = str(payload.get("source_save_bytes_base64") or "").strip()
    if not save_blob:
        return None
    parser_cls = {1: Gen1Parser, 2: Gen2Parser, 3: Gen3Parser, 4: Gen4Parser}.get(int(source_generation))
    if parser_cls is None:
        return None
    suffix = str(payload.get("source_save_suffix") or ".sav")
    raw = base64.b64decode(save_blob.encode("ascii"))
    tmpdir = tempfile.TemporaryDirectory(prefix="pokecable_runtime_outgoing_")
    tmp_path = Path(tmpdir.name) / f"source{suffix if suffix.startswith('.') else '.sav'}"
    tmp_path.write_bytes(raw)
    parser = parser_cls()
    parser.load(tmp_path)
    return tmpdir, parser


def build_trade_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    received = dict(payload.get("received_payload") or payload.get("payload") or {})
    target_generation = _as_int(payload.get("target_generation") or received.get("target_generation") or received.get("generation"), 0)
    target_game = str(payload.get("target_game") or received.get("target_game") or "")
    source_generation = _as_int(received.get("generation") or received.get("source_generation"), 0)
    reasons: list[str] = []
    warnings: list[str] = []

    if not received:
        reasons.append("Oferta remota ausente.")
    enriched = enrich_one_pokemon(received, default_generation=source_generation)
    if not enriched.get("species_valid"):
        reasons.append(str(enriched.get("species_error") or "Pokemon invalido."))
    level = _as_int(enriched.get("level"), 0)
    if level < 1 or level > 100:
        reasons.append("Nivel do Pokemon esta fora do intervalo 1-100.")
    if not enriched.get("held_item_valid", True):
        reasons.append("Item segurado nao existe nessa geracao.")
    if enriched.get("invalid_moves"):
        warnings.append(f"Movimentos invalidos nessa geracao: {', '.join(str(move) for move in enriched['invalid_moves'])}.")

    evolution = trade_evolution_dict(received)
    mode = "same_generation" if source_generation == target_generation else "cross_generation"
    removed_moves: list[dict[str, Any]] = []
    removed_items: list[dict[str, Any]] = []
    transformations: list[str] = []
    suggested_actions: list[str] = []
    requires_user_confirmation = False
    if mode == "cross_generation" and source_generation and target_generation:
        canonical_payload = received.get("canonical") if isinstance(received.get("canonical"), dict) else None
        if not canonical_payload:
            reasons.append("Payload cross-generation sem dados canonical.")
        else:
            try:
                canonical = CanonicalPokemon.from_dict(canonical_payload)
                try:
                    converter = get_converter(source_generation, target_generation)
                except KeyError:
                    reasons.append(f"Conversao Gen {source_generation} -> Gen {target_generation} nao suportada.")
                    converter = None
                if converter is not None:
                    report = converter.can_convert(canonical, policy="auto_retrocompat", target_game=target_game)
                    removed_moves = list(report.removed_moves or [])
                    removed_items = list(report.removed_items or [])
                    transformations = [str(item).strip() for item in (report.transformations or []) if str(item).strip()]
                    suggested_actions = [str(item).strip() for item in (report.suggested_actions or []) if str(item).strip()]
                    requires_user_confirmation = bool(report.requires_user_confirmation)
                    for reason in report.blocking_reasons or []:
                        text = str(reason).strip()
                        if text and text not in reasons:
                            reasons.append(text)
                    for warning in report.warnings or []:
                        text = str(warning).strip()
                        if text and text not in warnings:
                            warnings.append(text)
            except Exception as exc:
                reasons.append(f"Erro avaliando compatibilidade: {exc}")
                removed_moves = []
                removed_items = []
                transformations = []
                suggested_actions = []
                requires_user_confirmation = False
    compatible = not reasons
    return {
        "compatible": compatible,
        "mode": mode,
        "source_generation": source_generation,
        "target_generation": target_generation,
        "target_game": target_game,
        "blocking_reasons": reasons,
        "warnings": warnings,
        "data_loss": [],
        "suggested_actions": suggested_actions,
        "pokemon": enriched,
        "trade_evolution": evolution,
        "removed_moves": removed_moves,
        "removed_items": removed_items,
        "transformations": transformations,
        "requires_user_confirmation": requires_user_confirmation,
        "item_relocation": {},
    }


def build_outgoing_item_relocation(payload: dict[str, Any]) -> dict[str, Any]:
    sent = dict(payload.get("sent_payload") or payload.get("payload") or {})
    target_generation = _as_int(payload.get("target_generation") or sent.get("target_generation"), 0)
    target_game = str(payload.get("target_game") or sent.get("target_game") or "")
    source_generation = _as_int(sent.get("generation") or sent.get("source_generation"), 0)
    if not sent or not source_generation or not target_generation or source_generation == target_generation:
        return {}
    canonical_payload = sent.get("canonical") if isinstance(sent.get("canonical"), dict) else None
    if not canonical_payload:
        return {}
    try:
        canonical = CanonicalPokemon.from_dict(canonical_payload)
        converter = get_converter(source_generation, target_generation)
        report = converter.can_convert(canonical, policy="auto_retrocompat", target_game=target_game)
        if not report.removed_items:
            return {}
        source_parser_bundle = _build_source_parser(payload, source_generation)
        if source_parser_bundle is None:
            return {}
        tmpdir, source_parser = source_parser_bundle
        try:
            raw_item_relocation = converter.inspect_item_relocation(canonical, source_parser, report)
        finally:
            tmpdir.cleanup()
        if not raw_item_relocation:
            return {}
        item_relocation = dict(raw_item_relocation)
        item_relocation["source_generation"] = source_generation
        item_relocation["target_generation"] = target_generation
        return item_relocation
    except Exception:
        return {}
