#!/usr/bin/env python3
"""
PokeCable Room - R36S UI
Interface para trading de Pokémon via WebSocket
"""

import os
import sys
import logging
import queue
import threading
from pathlib import Path
from datetime import datetime

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

DEBUG = os.getenv("POKECABLE_DEBUG", "0").lower() in ("1", "true", "yes")

try:
    import pygame
except ImportError:
    print("python3-pygame required: sudo apt install python3-pygame", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from r36s_pokecable_core import PokecableState, start_trade_thread

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"pokecable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("PokeCable Room - R36S UI")
logger.info(f"Log: {LOG_FILE}")
logger.info("=" * 80)

SCREEN_W, SCREEN_H = 640, 480
HEADER_H, FOOTER_H = 44, 60
LIST_W = 250

BG = (13, 17, 22)
PANEL = (24, 31, 39)
PANEL_2 = (34, 43, 54)
TEXT = (230, 236, 242)
MUTED = (147, 158, 171)
ACCENT = (72, 176, 255)
OK = (82, 211, 143)
RED = (245, 74, 91)


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
    if max_w:
        while value and fnt.size(value)[0] > max_w:
            value = value[:-2] + "."
    surface.blit(fnt.render(value, True, color), (x, y))


def rect(surface, color, area, radius=0):
    pygame.draw.rect(surface, color, area, border_radius=radius)


def button(surface, fnt, label, desc, x, y):
    rect(surface, PANEL_2, pygame.Rect(x, y, 24, 24), 4)
    text(surface, fnt, label, x + 7, y + 4, ACCENT)
    text(surface, fnt, desc, x + 31, y + 4, MUTED)


def draw_menu(screen, fonts, selected):
    title_f, body_f, small_f, tiny_f = fonts
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


def draw_keyboard(screen, fonts, title, value, grid_index, is_password=False, shift=False):
    """Draw keyboard with letters, numbers, symbols, and SHIFT toggle"""
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))

    shift_label = "SHIFT" if shift else "shift"
    text(screen, title_f, f"{title} [{shift_label}]", 14, 10)

    display_value = "*" * len(value) if is_password else value
    input_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, 50)
    rect(screen, PANEL, input_panel, 6)
    text(screen, body_f, display_value if display_value else "(vazio)", 20, HEADER_H + 20, ACCENT, SCREEN_W - 40)

    # Keyboard layout
    if shift:
        keyboard = "ABCDEFGHIJ KLMNOPQRST UVWXYZ      !@#$%^&*"
    else:
        keyboard = "abcdefghij klmnopqrst uvwxyz0123 456789.-_"

    chars = [c for c in keyboard if c != " "]
    grid_w, grid_h = 10, 5
    key_w, key_h = 50, 40
    start_x, start_y = 20, HEADER_H + 80

    for idx, char in enumerate(chars[:40]):
        col, row = idx % grid_w, idx // grid_w
        x, y = start_x + col * key_w, start_y + row * key_h
        is_selected = idx == grid_index
        bg_color = ACCENT if is_selected else PANEL
        rect(screen, bg_color, pygame.Rect(x, y, key_w - 5, key_h - 5), 4)
        text(screen, small_f, char if char != " " else "", x + 10, y + 10, TEXT if is_selected else MUTED)

    del_x, del_y = start_x, start_y + 4 * key_h
    shift_x, shift_y = start_x + key_w, start_y + 4 * key_h
    ok_x, ok_y = start_x + key_w * 2, start_y + 4 * key_h
    space_x, space_y = start_x + key_w * 3, start_y + 4 * key_h

    for i, (x, y, lbl) in enumerate([(del_x, del_y, "DEL"), (shift_x, shift_y, "SHIFT"), (ok_x, ok_y, "OK"), (space_x, space_y, "SPC")]):
        idx = 40 + i
        rect(screen, ACCENT if grid_index == idx else PANEL, pygame.Rect(x, y, key_w - 5, key_h - 5), 4)
        text(screen, small_f, lbl, x + 5, y + 10, TEXT if grid_index == idx else MUTED)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "SELECT", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "DEL", 112, SCREEN_H - 48)


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
        text(screen, small_f, save_path.name[:30], row.x + 9, row.y + 9, color, row.w - 18)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)


def draw_select_pokemon(screen, fonts, selected, pokemon_list):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Select Pokemon", 14, 10)

    if not pokemon_list:
        text(screen, body_f, "No Pokemon found!", 50, HEADER_H + 100, RED)
        rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
        button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)
        return

    list_panel = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, list_panel, 6)

    for idx, pokemon in enumerate(pokemon_list[:8]):
        y = HEADER_H + 30 + idx * 45
        row = pygame.Rect(18, y, SCREEN_W - 36, 40)
        color = (5, 11, 18) if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, pokemon.get("display", f"Pokemon {idx+1}")[:40], row.x + 9, row.y + 9, color, row.w - 18)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "BACK", 112, SCREEN_H - 48)


def draw_connecting(screen, fonts, frame):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Conectando", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)

    dots = "." * ((frame // 15) % 4)
    text(screen, body_f, f"Conectando ao servidor{dots}", 50, HEADER_H + 150, MUTED)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    text(screen, tiny_f, "Aguarde...", 250, SCREEN_H - 45, MUTED)


def draw_waiting_partner(screen, fonts):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Aguardando", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)

    text(screen, body_f, "Aguardando outro jogador...", 50, HEADER_H + 150, MUTED)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    text(screen, tiny_f, "Aguarde...", 250, SCREEN_H - 45, MUTED)


def draw_trade_confirm(screen, fonts, my_pokemon, opponent_pokemon):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Confirmar Troca", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)

    text(screen, small_f, "Seu Pokemon:", 30, HEADER_H + 60, TEXT)
    text(screen, body_f, my_pokemon.get("display", "???"), 30, HEADER_H + 90, OK)

    text(screen, small_f, "Pokemon do Oponente:", 30, HEADER_H + 200, TEXT)
    text(screen, body_f, opponent_pokemon.get("display", "???"), 30, HEADER_H + 230, ACCENT)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "CONFIRMAR", 12, SCREEN_H - 48)
    button(screen, tiny_f, "B", "CANCELAR", 112, SCREEN_H - 48)


def draw_trading(screen, fonts, status):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Trading", 14, 10)

    content = pygame.Rect(10, HEADER_H + 10, SCREEN_W - 20, SCREEN_H - HEADER_H - FOOTER_H - 20)
    rect(screen, PANEL, content, 6)

    text(screen, body_f, status, 30, HEADER_H + 150, MUTED)

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
        pokemon_display = data.get("display", "???") if isinstance(data, dict) else str(data)[:50]
        text(screen, small_f, f"Recebido: {pokemon_display}", 50, HEADER_H + 180, TEXT)
    else:
        text(screen, body_f, "Erro ou Cancelado", 50, HEADER_H + 100, RED)
        error_msg = str(data)[:50] if data else "Trade não completado"
        text(screen, small_f, error_msg, 50, HEADER_H + 180, RED)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "OK", 12, SCREEN_H - 48)


def main():
    logger.info("Init pygame...")
    pygame.init()
    pygame.joystick.init()

    joysticks = []
    for i in range(pygame.joystick.get_count()):
        joy = pygame.joystick.Joystick(i)
        joy.init()
        joysticks.append(joy)
        logger.info(f"Joystick {i}: {joy.get_name()}")

    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("PokeCable Room")
    clock = pygame.time.Clock()
    fonts = (font(22, True), font(18), font(16), font(14))

    logger.info("Loading state...")
    state = PokecableState()
    state.find_saves()
    logger.info(f"Found {len(state.saves)} saves")

    current_screen = "menu"
    menu_index = 0
    running = True
    frame = 0

    keyboard_index = 0
    keyboard_shift = False
    room_name = ""
    room_password = ""

    ui_queue = queue.Queue()
    confirm_queue = queue.Queue()
    trade_thread = None
    trade_status = ""
    opponent_pokemon = {}

    while running:
        action = None
        frame += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    action = "up"
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    action = "down"
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    action = "left"
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    action = "right"
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    action = "select"
                elif event.key in (pygame.K_BACKSPACE, pygame.K_ESCAPE):
                    action = "back"

        if current_screen == "menu" and action:
            if action == "up":
                menu_index = (menu_index - 1) % 3
            elif action == "down":
                menu_index = (menu_index + 1) % 3
            elif action == "select":
                if menu_index == 0:
                    current_screen = "enter_room_name"
                    keyboard_index = 0
                    keyboard_shift = False
                    room_name = ""
                elif menu_index == 2:
                    running = False
            elif action == "back":
                running = False

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
                if keyboard_index == 40:  # DEL
                    room_name = room_name[:-1]
                elif keyboard_index == 41:  # SHIFT
                    keyboard_shift = not keyboard_shift
                elif keyboard_index == 42:  # OK
                    if room_name:
                        current_screen = "enter_password"
                        keyboard_index = 0
                        keyboard_shift = False
                        room_password = ""
                elif keyboard_index == 43:  # SPACE
                    room_name += " "
                else:
                    chars = "abcdefghijklmnopqrstuvwxyz0123456789.-_" if not keyboard_shift else "ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()"
                    if keyboard_index < len(chars):
                        room_name += chars[keyboard_index]
            elif action == "back":
                room_name = room_name[:-1]

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
                if keyboard_index == 40:  # DEL
                    room_password = room_password[:-1]
                elif keyboard_index == 41:  # SHIFT
                    keyboard_shift = not keyboard_shift
                elif keyboard_index == 42:  # OK
                    if room_name and room_password:
                        state.room_name = room_name
                        state.room_password = room_password
                        current_screen = "load_save"
                        menu_index = 0
                elif keyboard_index == 43:  # SPACE
                    room_password += " "
                else:
                    chars = "abcdefghijklmnopqrstuvwxyz0123456789.-_" if not keyboard_shift else "ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()"
                    if keyboard_index < len(chars):
                        room_password += chars[keyboard_index]
            elif action == "back":
                room_password = room_password[:-1]

        elif current_screen == "load_save" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(len(state.saves) - 1, menu_index + 1)
            elif action == "select" and state.saves:
                state.selected_save = state.saves[menu_index]
                state.load_pokemon(state.selected_save, "party")
                current_screen = "select_pokemon"
                menu_index = 0
            elif action == "back":
                current_screen = "enter_password"

        elif current_screen == "select_pokemon" and action:
            if action == "up":
                menu_index = max(0, menu_index - 1)
            elif action == "down":
                menu_index = min(len(state.pokemon_list) - 1, menu_index + 1)
            elif action == "select" and state.pokemon_list:
                state.selected_pokemon = state.pokemon_list[menu_index]
                trade_thread = start_trade_thread(state, "join", ui_queue, confirm_queue)
                current_screen = "connecting"
                trade_status = "Conectando..."
            elif action == "back":
                current_screen = "load_save"

        elif current_screen == "connecting" and action:
            if action == "back":
                running = False

        elif current_screen == "waiting_partner" and action:
            if action == "back":
                running = False

        elif current_screen == "trade_confirm" and action:
            if action == "select":
                confirm_queue.put(True)
                current_screen = "trading"
            elif action == "back":
                confirm_queue.put(False)
                current_screen = "menu"
                menu_index = 0

        elif current_screen == "trading" and action:
            pass

        elif current_screen == "trade_result" and action:
            if action in ("select", "back"):
                current_screen = "menu"
                menu_index = 0

        # Process queue messages
        try:
            msg_type, payload = ui_queue.get_nowait()
            if msg_type == "status":
                trade_status = payload
                if "Sala" in payload or "Conectado" in payload:
                    current_screen = "waiting_partner"
                elif "preflight" in payload.lower() or "opponent" in payload.lower():
                    current_screen = "trade_confirm"
            elif msg_type == "confirm_prompt":
                current_screen = "trade_confirm"
            elif msg_type == "result":
                opponent_pokemon = payload if isinstance(payload, dict) else {"display": str(payload)}
                current_screen = "trade_result"
            elif msg_type == "error":
                logger.error(f"Trade error: {payload}")
                trade_status = f"Erro: {payload}"
                current_screen = "trade_result"
        except queue.Empty:
            pass

        # Draw current screen
        if current_screen == "menu":
            draw_menu(screen, fonts, menu_index)
        elif current_screen == "enter_room_name":
            draw_keyboard(screen, fonts, "Nome da Sala", room_name, keyboard_index, False, keyboard_shift)
        elif current_screen == "enter_password":
            draw_keyboard(screen, fonts, "Senha", room_password, keyboard_index, True, keyboard_shift)
        elif current_screen == "load_save":
            draw_select_save(screen, fonts, menu_index, state.saves)
        elif current_screen == "select_pokemon":
            draw_select_pokemon(screen, fonts, menu_index, state.pokemon_list)
        elif current_screen == "connecting":
            draw_connecting(screen, fonts, frame)
        elif current_screen == "waiting_partner":
            draw_waiting_partner(screen, fonts)
        elif current_screen == "trade_confirm":
            draw_trade_confirm(screen, fonts, state.selected_pokemon or {}, opponent_pokemon)
        elif current_screen == "trading":
            draw_trading(screen, fonts, trade_status)
        elif current_screen == "trade_result":
            success = isinstance(opponent_pokemon, dict) and "name" in opponent_pokemon
            draw_trade_result(screen, fonts, success, opponent_pokemon if success else trade_status)

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
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        print(f"\n❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)
