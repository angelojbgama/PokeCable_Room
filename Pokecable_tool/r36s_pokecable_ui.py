#!/usr/bin/env python3
"""
PokeCable Room - R36S UI
Interface para trading de Pokemon via WebSocket.
"""

import os
import sys
import time
import logging
import queue
import threading
import urllib.request
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

DEBUG = os.getenv("POKECABLE_DEBUG", "0").lower() in ("1", "true", "yes")

try:
    import pygame
except ImportError:
    print("python3-pygame required: sudo apt install python3-pygame", file=sys.stderr)
    sys.exit(1)

from pokecable_logging import configure_logging
from r36s_pokecable_core import PokecableState, start_trade_thread


LOG_PATHS = configure_logging()
SESSION_DIR = Path(str(LOG_PATHS["session_dir"]))
LOG_FILE = SESSION_DIR / "ui.log"

logger = logging.getLogger("r36s_pokecable_ui")

logger.info("=" * 80)
logger.info("PokeCable Room - R36S UI")
logger.info(f"Log: {LOG_FILE}")
logger.info(f"Session dir: {SESSION_DIR}")
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

BG = (13, 17, 22)
PANEL = (24, 31, 39)
PANEL_2 = (34, 43, 54)
TEXT = (230, 236, 242)
MUTED = (147, 158, 171)
ACCENT = (72, 176, 255)
OK = (82, 211, 143)
RED = (245, 74, 91)
WARN = (255, 190, 88)

SPRITE_CACHE_DIR = Path.home() / ".pokecable" / "sprites"
SPRITE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)


def text(surface, fnt, value, x, y, color=TEXT, max_w=None):
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
        self.request_key = ""
        self.request_id = 0
        self.surface = None
        self.loading = False
        self.error = ""

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

    def request(self, pokemon):
        species_name = pokemon.get("species_name") if pokemon else ""
        species_id = int((pokemon or {}).get("species_id") or 0)
        logger.debug("Sprite request: species_id=%s species_name=%s", species_id, species_name)
        if not pokemon or (not species_name and not species_id) or species_name.lower() == "egg":
            with self.lock:
                self.request_key = ""
                self.request_id += 1
                self.surface = None
                self.loading = False
                self.error = ""
            return

        generation = int((pokemon or {}).get("generation") or 0)
        slug = pokemon_sprite_slug(species_name)
        if not slug:
            with self.lock:
                self.request_key = ""
                self.request_id += 1
                self.surface = None
                self.loading = False
                self.error = ""
            return
        key = f"gen{generation}-{slug}-front"
        lookup = {"generation": generation, "species_slug": slug}
        with self.lock:
            if self.request_key == key and (self.loading or self.surface is not None):
                return
            self.request_key = key
            self.request_id += 1
            request_id = self.request_id
            self.surface = None
            self.loading = True
            self.error = ""
        threading.Thread(target=self._load, args=(request_id, key, lookup), daemon=True).start()

    def _load(self, request_id, key, lookup):
        try:
            if not self.http_base_url:
                raise RuntimeError("invalid backend URL")
            cache_file = SPRITE_CACHE_DIR / f"{key}.png"
            if not cache_file.exists():
                logger.debug("Sprite cache miss: key=%s", key)
                generation = int(lookup.get("generation") or 0)
                species_slug = str(lookup.get("species_slug") or "")
                sprite_url = f"{self.http_base_url}/sprites/{generation}/{species_slug}/front.png"
                with urllib.request.urlopen(sprite_url, timeout=6) as response:
                    cache_file.write_bytes(response.read())
                logger.info("Sprite downloaded: key=%s", key)
            surface = pygame.image.load(str(cache_file)).convert_alpha()
            error = ""
        except Exception as exc:
            surface = None
            error = str(exc)
            logger.warning("Sprite load failed: key=%s error=%s", key, exc)
        with self.lock:
            if request_id == self.request_id:
                self.surface = surface
                self.loading = False
                self.error = error

    def snapshot(self):
        with self.lock:
            return self.surface, self.loading, self.error


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


def draw_menu(screen, fonts, selected):
    title_f, _, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "PokeCable", 14, 10)

    items = ["Acessar Sala", "Config", "Sair"]
    list_panel = pygame.Rect(10, HEADER_H + 10, LIST_W - 18, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)
    text(screen, small_f, "Menu", 22, HEADER_H + 22, MUTED)

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


def draw_keyboard(screen, fonts, title, value, grid_index, is_password=False, shift=False):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    shift_label = "SHIFT" if shift else "shift"
    text(screen, title_f, f"{title} [{shift_label}]", 14, 10)

    display_value = "*" * len(value) if is_password else value
    input_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, 50)
    rect(screen, PANEL, input_panel, 6)
    text(screen, body_f, display_value if display_value else "(vazio)", 20, HEADER_H + 20, ACCENT, SCREEN_W - 40)

    if shift:
        keyboard = "ABCDEFGHIJ KLMNOPQRST UVWXYZ      !@#$%^&*"
    else:
        keyboard = "abcdefghij klmnopqrst uvwxyz0123 456789.-_"

    chars = [c for c in keyboard if c != " "]
    grid_w, key_w, key_h = 10, 50, 40
    start_x, start_y = 20, HEADER_H + 80

    for idx, char in enumerate(chars[:40]):
        col, row = idx % grid_w, idx // grid_w
        x, y = start_x + col * key_w, start_y + row * key_h
        selected = idx == grid_index
        rect(screen, ACCENT if selected else PANEL, pygame.Rect(x, y, key_w - 5, key_h - 5), 4)
        text(screen, small_f, char, x + 10, y + 10, TEXT if selected else MUTED)

    specials = [("DEL", 40), ("SHIFT", 41), ("OK", 42), ("SPC", 43)]
    for offset, (label, idx) in enumerate(specials):
        x = start_x + offset * key_w
        y = start_y + 4 * key_h
        selected = idx == grid_index
        rect(screen, ACCENT if selected else PANEL, pygame.Rect(x, y, key_w - 5, key_h - 5), 4)
        text(screen, small_f, label, x + 5, y + 10, TEXT if selected else MUTED)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SELECT", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "DEL/BACK", 112, SCREEN_H - 48)


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

    for idx, save_path in enumerate(saves[:8]):
        y = HEADER_H + 30 + idx * 45
        row = pygame.Rect(18, y, SCREEN_W - 36, 40)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, save_path.name[:50], row.x + 9, row.y + 9, color, row.w - 18)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)


def draw_select_pokemon_source(screen, fonts, selected):
    title_f, _, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Escolher Origem", 14, 10)

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

    text(screen, tiny_f, "Escolha de onde sair o Pokemon para a troca.", 22, SCREEN_H - FOOTER_H - 24, MUTED)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)


def draw_select_pokemon(screen, fonts, selected, pokemon_list, source_label, sprite_loader):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Escolher Pokemon", 14, 10)

    if not pokemon_list:
        text(screen, body_f, "No Pokemon found!", 50, HEADER_H + 100, RED)
        rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
        button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)
        return

    list_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)

    for idx, pokemon in enumerate(pokemon_list[:8]):
        y = HEADER_H + 30 + idx * 45
        row = pygame.Rect(18, y, 292, 40)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, pokemon.get("display", f"Pokemon {idx+1}")[:48], row.x + 9, row.y + 9, color, row.w - 18)

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
        location = selected_pokemon.get("location", "")
        if location.startswith("box:"):
            parts = location.split(":")
            box_name = selected_pokemon.get("raw", {}).get("box_name") or f"Box {int(parts[1]) + 1}"
            text(screen, tiny_f, box_name, detail_panel.x + 164, detail_panel.y + 112, MUTED, 110)
        else:
            text(screen, tiny_f, "Party", detail_panel.x + 164, detail_panel.y + 112, MUTED, 110)

        detail_y = detail_panel.y + 194
        text(screen, small_f, "Resumo", detail_panel.x + 14, detail_y, TEXT)
        text(screen, tiny_f, selected_pokemon.get("display", ""), detail_panel.x + 14, detail_y + 26, MUTED, detail_panel.w - 28)
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
    text(screen, title_f, "Aguardando", 14, 10)
    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)
    text(screen, body_f, status or "Aguardando outro jogador...", 40, HEADER_H + 150, MUTED, SCREEN_W - 80)
    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    text(screen, tiny_f, "Aguarde...", 250, SCREEN_H - 45, MUTED)


def draw_trade_confirm(screen, fonts, my_pokemon, opponent_pokemon):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Confirmar Troca", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)

    mine = my_pokemon.get("display", "???")
    peer = opponent_pokemon.get("display_summary") or opponent_pokemon.get("nickname") or opponent_pokemon.get("species_name") or "???"
    text(screen, small_f, "Seu Pokemon:", 30, HEADER_H + 60, TEXT)
    text(screen, body_f, mine, 30, HEADER_H + 90, OK)
    text(screen, small_f, "Pokemon do Oponente:", 30, HEADER_H + 200, TEXT)
    text(screen, body_f, peer, 30, HEADER_H + 230, ACCENT)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "CONFIRMAR", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "CANCELAR", 112, SCREEN_H - 48)


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
        pokemon_display = peer.get("display_summary") or peer.get("nickname") or peer.get("species_name") or "Pokemon"
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
    logger.info("UI boot complete: saves=%s server=%s", len(state.saves), state.server_url)

    current_screen = "menu"
    menu_index = 0
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
                elif menu_index == 2:
                    logger.info("Menu select: exit")
                    running = False
            elif action == "back":
                logger.info("Menu back: exit")
                running = False

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
                room_name = ""
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
                state.get_pokemon_list(state.pokemon_source)
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
            if action == "up":
                keyboard_index = max(0, keyboard_index - 10)
            elif action == "down":
                keyboard_index = min(43, keyboard_index + 10)
            elif action == "left":
                keyboard_index = max(0, keyboard_index - 1)
            elif action == "right":
                keyboard_index = min(43, keyboard_index + 1)
            elif action == "select":
                if keyboard_index == 40:
                    room_name = room_name[:-1]
                elif keyboard_index == 41:
                    keyboard_shift = not keyboard_shift
                elif keyboard_index == 42:
                    if room_name:
                        logger.info("Room name submitted: %s", room_name)
                        switch_screen("enter_password", "room_name_submitted")
                        keyboard_index = 0
                        keyboard_shift = False
                        room_password = ""
                elif keyboard_index == 43:
                    room_name += " "
                else:
                    chars = "abcdefghijklmnopqrstuvwxyz0123456789.-_" if not keyboard_shift else "ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()"
                    if keyboard_index < len(chars):
                        room_name += chars[keyboard_index]
            elif action == "back":
                if room_name:
                    room_name = room_name[:-1]
                else:
                    switch_screen("load_save", "back_from_room_name")
                    menu_index = 0

        elif current_screen == "enter_password" and action:
            if action == "up":
                keyboard_index = max(0, keyboard_index - 10)
            elif action == "down":
                keyboard_index = min(43, keyboard_index + 10)
            elif action == "left":
                keyboard_index = max(0, keyboard_index - 1)
            elif action == "right":
                keyboard_index = min(43, keyboard_index + 1)
            elif action == "select":
                if keyboard_index == 40:
                    room_password = room_password[:-1]
                elif keyboard_index == 41:
                    keyboard_shift = not keyboard_shift
                elif keyboard_index == 42:
                    if room_name and room_password:
                        state.room_name = room_name
                        state.room_password = room_password
                        state.selected_pokemon = None
                        state.pokemon_list = []
                        logger.info("Starting trade: room=%s password_len=%s action=%s", state.room_name, len(state.room_password), state.action)
                        trade_thread = start_trade_thread(state, state.action or "access", ui_queue, confirm_queue)
                        switch_screen("connecting", "trade_thread_started")
                        trade_status = "Conectando..."
                elif keyboard_index == 43:
                    room_password += " "
                else:
                    chars = "abcdefghijklmnopqrstuvwxyz0123456789.-_" if not keyboard_shift else "ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()"
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

        elif current_screen == "trade_result" and action in ("select", "back"):
            logger.info("Trade result acknowledged: %s", result_data)
            switch_screen("menu", "trade_result_ack")
            menu_index = 0
            result_data = {}
            trade_status = ""
            reset_flow_state(state)

        if current_screen == "menu":
            draw_menu(screen, fonts, menu_index)
        elif current_screen == "load_save":
            draw_select_save(screen, fonts, menu_index, state.saves)
        elif current_screen == "select_pokemon_source":
            draw_select_pokemon_source(screen, fonts, menu_index)
        elif current_screen == "select_pokemon":
            source_label = "Sua Party" if state.pokemon_source == "party" else "Seu PC"
            draw_select_pokemon(screen, fonts, menu_index, state.pokemon_list, source_label, sprite_loader)
        elif current_screen == "enter_room_name":
            draw_keyboard(screen, fonts, "Nome da Sala", room_name, keyboard_index, False, keyboard_shift)
        elif current_screen == "enter_password":
            draw_keyboard(screen, fonts, "Senha", room_password, keyboard_index, True, keyboard_shift)
        elif current_screen == "connecting":
            draw_connecting(screen, fonts, frame)
        elif current_screen == "waiting_partner":
            draw_waiting_partner(screen, fonts, trade_status)
        elif current_screen == "trade_confirm":
            draw_trade_confirm(screen, fonts, state.selected_pokemon or {}, result_data if isinstance(result_data, dict) else {})
        elif current_screen == "trading":
            draw_trading(screen, fonts, trade_status)
        elif current_screen == "trade_result":
            success = bool(isinstance(result_data, dict) and result_data.get("success"))
            data = result_data if success else result_data.get("error", trade_status) if isinstance(result_data, dict) else trade_status
            draw_trade_result(screen, fonts, success, data)

        if trade_status and current_screen in ("load_save", "select_pokemon_source", "select_pokemon"):
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
        print("\nErro fatal. Veja os logs da sessão em logs/latest.", file=sys.stderr)
        sys.exit(1)
