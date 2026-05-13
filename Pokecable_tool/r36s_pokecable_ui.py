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
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

DEBUG = os.getenv("POKECABLE_DEBUG", "0").lower() in ("1", "true", "yes")

try:
    import pygame
except ImportError:
    print("pygame required: run ./pokecable.sh", file=sys.stderr)
    sys.exit(1)

from pokecable_logging import configure_logging
from pokecable_save import SaveError
from r36s_pokecable_core import PokecableState, start_trade_thread


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
ACTION_DEBOUNCE = 0.14
QUIT_COMBO_WINDOW = 0.35
JOY_BUTTON_START = 13
JOY_BUTTON_SELECT = 12
ROW_H = 45
ROW_VISIBLE = 8

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

SPRITE_CACHE_DIR = Path.home() / ".pokecable" / "sprites"
SPRITE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
    if names:
        return [str(name) for name in names[:4] if name]
    moves = (pokemon or {}).get("moves") or raw.get("moves") or []
    labels = []
    for move_id in moves[:4]:
        if not move_id:
            continue
        move_id = int(move_id)
        labels.append(f"Move #{move_id}")
    return labels


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


class SpriteLoader:
    def __init__(self, server_url: str):
        self.lock = threading.Lock()
        self.http_base_url = self._http_base_url(server_url)
        self.current_key = ""
        self.entries = {}

    @staticmethod
    def _http_base_url(server_url: str) -> str:
        candidate = (server_url or "").strip()
        if not candidate:
            return ""
        if candidate.startswith("ws://"):
            return "http://" + candidate[len("ws://"):].rstrip("/")
        if candidate.startswith("wss://"):
            return "https://" + candidate[len("wss://"):].rstrip("/")
        parsed = urlparse(candidate)
        if parsed.scheme in {"http", "https"}:
            return candidate.rstrip("/")
        return ""

    def _identity(self, pokemon):
        species_name = pokemon.get("species_name") if pokemon else ""
        species_id = int((pokemon or {}).get("species_id") or 0)
        if not pokemon or (not species_name and not species_id) or species_name.lower() == "egg":
            return "", {}

        generation = int((pokemon or {}).get("generation") or 0)
        raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
        national_dex_id = int((pokemon or {}).get("national_dex_id") or raw.get("national_dex_id") or 0)
        slug = pokemon_sprite_slug(species_name)
        if not slug and not national_dex_id:
            return "", {}
        key = f"national-{national_dex_id or slug}-front"
        lookup = {
            "generation": generation,
            "species_slug": slug,
            "species_id": species_id,
            "national_dex_id": national_dex_id,
        }
        return key, lookup

    def request(self, pokemon):
        self.request_for(pokemon)

    def request_for(self, pokemon):
        species_name = pokemon.get("species_name") if pokemon else ""
        species_id = int((pokemon or {}).get("species_id") or 0)
        logger.debug("Sprite request: species_id=%s species_name=%s", species_id, species_name)
        key, lookup = self._identity(pokemon)
        with self.lock:
            self.current_key = key
            if not key:
                return
            entry = self.entries.get(key)
            if entry and (entry.get("loading") or entry.get("surface") is not None):
                return
            self.entries[key] = {"surface": None, "loading": True, "error": ""}
        threading.Thread(target=self._load, args=(key, lookup), daemon=True).start()

    def _sprite_urls(self, lookup):
        generation = int(lookup.get("generation") or 0)
        species_slug = str(lookup.get("species_slug") or "")
        national_dex_id = int(lookup.get("national_dex_id") or 0)
        urls = []
        if national_dex_id:
            urls.append(f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{national_dex_id}.png")
        if self.http_base_url and generation and species_slug:
            urls.append(f"{self.http_base_url}/sprites/{generation}/{species_slug}/front.png")
        if species_slug:
            urls.append(f"https://img.pokemondb.net/sprites/home/normal/{species_slug}.png")
        return urls

    def _load(self, key, lookup):
        try:
            cache_file = SPRITE_CACHE_DIR / f"{key}.png"
            if not cache_file.exists():
                logger.debug("Sprite cache miss: key=%s", key)
                errors = []
                for sprite_url in self._sprite_urls(lookup):
                    try:
                        request = urllib.request.Request(sprite_url, headers={"User-Agent": "PokeCable/1.0"})
                        with urllib.request.urlopen(request, timeout=8) as response:
                            cache_file.write_bytes(response.read())
                        logger.info("Sprite downloaded: key=%s url=%s", key, sprite_url)
                        break
                    except Exception as exc:
                        errors.append(f"{sprite_url}: {exc}")
                        logger.debug("Sprite source failed: key=%s url=%s error=%s", key, sprite_url, exc)
                if not cache_file.exists():
                    raise RuntimeError("; ".join(errors) or "no sprite URL available")
            surface = pygame.image.load(str(cache_file)).convert_alpha()
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
            return entry.get("surface"), bool(entry.get("loading")), str(entry.get("error") or "")


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

    items = [t(language, "menu_access_room"), t(language, "menu_config"), t(language, "menu_exit")]
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
    return f"{random.choice(POKEMON_ROOM_NAMES)}-{random.randint(10, 99)}"


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
    key_w, key_h = 48, 34
    start_x, start_y = 18, HEADER_H + 74

    for idx, char in enumerate(chars):
        col, row = idx % KEYBOARD_GRID_W, idx // KEYBOARD_GRID_W
        x, y = start_x + col * key_w, start_y + row * key_h
        selected = idx == grid_index
        key_rect = pygame.Rect(x, y, key_w - 6, key_h - 5)
        rect(screen, ACCENT if selected else PANEL_2, key_rect, 5)
        text(screen, tiny_f, char, key_rect.x + 6, key_rect.y + 8, (5, 11, 18) if selected else TEXT)

    specials_row = math.ceil(len(chars) / KEYBOARD_GRID_W)
    special_start = len(chars)
    specials = [("DEL", special_start), ("SHIFT", special_start + 1), ("SPACE", special_start + 2), ("OK", special_start + 3)]
    for offset, (label, idx) in enumerate(specials):
        x = start_x + offset * (key_w * 2)
        y = start_y + specials_row * key_h + 8
        selected = idx == grid_index
        key_rect = pygame.Rect(x, y, key_w * 2 - 12, key_h - 3)
        rect(screen, ACCENT if selected else PANEL_2, key_rect, 5)
        text(screen, tiny_f, label, key_rect.x + 8, key_rect.y + 8, (5, 11, 18) if selected else TEXT)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SELECT", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "DEL/VOLTAR", 112, SCREEN_H - 48)


def draw_select_save(screen, fonts, selected, saves):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Select Save", 14, 10)

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


def draw_select_pokemon_source(screen, fonts, selected, status=""):
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

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)


def draw_select_pokemon(screen, fonts, selected, pokemon_list, source_label, sprite_loader, status=""):
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
    text(screen, tiny_f, "Aguarde...", 250, SCREEN_H - 45, MUTED)


def draw_trade_confirm(screen, fonts, my_pokemon, opponent_pokemon, sprite_loader):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Confirmar Troca", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)

    mine = my_pokemon.get("display") or my_pokemon.get("display_summary") or "???"
    peer = opponent_pokemon.get("display_summary") or opponent_pokemon.get("nickname") or opponent_pokemon.get("species_name") or "???"

    my_entry = {
        "generation": int(my_pokemon.get("generation") or 0),
        "species_id": int(my_pokemon.get("species_id") or 0),
        "species_name": my_pokemon.get("species_name") or "Pokemon",
    }
    peer_entry = {
        "generation": int(opponent_pokemon.get("generation") or opponent_pokemon.get("source_generation") or 0),
        "species_id": int(opponent_pokemon.get("species_id") or 0),
        "species_name": opponent_pokemon.get("species_name") or "Pokemon",
    }
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
    return {
        "generation": int(evolution.get("generation") or 0),
        "species_id": int(evolution.get(f"{side}_species_id") or 0),
        "species_name": evolution.get(f"{side}_name") or "Pokemon",
    }


def draw_scaled_sprite(surface, sprite, center, size, alpha=255):
    if not sprite:
        return
    scaled = pygame.transform.smoothscale(sprite, (size, size)).convert_alpha()
    scaled.set_alpha(max(0, min(255, int(alpha))))
    surface.blit(scaled, (center[0] - size // 2, center[1] - size // 2))


def draw_evolution_animation(screen, fonts, evolution, sprite_loader, frame, final_form="loop"):
    _, _, small_f, tiny_f = fonts
    source = evolution_sprite_entry(evolution, "source")
    target = evolution_sprite_entry(evolution, "target")
    sprite_loader.request_for(source)
    sprite_loader.request_for(target)
    source_sprite, source_loading, _ = sprite_loader.snapshot_for(source)
    target_sprite, target_loading, _ = sprite_loader.snapshot_for(target)

    stage = pygame.Rect(190, HEADER_H + 44, 260, 142)
    rect(screen, BG, stage, 8)
    progress = (math.sin(frame * 0.16) + 1.0) / 2.0
    if final_form == "source":
        progress = 0.0
    elif final_form == "target":
        progress = 1.0

    glow = int(65 + 70 * progress)
    pygame.draw.circle(screen, (glow, 176, 255), stage.center, 62, 3)
    pygame.draw.circle(screen, (255, 255, 255), stage.center, 34 + int(14 * progress), 1)

    if source_sprite or target_sprite:
        draw_scaled_sprite(screen, source_sprite, stage.center, 104, 255 * (1.0 - progress))
        draw_scaled_sprite(screen, target_sprite, stage.center, 104, 255 * progress)
        if final_form == "loop" and 0.42 < progress < 0.58:
            flash = pygame.Surface((stage.w, stage.h), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 60))
            screen.blit(flash, stage.topleft)
    else:
        label = "Carregando sprites..." if source_loading or target_loading else "Sem sprite"
        text(screen, small_f, label, stage.x + 58, stage.y + 58, MUTED)

    text(screen, tiny_f, source["species_name"], stage.x + 8, stage.bottom - 24, MUTED, 100)
    text(screen, tiny_f, target["species_name"], stage.right - 108, stage.bottom - 24, ACCENT, 100)


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
    text(screen, body_f, f"{source} quer evoluir para {target}.", 30, HEADER_H + 210, TEXT, SCREEN_W - 60)
    text(screen, small_f, "Deseja cancelar essa evolucao?", 30, HEADER_H + 246, WARN, SCREEN_W - 60)
    text(screen, tiny_f, "B deixa a animacao terminar na forma evoluida.", 30, HEADER_H + 282, MUTED, SCREEN_W - 60)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "CANCELAR EVO", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "DEIXAR EVOLUIR", 172, SCREEN_H - 48)


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
    text(screen, body_f, "Tem certeza?", 30, HEADER_H + 210, WARN, SCREEN_W - 60)
    text(screen, small_f, f"Isso ira interromper a evolucao de {source} para {target}.", 30, HEADER_H + 246, TEXT, SCREEN_W - 60)
    text(screen, tiny_f, "A troca continua, mas o Pokemon recebido fica sem evoluir.", 30, HEADER_H + 282, MUTED, SCREEN_W - 60)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SIM, INTERROMPER", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "NAO", 218, SCREEN_H - 48)


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
        backup_name = Path(data.get("backup", "")).name if isinstance(data, dict) and data.get("backup") else "nenhum"
        text(screen, small_f, f"Recebido: {pokemon_display}", 50, HEADER_H + 170, TEXT)
        text(screen, tiny_f, f"Backup: {backup_name}", 50, HEADER_H + 210, MUTED)
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
    logger.info("Init pygame...")
    logger.info("Debug mode: %s", DEBUG)
    pygame.init()
    pygame.font.init()
    try:
        pygame.joystick.init()
    except Exception as exc:
        logger.warning(f"Joystick init failed: {exc}")

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

    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("PokeCable Room")
    clock = pygame.time.Clock()
    fonts = (font(22, True), font(18), font(16), font(14))

    state = PokecableState()
    state.find_saves()
    state.action = "access"
    apply_theme(state.theme)
    logger.info("UI boot complete: saves=%s server=%s", len(state.saves), state.server_url)

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
    sprite_loader = SpriteLoader(state.server_url)

    def switch_screen(new_screen, reason):
        nonlocal current_screen
        if current_screen != new_screen:
            logger.info("SCREEN %s -> %s (%s)", current_screen, new_screen, reason)
        current_screen = new_screen

    while running:
        frame += 1
        action = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            mapped = event_to_action(event, axis_state, combo_state)
            mapped = debounce_action(mapped, action_state)
            if mapped and action is None:
                action = mapped

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
                elif msg_type == "evolution_cancel_prompt":
                    result_data = payload if isinstance(payload, dict) else {}
                    logger.info("QUEUE evolution_cancel_prompt: %s", result_data)
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
                menu_index = (menu_index - 1) % 3
            elif action == "down":
                menu_index = (menu_index + 1) % 3
            elif action == "select":
                if menu_index == 0:
                    reset_flow_state(state)
                    state.find_saves()
                    logger.info("Menu select: access room")
                    switch_screen("load_save", "menu_access_room")
                    menu_index = 0
                elif menu_index == 1:
                    logger.info("Menu select: config")
                    switch_screen("config", "menu_config")
                    menu_index = 0
                elif menu_index == 2:
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

        elif current_screen == "select_pokemon_source" and action:
            if action == "up":
                menu_index = (menu_index - 1) % 2
            elif action == "down":
                menu_index = (menu_index + 1) % 2
            elif action == "select":
                state.pokemon_source = "party" if menu_index == 0 else "boxes"
                try:
                    state.get_pokemon_list(state.pokemon_source)
                except SaveError as exc:
                    logger.error("Pokemon enrichment failed: %s", exc)
                    trade_status = str(exc)
                    result_data = {"success": False, "error": str(exc)}
                    switch_screen("trade_result", "api_enrichment_failed")
                    continue
                logger.info("Pokemon source selected: %s count=%s", state.pokemon_source, len(state.pokemon_list))
                switch_screen("select_pokemon", "pokemon_source_selected")
                menu_index = 0
            elif action == "back":
                switch_screen("waiting_partner" if in_room_selection else "load_save", "back_from_source")
                menu_index = 0

        elif current_screen == "select_pokemon" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(max(0, len(state.pokemon_list) - 1), menu_index + 1)
            elif action == "select" and state.pokemon_list:
                state.selected_pokemon = state.pokemon_list[menu_index]
                logger.info("Pokemon selected: %s location=%s", state.selected_pokemon.get("display"), state.selected_pokemon.get("location"))
                trade_status = f"Pokemon selecionado: {state.selected_pokemon.get('display', 'Pokemon')}"
                switch_screen("waiting_partner" if in_room_selection else "enter_room_name", "pokemon_selected")
            elif action == "back":
                switch_screen("select_pokemon_source", "back_from_pokemon")
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

        elif current_screen == "evolution_cancel_prompt" and action:
            if action == "select":
                logger.info("Evolution cancellation requested")
                switch_screen("evolution_cancel_confirm", "evolution_cancel_requested")
            elif action == "back":
                logger.info("Evolution cancellation skipped")
                confirm_queue.put(False)
                switch_screen("trading", "evolution_cancel_no")

        elif current_screen == "evolution_cancel_confirm" and action:
            if action == "select":
                logger.info("Evolution cancellation confirmed")
                confirm_queue.put(True)
                switch_screen("trading", "evolution_cancel_yes")
            elif action == "back":
                logger.info("Evolution cancellation rejected")
                confirm_queue.put(False)
                switch_screen("trading", "evolution_cancel_rejected")

        elif current_screen == "trade_result" and action in ("select", "back"):
            logger.info("Trade result acknowledged: %s", result_data)
            switch_screen("menu", "trade_result_ack")
            menu_index = 0
            result_data = {}
            trade_status = ""
            reset_flow_state(state)

        if current_screen == "menu":
            draw_menu(screen, fonts, menu_index, state.language)
        elif current_screen == "config":
            draw_config_menu(screen, fonts, menu_index, state.language, state.theme)
        elif current_screen == "load_save":
            draw_select_save(screen, fonts, menu_index, state.saves)
        elif current_screen == "select_pokemon_source":
            draw_select_pokemon_source(screen, fonts, menu_index, trade_status)
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
        elif current_screen == "trade_confirm":
            draw_trade_confirm(
                screen,
                fonts,
                state.selected_pokemon or {},
                result_data if isinstance(result_data, dict) else {},
                sprite_loader,
            )
        elif current_screen == "evolution_cancel_prompt":
            draw_evolution_cancel_prompt(screen, fonts, result_data if isinstance(result_data, dict) else {}, sprite_loader, frame)
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
