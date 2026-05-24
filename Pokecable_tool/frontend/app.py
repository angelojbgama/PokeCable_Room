#!/usr/bin/env python3
"""
PokeCable Room - R36S UI
Interface para trading de Pokemon via WebSocket.
"""

import os
import sys
import time
import math
import random
import logging
import queue
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("AUDIODEV", "null")

DEBUG = os.getenv("POKECABLE_DEBUG", "0").lower() in ("1", "true", "yes")

try:
    import pygame
except ImportError:
    print("pygame required: run ./pokecable.sh", file=sys.stderr)
    sys.exit(1)

from pokecable_logging import configure_logging
from pokecable_save import SaveError, _ensure_backend_import_path
from frontend.fonts import font, gender_font, title_font
from frontend.i18n import TYPE_LABELS, TYPE_LABELS_BY_LANG, screen_title, t, translate_literal
from frontend.item_sprites import draw_item_sprite
from frontend.input import (
    ACTION_DEBOUNCE,
    AXIS_THRESHOLD,
    AXIS_X,
    AXIS_Y,
    JOY_BUTTON_SELECT,
    JOY_BUTTON_START,
    JOY_MAP,
    QUIT_COMBO_WINDOW,
    debounce_action,
    event_to_action,
    translate_joy_button,
    translate_key,
)
from frontend.sprites import (
    SPRITE_LOADING_MAX_SECONDS,
    SpriteLoader,
    pokemon_sprite_slug,
    pokemon_sprite_variant,
    resolve_sprite_national_dex_id,
    sprite_form_slug,
)
from frontend.queue_dispatch import dispatch_ui_queue
from frontend.screens import ScreenController, register_default_screens
from frontend.session import InputSessionState, MutableRef, UiContext, UiServices, UiSessionState
from frontend.theme import next_theme, palette_for_theme, theme_display_name
from frontend.trade_flow import (
    advance_self_trade_prompts,
    finish_self_trade,
    load_self_trade_party,
    load_self_trade_source,
    reload_after_pc_management,
    self_trade_source_label,
)
from frontend.components.primitives import (
    FooterActionStyle,
    LIST_SCROLLBAR,
    PokedexFrame as PokedexFrameElement,
    PokedexStyle,
    SelectableListItemStyle,
    compact_action_label as compact_footer_action_label,
    draw_digital_visor as draw_digital_visor_element,
    draw_footer_action_button as draw_footer_action_button_component,
    draw_footer_actions as draw_footer_actions_component,
    draw_glass_panel as draw_glass_panel_element,
    draw_item_icon as draw_item_icon_element,
    draw_lens_pulse as draw_lens_pulse_element,
    draw_pokedex_shell as draw_pokedex_shell_element,
    draw_right_panel_frame as draw_right_panel_frame_element,
    draw_selectable_list_item as draw_selectable_list_item_component,
    draw_type_badges as draw_type_badges_element,
    fit_text as fit_text_element,
    normalized_rect as normalized_rect_element,
    rect as rect_element,
    render_title_sweep as render_title_sweep_element,
    right_info_panel as right_info_panel_element,
    text as text_element,
    text_center as text_center_element,
    text_right as text_right_element,
    wrap_text as wrap_text_element,
)
from r36s_pokecable_core import (
    PokecableState,
    execute_self_trade,
    prepare_self_trade,
    validate_self_trade_candidate,
    start_trade_thread,
    start_lan_trade_thread,
    request_trade_cancel,
    request_leave_room,
    _create_backup,
)


LOG_PATHS = configure_logging()
ERROR_LOG = Path(str(LOG_PATHS["error_log"]))

logger = logging.getLogger("r36s_pokecable_ui")

logger.info("=" * 80)
logger.info("PokeCable Room - R36S UI")
logger.info("Error log: %s", ERROR_LOG)
logger.info("=" * 80)

SCREEN_W, SCREEN_H = 640, 480
HEADER_H, FOOTER_H = 44, 60
LIST_W = 250
INPUT_TRANSITION_GUARD_SECONDS = 0.25
NAV_REPEAT_DELAY = 0.25
NAV_REPEAT_INTERVAL = 0.06
ROW_H = 52
ROW_VISIBLE = 6
GUARDED_INPUT_ACTIONS = {"select", "back", "x", "y", "up", "down", "left", "right"}

BG = (0, 0, 0)
SHELL = (0, 0, 0)
SHELL_2 = (0, 0, 0)
PANEL = (0, 0, 0)
PANEL_2 = (0, 0, 0)
SCREEN = (0, 0, 0)
SCREEN_TEXT = (255, 255, 255)
BORDER = (0, 0, 0)
SHADOW = (0, 0, 0)
TEXT = (255, 255, 255)
MUTED = (155, 155, 155)
ACCENT = (255, 0, 0)
OK = (0, 200, 0)
RED = (255, 0, 0)
WARN = (255, 200, 0)


def animate_led_color(elapsed_time, cycle_duration=1.0):
    """Anima cor do LED entre MUTED (cinza) e ACCENT (azul)."""
    progress = (elapsed_time % cycle_duration) / cycle_duration
    if progress > 0.5:
        progress = 1.0 - progress
    progress *= 2

    r = int(MUTED[0] + (ACCENT[0] - MUTED[0]) * progress)
    g = int(MUTED[1] + (ACCENT[1] - MUTED[1]) * progress)
    b = int(MUTED[2] + (ACCENT[2] - MUTED[2]) * progress)
    return (r, g, b)


def apply_theme(theme_name):
    global BG, SHELL, SHELL_2, PANEL, PANEL_2, SCREEN, SCREEN_TEXT, BORDER, SHADOW, TEXT, MUTED, ACCENT, OK, RED, WARN
    palette = palette_for_theme(theme_name)
    BG = palette["bg"]
    SHELL = palette["shell"]
    SHELL_2 = palette["shell_2"]
    PANEL = palette["panel"]
    PANEL_2 = palette["panel_2"]
    SCREEN = palette["screen"]
    SCREEN_TEXT = palette["screen_text"]
    BORDER = palette["border"]
    SHADOW = palette["shadow"]
    TEXT = palette["text"]
    MUTED = palette["muted"]
    ACCENT = palette["accent"]
    OK = palette["ok"]
    RED = palette["red"]
    WARN = palette["warn"]

SCROLL_STATE = {}
TITLE_SWEEP_STATE = {"start_time": 0.0}
LENS_PULSE_STATE = {"start_time": 0.0, "title": None}
MENU_VISOR_STATE = {"title": None, "start_time": 0.0}
SELECT_SAVE_VISOR_STATE = {"title": None, "start_time": 0.0}
KEYBOARD_GRID_W = 12
POKEMON_ROOM_NAMES = [
    "Pikachu", "Eevee", "Snorlax", "Charizard", "Bulbasaur", "Squirtle",
    "Gengar", "Dragonite", "Lapras", "Mew", "Mewtwo", "Lucario",
    "Garchomp", "Greninja", "Umbreon", "Espeon", "Jolteon", "Vaporeon",
    "Flareon", "Sylveon", "Ditto", "Tyranitar", "Blaziken", "Sceptile",
    "Swampert", "Rayquaza", "Gardevoir", "Arcanine", "Machamp", "Alakazam",
]
TYPE_COLORS = {
    "normal": (168, 167, 122),
    "fire": (238, 129, 48),
    "water": (99, 144, 240),
    "electric": (247, 208, 44),
    "grass": (122, 199, 76),
    "ice": (150, 217, 214),
    "fighting": (194, 46, 40),
    "poison": (163, 62, 161),
    "ground": (226, 191, 101),
    "flying": (169, 143, 243),
    "psychic": (249, 85, 135),
    "bug": (166, 185, 26),
    "rock": (182, 161, 54),
    "ghost": (115, 87, 151),
    "dragon": (111, 53, 252),
    "dark": (112, 87, 70),
    "steel": (183, 183, 206),
    "fairy": (214, 133, 173),
}

def _resolve_item_name_by_id(item_id, generation):
    try:
        item_id = int(item_id or 0)
    except (TypeError, ValueError):
        return None
    try:
        generation = int(generation or 0)
    except (TypeError, ValueError):
        generation = 0
    if item_id <= 0 or generation <= 0:
        return None
    try:
        _ensure_backend_import_path()
        from data.items import item_name as runtime_item_name  # type: ignore

        return runtime_item_name(item_id, generation)
    except Exception:
        return None


def held_item_label(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    item_id = (pokemon or {}).get("held_item_id") or raw.get("held_item_id")
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    held_item = canonical.get("held_item", {}) if isinstance(canonical, dict) else {}
    generation = (
        (pokemon or {}).get("generation")
        or raw.get("generation")
        or canonical.get("source_generation")
        or (pokemon or {}).get("source_generation")
    )
    item_name = (
        (pokemon or {}).get("held_item_name")
        or raw.get("held_item_name")
        or held_item.get("name")
        or _resolve_item_name_by_id(item_id, generation)
    )
    if not item_id:
        return "Item: nenhum"
    return f"Item: {item_name or f'#{item_id}'}"


def held_item_info(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    held_item = canonical.get("held_item", {}) if isinstance(canonical, dict) else {}
    item_id = (pokemon or {}).get("held_item_id") or raw.get("held_item_id")
    if not item_id:
        return None
    item_id = int(item_id)
    generation = (
        (pokemon or {}).get("generation")
        or raw.get("generation")
        or canonical.get("source_generation")
        or (pokemon or {}).get("source_generation")
    )
    return {
        "id": item_id,
        "name": (
            (pokemon or {}).get("held_item_name")
            or raw.get("held_item_name")
            or held_item.get("name")
            or _resolve_item_name_by_id(item_id, generation)
            or f"#{item_id}"
        ),
        "category": (pokemon or {}).get("held_item_category") or raw.get("held_item_category") or "item",
        "generation": generation,
    }


def pokemon_display_name(pokemon, fallback="Pokemon"):
    pokemon = pokemon or {}
    base = (
        pokemon.get("nickname")
        or pokemon.get("species_name")
        or pokemon.get("name")
        or pokemon.get("display_summary")
        or pokemon.get("display")
        or fallback
    )
    gender = pokemon.get("gender")
    if gender in ("♂", "♀"):
        return f"{base} {gender}"
    return base


def pokemon_compact_label(pokemon, fallback, language="pt"):
    name = pokemon_display_name(pokemon, fallback)
    level = (pokemon or {}).get("level")
    if level:
        return f"{name} {t(language, 'level_tag', level=level)}"
    return name


def move_labels(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    names = (pokemon or {}).get("move_names") or raw.get("move_names") or []
    moves = (pokemon or {}).get("moves") or raw.get("moves") or []
    if names:
        labels = []
        for idx, name in enumerate(names[:4]):
            if not name:
                continue
            move_id = moves[idx] if idx < len(moves) else 0
            labels.append(local_move_name(move_id) if is_move_number_label(name) and move_id else str(name))
        return labels
    labels = []
    for move_id in moves[:4]:
        if not move_id:
            continue
        move_id = int(move_id)
        labels.append(local_move_name(move_id))
    return labels


def _pokemon_generation_for_moves(pokemon):
    if not isinstance(pokemon, dict):
        return 0
    raw = pokemon.get("raw") if isinstance(pokemon.get("raw"), dict) else {}
    summary = pokemon.get("summary") if isinstance(pokemon.get("summary"), dict) else {}
    canonical = pokemon.get("canonical") if isinstance(pokemon.get("canonical"), dict) else {}
    for value in (
        pokemon.get("generation"),
        pokemon.get("source_generation"),
        summary.get("generation"),
        summary.get("source_generation"),
        raw.get("generation"),
        canonical.get("source_generation"),
    ):
        try:
            generation = int(value or 0)
        except (TypeError, ValueError):
            generation = 0
        if generation > 0:
            return generation
    return 0


def _canonical_move_ids_and_names(canonical_moves):
    moves = []
    names = []
    for move in (canonical_moves or [])[:4]:
        if not isinstance(move, dict):
            continue
        try:
            move_id = int(move.get("move_id") or 0)
        except (TypeError, ValueError):
            move_id = 0
        if move_id <= 0:
            continue
        moves.append(move_id)
        names.append(move.get("name") or "")
    return moves, names


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dict_value(value):
    return value if isinstance(value, dict) else {}


def _experience_progress_tuple(progress):
    if not isinstance(progress, dict):
        return None
    if "fill_ratio" not in progress and "next_level_experience" not in progress:
        return None
    try:
        filled = max(0.0, min(1.0, float(progress.get("fill_ratio") or 0.0)))
        current_xp = int(progress.get("experience") or 0)
        next_xp = int(progress.get("next_level_experience") or current_xp)
        return filled, current_xp, next_xp
    except Exception:
        return None


def _pokemon_experience_sources(pokemon):
    pokemon = _dict_value(pokemon)
    raw = _dict_value(pokemon.get("raw"))
    summary = _dict_value(pokemon.get("summary"))
    canonical = _dict_value(pokemon.get("canonical"))
    raw_canonical = _dict_value(raw.get("canonical"))
    raw_summary = _dict_value(raw.get("summary"))
    canonical_species = _dict_value(canonical.get("species"))
    raw_canonical_species = _dict_value(raw_canonical.get("species"))
    canonical_metadata = _dict_value(canonical.get("metadata"))
    raw_canonical_metadata = _dict_value(raw_canonical.get("metadata"))
    return {
        "pokemon": pokemon,
        "raw": raw,
        "summary": summary,
        "raw_summary": raw_summary,
        "canonical": canonical,
        "raw_canonical": raw_canonical,
        "canonical_species": canonical_species,
        "raw_canonical_species": raw_canonical_species,
        "canonical_metadata": canonical_metadata,
        "raw_canonical_metadata": raw_canonical_metadata,
    }


def _resolve_experience_progress(pokemon):
    sources = _pokemon_experience_sources(pokemon)
    for progress in (
        sources["pokemon"].get("experience_progress"),
        sources["summary"].get("experience_progress"),
        sources["raw"].get("experience_progress"),
        sources["raw_summary"].get("experience_progress"),
        sources["canonical_metadata"].get("experience_progress"),
        sources["raw_canonical_metadata"].get("experience_progress"),
    ):
        parsed = _experience_progress_tuple(progress)
        if parsed is not None:
            return dict(progress), parsed

    national_dex_id = _safe_int(
        sources["pokemon"].get("national_dex_id")
        or sources["summary"].get("national_dex_id")
        or sources["raw"].get("national_dex_id")
        or sources["raw_summary"].get("national_dex_id")
        or sources["canonical"].get("species_national_id")
        or sources["raw_canonical"].get("species_national_id")
        or sources["canonical_species"].get("national_dex_id")
        or sources["raw_canonical_species"].get("national_dex_id")
    )
    experience = None
    for source in (
        sources["pokemon"],
        sources["summary"],
        sources["raw"],
        sources["raw_summary"],
        sources["canonical"],
        sources["raw_canonical"],
    ):
        if source.get("experience") not in (None, ""):
            experience = source.get("experience")
            break
    if experience is None:
        return {}, (0.0, 0, 0)

    try:
        _ensure_backend_import_path()
        from data.growth_rates import experience_progress_for_species  # type: ignore

        if national_dex_id <= 0:
            generation = _safe_int(
                sources["pokemon"].get("generation")
                or sources["pokemon"].get("source_generation")
                or sources["summary"].get("generation")
                or sources["summary"].get("source_generation")
                or sources["raw"].get("generation")
                or sources["raw"].get("source_generation")
                or sources["canonical"].get("source_generation")
                or sources["raw_canonical"].get("source_generation")
            )
            internal_species_id = _safe_int(
                sources["pokemon"].get("species_id")
                or sources["summary"].get("species_id")
                or sources["raw"].get("species_id")
                or sources["raw_summary"].get("species_id")
                or sources["canonical_species"].get("source_species_id")
                or sources["raw_canonical_species"].get("source_species_id")
            )
            if generation and internal_species_id:
                try:
                    from data.species import native_to_national  # type: ignore

                    national_dex_id = int(native_to_national(generation, internal_species_id) or 0)
                except Exception:
                    national_dex_id = 0
        if national_dex_id <= 0:
            return {}, (0.0, 0, 0)
        progress = dict(experience_progress_for_species(national_dex_id, int(experience)))
        parsed = _experience_progress_tuple(progress)
        return progress, parsed or (0.0, 0, 0)
    except Exception:
        return {}, (0.0, 0, 0)


def enrich_pokemon_experience_for_display(pokemon):
    if not isinstance(pokemon, dict):
        return pokemon
    progress, parsed = _resolve_experience_progress(pokemon)
    if not progress:
        return pokemon
    enriched = dict(pokemon)
    enriched["experience_progress"] = progress
    if enriched.get("experience") in (None, ""):
        enriched["experience"] = parsed[1]
    return enriched


def move_display_entries(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    summary = (pokemon or {}).get("summary", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    canonical = canonical if isinstance(canonical, dict) else {}
    canonical_moves = (canonical.get("moves") if isinstance(canonical, dict) else []) or []
    moves = (pokemon or {}).get("moves") or summary.get("moves") or raw.get("moves") or []
    names = (pokemon or {}).get("move_names") or summary.get("move_names") or raw.get("move_names") or []
    if not moves and canonical_moves:
        moves, names = _canonical_move_ids_and_names(canonical_moves)
    raw_move_details = raw.get("move_details") if isinstance(raw, dict) else []
    summary_move_details = summary.get("move_details") if isinstance(summary, dict) else []
    top_move_details = (pokemon or {}).get("move_details") if isinstance(pokemon, dict) else []
    raw_move_details = raw_move_details if isinstance(raw_move_details, list) else []
    summary_move_details = summary_move_details if isinstance(summary_move_details, list) else []
    top_move_details = top_move_details if isinstance(top_move_details, list) else []
    generation = _pokemon_generation_for_moves(pokemon)
    entries = []
    for idx, move_id in enumerate(moves[:4]):
        if not move_id:
            continue
        move_id = int(move_id)
        name = names[idx] if idx < len(names) and names[idx] else local_move_name(move_id)
        if is_move_number_label(name):
            name = local_move_name(move_id)
        current_pp = None
        max_pp = None
        move_detail = None
        if idx < len(canonical_moves) and isinstance(canonical_moves[idx], dict):
            move_detail = canonical_moves[idx]
        if not move_detail and idx < len(top_move_details) and isinstance(top_move_details[idx], dict):
            move_detail = top_move_details[idx]
        if not move_detail and idx < len(summary_move_details) and isinstance(summary_move_details[idx], dict):
            move_detail = summary_move_details[idx]
        if not move_detail and idx < len(raw_move_details) and isinstance(raw_move_details[idx], dict):
            move_detail = raw_move_details[idx]
        if isinstance(move_detail, dict):
            current_pp = move_detail.get("pp")
            max_pp = move_detail.get("max_pp")
        try:
            _ensure_backend_import_path()
            from data.moves import move_base_pp  # type: ignore

            try:
                base_pp = move_base_pp(move_id, generation) or 0
            except TypeError:
                base_pp = move_base_pp(move_id) or 0
        except Exception:
            base_pp = 0
        if max_pp is None or int(max_pp or 0) <= 0:
            max_pp = base_pp
        if current_pp is None or int(current_pp or -1) < 0:
            current_pp = max_pp
        entries.append({"move_id": move_id, "name": name, "pp": int(current_pp or 0), "max_pp": int(max_pp or 0)})
    return entries


def pokemon_xp_bar(pokemon):
    _, parsed = _resolve_experience_progress(pokemon)
    return parsed


def is_move_number_label(value):
    text_value = str(value or "").strip().lower()
    if not text_value.startswith("move #"):
        return False
    return text_value[6:].strip().isdigit()


def local_move_name(move_id):
    numeric_id = 0
    try:
        numeric_id = int(move_id or 0)
        _ensure_backend_import_path()
        from data.moves import move_name  # type: ignore

        return move_name(numeric_id) or f"Move #{numeric_id}"
    except Exception:
        return f"Move #{numeric_id or move_id}"


def pokemon_types(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    types = (pokemon or {}).get("types") or raw.get("types") or []
    if not types:
        candidate = []
        for key in ("type1", "type2", "primary_type", "secondary_type"):
            value = (pokemon or {}).get(key) or raw.get(key)
            if value:
                candidate.append(value)
        types = candidate
    if not types:
        generation = (pokemon or {}).get("generation") or raw.get("generation") or (canonical.get("source_generation") if isinstance(canonical, dict) else 0)
        species_id = (pokemon or {}).get("species_id") or raw.get("species_id") or (canonical.get("species_id") if isinstance(canonical, dict) else 0)
        national_dex_id = resolve_sprite_national_dex_id(generation, species_id, pokemon)
        if national_dex_id:
            try:
                _ensure_backend_import_path()
                from data.base_stats import BASE_STATS  # type: ignore

                types = (BASE_STATS.get(int(national_dex_id)) or {}).get("types") or []
            except Exception:
                types = []
    return [str(type_name).lower() for type_name in types if type_name]


def type_label(type_name, language="pt"):
    labels = TYPE_LABELS_BY_LANG.get(str(language or "pt").lower(), TYPE_LABELS_BY_LANG["pt"])
    return labels.get(type_name, TYPE_LABELS.get(type_name, type_name.title()))


def draw_type_badges(surface, font_obj, type_names, x, y, max_width, language="pt"):
    draw_type_badges_element(
        surface,
        font_obj,
        type_names,
        x,
        y,
        max_width,
        lambda type_name: type_label(type_name, language),
        TYPE_COLORS,
        MUTED,
    )


def draw_item_icon(surface, area, item_info, selected=False):
    if draw_item_sprite(surface, area, item_info, BG if selected else PANEL):
        return
    draw_item_icon_element(surface, area, item_info, selected, BG, PANEL, MUTED, TEXT)


def render_title_sweep(text_surface, progress):
    return render_title_sweep_element(text_surface, progress)


def draw_lens_pulse(screen, center, progress):
    draw_lens_pulse_element(screen, center, progress)


def draw_glass_panel(screen, area, progress, base_color=(170, 188, 214)):
    draw_glass_panel_element(screen, area, progress, base_color)


def draw_digital_visor(screen, area, progress, tint=None):
    draw_digital_visor_element(screen, area, progress, tint=tint)


def text(surface, fnt, value, x, y, color=None, max_w=None):
    if color is None:
        color = TEXT
    text_element(surface, fnt, value, x, y, color, max_w)


def fit_text(fnt, value, max_w):
    return fit_text_element(fnt, value, max_w)


def text_center(surface, fnt, value, area, color=None):
    if color is None:
        color = TEXT
    text_center_element(surface, fnt, value, area, color)


def text_right(surface, fnt, value, area, color=None):
    if color is None:
        color = TEXT
    text_right_element(surface, fnt, value, area, color)


def wrap_text(surface, fnt, value, area, color=None, line_gap=4, max_lines=None):
    if color is None:
        color = TEXT
    return wrap_text_element(surface, fnt, value, area, color, line_gap, max_lines)


def normalized_rect(area):
    return normalized_rect_element(area)


def rect(surface, color, area, radius=0):
    result = rect_element(surface, color, area, radius)
    if result is None:
        logger.warning("Skipping invalid rect draw: area=%r radius=%r", area, radius)
    return result


def compact_action_label(value):
    return compact_footer_action_label(value)


def footer_action_style():
    return FooterActionStyle(
        screen_size=(SCREEN_W, SCREEN_H),
        shadow_color=(209, 230, 248),
        fill_color=(247, 252, 255),
        border_color=BORDER,
        cap_color=ACCENT,
        cap_text_color=SCREEN_TEXT,
        text_color=TEXT,
    )


def selectable_list_item_style():
    return SelectableListItemStyle(
        fill_color=PANEL_2,
        selected_fill_color=ACCENT,
        border_color=BORDER,
        selected_inner_color=(255, 255, 255),
    )


def draw_selectable_list_item(screen, area, selected=False):
    return draw_selectable_list_item_component(screen, area, selected, selectable_list_item_style())


def pokedex_style():
    return PokedexStyle(
        screen_size=(SCREEN_W, SCREEN_H),
        header_height=HEADER_H,
        footer_height=FOOTER_H,
        bg=BG,
        shell=SHELL,
        shell_2=SHELL_2,
        panel_2=PANEL_2,
        screen=SCREEN,
        screen_text=SCREEN_TEXT,
        border=BORDER,
        shadow=SHADOW,
        muted=MUTED,
        accent=ACCENT,
        ok=OK,
        red=RED,
        warn=WARN,
    )


def button(surface, fnt, label, desc, x, y, width=None):
    button_f = font(14)
    cap_f = font(13, True)
    desc = compact_action_label(desc)
    width = int(width or max(64, min(132, button_f.size(str(desc or ""))[0] + 40)))
    area = pygame.Rect(x, y, width, 26)
    draw_footer_action_button_component(surface, (label, desc), area, button_f, cap_f, footer_action_style())


def draw_footer_actions(screen, fnt, actions):
    draw_footer_bar(screen)
    del fnt
    draw_footer_actions_component(screen, actions, font(14), font(13, True), footer_action_style())


def PokedexFrame():
    return PokedexFrameElement((SCREEN_W, SCREEN_H), HEADER_H, FOOTER_H)


def right_info_panel(layout, top_offset=0, inset_x=0, bottom_pad=0):
    return right_info_panel_element(layout, top_offset, inset_x, bottom_pad)


def right_visor_rect(panel):
    top_pad = 16
    side_pad = 12
    height = 100
    return pygame.Rect(panel.x + side_pad, panel.y + top_pad, panel.w - side_pad * 2, height)


def draw_pokemon_detail_component(screen, fonts, panel_area, pokemon, display_name, sprite, loading, language="pt", visor_tint=None):
    """Componente modular: visor digital + box informativo com item e ataques."""
    _, _, small_f, tiny_f = fonts
    pokemon = enrich_pokemon_experience_for_display(pokemon)

    side_pad = 12
    visor_height = 100
    visor_x = panel_area.x + side_pad
    visor_y = panel_area.y + 16
    visor_w = panel_area.w - side_pad * 2

    visor_area = pygame.Rect(visor_x, visor_y, visor_w, visor_height)

    draw_digital_visor(screen, visor_area, 1.0, tint=visor_tint)
    pygame.draw.rect(screen, BORDER, visor_area, 2)

    sprite_box = pygame.Rect(visor_area.x + 2, visor_area.y + 8, 80, 80)
    if sprite:
        scaled = pygame.transform.smoothscale(sprite, (80, 80))
        screen.blit(scaled, sprite_box.topleft)
    elif loading:
        wrap_text(screen, tiny_f, t(language, "loading_sprite"), pygame.Rect(sprite_box.x + 4, sprite_box.y + 30, sprite_box.w - 8, 18), MUTED, max_lines=2)
    else:
        text_center(screen, tiny_f, t(language, "no_sprite"), sprite_box, MUTED)

    text_x = sprite_box.right + 8
    text_w = visor_area.right - text_x - 8
    name_area = pygame.Rect(text_x, visor_area.y + 8, text_w, 18)
    level = int((pokemon or {}).get("level") or 0)
    name_f = font(11)
    wrap_text(screen, name_f, display_name, name_area, (0, 0, 0), line_gap=1, max_lines=1)

    level_y = visor_area.y + 30
    level_text = f"Nivel {level}" if level else t(language, "level_unknown")
    level_surface = font(10).render(level_text, True, (0, 0, 0))
    screen.blit(level_surface, (text_x, level_y))

    type_box = pygame.Rect(text_x, level_y + 14, text_w, 22)
    draw_digital_visor(screen, type_box, 1.0)
    type_names = pokemon_types(pokemon)
    if type_names:
        tint = TYPE_COLORS.get(type_names[0], (170, 232, 206))
        overlay = pygame.Surface(type_box.size, pygame.SRCALPHA)
        overlay.fill((tint[0], tint[1], tint[2], 42))
        pygame.draw.rect(overlay, (255, 255, 255, 60), overlay.get_rect(), 1)
        screen.blit(overlay, type_box.topleft)
    pygame.draw.rect(screen, BORDER, type_box, 1)
    type_label_text = " / ".join(type_label(type_name, language) for type_name in type_names[:2]) or "-"
    type_surface = font(10).render(type_label_text, True, (0, 0, 0))
    screen.blit(type_surface, type_surface.get_rect(center=type_box.center))

    xp_fill, _, _ = pokemon_xp_bar(pokemon)
    xp_bar = pygame.Rect(text_x, type_box.bottom + 6, text_w, 10)
    rect(screen, (214, 214, 214), xp_bar, 0)
    pygame.draw.rect(screen, BORDER, xp_bar, 1, border_radius=0)
    if xp_fill > 0:
        fill_w = max(2, int((xp_bar.w - 2) * xp_fill))
        rect(screen, ACCENT, pygame.Rect(xp_bar.x + 1, xp_bar.y + 1, fill_w, xp_bar.h - 2), 0)

    summary_top = visor_area.bottom + 8
    summary_panel = pygame.Rect(panel_area.x + side_pad, summary_top, panel_area.w - side_pad * 2, panel_area.bottom - summary_top - 8)
    if summary_panel.h > 0:
        rect(screen, PANEL_2, summary_panel, 0)
        pygame.draw.rect(screen, BORDER, summary_panel, 2)

        location = pokemon.get("location", "")
        if location.startswith("box:"):
            parts = location.split(":")
            place_text = pokemon.get("raw", {}).get("box_name") or f"Box {int(parts[1]) + 1}"
        else:
            place_text = t(language, "party")
        save_label = pokemon.get("save_name") or (pokemon.get("raw", {}) or {}).get("save_name") or ""
        text(screen, tiny_f, place_text, summary_panel.x + 8, summary_panel.y + 2, SCREEN_TEXT, summary_panel.w - 16)

        item_info = held_item_info(pokemon)
        item_text = item_info["name"] if item_info else t(language, "item_none")
        item_icon = pygame.Rect(summary_panel.x + 6, summary_panel.y + 20, 32, 32)
        draw_item_icon(screen, item_icon, item_info)
        text(screen, tiny_f, item_text, item_icon.right + 6, summary_panel.y + 28, MUTED, summary_panel.w - 26)

        moves_panel = pygame.Rect(summary_panel.x + 8, summary_panel.y + 50, summary_panel.w - 16, summary_panel.h - 58)
        text(screen, small_f, t(language, "moves"), moves_panel.x, moves_panel.y, TEXT, moves_panel.w)
        move_entries = move_display_entries(pokemon)
        if move_entries:
            move_f = font(11)
            for move_idx, move_entry in enumerate(move_entries[:4]):
                move_y = moves_panel.y + 20 + move_idx * 20
                move_rect = pygame.Rect(moves_panel.x, move_y, moves_panel.w, 16)
                rect(screen, BG, move_rect, 0)
                pygame.draw.rect(screen, BORDER, move_rect, 1, border_radius=0)
                name_area = pygame.Rect(move_rect.x + 6, move_rect.y + 1, move_rect.w - 60, 14)
                text(screen, move_f, move_entry["name"], name_area.x, name_area.y, TEXT, name_area.w)
                pp_text = f"{move_entry['pp']}/{move_entry['max_pp']}" if move_entry.get("max_pp") else str(move_entry["pp"])
                pp_area = pygame.Rect(move_rect.right - 52, move_rect.y + 1, 48, 14)
                pp_surface = tiny_f.render(pp_text, True, MUTED)
                screen.blit(pp_surface, pp_surface.get_rect(midright=pp_area.midright))
        else:
            text(screen, tiny_f, t(language, "no_moves"), moves_panel.x, moves_panel.y + 20, MUTED, moves_panel.w)

        if save_label:
            text(screen, tiny_f, str(save_label), summary_panel.x + 8, summary_panel.bottom - 22, MUTED, summary_panel.w - 16)


def draw_right_panel_frame(screen, panel, progress=None, glass=False):
    draw_right_panel_frame_element(screen, panel, pokedex_style(), progress, glass)


def draw_pokedex_shell(screen, title="", subtitle="", loading_progress=1.0, pulsing=False, ok_pulse=False, warn_pulse=False):
    return draw_pokedex_shell_element(
        screen,
        title,
        subtitle,
        pokedex_style(),
        font,
        title_font,
        LENS_PULSE_STATE,
        TITLE_SWEEP_STATE,
        loading_progress,
        pulsing,
        ok_pulse=ok_pulse,
        warn_pulse=warn_pulse,
    )


def draw_footer_bar(screen):
    return None


def list_scroll_offset(key, selected, total, visible=ROW_VISIBLE):
    if total <= visible:
        SCROLL_STATE[key] = 0.0
        return 0.0
    max_start = max(0, total - visible)
    target = min(max(0, int(selected) - visible // 2), max_start)
    current = min(max(0.0, float(SCROLL_STATE.get(key, target))), float(max_start))
    if abs(target - current) > visible:
        current = float(target)
    current += (target - current) * 0.35
    if abs(target - current) < 0.03:
        current = float(target)
    SCROLL_STATE[key] = current
    return current



def draw_menu(screen, fonts, selected, language):
    _, _, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, "PokeCable")

    items = [
        t(language, "menu_access_room"),
        t(language, "menu_self_trade"),
        t(language, "menu_config"),
        t(language, "menu_infos"),
        t(language, "menu_update"),
        t(language, "menu_exit"),
    ]
    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 0)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)

    for idx, item in enumerate(items):
        y = list_panel.y + 14 + idx * 48
        row = pygame.Rect(list_panel.x + 10, y, list_panel.w - 20, 38)
        color = SCREEN if idx == selected else TEXT
        draw_selectable_list_item(screen, row, idx == selected)
        text(screen, small_f, item, row.x + 9, row.y + 9, color, row.w - 18)

    info_panel = right_info_panel(layout)
    rect(screen, PANEL_2, info_panel, 0)
    pygame.draw.rect(screen, BORDER, info_panel, 2, border_radius=0)
    title_rect = right_visor_rect(info_panel)
    if MENU_VISOR_STATE["title"] != "menu":
        MENU_VISOR_STATE["title"] = "menu"
        MENU_VISOR_STATE["start_time"] = time.perf_counter()
    visor_elapsed = max(0.0, time.perf_counter() - MENU_VISOR_STATE["start_time"])
    visor_duration = 1.2
    draw_digital_visor(screen, title_rect, min(visor_elapsed / visor_duration, 1.0))
    pygame.draw.rect(screen, BORDER, title_rect, 2)
    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))])


def draw_infos_topics(screen, fonts, selected, language):
    """List of Info topics on the left, simple info on the right."""
    from frontend.infos_content import get_topics
    _, _, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, t(language, "infos_title"))

    topics = get_topics(language)
    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 0)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)
    # i18n keys for each topic
    topic_i18n = {"retrocompat": "infos_topic_retrocompat", "about": "infos_topic_about"}
    for idx, (key, _) in enumerate(topics):
        y = list_panel.y + 14 + idx * 48
        row = pygame.Rect(list_panel.x + 10, y, list_panel.w - 20, 38)
        color = SCREEN if idx == selected else TEXT
        draw_selectable_list_item(screen, row, idx == selected)
        text(screen, small_f, t(language, topic_i18n.get(key, "infos_topic_retrocompat")),
             row.x + 9, row.y + 9, color, row.w - 18)

    info_panel = right_info_panel(layout)
    rect(screen, PANEL_2, info_panel, 0)
    pygame.draw.rect(screen, BORDER, info_panel, 2, border_radius=0)
    title_rect = right_visor_rect(info_panel)
    draw_digital_visor(screen, title_rect, 1.0)
    pygame.draw.rect(screen, BORDER, title_rect, 2)
    # Brief teaser inside the visor
    wrap_text(
        screen, small_f,
        t(language, "infos_topic_retrocompat") if selected == 0 else t(language, "infos_topic_about"),
        pygame.Rect(title_rect.x + 10, title_rect.y + 10, title_rect.w - 20, title_rect.h - 20),
        (0, 0, 0), line_gap=2, max_lines=3,
    )
    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))])


def draw_infos_reader(screen, fonts, topic_key, scroll, language):
    """Scrollable article view. Returns the maximum scroll value for clamping."""
    from frontend.infos_content import get_article
    _, body_f, small_f, tiny_f = fonts
    article = get_article(topic_key, language)
    layout = draw_pokedex_shell(screen, article["title"])

    # Full-width content panel = both halves combined for max reading room.
    content_panel = pygame.Rect(
        layout.left_panel.x,
        layout.left_panel.y,
        right_info_panel(layout).right - layout.left_panel.x,
        layout.left_panel.h,
    )
    rect(screen, PANEL, content_panel, 0)
    pygame.draw.rect(screen, BORDER, content_panel, 2, border_radius=0)

    inner_pad = 12
    text_x = content_panel.x + inner_pad
    text_y0 = content_panel.y + inner_pad
    text_w = content_panel.w - inner_pad * 2
    text_h = content_panel.h - inner_pad * 2 - 18  # leave room for scroll hint

    # Pre-render paragraphs into wrapped lines so we know total height + can clip.
    line_height = small_f.get_linesize() + 2
    paragraph_gap = 6
    lines: list[tuple[str, int]] = []  # (line text, y_offset_within_doc)
    cursor_y = 0
    for paragraph in article["paragraphs"]:
        # Use the same word-wrap algorithm as wrap_text but capture per-line strings
        words = paragraph.replace("\n", " \n ").split(" ")
        current = ""
        for word in words:
            if word == "\n":
                if current:
                    lines.append((current, cursor_y))
                    cursor_y += line_height
                    current = ""
                continue
            candidate = word if not current else f"{current} {word}"
            if small_f.size(candidate)[0] <= text_w:
                current = candidate
                continue
            if current:
                lines.append((current, cursor_y))
                cursor_y += line_height
            current = word
        if current:
            lines.append((current, cursor_y))
            cursor_y += line_height
        cursor_y += paragraph_gap  # blank line between paragraphs
    total_height = cursor_y
    max_scroll = max(0, total_height - text_h)
    actual_scroll = min(scroll, max_scroll)

    previous_clip = screen.get_clip()
    screen.set_clip(pygame.Rect(text_x, text_y0, text_w, text_h))
    for line_text, y_off in lines:
        y = text_y0 + (y_off - actual_scroll)
        if y + line_height < text_y0 or y > text_y0 + text_h:
            continue  # outside visible window
        text(screen, small_f, line_text, text_x, y, TEXT, text_w)
    screen.set_clip(previous_clip)

    # Scroll indicator on the right side
    if max_scroll > 0:
        bar_x = content_panel.right - 8
        bar_y = text_y0
        bar_h = text_h
        thumb_h = max(20, int(bar_h * text_h / total_height))
        thumb_y = bar_y + int((bar_h - thumb_h) * actual_scroll / max_scroll)
        pygame.draw.rect(screen, BORDER, pygame.Rect(bar_x, bar_y, 4, bar_h), 1)
        pygame.draw.rect(screen, ACCENT, pygame.Rect(bar_x, thumb_y, 4, thumb_h))

    # Scroll hint under the content
    hint = t(language, "infos_scroll_hint")
    text(screen, tiny_f, hint, content_panel.x + inner_pad,
         content_panel.bottom - 16, MUTED, content_panel.w - inner_pad * 2)

    draw_footer_actions(screen, tiny_f, [("B", t(language, "btn_back"))])
    return max_scroll


def draw_config_menu(screen, fonts, selected, language, theme):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, t(language, "config_title"))

    items = [
        (t(language, "config_language"), t(language, f"lang_{language}")),
        (t(language, "config_theme"), theme_display_name(theme)),
    ]
    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 0)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)
    for idx, (label, value) in enumerate(items):
        y = list_panel.y + 34 + idx * 76
        row = pygame.Rect(list_panel.x + 12, y, list_panel.w - 24, 56)
        color = SCREEN if idx == selected else TEXT
        draw_selectable_list_item(screen, row, idx == selected)
        text(screen, small_f, label, row.x + 9, row.y + 8, color, row.w - 18)
        value_font = tiny_f if idx == 1 else body_f
        text(screen, value_font, value, row.x + 9, row.y + 29, color, row.w - 18)

    text(screen, tiny_f, "< >", list_panel.right - 54, list_panel.y + 12, MUTED)

    preview_panel = right_info_panel(layout, top_offset=30)
    draw_right_panel_frame(screen, preview_panel)
    screen_rect = right_visor_rect(preview_panel)
    config_title = "config"
    if MENU_VISOR_STATE["title"] != config_title:
        MENU_VISOR_STATE["title"] = config_title
        MENU_VISOR_STATE["start_time"] = time.perf_counter()
    visor_elapsed = max(0.0, time.perf_counter() - MENU_VISOR_STATE["start_time"])
    draw_digital_visor(screen, screen_rect, min(visor_elapsed / 1.2, 1.0))
    pygame.draw.rect(screen, BORDER, screen_rect, 2)
    text_center(screen, body_f, t(language, "config_title"), screen_rect, SCREEN_TEXT)
    draw_footer_actions(screen, tiny_f, [
        ("A", t(language, "btn_ok")),
        ("B", t(language, "btn_back")),
        ("<>", t(language, "btn_change")),
    ])


def draw_action_menu(screen, fonts, selected, language="pt"):
    _, _, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, t(language, "action_title"))

    items = [t(language, "action_create_room"), t(language, "action_join_room")]
    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 0)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)
    text(screen, small_f, t(language, "choose"), list_panel.x + 14, list_panel.y + 14, MUTED)

    for idx, item in enumerate(items):
        y = list_panel.y + 46 + idx * 50
        row = pygame.Rect(list_panel.x + 10, y, list_panel.w - 20, 40)
        color = SCREEN if idx == selected else TEXT
        draw_selectable_list_item(screen, row, idx == selected)
        text(screen, small_f, item, row.x + 9, row.y + 9, color, row.w - 18)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))])


def keyboard_chars(shift=False):
    base = "`1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./"
    shifted = '~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:"ZXCVBNM<>?'
    return list(shifted if shift else base)


def keyboard_limits(shift=False):
    total = len(keyboard_chars(shift)) + 4
    return total - 1


def random_room_name():
    return f"{random.choice(POKEMON_ROOM_NAMES).lower()}{random.randint(10, 99)}"


def draw_keyboard(screen, fonts, title, value, grid_index, is_password=False, shift=False, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, title)
    display_panel = layout.left_panel
    key_panel = right_info_panel(layout)
    shift_label = t(language, "shift_on" if shift else "shift_off")

    display_value = "*" * len(value) if is_password else value
    rect(screen, PANEL, display_panel, 0)
    pygame.draw.rect(screen, BORDER, display_panel, 2, border_radius=0)
    screen_rect = pygame.Rect(display_panel.x + 18, display_panel.y + 30, display_panel.w - 36, 92)
    rect(screen, SCREEN, screen_rect, 0)
    pygame.draw.rect(screen, BORDER, screen_rect, 2, border_radius=0)
    text(screen, tiny_f, title, screen_rect.x + 12, screen_rect.y + 10, (142, 189, 224), screen_rect.w - 24)
    value_area = pygame.Rect(screen_rect.x + 12, screen_rect.y + 38, screen_rect.w - 24, 34)
    text(screen, body_f, display_value if display_value else t(language, "empty"), value_area.x, value_area.y, SCREEN_TEXT, value_area.w)
    text(screen, tiny_f, shift_label, display_panel.x + 18, screen_rect.bottom + 18, MUTED, display_panel.w - 36)
    pygame.draw.circle(screen, ACCENT if shift else MUTED, (display_panel.x + 30, screen_rect.bottom + 56), 8)
    pygame.draw.circle(screen, WARN, (display_panel.x + 58, screen_rect.bottom + 56), 8)
    rect(screen, SCREEN, pygame.Rect(display_panel.x + 86, screen_rect.bottom + 48, display_panel.w - 124, 16), 0)

    chars = keyboard_chars(shift)
    rect(screen, PANEL, key_panel, 0)
    pygame.draw.rect(screen, BORDER, key_panel, 2, border_radius=0)
    top_display = pygame.Rect(key_panel.x + 18, key_panel.y + 18, key_panel.w - 36, 34)
    rect(screen, SCREEN, top_display, 0)
    text(screen, tiny_f, t(language, "keypad"), top_display.x + 10, top_display.y + 9, SCREEN_TEXT, top_display.w - 20)

    margin_x = key_panel.x + 12
    grid_pitch = (key_panel.w - 24) // KEYBOARD_GRID_W
    key_w = max(16, grid_pitch - 3)
    key_h = 25
    key_font = font(11, True)
    special_font = font(10, True)
    start_x = margin_x + (key_panel.w - 24 - grid_pitch * KEYBOARD_GRID_W) // 2
    start_y = key_panel.y + 66
    rows_used = math.ceil(len(chars) / KEYBOARD_GRID_W)

    for idx, char in enumerate(chars):
        col, row = idx % KEYBOARD_GRID_W, idx // KEYBOARD_GRID_W
        row_chars = min(KEYBOARD_GRID_W, len(chars) - row * KEYBOARD_GRID_W)
        row_offset = (KEYBOARD_GRID_W - row_chars) * grid_pitch // 2
        x = start_x + row_offset + col * grid_pitch
        y = start_y + row * (key_h + 4)
        selected = idx == grid_index
        key_rect = pygame.Rect(x, y, key_w, key_h)
        rect(screen, ACCENT if selected else PANEL_2, key_rect, 0)
        pygame.draw.rect(screen, BORDER, key_rect, 1, border_radius=0)
        char_surface = key_font.render(char, True, SCREEN if selected else TEXT)
        screen.blit(char_surface, char_surface.get_rect(center=key_rect.center))

    special_start = len(chars)
    specials = [("DEL", special_start), ("SHIFT", special_start + 1), ("SPACE", special_start + 2), ("OK", special_start + 3)]
    specials_y = start_y + rows_used * (key_h + 4) + 10
    special_total_w = key_panel.w - 24
    special_w = (special_total_w - 3 * 10) // 4
    for offset, (label, idx) in enumerate(specials):
        x = margin_x + offset * (special_w + 10)
        selected = idx == grid_index
        key_rect = pygame.Rect(x, specials_y, special_w, key_h + 4)
        rect(screen, ACCENT if selected else PANEL_2, key_rect, 0)
        pygame.draw.rect(screen, BORDER, key_rect, 1, border_radius=0)
        label_surface = special_font.render(label, True, SCREEN if selected else TEXT)
        screen.blit(label_surface, label_surface.get_rect(center=key_rect.center))

    draw_footer_actions(screen, tiny_f, [("A", t(language, "key_select")), ("B", t(language, "key_delete_back"))])


def draw_select_save(screen, fonts, selected, saves, title=None, language="pt", state=None, is_loading=1.0):
    _, body_f, small_f, tiny_f = fonts
    progress = is_loading if isinstance(is_loading, (int, float)) else 1.0
    layout = draw_pokedex_shell(screen, title or screen_title(language, "select_save"), loading_progress=progress, pulsing=False)
    list_panel = layout.left_panel
    detail_panel = right_info_panel(layout)

    rect(screen, PANEL, list_panel, 0)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)
    draw_right_panel_frame(screen, detail_panel)

    if not saves:
        message_screen = pygame.Rect(list_panel.x + 18, list_panel.y + 34, list_panel.w - 36, 120)
        rect(screen, SCREEN, message_screen, 0)
        pygame.draw.rect(screen, BORDER, message_screen, 2, border_radius=0)
        wrap_text(screen, small_f, t(language, "no_saves"), pygame.Rect(message_screen.x + 16, message_screen.y + 44, message_screen.w - 32, 40), SCREEN_TEXT, max_lines=2)
        wrap_text(screen, small_f, t(language, "save_pick_hint"), pygame.Rect(detail_panel.x + 18, detail_panel.y + 38, detail_panel.w - 36, 80), MUTED, max_lines=3)
        draw_footer_actions(screen, tiny_f, [("B", t(language, "btn_back"))])
        return

    visible = 6
    row_h = 42
    scroll = list_scroll_offset("saves", selected, len(saves), visible)
    first = max(0, int(scroll) - 1)
    last = min(len(saves), int(scroll) + visible + 2)
    previous_clip = screen.get_clip()
    screen.set_clip(list_panel.inflate(-8, -8))
    for idx in range(first, last):
        save_path = saves[idx]
        y = list_panel.y + 14 + int((idx - scroll) * row_h)
        row = pygame.Rect(list_panel.x + 10, y, list_panel.w - 20, 36)
        color = SCREEN if idx == selected else TEXT
        draw_selectable_list_item(screen, row, idx == selected)
        wrap_text(screen, tiny_f, save_path.name, pygame.Rect(row.x + 9, row.y + 4, row.w - 18, row.h - 6), color, line_gap=0, max_lines=2)
    screen.set_clip(previous_clip)
    LIST_SCROLLBAR.draw(screen, scroll, len(saves), visible)

    selected_save = saves[selected] if 0 <= selected < len(saves) else saves[0]
    screen_rect = right_visor_rect(detail_panel)
    selected_title = f"select_save:{selected_save.name}"
    if SELECT_SAVE_VISOR_STATE["title"] != selected_title:
        SELECT_SAVE_VISOR_STATE["title"] = selected_title
        SELECT_SAVE_VISOR_STATE["start_time"] = time.perf_counter()
    visor_elapsed = max(0.0, time.perf_counter() - SELECT_SAVE_VISOR_STATE["start_time"])
    draw_digital_visor(screen, screen_rect, min(visor_elapsed / 1.2, 1.0))
    pygame.draw.rect(screen, BORDER, screen_rect, 2)

    generation_text = ""
    pokemon_count = 0
    badges_mask = 0
    game_id = ""
    player_name = ""
    trainer_id = 0
    analysis_loading = False
    if state:
        try:
            key = str(selected_save.resolve())
            analysis = state.save_analysis.get(key)
            if analysis is None:
                analysis_loading = True
            if analysis:
                gen = analysis.get("generation", 0)
                generation_text = f"Gen {gen}" if gen else ""
                party_count = analysis.get("party_count", 0)
                box_count = analysis.get("box_count", 0)
                pokemon_count = party_count + box_count
                badges_mask = int(analysis.get("badges_mask") or 0)
                game_id = analysis.get("game") or ""
                player_name = analysis.get("player_name") or ""
                trainer_id = int(analysis.get("trainer_id") or 0)
        except Exception:
            pass

    header_y = screen_rect.y + 8
    if analysis_loading:
        text(screen, small_f, t(language, "analyzing"), screen_rect.x + 12, header_y + 20, (100, 100, 100), screen_rect.w - 24)
    elif player_name or trainer_id:
        name_label = player_name or "—"
        name_surface = body_f.render(name_label, True, (0, 0, 0))
        screen.blit(name_surface, (screen_rect.x + 12, header_y))
        if trainer_id:
            tid_text = f"#{trainer_id:05d}"
            tid_surface = tiny_f.render(tid_text, True, (0, 0, 0))
            tid_rect = tid_surface.get_rect()
            tid_rect.right = screen_rect.right - 12
            tid_rect.y = header_y + 4
            screen.blit(tid_surface, tid_rect)
        text(screen, body_f, generation_text, screen_rect.x + 12, header_y + 22, (0, 0, 0), screen_rect.w - 24)
        text(screen, body_f, f"{pokemon_count} Pokémon", screen_rect.x + 12, header_y + 42, (0, 0, 0), screen_rect.w - 24)
    if game_id:
        from frontend.components.badges import draw_badge_strip, badge_slots_for
        slots = badge_slots_for(game_id)
        if slots:
            badge_size = 16
            spacing = max(2, (screen_rect.w - 24 - badge_size * len(slots)) // max(1, len(slots) - 1))
            spacing = min(spacing, 6)
            draw_badge_strip(
                screen,
                (screen_rect.x + 12, screen_rect.bottom - badge_size - 8),
                game_id,
                badges_mask,
                size=badge_size,
                spacing=spacing,
            )

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))])


def draw_select_pokemon(screen, fonts, selected, pokemon_list, source_label, sprite_loader, status="", allow_pc_actions=True, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "choose_pokemon"))

    if not pokemon_list:
        list_panel = layout.left_panel
        detail_panel = right_info_panel(layout)
        rect(screen, PANEL, list_panel, 0)
        pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)
        draw_right_panel_frame(screen, detail_panel)
        message_screen = pygame.Rect(list_panel.x + 18, list_panel.y + 34, list_panel.w - 36, 120)
        rect(screen, SCREEN, message_screen, 0)
        pygame.draw.rect(screen, BORDER, message_screen, 2, border_radius=0)
        wrap_text(screen, small_f, t(language, "no_pokemon"), pygame.Rect(message_screen.x + 16, message_screen.y + 42, message_screen.w - 32, 44), SCREEN_TEXT, max_lines=2)
        text(screen, small_f, source_label, detail_panel.x + 18, detail_panel.y + 38, MUTED, detail_panel.w - 36)
        draw_footer_actions(screen, tiny_f, [("B", t(language, "btn_back"))])
        return

    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 0)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)

    content_pad_left = 4
    content_pad_top = 4
    content_pad_right = 4
    content_pad_bottom = 2
    content = pygame.Rect(
        list_panel.x + content_pad_left,
        list_panel.y + content_pad_top,
        list_panel.w - (content_pad_left + content_pad_right),
        list_panel.h - (content_pad_top + content_pad_bottom),
    )
    card_min_pitch = 53
    card_gap = 2
    card_pitch = max(card_min_pitch, content.h // ROW_VISIBLE)
    card_h = card_pitch - card_gap
    sprite_size = 52
    sprite_pad_left = 8
    text_gap = 10
    text_pad_right = 12
    title_y_offset = 4
    level_y_offset = 19
    item_y_offset = 32
    name_font = font(13)
    meta_font = font(11)

    scroll = list_scroll_offset("pokemon", selected, len(pokemon_list))
    first = max(0, int(scroll) - 1)
    last = min(len(pokemon_list), int(scroll) + ROW_VISIBLE + 2)
    previous_clip = screen.get_clip()
    screen.set_clip(content)
    for idx in range(first, last):
        pokemon = pokemon_list[idx]
        y = content.y + int((idx - scroll) * card_pitch)
        row = pygame.Rect(content.x, y, content.w, card_h)
        color = SCREEN if idx == selected else TEXT
        draw_selectable_list_item(screen, row, idx == selected)
        sprite_loader.request_for(pokemon)
        sprite, loading, _ = sprite_loader.snapshot_for(pokemon)
        sprite_slot = pygame.Rect(row.x + sprite_pad_left, row.y + (row.h - sprite_size) // 2, sprite_size, sprite_size)
        if sprite:
            scaled = pygame.transform.smoothscale(sprite, (sprite_size, sprite_size))
            screen.blit(scaled, sprite_slot.topleft)
        elif loading:
            text_center(screen, meta_font, "...", sprite_slot, MUTED)
        text_x = sprite_slot.right + text_gap
        text_w = row.right - text_x - text_pad_right
        title_area = pygame.Rect(text_x, row.y + title_y_offset, text_w, 14)
        level_area = pygame.Rect(text_x, row.y + level_y_offset, text_w, 12)
        item_area = pygame.Rect(text_x, row.y + item_y_offset, text_w, 12)
        level = int(pokemon.get("level") or 0)
        text(screen, name_font, pokemon_display_name(pokemon, f"Pokemon {idx + 1}"), title_area.x, title_area.y, color, title_area.w)
        text(screen, meta_font, t(language, "level_tag", level=level), level_area.x, level_area.y, color if idx == selected else MUTED, level_area.w)
        item_info = held_item_info(pokemon)
        item_name = item_info["name"] if item_info else t(language, "item_none")
        item_text = t(language, "item_label", name=item_name)
        text(screen, meta_font, item_text, item_area.x, item_area.y, color if idx == selected else MUTED, item_area.w)
    screen.set_clip(previous_clip)
    LIST_SCROLLBAR.draw(screen, scroll, len(pokemon_list), ROW_VISIBLE)

    selected_pokemon = pokemon_list[selected] if 0 <= selected < len(pokemon_list) else None
    sprite_loader.request(selected_pokemon)
    detail_panel = right_info_panel(layout)
    draw_right_panel_frame(screen, detail_panel)

    if selected_pokemon:
        sprite, loading, error = sprite_loader.snapshot()
        display_name = pokemon_display_name(selected_pokemon, "Pokemon")
        draw_pokemon_detail_component(screen, fonts, detail_panel, selected_pokemon, display_name, sprite, loading, language)
        if error and DEBUG:
            text(screen, tiny_f, error[:40], detail_panel.x + 14, detail_panel.bottom - 30, WARN, detail_panel.w - 28)
    else:
        text(screen, small_f, source_label, detail_panel.x + 16, detail_panel.y + 122, MUTED, detail_panel.w - 32)

    actions = [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))]
    if allow_pc_actions:
        is_party = "party" in (source_label or "").lower()
        x_label = t(language, "btn_move_pc") if is_party else t(language, "btn_withdraw")
        y_label = t(language, "btn_view_pc") if is_party else t(language, "btn_view_party")
        actions.extend([("X", x_label), ("Y", y_label)])
    draw_footer_actions(screen, tiny_f, actions)


def draw_connecting(screen, fonts, frame, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "connecting"), pulsing=True)
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)

    rect(screen, PANEL, left_panel, 0)
    rect(screen, PANEL_2, right_panel, 0)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=0)

    dots = "." * ((frame // 15) % 4)
    message = t(language, "connecting_server", dots=dots)
    visor_rect = right_visor_rect(right_panel)

    draw_digital_visor(screen, visor_rect, 1.0)
    pygame.draw.rect(screen, BORDER, visor_rect, 2)
    wrap_text(screen, body_f, message, pygame.Rect(visor_rect.x + 12, visor_rect.y + 35, visor_rect.w - 24, 60), (0, 0, 0), line_gap=1, max_lines=3)

    import time
    if not hasattr(draw_connecting, '_pulse_start'):
        draw_connecting._pulse_start = time.perf_counter()
    pulse_elapsed = time.perf_counter() - draw_connecting._pulse_start
    pulse_duration = 0.9
    if pulse_elapsed <= pulse_duration:
        from frontend.components.primitives import draw_lens_pulse
        draw_lens_pulse(screen, (49, 47), pulse_elapsed / pulse_duration)
    else:
        draw_connecting._pulse_start = time.perf_counter()

    draw_footer_actions(screen, tiny_f, [("B", t(language, "btn_cancel"))])


def draw_waiting_partner(screen, fonts, status, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "waiting_partner"), pulsing=True)
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)

    rect(screen, PANEL, left_panel, 0)
    rect(screen, PANEL_2, right_panel, 0)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=0)

    message = translate_literal(language, status) if status else t(language, "waiting_partner")
    visor_rect = right_visor_rect(right_panel)

    draw_digital_visor(screen, visor_rect, 1.0)
    pygame.draw.rect(screen, BORDER, visor_rect, 2)
    wrap_text(screen, body_f, message, pygame.Rect(visor_rect.x + 12, visor_rect.y + 35, visor_rect.w - 24, 60), (0, 0, 0), line_gap=1, max_lines=3)

    import time
    if not hasattr(draw_waiting_partner, '_pulse_start'):
        draw_waiting_partner._pulse_start = time.perf_counter()
    pulse_elapsed = time.perf_counter() - draw_waiting_partner._pulse_start
    pulse_duration = 0.9
    if pulse_elapsed <= pulse_duration:
        from frontend.components.primitives import draw_lens_pulse
        draw_lens_pulse(screen, (49, 47), pulse_elapsed / pulse_duration)
    else:
        draw_waiting_partner._pulse_start = time.perf_counter()

    draw_footer_actions(screen, tiny_f, [("X", t(language, "btn_enter_ip")), ("B", t(language, "btn_cancel"))])


def draw_pokedex_prompt(screen, fonts, title, question, detail_lines, actions, language="pt", tone=WARN):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, title)
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 0)
    rect(screen, PANEL_2, right_panel, 0)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=0)

    status_screen = pygame.Rect(left_panel.x + 18, left_panel.y + 32, left_panel.w - 36, 132)
    rect(screen, SCREEN, status_screen, 0)
    pygame.draw.rect(screen, BORDER, status_screen, 2, border_radius=0)
    wrap_text(screen, body_f, question, pygame.Rect(status_screen.x + 16, status_screen.y + 28, status_screen.w - 32, status_screen.h - 56), SCREEN_TEXT, max_lines=3)
    for idx, color in enumerate((tone, WARN, OK)):
        pygame.draw.circle(screen, BORDER, (left_panel.x + 74 + idx * 52, status_screen.bottom + 46), 12)
        pygame.draw.circle(screen, color, (left_panel.x + 74 + idx * 52, status_screen.bottom + 46), 8)

    y = right_panel.y + 26
    for line in detail_lines:
        area = pygame.Rect(right_panel.x + 18, y, right_panel.w - 36, 54)
        wrap_text(screen, small_f, line, area, TEXT if y == right_panel.y + 26 else MUTED, max_lines=2)
        y += 62
    draw_footer_actions(screen, tiny_f, actions)


def draw_leave_room_confirm(screen, fonts, language="pt"):
    draw_pokedex_prompt(
        screen,
        fonts,
        screen_title(language, "leave_room_title"),
        t(language, "leave_room_question"),
        [t(language, "leave_room_help"), t(language, "leave_room_more")],
        [("A", t(language, "btn_yes")), ("B", t(language, "btn_no"))],
        language,
        RED,
    )


def draw_deposit_confirm(screen, fonts, pokemon, sprite_loader, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "deposit_title"), warn_pulse=True)
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 0)
    rect(screen, PANEL_2, right_panel, 0)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=0)

    name = pokemon_display_name(pokemon)
    msg = t(language, "deposit_question", name=name)
    text_area = pygame.Rect(left_panel.x + 18, left_panel.y + 22, left_panel.w - 36, 68)
    wrap_text(screen, body_f, msg, text_area, TEXT, line_gap=2)

    level = (pokemon or {}).get("level")
    details = []
    if level:
        details.append(t(language, "level_short", level=level))
    details.append(t(language, "deposit_help"))
    details.append(t(language, "backup_help"))
    details_area = pygame.Rect(left_panel.x + 18, text_area.bottom + 12, left_panel.w - 36, left_panel.h - (text_area.bottom - left_panel.y) - 30)
    detail_y = details_area.y
    for index, detail in enumerate(details):
        font_obj = small_f if index == 0 and level else tiny_f
        color = TEXT if index == 0 and level else MUTED
        line_area = pygame.Rect(details_area.x, detail_y, details_area.w, details_area.bottom - detail_y)
        next_y = wrap_text(screen, font_obj, detail, line_area, color, line_gap=2)
        detail_y = next_y + 8

    entry = _build_sprite_entry(pokemon)
    sprite_loader.request_for(entry)
    sprite, loading, _ = sprite_loader.snapshot_for(entry)
    display_name = pokemon_display_name(pokemon, "Pokemon")
    draw_pokemon_detail_component(screen, fonts, right_panel, pokemon, display_name, sprite, loading, language)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_yes")), ("B", t(language, "btn_no"))])


def draw_withdraw_confirm(screen, fonts, pokemon, language="pt"):
    name = pokemon_display_name(pokemon)
    box_name = (pokemon or {}).get("box_name") or ""
    details = [t(language, "withdraw_from", box=box_name)] if box_name else []
    details.extend([t(language, "withdraw_help"), t(language, "backup_help")])
    draw_pokedex_prompt(
        screen,
        fonts,
        screen_title(language, "withdraw_title"),
        t(language, "withdraw_question", name=name),
        details,
        [("A", t(language, "btn_yes")), ("B", t(language, "btn_no"))],
        language,
        ACCENT,
    )


def draw_info_modal(screen, fonts, title, message, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    display_title = translate_literal(language, title) if title else t(language, "notice")
    layout = draw_pokedex_shell(screen, display_title or screen_title(language, "notice"))
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 0)
    rect(screen, PANEL_2, right_panel, 0)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=0)

    text_area = pygame.Rect(left_panel.x + 18, left_panel.y + 24, left_panel.w - 36, left_panel.h - 48)
    wrap_text(screen, body_f, display_title, text_area, TEXT, max_lines=2)
    wrap_text(screen, small_f, translate_literal(language, (message or "").strip()) or t(language, "no_details"), pygame.Rect(text_area.x, text_area.y + 40, text_area.w, text_area.h - 40), MUTED, max_lines=6)

    visor_rect = right_visor_rect(right_panel)
    draw_digital_visor(screen, visor_rect, 1.0)
    pygame.draw.rect(screen, BORDER, visor_rect, 2, border_radius=0)
    body_msg = translate_literal(language, (message or "").strip()) or t(language, "no_details")
    wrap_text(screen, small_f, body_msg, pygame.Rect(visor_rect.x + 10, visor_rect.y + 10, visor_rect.w - 20, visor_rect.h - 20), (0, 0, 0), max_lines=5)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok"))])


def draw_resolve_moves(screen, fonts, removed_move, replacement_index, current_idx, total, chosen_ids=None, sprite_loader=None, pokemon=None, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "incompatible_move_title", current=current_idx + 1, total=total), warn_pulse=True)

    list_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, list_panel, 0)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)
    draw_right_panel_frame(screen, right_panel)

    chosen_set = set(int(x) for x in (chosen_ids or []) if x)
    replacements = [
        r for r in (removed_move.get("valid_replacements") or [])
        if int(r.get("move_id") or 0) not in chosen_set
    ]
    options = replacements + [{"move_id": 0, "name": t(language, "empty_move")}]

    visible = 8
    row_h = 34
    scroll = list_scroll_offset(f"resolve_moves_{current_idx}", replacement_index, len(options), visible)
    first = max(0, int(scroll) - 1)
    last = min(len(options), int(scroll) + visible + 2)
    previous_clip = screen.get_clip()
    screen.set_clip(list_panel.inflate(-4, -8))
    for idx in range(first, last):
        option = options[idx]
        y = list_panel.y + 6 + int((idx - scroll) * row_h)
        row = pygame.Rect(list_panel.x + 4, y, list_panel.w - 8, 30)
        selected = idx == replacement_index
        draw_selectable_list_item(screen, row, selected)
        label = option.get("name") or local_move_name(option.get("move_id", 0))
        if is_move_number_label(label):
            label = local_move_name(option.get("move_id", 0))
        try:
            learn_level = int(option.get("learn_level") or 0)
        except (TypeError, ValueError):
            learn_level = 0
        color = SCREEN if selected else TEXT
        move_type = option.get("type", "")
        badge_w = 68
        right_margin = 8
        type_badge_w = badge_w + right_margin + 4 if move_type and move_type in TYPE_COLORS else 0
        prefix_text = ""
        prefix_w = 0
        if int(option.get("move_id") or 0) > 0 and learn_level > 0:
            prefix_text = f"Nv.{learn_level}"
            prefix_w = tiny_f.size(prefix_text)[0] + 6
            text(screen, tiny_f, prefix_text, row.x + 10, row.y + 9, color)
        name_x = row.x + 10 + prefix_w
        name_max_w = row.w - 20 - type_badge_w - prefix_w
        text(screen, small_f, label, name_x, row.y + 7, color, name_max_w)
        if move_type and move_type in TYPE_COLORS:
            tint = TYPE_COLORS[move_type]
            badge = pygame.Rect(row.right - badge_w - right_margin, row.y + 6, badge_w, 18)
            rect(screen, tint, badge, 0)
            pygame.draw.rect(screen, BORDER, badge, 1)
            lbl_surf = font(9).render(type_label(move_type, language), True, (255, 255, 255))
            screen.blit(lbl_surf, lbl_surf.get_rect(center=badge.center))
    screen.set_clip(previous_clip)
    LIST_SCROLLBAR.draw(screen, scroll, len(options), visible)

    # visor com dados do pokemon à direita
    if sprite_loader and pokemon:
        entry = _build_sprite_entry(pokemon)
        sprite_loader.request_for(entry)
        sprite, loading, _ = sprite_loader.snapshot_for(entry)
        display_name = pokemon_display_name(pokemon, "Pokemon")
        draw_pokemon_detail_component(screen, fonts, right_panel, pokemon, display_name, sprite, loading, language)

        # sobrescreve o box de movimentos com oscilação no slot que precisa trocar
        move_name_text = removed_move.get("name") or local_move_name(removed_move.get("move_id", 0))
        if is_move_number_label(move_name_text):
            move_name_text = local_move_name(removed_move.get("move_id", 0))
        pulse = 0.5 + 0.5 * math.sin(time.perf_counter() * 3.0)
        pulse_border_color = (255, int(100 * pulse), int(100 * pulse))

        side_pad = 12
        visor_y = right_panel.y + 16 + 100 + 8
        summary_panel = pygame.Rect(right_panel.x + side_pad, visor_y, right_panel.w - side_pad * 2, right_panel.bottom - visor_y - 8)
        move_entries = move_display_entries(pokemon)
        move_id_to_replace = int(removed_move.get("move_id") or 0)
        if move_entries and summary_panel.h > 0:
            moves_panel = pygame.Rect(summary_panel.x + 8, summary_panel.y + 50, summary_panel.w - 16, summary_panel.h - 58)
            move_f = font(11)
            for move_idx, move_entry in enumerate(move_entries[:4]):
                move_y = moves_panel.y + 20 + move_idx * 20
                move_rect = pygame.Rect(moves_panel.x, move_y, moves_panel.w, 16)
                is_target = int(move_entry.get("move_id") or 0) == move_id_to_replace
                # Fundo normal, apenas borda oscila
                rect(screen, BG, move_rect, 0)
                border_color = pulse_border_color if is_target else BORDER
                border_width = 2 if is_target else 1
                pygame.draw.rect(screen, border_color, move_rect, border_width, border_radius=0)
                name_area = pygame.Rect(move_rect.x + 6, move_rect.y + 1, move_rect.w - 60, 14)
                text(screen, move_f, move_entry["name"], name_area.x, name_area.y, TEXT, name_area.w)
                pp_text = f"{move_entry['pp']}/{move_entry['max_pp']}" if move_entry.get("max_pp") else str(move_entry["pp"])
                pp_area = pygame.Rect(move_rect.right - 52, move_rect.y + 1, 48, 14)
                pp_surface = tiny_f.render(pp_text, True, MUTED)
                screen.blit(pp_surface, pp_surface.get_rect(midright=pp_area.midright))
    else:
        move_name_text = removed_move.get("name") or local_move_name(removed_move.get("move_id", 0))
        if is_move_number_label(move_name_text):
            move_name_text = local_move_name(removed_move.get("move_id", 0))
        visor_rect = right_visor_rect(right_panel)
        draw_digital_visor(screen, visor_rect, 1.0)
        pygame.draw.rect(screen, BORDER, visor_rect, 2, border_radius=0)
        wrap_text(screen, body_f, t(language, "unsupported_move", move=move_name_text), pygame.Rect(visor_rect.x + 10, visor_rect.y + 10, visor_rect.w - 20, 60), (0, 0, 0), max_lines=3)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_choose")), ("B", t(language, "btn_skip"))])


def draw_resolve_item_relocation(screen, fonts, item_relocation, selected_index, sprite_loader=None, pokemon=None, language="pt"):
    _, _, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "incompatible_item_title"), warn_pulse=True)

    list_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, list_panel, 0)
    rect(screen, PANEL_2, right_panel, 0)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=0)

    options = [str(option) for option in (item_relocation.get("options") or []) if str(option)]
    labels = {
        "bag": t(language, "item_destination_bag"),
        "pc": t(language, "item_destination_pc"),
        "remove": t(language, "item_destination_remove"),
    }
    for idx, option in enumerate(options):
        row = pygame.Rect(list_panel.x + 8, list_panel.y + 14 + idx * 38, list_panel.w - 16, 30)
        selected = idx == selected_index
        draw_selectable_list_item(screen, row, selected)
        color = SCREEN if selected else TEXT
        text(screen, small_f, labels.get(option, option.upper()), row.x + 10, row.y + 7, color, row.w - 20)

    if sprite_loader and pokemon:
        entry = _build_sprite_entry(pokemon)
        sprite_loader.request_for(entry)
        sprite, loading, _ = sprite_loader.snapshot_for(entry)
        display_name = pokemon_display_name(pokemon, "Pokemon")
        draw_pokemon_detail_component(screen, fonts, right_panel, pokemon, display_name, sprite, loading, language)
    else:
        visor_rect = right_visor_rect(right_panel)
        draw_digital_visor(screen, visor_rect, 1.0)
        pygame.draw.rect(screen, BORDER, visor_rect, 2, border_radius=0)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_store_item")), ("B", t(language, "btn_back"))])


def draw_cancel_waiting_confirm(screen, fonts, pokemon, sprite_loader, language="pt"):
    title_f, body_f, small_f, tiny_f = fonts
    del title_f
    layout = draw_pokedex_shell(screen, screen_title(language, "cancel_trade_title"))

    pokemon_name = pokemon_display_name(pokemon, "???")

    pokemon_entry = dict(pokemon or {})
    pokemon_entry.setdefault("generation", int(pokemon.get("generation") or 0))
    pokemon_entry.setdefault("species_id", int(pokemon.get("species_id") or 0))
    pokemon_entry.setdefault("species_name", pokemon.get("species_name") or "Pokemon")
    sprite_loader.request_for(pokemon_entry)
    pokemon_sprite, pokemon_loading, _ = sprite_loader.snapshot_for(pokemon_entry)

    left_card = layout.left_panel
    right_card = right_info_panel(layout)
    rect(screen, PANEL, left_card, 0)
    rect(screen, PANEL_2, right_card, 0)
    pygame.draw.rect(screen, BORDER, left_card, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_card, 2, border_radius=0)

    draw_confirm_pokemon_visor(screen, fonts, left_card, pokemon, pokemon_name, pokemon_sprite, pokemon_loading, language)

    visor_rect = right_visor_rect(right_card)
    draw_digital_visor(screen, visor_rect, 1.0)
    pygame.draw.rect(screen, BORDER, visor_rect, 2)

    y = visor_rect.y + 20
    wrap_text(screen, small_f, t(language, "cancel_trade_question"),
              pygame.Rect(visor_rect.x + 8, y, visor_rect.w - 16, 40), (0, 0, 0), line_gap=1, max_lines=2)

    y = visor_rect.y + 65
    wrap_text(screen, tiny_f, t(language, "save_not_modified"),
              pygame.Rect(visor_rect.x + 8, y, visor_rect.w - 16, 15), (0, 0, 0))
    y += 18
    wrap_text(screen, tiny_f, t(language, "room_stays_open"),
              pygame.Rect(visor_rect.x + 8, y, visor_rect.w - 16, 15), (0, 0, 0))

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_yes")), ("B", t(language, "btn_no"))])


def draw_confirm_pokemon_visor(screen, fonts, panel_area, pokemon, display_name, sprite, loading, language="pt"):
    draw_pokemon_detail_component(screen, fonts, panel_area, pokemon, display_name, sprite, loading, language)


def draw_trade_confirm(screen, fonts, my_pokemon, opponent_pokemon, sprite_loader, language="pt"):
    title_f, body_f, small_f, tiny_f = fonts
    del title_f
    layout = draw_pokedex_shell(screen, screen_title(language, "confirm_trade"))

    mine = pokemon_display_name(my_pokemon, "???")
    peer = pokemon_display_name(opponent_pokemon, "???")

    my_entry = dict(my_pokemon or {})
    my_entry.setdefault("generation", int(my_pokemon.get("generation") or 0))
    my_entry.setdefault("species_id", int(my_pokemon.get("species_id") or 0))
    my_entry.setdefault("species_name", my_pokemon.get("species_name") or "Pokemon")
    peer_entry = dict(opponent_pokemon or {})
    canonical = opponent_pokemon.get("canonical") if isinstance(opponent_pokemon, dict) else {}
    canonical = canonical if isinstance(canonical, dict) else {}
    species_block = canonical.get("species") if isinstance(canonical.get("species"), dict) else {}
    peer_ndex = int(
        opponent_pokemon.get("national_dex_id")
        or canonical.get("species_national_id")
        or species_block.get("national_dex_id")
        or 0
    )
    peer_entry["national_dex_id"] = peer_ndex
    peer_entry.setdefault("generation", int(opponent_pokemon.get("generation") or canonical.get("source_generation") or opponent_pokemon.get("source_generation") or 0))
    peer_entry.setdefault("species_id", int(opponent_pokemon.get("species_id") or 0))
    peer_entry.setdefault("species_name", opponent_pokemon.get("species_name") or canonical.get("species_name") or species_block.get("name") or "Pokemon")
    sprite_loader.request_for(my_entry)
    sprite_loader.request_for(peer_entry)
    my_sprite, my_loading, _ = sprite_loader.snapshot_for(my_entry)
    peer_sprite, peer_loading, _ = sprite_loader.snapshot_for(peer_entry)

    left_card = layout.left_panel
    right_card = right_info_panel(layout)
    rect(screen, PANEL, left_card, 0)
    rect(screen, PANEL, right_card, 0)
    pygame.draw.rect(screen, BORDER, left_card, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_card, 2, border_radius=0)

    draw_confirm_pokemon_visor(screen, fonts, left_card, my_pokemon, mine, my_sprite, my_loading, language)
    draw_confirm_pokemon_visor(screen, fonts, right_card, opponent_pokemon, peer, peer_sprite, peer_loading, language)

    arrow_y = left_card.y + 146
    pulse = math.sin(time.perf_counter() * 4.0)
    dx_anim = int(pulse * 4)
    cx = SCREEN_W // 2

    circle_radius_outer = 17
    circle_radius_inner = 13

    pygame.draw.circle(screen, BORDER, (cx, arrow_y - 13), circle_radius_outer)
    pygame.draw.circle(screen, ACCENT, (cx, arrow_y - 13), circle_radius_inner)
    pygame.draw.polygon(screen, SCREEN, [
        (cx - 7 + dx_anim, arrow_y - 18),
        (cx + 7 + dx_anim, arrow_y - 18),
        (cx + 7 + dx_anim, arrow_y - 21),
        (cx + 13 + dx_anim, arrow_y - 13),
        (cx + 7 + dx_anim, arrow_y - 5),
        (cx + 7 + dx_anim, arrow_y - 8),
        (cx - 7 + dx_anim, arrow_y - 8),
    ])

    pygame.draw.circle(screen, BORDER, (cx, arrow_y + 23), circle_radius_outer)
    pygame.draw.circle(screen, ACCENT, (cx, arrow_y + 23), circle_radius_inner)
    pygame.draw.polygon(screen, SCREEN, [
        (cx + 7 - dx_anim, arrow_y + 18),
        (cx - 7 - dx_anim, arrow_y + 18),
        (cx - 7 - dx_anim, arrow_y + 15),
        (cx - 13 - dx_anim, arrow_y + 23),
        (cx - 7 - dx_anim, arrow_y + 31),
        (cx - 7 - dx_anim, arrow_y + 28),
        (cx + 7 - dx_anim, arrow_y + 28),
    ])

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_confirm")), ("B", t(language, "btn_cancel"))])


def evolution_sprite_entry(evolution, side):
    generation = int(evolution.get("generation") or 0)
    species_id = int(evolution.get(f"{side}_species_id") or 0)
    explicit_ndex = int(evolution.get(f"{side}_national_id") or evolution.get(f"{side}_national_dex_id") or 0)
    national_dex_id = explicit_ndex
    if not national_dex_id and species_id:
        if generation == 2:
            national_dex_id = species_id
        else:
            try:
                _ensure_backend_import_path()
                from data.species import native_to_national
                national_dex_id = int(native_to_national(generation, species_id) or 0)
            except Exception as exc:
                logger.debug("evolution_sprite_entry national lookup failed: %s", exc)
                national_dex_id = 0
    return {
        "generation": generation,
        "species_id": species_id,
        "species_name": evolution.get(f"{side}_name") or "Pokemon",
        "national_dex_id": national_dex_id,
    }


def evolution_types(evolution, side):
    sprite_entry = evolution_sprite_entry(evolution, side)
    national_dex_id = sprite_entry.get("national_dex_id", 0)
    if national_dex_id:
        try:
            _ensure_backend_import_path()
            from data.base_stats import BASE_STATS
            types = (BASE_STATS.get(int(national_dex_id)) or {}).get("types") or []
            return [str(t).lower() for t in types if t]
        except Exception:
            pass
    return []


def draw_scaled_sprite(surface, sprite, center, size, alpha=255):
    if not sprite:
        return
    scaled = pygame.transform.smoothscale(sprite, (size, size)).convert_alpha()
    scaled.set_alpha(max(0, min(255, int(alpha))))
    surface.blit(scaled, (center[0] - size // 2, center[1] - size // 2))


def _silhouette_surface(sprite, size):
    scaled = pygame.transform.smoothscale(sprite, (size, size)).convert_alpha()
    scaled.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
    return scaled


def _draw_scaled_silhouette(screen, sprite, center, width, height, alpha=255):
    if not sprite or width <= 0 or height <= 0:
        return
    silhouette = pygame.transform.smoothscale(sprite, (int(width), int(height))).convert_alpha()
    silhouette.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
    silhouette.set_alpha(max(0, min(255, int(alpha))))
    screen.blit(silhouette, (center[0] - int(width) // 2, center[1] - int(height) // 2))


def _draw_scaled_full(screen, sprite, center, width, height, alpha=255):
    if not sprite or width <= 0 or height <= 0:
        return
    scaled = pygame.transform.smoothscale(sprite, (int(width), int(height))).convert_alpha()
    scaled.set_alpha(max(0, min(255, int(alpha))))
    screen.blit(scaled, (center[0] - int(width) // 2, center[1] - int(height) // 2))


def _draw_white_silhouette(screen, sprite, center, width, height, alpha=255):
    if not sprite or width <= 0 or height <= 0:
        return
    scaled = pygame.transform.smoothscale(sprite, (int(width), int(height))).convert_alpha()
    white_surf = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
    white_surf.fill((255, 255, 255, 255))
    white_surf.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    white_surf.set_alpha(max(0, min(255, int(alpha))))
    screen.blit(white_surf, (center[0] - int(width) // 2, center[1] - int(height) // 2))


def draw_evolution_animation(screen, fonts, evolution, sprite_loader, frame, final_form="loop", language="pt", stage=None):
    _, _, small_f, tiny_f = fonts
    tr = globals()["t"]
    source = evolution_sprite_entry(evolution, "source")
    target = evolution_sprite_entry(evolution, "target")
    sprite_loader.request_for(source)
    sprite_loader.request_for(target)
    source_sprite, source_loading, _ = sprite_loader.snapshot_for(source)
    target_sprite, target_loading, _ = sprite_loader.snapshot_for(target)

    # Frame estilo Game Boy: bezel -> tela escura -> textbox
    if stage is None:
        stage_w, stage_h = 360, 196
        stage = pygame.Rect((SCREEN_W - stage_w) // 2, 104, stage_w, stage_h)
    else:
        stage = pygame.Rect(stage)
    # sombra
    shadow = pygame.Surface((stage.w + 8, stage.h + 8), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 100), shadow.get_rect(), border_radius=0)
    screen.blit(shadow, (stage.x - 4, stage.y + 4))
    # bezel claro
    pygame.draw.rect(screen, (62, 76, 110), stage, border_radius=0)
    # borda escura
    pygame.draw.rect(screen, (12, 18, 32), stage.inflate(-10, -10), 3, border_radius=0)
    # tela
    crt = stage.inflate(-22, -22)
    pygame.draw.rect(screen, (10, 16, 30), crt, border_radius=0)

    # area do sprite (deixa espaco embaixo para textbox de ate 2 linhas)
    sprite_area = pygame.Rect(crt.x, crt.y, crt.w, crt.h - 56)
    textbox = pygame.Rect(crt.x + 8, crt.bottom - 52, crt.w - 16, 42)

    # cycle: one-shot animation, frame param ja vem com offset desde o start
    if final_form == "source":
        cycle = 0.0
    elif final_form == "target":
        cycle = 1.0
    else:
        cycle = min(1.0, max(0.0, frame / 180.0))

    cx, cy = sprite_area.center
    base_size = min(132, max(82, min(sprite_area.w, sprite_area.h) - 8))

    if not (source_sprite or target_sprite):
        label = tr(language, "loading_sprites") if source_loading or target_loading else tr(language, "no_sprite")
        text_center(screen, small_f, label, sprite_area, MUTED)
    else:
        if cycle <= 0.10:
            # idle: source com leve bob
            bob = int(math.sin(frame * 0.15) * 2)
            _draw_scaled_full(screen, source_sprite, (cx, cy + bob), base_size, base_size, 255)
        elif cycle <= 0.25:
            # wind-up: stretch vertical
            t = (cycle - 0.10) / 0.15
            h = int(base_size * (1.0 + 0.25 * t))
            w = int(base_size * (1.0 - 0.10 * t))
            _draw_scaled_full(screen, source_sprite, (cx, cy), w, h, 255)
        elif cycle <= 0.85:
            # silhouette swap com frequencia crescente
            t = (cycle - 0.25) / 0.60
            phase = (t ** 2) * 16 * math.pi
            show_target = math.sin(phase) > 0
            visible = target_sprite if show_target else source_sprite
            fallback = source_sprite if show_target else target_sprite
            chosen = visible or fallback
            h = int(base_size * 1.25)
            w = int(base_size * 0.90)
            _draw_scaled_silhouette(screen, chosen, (cx, cy), w, h, 255)
            # flash quando esta perto de trocar (cos(phase) ~ 0)
            flash_intensity = 1.0 - abs(math.cos(phase))
            if flash_intensity > 0.92:
                flash_alpha = int(150 * (flash_intensity - 0.92) / 0.08)
                flash = pygame.Surface(sprite_area.size, pygame.SRCALPHA)
                flash.fill((255, 255, 255, max(0, min(180, flash_alpha))))
                screen.blit(flash, sprite_area.topleft)
        else:
            # reveal do target
            t = (cycle - 0.85) / 0.15
            size = int(base_size * (0.70 + 0.30 * t))
            _draw_scaled_full(screen, target_sprite, (cx, cy), size, size, int(255 * min(1.0, t * 1.5)))
            # flash inicial decrescente
            if t < 0.5:
                flash = pygame.Surface(sprite_area.size, pygame.SRCALPHA)
                flash.fill((255, 255, 255, int(200 * (1 - t * 2))))
                screen.blit(flash, sprite_area.topleft)

    # Textbox: fundo branco com borda escura
    pygame.draw.rect(screen, (240, 240, 230), textbox, border_radius=0)
    pygame.draw.rect(screen, (12, 18, 32), textbox, 2, border_radius=0)
    source_name = source["species_name"]
    target_name = target["species_name"]
    if cycle < 0.25:
        msg = f"{source_name} esta evoluindo!" if language == "pt" else f"{source_name} is evolving!" if language == "en" else f"{source_name} esta evolucionando!"
    elif cycle < 0.85:
        # texto pisca durante a fase de silhouette
        evolving_msg = f"{source_name} esta evoluindo!" if language == "pt" else f"{source_name} is evolving!" if language == "en" else f"{source_name} esta evolucionando!"
        msg = "???" if int(frame / 6) % 2 == 0 else evolving_msg
    else:
        msg = f"{source_name} evoluiu em {target_name}!" if language == "pt" else f"{source_name} evolved into {target_name}!" if language == "en" else f"{source_name} evoluciono a {target_name}!"
    wrap_text(screen, tiny_f, msg, pygame.Rect(textbox.x + 8, textbox.y + 7, textbox.w - 16, textbox.h - 10), (12, 18, 32), line_gap=2, max_lines=2)


def _draw_evolution_flash(screen, center, radius, flash_progress):
    """Desenha um efeito de flash/brilho elegante com partículas e raios."""
    if flash_progress <= 0:
        return

    # Gradiente de opacidade: forte no início, desaparece no final
    alpha_base = int(200 * (1.0 - flash_progress))

    # Núcleo brilhante (amarelo -> branco)
    core_radius = int(radius * (0.4 + flash_progress * 0.6))
    if core_radius > 2:
        core_surf = pygame.Surface((core_radius * 2, core_radius * 2), pygame.SRCALPHA)
        # Gradiente manual do núcleo
        for r in range(core_radius, 0, -1):
            ratio = r / core_radius
            color_alpha = int(alpha_base * (1.0 - ratio * 0.7))
            color = (255, 255, int(150 + ratio * 105), color_alpha)
            pygame.draw.circle(core_surf, color, (core_radius, core_radius), r)
        screen.blit(core_surf, (center[0] - core_radius, center[1] - core_radius))

    # Partículas de brilho saindo do centro
    num_particles = 12
    for i in range(num_particles):
        angle = (i / num_particles) * 2 * math.pi + (flash_progress * 0.3)
        particle_dist = radius * (0.6 + flash_progress * 1.0)
        particle_x = center[0] + math.cos(angle) * particle_dist
        particle_y = center[1] + math.sin(angle) * particle_dist
        particle_size = max(1, int(4 - flash_progress * 3))
        particle_alpha = int(alpha_base * (1.0 - flash_progress * 0.8))

        if particle_alpha > 0:
            particle_surf = pygame.Surface((particle_size * 2, particle_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, (255, 255, 255, particle_alpha), (particle_size, particle_size), particle_size)
            screen.blit(particle_surf, (int(particle_x) - particle_size, int(particle_y) - particle_size))

    # Onda expansiva (círculo que expande)
    wave_radius = int(radius * (0.5 + flash_progress * 1.2))
    wave_alpha = int(alpha_base * 0.6 * (1.0 - flash_progress))
    if wave_radius > 0 and wave_alpha > 0:
        wave_surf = pygame.Surface((wave_radius * 2, wave_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(wave_surf, (255, 255, 220, wave_alpha), (wave_radius, wave_radius), wave_radius, 3)
        screen.blit(wave_surf, (center[0] - wave_radius, center[1] - wave_radius))


def draw_evolution_cancel_prompt(screen, fonts, evolution, sprite_loader, frame, language="pt", pokemon_data=None):
    _, body_f, small_f, tiny_f = fonts
    tr = globals()["t"]
    layout = draw_pokedex_shell(screen, screen_title(language, "trade_evolution"))

    text_panel = layout.left_panel
    info_panel = right_info_panel(layout)
    rect(screen, PANEL, text_panel, 0)
    rect(screen, PANEL_2, info_panel, 0)
    pygame.draw.rect(screen, BORDER, text_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, info_panel, 2, border_radius=0)

    source_name = evolution.get("source_name", "Pokemon")
    target_name = evolution.get("target_name", "evolucao")

    # Painel esquerdo: apenas texto em preto
    wrap_text(screen, body_f, tr(language, "wants_evolve", source=source_name, target=target_name),
              pygame.Rect(text_panel.x + 16, text_panel.y + 40, text_panel.w - 32, 100), (0, 0, 0), max_lines=4, line_gap=2)
    wrap_text(screen, small_f, tr(language, "cancel_evolution_question"),
              pygame.Rect(text_panel.x + 16, text_panel.y + 160, text_panel.w - 32, 60), (0, 0, 0), max_lines=2, line_gap=1)

    # Calcular ciclo para determinar qual sprite mostrar (oscilação mais rápida: 120 frames)
    cycle = min(1.0, max(0.0, frame / 120.0))
    show_target = False
    if cycle <= 0.10:
        show_target = False
    elif cycle >= 0.85:
        show_target = True
    else:
        t = (cycle - 0.25) / 0.60 if cycle >= 0.25 else 0
        phase = (t ** 2) * 24 * math.pi
        show_target = math.sin(phase) > 0

    # Painel direito: layout de select_pokemon com animação no visor
    visor_area = right_visor_rect(info_panel)

    # Efeito de brilho: oscilante durante evolução, forte após conclusão
    if frame < 120:
        progress = (math.sin(frame * 0.08) + 1.0) / 2.0
    else:
        elapsed = frame - 120
        pulse = (math.sin(elapsed * 0.08) + 1.0) / 2.0
        progress = 0.8 + pulse * 0.2

    # Visor com animação
    draw_digital_visor(screen, visor_area, progress)
    pygame.draw.rect(screen, BORDER, visor_area, 2)

    # Informações DENTRO do visor (aparecem gradualmente após frame 120)
    # Calcular opacidade: invisível durante oscilação (0-120), depois aparece gradualmente
    info_display_alpha = 0
    if cycle >= 1.0:
        # Após animação oscilante terminar, calcular fade-in das informações
        move_progress = min(1.0, (frame - 120) / 70.0)
        info_display_alpha = int(255 * (move_progress ** 0.7))

    if info_display_alpha > 0:
        display_name = target_name if show_target else source_name
        display_types = evolution_types(evolution, "target" if show_target else "source")

        # Layout igual select_pokemon: sprite à esquerda, informações à direita
        sprite_box = pygame.Rect(visor_area.x + 2, visor_area.y + 8, 80, 80)
        text_x = sprite_box.right + 8
        text_w = visor_area.right - text_x - 8

        # Nome (com cores originais + opacity)
        name_f = font(11)
        name_surf = name_f.render(display_name, True, (0, 0, 0))
        name_surf.set_alpha(info_display_alpha)
        screen.blit(name_surf, (text_x, visor_area.y + 8))

        # Level
        if pokemon_data:
            level = int(pokemon_data.get("level") or 0)
            level_text = f"Nivel {level}" if level else tr(language, "level_unknown")
        else:
            level_text = "-"
        level_surf = font(10).render(level_text, True, (0, 0, 0))
        level_surf.set_alpha(info_display_alpha)
        screen.blit(level_surf, (text_x, visor_area.y + 30))

        # Tipos em box (igual select_pokemon)
        type_box = pygame.Rect(text_x, visor_area.y + 44, text_w, 22)
        draw_digital_visor(screen, type_box, 1.0)
        if display_types:
            tint = TYPE_COLORS.get(display_types[0], (170, 232, 206))
            overlay = pygame.Surface(type_box.size, pygame.SRCALPHA)
            overlay.fill((tint[0], tint[1], tint[2], 42))
            overlay.set_alpha(info_display_alpha)
            pygame.draw.rect(overlay, (255, 255, 255, 60), overlay.get_rect(), 1)
            screen.blit(overlay, type_box.topleft)
        pygame.draw.rect(screen, BORDER, type_box, 1)
        type_text = " / ".join(type_label(tn, language) for tn in display_types[:2]) or "-"
        type_surf = font(10).render(type_text, True, (0, 0, 0))
        type_surf.set_alpha(info_display_alpha)
        screen.blit(type_surf, type_surf.get_rect(center=type_box.center))

        # XP bar (se pokemon_data disponível)
        if pokemon_data:
            xp_fill, _, _ = pokemon_xp_bar(pokemon_data)
            xp_bar = pygame.Rect(text_x, type_box.bottom + 6, text_w, 10)
            # Fundo da barra com opacity
            bg_surf = pygame.Surface(xp_bar.size, pygame.SRCALPHA)
            bg_surf.fill((214, 214, 214, info_display_alpha))
            screen.blit(bg_surf, xp_bar.topleft)
            pygame.draw.rect(screen, BORDER, xp_bar, 1, border_radius=0)
            if xp_fill > 0:
                fill_w = max(2, int((xp_bar.w - 2) * xp_fill))
                fill_surf = pygame.Surface((fill_w, xp_bar.h - 2), pygame.SRCALPHA)
                fill_surf.fill((ACCENT[0], ACCENT[1], ACCENT[2], info_display_alpha))
                screen.blit(fill_surf, (xp_bar.x + 1, xp_bar.y + 1))

    # Frame branco ficando transparente apenas durante oscilação (120 frames)
    if cycle < 1.0:
        frame_alpha = int(255 * (1.0 - cycle))
        if frame_alpha > 0:
            frame_surface = pygame.Surface(visor_area.size, pygame.SRCALPHA)
            frame_surface.fill((255, 255, 255, frame_alpha))
            screen.blit(frame_surface, visor_area.topleft)

    # Sprite oscilante como silhueta branca que clareia
    sprite_entry = evolution_sprite_entry(evolution, "target" if show_target else "source")
    sprite_loader.request_for(sprite_entry)
    sprite, sprite_loading, _ = sprite_loader.snapshot_for(sprite_entry)

    # Summary panel com item e ataques (desenhar PRIMEIRO, antes do sprite/raios)
    summary_top = visor_area.bottom + 8
    summary_panel = pygame.Rect(info_panel.x + 12, summary_top, info_panel.w - 24, info_panel.bottom - summary_top - 8)

    # Sprite: durante animação (0-120) centralizado, depois move para esquerda
    # Armazenar info do sprite para desenhar por último (por cima)
    sprite_center = None
    draw_flash = False

    if cycle < 1.0:
        # Frames 0-120: Animação oscilante, sprite centralizado
        sprite_center = (visor_area.centerx, visor_area.centery)

        # Flash de brilho no final da oscilação (últimos 30 frames)
        if cycle > 0.75:
            flash_progress = (cycle - 0.75) / 0.25
            _draw_evolution_flash(screen, sprite_center, 60, flash_progress)
            draw_flash = True
    else:
        # Frames 120+: Sprite move para esquerda com easing (acelera no início, freia no final)
        move_progress = min(1.0, (frame - 120) / 70.0)
        # Ease-out quadrático: começa rápido e vai freando
        eased_progress = 1.0 - ((1.0 - move_progress) ** 2)
        sprite_box_final = pygame.Rect(visor_area.x + 2, visor_area.y + 8, 80, 80)
        # Interpolação do sprite: centro -> esquerda
        sprite_x = visor_area.centerx + (sprite_box_final.centerx - visor_area.centerx) * eased_progress
        sprite_center = (sprite_x, visor_area.centery)
    # Desenhar summary panel ANTES do sprite/raios
    if summary_panel.h > 0:
        rect(screen, PANEL_2, summary_panel, 0)
        pygame.draw.rect(screen, BORDER, summary_panel, 2)

        if pokemon_data:
            item_info = held_item_info(pokemon_data)
            item_text = item_info["name"] if item_info else tr(language, "item_none")
            item_icon = pygame.Rect(summary_panel.x + 6, summary_panel.y + 20, 32, 32)
            draw_item_icon(screen, item_icon, item_info)
            text(screen, tiny_f, item_text, item_icon.right + 6, summary_panel.y + 28, MUTED, summary_panel.w - 26)

            moves_panel = pygame.Rect(summary_panel.x + 8, summary_panel.y + 50, summary_panel.w - 16, summary_panel.h - 58)
            text(screen, small_f, tr(language, "moves"), moves_panel.x, moves_panel.y, TEXT, moves_panel.w)
            move_entries = move_display_entries(pokemon_data)
            if move_entries:
                move_f = font(11)
                for move_idx, move_entry in enumerate(move_entries[:4]):
                    move_y = moves_panel.y + 20 + move_idx * 20
                    move_rect = pygame.Rect(moves_panel.x, move_y, moves_panel.w, 16)
                    rect(screen, BG, move_rect, 0)
                    pygame.draw.rect(screen, BORDER, move_rect, 1, border_radius=0)
                    name_area = pygame.Rect(move_rect.x + 6, move_rect.y + 1, move_rect.w - 60, 14)
                    text(screen, move_f, move_entry["name"], name_area.x, name_area.y, TEXT, name_area.w)
                    pp_text = f"{move_entry['pp']}/{move_entry['max_pp']}" if move_entry.get("max_pp") else str(move_entry["pp"])
                    pp_area = pygame.Rect(move_rect.right - 52, move_rect.y + 1, 48, 14)
                    pp_surface = tiny_f.render(pp_text, True, MUTED)
                    screen.blit(pp_surface, pp_surface.get_rect(midright=pp_area.midright))
            else:
                text(screen, tiny_f, tr(language, "no_moves"), moves_panel.x, moves_panel.y + 20, MUTED, moves_panel.w)

    # Desenhar raios (por cima do summary, antes do sprite)
    if draw_flash and cycle > 0.75 and sprite_center:
        flash_progress = (cycle - 0.75) / 0.25
        alpha_base = int(200 * (1.0 - flash_progress))
        radius = 60
        num_rays = 16
        for i in range(num_rays):
            angle = (i / num_rays) * 2 * math.pi
            ray_length = int(radius * (1.2 + flash_progress * 1.0))
            ray_alpha = int(alpha_base * (0.8 - flash_progress * 0.5))
            if ray_alpha > 0:
                end_x = sprite_center[0] + math.cos(angle) * ray_length
                end_y = sprite_center[1] + math.sin(angle) * ray_length
                ray_width = max(1, int(3 - flash_progress * 2))
                # Desenhar raios em uma surface para aplicar alpha corretamente
                ray_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
                pygame.draw.line(ray_surface, (255, 255, 200, ray_alpha), sprite_center, (end_x, end_y), ray_width)
                screen.blit(ray_surface, (0, 0))

    # Desenhar sprite POR ÚLTIMO (por cima de tudo)
    if sprite_center:
        if sprite:
            _draw_white_silhouette(screen, sprite, sprite_center, 80, 80, 255)
        elif sprite_loading:
            wrap_text(screen, tiny_f, tr(language, "loading_sprite"), pygame.Rect(sprite_center[0] - 35, sprite_center[1] - 9, 70, 18), MUTED, max_lines=2)
        else:
            text_center(screen, tiny_f, tr(language, "no_sprite"), pygame.Rect(sprite_center[0] - 40, sprite_center[1] - 40, 80, 80), MUTED)

    draw_footer_actions(screen, tiny_f, [("A", tr(language, "btn_let_evolve")), ("B", tr(language, "btn_cancel_evo"))])


def draw_evolution_cancel_confirm(screen, fonts, evolution, sprite_loader, frame, language="pt", pokemon_data=None):
    _, body_f, small_f, tiny_f = fonts
    tr = globals()["t"]
    layout = draw_pokedex_shell(screen, screen_title(language, "confirm_cancel"))

    stage_panel = layout.left_panel
    info_panel = right_info_panel(layout)
    rect(screen, PANEL, stage_panel, 0)
    rect(screen, PANEL_2, info_panel, 0)
    pygame.draw.rect(screen, BORDER, stage_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, info_panel, 2, border_radius=0)

    source_name = evolution.get("source_name", "Pokemon")

    # Animação congelada à esquerda (forma original)
    stage = pygame.Rect(stage_panel.x + 14, stage_panel.y + 20, stage_panel.w - 28, stage_panel.h - 40)
    draw_evolution_animation(screen, fonts, evolution, sprite_loader, frame, final_form="source", language=language, stage=stage)

    # Painel direito com visor digital (sprite original congelado)
    visor_area = right_visor_rect(info_panel)
    progress = (math.sin(frame * 0.05) + 1.0) / 2.0
    draw_digital_visor(screen, visor_area, progress)
    pygame.draw.rect(screen, BORDER, visor_area, 2)

    # Nome da forma original (sem oscilação) em preto
    text_center(screen, body_f, source_name, pygame.Rect(info_panel.x + 12, visor_area.y + 8, visor_area.w, 20), (0, 0, 0))

    # Sprite original no visor
    sprite_entry = evolution_sprite_entry(evolution, "source")
    sprite_loader.request_for(sprite_entry)
    sprite, _, _ = sprite_loader.snapshot_for(sprite_entry)
    if sprite:
        sprite_center = (visor_area.centerx, visor_area.y + 40)
        _draw_scaled_full(screen, sprite, sprite_center, 80, 80, 255)

    # Tipos e XP
    info_y = visor_area.bottom + 12
    # Pega tipos da forma source
    source_types = evolution_types(evolution, "source")
    if source_types:
        # Mostrar tipos em caixa como em select_pokemon
        type_box = pygame.Rect(info_panel.x + 12, info_y, info_panel.w - 24, 22)
        draw_digital_visor(screen, type_box, 1.0)
        tint = TYPE_COLORS.get(source_types[0], (170, 232, 206))
        overlay = pygame.Surface(type_box.size, pygame.SRCALPHA)
        overlay.fill((tint[0], tint[1], tint[2], 42))
        pygame.draw.rect(overlay, (255, 255, 255, 60), overlay.get_rect(), 1)
        screen.blit(overlay, type_box.topleft)
        pygame.draw.rect(screen, BORDER, type_box, 1)
        type_label_text = " / ".join(type_label(tn, language) for tn in source_types[:2]) or "-"
        type_surface = font(10).render(type_label_text, True, (0, 0, 0))
        screen.blit(type_surface, type_surface.get_rect(center=type_box.center))
        info_y += 30

        # Level
        level = pokemon_data.get("level", 0)
        level_text = f"Nivel {level}" if level else tr(language, "level_unknown")
        level_surface = font(10).render(level_text, True, (0, 0, 0))
        screen.blit(level_surface, (info_panel.x + 12, info_y))
        info_y += 16

        # Barra de XP
        xp_fill, _, _ = pokemon_xp_bar(pokemon_data)
        xp_bar = pygame.Rect(info_panel.x + 12, info_y, info_panel.w - 24, 10)
        rect(screen, (214, 214, 214), xp_bar, 0)
        pygame.draw.rect(screen, BORDER, xp_bar, 1, border_radius=0)
        if xp_fill > 0:
            fill_w = max(2, int((xp_bar.w - 2) * xp_fill))
            rect(screen, ACCENT, pygame.Rect(xp_bar.x + 1, xp_bar.y + 1, fill_w, xp_bar.h - 2), 0)
        info_y += 16

        # Item
        item_info = held_item_info(pokemon_data)
        item_text = item_info["name"] if item_info else tr(language, "item_none")
        item_surface = tiny_f.render(item_text, True, MUTED)
        screen.blit(item_surface, (info_panel.x + 12, info_y))

    # Aviso de cancelamento em preto
    wrap_text(screen, small_f, tr(language, "cancel_evolution_confirm", source=source_name, target="evolucao"),
              pygame.Rect(info_panel.x + 12, info_y + 20, info_panel.w - 24, 50), (0, 0, 0), max_lines=3)

    draw_footer_actions(screen, tiny_f, [("A", tr(language, "btn_no_let_evolve")), ("B", tr(language, "btn_yes_interrupt"))])


def draw_trading(screen, fonts, status, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "trading"), pulsing=True)
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)

    rect(screen, PANEL, left_panel, 0)
    rect(screen, PANEL_2, right_panel, 0)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=0)

    message = translate_literal(language, status) or t(language, "processing")
    visor_rect = right_visor_rect(right_panel)

    draw_digital_visor(screen, visor_rect, 1.0)
    pygame.draw.rect(screen, BORDER, visor_rect, 2)
    wrap_text(screen, body_f, message, pygame.Rect(visor_rect.x + 12, visor_rect.y + 35, visor_rect.w - 24, 60), (0, 0, 0), line_gap=1, max_lines=3)

    import time
    if not hasattr(draw_trading, '_pulse_start'):
        draw_trading._pulse_start = time.perf_counter()
    pulse_elapsed = time.perf_counter() - draw_trading._pulse_start
    pulse_duration = 0.9
    if pulse_elapsed <= pulse_duration:
        from frontend.components.primitives import draw_lens_pulse
        draw_lens_pulse(screen, (49, 47), pulse_elapsed / pulse_duration)
    else:
        draw_trading._pulse_start = time.perf_counter()

    draw_footer_actions(screen, tiny_f, [("B", t(language, "btn_cancel"))])


def _build_sprite_entry(pokemon):
    entry = dict(pokemon or {})
    canonical = pokemon.get("canonical") if isinstance(pokemon, dict) else {}
    canonical = canonical if isinstance(canonical, dict) else {}
    species_block = canonical.get("species") if isinstance(canonical.get("species"), dict) else {}
    ndex = int(
        pokemon.get("national_dex_id")
        or canonical.get("species_national_id")
        or species_block.get("national_dex_id")
        or 0
    )
    entry["national_dex_id"] = ndex
    entry.setdefault("generation", int(pokemon.get("generation") or canonical.get("source_generation") or 0))
    entry.setdefault("species_id", int(pokemon.get("species_id") or 0))
    entry.setdefault("species_name", pokemon.get("species_name") or canonical.get("species_name") or species_block.get("name") or "Pokemon")
    return entry


def draw_trade_result(screen, fonts, success, data, sprite_loader, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "result"), ok_pulse=success)
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 0)
    rect(screen, PANEL_2, right_panel, 0)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=0)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=0)

    if success:
        # Para self_trade: received_a (foi pro save A) e received_b (foi pro save B)
        # Para troca de rede: received (recebi) e peer (enviei)
        received_a = data.get("received_a", {}) if isinstance(data, dict) else {}
        received_b = data.get("received_b", {}) if isinstance(data, dict) else {}
        received = data.get("received", {}) if isinstance(data, dict) else {}
        peer = data.get("peer", {}) if isinstance(data, dict) else {}

        if received_a and received_b:
            # self_trade: mostra os dois pokemons que foram para cada save
            left_pokemon = dict(received_a)
            right_pokemon = dict(received_b)
            save_a_name = Path(data.get("save_a", "")).name if data.get("save_a") else ""
            save_b_name = Path(data.get("save_b", "")).name if data.get("save_b") else ""
            left_pokemon.setdefault("save_name", save_a_name)
            right_pokemon.setdefault("save_name", save_b_name)
        else:
            # troca de rede: received = o que recebi, peer = o que enviei
            left_pokemon = dict(received or peer)
            right_pokemon = dict(peer)
            left_pokemon.setdefault("save_name", "")
            right_pokemon.setdefault("save_name", "")

        left_entry = _build_sprite_entry(left_pokemon)
        right_entry = _build_sprite_entry(right_pokemon)

        sprite_loader.request_for(left_entry)
        sprite_loader.request_for(right_entry)
        left_sprite, left_loading, _ = sprite_loader.snapshot_for(left_entry)
        right_sprite, right_loading, _ = sprite_loader.snapshot_for(right_entry)

        left_name = pokemon_display_name(left_pokemon) if left_pokemon else "Pokemon"
        right_name = pokemon_display_name(right_pokemon) if right_pokemon else "Pokemon"

        pulse = 0.5 + 0.5 * math.sin(time.perf_counter() * 3.0)
        green_tint = (int(140 + 60 * pulse), int(210 + 30 * pulse), int(150 + 40 * pulse), 255)
        draw_pokemon_detail_component(screen, fonts, left_panel, left_pokemon, left_name, left_sprite, left_loading, language, visor_tint=green_tint)
        draw_pokemon_detail_component(screen, fonts, right_panel, right_pokemon, right_name, right_sprite, right_loading, language, visor_tint=green_tint)
    else:
        error_msg = str(data or t(language, "trade_not_complete"))[:240]
        error_rect = pygame.Rect(left_panel.x + 18, left_panel.y + 34, left_panel.w - 36, 120)
        rect(screen, SCREEN, error_rect, 0)
        pygame.draw.rect(screen, BORDER, error_rect, 2, border_radius=0)
        text_center(screen, body_f, t(language, "error_cancelled"), error_rect, SCREEN_TEXT)
        wrap_text(screen, small_f, error_msg, pygame.Rect(error_rect.x + 16, error_rect.y + 40, error_rect.w - 32, error_rect.h - 50), RED, max_lines=3)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok"))])


def draw_update_screen(screen, fonts, update_status, update_data, language):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, "PokeCable")

    panel = layout.left_panel
    rect(screen, PANEL, panel, 0)
    pygame.draw.rect(screen, BORDER, panel, 2, border_radius=0)

    status_text = ""
    detail_text = ""
    show_update_btn = False

    if update_status == "checking" or update_status == "":
        status_text = t(language, "update_checking")
        detail_text = ""
    elif update_status == "error":
        status_text = t(language, "update_error")
        detail_text = update_data.get("error", "Unknown error")[:100]
    elif update_status == "up_to_date":
        status_text = t(language, "update_up_to_date")
        current = update_data.get("current", "?")
        detail_text = f"v{current}"
    elif update_status == "available":
        status_text = t(language, "update_available")
        latest = update_data.get("latest", "?")
        detail_text = f"v{latest}\n\n{t(language, 'update_press_a')}"
        show_update_btn = True
    elif update_status == "updating":
        status_text = t(language, "update_updating")
        detail_text = ""
    elif update_status == "done":
        status_text = t(language, "update_done")
        detail_text = ""

    y_offset = panel.y + 20
    text(screen, small_f, status_text, panel.x + 20, y_offset, TEXT, panel.w - 40)

    if detail_text:
        detail_y = y_offset + 50
        for line in detail_text.split('\n'):
            text(screen, tiny_f, line, panel.x + 20, detail_y, MUTED, panel.w - 40)
            detail_y += 20

    action_text = t(language, "btn_back")
    if show_update_btn:
        draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))])
    else:
        draw_footer_actions(screen, tiny_f, [("B", t(language, "btn_back"))])


def reset_flow_state(state):
    state.selected_save = None
    state.selected_pokemon = None
    state.pokemon_list = []
    state.pokemon_source = "party"
    state.room_name = ""
    state.room_password = ""
    state.lan_manual_endpoint = ""
    state.action = "access"


def main(initial_screen=None):
    boot_start = time.perf_counter()
    logger.info("Init pygame...")
    logger.info("Debug mode: %s", DEBUG)
    pygame.display.init()
    pygame.font.init()
    pygame.time.get_ticks()
    pygame.key.set_repeat(int(NAV_REPEAT_DELAY * 1000), int(NAV_REPEAT_INTERVAL * 1000))
    logger.info("Boot timing: pygame modules init %.3fs", time.perf_counter() - boot_start)
    joystick_start = time.perf_counter()
    try:
        pygame.joystick.init()
    except Exception as exc:
        logger.warning(f"Joystick init failed: {exc}")
    logger.info("Boot timing: joystick init %.3fs", time.perf_counter() - joystick_start)

    joystick_enum_start = time.perf_counter()
    joysticks = []
    for index in range(pygame.joystick.get_count()):
        joy = pygame.joystick.Joystick(index)
        joy.init()
        joysticks.append(joy)
        logger.info(
            "Joystick %s: %s buttons=%s axes=%s hats=%s",
            index,
            joy.get_name(),
            joy.get_numbuttons(),
            joy.get_numaxes(),
            joy.get_numhats(),
        )
    logger.info("Boot timing: joystick enumeration %.3fs (count=%s)", time.perf_counter() - joystick_enum_start, len(joysticks))

    pygame.mouse.set_visible(False)
    display_start = time.perf_counter()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("PokeCable")
    clock = pygame.time.Clock()
    fonts = (font(20, True), font(16), font(14), font(12))
    logger.info("Boot timing: display + fonts %.3fs", time.perf_counter() - display_start)

    saves_start = time.perf_counter()
    state = PokecableState()
    state.find_saves()
    logger.info("Boot timing: save scan %.3fs", time.perf_counter() - saves_start)
    state.action = "access"
    apply_theme(state.theme)
    logger.info("UI boot complete: saves=%s server=%s total=%.3fs", len(state.saves), state.server_url, time.perf_counter() - boot_start)

    session = UiSessionState()
    if initial_screen:
        session.current_screen = initial_screen
        logger.info("Starting at screen: %s", initial_screen)
        if initial_screen == "select_pokemon" and state.saves:
            state.selected_save = state.saves[0]
            state.pokemon_source = "party"
            try:
                state.get_pokemon_list("party", enrich=True)
                logger.info("Loaded party for debug screen: %s (%s pokemon)", state.selected_save, len(state.pokemon_list))
            except Exception as exc:
                logger.debug("Failed to load party for debug: %s", exc)
    input_state = InputSessionState()
    ui_queue = queue.Queue()
    confirm_queue = queue.Queue()
    trade_thread_ref = MutableRef()
    sprite_loader = SpriteLoader(state.server_url)
    controller = register_default_screens(
        ScreenController(session, input_state, logger, INPUT_TRANSITION_GUARD_SECONDS)
    )

    draw = SimpleNamespace(
        draw_menu=draw_menu,
        draw_config_menu=draw_config_menu,
        draw_infos_topics=draw_infos_topics,
        draw_infos_reader=draw_infos_reader,
        draw_select_save=draw_select_save,
        draw_select_pokemon=draw_select_pokemon,
        draw_keyboard=draw_keyboard,
        draw_connecting=draw_connecting,
        draw_waiting_partner=draw_waiting_partner,
        draw_cancel_waiting_confirm=draw_cancel_waiting_confirm,
        draw_leave_room_confirm=draw_leave_room_confirm,
        draw_trade_confirm=draw_trade_confirm,
        draw_info_modal=draw_info_modal,
        draw_deposit_confirm=draw_deposit_confirm,
        draw_withdraw_confirm=draw_withdraw_confirm,
        draw_resolve_item_relocation=draw_resolve_item_relocation,
        draw_resolve_moves=draw_resolve_moves,
        draw_evolution_cancel_prompt=draw_evolution_cancel_prompt,
        draw_evolution_cancel_confirm=draw_evolution_cancel_confirm,
        draw_trading=draw_trading,
        draw_trade_result=draw_trade_result,
        draw_update_screen=draw_update_screen,
        next_theme=next_theme,
        KEYBOARD_GRID_W=KEYBOARD_GRID_W,
    )
    ctx = UiContext(screen=screen, fonts=fonts, state=state, sprite_loader=sprite_loader, logger=logger, draw=draw)

    def clear_input_source(source):
        action = input_state.input_source_actions.pop(source, None)
        if not action:
            return
        sources = input_state.pressed_input_actions.get(action)
        if sources:
            sources.discard(source)
            if not sources:
                input_state.pressed_input_actions.pop(action, None)
                input_state.blocked_input_actions.discard(action)

    def set_input_source(source, action):
        if action not in GUARDED_INPUT_ACTIONS:
            clear_input_source(source)
            return
        previous = input_state.input_source_actions.get(source)
        if previous == action:
            return
        clear_input_source(source)
        input_state.input_source_actions[source] = action
        input_state.pressed_input_actions.setdefault(action, set()).add(source)

    def track_input_event(event, mapped_action):
        if event.type == pygame.KEYDOWN:
            set_input_source(f"key:{event.key}", mapped_action)
        elif event.type == pygame.KEYUP:
            clear_input_source(f"key:{event.key}")
        elif event.type == pygame.JOYBUTTONDOWN:
            set_input_source(f"joy:{event.button}", mapped_action)
        elif event.type == pygame.JOYBUTTONUP:
            clear_input_source(f"joy:{event.button}")
        elif event.type == pygame.JOYHATMOTION:
            source = f"hat:{getattr(event, 'hat', 0)}"
            if mapped_action in ("up", "down", "left", "right"):
                set_input_source(source, mapped_action)
            else:
                clear_input_source(source)
        elif event.type == pygame.JOYAXISMOTION and event.axis in (AXIS_X, AXIS_Y):
            source = f"axis:{event.axis}"
            if abs(event.value) < AXIS_THRESHOLD:
                clear_input_source(source)
            elif mapped_action in ("up", "down", "left", "right"):
                set_input_source(source, mapped_action)

    def input_action_blocked(action):
        if action not in GUARDED_INPUT_ACTIONS:
            return False
        return action in input_state.blocked_input_actions or time.monotonic() < input_state.input_guard_until

    def same_save_path(path_a, path_b):
        if not path_a or not path_b:
            return False
        try:
            return Path(path_a).resolve() == Path(path_b).resolve()
        except OSError:
            return str(Path(path_a).absolute()) == str(Path(path_b).absolute())

    def reset_flow_state_with_history(current_state):
        session.navigation_history.clear()
        session.trade_return_context = {}
        session.self_trade_return_context = {}
        session.prompt_return_context = {}
        reset_flow_state(current_state)

    def capture_selection_context(
        screen_id,
        *,
        save_path=None,
        source=None,
        selected_location=None,
        selected_index=None,
        enrich=None,
    ):
        current_save = save_path if save_path is not None else state.selected_save
        current_source = str(source or state.pokemon_source or "party")
        current_selected = state.selected_pokemon if selected_location is None else None
        if selected_location is None and isinstance(current_selected, dict):
            selected_location = str(current_selected.get("location") or "")
        return {
            "screen_id": str(screen_id or session.current_screen or "menu"),
            "save_path": str(current_save) if current_save else "",
            "source": current_source,
            "selected_location": str(selected_location or ""),
            "selected_index": int(session.menu_index if selected_index is None else selected_index),
            "enrich": bool(state.action != "lan") if enrich is None else bool(enrich),
        }

    def restore_selection_context(context, reason, fallback_screen="menu"):
        if not isinstance(context, dict):
            controller.switch_screen(fallback_screen, reason, nav_mode="replace")
            return False
        screen_id = str(context.get("screen_id") or fallback_screen or "menu")
        save_path = str(context.get("save_path") or "").strip()
        source = str(context.get("source") or "party")
        selected_location = str(context.get("selected_location") or "")
        selected_index = int(context.get("selected_index") or 0)
        enrich = bool(context.get("enrich"))
        if save_path:
            state.selected_save = Path(save_path)
            state.selected_pokemon = None
            state.pokemon_source = source
            try:
                state.get_pokemon_list(source, enrich=enrich)
            except Exception as exc:
                logger.warning("Failed to restore selection context %s: %s", screen_id, exc)
                controller.switch_screen(fallback_screen, reason, nav_mode="replace")
                return False
            if selected_location:
                for idx, pokemon in enumerate(state.pokemon_list):
                    if str((pokemon or {}).get("location") or "") == selected_location:
                        selected_index = idx
                        break
            session.menu_index = min(max(0, selected_index), max(0, len(state.pokemon_list) - 1))
        controller.switch_screen(screen_id, reason, nav_mode="replace")
        return True

    services = UiServices(
        ui_queue=ui_queue,
        confirm_queue=confirm_queue,
        trade_thread_ref=trade_thread_ref,
        apply_theme=apply_theme,
        reset_flow_state=reset_flow_state_with_history,
        reset_self_trade_state=session.reset_self_trade,
        same_save_path=same_save_path,
        load_self_trade_source=lambda *args, **kwargs: load_self_trade_source(session, state, *args, **kwargs),
        load_self_trade_party=lambda *args, **kwargs: load_self_trade_party(session, state, *args, **kwargs),
        self_trade_source_label=lambda *args, **kwargs: self_trade_source_label(session, state, *args, **kwargs),
        reload_after_pc_management=lambda *args, **kwargs: reload_after_pc_management(session, state, *args, **kwargs),
        advance_self_trade_prompts=lambda: advance_self_trade_prompts(session, state, services, logger),
        finish_self_trade=lambda: finish_self_trade(session, state, services, logger),
        keyboard_chars=keyboard_chars,
        keyboard_limits=keyboard_limits,
        random_room_name=random_room_name,
        start_trade_thread=start_trade_thread,
        start_lan_trade_thread=start_lan_trade_thread,
        request_trade_cancel=request_trade_cancel,
        request_leave_room=request_leave_room,
        create_backup=_create_backup,
        prepare_self_trade=prepare_self_trade,
        validate_self_trade_candidate=validate_self_trade_candidate,
        execute_self_trade=execute_self_trade,
        switch_screen=controller.switch_screen,
        go_back=controller.go_back,
        capture_selection_context=capture_selection_context,
        restore_selection_context=restore_selection_context,
    )

    while session.running:
        session.frame += 1
        action = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                session.running = False
                continue
            mapped = event_to_action(event, input_state.axis_state, input_state.combo_state, logger)
            track_input_event(event, mapped)
            if event.type == pygame.JOYHATMOTION:
                hat_x, hat_y = event.value
                if hat_x == 0 and hat_y == 0:
                    input_state.nav_hold["direction"] = None
                elif mapped in ("up", "down", "left", "right") and not input_action_blocked(mapped):
                    now = time.monotonic()
                    input_state.nav_hold["direction"] = mapped
                    input_state.nav_hold["started"] = now
                    input_state.nav_hold["last_fire"] = now
            elif event.type == pygame.JOYAXISMOTION and event.axis in (AXIS_X, AXIS_Y):
                if abs(event.value) < AXIS_THRESHOLD:
                    if (event.axis == AXIS_Y and input_state.nav_hold["direction"] in ("up", "down")) or \
                       (event.axis == AXIS_X and input_state.nav_hold["direction"] in ("left", "right")):
                        input_state.nav_hold["direction"] = None
                elif mapped in ("up", "down", "left", "right") and not input_action_blocked(mapped):
                    now = time.monotonic()
                    input_state.nav_hold["direction"] = mapped
                    input_state.nav_hold["started"] = now
                    input_state.nav_hold["last_fire"] = now
            if input_action_blocked(mapped):
                logger.debug("Input action blocked after screen transition: %s", mapped)
                mapped = None
            mapped = debounce_action(mapped, input_state.action_state)
            if mapped and action is None:
                action = mapped

        if action is None and input_state.nav_hold["direction"]:
            now = time.monotonic()
            if now - input_state.nav_hold["started"] >= NAV_REPEAT_DELAY and \
               now - input_state.nav_hold["last_fire"] >= NAV_REPEAT_INTERVAL:
                repeated_action = input_state.nav_hold["direction"]
                if input_action_blocked(repeated_action):
                    input_state.nav_hold["direction"] = None
                else:
                    action = repeated_action
                    input_state.nav_hold["last_fire"] = now
                    input_state.action_state["last_action"] = action
                    input_state.action_state["last_time"] = now

        dispatch_ui_queue(session, services, logger)

        if action and input_action_blocked(action):
            logger.debug("Input action blocked on active screen: %s", action)
            action = None

        if action:
            logger.debug(
                "ACTION screen=%s action=%s menu=%s room=%s",
                session.current_screen,
                action,
                session.menu_index,
                state.room_name,
            )
        if action == "quit_system":
            logger.info("Global quit requested by Start+Select")
            session.running = False
            continue

        if action:
            controller.handle_current_action(action, ctx, state, services)

        controller.render_current(ctx, state, services)

        lowered_status = session.trade_status.lower()
        show_footer_status = (
            session.trade_status
            and not lowered_status.startswith("aguardando")
            and not lowered_status.startswith("sala pronta")
            and "escolha pokemon" not in lowered_status
            and "escolha o pokemon" not in lowered_status
            and "escolha o seu" not in lowered_status
        )
        if show_footer_status and session.current_screen in ("load_save", "select_pokemon"):
            text(screen, fonts[3], translate_literal(state.language, session.trade_status), 20, SCREEN_H - 78, WARN, SCREEN_W - 40)

        pygame.display.flip()
        clock.tick(30)

    if trade_thread_ref.current and trade_thread_ref.current.is_alive():
        trade_thread_ref.current.join(timeout=2)
    pygame.quit()
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        initial_screen = sys.argv[1] if len(sys.argv) > 1 else None
        main(initial_screen)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as exc:
        logger.exception(f"Fatal error: {exc}")
        print(f"\nErro fatal. Veja {ERROR_LOG}.", file=sys.stderr)
        sys.exit(1)
