#!/usr/bin/env python3
"""
Button Mapper - Ferramenta para mapear botões do R36S
Detecta e registra cada botão pressionado
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

try:
    import pygame
except ImportError:
    print("Precisa: sudo apt install python3-pygame", file=sys.stderr)
    sys.exit(1)

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"button_mapper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("BUTTON MAPPER - R36S")
logger.info(f"Log: {LOG_FILE}")
logger.info("=" * 80)

SCREEN_W = 640
SCREEN_H = 480
HEADER_H = 60
FOOTER_H = 80

# Colors
BG = (13, 17, 22)
PANEL = (24, 31, 39)
PANEL_2 = (34, 43, 54)
TEXT = (230, 236, 242)
MUTED = (147, 158, 171)
ACCENT = (72, 176, 255)
OK = (82, 211, 143)
RED = (245, 74, 91)
YELLOW = (255, 190, 88)

CONFIG_FILE = Path(__file__).parent / "button_config.json"


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


def draw_button_box(surface, fnt, label, x, y, w, h, is_pressed=False):
    """Desenha um botão visual"""
    color = OK if is_pressed else PANEL_2
    rect(surface, color, pygame.Rect(x, y, w, h), 4)
    text_color = (5, 11, 18) if is_pressed else TEXT
    text(surface, fnt, label, x + w//2 - fnt.size(label)[0]//2, y + h//2 - 10, text_color)


def save_config(mapping):
    """Salva mapeamento de botões"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(mapping, f, indent=2)
        logger.info(f"Config saved: {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False


def load_config():
    """Carrega mapeamento de botões"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    return {}


def main():
    logger.info("Init pygame...")
    pygame.init()
    pygame.joystick.init()

    logger.info(f"Joysticks: {pygame.joystick.get_count()}")
    joysticks = []
    for i in range(pygame.joystick.get_count()):
        joy = pygame.joystick.Joystick(i)
        joy.init()
        joysticks.append(joy)
        logger.info(f"  Joy {i}: {joy.get_name()}")
        logger.info(f"    Buttons: {joy.get_numbuttons()}")
        logger.info(f"    Axes: {joy.get_numaxes()}")
        logger.info(f"    Hats: {joy.get_numhats()}")

    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Button Mapper")
    clock = pygame.time.Clock()
    fonts = (font(24, True), font(18), font(14), font(12))

    # Mapeamento
    mapping = load_config()
    button_events = {}
    last_press_time = {}
    last_action = ""

    logger.info("Ready! Press buttons to map...")

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

            elif event.type == pygame.JOYBUTTONDOWN:
                button_id = f"button_{event.button}"
                button_events[button_id] = True
                last_press_time[button_id] = pygame.time.get_ticks()
                last_action = f"Button {event.button} DOWN"
                logger.info(f"JOYBUTTONDOWN: {event.button}")
                mapping[button_id] = f"button_{event.button}"

            elif event.type == pygame.JOYBUTTONUP:
                button_id = f"button_{event.button}"
                button_events[button_id] = False
                logger.info(f"JOYBUTTONUP: {event.button}")

            elif event.type == pygame.JOYHATMOTION:
                last_action = f"D-Pad: {event.value}"
                logger.info(f"JOYHATMOTION: {event.value}")
                if event.value == (0, -1):
                    mapping["dpad_up"] = "dpad_up"
                elif event.value == (0, 1):
                    mapping["dpad_down"] = "dpad_down"
                elif event.value == (-1, 0):
                    mapping["dpad_left"] = "dpad_left"
                elif event.value == (1, 0):
                    mapping["dpad_right"] = "dpad_right"

            elif event.type == pygame.JOYAXISMOTION:
                if abs(event.value) > 0.7:
                    last_action = f"Axis {event.axis}: {event.value:.2f}"
                    logger.info(f"JOYAXISMOTION: axis {event.axis} = {event.value:.2f}")
                    if event.axis == 1:
                        if event.value < -0.7:
                            mapping["analog_up"] = "analog_up"
                        elif event.value > 0.7:
                            mapping["analog_down"] = "analog_down"

        # Clear old presses (0.5s timeout)
        current_time = pygame.time.get_ticks()
        for button_id in list(last_press_time.keys()):
            if current_time - last_press_time[button_id] > 500:
                button_events[button_id] = False
                del last_press_time[button_id]

        # Draw
        screen.fill(BG)

        # Header
        rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
        text(screen, fonts[0], "Button Mapper", 20, 15)

        # Instructions
        y = HEADER_H + 20
        text(screen, fonts[2], "Pressione cada botão do R36S", 30, y, MUTED)
        y += 40
        text(screen, fonts[3], f"Último: {last_action}", 30, y, ACCENT)

        # Button grid
        y = HEADER_H + 120
        button_positions = [
            (50, y, 80, 60, "A", button_events.get("button_0", False)),
            (150, y, 80, 60, "B", button_events.get("button_1", False)),
            (250, y, 80, 60, "X", button_events.get("button_3", False)),
            (350, y, 80, 60, "Y", button_events.get("button_2", False)),
        ]

        for x, yp, w, h, label, is_pressed in button_positions:
            draw_button_box(screen, fonts[1], label, x, yp, w, h, is_pressed)

        # D-Pad
        y += 120
        dpad_x = 80
        text(screen, fonts[2], "D-Pad:", 30, y, TEXT)
        draw_button_box(screen, fonts[3], "↑", dpad_x + 40, y + 30, 40, 40, mapping.get("dpad_up") == "dpad_up")
        draw_button_box(screen, fonts[3], "↓", dpad_x + 40, y + 100, 40, 40, mapping.get("dpad_down") == "dpad_down")
        draw_button_box(screen, fonts[3], "←", dpad_x, y + 65, 40, 40, mapping.get("dpad_left") == "dpad_left")
        draw_button_box(screen, fonts[3], "→", dpad_x + 80, y + 65, 40, 40, mapping.get("dpad_right") == "dpad_right")

        # Info
        y += 180
        rect(screen, PANEL, pygame.Rect(0, y - 40, SCREEN_W, SCREEN_H - y + 40))
        text(screen, fonts[3], f"Mapped: {len(mapping)} buttons", 30, y, OK)
        text(screen, fonts[3], "ESC/Q = Save & Exit", 30, y + 35, MUTED)

        # Footer
        rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
        text(screen, fonts[3], f"Config file: {CONFIG_FILE.name}", 20, SCREEN_H - 50, MUTED)
        text(screen, fonts[3], "Log: logs/button_mapper_*.log", 20, SCREEN_H - 20, MUTED)

        pygame.display.flip()
        clock.tick(30)

    # Save on exit
    logger.info("=" * 80)
    logger.info(f"Final mapping: {mapping}")
    save_config(mapping)
    logger.info("=" * 80)

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Error: {e}")
        sys.exit(1)
