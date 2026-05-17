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
import threading
from pathlib import Path

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
from r36s_pokecable_core import (
    PokecableState,
    execute_self_trade,
    prepare_self_trade,
    validate_self_trade_candidate,
    start_trade_thread,
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
AXIS_X = 0
AXIS_Y = 1
AXIS_THRESHOLD = 0.7
ACTION_DEBOUNCE = 0.05
NAV_REPEAT_DELAY = 0.25
NAV_REPEAT_INTERVAL = 0.06
QUIT_COMBO_WINDOW = 0.35
JOY_BUTTON_START = 13
JOY_BUTTON_SELECT = 12
ROW_H = 45
ROW_VISIBLE = 7

# GO-Super Gamepad mapping from /opt/inttools/gamecontrollerdb.txt
JOY_MAP = {
    "select": {1},       # a
    "back": {0},         # b
    "x": {2},
    "y": {3},
    "up": {8},
    "down": {9},
    "left": {10},
    "right": {11},
}

THEMES = {
    "pokedex_dark": {
        "bg": (15, 20, 24),
        "panel": (29, 38, 45),
        "panel_2": (43, 55, 65),
        "text": (233, 239, 244),
        "muted": (154, 166, 178),
        "accent": (233, 70, 92),
        "ok": (76, 206, 139),
        "red": (245, 74, 91),
        "warn": (255, 190, 88),
    },
    "pokedex_white": {
        "bg": (236, 239, 243),
        "panel": (251, 252, 254),
        "panel_2": (218, 223, 230),
        "text": (23, 31, 39),
        "muted": (91, 105, 122),
        "accent": (213, 56, 83),
        "ok": (38, 166, 106),
        "red": (211, 54, 73),
        "warn": (196, 138, 44),
    },
}

STRINGS = {
    "pt": {
        "menu_title": "Menu",
        "menu_access_room": "Acessar Sala",
        "menu_self_trade": "Trocar comigo",
        "menu_config": "Config",
        "menu_exit": "Sair",
        "config_title": "Configuracoes",
        "config_language": "Idioma",
        "config_theme": "Tema",
        "lang_pt": "Portugues",
        "lang_en": "English",
        "lang_es": "Espanol",
        "theme_dark": "Dark Pokedex",
        "theme_white": "White Pokedex",
        "btn_ok": "OK",
        "btn_back": "VOLTAR",
        "btn_change": "ALTERAR",
    },
    "en": {
        "menu_title": "Menu",
        "menu_access_room": "Enter Room",
        "menu_self_trade": "Trade With Myself",
        "menu_config": "Config",
        "menu_exit": "Exit",
        "config_title": "Settings",
        "config_language": "Language",
        "config_theme": "Theme",
        "lang_pt": "Portuguese",
        "lang_en": "English",
        "lang_es": "Spanish",
        "theme_dark": "Dark Pokedex",
        "theme_white": "White Pokedex",
        "btn_ok": "OK",
        "btn_back": "BACK",
        "btn_change": "CHANGE",
    },
    "es": {
        "menu_title": "Menu",
        "menu_access_room": "Entrar en Sala",
        "menu_self_trade": "Intercambiar conmigo",
        "menu_config": "Config",
        "menu_exit": "Salir",
        "config_title": "Configuracion",
        "config_language": "Idioma",
        "config_theme": "Tema",
        "lang_pt": "Portugues",
        "lang_en": "Ingles",
        "lang_es": "Espanol",
        "theme_dark": "Dark Pokedex",
        "theme_white": "White Pokedex",
        "btn_ok": "OK",
        "btn_back": "VOLVER",
        "btn_change": "CAMBIAR",
    },
}

BG = (0, 0, 0)
PANEL = (0, 0, 0)
PANEL_2 = (0, 0, 0)
TEXT = (255, 255, 255)
MUTED = (155, 155, 155)
ACCENT = (255, 0, 0)
OK = (0, 200, 0)
RED = (255, 0, 0)
WARN = (255, 200, 0)


def apply_theme(theme_name):
    global BG, PANEL, PANEL_2, TEXT, MUTED, ACCENT, OK, RED, WARN
    palette = THEMES.get(str(theme_name or "").strip().lower(), THEMES["pokedex_dark"])
    BG = palette["bg"]
    PANEL = palette["panel"]
    PANEL_2 = palette["panel_2"]
    TEXT = palette["text"]
    MUTED = palette["muted"]
    ACCENT = palette["accent"]
    OK = palette["ok"]
    RED = palette["red"]
    WARN = palette["warn"]


def t(lang, key):
    language = str(lang or "pt").strip().lower()
    table = STRINGS.get(language, STRINGS["pt"])
    return table.get(key, STRINGS["pt"].get(key, key))

POKEMON_SPRITE_ASSET_DIR = Path(__file__).resolve().parent / "assets" / "pokemon_sprites"
SPRITE_CACHE_VERSION = "pixel-v1"
SPRITE_LOADING_MAX_SECONDS = float(os.getenv("POKECABLE_SPRITE_LOADING_MAX_SECONDS", "3"))

SCROLL_STATE = {}
KEYBOARD_GRID_W = 12
POKEMON_ROOM_NAMES = [
    "Pikachu", "Eevee", "Snorlax", "Charizard", "Bulbasaur", "Squirtle",
    "Gengar", "Dragonite", "Lapras", "Mew", "Mewtwo", "Lucario",
    "Garchomp", "Greninja", "Umbreon", "Espeon", "Jolteon", "Vaporeon",
    "Flareon", "Sylveon", "Ditto", "Tyranitar", "Blaziken", "Sceptile",
    "Swampert", "Rayquaza", "Gardevoir", "Arcanine", "Machamp", "Alakazam",
]
TYPE_LABELS = {
    "normal": "Normal",
    "fire": "Fogo",
    "water": "Agua",
    "electric": "Eletrico",
    "grass": "Grama",
    "ice": "Gelo",
    "fighting": "Lutador",
    "poison": "Veneno",
    "ground": "Terra",
    "flying": "Voador",
    "psychic": "Psiquico",
    "bug": "Inseto",
    "rock": "Pedra",
    "ghost": "Fantasma",
    "dragon": "Dragao",
    "dark": "Sombrio",
    "steel": "Aco",
    "fairy": "Fada",
}
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

def held_item_label(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    item_id = (pokemon or {}).get("held_item_id") or raw.get("held_item_id")
    item_name = (pokemon or {}).get("held_item_name") or raw.get("held_item_name")
    if not item_id:
        return "Item: nenhum"
    return f"Item: {item_name or f'#{item_id}'}"


def held_item_info(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    item_id = (pokemon or {}).get("held_item_id") or raw.get("held_item_id")
    if not item_id:
        return None
    item_id = int(item_id)
    return {
        "id": item_id,
        "name": (pokemon or {}).get("held_item_name") or raw.get("held_item_name") or f"#{item_id}",
        "category": (pokemon or {}).get("held_item_category") or raw.get("held_item_category") or "item",
    }


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
    types = (pokemon or {}).get("types") or raw.get("types") or []
    return [str(type_name).lower() for type_name in types if type_name]


def draw_type_badges(surface, font_obj, type_names, x, y, max_width):
    cursor_x = x
    for type_name in type_names[:2]:
        label = TYPE_LABELS.get(type_name, type_name.title())
        badge_w = min(62, max(42, font_obj.size(label)[0] + 14))
        if cursor_x + badge_w > x + max_width:
            break
        badge = pygame.Rect(cursor_x, y, badge_w, 18)
        rect(surface, TYPE_COLORS.get(type_name, MUTED), badge, 4)
        text(surface, font_obj, label, badge.x + 7, badge.y + 4, (8, 12, 16), badge.w - 12)
        cursor_x += badge_w + 6


def draw_item_icon(surface, area, item_info, selected=False):
    category_colors = {
        "ball": (239, 68, 68),
        "berry": (34, 197, 94),
        "key_item": (245, 158, 11),
        "tm": (59, 130, 246),
        "hm": (37, 99, 235),
        "tmhm": (59, 130, 246),
        "badge": (139, 92, 246),
        "hold_item": (251, 191, 36),
        "system": (148, 163, 184),
        "unused": (100, 116, 139),
        "item": (251, 191, 36),
    }
    rect(surface, BG if selected else PANEL, area, 4)
    if not item_info:
        pygame.draw.line(surface, MUTED, (area.x + 7, area.centery), (area.right - 7, area.centery), 2)
        return
    color = category_colors.get(str(item_info.get("category") or "item"), category_colors["item"])
    pygame.draw.circle(surface, color, area.center, min(area.w, area.h) // 3)
    pygame.draw.circle(surface, TEXT, (area.centerx - 3, area.centery - 3), 2)


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)


def text(surface, fnt, value, x, y, color=None, max_w=None):
    if color is None:
        color = TEXT
    value = str(value)
    if max_w is not None:
        while value and fnt.size(value)[0] > max_w:
            value = value[:-2] + "."
    surface.blit(fnt.render(value, True, color), (x, y))


def rect(surface, color, area, radius=0):
    pygame.draw.rect(surface, color, area, border_radius=radius)


def button(surface, fnt, label, desc, x, y):
    rect(surface, PANEL_2, pygame.Rect(x, y, 24, 24), 4)
    text(surface, fnt, label, x + 7, y + 4, ACCENT)
    text(surface, fnt, desc, x + 31, y + 4, MUTED)


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


def draw_scrollbar(surface, panel, offset, total, visible=ROW_VISIBLE):
    if total <= visible:
        return
    track = pygame.Rect(panel.right - 10, panel.y + 12, 4, panel.h - 24)
    rect(surface, PANEL_2, track, 3)
    thumb_h = max(24, int(track.h * visible / total))
    max_offset = max(1, total - visible)
    thumb_y = track.y + int((track.h - thumb_h) * min(max(offset, 0), max_offset) / max_offset)
    rect(surface, ACCENT, pygame.Rect(track.x, thumb_y, track.w, thumb_h), 3)


def pokemon_sprite_slug(name):
    value = str(name or "").strip().lower()
    replacements = {
        "mr. mime": "mr-mime",
        "farfetch'd": "farfetchd",
        "nidoran f": "nidoran-f",
        "nidoran m": "nidoran-m",
        "ho-oh": "ho-oh",
    }
    if value in replacements:
        return replacements[value]
    value = value.replace("♀", "-f").replace("♂", "-m")
    for token in ["'", ".", ":", ",", "(", ")", "[", "]"]:
        value = value.replace(token, "")
    value = value.replace(" ", "-")
    value = value.replace("--", "-")
    return value


def sprite_form_slug(form):
    value = str(form or "").strip().lower()
    if not value or value == "a":
        return ""
    if value == "!":
        return "exclamation"
    if value == "?":
        return "question"
    value = value.replace("!", "exclamation").replace("?", "question")
    for token in ["'", ".", ":", ",", "(", ")", "[", "]"]:
        value = value.replace(token, "")
    value = value.replace(" ", "-").replace("_", "-")
    while "--" in value:
        value = value.replace("--", "-")
    return value.strip("-")


def pokemon_sprite_variant(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    metadata = (pokemon or {}).get("metadata", {}) if isinstance(pokemon, dict) else {}
    raw_metadata = raw.get("metadata", {}) if isinstance(raw, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    canonical_metadata = canonical.get("metadata", {}) if isinstance(canonical, dict) else {}
    is_shiny = bool(
        (pokemon or {}).get("is_shiny")
        or (raw.get("is_shiny") if isinstance(raw, dict) else False)
        or (metadata.get("is_shiny") if isinstance(metadata, dict) else False)
        or (raw_metadata.get("is_shiny") if isinstance(raw_metadata, dict) else False)
        or (canonical.get("is_shiny") if isinstance(canonical, dict) else False)
        or (canonical_metadata.get("is_shiny") if isinstance(canonical_metadata, dict) else False)
    )
    form = (
        (pokemon or {}).get("unown_form")
        or (pokemon or {}).get("form")
        or (metadata.get("unown_form") if isinstance(metadata, dict) else "")
        or (metadata.get("form") if isinstance(metadata, dict) else "")
        or (raw.get("unown_form") if isinstance(raw, dict) else "")
        or (raw.get("form") if isinstance(raw, dict) else "")
        or (raw_metadata.get("unown_form") if isinstance(raw_metadata, dict) else "")
        or (raw_metadata.get("form") if isinstance(raw_metadata, dict) else "")
        or (canonical_metadata.get("unown_form") if isinstance(canonical_metadata, dict) else "")
        or (canonical_metadata.get("form") if isinstance(canonical_metadata, dict) else "")
    )
    return "shiny" if is_shiny else "normal", sprite_form_slug(form)


def resolve_sprite_national_dex_id(generation, species_id, pokemon=None):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    species_block = canonical.get("species", {}) if isinstance(canonical, dict) else {}
    for value in (
        (pokemon or {}).get("national_dex_id") if isinstance(pokemon, dict) else None,
        raw.get("national_dex_id") if isinstance(raw, dict) else None,
        canonical.get("species_national_id") if isinstance(canonical, dict) else None,
        species_block.get("national_dex_id") if isinstance(species_block, dict) else None,
    ):
        try:
            national_id = int(value or 0)
        except (TypeError, ValueError):
            national_id = 0
        if national_id > 0:
            return national_id
    try:
        generation = int(generation or 0)
        species_id = int(species_id or 0)
        if generation <= 0 or species_id <= 0:
            return 0
        _ensure_backend_import_path()
        from data.species import native_to_national  # type: ignore

        return int(native_to_national(generation, species_id) or 0)
    except Exception as exc:
        logger.debug("Sprite national dex lookup failed: generation=%s species_id=%s error=%s", generation, species_id, exc)
        return 0


class SpriteLoader:
    def __init__(self, server_url: str):
        self.lock = threading.Lock()
        self.asset_dir = POKEMON_SPRITE_ASSET_DIR
        self.current_key = ""
        self.entries = {}
        del server_url

    def _identity(self, pokemon):
        species_name = pokemon.get("species_name") if pokemon else ""
        species_id = int((pokemon or {}).get("species_id") or 0)
        if not pokemon or (not species_name and not species_id) or species_name.lower() == "egg":
            return "", {}

        generation = int((pokemon or {}).get("generation") or 0)
        raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
        national_dex_id = resolve_sprite_national_dex_id(generation, species_id, pokemon)
        slug = pokemon_sprite_slug(species_name)
        if not slug and not national_dex_id:
            return "", {}
        variant, form = pokemon_sprite_variant(pokemon)
        sprite_id = self._sprite_id(national_dex_id, slug, form)
        key = f"{SPRITE_CACHE_VERSION}-{variant}-{sprite_id}-front"
        lookup = {
            "generation": generation,
            "species_slug": slug,
            "species_id": species_id,
            "national_dex_id": national_dex_id,
            "sprite_id": sprite_id,
            "variant": variant,
        }
        return key, lookup

    @staticmethod
    def _sprite_id(national_dex_id, species_slug="", form=""):
        base = str(int(national_dex_id)) if int(national_dex_id or 0) else str(species_slug or "")
        form = sprite_form_slug(form)
        if form:
            return f"{base}-{form}"
        return base

    def request(self, pokemon):
        self.request_for(pokemon)

    def request_for(self, pokemon):
        species_name = pokemon.get("species_name") if pokemon else ""
        species_id = int((pokemon or {}).get("species_id") or 0)
        logger.debug("Sprite request: species_id=%s species_name=%s", species_id, species_name)
        key, lookup = self._identity(pokemon)
        should_load = False
        with self.lock:
            self.current_key = key
            if not key:
                return
            entry = self.entries.get(key)
            if entry and (entry.get("loading") or entry.get("surface") is not None):
                return
            self.entries[key] = {"surface": None, "loading": True, "error": "", "started_at": time.monotonic()}
            should_load = True
        if should_load:
            self._load(key, lookup)

    def _sprite_path(self, lookup):
        variant = str(lookup.get("variant") or "normal")
        sprite_id = str(lookup.get("sprite_id") or lookup.get("national_dex_id") or lookup.get("species_slug") or "")
        if not sprite_id:
            return None
        return self.asset_dir / variant / f"{sprite_id}.png"

    def _load(self, key, lookup):
        try:
            sprite_path = self._sprite_path(lookup)
            if not sprite_path or not sprite_path.exists():
                raise RuntimeError(f"local sprite not found: {sprite_path}")
            surface = pygame.image.load(str(sprite_path)).convert_alpha()
            error = ""
        except Exception as exc:
            surface = None
            error = str(exc)
            logger.warning("Sprite load failed: key=%s error=%s", key, exc)

        with self.lock:
            self.entries[key] = {"surface": surface, "loading": False, "error": error}

    def snapshot(self):
        return self.snapshot_key(self.current_key)

    def snapshot_for(self, pokemon):
        key, _ = self._identity(pokemon)
        return self.snapshot_key(key)

    def snapshot_key(self, key):
        with self.lock:
            entry = self.entries.get(key or "", {})
            loading = bool(entry.get("loading"))
            if loading and time.monotonic() - float(entry.get("started_at") or 0) > SPRITE_LOADING_MAX_SECONDS:
                loading = False
            return entry.get("surface"), loading, str(entry.get("error") or "")


def translate_joy_button(button_id):
    for action, ids in JOY_MAP.items():
        if button_id in ids:
            return action
    return None


def translate_key(key):
    if key in (pygame.K_UP, pygame.K_w):
        return "up"
    if key in (pygame.K_DOWN, pygame.K_s):
        return "down"
    if key in (pygame.K_LEFT, pygame.K_a):
        return "left"
    if key in (pygame.K_RIGHT, pygame.K_d):
        return "right"
    if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        return "select"
    if key in (pygame.K_BACKSPACE, pygame.K_ESCAPE):
        return "back"
    if key == pygame.K_x:
        return "x"
    if key == pygame.K_y:
        return "y"
    return None


def event_to_action(event, axis_state, combo_state):
    if event.type == pygame.KEYDOWN:
        logger.debug(f"KEYDOWN: key={event.key} name={pygame.key.name(event.key)}")
        return translate_key(event.key)

    if event.type == pygame.JOYBUTTONDOWN:
        logger.debug(f"JOYBUTTONDOWN: {event.button}")
        now = time.monotonic()
        combo_state["pressed"].add(event.button)
        combo_state["last_down"][event.button] = now
        if event.button in (JOY_BUTTON_START, JOY_BUTTON_SELECT):
            other = JOY_BUTTON_SELECT if event.button == JOY_BUTTON_START else JOY_BUTTON_START
            other_down = combo_state["last_down"].get(other, 0.0)
            if other in combo_state["pressed"] or (other_down and now - other_down <= QUIT_COMBO_WINDOW):
                logger.info("Quit combo detected: start+select")
                combo_state["pressed"].discard(JOY_BUTTON_START)
                combo_state["pressed"].discard(JOY_BUTTON_SELECT)
                combo_state["suppress_until"] = now + QUIT_COMBO_WINDOW
                return "quit_system"
            if now < combo_state.get("suppress_until", 0.0):
                return None
        return translate_joy_button(event.button)

    if event.type == pygame.JOYBUTTONUP:
        logger.debug(f"JOYBUTTONUP: {event.button}")
        combo_state["pressed"].discard(event.button)
        return None

    if event.type == pygame.JOYHATMOTION:
        logger.debug(f"JOYHATMOTION: {event.value}")
        hat_x, hat_y = event.value
        if hat_y > 0:
            return "up"
        if hat_y < 0:
            return "down"
        if hat_x < 0:
            return "left"
        if hat_x > 0:
            return "right"
        return None

    if event.type == pygame.JOYAXISMOTION:
        logger.debug(f"JOYAXISMOTION: axis={event.axis} value={event.value:.2f}")
        prev = axis_state.get(event.axis, 0.0)
        axis_state[event.axis] = event.value
        if event.axis == AXIS_Y:
            if event.value <= -AXIS_THRESHOLD and prev > -AXIS_THRESHOLD:
                return "up"
            if event.value >= AXIS_THRESHOLD and prev < AXIS_THRESHOLD:
                return "down"
        if event.axis == AXIS_X:
            if event.value <= -AXIS_THRESHOLD and prev > -AXIS_THRESHOLD:
                return "left"
            if event.value >= AXIS_THRESHOLD and prev < AXIS_THRESHOLD:
                return "right"
    return None


def debounce_action(action, action_state):
    if not action:
        return None
    now = time.monotonic()
    if action_state["last_action"] == action and now - action_state["last_time"] < ACTION_DEBOUNCE:
        return None
    action_state["last_action"] = action
    action_state["last_time"] = now
    return action


def draw_menu(screen, fonts, selected, language):
    title_f, _, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "PokeCable", 14, 10)

    items = [
        t(language, "menu_access_room"),
        t(language, "menu_self_trade"),
        t(language, "menu_config"),
        t(language, "menu_exit"),
    ]
    list_panel = pygame.Rect(10, HEADER_H + 10, LIST_W - 18, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)
    text(screen, small_f, t(language, "menu_title"), 22, HEADER_H + 22, MUTED)

    for idx, item in enumerate(items):
        y = HEADER_H + 54 + idx * 50
        row = pygame.Rect(18, y, LIST_W - 34, 40)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, item, row.x + 9, row.y + 9, color, row.w - 18)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", t(language, "btn_ok"), 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", t(language, "btn_back"), 112, SCREEN_H - 48)


def draw_config_menu(screen, fonts, selected, language, theme):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, t(language, "config_title"), 14, 10)

    items = [
        (t(language, "config_language"), t(language, f"lang_{language}")),
        (t(language, "config_theme"), t(language, "theme_dark" if theme == "pokedex_dark" else "theme_white")),
    ]
    list_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)
    for idx, (label, value) in enumerate(items):
        y = HEADER_H + 44 + idx * 64
        row = pygame.Rect(18, y, SCREEN_W - 36, 50)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, label, row.x + 9, row.y + 8, color, row.w - 18)
        text(screen, body_f, value, row.x + 9, row.y + 25, color, row.w - 18)

    helper = "< >"
    text(screen, tiny_f, helper, SCREEN_W - 62, HEADER_H + 14, MUTED)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", t(language, "btn_ok"), 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", t(language, "btn_back"), 112, SCREEN_H - 48)
    button(screen, tiny_f, "<>", t(language, "btn_change"), 238, SCREEN_H - 48)


def draw_action_menu(screen, fonts, selected):
    title_f, _, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Acao", 14, 10)

    items = ["Criar Sala", "Entrar em Sala"]
    list_panel = pygame.Rect(10, HEADER_H + 10, LIST_W - 18, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)
    text(screen, small_f, "Escolha", 22, HEADER_H + 22, MUTED)

    for idx, item in enumerate(items):
        y = HEADER_H + 54 + idx * 50
        row = pygame.Rect(18, y, LIST_W - 34, 40)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, item, row.x + 9, row.y + 9, color, row.w - 18)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)


def keyboard_chars(shift=False):
    base = "`1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./"
    shifted = '~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:"ZXCVBNM<>?'
    return list(shifted if shift else base)


def keyboard_limits(shift=False):
    total = len(keyboard_chars(shift)) + 4
    return total - 1


def random_room_name():
    return f"{random.choice(POKEMON_ROOM_NAMES).lower()}{random.randint(10, 99)}"


def draw_keyboard(screen, fonts, title, value, grid_index, is_password=False, shift=False):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    shift_label = "SHIFT ON" if shift else "SHIFT OFF"
    text(screen, title_f, f"{title} [{shift_label}]", 14, 10)

    display_value = "*" * len(value) if is_password else value
    input_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, 50)
    rect(screen, PANEL, input_panel, 6)
    text(screen, body_f, display_value if display_value else "(vazio)", 20, HEADER_H + 20, ACCENT, SCREEN_W - 40)

    chars = keyboard_chars(shift)
    margin_x = 16
    grid_pitch = (SCREEN_W - margin_x * 2) // KEYBOARD_GRID_W
    key_w = grid_pitch - 4
    key_h = 40
    start_x = margin_x + (SCREEN_W - margin_x * 2 - grid_pitch * KEYBOARD_GRID_W) // 2
    start_y = HEADER_H + 74
    rows_used = math.ceil(len(chars) / KEYBOARD_GRID_W)

    for idx, char in enumerate(chars):
        col, row = idx % KEYBOARD_GRID_W, idx // KEYBOARD_GRID_W
        row_chars = min(KEYBOARD_GRID_W, len(chars) - row * KEYBOARD_GRID_W)
        row_offset = (KEYBOARD_GRID_W - row_chars) * grid_pitch // 2
        x = start_x + row_offset + col * grid_pitch
        y = start_y + row * (key_h + 4)
        selected = idx == grid_index
        key_rect = pygame.Rect(x, y, key_w, key_h)
        rect(screen, ACCENT if selected else PANEL_2, key_rect, 5)
        char_surface = tiny_f.render(char, True, (5, 11, 18) if selected else TEXT)
        screen.blit(char_surface, char_surface.get_rect(center=key_rect.center))

    special_start = len(chars)
    specials = [("DEL", special_start), ("SHIFT", special_start + 1), ("SPACE", special_start + 2), ("OK", special_start + 3)]
    specials_y = start_y + rows_used * (key_h + 4) + 6
    special_total_w = SCREEN_W - margin_x * 2
    special_w = (special_total_w - 3 * 10) // 4
    for offset, (label, idx) in enumerate(specials):
        x = margin_x + offset * (special_w + 10)
        selected = idx == grid_index
        key_rect = pygame.Rect(x, specials_y, special_w, key_h + 4)
        rect(screen, ACCENT if selected else PANEL_2, key_rect, 5)
        label_surface = tiny_f.render(label, True, (5, 11, 18) if selected else TEXT)
        screen.blit(label_surface, label_surface.get_rect(center=key_rect.center))

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SELECT", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "DEL/VOLTAR", 112, SCREEN_H - 48)


def draw_select_save(screen, fonts, selected, saves, title="Select Save"):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, title, 14, 10)

    if not saves:
        text(screen, body_f, "No saves found!", 50, HEADER_H + 100, RED)
        rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
        button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)
        return

    list_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)

    scroll = list_scroll_offset("saves", selected, len(saves))
    first = max(0, int(scroll) - 1)
    last = min(len(saves), int(scroll) + ROW_VISIBLE + 2)
    previous_clip = screen.get_clip()
    screen.set_clip(list_panel.inflate(-8, -8))
    for idx in range(first, last):
        save_path = saves[idx]
        y = HEADER_H + 30 + int((idx - scroll) * ROW_H)
        row = pygame.Rect(18, y, SCREEN_W - 36, 40)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, save_path.name[:50], row.x + 9, row.y + 9, color, row.w - 18)
    screen.set_clip(previous_clip)
    draw_scrollbar(screen, list_panel, scroll, len(saves))

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)


def draw_select_pokemon_source(screen, fonts, selected, status="", room_name="", room_password=""):
    title_f, _, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Escolher Origem", 14, 10)
    helper = status or "Escolha de onde sair o Pokemon para a troca."
    text(screen, tiny_f, helper, max(230, SCREEN_W - tiny_f.size(helper)[0] - 14), 14, MUTED, SCREEN_W - 244)

    items = ["Party", "PC"]
    list_panel = pygame.Rect(10, HEADER_H + 10, LIST_W - 18, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)
    text(screen, small_f, "Escolha", 22, HEADER_H + 22, MUTED)

    for idx, item in enumerate(items):
        y = HEADER_H + 54 + idx * 50
        row = pygame.Rect(18, y, LIST_W - 34, 40)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, item, row.x + 9, row.y + 9, color, row.w - 18)

    info_panel = pygame.Rect(LIST_W + 2, HEADER_H + 10, SCREEN_W - LIST_W - 12, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, info_panel, 6)
    text(screen, small_f, "Sala", info_panel.x + 14, info_panel.y + 12, MUTED)
    text(screen, small_f, room_name or "(sem nome)", info_panel.x + 14, info_panel.y + 38, ACCENT, info_panel.w - 28)
    text(screen, small_f, "Senha", info_panel.x + 14, info_panel.y + 78, MUTED)
    text(screen, small_f, room_password or "(sem senha)", info_panel.x + 14, info_panel.y + 104, ACCENT, info_panel.w - 28)
    text(screen, tiny_f, "Compartilhe estes dados com seu parceiro para entrar na mesma sala.", info_panel.x + 14, info_panel.y + 150, MUTED, info_panel.w - 28)

    ball_cx = info_panel.centerx
    ball_cy = info_panel.bottom - 70
    ball_r = 44
    pygame.draw.circle(screen, (220, 40, 40), (ball_cx, ball_cy), ball_r)
    pygame.draw.circle(screen, (240, 240, 240), (ball_cx, ball_cy), ball_r, draw_top_right=False, draw_top_left=False)
    pygame.draw.rect(screen, (20, 20, 20), pygame.Rect(ball_cx - ball_r, ball_cy - 4, ball_r * 2, 8))
    pygame.draw.circle(screen, (20, 20, 20), (ball_cx, ball_cy), ball_r, 3)
    pygame.draw.circle(screen, (20, 20, 20), (ball_cx, ball_cy), 12)
    pygame.draw.circle(screen, (240, 240, 240), (ball_cx, ball_cy), 7)
    pygame.draw.circle(screen, (20, 20, 20), (ball_cx, ball_cy), 7, 2)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)


def draw_select_pokemon(screen, fonts, selected, pokemon_list, source_label, sprite_loader, status="", allow_pc_actions=True):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    title = "Escolher Pokemon"
    waiting = status or "Aguardando segundo jogador"
    text(screen, title_f, title, 14, 10)
    text(screen, small_f, waiting, max(250, SCREEN_W - small_f.size(waiting)[0] - 14), 14, MUTED, 376)

    if not pokemon_list:
        text(screen, body_f, "No Pokemon found!", 50, HEADER_H + 100, RED)
        rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
        button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)
        return

    list_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)

    scroll = list_scroll_offset("pokemon", selected, len(pokemon_list))
    first = max(0, int(scroll) - 1)
    last = min(len(pokemon_list), int(scroll) + ROW_VISIBLE + 2)
    previous_clip = screen.get_clip()
    screen.set_clip(pygame.Rect(list_panel.x + 4, list_panel.y + 4, 304, list_panel.h - 8))
    for idx in range(first, last):
        pokemon = pokemon_list[idx]
        y = HEADER_H + 30 + int((idx - scroll) * ROW_H)
        row = pygame.Rect(18, y, 292, 40)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        sprite_loader.request_for(pokemon)
        sprite, loading, _ = sprite_loader.snapshot_for(pokemon)
        sprite_slot = pygame.Rect(row.x + 5, row.y + 4, 32, 32)
        rect(screen, BG if idx == selected else PANEL_2, sprite_slot, 4)
        if sprite:
            scaled = pygame.transform.smoothscale(sprite, (30, 30))
            screen.blit(scaled, (sprite_slot.x + 1, sprite_slot.y + 1))
        elif loading:
            text(screen, tiny_f, "...", sprite_slot.x + 8, sprite_slot.y + 8, MUTED)
        item_info = held_item_info(pokemon)
        item_slot = pygame.Rect(row.right - 29, row.y + 8, 22, 22)
        draw_item_icon(screen, item_slot, item_info, idx == selected)
        text(screen, small_f, pokemon.get("display", f"Pokemon {idx+1}")[:42], row.x + 44, row.y + 4, color, row.w - 52)
        item_name = item_info["name"] if item_info else "nenhum"
        text(screen, tiny_f, f"Item: {item_name}", row.x + 44, row.y + 23, color if idx == selected else MUTED, 118)
        draw_type_badges(screen, tiny_f, pokemon_types(pokemon), row.right - 124, row.y + 22, 88)
    screen.set_clip(previous_clip)
    draw_scrollbar(screen, pygame.Rect(10, list_panel.y, 308, list_panel.h), scroll, len(pokemon_list))

    selected_pokemon = pokemon_list[selected] if 0 <= selected < len(pokemon_list) else None
    sprite_loader.request(selected_pokemon)
    detail_panel = pygame.Rect(326, HEADER_H + 20, 292, SCREEN_H - HEADER_H - FOOTER_H - 40)
    rect(screen, PANEL_2, detail_panel, 6)
    text(screen, small_f, source_label, detail_panel.x + 14, detail_panel.y + 12, MUTED)

    if selected_pokemon:
        sprite, loading, error = sprite_loader.snapshot()
        sprite_box = pygame.Rect(detail_panel.x + 20, detail_panel.y + 40, 128, 128)
        rect(screen, BG, sprite_box, 8)
        if sprite:
            scaled = pygame.transform.smoothscale(sprite, (96, 96))
            screen.blit(scaled, (sprite_box.x + 16, sprite_box.y + 16))
        elif loading:
            text(screen, tiny_f, "Carregando sprite...", sprite_box.x + 8, sprite_box.y + 56, MUTED)
        else:
            text(screen, tiny_f, "Sem sprite", sprite_box.x + 28, sprite_box.y + 56, MUTED)

        text(screen, body_f, selected_pokemon.get("name", "Pokemon"), detail_panel.x + 164, detail_panel.y + 54, TEXT, 110)
        text(screen, small_f, f"Nivel: {selected_pokemon.get('level', 0)}", detail_panel.x + 164, detail_panel.y + 86, ACCENT)
        draw_type_badges(screen, tiny_f, pokemon_types(selected_pokemon), detail_panel.x + 164, detail_panel.y + 108, 112)
        item_info = held_item_info(selected_pokemon)
        item_icon = pygame.Rect(detail_panel.x + 164, detail_panel.y + 132, 20, 20)
        draw_item_icon(screen, item_icon, item_info)
        text(screen, tiny_f, item_info["name"] if item_info else "Sem item", detail_panel.x + 190, detail_panel.y + 134, MUTED, 86)
        location = selected_pokemon.get("location", "")
        if location.startswith("box:"):
            parts = location.split(":")
            box_name = selected_pokemon.get("raw", {}).get("box_name") or f"Box {int(parts[1]) + 1}"
            text(screen, tiny_f, box_name, detail_panel.x + 164, detail_panel.y + 158, MUTED, 110)
        else:
            text(screen, tiny_f, "Party", detail_panel.x + 164, detail_panel.y + 158, MUTED, 110)

        detail_y = detail_panel.y + 190
        text(screen, small_f, "Ataques", detail_panel.x + 14, detail_y, TEXT)
        moves = move_labels(selected_pokemon)
        if moves:
            for move_idx, move_name in enumerate(moves[:4]):
                move_x = detail_panel.x + 14 + (move_idx % 2) * 136
                move_y = detail_y + 28 + (move_idx // 2) * 28
                move_rect = pygame.Rect(move_x, move_y, 126, 22)
                rect(screen, BG, move_rect, 4)
                text(screen, tiny_f, move_name, move_rect.x + 6, move_rect.y + 5, TEXT, move_rect.w - 12)
        else:
            text(screen, tiny_f, "Sem ataques", detail_panel.x + 14, detail_y + 28, MUTED)
        if error and DEBUG:
            text(screen, tiny_f, error[:40], detail_panel.x + 14, detail_panel.bottom - 30, WARN, detail_panel.w - 28)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)
    if allow_pc_actions:
        is_party = "party" in (source_label or "").lower()
        x_label = "MOVER P/ PC" if is_party else "RETIRAR"
        button(screen, tiny_f, "X", x_label, 212, SCREEN_H - 48)
        y_label = "VER PC" if is_party else "VER PARTY"
        button(screen, tiny_f, "Y", y_label, 360, SCREEN_H - 48)


def draw_connecting(screen, fonts, frame):
    title_f, body_f, _, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Conectando", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    dots = "." * ((frame // 15) % 4)
    text(screen, body_f, f"Conectando ao servidor{dots}", 50, HEADER_H + 150, MUTED)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    text(screen, tiny_f, "Aguarde...", 250, SCREEN_H - 45, MUTED)


def draw_waiting_partner(screen, fonts, status):
    title_f, body_f, _, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Aguardando segundo jogador", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    text(screen, body_f, status or "Aguardando segundo jogador...", 40, HEADER_H + 150, MUTED, SCREEN_W - 80)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "B", "CANCELAR", 12, SCREEN_H - 48)


def draw_leave_room_confirm(screen, fonts):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Sair da sala?", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    text(screen, body_f, "Deseja encerrar esta sala?", 30, HEADER_H + 60, TEXT, SCREEN_W - 60)
    text(screen, small_f, "Voce e o parceiro voltarao ao menu.", 30, HEADER_H + 110, MUTED, SCREEN_W - 60)
    text(screen, small_f, "Para mais trocas, escolha A=NAO.", 30, HEADER_H + 140, MUTED, SCREEN_W - 60)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SIM", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "NAO", 112, SCREEN_H - 48)


def draw_deposit_confirm(screen, fonts, pokemon):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Mover para PC?", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    name = (pokemon or {}).get("display") or (pokemon or {}).get("nickname") or (pokemon or {}).get("species_name") or "Pokemon"
    level = (pokemon or {}).get("level")
    text(screen, body_f, f"Enviar {name} para o PC?", 30, HEADER_H + 60, TEXT, SCREEN_W - 60)
    if level:
        text(screen, small_f, f"Nivel {level}", 30, HEADER_H + 100, MUTED)
    text(screen, small_f, "Ele ira para o primeiro slot livre.", 30, HEADER_H + 140, MUTED, SCREEN_W - 60)
    text(screen, small_f, "Um backup do save sera criado antes.", 30, HEADER_H + 170, MUTED, SCREEN_W - 60)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SIM", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "NAO", 112, SCREEN_H - 48)


def draw_withdraw_confirm(screen, fonts, pokemon):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Retirar do PC?", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    name = (pokemon or {}).get("display") or (pokemon or {}).get("nickname") or (pokemon or {}).get("species_name") or "Pokemon"
    box_name = (pokemon or {}).get("box_name") or ""
    text(screen, body_f, f"Trazer {name} para a Party?", 30, HEADER_H + 60, TEXT, SCREEN_W - 60)
    if box_name:
        text(screen, small_f, f"De: {box_name}", 30, HEADER_H + 100, MUTED)
    text(screen, small_f, "Sera adicionado no proximo slot livre da Party.", 30, HEADER_H + 140, MUTED, SCREEN_W - 60)
    text(screen, small_f, "Um backup do save sera criado antes.", 30, HEADER_H + 170, MUTED, SCREEN_W - 60)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SIM", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "NAO", 112, SCREEN_H - 48)


def draw_info_modal(screen, fonts, title, message):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, title or "Aviso", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    body_msg = (message or "").strip() or "Sem detalhes."
    text(screen, body_f, body_msg[:240], content.x + 16, content.y + 30, TEXT, content.w - 32)
    text(screen, small_f, "A troca foi cancelada. A sala continua aberta.", content.x + 16, content.bottom - 60, MUTED, content.w - 32)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)


def draw_resolve_moves(screen, fonts, removed_move, replacement_index, current_idx, total, chosen_ids=None):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, f"Move incompativel {current_idx + 1}/{total}", 14, 10)

    info_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, 70)
    rect(screen, PANEL, info_panel, 6)
    move_name_text = removed_move.get("name") or local_move_name(removed_move.get("move_id", 0))
    if is_move_number_label(move_name_text):
        move_name_text = local_move_name(removed_move.get("move_id", 0))
    text(screen, body_f, f"Sem suporte: {move_name_text}", info_panel.x + 14, info_panel.y + 14, ACCENT)
    text(screen, small_f, "Escolha um substituto ou deixe vazio.", info_panel.x + 14, info_panel.y + 42, MUTED)

    chosen_set = set(int(x) for x in (chosen_ids or []) if x)
    replacements = [
        r for r in (removed_move.get("valid_replacements") or [])
        if int(r.get("move_id") or 0) not in chosen_set
    ]
    options = replacements + [{"move_id": 0, "name": "(deixar vazio)"}]
    list_panel = pygame.Rect(10, HEADER_H + 90, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 100)
    rect(screen, PANEL, list_panel, 6)

    scroll = list_scroll_offset(f"resolve_moves_{current_idx}", replacement_index, len(options))
    first = max(0, int(scroll) - 1)
    last = min(len(options), int(scroll) + ROW_VISIBLE + 2)
    previous_clip = screen.get_clip()
    screen.set_clip(list_panel.inflate(-8, -8))
    for idx in range(first, last):
        option = options[idx]
        y = list_panel.y + 14 + int((idx - scroll) * ROW_H)
        row = pygame.Rect(list_panel.x + 8, y, list_panel.w - 24, 40)
        color = (5, 11, 18) if idx == replacement_index else TEXT
        if idx == replacement_index:
            rect(screen, ACCENT, row, 4)
        label = option.get("name") or local_move_name(option.get("move_id", 0))
        if is_move_number_label(label):
            label = local_move_name(option.get("move_id", 0))
        text(screen, small_f, label[:48], row.x + 10, row.y + 10, color, row.w - 20)
    screen.set_clip(previous_clip)
    draw_scrollbar(screen, list_panel, scroll, len(options))

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "ESCOLHER", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "PULAR", 132, SCREEN_H - 48)


def draw_cancel_waiting_confirm(screen, fonts):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Cancelar troca?", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    text(screen, body_f, "Cancelar a troca deste Pokemon?", 30, HEADER_H + 60, TEXT, SCREEN_W - 60)
    text(screen, small_f, "Seu save NAO sera modificado.", 30, HEADER_H + 110, MUTED, SCREEN_W - 60)
    text(screen, small_f, "A sala continua aberta - voce escolhera outro Pokemon.", 30, HEADER_H + 140, MUTED, SCREEN_W - 60)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SIM", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "NAO", 112, SCREEN_H - 48)


def draw_trade_confirm(screen, fonts, my_pokemon, opponent_pokemon, sprite_loader):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Confirmar Troca", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)

    mine = my_pokemon.get("display") or my_pokemon.get("display_summary") or "???"
    peer = opponent_pokemon.get("display_summary") or opponent_pokemon.get("nickname") or opponent_pokemon.get("species_name") or "???"

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

    left_card = pygame.Rect(26, HEADER_H + 44, 286, 222)
    right_card = pygame.Rect(328, HEADER_H + 44, 286, 222)
    rect(screen, PANEL_2, left_card, 8)
    rect(screen, PANEL_2, right_card, 8)
    text(screen, small_f, "Seu Pokemon", left_card.x + 12, left_card.y + 10, OK)
    text(screen, small_f, "Oponente", right_card.x + 12, right_card.y + 10, ACCENT)

    my_sprite_box = pygame.Rect(left_card.x + 78, left_card.y + 36, 128, 128)
    peer_sprite_box = pygame.Rect(right_card.x + 78, right_card.y + 36, 128, 128)
    rect(screen, BG, my_sprite_box, 8)
    rect(screen, BG, peer_sprite_box, 8)
    if my_sprite:
        scaled = pygame.transform.smoothscale(my_sprite, (108, 108))
        screen.blit(scaled, (my_sprite_box.x + 10, my_sprite_box.y + 10))
    elif my_loading:
        text(screen, tiny_f, "Carregando...", my_sprite_box.x + 18, my_sprite_box.y + 56, MUTED)
    else:
        text(screen, tiny_f, "Sem sprite", my_sprite_box.x + 28, my_sprite_box.y + 56, MUTED)
    if peer_sprite:
        scaled = pygame.transform.smoothscale(peer_sprite, (108, 108))
        screen.blit(scaled, (peer_sprite_box.x + 10, peer_sprite_box.y + 10))
    elif peer_loading:
        text(screen, tiny_f, "Carregando...", peer_sprite_box.x + 18, peer_sprite_box.y + 56, MUTED)
    else:
        text(screen, tiny_f, "Sem sprite", peer_sprite_box.x + 28, peer_sprite_box.y + 56, MUTED)

    text(screen, tiny_f, mine, left_card.x + 12, left_card.y + 176, TEXT, left_card.w - 24)
    text(screen, tiny_f, peer, right_card.x + 12, right_card.y + 176, TEXT, right_card.w - 24)
    my_level = int(my_pokemon.get("level") or 0)
    peer_level = int(opponent_pokemon.get("level") or 0)
    text(screen, tiny_f, f"Nivel {my_level}" if my_level else "Nivel ?", left_card.x + 12, left_card.y + 198, MUTED)
    text(screen, tiny_f, f"Nivel {peer_level}" if peer_level else "Nivel ?", right_card.x + 12, right_card.y + 198, MUTED)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "CONFIRMAR", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "CANCELAR", 112, SCREEN_H - 48)


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


def draw_evolution_animation(screen, fonts, evolution, sprite_loader, frame, final_form="loop"):
    _, _, small_f, tiny_f = fonts
    source = evolution_sprite_entry(evolution, "source")
    target = evolution_sprite_entry(evolution, "target")
    sprite_loader.request_for(source)
    sprite_loader.request_for(target)
    source_sprite, source_loading, _ = sprite_loader.snapshot_for(source)
    target_sprite, target_loading, _ = sprite_loader.snapshot_for(target)

    # Frame estilo Game Boy: bezel -> tela escura -> textbox
    stage_w, stage_h = 360, 210
    stage = pygame.Rect((SCREEN_W - stage_w) // 2, HEADER_H + 16, stage_w, stage_h)
    # sombra
    shadow = pygame.Surface((stage.w + 8, stage.h + 8), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 100), shadow.get_rect(), border_radius=16)
    screen.blit(shadow, (stage.x - 4, stage.y + 4))
    # bezel claro
    pygame.draw.rect(screen, (62, 76, 110), stage, border_radius=14)
    # borda escura
    pygame.draw.rect(screen, (12, 18, 32), stage.inflate(-10, -10), 3, border_radius=10)
    # tela
    crt = stage.inflate(-22, -22)
    pygame.draw.rect(screen, (10, 16, 30), crt, border_radius=8)

    # area do sprite (deixa ~46px embaixo para textbox)
    sprite_area = pygame.Rect(crt.x, crt.y, crt.w, crt.h - 46)
    textbox = pygame.Rect(crt.x + 8, crt.bottom - 42, crt.w - 16, 32)

    # cycle: one-shot animation, frame param ja vem com offset desde o start
    if final_form == "source":
        cycle = 0.0
    elif final_form == "target":
        cycle = 1.0
    else:
        cycle = min(1.0, max(0.0, frame / 180.0))

    cx, cy = sprite_area.center
    base_size = 132

    if not (source_sprite or target_sprite):
        label = "Carregando sprites..." if source_loading or target_loading else "Sem sprite"
        text(screen, small_f, label, sprite_area.x + 80, sprite_area.centery - 8, MUTED)
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
    pygame.draw.rect(screen, (240, 240, 230), textbox, border_radius=4)
    pygame.draw.rect(screen, (12, 18, 32), textbox, 2, border_radius=4)
    source_name = source["species_name"]
    target_name = target["species_name"]
    if cycle < 0.25:
        msg = f"{source_name} esta evoluindo!"
    elif cycle < 0.85:
        # texto pisca durante a fase de silhouette
        msg = "???" if int(frame / 6) % 2 == 0 else f"{source_name} esta evoluindo!"
    else:
        msg = f"{source_name} evoluiu em {target_name}!"
    text(screen, tiny_f, msg, textbox.x + 8, textbox.y + 8, (12, 18, 32), textbox.w - 16)


def draw_evolution_cancel_prompt(screen, fonts, evolution, sprite_loader, frame):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Evolucao por Troca", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    source = evolution.get("source_name", "Pokemon")
    target = evolution.get("target_name", "evolucao")
    draw_evolution_animation(screen, fonts, evolution, sprite_loader, frame)
    text(screen, body_f, f"{source} quer evoluir para {target}.", 30, HEADER_H + 240, TEXT, SCREEN_W - 60)
    text(screen, small_f, "Deseja cancelar essa evolucao?", 30, HEADER_H + 274, WARN, SCREEN_W - 60)
    text(screen, tiny_f, "B deixa a animacao terminar na forma evoluida.", 30, HEADER_H + 308, MUTED, SCREEN_W - 60)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "DEIXAR EVOLUIR", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "CANCELAR EVO", 172, SCREEN_H - 48)


def draw_evolution_cancel_confirm(screen, fonts, evolution, sprite_loader, frame):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Confirmar Cancelamento", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    source = evolution.get("source_name", "Pokemon")
    target = evolution.get("target_name", "evolucao")
    draw_evolution_animation(screen, fonts, evolution, sprite_loader, frame, final_form="source")
    text(screen, body_f, "Tem certeza?", 30, HEADER_H + 240, WARN, SCREEN_W - 60)
    text(screen, small_f, f"Isso ira interromper a evolucao de {source} para {target}.", 30, HEADER_H + 274, TEXT, SCREEN_W - 60)
    text(screen, tiny_f, "A troca continua, mas o Pokemon recebido fica sem evoluir.", 30, HEADER_H + 308, MUTED, SCREEN_W - 60)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "NAO, DEIXAR EVOLUIR", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "SIM, INTERROMPER", 250, SCREEN_H - 48)


def draw_trading(screen, fonts, status):
    title_f, body_f, _, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Trading", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    text(screen, body_f, status or "Processando...", 30, HEADER_H + 150, MUTED, SCREEN_W - 60)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    text(screen, tiny_f, "Processando...", 250, SCREEN_H - 45, MUTED)


def draw_trade_result(screen, fonts, success, data):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Resultado", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)

    if success:
        text(screen, body_f, "Trade Completo!", 50, HEADER_H + 100, OK)
        peer = data.get("peer", {}) if isinstance(data, dict) else {}
        received = data.get("received", {}) if isinstance(data, dict) else {}
        evolution = received.get("trade_evolution", {}) if isinstance(received, dict) else {}
        pokemon_display = (
            f"{evolution.get('source_name')} -> {evolution.get('target_name')}"
            if evolution.get("evolved")
            else f"{evolution.get('source_name')} sem evoluir"
            if evolution.get("cancelled")
            else received.get("display_summary") or peer.get("display_summary") or peer.get("nickname") or peer.get("species_name") or "Pokemon"
        )
        if isinstance(data, dict) and (data.get("backup_a") or data.get("backup_b")):
            backup_a = Path(data.get("backup_a", "")).name if data.get("backup_a") else "nenhum"
            backup_b = Path(data.get("backup_b", "")).name if data.get("backup_b") else "nenhum"
            backup_name = f"{backup_a} / {backup_b}"
        else:
            backup_name = Path(data.get("backup", "")).name if isinstance(data, dict) and data.get("backup") else "nenhum"
        text(screen, small_f, f"Recebido: {pokemon_display}", 50, HEADER_H + 170, TEXT)
        text(screen, tiny_f, f"Backup: {backup_name}", 50, HEADER_H + 210, MUTED, SCREEN_W - 100)
    else:
        text(screen, body_f, "Erro ou Cancelado", 50, HEADER_H + 100, RED)
        text(screen, small_f, str(data or "Trade nao completado")[:70], 50, HEADER_H + 180, RED, SCREEN_W - 100)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)


def reset_flow_state(state):
    state.selected_save = None
    state.selected_pokemon = None
    state.pokemon_list = []
    state.pokemon_source = "party"
    state.room_name = ""
    state.room_password = ""
    state.action = "access"


def main():
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
    pygame.display.set_caption("PokeCable Room")
    clock = pygame.time.Clock()
    fonts = (font(22, True), font(18), font(16), font(14))
    logger.info("Boot timing: display + fonts %.3fs", time.perf_counter() - display_start)

    saves_start = time.perf_counter()
    state = PokecableState()
    state.find_saves()
    logger.info("Boot timing: save scan %.3fs", time.perf_counter() - saves_start)
    state.action = "access"
    apply_theme(state.theme)
    logger.info("UI boot complete: saves=%s server=%s total=%.3fs", len(state.saves), state.server_url, time.perf_counter() - boot_start)

    current_screen = "menu"
    menu_index = 0
    config_dirty = False
    keyboard_index = 0
    keyboard_shift = False
    room_name = ""
    room_password = ""
    frame = 0
    running = True

    ui_queue = queue.Queue()
    confirm_queue = queue.Queue()
    trade_thread = None
    trade_status = ""
    result_data = {}
    axis_state = {}
    combo_state = {"pressed": set(), "last_down": {}, "suppress_until": 0.0}
    action_state = {"last_action": None, "last_time": 0.0}
    nav_hold = {"direction": None, "started": 0.0, "last_fire": 0.0}
    pending_removed_moves = []
    resolve_current_idx = 0
    resolve_replacement_idx = 0
    resolved_moves_choices = {}
    info_modal_data = {"title": "", "message": ""}
    pending_deposit_idx = -1
    pending_withdraw_pokemon = None
    evolution_anim_start = None
    self_trade_save_a = None
    self_trade_save_b = None
    self_trade_pokemon_a = None
    self_trade_pokemon_b = None
    self_trade_context = {}
    self_trade_pending_decision = ""
    evolution_prompt_input_unlock_until = 0.0
    self_trade_decisions = {
        "cancel_evolution_to_a": False,
        "cancel_evolution_to_b": False,
        "resolved_moves_to_a": {},
        "resolved_moves_to_b": {},
        "_evolution_to_a_done": False,
        "_evolution_to_b_done": False,
        "_moves_to_a_done": False,
        "_moves_to_b_done": False,
    }
    sprite_loader = SpriteLoader(state.server_url)

    def switch_screen(new_screen, reason):
        nonlocal current_screen, evolution_prompt_input_unlock_until
        if current_screen != new_screen:
            logger.info("SCREEN %s -> %s (%s)", current_screen, new_screen, reason)
        current_screen = new_screen
        if new_screen in ("evolution_cancel_prompt", "evolution_cancel_confirm"):
            # Prevent residual A/B input from the previous screen from auto-confirming.
            evolution_prompt_input_unlock_until = time.monotonic() + 0.25

    def reset_self_trade_state():
        nonlocal self_trade_save_a, self_trade_save_b, self_trade_pokemon_a, self_trade_pokemon_b
        nonlocal self_trade_context, self_trade_pending_decision, self_trade_decisions
        self_trade_save_a = None
        self_trade_save_b = None
        self_trade_pokemon_a = None
        self_trade_pokemon_b = None
        self_trade_context = {}
        self_trade_pending_decision = ""
        self_trade_decisions = {
            "cancel_evolution_to_a": False,
            "cancel_evolution_to_b": False,
            "resolved_moves_to_a": {},
            "resolved_moves_to_b": {},
            "_evolution_to_a_done": False,
            "_evolution_to_b_done": False,
            "_moves_to_a_done": False,
            "_moves_to_b_done": False,
        }

    def same_save_path(path_a, path_b):
        if not path_a or not path_b:
            return False
        try:
            return Path(path_a).resolve() == Path(path_b).resolve()
        except OSError:
            return str(Path(path_a).absolute()) == str(Path(path_b).absolute())

    def load_self_trade_party(save_path, *, target_save_path=None, require_compatible_to_target=False):
        nonlocal trade_status
        state.selected_save = Path(save_path)
        state.pokemon_source = "party"
        state.selected_pokemon = None
        state.get_pokemon_list("party", enrich=False)
        base_status = f"Party: {Path(save_path).name}"
        if not require_compatible_to_target or not target_save_path or not self_trade_pokemon_a:
            trade_status = base_status
            return
        trade_status = base_status

    def advance_self_trade_prompts():
        nonlocal pending_removed_moves, resolve_current_idx, resolve_replacement_idx, resolved_moves_choices
        nonlocal result_data, evolution_anim_start, self_trade_pending_decision, trade_status, menu_index
        preflight_to_a = self_trade_context.get("preflight_to_a", {}) if isinstance(self_trade_context, dict) else {}
        preflight_to_b = self_trade_context.get("preflight_to_b", {}) if isinstance(self_trade_context, dict) else {}
        evolution_to_a = self_trade_context.get("trade_evolution_to_a", {}) if isinstance(self_trade_context, dict) else {}
        evolution_to_b = self_trade_context.get("trade_evolution_to_b", {}) if isinstance(self_trade_context, dict) else {}

        if not self_trade_decisions.get("_evolution_to_a_done"):
            self_trade_decisions["_evolution_to_a_done"] = True
            evolution = evolution_to_a if isinstance(evolution_to_a, dict) and evolution_to_a else {}
            if not evolution and isinstance(preflight_to_a, dict):
                evolution = preflight_to_a.get("trade_evolution") or {}
                logger.warning("Self-trade evolution fallback used for save A preflight payload")
            if isinstance(evolution, dict) and evolution.get("evolved"):
                result_data = evolution
                self_trade_pending_decision = "cancel_evolution_to_a"
                evolution_anim_start = frame
                trade_status = f"{Path(self_trade_save_a).name}: decidir evolucao"
                switch_screen("evolution_cancel_prompt", "self_trade_evolution_to_a")
                return
            logger.info("Self-trade no evolution prompt for save A: evolved=%s reason=%s", evolution.get("evolved"), evolution.get("reason"))

        if not self_trade_decisions.get("_moves_to_a_done"):
            self_trade_decisions["_moves_to_a_done"] = True
            removed = list(preflight_to_a.get("removed_moves") or []) if isinstance(preflight_to_a, dict) else []
            if removed:
                pending_removed_moves = removed
                resolve_current_idx = 0
                resolve_replacement_idx = 0
                resolved_moves_choices = {}
                self_trade_pending_decision = "resolved_moves_to_a"
                trade_status = f"{Path(self_trade_save_a).name}: resolver movimentos"
                switch_screen("resolve_moves", "self_trade_moves_to_a")
                return

        if not self_trade_decisions.get("_evolution_to_b_done"):
            self_trade_decisions["_evolution_to_b_done"] = True
            evolution = evolution_to_b if isinstance(evolution_to_b, dict) and evolution_to_b else {}
            if not evolution and isinstance(preflight_to_b, dict):
                evolution = preflight_to_b.get("trade_evolution") or {}
                logger.warning("Self-trade evolution fallback used for save B preflight payload")
            if isinstance(evolution, dict) and evolution.get("evolved"):
                result_data = evolution
                self_trade_pending_decision = "cancel_evolution_to_b"
                evolution_anim_start = frame
                trade_status = f"{Path(self_trade_save_b).name}: decidir evolucao"
                switch_screen("evolution_cancel_prompt", "self_trade_evolution_to_b")
                return
            logger.info("Self-trade no evolution prompt for save B: evolved=%s reason=%s", evolution.get("evolved"), evolution.get("reason"))

        if not self_trade_decisions.get("_moves_to_b_done"):
            self_trade_decisions["_moves_to_b_done"] = True
            removed = list(preflight_to_b.get("removed_moves") or []) if isinstance(preflight_to_b, dict) else []
            if removed:
                pending_removed_moves = removed
                resolve_current_idx = 0
                resolve_replacement_idx = 0
                resolved_moves_choices = {}
                self_trade_pending_decision = "resolved_moves_to_b"
                trade_status = f"{Path(self_trade_save_b).name}: resolver movimentos"
                switch_screen("resolve_moves", "self_trade_moves_to_b")
                return

        state.selected_pokemon = self_trade_pokemon_a
        result_data = self_trade_context.get("payload_b", {}) if isinstance(self_trade_context, dict) else {}
        trade_status = "Validacoes concluidas. Confirme a troca local."
        menu_index = 0
        switch_screen("self_trade_confirm", "self_trade_ready_to_confirm")

    def finish_self_trade():
        nonlocal result_data, trade_status, menu_index
        trade_status = "Aplicando troca local..."
        switch_screen("trading", "self_trade_commit")
        try:
            result_data = execute_self_trade(
                self_trade_context,
                cancel_evolution_to_a=bool(self_trade_decisions.get("cancel_evolution_to_a")),
                cancel_evolution_to_b=bool(self_trade_decisions.get("cancel_evolution_to_b")),
                resolved_moves_to_a=dict(self_trade_decisions.get("resolved_moves_to_a") or {}),
                resolved_moves_to_b=dict(self_trade_decisions.get("resolved_moves_to_b") or {}),
            )
            trade_status = "Troca local concluida!"
            state.save_analysis.clear()
            switch_screen("trade_result", "self_trade_done")
            menu_index = 0
        except Exception as exc:
            logger.exception("Self trade failed: %s", exc)
            trade_status = f"Erro: {exc}"
            result_data = {"success": False, "error": str(exc)}
            switch_screen("trade_result", "self_trade_failed")
            menu_index = 0

    while running:
        frame += 1
        action = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            mapped = event_to_action(event, axis_state, combo_state)
            if event.type == pygame.JOYHATMOTION:
                hat_x, hat_y = event.value
                if hat_x == 0 and hat_y == 0:
                    nav_hold["direction"] = None
                elif mapped in ("up", "down", "left", "right"):
                    now = time.monotonic()
                    nav_hold["direction"] = mapped
                    nav_hold["started"] = now
                    nav_hold["last_fire"] = now
            elif event.type == pygame.JOYAXISMOTION and event.axis in (AXIS_X, AXIS_Y):
                if abs(event.value) < AXIS_THRESHOLD:
                    if (event.axis == AXIS_Y and nav_hold["direction"] in ("up", "down")) or \
                       (event.axis == AXIS_X and nav_hold["direction"] in ("left", "right")):
                        nav_hold["direction"] = None
                elif mapped in ("up", "down", "left", "right"):
                    now = time.monotonic()
                    nav_hold["direction"] = mapped
                    nav_hold["started"] = now
                    nav_hold["last_fire"] = now
            mapped = debounce_action(mapped, action_state)
            if mapped and action is None:
                action = mapped

        if action is None and nav_hold["direction"]:
            now = time.monotonic()
            if now - nav_hold["started"] >= NAV_REPEAT_DELAY and \
               now - nav_hold["last_fire"] >= NAV_REPEAT_INTERVAL:
                action = nav_hold["direction"]
                nav_hold["last_fire"] = now
                action_state["last_action"] = action
                action_state["last_time"] = now

        try:
            while True:
                msg_type, payload = ui_queue.get_nowait()
                if msg_type == "status":
                    trade_status = payload
                    logger.info("QUEUE status: %s", payload)
                elif msg_type == "screen":
                    logger.info("QUEUE screen: %s", payload)
                    switch_screen(payload, "ui_queue")
                elif msg_type == "confirm_prompt":
                    result_data = payload if isinstance(payload, dict) else {}
                    logger.info("QUEUE confirm_prompt: %s", result_data)
                    switch_screen("trade_confirm", "confirm_prompt")
                elif msg_type == "info_modal":
                    data = payload if isinstance(payload, dict) else {}
                    info_modal_data = {"title": data.get("title", ""), "message": data.get("message", "")}
                    logger.info("QUEUE info_modal: %s", info_modal_data)
                    switch_screen("info_modal", "info_modal_prompt")
                elif msg_type == "resolve_moves_prompt":
                    data = payload if isinstance(payload, dict) else {}
                    pending_removed_moves = list(data.get("removed_moves") or [])
                    resolve_current_idx = 0
                    resolve_replacement_idx = 0
                    resolved_moves_choices = {}
                    logger.info("QUEUE resolve_moves_prompt: %s moves", len(pending_removed_moves))
                    if pending_removed_moves:
                        switch_screen("resolve_moves", "resolve_moves_prompt")
                    else:
                        confirm_queue.put({})
                elif msg_type == "evolution_cancel_prompt":
                    result_data = payload if isinstance(payload, dict) else {}
                    logger.info("QUEUE evolution_cancel_prompt: %s", result_data)
                    evolution_anim_start = frame
                    switch_screen("evolution_cancel_prompt", "evolution_cancel_prompt")
                elif msg_type == "result":
                    result_data = payload if isinstance(payload, dict) else {"success": True}
                    logger.info("QUEUE result: %s", result_data)
                    switch_screen("trade_result", "result")
                elif msg_type == "error":
                    trade_status = f"Erro: {payload}"
                    result_data = {"success": False, "error": payload}
                    logger.error("QUEUE error: %s", payload)
                    switch_screen("trade_result", "error")
        except queue.Empty:
            pass

        in_room_selection = bool(trade_thread and trade_thread.is_alive() and state.room_name)
        if action:
            logger.debug("ACTION screen=%s action=%s menu=%s room=%s", current_screen, action, menu_index, state.room_name)
        if action == "quit_system":
            logger.info("Global quit requested by Start+Select")
            running = False
            continue

        if current_screen == "menu" and action:
            if action == "up":
                menu_index = (menu_index - 1) % 4
            elif action == "down":
                menu_index = (menu_index + 1) % 4
            elif action == "select":
                if menu_index == 0:
                    reset_flow_state(state)
                    state.find_saves()
                    logger.info("Menu select: access room")
                    switch_screen("load_save", "menu_access_room")
                    menu_index = 0
                elif menu_index == 1:
                    reset_flow_state(state)
                    reset_self_trade_state()
                    state.find_saves()
                    logger.info("Menu select: self trade")
                    switch_screen("self_select_save_a", "menu_self_trade")
                    menu_index = 0
                elif menu_index == 2:
                    logger.info("Menu select: config")
                    switch_screen("config", "menu_config")
                    menu_index = 0
                elif menu_index == 3:
                    logger.info("Menu select: exit")
                    running = False
            elif action == "back":
                logger.info("Menu back: exit")
                running = False

        elif current_screen == "config" and action:
            if action == "up":
                menu_index = (menu_index - 1) % 2
            elif action == "down":
                menu_index = (menu_index + 1) % 2
            elif action in ("left", "right"):
                if menu_index == 0:
                    order = ["pt", "en", "es"]
                    index = order.index(state.language) if state.language in order else 0
                    direction = -1 if action == "left" else 1
                    state.language = order[(index + direction) % len(order)]
                    config_dirty = True
                else:
                    state.theme = "pokedex_white" if state.theme == "pokedex_dark" else "pokedex_dark"
                    apply_theme(state.theme)
                    config_dirty = True
            elif action == "select":
                state.save_ui_config(state.language, state.theme)
                config_dirty = False
                switch_screen("menu", "config_saved")
                menu_index = 0
            elif action == "back":
                if config_dirty:
                    state.save_ui_config(state.language, state.theme)
                    config_dirty = False
                switch_screen("menu", "back_from_config")
                menu_index = 0

        elif current_screen == "load_save" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(max(0, len(state.saves) - 1), menu_index + 1)
            elif action == "select" and state.saves:
                state.selected_save = state.saves[menu_index]
                state.selected_pokemon = None
                state.pokemon_list = []
                logger.info("Save selected: %s", state.selected_save)
                switch_screen("enter_room_name", "save_selected")
                keyboard_index = 0
                keyboard_shift = False
                room_name = random_room_name()
                menu_index = 0
            elif action == "back":
                switch_screen("menu", "back_from_load_save")
                menu_index = 0

        elif current_screen == "self_select_save_a" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(max(0, len(state.saves) - 1), menu_index + 1)
            elif action == "select" and state.saves:
                self_trade_save_a = state.saves[menu_index]
                logger.info("Self trade save A selected: %s", self_trade_save_a)
                switch_screen("self_select_save_b", "self_save_a_selected")
                menu_index = 0
            elif action == "back":
                reset_self_trade_state()
                switch_screen("menu", "back_from_self_save_a")
                menu_index = 0

        elif current_screen == "self_select_save_b" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(max(0, len(state.saves) - 1), menu_index + 1)
            elif action == "select" and state.saves:
                candidate = state.saves[menu_index]
                if same_save_path(self_trade_save_a, candidate):
                    info_modal_data = {
                        "title": "Save repetido",
                        "message": "Escolha dois arquivos de save diferentes para trocar comigo.",
                        "return_screen": "self_select_save_b",
                    }
                    switch_screen("info_modal", "self_same_save_blocked")
                else:
                    self_trade_save_b = candidate
                    logger.info("Self trade save B selected: %s", self_trade_save_b)
                    try:
                        load_self_trade_party(self_trade_save_a)
                        switch_screen("self_select_pokemon_a", "self_save_b_selected")
                        menu_index = 0
                    except Exception as exc:
                        logger.exception("Failed to load self trade party A: %s", exc)
                        info_modal_data = {
                            "title": "Falha ao carregar Party",
                            "message": str(exc),
                            "return_screen": "self_select_save_a",
                        }
                        switch_screen("info_modal", "self_party_a_failed")
            elif action == "back":
                self_trade_save_b = None
                switch_screen("self_select_save_a", "back_from_self_save_b")
                menu_index = 0

        elif current_screen == "self_select_pokemon_a" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(max(0, len(state.pokemon_list) - 1), menu_index + 1)
            elif action == "select" and state.pokemon_list:
                self_trade_pokemon_a = state.pokemon_list[menu_index]
                logger.info("Self trade pokemon A selected: %s", self_trade_pokemon_a.get("location"))
                try:
                    load_self_trade_party(self_trade_save_b)
                    switch_screen("self_select_pokemon_b", "self_pokemon_a_selected")
                    menu_index = 0
                except Exception as exc:
                    logger.exception("Failed to load self trade party B: %s", exc)
                    info_modal_data = {
                        "title": "Falha ao carregar Party",
                        "message": str(exc),
                        "return_screen": "self_select_save_b",
                    }
                    switch_screen("info_modal", "self_party_b_failed")
            elif action == "back":
                self_trade_pokemon_a = None
                switch_screen("self_select_save_b", "back_from_self_pokemon_a")
                menu_index = 0

        elif current_screen == "self_select_pokemon_b" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(max(0, len(state.pokemon_list) - 1), menu_index + 1)
            elif action == "select" and state.pokemon_list:
                self_trade_pokemon_b = state.pokemon_list[menu_index]
                logger.info("Self trade pokemon B selected: %s", self_trade_pokemon_b.get("location"))
                try:
                    preview = validate_self_trade_candidate(
                        state,
                        source_save_path=Path(self_trade_save_b),
                        source_pokemon_location=str(self_trade_pokemon_b.get("location") or "party:0"),
                        target_save_path=Path(self_trade_save_a),
                    )
                except Exception as exc:
                    logger.exception("Self trade candidate validation failed: %s", exc)
                    info_modal_data = {
                        "title": "Falha na validacao",
                        "message": str(exc),
                        "return_screen": "self_select_pokemon_b",
                    }
                    switch_screen("info_modal", "self_candidate_validation_failed")
                    continue
                if not preview.get("compatible"):
                    message = str(preview.get("blocking_message") or "Pokemon incompativel com o save de destino.")
                    info_modal_data = {
                        "title": "Pokemon incompativel",
                        "message": message,
                        "return_screen": "self_select_pokemon_b",
                    }
                    switch_screen("info_modal", "self_candidate_incompatible")
                    continue
                trade_status = "Validando troca local..."
                switch_screen("trading", "self_trade_preflight")
                try:
                    self_trade_context = prepare_self_trade(
                        state,
                        self_trade_save_a,
                        str(self_trade_pokemon_a.get("location") or "party:0"),
                        self_trade_save_b,
                        str(self_trade_pokemon_b.get("location") or "party:0"),
                    )
                    advance_self_trade_prompts()
                except Exception as exc:
                    logger.exception("Self trade preflight failed: %s", exc)
                    info_modal_data = {
                        "title": "Troca incompativel",
                        "message": str(exc),
                        "return_screen": "self_select_pokemon_b",
                    }
                    switch_screen("info_modal", "self_preflight_failed")
            elif action == "back":
                self_trade_pokemon_b = None
                try:
                    load_self_trade_party(self_trade_save_a)
                except Exception:
                    pass
                switch_screen("self_select_pokemon_a", "back_from_self_pokemon_b")
                menu_index = 0

        elif current_screen == "select_pokemon_source" and action:
            if action in ("up", "down", "y"):
                menu_index = (menu_index + (1 if action != "up" else -1)) % 2
            elif action == "select":
                state.pokemon_source = "party" if menu_index == 0 else "boxes"
                try:
                    state.get_pokemon_list(state.pokemon_source)
                except SaveError as exc:
                    logger.error("Pokemon enrichment failed: %s", exc)
                    info_modal_data = {
                        "title": "Falha ao carregar Pokemon",
                        "message": str(exc),
                        "return_screen": "select_pokemon_source",
                    }
                    switch_screen("info_modal", "api_enrichment_failed")
                    continue
                logger.info("Pokemon source selected: %s count=%s", state.pokemon_source, len(state.pokemon_list))
                switch_screen("select_pokemon", "pokemon_source_selected")
                menu_index = 0
            elif action == "back":
                if in_room_selection:
                    switch_screen("leave_room_confirm", "leave_from_source")
                else:
                    switch_screen("load_save", "back_from_source")
                menu_index = 0

        elif current_screen == "select_pokemon" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(max(0, len(state.pokemon_list) - 1), menu_index + 1)
            elif action == "select" and state.pokemon_list:
                if state.pokemon_source != "party":
                    info_modal_data = {
                        "title": "Pokemon esta no PC",
                        "message": "Pressione X para retirar este Pokemon para a Party antes de troca-lo.",
                        "return_screen": "select_pokemon",
                    }
                    switch_screen("info_modal", "select_from_pc_blocked")
                else:
                    state.selected_pokemon = state.pokemon_list[menu_index]
                    logger.info("Pokemon selected: %s location=%s", state.selected_pokemon.get("display"), state.selected_pokemon.get("location"))
                    trade_status = f"Pokemon selecionado: {state.selected_pokemon.get('display', 'Pokemon')}"
                    switch_screen("waiting_partner" if in_room_selection else "enter_room_name", "pokemon_selected")
            elif action == "x" and state.pokemon_list:
                if state.trade_phase not in ("idle", "waiting"):
                    trade_status = "Aguarde a troca terminar antes de mover."
                elif state.pokemon_source == "party":
                    pending_deposit_idx = menu_index
                    logger.info("Deposit requested for party slot %s", pending_deposit_idx)
                    switch_screen("deposit_confirm", "deposit_request")
                else:
                    pending_withdraw_pokemon = state.pokemon_list[menu_index]
                    logger.info("Withdraw requested for %s", pending_withdraw_pokemon.get("location"))
                    switch_screen("withdraw_confirm", "withdraw_request")
            elif action == "y":
                new_source = "boxes" if state.pokemon_source == "party" else "party"
                try:
                    state.pokemon_source = new_source
                    state.get_pokemon_list(new_source)
                    menu_index = 0
                    logger.info("Toggled source -> %s (%s entries)", new_source, len(state.pokemon_list))
                except SaveError as exc:
                    logger.error("Source toggle failed: %s", exc)
                    info_modal_data = {
                        "title": "Erro",
                        "message": str(exc),
                        "return_screen": "select_pokemon",
                    }
                    switch_screen("info_modal", "source_toggle_failed")
            elif action == "back":
                if in_room_selection:
                    switch_screen("select_pokemon_source", "back_to_source")
                else:
                    switch_screen("load_save", "back_from_pokemon")
                menu_index = 0

        elif current_screen == "enter_room_name" and action:
            max_key_index = keyboard_limits(keyboard_shift)
            char_count = len(keyboard_chars(keyboard_shift))
            if action == "up":
                keyboard_index = max(0, keyboard_index - KEYBOARD_GRID_W)
            elif action == "down":
                keyboard_index = min(max_key_index, keyboard_index + KEYBOARD_GRID_W)
            elif action == "left":
                keyboard_index = max(0, keyboard_index - 1)
            elif action == "right":
                keyboard_index = min(max_key_index, keyboard_index + 1)
            elif action == "select":
                if keyboard_index == char_count:
                    room_name = room_name[:-1]
                elif keyboard_index == char_count + 1:
                    keyboard_shift = not keyboard_shift
                    keyboard_index = min(keyboard_index, keyboard_limits(keyboard_shift))
                elif keyboard_index == char_count + 2:
                    room_name += " "
                elif keyboard_index == char_count + 3:
                    if room_name:
                        logger.info("Room name submitted: %s", room_name)
                        switch_screen("enter_password", "room_name_submitted")
                        keyboard_index = 0
                        keyboard_shift = False
                        room_password = ""
                else:
                    chars = keyboard_chars(keyboard_shift)
                    if keyboard_index < len(chars):
                        room_name += chars[keyboard_index]
            elif action == "back":
                if room_name:
                    room_name = room_name[:-1]
                else:
                    switch_screen("load_save", "back_from_room_name")
                    menu_index = 0

        elif current_screen == "enter_password" and action:
            max_key_index = keyboard_limits(keyboard_shift)
            char_count = len(keyboard_chars(keyboard_shift))
            if action == "up":
                keyboard_index = max(0, keyboard_index - KEYBOARD_GRID_W)
            elif action == "down":
                keyboard_index = min(max_key_index, keyboard_index + KEYBOARD_GRID_W)
            elif action == "left":
                keyboard_index = max(0, keyboard_index - 1)
            elif action == "right":
                keyboard_index = min(max_key_index, keyboard_index + 1)
            elif action == "select":
                if keyboard_index == char_count:
                    room_password = room_password[:-1]
                elif keyboard_index == char_count + 1:
                    keyboard_shift = not keyboard_shift
                    keyboard_index = min(keyboard_index, keyboard_limits(keyboard_shift))
                elif keyboard_index == char_count + 2:
                    room_password += " "
                elif keyboard_index == char_count + 3:
                    if room_name and room_password:
                        state.room_name = room_name
                        state.room_password = room_password
                        state.selected_pokemon = None
                        state.pokemon_list = []
                        logger.info("Starting trade: room=%s password_len=%s action=%s", state.room_name, len(state.room_password), state.action)
                        trade_thread = start_trade_thread(state, state.action or "access", ui_queue, confirm_queue)
                        switch_screen("connecting", "trade_thread_started")
                        trade_status = "Conectando..."
                else:
                    chars = keyboard_chars(keyboard_shift)
                    if keyboard_index < len(chars):
                        room_password += chars[keyboard_index]
            elif action == "back":
                if room_password:
                    room_password = room_password[:-1]
                else:
                    switch_screen("enter_room_name", "back_from_password")
                    keyboard_index = 0

        elif current_screen == "self_trade_confirm" and action:
            if action == "select":
                logger.info("Self trade confirmation accepted")
                finish_self_trade()
            elif action == "back":
                logger.info("Self trade confirmation declined")
                result_data = {}
                trade_status = "Troca local cancelada."
                reset_self_trade_state()
                reset_flow_state(state)
                switch_screen("menu", "self_trade_confirm_no")
                menu_index = 0

        elif current_screen == "trade_confirm" and action:
            if action == "select":
                logger.info("Trade confirmation accepted")
                confirm_queue.put(True)
                switch_screen("trading", "trade_confirm_yes")
            elif action == "back":
                logger.info("Trade confirmation declined")
                confirm_queue.put(False)
                switch_screen("menu", "trade_confirm_no")
                menu_index = 0
                result_data = {}
                reset_flow_state(state)

        elif current_screen == "info_modal" and action in ("select", "back"):
            logger.info("Info modal acknowledged")
            return_screen = info_modal_data.get("return_screen") if isinstance(info_modal_data, dict) else ""
            info_modal_data = {"title": "", "message": ""}
            if return_screen:
                switch_screen(return_screen, "info_modal_ack")
            else:
                confirm_queue.put(True)

        elif current_screen == "resolve_moves" and action and pending_removed_moves:
            current_move = pending_removed_moves[resolve_current_idx]
            chosen_set = set(int(x) for x in resolved_moves_choices.values() if x)
            replacements = [
                r for r in (current_move.get("valid_replacements") or [])
                if int(r.get("move_id") or 0) not in chosen_set
            ]
            total_options = len(replacements) + 1
            if action == "up":
                resolve_replacement_idx = (resolve_replacement_idx - 1) % total_options
            elif action == "down":
                resolve_replacement_idx = (resolve_replacement_idx + 1) % total_options
            elif action in ("select", "back"):
                if action == "select" and resolve_replacement_idx < len(replacements):
                    move_id = int(current_move.get("move_id") or 0)
                    replacement_id = int(replacements[resolve_replacement_idx].get("move_id") or 0)
                    if move_id and replacement_id:
                        resolved_moves_choices[move_id] = replacement_id
                resolve_current_idx += 1
                resolve_replacement_idx = 0
                if resolve_current_idx >= len(pending_removed_moves):
                    logger.info("Move resolution complete: %s", resolved_moves_choices)
                    if self_trade_pending_decision in ("resolved_moves_to_a", "resolved_moves_to_b"):
                        self_trade_decisions[self_trade_pending_decision] = dict(resolved_moves_choices)
                        self_trade_pending_decision = ""
                        pending_removed_moves = []
                        advance_self_trade_prompts()
                    else:
                        confirm_queue.put(dict(resolved_moves_choices))
                        pending_removed_moves = []

        elif current_screen == "evolution_cancel_prompt" and action:
            if time.monotonic() < evolution_prompt_input_unlock_until:
                continue
            if action == "select":
                logger.info("Evolution cancellation skipped (A = let evolve)")
                if self_trade_pending_decision in ("cancel_evolution_to_a", "cancel_evolution_to_b"):
                    self_trade_decisions[self_trade_pending_decision] = False
                    self_trade_pending_decision = ""
                    switch_screen("trading", "self_evolution_cancel_no")
                    advance_self_trade_prompts()
                else:
                    confirm_queue.put(False)
                    switch_screen("trading", "evolution_cancel_no")
            elif action == "back":
                logger.info("Evolution cancellation requested (B = interrupt)")
                switch_screen("evolution_cancel_confirm", "evolution_cancel_requested")

        elif current_screen == "evolution_cancel_confirm" and action:
            if time.monotonic() < evolution_prompt_input_unlock_until:
                continue
            if action == "select":
                logger.info("Evolution cancellation rejected (A = let evolve)")
                if self_trade_pending_decision in ("cancel_evolution_to_a", "cancel_evolution_to_b"):
                    self_trade_decisions[self_trade_pending_decision] = False
                    self_trade_pending_decision = ""
                    switch_screen("trading", "self_evolution_cancel_rejected")
                    advance_self_trade_prompts()
                else:
                    confirm_queue.put(False)
                    switch_screen("trading", "evolution_cancel_rejected")
            elif action == "back":
                logger.info("Evolution cancellation confirmed (B = interrupt)")
                if self_trade_pending_decision in ("cancel_evolution_to_a", "cancel_evolution_to_b"):
                    self_trade_decisions[self_trade_pending_decision] = True
                    self_trade_pending_decision = ""
                    switch_screen("trading", "self_evolution_cancel_yes")
                    advance_self_trade_prompts()
                else:
                    confirm_queue.put(True)
                    switch_screen("trading", "evolution_cancel_yes")

        elif current_screen == "withdraw_confirm" and action:
            if action == "select":
                save_model = state.get_selected_save_model()
                if not save_model or not pending_withdraw_pokemon:
                    info_modal_data = {
                        "title": "Erro",
                        "message": "Slot do PC nao encontrado.",
                        "return_screen": "select_pokemon",
                    }
                    switch_screen("info_modal", "withdraw_no_target")
                else:
                    try:
                        _create_backup(state.selected_save)
                        location = str(pending_withdraw_pokemon.get("location") or "")
                        parts = location.split(":")
                        if len(parts) >= 3 and parts[0] == "box":
                            box_idx = int(parts[1])
                            slot_idx = int(parts[2])
                        else:
                            box_idx = int(pending_withdraw_pokemon.get("box_index") or 0)
                            slot_idx = int(pending_withdraw_pokemon.get("slot_index") or 0)
                        logger.info("Withdraw target: location=%s box=%s slot=%s", location, box_idx, slot_idx)
                        result = save_model.withdraw_box_to_party(box_idx, slot_idx)
                        save_model.write_to_disk()
                        state.expected_signature = save_model.signature()
                        state.refresh_selected_save()
                        state.get_pokemon_list(state.pokemon_source or "boxes")
                        trade_status = f"{result.get('species_name', 'Pokemon')} agora esta na Party."
                        menu_index = min(menu_index, max(0, len(state.pokemon_list) - 1))
                        switch_screen("select_pokemon", "withdraw_done")
                    except Exception as exc:
                        logger.exception("Withdraw failed: %s", exc)
                        info_modal_data = {
                            "title": "Nao foi possivel retirar",
                            "message": str(exc),
                            "return_screen": "select_pokemon",
                        }
                        switch_screen("info_modal", "withdraw_failed")
                pending_withdraw_pokemon = None
            elif action == "back":
                pending_withdraw_pokemon = None
                switch_screen("select_pokemon", "withdraw_aborted")

        elif current_screen == "deposit_confirm" and action:
            if action == "select":
                save_model = state.get_selected_save_model()
                if not save_model:
                    info_modal_data = {
                        "title": "Erro",
                        "message": "Save nao carregado.",
                        "return_screen": "select_pokemon",
                    }
                    switch_screen("info_modal", "deposit_no_save")
                else:
                    try:
                        _create_backup(state.selected_save)
                        result = save_model.deposit_party_to_pc(pending_deposit_idx)
                        save_model.write_to_disk()
                        state.expected_signature = save_model.signature()
                        state.refresh_selected_save()
                        state.get_pokemon_list("party")
                        trade_status = f"{result.get('species_name', 'Pokemon')} movido para o PC."
                        menu_index = min(menu_index, max(0, len(state.pokemon_list) - 1))
                        switch_screen("select_pokemon", "deposit_done")
                    except Exception as exc:
                        logger.exception("Deposit failed: %s", exc)
                        info_modal_data = {
                            "title": "Nao foi possivel mover",
                            "message": str(exc),
                            "return_screen": "select_pokemon",
                        }
                        switch_screen("info_modal", "deposit_failed")
                pending_deposit_idx = -1
            elif action == "back":
                pending_deposit_idx = -1
                switch_screen("select_pokemon", "deposit_aborted")

        elif current_screen == "waiting_partner" and action == "back":
            logger.info("Cancel from waiting_partner requested")
            switch_screen("cancel_waiting_confirm", "cancel_requested")

        elif current_screen == "cancel_waiting_confirm" and action:
            if action == "select":
                ok = request_trade_cancel(state)
                logger.info("Cancel from waiting confirmed: scheduled=%s", ok)
                if ok:
                    trade_status = "Cancelando..."
                    switch_screen("waiting_partner", "cancel_pending")
                else:
                    trade_status = "Nao foi possivel cancelar agora."
                    switch_screen("waiting_partner", "cancel_failed")
            elif action == "back":
                logger.info("Cancel from waiting aborted")
                switch_screen("waiting_partner", "cancel_aborted")

        elif current_screen == "leave_room_confirm" and action:
            if action == "select":
                logger.info("Leave room confirmed")
                request_leave_room(state)
                trade_status = "Saindo da sala..."
                switch_screen("menu", "leave_room_yes")
                menu_index = 0
                reset_flow_state(state)
            elif action == "back":
                logger.info("Leave room aborted")
                switch_screen("select_pokemon_source", "leave_room_no")

        elif current_screen == "trade_result" and action in ("select", "back"):
            logger.info("Trade result acknowledged: %s", result_data)
            success = bool(isinstance(result_data, dict) and result_data.get("success"))
            staying_in_room = success and trade_thread and trade_thread.is_alive()
            result_data = {}
            trade_status = ""
            menu_index = 0
            if staying_in_room:
                switch_screen("select_pokemon_source", "trade_result_ack_continue")
            else:
                switch_screen("menu", "trade_result_ack")
                reset_flow_state(state)
                reset_self_trade_state()

        if current_screen == "menu":
            draw_menu(screen, fonts, menu_index, state.language)
        elif current_screen == "config":
            draw_config_menu(screen, fonts, menu_index, state.language, state.theme)
        elif current_screen == "load_save":
            draw_select_save(screen, fonts, menu_index, state.saves)
        elif current_screen == "self_select_save_a":
            draw_select_save(screen, fonts, menu_index, state.saves, "Trocar comigo: Save 1")
        elif current_screen == "self_select_save_b":
            draw_select_save(screen, fonts, menu_index, state.saves, "Trocar comigo: Save 2")
        elif current_screen == "self_select_pokemon_a":
            label = f"Party Save 1: {Path(self_trade_save_a).name}" if self_trade_save_a else "Party Save 1"
            draw_select_pokemon(screen, fonts, menu_index, state.pokemon_list, label, sprite_loader, trade_status, False)
        elif current_screen == "self_select_pokemon_b":
            label = f"Party Save 2: {Path(self_trade_save_b).name}" if self_trade_save_b else "Party Save 2"
            draw_select_pokemon(screen, fonts, menu_index, state.pokemon_list, label, sprite_loader, trade_status, False)
        elif current_screen == "select_pokemon_source":
            draw_select_pokemon_source(screen, fonts, menu_index, trade_status, state.room_name or room_name, state.room_password or room_password)
        elif current_screen == "select_pokemon":
            source_label = "Sua Party" if state.pokemon_source == "party" else "Seu PC"
            draw_select_pokemon(screen, fonts, menu_index, state.pokemon_list, source_label, sprite_loader, trade_status)
        elif current_screen == "enter_room_name":
            draw_keyboard(screen, fonts, "Nome da Sala", room_name, keyboard_index, False, keyboard_shift)
        elif current_screen == "enter_password":
            draw_keyboard(screen, fonts, "Senha", room_password, keyboard_index, True, keyboard_shift)
        elif current_screen == "connecting":
            draw_connecting(screen, fonts, frame)
        elif current_screen == "waiting_partner":
            draw_waiting_partner(screen, fonts, trade_status)
        elif current_screen == "cancel_waiting_confirm":
            draw_cancel_waiting_confirm(screen, fonts)
        elif current_screen == "leave_room_confirm":
            draw_leave_room_confirm(screen, fonts)
        elif current_screen == "self_trade_confirm":
            draw_trade_confirm(
                screen,
                fonts,
                self_trade_pokemon_a or {},
                self_trade_context.get("payload_b", {}) if isinstance(self_trade_context, dict) else {},
                sprite_loader,
            )
        elif current_screen == "trade_confirm":
            draw_trade_confirm(
                screen,
                fonts,
                state.selected_pokemon or {},
                result_data if isinstance(result_data, dict) else {},
                sprite_loader,
            )
        elif current_screen == "info_modal":
            draw_info_modal(screen, fonts, info_modal_data.get("title", ""), info_modal_data.get("message", ""))
        elif current_screen == "deposit_confirm":
            target_pokemon = None
            if 0 <= pending_deposit_idx < len(state.pokemon_list):
                target_pokemon = state.pokemon_list[pending_deposit_idx]
            draw_deposit_confirm(screen, fonts, target_pokemon or {})
        elif current_screen == "withdraw_confirm":
            draw_withdraw_confirm(screen, fonts, pending_withdraw_pokemon or {})
        elif current_screen == "resolve_moves" and pending_removed_moves:
            draw_resolve_moves(
                screen,
                fonts,
                pending_removed_moves[resolve_current_idx],
                resolve_replacement_idx,
                resolve_current_idx,
                len(pending_removed_moves),
                set(resolved_moves_choices.values()),
            )
        elif current_screen == "evolution_cancel_prompt":
            anim_frame = max(0, frame - (evolution_anim_start if evolution_anim_start is not None else frame))
            draw_evolution_cancel_prompt(screen, fonts, result_data if isinstance(result_data, dict) else {}, sprite_loader, anim_frame)
        elif current_screen == "evolution_cancel_confirm":
            draw_evolution_cancel_confirm(screen, fonts, result_data if isinstance(result_data, dict) else {}, sprite_loader, frame)
        elif current_screen == "trading":
            draw_trading(screen, fonts, trade_status)
        elif current_screen == "trade_result":
            success = bool(isinstance(result_data, dict) and result_data.get("success"))
            data = result_data if success else result_data.get("error", trade_status) if isinstance(result_data, dict) else trade_status
            draw_trade_result(screen, fonts, success, data)

        lowered_status = trade_status.lower()
        show_footer_status = (
            trade_status
            and not lowered_status.startswith("aguardando")
            and not lowered_status.startswith("sala pronta")
            and "escolha pokemon" not in lowered_status
            and "escolha o pokemon" not in lowered_status
            and "escolha o seu" not in lowered_status
        )
        if show_footer_status and current_screen in ("load_save", "select_pokemon_source", "select_pokemon"):
            text(screen, fonts[3], trade_status, 20, SCREEN_H - 78, WARN, SCREEN_W - 40)

        pygame.display.flip()
        clock.tick(30)

    if trade_thread and trade_thread.is_alive():
        trade_thread.join(timeout=2)
    pygame.quit()
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as exc:
        logger.exception(f"Fatal error: {exc}")
        print(f"\nErro fatal. Veja {ERROR_LOG}.", file=sys.stderr)
        sys.exit(1)
