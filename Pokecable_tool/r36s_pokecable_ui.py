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
INPUT_TRANSITION_GUARD_SECONDS = 0.25
NAV_REPEAT_DELAY = 0.25
NAV_REPEAT_INTERVAL = 0.06
QUIT_COMBO_WINDOW = 0.35
JOY_BUTTON_START = 13
JOY_BUTTON_SELECT = 12
ROW_H = 45
ROW_VISIBLE = 7
GUARDED_INPUT_ACTIONS = {"select", "back", "x", "y", "up", "down", "left", "right"}

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
    "pokedex_red": {
        "bg": (234, 247, 255),
        "shell": (245, 27, 79),
        "shell_2": (199, 31, 85),
        "panel": (244, 241, 232),
        "panel_2": (216, 213, 205),
        "screen": (15, 44, 101),
        "screen_text": (234, 251, 255),
        "border": (40, 36, 93),
        "shadow": (108, 36, 81),
        "text": (23, 27, 63),
        "muted": (94, 102, 133),
        "accent": (24, 212, 242),
        "ok": (22, 182, 95),
        "red": (245, 27, 79),
        "warn": (255, 217, 31),
    },
    "pokedex_dark": {
        "bg": (225, 239, 252),
        "shell": (33, 100, 178),
        "shell_2": (245, 250, 255),
        "panel": (248, 252, 255),
        "panel_2": (219, 237, 252),
        "screen": (16, 38, 75),
        "screen_text": (238, 248, 255),
        "border": (27, 58, 103),
        "shadow": (35, 69, 112),
        "text": (12, 31, 56),
        "muted": (78, 105, 135),
        "accent": (22, 172, 217),
        "ok": (35, 128, 206),
        "red": (224, 55, 76),
        "warn": (230, 163, 31),
    },
    "pokedex_white": {
        "bg": (239, 248, 255),
        "shell": (244, 249, 254),
        "shell_2": (35, 103, 183),
        "panel": (252, 254, 255),
        "panel_2": (222, 239, 253),
        "screen": (18, 44, 83),
        "screen_text": (238, 248, 255),
        "border": (31, 73, 124),
        "shadow": (168, 196, 224),
        "text": (13, 32, 58),
        "muted": (83, 111, 141),
        "accent": (18, 173, 218),
        "ok": (32, 125, 207),
        "red": (224, 55, 76),
        "warn": (232, 169, 37),
    },
}

THEME_COLORSETS = {
    "ink_wash": ("Ink wash", ["#252525", "#CFCFCF", "#7D7D7D", "#545454"]),
    "neutral_elegance": ("Neutral elegance", ["#FFDBBB", "#CCBEB1", "#997E67", "#664930"]),
    "jade_pebble_morning": ("Jade pebble morning", ["#7B9669", "#E6E6E6", "#6C8480", "#BAC8B1", "#404E3B"]),
    "woodland": ("Woodland", ["#9F7560", "#9E9E9E", "#AAD31E", "#D4AF9F", "#525034"]),
    "driftwood_pearl_morning": ("Driftwood pearl morning", ["#BC7B6F", "#5A322A", "#E4A499", "#718A9E", "#CCCDC7"]),
    "graphite": ("Graphite", ["#C1C0C2", "#F5E9E7", "#837D68", "#8A9DB1", "#ECC5C6"]),
    "urban_slate": ("Urban slate", ["#E9E6E7", "#5E5653", "#7B7F8A", "#AB978C", "#6B7C98"]),
    "pearl": ("Pearl", ["#E9E3DE", "#A5937B", "#E3C49B", "#666161", "#AF9AC9"]),
    "vichy": ("Vichy", ["#BBBFBF", "#878787", "#05AD98", "#FFFFFF"]),
    "sorbet": ("Sorbet", ["#CCCCCC", "#EDECEC", "#B7C396", "#FEFEFE", "#E0E7D7", "#BA9A91"]),
    "frozen_mist": ("Frozen mist", ["#7C7D75", "#ADACA7", "#FCF8D8", "#D9DADF", "#DD700B"]),
    "yacht_club": ("Yacht club", ["#F2F0EF", "#BBBDBC", "#245F73", "#733E24"]),
    "amber_walnut_morning": ("Amber walnut morning", ["#EBEFEE", "#CCB499", "#C8906D", "#BB6C43", "#4A413C"]),
    "copper_aquamarine_dream": ("Copper aquamarine dream", ["#DCAA89", "#30525C", "#C35627", "#D6794D", "#4C848D", "#BFB9B5"]),
    "cocoa_topaz_noonday": ("Cocoa topaz noonday", ["#742F14", "#5A84AC", "#C7AC9F", "#FC9C44", "#5C3C2C"]),
    "sandstone_aquamarine_serenity": ("Sandstone aquamarine serenity", ["#BC6C50", "#304C53", "#DDAD9C", "#5A2F25", "#AFE0E7"]),
    "honey_opal_sunset": ("Honey opal sunset", ["#ECB914", "#F6D579", "#9D8108", "#CBB8A0", "#4F3D35"]),
    "seashell_garnet_afternoon": ("Seashell garnet afternoon", ["#F6C992", "#30525C", "#ACC0D3", "#D396A6", "#09A1A1", "#5484A4"]),
    "rose_quartz_evening": ("Rose quartz evening", ["#64242F", "#B44446", "#FC8F8F", "#DFD9D8"]),
    "calcite": ("Calcite", ["#DDDCD8", "#FD7B41", "#EDBF9B", "#3C4044"]),
    "fireside": ("Fireside", ["#E76814", "#D8D4BC", "#891A10", "#DC8236", "#B8210F", "#714236"]),
    "terrazzo": ("Terrazzo", ["#EDBD95", "#374F4E", "#D1801E", "#DACCC4", "#AA8552"]),
    "sapphire_nightfall_whisper": ("Sapphire nightfall whisper", ["#0474C4", "#5379AE", "#2C444C", "#A8C4EC", "#06457F", "#262B40"]),
    "lapis_velvet_evening": ("Lapis velvet evening", ["#213885", "#ECDFD2", "#5F3475", "#081849", "#CCCACC", "#893172"]),
    "marina": ("Marina", ["#FFF1E7", "#B5D2E6", "#326080", "#805232"]),
    "emerald_lavender_lake": ("Emerald lavender lake", ["#248C54", "#89618E", "#95DCE4"]),
    "sage_peridot_morning": ("Sage peridot morning", ["#345C32", "#9CAC54", "#A7F0DD", "#97CD97"]),
    "amethyst_dawn_haze": ("Amethyst dawn haze", ["#341C67", "#472F5B", "#C4AEF4", "#CCA4B4", "#DCCE40"]),
    "moon_dust": ("Moon dust", ["#D3D3FF", "#CEB5FF", "#8EC1DE", "#80A8FF"]),
    "turquoise_amber_autumn": ("Turquoise amber autumn", ["#304C64", "#26788E", "#A4CCD4", "#E2480C", "#631B08"]),
    "sapphire_ash_morning": ("Sapphire ash morning", ["#35627A", "#E5AEA9", "#B46258", "#A6A9D0", "#F5F5F5", "#8E9A98"]),
    "frosted_aura": ("Frosted aura", ["#5C7E8F", "#A2A2A2", "#D4DDE2", "#FFFFFF"]),
    "royal_glimmer": ("Royal glimmer", ["#AD7C4B", "#293C7C", "#C7984F", "#024944", "#812B4A"]),
    "neptune": ("Neptune", ["#8FD9FB", "#4AB5B5", "#6D8BC0", "#525AFF"]),
    "tropical_jade_sunrise": ("Tropical jade sunrise", ["#FCA47C", "#23CED9", "#F9D779", "#A1CCA6", "#097C87"]),
    "amethyst_mint_harmony": ("Amethyst mint harmony", ["#2A3F38", "#8DF688", "#562F54", "#57585D", "#F650BD"]),
    "hibiscus_aura": ("Hibiscus aura", ["#EA44D4", "#DD3027", "#733D6F", "#5848B3"]),
    "ocean_ruby_radiance": ("Ocean ruby radiance", ["#D8226C", "#B2DAE4", "#F86A38", "#029456", "#005BB3"]),
    "tropical_heat": ("Tropical heat", ["#00CEC8", "#FCEFC3", "#FF9C5F", "#EB4203"]),
    "celestial": ("Celestial", ["#2323FF", "#807D52", "#FFBD24", "#FFF224"]),
    "festive_eve": ("Festive eve", ["#2323FF", "#24AEFF", "#C04AFF", "#7E3DFF"]),
    "freshly_squeezed": ("Freshly squeezed", ["#FFBF00", "#F2CF7E", "#FFE642", "#FF7900"]),
    "jelly_shoes": ("Jelly shoes", ["#E0AFFF", "#C4D6FF", "#DD68E3", "#8866DE"]),
    "opaline": ("Opaline", ["#F4F4F6", "#E7E7E7", "#D2D2D4", "#FF634A"]),
    "gossamer": ("Gossamer", ["#FAFAFA", "#939599", "#CDCDCF", "#2BCFCE", "#EC4D25"]),
    "clockwork": ("Clockwork", ["#919599", "#F8F8F8", "#CDCDCB", "#FBA45C", "#E56515"]),
    "lemon_granite_morning": ("Lemon granite morning", ["#F3E308", "#B8BFC1", "#6C8494", "#2C4C5C"]),
    "arctic_reflection": ("Arctic reflection", ["#5289AD", "#243C4C", "#ACBCBF", "#F4FCFB", "#698696"]),
    "slate": ("Slate", ["#BEBEBE", "#79ED91", "#4DBE55", "#71776D", "#698696"]),
    "autumn_luxe": ("Autumn luxe", ["#E2E1EB", "#AAAAAE", "#7F7265", "#BF8440", "#322D27"]),
    "inked": ("Inked", ["#000000", "#DFDEDC", "#464545", "#00ACAC", "#A6A7A2"]),
    "wraith": ("Wraith", ["#1E1702", "#E5E3E4", "#8C886B", "#047C58", "#342005"]),
    "urban_nocturne": ("Urban nocturne", ["#141414", "#444444", "#D6D6D6", "#E2E800", "#979797"]),
}

THEME_NAMES = {
    "pokedex_red": "Pokedex vermelha",
    "pokedex_dark": "Azul tecnico",
    "pokedex_white": "Branco + azul",
}
THEME_NAMES.update({theme_id: data[0] for theme_id, data in THEME_COLORSETS.items()})
THEME_ORDER = ["pokedex_red", "pokedex_white", "pokedex_dark"] + list(THEME_COLORSETS.keys())


def hex_color(value):
    value = str(value or "").strip().lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def mix_color(a, b, amount):
    amount = max(0.0, min(1.0, float(amount)))
    return tuple(int(round(a[idx] * (1.0 - amount) + b[idx] * amount)) for idx in range(3))


def luminance(color):
    return color[0] * 0.2126 + color[1] * 0.7152 + color[2] * 0.0722


def saturation(color):
    return max(color) - min(color)


def readable_text_color(background):
    return (13, 32, 58) if luminance(background) >= 150 else (238, 248, 255)


def muted_text_color(text_color, panel_color):
    return mix_color(text_color, panel_color, 0.45)


def generated_palette(hex_values):
    colors = [hex_color(value) for value in hex_values]
    by_luminance = sorted(colors, key=luminance)
    base_darkest = by_luminance[0]
    lightest = by_luminance[-1]
    second_lightest = by_luminance[-2] if len(by_luminance) > 1 else lightest
    shell = colors[0]
    shell_2 = colors[1] if len(colors) > 1 else mix_color(shell, lightest, 0.55)
    raw_accent = max(colors, key=lambda color: saturation(color) * 2.0 + luminance(color) * 0.35)
    accent = raw_accent
    if luminance(accent) < 95:
        accent = mix_color(accent, (255, 255, 255), 0.42)
    screen_base = next((color for color in by_luminance if color != raw_accent), base_darkest)
    panel = mix_color(lightest, (255, 255, 255), 0.72)
    panel_2 = mix_color(second_lightest, (255, 255, 255), 0.48)
    screen = mix_color(screen_base, (0, 0, 0), 0.18)
    text_color = readable_text_color(panel)
    return {
        "bg": mix_color(lightest, (255, 255, 255), 0.55),
        "shell": shell,
        "shell_2": shell_2,
        "panel": panel,
        "panel_2": panel_2,
        "screen": screen,
        "screen_text": readable_text_color(screen),
        "border": mix_color(base_darkest, (0, 0, 0), 0.28),
        "shadow": mix_color(base_darkest, (0, 0, 0), 0.08),
        "text": text_color,
        "muted": muted_text_color(text_color, panel),
        "accent": accent,
        "ok": max(colors, key=lambda color: color[1] - color[0] * 0.25 - color[2] * 0.15),
        "red": max(colors, key=lambda color: color[0] - color[1] * 0.35),
        "warn": max(colors, key=lambda color: color[0] + color[1] - color[2] * 0.45),
    }


THEMES.update({theme_id: generated_palette(colors) for theme_id, (_, colors) in THEME_COLORSETS.items()})


def theme_display_name(theme_name):
    key = str(theme_name or "").strip().lower()
    return THEME_NAMES.get(key, THEME_NAMES["pokedex_white"])


def next_theme(theme_name, direction):
    key = str(theme_name or "").strip().lower()
    index = THEME_ORDER.index(key) if key in THEME_ORDER else 0
    return THEME_ORDER[(index + int(direction)) % len(THEME_ORDER)]

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
        "theme_dark": "Azul tecnico",
        "theme_white": "Branco + azul",
        "action_title": "Acao",
        "action_create_room": "Criar sala",
        "action_join_room": "Entrar em sala",
        "choose": "Escolha",
        "select_save": "Selecionar save",
        "self_save_1": "Trocar comigo: Save 1",
        "self_save_2": "Trocar comigo: Save 2",
        "no_saves": "Nenhum save encontrado.",
        "selected_save": "Save selecionado",
        "save_file": "Arquivo",
        "save_folder": "Pasta",
        "save_pick_hint": "Escolha o save que vai entrar na troca.",
        "choose_source": "Escolher origem",
        "source_helper": "Escolha de onde sair o Pokemon para a troca.",
        "room": "Sala",
        "password": "Senha",
        "no_name": "(sem nome)",
        "no_password": "(sem senha)",
        "share_room": "Compartilhe estes dados com seu parceiro para entrar na mesma sala.",
        "choose_pokemon": "Escolher Pokemon",
        "waiting_partner": "Aguardando segundo jogador",
        "no_pokemon": "Nenhum Pokemon encontrado.",
        "loading_sprite": "Carregando sprite...",
        "loading_sprites": "Carregando sprites...",
        "no_sprite": "Sem sprite",
        "item_none": "Sem item",
        "item_label": "Item: {name}",
        "item_label_none": "Item: nenhum",
        "level": "Nivel: {level}",
        "level_short": "Nivel {level}",
        "level_tag": "Nivel {level}",
        "level_unknown": "Nivel ?",
        "moves": "Ataques",
        "no_moves": "Sem ataques",
        "party": "Party",
        "pc": "PC",
        "your_party": "Sua Party",
        "your_pc": "Seu PC",
        "party_save": "Party Save {slot}",
        "party_save_named": "Party Save {slot}: {name}",
        "pc_save": "PC Save {slot}",
        "pc_save_named": "PC Save {slot}: {name}",
        "connecting": "Conectando",
        "connecting_server": "Conectando ao servidor{dots}",
        "please_wait": "Aguarde...",
        "leave_room_title": "Sair da sala?",
        "leave_room_question": "Deseja encerrar esta sala?",
        "leave_room_help": "Voce e o parceiro voltarao ao menu.",
        "leave_room_more": "Para mais trocas, escolha A=NAO.",
        "deposit_title": "Mover para PC?",
        "deposit_question": "Enviar {name} para o PC?",
        "deposit_help": "Ele ira para o primeiro slot livre.",
        "backup_help": "Um backup do save sera criado antes.",
        "withdraw_title": "Retirar do PC?",
        "withdraw_question": "Trazer {name} para a Party?",
        "withdraw_from": "De: {box}",
        "withdraw_help": "Sera adicionado no proximo slot livre da Party.",
        "notice": "Aviso",
        "no_details": "Sem detalhes.",
        "trade_cancelled_room_open": "A troca foi cancelada. A sala continua aberta.",
        "incompatible_move_title": "Move incompativel {current}/{total}",
        "unsupported_move": "Sem suporte: {move}",
        "choose_replacement": "Escolha um substituto ou deixe vazio.",
        "empty_move": "(deixar vazio)",
        "cancel_trade_title": "Cancelar troca?",
        "cancel_trade_question": "Cancelar a troca deste Pokemon?",
        "save_not_modified": "Seu save NAO sera modificado.",
        "room_stays_open": "A sala continua aberta - voce escolhera outro Pokemon.",
        "room_open_short": "Sala aberta",
        "confirm_trade": "Confirmar troca",
        "your_pokemon": "Seu Pokemon",
        "opponent": "Oponente",
        "trade_evolution": "Evolucao por troca",
        "confirm_cancel": "Confirmar cancelamento",
        "wants_evolve": "{source} quer evoluir para {target}.",
        "cancel_evolution_question": "Deseja cancelar essa evolucao?",
        "cancel_evolution_hint": "B deixa a animacao terminar na forma evoluida.",
        "are_you_sure": "Tem certeza?",
        "cancel_evolution_confirm": "Isso ira interromper a evolucao de {source} para {target}.",
        "cancel_evolution_result": "A troca continua, mas o Pokemon recebido fica sem evoluir.",
        "trading": "Trocando",
        "processing": "Processando...",
        "result": "Resultado",
        "trade_complete": "Troca completa!",
        "received": "Recebido: {pokemon}",
        "backup": "Backup: {backup}",
        "none": "nenhum",
        "without_evolving": "{pokemon} sem evoluir",
        "error_cancelled": "Erro ou cancelado",
        "trade_not_complete": "Troca nao completada",
        "room_name": "Nome da sala",
        "empty": "(vazio)",
        "keypad": "Teclado",
        "shift_on": "SHIFT ON",
        "shift_off": "SHIFT OFF",
        "key_select": "SELECT",
        "key_delete_back": "DEL/VOLTAR",
        "btn_yes": "SIM",
        "btn_no": "NAO",
        "btn_cancel": "CANCELAR",
        "btn_confirm": "CONFIRMAR",
        "btn_choose": "ESCOLHER",
        "btn_skip": "PULAR",
        "btn_let_evolve": "DEIXAR EVOLUIR",
        "btn_cancel_evo": "CANCELAR EVO",
        "btn_no_let_evolve": "NAO, DEIXAR EVOLUIR",
        "btn_yes_interrupt": "SIM, INTERROMPER",
        "btn_move_pc": "MOVER P/ PC",
        "btn_withdraw": "RETIRAR",
        "btn_view_pc": "VER PC",
        "btn_view_party": "VER PARTY",
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
        "theme_dark": "Tech Blue",
        "theme_white": "White + Blue",
        "action_title": "Action",
        "action_create_room": "Create Room",
        "action_join_room": "Join Room",
        "choose": "Choose",
        "select_save": "Select Save",
        "self_save_1": "Trade With Myself: Save 1",
        "self_save_2": "Trade With Myself: Save 2",
        "no_saves": "No saves found.",
        "selected_save": "Selected save",
        "save_file": "File",
        "save_folder": "Folder",
        "save_pick_hint": "Choose the save that will enter the trade.",
        "choose_source": "Choose Source",
        "source_helper": "Choose where the Pokemon for the trade comes from.",
        "room": "Room",
        "password": "Password",
        "no_name": "(no name)",
        "no_password": "(no password)",
        "share_room": "Share these details with your partner to enter the same room.",
        "choose_pokemon": "Choose Pokemon",
        "waiting_partner": "Waiting for second player",
        "no_pokemon": "No Pokemon found.",
        "loading_sprite": "Loading sprite...",
        "loading_sprites": "Loading sprites...",
        "no_sprite": "No sprite",
        "item_none": "No item",
        "item_label": "Item: {name}",
        "item_label_none": "Item: none",
        "level": "Level: {level}",
        "level_short": "Level {level}",
        "level_tag": "Lv. {level}",
        "level_unknown": "Level ?",
        "moves": "Moves",
        "no_moves": "No moves",
        "party": "Party",
        "pc": "PC",
        "your_party": "Your Party",
        "your_pc": "Your PC",
        "party_save": "Party Save {slot}",
        "party_save_named": "Party Save {slot}: {name}",
        "pc_save": "PC Save {slot}",
        "pc_save_named": "PC Save {slot}: {name}",
        "connecting": "Connecting",
        "connecting_server": "Connecting to server{dots}",
        "please_wait": "Please wait...",
        "leave_room_title": "Leave room?",
        "leave_room_question": "Do you want to close this room?",
        "leave_room_help": "You and your partner will return to the menu.",
        "leave_room_more": "For more trades, choose A=NO.",
        "deposit_title": "Move to PC?",
        "deposit_question": "Send {name} to the PC?",
        "deposit_help": "It will go to the first free slot.",
        "backup_help": "A save backup will be created first.",
        "withdraw_title": "Withdraw from PC?",
        "withdraw_question": "Bring {name} to the Party?",
        "withdraw_from": "From: {box}",
        "withdraw_help": "It will be added to the next free Party slot.",
        "notice": "Notice",
        "no_details": "No details.",
        "trade_cancelled_room_open": "The trade was cancelled. The room remains open.",
        "incompatible_move_title": "Incompatible move {current}/{total}",
        "unsupported_move": "Unsupported: {move}",
        "choose_replacement": "Choose a replacement or leave it empty.",
        "empty_move": "(leave empty)",
        "cancel_trade_title": "Cancel trade?",
        "cancel_trade_question": "Cancel this Pokemon trade?",
        "save_not_modified": "Your save will NOT be modified.",
        "room_stays_open": "The room remains open - you will choose another Pokemon.",
        "room_open_short": "Room open",
        "confirm_trade": "Confirm trade",
        "your_pokemon": "Your Pokemon",
        "opponent": "Opponent",
        "trade_evolution": "Trade evolution",
        "confirm_cancel": "Confirm cancel",
        "wants_evolve": "{source} wants to evolve into {target}.",
        "cancel_evolution_question": "Do you want to cancel this evolution?",
        "cancel_evolution_hint": "B lets the animation end in the evolved form.",
        "are_you_sure": "Are you sure?",
        "cancel_evolution_confirm": "This will stop {source} from evolving into {target}.",
        "cancel_evolution_result": "The trade continues, but the received Pokemon stays unevolved.",
        "trading": "Trading",
        "processing": "Processing...",
        "result": "Result",
        "trade_complete": "Trade complete!",
        "received": "Received: {pokemon}",
        "backup": "Backup: {backup}",
        "none": "none",
        "without_evolving": "{pokemon} without evolving",
        "error_cancelled": "Error or cancelled",
        "trade_not_complete": "Trade not completed",
        "room_name": "Room name",
        "empty": "(empty)",
        "keypad": "Keyboard",
        "shift_on": "SHIFT ON",
        "shift_off": "SHIFT OFF",
        "key_select": "SELECT",
        "key_delete_back": "DEL/BACK",
        "btn_yes": "YES",
        "btn_no": "NO",
        "btn_cancel": "CANCEL",
        "btn_confirm": "CONFIRM",
        "btn_choose": "CHOOSE",
        "btn_skip": "SKIP",
        "btn_let_evolve": "LET EVOLVE",
        "btn_cancel_evo": "CANCEL EVO",
        "btn_no_let_evolve": "NO, LET EVOLVE",
        "btn_yes_interrupt": "YES, STOP",
        "btn_move_pc": "MOVE TO PC",
        "btn_withdraw": "WITHDRAW",
        "btn_view_pc": "VIEW PC",
        "btn_view_party": "VIEW PARTY",
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
        "theme_dark": "Azul tecnico",
        "theme_white": "Blanco + azul",
        "action_title": "Accion",
        "action_create_room": "Crear sala",
        "action_join_room": "Entrar en sala",
        "choose": "Elegir",
        "select_save": "Seleccionar save",
        "self_save_1": "Intercambiar conmigo: Save 1",
        "self_save_2": "Intercambiar conmigo: Save 2",
        "no_saves": "No se encontraron saves.",
        "selected_save": "Save seleccionado",
        "save_file": "Archivo",
        "save_folder": "Carpeta",
        "save_pick_hint": "Elige el save que entrara en el intercambio.",
        "choose_source": "Elegir origen",
        "source_helper": "Elige de donde sale el Pokemon para el intercambio.",
        "room": "Sala",
        "password": "Contrasena",
        "no_name": "(sin nombre)",
        "no_password": "(sin contrasena)",
        "share_room": "Comparte estos datos con tu companero para entrar en la misma sala.",
        "choose_pokemon": "Elegir Pokemon",
        "waiting_partner": "Esperando segundo jugador",
        "no_pokemon": "No se encontraron Pokemon.",
        "loading_sprite": "Cargando sprite...",
        "loading_sprites": "Cargando sprites...",
        "no_sprite": "Sin sprite",
        "item_none": "Sin item",
        "item_label": "Item: {name}",
        "item_label_none": "Item: ninguno",
        "level": "Nivel: {level}",
        "level_short": "Nivel {level}",
        "level_tag": "Nivel {level}",
        "level_unknown": "Nivel ?",
        "moves": "Movimientos",
        "no_moves": "Sin movimientos",
        "party": "Party",
        "pc": "PC",
        "your_party": "Tu Party",
        "your_pc": "Tu PC",
        "party_save": "Party Save {slot}",
        "party_save_named": "Party Save {slot}: {name}",
        "pc_save": "PC Save {slot}",
        "pc_save_named": "PC Save {slot}: {name}",
        "connecting": "Conectando",
        "connecting_server": "Conectando al servidor{dots}",
        "please_wait": "Espera...",
        "leave_room_title": "Salir de la sala?",
        "leave_room_question": "Quieres cerrar esta sala?",
        "leave_room_help": "Tu y tu companero volveran al menu.",
        "leave_room_more": "Para mas intercambios, elige A=NO.",
        "deposit_title": "Mover al PC?",
        "deposit_question": "Enviar {name} al PC?",
        "deposit_help": "Ira al primer espacio libre.",
        "backup_help": "Primero se creara un backup del save.",
        "withdraw_title": "Retirar del PC?",
        "withdraw_question": "Traer {name} a la Party?",
        "withdraw_from": "De: {box}",
        "withdraw_help": "Se agregara al proximo espacio libre de la Party.",
        "notice": "Aviso",
        "no_details": "Sin detalles.",
        "trade_cancelled_room_open": "El intercambio fue cancelado. La sala sigue abierta.",
        "incompatible_move_title": "Movimiento incompatible {current}/{total}",
        "unsupported_move": "Sin soporte: {move}",
        "choose_replacement": "Elige un reemplazo o dejalo vacio.",
        "empty_move": "(dejar vacio)",
        "cancel_trade_title": "Cancelar intercambio?",
        "cancel_trade_question": "Cancelar el intercambio de este Pokemon?",
        "save_not_modified": "Tu save NO sera modificado.",
        "room_stays_open": "La sala sigue abierta - elegiras otro Pokemon.",
        "room_open_short": "Sala abierta",
        "confirm_trade": "Confirmar intercambio",
        "your_pokemon": "Tu Pokemon",
        "opponent": "Oponente",
        "trade_evolution": "Evolucion por intercambio",
        "confirm_cancel": "Confirmar cancelacion",
        "wants_evolve": "{source} quiere evolucionar a {target}.",
        "cancel_evolution_question": "Quieres cancelar esta evolucion?",
        "cancel_evolution_hint": "B deja que la animacion termine en la forma evolucionada.",
        "are_you_sure": "Estas seguro?",
        "cancel_evolution_confirm": "Esto interrumpira la evolucion de {source} a {target}.",
        "cancel_evolution_result": "El intercambio continua, pero el Pokemon recibido no evoluciona.",
        "trading": "Intercambiando",
        "processing": "Procesando...",
        "result": "Resultado",
        "trade_complete": "Intercambio completo!",
        "received": "Recibido: {pokemon}",
        "backup": "Backup: {backup}",
        "none": "ninguno",
        "without_evolving": "{pokemon} sin evolucionar",
        "error_cancelled": "Error o cancelado",
        "trade_not_complete": "Intercambio no completado",
        "room_name": "Nombre de sala",
        "empty": "(vacio)",
        "keypad": "Teclado",
        "shift_on": "SHIFT ON",
        "shift_off": "SHIFT OFF",
        "key_select": "SELECT",
        "key_delete_back": "DEL/VOLVER",
        "btn_yes": "SI",
        "btn_no": "NO",
        "btn_cancel": "CANCELAR",
        "btn_confirm": "CONFIRMAR",
        "btn_choose": "ELEGIR",
        "btn_skip": "SALTAR",
        "btn_let_evolve": "DEJAR EVOLUCIONAR",
        "btn_cancel_evo": "CANCELAR EVO",
        "btn_no_let_evolve": "NO, DEJAR EVOLUCIONAR",
        "btn_yes_interrupt": "SI, INTERRUMPIR",
        "btn_move_pc": "MOVER AL PC",
        "btn_withdraw": "RETIRAR",
        "btn_view_pc": "VER PC",
        "btn_view_party": "VER PARTY",
        "btn_ok": "OK",
        "btn_back": "VOLVER",
        "btn_change": "CAMBIAR",
    },
}

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


def apply_theme(theme_name):
    global BG, SHELL, SHELL_2, PANEL, PANEL_2, SCREEN, SCREEN_TEXT, BORDER, SHADOW, TEXT, MUTED, ACCENT, OK, RED, WARN
    palette = THEMES.get(str(theme_name or "").strip().lower(), THEMES["pokedex_white"])
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


def t(lang, key, **kwargs):
    language = str(lang or "pt").strip().lower()
    table = STRINGS.get(language, STRINGS["pt"])
    value = table.get(key, STRINGS["pt"].get(key, key))
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return value
    return value


LITERAL_TRANSLATIONS = {
    "en": {
        "Save repetido": "Repeated save",
        "Escolha dois arquivos de save diferentes para trocar comigo.": "Choose two different save files to trade with myself.",
        "Falha ao carregar Party": "Failed to load Party",
        "Falha na validacao": "Validation failed",
        "Pokemon incompativel": "Incompatible Pokemon",
        "Pokemon incompativel com o save de destino.": "Pokemon is incompatible with the target save.",
        "Troca incompativel": "Incompatible trade",
        "Falha ao carregar Pokemon": "Failed to load Pokemon",
        "Pokemon esta no PC": "Pokemon is in the PC",
        "Pressione X para retirar este Pokemon para a Party antes de troca-lo.": "Press X to withdraw this Pokemon to the Party before trading it.",
        "Aguarde a troca terminar antes de mover.": "Wait for the trade to finish before moving Pokemon.",
        "Erro": "Error",
        "Slot do PC nao encontrado.": "PC slot not found.",
        "Save nao carregado.": "Save not loaded.",
        "Nao foi possivel retirar": "Could not withdraw",
        "Nao foi possivel mover": "Could not move",
        "Validando troca local...": "Validating local trade...",
        "Validacoes concluidas. Confirme a troca local.": "Validations complete. Confirm the local trade.",
        "Aplicando troca local...": "Applying local trade...",
        "Troca local concluida!": "Local trade complete!",
        "Troca local cancelada.": "Local trade cancelled.",
        "Conectando...": "Connecting...",
        "Cancelando...": "Cancelling...",
        "Nao foi possivel cancelar agora.": "Could not cancel right now.",
        "Saindo da sala...": "Leaving room...",
    },
    "es": {
        "Save repetido": "Save repetido",
        "Escolha dois arquivos de save diferentes para trocar comigo.": "Elige dos archivos de save diferentes para intercambiar conmigo.",
        "Falha ao carregar Party": "No se pudo cargar la Party",
        "Falha na validacao": "Fallo de validacion",
        "Pokemon incompativel": "Pokemon incompatible",
        "Pokemon incompativel com o save de destino.": "Pokemon incompatible con el save de destino.",
        "Troca incompativel": "Intercambio incompatible",
        "Falha ao carregar Pokemon": "No se pudo cargar Pokemon",
        "Pokemon esta no PC": "Pokemon esta en el PC",
        "Pressione X para retirar este Pokemon para a Party antes de troca-lo.": "Presiona X para retirar este Pokemon a la Party antes de intercambiarlo.",
        "Aguarde a troca terminar antes de mover.": "Espera a que termine el intercambio antes de mover Pokemon.",
        "Erro": "Error",
        "Slot do PC nao encontrado.": "Slot del PC no encontrado.",
        "Save nao carregado.": "Save no cargado.",
        "Nao foi possivel retirar": "No se pudo retirar",
        "Nao foi possivel mover": "No se pudo mover",
        "Validando troca local...": "Validando intercambio local...",
        "Validacoes concluidas. Confirme a troca local.": "Validaciones concluidas. Confirma el intercambio local.",
        "Aplicando troca local...": "Aplicando intercambio local...",
        "Troca local concluida!": "Intercambio local concluido!",
        "Troca local cancelada.": "Intercambio local cancelado.",
        "Conectando...": "Conectando...",
        "Cancelando...": "Cancelando...",
        "Nao foi possivel cancelar agora.": "No se pudo cancelar ahora.",
        "Saindo da sala...": "Saliendo de la sala...",
    },
}


def translate_literal(lang, value):
    text_value = str(value or "")
    language = str(lang or "pt").strip().lower()
    return LITERAL_TRANSLATIONS.get(language, {}).get(text_value, text_value)


def screen_title(lang, key, **kwargs):
    compact = {
        "select_save": {"pt": "Selecionar save", "en": "Select save", "es": "Elegir save"},
        "self_save_1": {"pt": "Save 1", "en": "Save 1", "es": "Save 1"},
        "self_save_2": {"pt": "Save 2", "en": "Save 2", "es": "Save 2"},
        "choose_source": {"pt": "Origem", "en": "Source", "es": "Origen"},
        "choose_pokemon": {"pt": "Pokemon", "en": "Pokemon", "es": "Pokemon"},
        "waiting_partner": {"pt": "Aguardando", "en": "Waiting", "es": "Esperando"},
        "incompatible_move_title": {
            "pt": "Move invalido {current}/{total}",
            "en": "Bad move {current}/{total}",
            "es": "Move invalido {current}/{total}",
        },
        "confirm_cancel": {"pt": "Cancelar evo?", "en": "Cancel evo?", "es": "Cancelar evo?"},
        "trade_evolution": {"pt": "Evolucao", "en": "Evolution", "es": "Evolucion"},
        "confirm_trade": {"pt": "Confirmar troca", "en": "Confirm trade", "es": "Confirmar trade"},
        "cancel_trade_title": {"pt": "Cancelar troca?", "en": "Cancel trade?", "es": "Cancelar trade?"},
        "leave_room_title": {"pt": "Sair da sala?", "en": "Leave room?", "es": "Salir sala?"},
        "deposit_title": {"pt": "Enviar ao PC?", "en": "Send to PC?", "es": "Enviar al PC?"},
        "withdraw_title": {"pt": "Retirar do PC?", "en": "Withdraw?", "es": "Retirar?"},
        "notice": {"pt": "Aviso", "en": "Notice", "es": "Aviso"},
        "connecting": {"pt": "Conectando", "en": "Connecting", "es": "Conectando"},
        "trading": {"pt": "Trocando", "en": "Trading", "es": "Intercambio"},
        "result": {"pt": "Resultado", "en": "Result", "es": "Resultado"},
    }
    language = str(lang or "pt").strip().lower()
    value = compact.get(key, {}).get(language) or compact.get(key, {}).get("pt")
    if value:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return value
    return t(language, key, **kwargs)


POKEMON_SPRITE_ASSET_DIR = Path(__file__).resolve().parent / "assets" / "pokemon_sprites"
UI_FONT_PATH = Path(__file__).resolve().parent / "assets" / "fonts" / "Pokemon Classic.ttf"
POKECABLE_TITLE_FONT_PATH = Path(__file__).resolve().parent / "assets" / "fonts" / "Ketchum.otf"
SPRITE_CACHE_VERSION = "pixel-v1"
SPRITE_LOADING_MAX_SECONDS = float(os.getenv("POKECABLE_SPRITE_LOADING_MAX_SECONDS", "3"))

SCROLL_STATE = {}
FONT_CACHE = {}
TITLE_FONT_CACHE = {}
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
TYPE_LABELS_BY_LANG = {
    "pt": TYPE_LABELS,
    "en": {
        "normal": "Normal",
        "fire": "Fire",
        "water": "Water",
        "electric": "Electric",
        "grass": "Grass",
        "ice": "Ice",
        "fighting": "Fighting",
        "poison": "Poison",
        "ground": "Ground",
        "flying": "Flying",
        "psychic": "Psychic",
        "bug": "Bug",
        "rock": "Rock",
        "ghost": "Ghost",
        "dragon": "Dragon",
        "dark": "Dark",
        "steel": "Steel",
        "fairy": "Fairy",
    },
    "es": {
        "normal": "Normal",
        "fire": "Fuego",
        "water": "Agua",
        "electric": "Electrico",
        "grass": "Planta",
        "ice": "Hielo",
        "fighting": "Lucha",
        "poison": "Veneno",
        "ground": "Tierra",
        "flying": "Volador",
        "psychic": "Psiquico",
        "bug": "Bicho",
        "rock": "Roca",
        "ghost": "Fantasma",
        "dragon": "Dragon",
        "dark": "Siniestro",
        "steel": "Acero",
        "fairy": "Hada",
    },
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


def pokemon_display_name(pokemon, fallback="Pokemon"):
    pokemon = pokemon or {}
    return (
        pokemon.get("nickname")
        or pokemon.get("species_name")
        or pokemon.get("name")
        or pokemon.get("display_summary")
        or pokemon.get("display")
        or fallback
    )


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


def move_display_entries(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    moves = (pokemon or {}).get("moves") or raw.get("moves") or []
    names = (pokemon or {}).get("move_names") or raw.get("move_names") or []
    canonical_moves = (canonical.get("moves") if isinstance(canonical, dict) else []) or []
    raw_move_details = raw.get("move_details") if isinstance(raw, dict) else []
    top_move_details = (pokemon or {}).get("move_details") if isinstance(pokemon, dict) else []
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
        if not move_detail and idx < len(raw_move_details) and isinstance(raw_move_details[idx], dict):
            move_detail = raw_move_details[idx]
        if isinstance(move_detail, dict):
            current_pp = move_detail.get("pp")
            max_pp = move_detail.get("max_pp")
        try:
            _ensure_backend_import_path()
            from data.moves import move_base_pp  # type: ignore

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
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    national_dex_id = int((pokemon or {}).get("national_dex_id") or raw.get("national_dex_id") or canonical.get("species_national_id") or 0)
    experience = canonical.get("experience") if isinstance(canonical, dict) else None
    if experience in (None, ""):
        experience = (pokemon or {}).get("experience") or raw.get("experience")
    level = int((pokemon or {}).get("level") or 0)
    if experience is None:
        return 0.0, 0, 0
    try:
        _ensure_backend_import_path()
        from data.growth_rates import experience_for_level, growth_rate_id_for_national, level_from_species_experience  # type: ignore

        if national_dex_id <= 0:
            generation = int((pokemon or {}).get("generation") or raw.get("generation") or (canonical.get("source_generation") if isinstance(canonical, dict) else 0) or 0)
            internal_species_id = int((pokemon or {}).get("species_id") or raw.get("species_id") or canonical.get("species_id") or 0)
            if generation and internal_species_id:
                try:
                    from data.species import native_to_national  # type: ignore
                    national_dex_id = int(native_to_national(generation, internal_species_id) or 0)
                except Exception:
                    national_dex_id = 0
        if national_dex_id <= 0:
            return 0.0, 0, 0
        species_id = national_dex_id
        growth_rate_id = growth_rate_id_for_national(species_id)
        if growth_rate_id is None:
            return 0.0, 0, 0
        current_level = max(1, min(100, int(level_from_species_experience(species_id, int(experience)))))
        next_level = min(100, current_level + 1)
        current_xp = int(experience)
        if next_level <= current_level:
            return 1.0, current_xp, current_xp
        min_xp = int(experience_for_level(growth_rate_id, current_level))
        max_xp = int(experience_for_level(growth_rate_id, next_level))
        span = max(1, max_xp - min_xp)
        filled = max(0.0, min(1.0, (current_xp - min_xp) / span))
        return filled, current_xp, max_xp
    except Exception:
        return 0.0, 0, 0


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
    cursor_x = x
    for type_name in type_names[:2]:
        label = type_label(type_name, language)
        badge_w = min(82, max(42, font_obj.size(label)[0] + 14))
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
    key = (int(size), bool(bold))
    cached = FONT_CACHE.get(key)
    if cached is not None:
        return cached

    adjusted_size = max(8, int(size) - 2 if UI_FONT_PATH.name == "Pokemon Classic.ttf" else int(size))

    candidates = [
        UI_FONT_PATH,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            FONT_CACHE[key] = pygame.font.Font(path, adjusted_size)
            return FONT_CACHE[key]
    FONT_CACHE[key] = pygame.font.SysFont(None, adjusted_size, bold=bold)
    return FONT_CACHE[key]


def title_font(size):
    key = int(size)
    cached = TITLE_FONT_CACHE.get(key)
    if cached is not None:
        return cached

    if POKECABLE_TITLE_FONT_PATH.exists():
        TITLE_FONT_CACHE[key] = pygame.font.Font(POKECABLE_TITLE_FONT_PATH, size)
        return TITLE_FONT_CACHE[key]
    TITLE_FONT_CACHE[key] = font(size, False)
    return TITLE_FONT_CACHE[key]


def render_title_sweep(text_surface, progress):
    width, height = text_surface.get_size()
    sweep_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    trail_w = max(34, width // 3)
    sweep_x = int(progress * (width + trail_w * 2)) - trail_w
    base = (255, 255, 255)
    glow = (102, 184, 255)
    hot = (200, 242, 255)
    sweep_surface.fill((*base, 255))
    for x in range(width):
        distance = abs(x - (sweep_x + trail_w // 2))
        if distance > trail_w:
            continue
        strength = 1.0 - (distance / trail_w)
        if strength <= 0:
            continue
        if strength < 0.5:
            blend = strength / 0.5
            color = tuple(int(base[i] * (1.0 - blend) + glow[i] * blend) for i in range(3))
        else:
            blend = (strength - 0.5) / 0.5
            color = tuple(int(glow[i] * (1.0 - blend) + hot[i] * blend) for i in range(3))
        pygame.draw.line(sweep_surface, color + (255,), (x, 0), (x, height))
    sweep_surface.blit(text_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return sweep_surface


def draw_lens_pulse(screen, center, progress):
    outer_radius = 52
    inner_radius = 20
    glow_surface = pygame.Surface((outer_radius * 2 + 2, outer_radius * 2 + 2), pygame.SRCALPHA)
    pulse_radius = int(inner_radius + (outer_radius - inner_radius) * progress)
    pulse_alpha = int(210 * (1.0 - progress))
    if pulse_alpha <= 0:
        return
    pygame.draw.circle(
        glow_surface,
        (120, 220, 255, pulse_alpha),
        (outer_radius + 1, outer_radius + 1),
        pulse_radius,
        width=max(1, 8 - int(progress * 7)),
    )
    pygame.draw.circle(
        glow_surface,
        (255, 255, 255, int(120 * (1.0 - progress))),
        (outer_radius + 1, outer_radius + 1),
        max(4, int(10 - progress * 7)),
    )
    screen.blit(glow_surface, (center[0] - outer_radius - 1, center[1] - outer_radius - 1))


def draw_glass_panel(screen, area, progress, base_color=(170, 188, 214)):
    glass = pygame.Surface(area.size, pygame.SRCALPHA)
    glass.fill((235, 242, 250, 96))
    pygame.draw.rect(glass, (255, 255, 255, 54), glass.get_rect(), 1, border_radius=6)
    shimmer_w = max(24, area.w // 5)
    shimmer_x = int(progress * (area.w + shimmer_w * 2)) - shimmer_w
    for x in range(area.w):
        distance = abs(x - (shimmer_x + shimmer_w // 2))
        if distance > shimmer_w:
            continue
        strength = 1.0 - (distance / shimmer_w)
        alpha = int(110 * strength)
        color = (
            min(255, base_color[0] + int(42 * strength)),
            min(255, base_color[1] + int(54 * strength)),
            min(255, base_color[2] + int(68 * strength)),
            alpha,
        )
        pygame.draw.line(glass, color, (x, 0), (x, area.h))
    screen.blit(glass, area.topleft)


def draw_digital_visor(screen, area, progress):
    visor = pygame.Surface(area.size, pygame.SRCALPHA)
    visor.fill((196, 206, 214, 255))
    glow_span = area.w + area.h
    glow_pos = int(progress * (glow_span + 40)) - 20
    for x in range(area.w):
        for y in range(0, area.h, 2):
            distance = abs((x + y) - glow_pos)
            if distance > 18:
                continue
            strength = 1.0 - (distance / 18.0)
            alpha = int(128 * strength)
            pygame.draw.line(visor, (170, 232, 206, alpha), (x, y), (x, min(area.h, y + 1)))
    for y in range(2, area.h - 2, 6):
        pygame.draw.line(visor, (236, 242, 236, 36), (2, y), (area.w - 3, y), 1)
    pygame.draw.rect(visor, (255, 255, 255, 70), visor.get_rect(), 1)
    screen.blit(visor, area.topleft)


def text(surface, fnt, value, x, y, color=None, max_w=None):
    if color is None:
        color = TEXT
    value = str(value or "")
    if max_w is not None:
        value = fit_text(fnt, value, max_w)
    surface.blit(fnt.render(value, True, color), (x, y))


def fit_text(fnt, value, max_w):
    value = str(value or "")
    if max_w is None or fnt.size(value)[0] <= max_w:
        return value
    ellipsis = "..."
    if fnt.size(ellipsis)[0] > max_w:
        return ""
    while value and fnt.size(value + ellipsis)[0] > max_w:
        value = value[:-1]
    return value.rstrip() + ellipsis


def text_center(surface, fnt, value, area, color=None):
    if color is None:
        color = TEXT
    label = fit_text(fnt, value, max(1, area.w - 4))
    rendered = fnt.render(label, True, color)
    surface.blit(rendered, rendered.get_rect(center=area.center))


def text_right(surface, fnt, value, area, color=None):
    if color is None:
        color = TEXT
    label = fit_text(fnt, value, area.w)
    rendered = fnt.render(label, True, color)
    screen_area = rendered.get_rect()
    screen_area.midright = area.midright
    surface.blit(rendered, screen_area)


def wrap_text(surface, fnt, value, area, color=None, line_gap=4, max_lines=None):
    if color is None:
        color = TEXT
    words = str(value or "").replace("\n", " \n ").split(" ")
    lines = []
    current = ""
    for word in words:
        if word == "\n":
            if current:
                lines.append(current)
                current = ""
            continue
        candidate = word if not current else f"{current} {word}"
        if fnt.size(candidate)[0] <= area.w:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    line_h = fnt.get_linesize()
    max_by_height = max(1, area.h // max(1, line_h + line_gap))
    limit = min(max_lines or max_by_height, max_by_height)
    for idx, line in enumerate(lines[:limit]):
        if idx == limit - 1 and len(lines) > limit:
            line = fit_text(fnt, line + " ...", area.w)
        text(surface, fnt, line, area.x, area.y + idx * (line_h + line_gap), color, area.w)
    return area.y + min(len(lines), limit) * (line_h + line_gap)


def normalized_rect(area):
    try:
        normalized = pygame.Rect(area)
    except (TypeError, ValueError):
        try:
            normalized = pygame.Rect(int(area.x), int(area.y), int(area.w), int(area.h))
        except (AttributeError, TypeError, ValueError):
            return None
    normalized.normalize()
    if normalized.w <= 0 or normalized.h <= 0:
        return None
    return normalized


def rect(surface, color, area, radius=0):
    normalized = normalized_rect(area)
    if not normalized:
        logger.warning("Skipping invalid rect draw: area=%r radius=%r", area, radius)
        return None
    try:
        safe_radius = max(0, min(int(radius or 0), min(normalized.w, normalized.h) // 2))
        return pygame.draw.rect(surface, color, normalized, border_radius=safe_radius)
    except (TypeError, ValueError) as exc:
        logger.warning("Skipping invalid rect draw: area=%r color=%r radius=%r error=%s", area, color, radius, exc)
        return None


def compact_action_label(value):
    normalized = str(value or "").strip().upper()
    replacements = {
        "VOLTAR": "Voltar",
        "BACK": "Back",
        "VOLVER": "Volver",
        "ALTERAR": "Alterar",
        "CHANGE": "Change",
        "CAMBIAR": "Cambiar",
        "CANCELAR": "Cancelar",
        "CANCEL": "Cancel",
        "CONFIRMAR": "Confirmar",
        "CONFIRM": "Confirm",
        "ESCOLHER": "Escolher",
        "CHOOSE": "Choose",
        "ELEGIR": "Elegir",
        "PULAR": "Pular",
        "SKIP": "Skip",
        "SALTAR": "Saltar",
        "MOVER P/ PC": "PC",
        "MOVE TO PC": "PC",
        "MOVER AL PC": "PC",
        "RETIRAR": "Retirar",
        "WITHDRAW": "Retirar",
        "VER PC": "Ver PC",
        "VIEW PC": "View PC",
        "VER PARTY": "Party",
        "VIEW PARTY": "Party",
        "SELECT": "Select",
        "DEL/VOLTAR": "Del",
        "DEL/BACK": "Del",
        "DEL/VOLVER": "Del",
        "DEIXAR EVOLUIR": "Evoluir",
        "LET EVOLVE": "Evolve",
        "DEJAR EVOLUCIONAR": "Evoluir",
        "CANCELAR EVO": "Cancelar",
        "CANCEL EVO": "Cancel",
        "NAO, DEIXAR EVOLUIR": "Evoluir",
        "NO, LET EVOLVE": "Evolve",
        "NO, DEJAR EVOLUCIONAR": "Evoluir",
        "SIM, INTERROMPER": "Interromper",
        "YES, STOP": "Stop",
        "SI, INTERRUMPIR": "Interrumpir",
    }
    return replacements.get(normalized, str(value or ""))


def button(surface, fnt, label, desc, x, y, width=None):
    desc = compact_action_label(desc)
    button_f = font(12)
    cap_f = font(11, True)
    width = int(width or max(54, min(118, button_f.size(str(desc or ""))[0] + 30)))
    area = pygame.Rect(x, y, width, 20)
    rect(surface, (209, 230, 248), area.move(1, 1), 4)
    rect(surface, (247, 252, 255), area, 4)
    pygame.draw.rect(surface, BORDER, area, 1, border_radius=4)
    cap = pygame.Rect(x + 3, y + 3, 16, 14)
    rect(surface, ACCENT, cap, 4)
    text_center(surface, cap_f, label, cap, SCREEN_TEXT)
    text(surface, button_f, desc, x + 24, y + 4, TEXT, width - 28)


def draw_footer_actions(screen, fnt, actions):
    draw_footer_bar(screen)
    del fnt
    footer = pygame.Rect(22, SCREEN_H - 28, SCREEN_W - 44, 22)
    gap = 6
    measure_f = font(12)
    compact_actions = [(label, compact_action_label(desc)) for label, desc in actions]
    widths = [max(54, min(118, measure_f.size(str(desc or ""))[0] + 32)) for _, desc in compact_actions]
    total = sum(widths) + gap * max(0, len(widths) - 1)
    if total > footer.w:
        width = max(50, (footer.w - gap * max(0, len(widths) - 1)) // max(1, len(widths)))
        widths = [width] * len(widths)
    x = footer.x
    for (label, desc), width in zip(compact_actions, widths):
        button(screen, None, label, desc, x, footer.y, width)
        x += width + gap


class PokedexFrame:
    def __init__(self):
        self.content = pygame.Rect(24, 84, SCREEN_W - 48, SCREEN_H - HEADER_H - FOOTER_H - 56)
        self.left_panel = pygame.Rect(28, 92, 269, 323)
        self.right_panel = pygame.Rect(337, 96, 286, 320)
        self.side_screen = pygame.Rect(390, 124, 168, 54)
        self.keypad = pygame.Rect(342, 214, 256, 144)
        self.footer = pygame.Rect(22, SCREEN_H - 28, SCREEN_W - 44, 22)
        self.modal = pygame.Rect(58, 118, SCREEN_W - 116, 220)

    def __getattr__(self, name):
        return getattr(self.content, name)

    def __getitem__(self, name):
        return getattr(self, name)


def right_info_panel(layout, top_offset=30, inset_x=2, bottom_pad=30):
    base = layout.right_panel
    return pygame.Rect(base.x + inset_x, base.y + top_offset, base.w - inset_x * 2, base.h - bottom_pad)


def right_visor_rect(panel):
    top_pad = 16
    side_pad = 16
    height = 100
    return pygame.Rect(panel.x + side_pad, panel.y + top_pad, panel.w - side_pad * 2, height)


def draw_right_panel_frame(screen, panel, progress=None, glass=False):
    if glass:
        draw_glass_panel(screen, panel, progress if progress is not None else 0.0)
    else:
        rect(screen, PANEL_2, panel, 6)
    pygame.draw.rect(screen, BORDER, panel, 2, border_radius=6)


def draw_pokedex_shell(screen, title="", subtitle=""):
    screen.fill(BG)
    frame = PokedexFrame()

    left_body = pygame.Rect(10, 16, 302, 418)
    right_points = [
        (330, 54), (418, 54), (436, 55), (454, 59), (472, 66), (490, 76), (510, 88), (530, 100), (554, 108), (630, 108),
        (630, 426), (330, 426),
    ]
    hinge = pygame.Rect(307, 54, 25, 370)

    rect(screen, SHADOW, left_body.move(0, 8), 15)
    pygame.draw.polygon(screen, SHADOW, [(x, y + 8) for x, y in right_points])
    rect(screen, SHELL, left_body, 15)
    pygame.draw.polygon(screen, SHELL_2, right_points)
    pygame.draw.lines(screen, BORDER, True, right_points, 2)
    pygame.draw.rect(screen, BORDER, left_body, 2, border_radius=15)

    hinge_body = pygame.Rect(hinge.x + 1, hinge.y + 1, hinge.w - 2, hinge.h - 2)
    pygame.draw.rect(screen, SHELL_2, hinge_body, border_radius=6)
    highlight = pygame.Rect(hinge.x + 4, hinge.y + 4, 4, hinge.h - 8)
    pygame.draw.rect(screen, SHELL, highlight, border_radius=3)
    for offset in (18, hinge.h - 22):
        pygame.draw.line(screen, BORDER, (hinge.x + 2, hinge.y + offset), (hinge.right - 2, hinge.y + offset), 2)
    pygame.draw.rect(screen, BORDER, hinge_body, 2, border_radius=6)

    # Top optical cluster.
    if LENS_PULSE_STATE["title"] != title:
        LENS_PULSE_STATE["title"] = title
        LENS_PULSE_STATE["start_time"] = time.perf_counter()
    pygame.draw.circle(screen, SCREEN, (55, 57), 33)
    pygame.draw.circle(screen, (237, 249, 255), (55, 57), 28)
    pygame.draw.circle(screen, ACCENT, (55, 57), 23)
    lens_elapsed = max(0.0, time.perf_counter() - LENS_PULSE_STATE["start_time"])
    lens_duration = 0.9
    if lens_elapsed <= lens_duration:
        draw_lens_pulse(screen, (55, 57), lens_elapsed / lens_duration)
    pygame.draw.circle(screen, (144, 229, 252), (47, 48), 8)
    pygame.draw.circle(screen, (255, 255, 255), (42, 41), 5)
    for x, color in ((116, RED), (144, WARN), (172, OK)):
        pygame.draw.circle(screen, BORDER, (x, 35), 10)
        pygame.draw.circle(screen, color, (x, 35), 7)

    title_panel = pygame.Rect(93, 48, 196, 34)
    if not TITLE_SWEEP_STATE["start_time"]:
        TITLE_SWEEP_STATE["start_time"] = time.perf_counter()
    sweep_elapsed = max(0.0, time.perf_counter() - TITLE_SWEEP_STATE["start_time"])
    sweep_duration = 1.1
    if title:
        title_f = title_font(12)
        for candidate_size in (32, 30, 28, 26, 24, 22, 20, 18, 16, 14, 12):
            candidate = title_font(candidate_size)
            if candidate.size(str(title))[0] <= title_panel.w - 18:
                title_f = candidate
                break
        title_surface = title_f.render(str(title), True, (255, 255, 255))
        sweep_surface = render_title_sweep(title_surface, (sweep_elapsed % sweep_duration) / sweep_duration)
        title_y = title_panel.y + max(0, (title_panel.h - title_surface.get_height()) // 2)
        screen.blit(sweep_surface, (title_panel.x + 9, title_y))
    if subtitle:
        text(screen, font(13), subtitle, title_panel.x + 10, title_panel.bottom + 3, MUTED, title_panel.w - 20)

    return frame


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
            bounds = surface.get_bounding_rect(min_alpha=1)
            if bounds.width > 0 and bounds.height > 0:
                cropped = surface.subsurface(bounds).copy()
                padded = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                pad_x = (surface.get_width() - cropped.get_width()) // 2
                pad_y = (surface.get_height() - cropped.get_height()) // 2
                padded.blit(cropped, (pad_x, pad_y))
                surface = padded
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
    _, _, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, "PokeCable")

    items = [
        t(language, "menu_access_room"),
        t(language, "menu_self_trade"),
        t(language, "menu_config"),
        t(language, "menu_exit"),
    ]
    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 6)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=6)
    text(screen, small_f, t(language, "menu_title"), list_panel.x + 14, list_panel.y + 14, MUTED, list_panel.w - 28)

    for idx, item in enumerate(items):
        y = list_panel.y + 46 + idx * 48
        row = pygame.Rect(list_panel.x + 10, y, list_panel.w - 20, 38)
        color = SCREEN if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, item, row.x + 9, row.y + 9, color, row.w - 18)

    info_panel = right_info_panel(layout)
    rect(screen, PANEL_2, info_panel, 6)
    pygame.draw.rect(screen, BORDER, info_panel, 2, border_radius=6)
    title_rect = right_visor_rect(info_panel)
    if MENU_VISOR_STATE["title"] != "menu":
        MENU_VISOR_STATE["title"] = "menu"
        MENU_VISOR_STATE["start_time"] = time.perf_counter()
    visor_elapsed = max(0.0, time.perf_counter() - MENU_VISOR_STATE["start_time"])
    visor_duration = 1.2
    draw_digital_visor(screen, title_rect, min(visor_elapsed / visor_duration, 1.0))
    pygame.draw.rect(screen, BORDER, title_rect, 2)
    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))])


def draw_config_menu(screen, fonts, selected, language, theme):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, t(language, "config_title"))

    items = [
        (t(language, "config_language"), t(language, f"lang_{language}")),
        (t(language, "config_theme"), theme_display_name(theme)),
    ]
    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 6)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=6)
    for idx, (label, value) in enumerate(items):
        y = list_panel.y + 34 + idx * 76
        row = pygame.Rect(list_panel.x + 12, y, list_panel.w - 24, 56)
        color = SCREEN if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
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
    rect(screen, PANEL, list_panel, 6)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=6)
    text(screen, small_f, t(language, "choose"), list_panel.x + 14, list_panel.y + 14, MUTED)

    for idx, item in enumerate(items):
        y = list_panel.y + 46 + idx * 50
        row = pygame.Rect(list_panel.x + 10, y, list_panel.w - 20, 40)
        color = SCREEN if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
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
    rect(screen, PANEL, display_panel, 6)
    pygame.draw.rect(screen, BORDER, display_panel, 2, border_radius=6)
    screen_rect = pygame.Rect(display_panel.x + 18, display_panel.y + 30, display_panel.w - 36, 92)
    rect(screen, SCREEN, screen_rect, 6)
    pygame.draw.rect(screen, BORDER, screen_rect, 2, border_radius=6)
    text(screen, tiny_f, title, screen_rect.x + 12, screen_rect.y + 10, (142, 189, 224), screen_rect.w - 24)
    value_area = pygame.Rect(screen_rect.x + 12, screen_rect.y + 38, screen_rect.w - 24, 34)
    text(screen, body_f, display_value if display_value else t(language, "empty"), value_area.x, value_area.y, SCREEN_TEXT, value_area.w)
    text(screen, tiny_f, shift_label, display_panel.x + 18, screen_rect.bottom + 18, MUTED, display_panel.w - 36)
    pygame.draw.circle(screen, ACCENT if shift else MUTED, (display_panel.x + 30, screen_rect.bottom + 56), 8)
    pygame.draw.circle(screen, WARN, (display_panel.x + 58, screen_rect.bottom + 56), 8)
    rect(screen, SCREEN, pygame.Rect(display_panel.x + 86, screen_rect.bottom + 48, display_panel.w - 124, 16), 4)

    chars = keyboard_chars(shift)
    rect(screen, PANEL, key_panel, 6)
    pygame.draw.rect(screen, BORDER, key_panel, 2, border_radius=6)
    top_display = pygame.Rect(key_panel.x + 18, key_panel.y + 18, key_panel.w - 36, 34)
    rect(screen, SCREEN, top_display, 5)
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
        rect(screen, ACCENT if selected else PANEL_2, key_rect, 5)
        pygame.draw.rect(screen, BORDER, key_rect, 1, border_radius=5)
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
        rect(screen, ACCENT if selected else PANEL_2, key_rect, 5)
        pygame.draw.rect(screen, BORDER, key_rect, 1, border_radius=5)
        label_surface = special_font.render(label, True, SCREEN if selected else TEXT)
        screen.blit(label_surface, label_surface.get_rect(center=key_rect.center))

    draw_footer_actions(screen, tiny_f, [("A", t(language, "key_select")), ("B", t(language, "key_delete_back"))])


def draw_select_save(screen, fonts, selected, saves, title=None, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, title or screen_title(language, "select_save"))
    list_panel = layout.left_panel
    detail_panel = right_info_panel(layout)

    rect(screen, PANEL, list_panel, 6)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=6)
    draw_right_panel_frame(screen, detail_panel)

    if not saves:
        message_screen = pygame.Rect(list_panel.x + 18, list_panel.y + 34, list_panel.w - 36, 120)
        rect(screen, SCREEN, message_screen, 6)
        pygame.draw.rect(screen, BORDER, message_screen, 2, border_radius=6)
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
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        wrap_text(screen, tiny_f, save_path.name, pygame.Rect(row.x + 9, row.y + 4, row.w - 18, row.h - 6), color, line_gap=0, max_lines=2)
    screen.set_clip(previous_clip)
    draw_scrollbar(screen, list_panel, scroll, len(saves), visible)

    selected_save = saves[selected] if 0 <= selected < len(saves) else saves[0]
    screen_rect = right_visor_rect(detail_panel)
    selected_title = f"select_save:{selected_save.name}"
    if SELECT_SAVE_VISOR_STATE["title"] != selected_title:
        SELECT_SAVE_VISOR_STATE["title"] = selected_title
        SELECT_SAVE_VISOR_STATE["start_time"] = time.perf_counter()
    visor_elapsed = max(0.0, time.perf_counter() - SELECT_SAVE_VISOR_STATE["start_time"])
    draw_digital_visor(screen, screen_rect, min(visor_elapsed / 1.2, 1.0))
    pygame.draw.rect(screen, BORDER, screen_rect, 2)
    text(screen, tiny_f, t(language, "selected_save"), screen_rect.x + 12, screen_rect.y + 8, (142, 189, 224), screen_rect.w - 24)
    wrap_text(screen, tiny_f, selected_save.name, pygame.Rect(screen_rect.x + 12, screen_rect.y + 28, screen_rect.w - 24, 26), SCREEN_TEXT, line_gap=1, max_lines=2)

    text(screen, small_f, t(language, "save_file"), detail_panel.x + 18, detail_panel.y + 124, TEXT, detail_panel.w - 36)
    wrap_text(screen, tiny_f, selected_save.name, pygame.Rect(detail_panel.x + 18, detail_panel.y + 150, detail_panel.w - 36, 48), MUTED, line_gap=1, max_lines=3)
    parent_name = selected_save.parent.name or str(selected_save.parent)
    text(screen, small_f, t(language, "save_folder"), detail_panel.x + 18, detail_panel.y + 206, TEXT, detail_panel.w - 36)
    text(screen, tiny_f, "-" if parent_name == "." else parent_name, detail_panel.x + 18, detail_panel.y + 232, MUTED, detail_panel.w - 36)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))])


def draw_select_pokemon_source(screen, fonts, selected, status="", room_name="", room_password="", language="pt"):
    _, _, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "choose_source"))

    items = [t(language, "party"), t(language, "pc")]
    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 6)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=6)
    text(screen, small_f, t(language, "choose"), list_panel.x + 14, list_panel.y + 14, MUTED)

    for idx, item in enumerate(items):
        y = list_panel.y + 48 + idx * 54
        row = pygame.Rect(list_panel.x + 10, y, list_panel.w - 20, 42)
        color = SCREEN if idx == selected else TEXT
        if idx == selected:
            rect(screen, ACCENT, row, 4)
        text(screen, small_f, item, row.x + 9, row.y + 9, color, row.w - 18)

    info_panel = right_info_panel(layout)
    draw_right_panel_frame(screen, info_panel)
    text(screen, small_f, t(language, "room"), info_panel.x + 14, info_panel.y + 12, MUTED)
    text(screen, small_f, room_name or t(language, "no_name"), info_panel.x + 14, info_panel.y + 38, ACCENT, info_panel.w - 28)
    text(screen, small_f, t(language, "password"), info_panel.x + 14, info_panel.y + 78, MUTED)
    text(screen, small_f, room_password or t(language, "no_password"), info_panel.x + 14, info_panel.y + 104, ACCENT, info_panel.w - 28)
    wrap_text(screen, tiny_f, t(language, "share_room"), pygame.Rect(info_panel.x + 14, info_panel.y + 146, info_panel.w - 28, 48), MUTED)

    ball_cx = info_panel.centerx
    ball_cy = info_panel.bottom - 58
    ball_r = 36
    pygame.draw.circle(screen, (220, 40, 40), (ball_cx, ball_cy), ball_r)
    pygame.draw.circle(screen, (240, 240, 240), (ball_cx, ball_cy), ball_r, draw_top_right=False, draw_top_left=False)
    pygame.draw.rect(screen, (20, 20, 20), pygame.Rect(ball_cx - ball_r, ball_cy - 4, ball_r * 2, 8))
    pygame.draw.circle(screen, (20, 20, 20), (ball_cx, ball_cy), ball_r, 3)
    pygame.draw.circle(screen, (20, 20, 20), (ball_cx, ball_cy), 12)
    pygame.draw.circle(screen, (240, 240, 240), (ball_cx, ball_cy), 7)
    pygame.draw.circle(screen, (20, 20, 20), (ball_cx, ball_cy), 7, 2)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))])


def draw_select_pokemon(screen, fonts, selected, pokemon_list, source_label, sprite_loader, status="", allow_pc_actions=True, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "choose_pokemon"))

    if not pokemon_list:
        list_panel = layout.left_panel
        detail_panel = right_info_panel(layout)
        rect(screen, PANEL, list_panel, 6)
        pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=6)
        draw_right_panel_frame(screen, detail_panel)
        message_screen = pygame.Rect(list_panel.x + 18, list_panel.y + 34, list_panel.w - 36, 120)
        rect(screen, SCREEN, message_screen, 6)
        pygame.draw.rect(screen, BORDER, message_screen, 2, border_radius=6)
        wrap_text(screen, small_f, t(language, "no_pokemon"), pygame.Rect(message_screen.x + 16, message_screen.y + 42, message_screen.w - 32, 44), SCREEN_TEXT, max_lines=2)
        text(screen, small_f, source_label, detail_panel.x + 18, detail_panel.y + 38, MUTED, detail_panel.w - 36)
        draw_footer_actions(screen, tiny_f, [("B", t(language, "btn_back"))])
        return

    list_panel = layout.left_panel
    rect(screen, PANEL, list_panel, 6)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=6)

    scroll = list_scroll_offset("pokemon", selected, len(pokemon_list))
    first = max(0, int(scroll) - 1)
    last = min(len(pokemon_list), int(scroll) + ROW_VISIBLE + 2)
    previous_clip = screen.get_clip()
    screen.set_clip(list_panel.inflate(-8, -8))
    for idx in range(first, last):
        pokemon = pokemon_list[idx]
        y = list_panel.y + 12 + int((idx - scroll) * ROW_H)
        row = pygame.Rect(list_panel.x + 8, y, list_panel.w - 20, 40)
        color = SCREEN if idx == selected else TEXT
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
        text(screen, font(11), pokemon_compact_label(pokemon, f"Pokemon {idx + 1}", language), row.x + 44, row.y + 4, color, row.w - 78)
        item_name = item_info["name"] if item_info else t(language, "item_none")
        text(screen, tiny_f, t(language, "item_label", name=item_name), row.x + 44, row.y + 23, color if idx == selected else MUTED, row.w - 84)
    screen.set_clip(previous_clip)
    draw_scrollbar(screen, list_panel, scroll, len(pokemon_list))

    selected_pokemon = pokemon_list[selected] if 0 <= selected < len(pokemon_list) else None
    sprite_loader.request(selected_pokemon)
    detail_panel = right_info_panel(layout)
    draw_right_panel_frame(screen, detail_panel)
    visor_rect = right_visor_rect(detail_panel)
    draw_digital_visor(screen, visor_rect, 1.0)
    pygame.draw.rect(screen, BORDER, visor_rect, 2)
    text(screen, small_f, source_label, detail_panel.x + 16, detail_panel.y + 122, MUTED, detail_panel.w - 32)

    if selected_pokemon:
        sprite, loading, error = sprite_loader.snapshot()
        sprite_box = pygame.Rect(visor_rect.x + 2, visor_rect.y + 8, 80, 80)
        if sprite:
            scaled = pygame.transform.smoothscale(sprite, (80, 80))
            screen.blit(scaled, sprite_box.topleft)
        elif loading:
            wrap_text(screen, tiny_f, t(language, "loading_sprite"), pygame.Rect(sprite_box.x + 4, sprite_box.y + 30, sprite_box.w - 8, 18), MUTED, max_lines=2)
        else:
            text_center(screen, tiny_f, t(language, "no_sprite"), sprite_box, MUTED)

        text_x = sprite_box.right + 8
        text_w = visor_rect.right - text_x - 8
        name_area = pygame.Rect(text_x, visor_rect.y + 8, text_w, 18)
        name_f = font(11)
        wrap_text(screen, name_f, selected_pokemon.get("name", "Pokemon"), name_area, (0, 0, 0), line_gap=1, max_lines=1)

        level_y = visor_rect.y + 30
        level_font = font(10)
        level_text = f"Nivel {selected_pokemon.get('level', 0)}"
        level_surface = level_font.render(level_text, True, (0, 0, 0))
        level_x = text_x
        screen.blit(level_surface, (level_x, level_y))
        type_box = pygame.Rect(text_x, level_y + 14, text_w, 22)
        draw_digital_visor(screen, type_box, 1.0)
        type_names = pokemon_types(selected_pokemon)
        if type_names:
            tint = TYPE_COLORS.get(type_names[0], (170, 232, 206))
            overlay = pygame.Surface(type_box.size, pygame.SRCALPHA)
            overlay.fill((tint[0], tint[1], tint[2], 42))
            pygame.draw.rect(overlay, (255, 255, 255, 60), overlay.get_rect(), 1)
            screen.blit(overlay, type_box.topleft)
        pygame.draw.rect(screen, BORDER, type_box, 1)
        type_label_text = " / ".join(type_label(type_name, language) for type_name in type_names[:2]) or "-"
        type_font = font(10)
        type_surface = type_font.render(type_label_text, True, (0, 0, 0))
        screen.blit(type_surface, type_surface.get_rect(center=type_box.center))
        xp_fill, _, _ = pokemon_xp_bar(selected_pokemon)
        xp_bar = pygame.Rect(text_x, type_box.bottom + 6, text_w, 10)
        rect(screen, (214, 214, 214), xp_bar, 4)
        pygame.draw.rect(screen, BORDER, xp_bar, 1, border_radius=4)
        if xp_fill > 0:
            fill_w = max(2, int((xp_bar.w - 2) * xp_fill))
            rect(screen, ACCENT, pygame.Rect(xp_bar.x + 1, xp_bar.y + 1, fill_w, xp_bar.h - 2), 3)

        summary_top = max(xp_bar.bottom, visor_rect.bottom) + 10
        summary_panel = pygame.Rect(detail_panel.x + 14, summary_top, detail_panel.w - 28, detail_panel.bottom - summary_top - 10)
        rect(screen, PANEL_2, summary_panel, 0)
        pygame.draw.rect(screen, BORDER, summary_panel, 2)
        location = selected_pokemon.get("location", "")
        if location.startswith("box:"):
            parts = location.split(":")
            place_text = selected_pokemon.get("raw", {}).get("box_name") or f"Box {int(parts[1]) + 1}"
        else:
            place_text = t(language, "party")
        save_label = selected_pokemon.get("save_name") or (selected_pokemon.get("raw", {}) or {}).get("save_name") or ""
        item_info = held_item_info(selected_pokemon)
        item_text = item_info["name"] if item_info else t(language, "item_none")
        text(screen, tiny_f, place_text, summary_panel.x + 8, summary_panel.y + 8, SCREEN_TEXT, summary_panel.w - 16)
        if save_label:
            text(screen, tiny_f, str(save_label), summary_panel.x + 8, summary_panel.y + 20, MUTED, summary_panel.w - 16)
        item_icon = pygame.Rect(summary_panel.x + 6, summary_panel.y + 28, 14, 14)
        draw_item_icon(screen, item_icon, item_info)
        text(screen, tiny_f, item_text, item_icon.right + 6, summary_panel.y + 28, MUTED, summary_panel.w - 26)

        moves_panel = pygame.Rect(summary_panel.x + 8, summary_panel.y + 50, summary_panel.w - 16, summary_panel.h - 58)
        text(screen, small_f, t(language, "moves"), moves_panel.x + 0, moves_panel.y, TEXT, moves_panel.w)
        move_entries = move_display_entries(selected_pokemon)
        if move_entries:
            move_f = font(11)
            for move_idx, move_entry in enumerate(move_entries[:4]):
                move_y = moves_panel.y + 20 + move_idx * 20
                move_rect = pygame.Rect(moves_panel.x, move_y, moves_panel.w, 16)
                rect(screen, BG, move_rect, 4)
                pygame.draw.rect(screen, BORDER, move_rect, 1, border_radius=4)
                name_area = pygame.Rect(move_rect.x + 6, move_rect.y + 1, move_rect.w - 60, 14)
                text(screen, move_f, move_entry["name"], name_area.x, name_area.y, TEXT, name_area.w)
                pp_text = f"{move_entry['pp']}/{move_entry['max_pp']}" if move_entry.get("max_pp") else str(move_entry["pp"])
                pp_area = pygame.Rect(move_rect.right - 52, move_rect.y + 1, 48, 14)
                pp_surface = tiny_f.render(pp_text, True, MUTED)
                screen.blit(pp_surface, pp_surface.get_rect(midright=pp_area.midright))
        else:
            text(screen, tiny_f, t(language, "no_moves"), moves_panel.x, moves_panel.y + 20, MUTED, moves_panel.w)
        if error and DEBUG:
            text(screen, tiny_f, error[:40], detail_panel.x + 14, detail_panel.bottom - 30, WARN, detail_panel.w - 28)
        elif status:
            pass

    actions = [("A", t(language, "btn_ok")), ("B", t(language, "btn_back"))]
    if allow_pc_actions:
        is_party = "party" in (source_label or "").lower()
        x_label = t(language, "btn_move_pc") if is_party else t(language, "btn_withdraw")
        y_label = t(language, "btn_view_pc") if is_party else t(language, "btn_view_party")
        actions.extend([("X", x_label), ("Y", y_label)])
    draw_footer_actions(screen, tiny_f, actions)


def draw_connecting(screen, fonts, frame, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "connecting"))
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 6)
    rect(screen, PANEL_2, right_panel, 6)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=6)
    dots = "." * ((frame // 15) % 4)
    status_screen = pygame.Rect(left_panel.x + 18, left_panel.y + 34, left_panel.w - 36, 120)
    rect(screen, SCREEN, status_screen, 6)
    pygame.draw.rect(screen, BORDER, status_screen, 2, border_radius=6)
    text_center(screen, body_f, t(language, "connecting_server", dots=dots), status_screen, SCREEN_TEXT)
    for idx in range(4):
        light = ACCENT if idx <= ((frame // 12) % 4) else MUTED
        pygame.draw.circle(screen, BORDER, (left_panel.x + 72 + idx * 44, status_screen.bottom + 48), 11)
        pygame.draw.circle(screen, light, (left_panel.x + 72 + idx * 44, status_screen.bottom + 48), 7)
    rect(screen, SCREEN, pygame.Rect(right_panel.x + 24, right_panel.y + 36, right_panel.w - 48, 52), 5)
    text_center(screen, small_f, t(language, "please_wait"), pygame.Rect(right_panel.x + 24, right_panel.y + 36, right_panel.w - 48, 52), SCREEN_TEXT)
    for idx in range(5):
        bar = pygame.Rect(right_panel.x + 34, right_panel.y + 120 + idx * 24, right_panel.w - 68 - idx * 12, 10)
        rect(screen, ACCENT if idx % 2 == 0 else OK, bar, 3)
    draw_footer_bar(screen)
    text_center(screen, tiny_f, t(language, "please_wait"), pygame.Rect(0, SCREEN_H - 30, SCREEN_W, 24), MUTED)


def draw_waiting_partner(screen, fonts, status, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "waiting_partner"))
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 6)
    rect(screen, PANEL_2, right_panel, 6)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=6)
    message = translate_literal(language, status) if status else t(language, "waiting_partner") + "..."
    status_screen = pygame.Rect(left_panel.x + 18, left_panel.y + 34, left_panel.w - 36, 122)
    rect(screen, SCREEN, status_screen, 6)
    pygame.draw.rect(screen, BORDER, status_screen, 2, border_radius=6)
    wrap_text(screen, body_f, message, pygame.Rect(status_screen.x + 16, status_screen.y + 30, status_screen.w - 32, 64), SCREEN_TEXT, max_lines=3)
    text_center(screen, small_f, t(language, "room_open_short"), pygame.Rect(right_panel.x + 18, right_panel.y + 42, right_panel.w - 36, 42), TEXT)
    for idx, label in enumerate(("A", "B", "C")):
        chip = pygame.Rect(right_panel.x + 34 + idx * 72, right_panel.y + 142, 48, 32)
        rect(screen, PANEL if idx else ACCENT, chip, 5)
        pygame.draw.rect(screen, BORDER, chip, 1, border_radius=5)
        text_center(screen, small_f, label, chip, SCREEN if idx == 0 else TEXT)
    draw_footer_actions(screen, tiny_f, [("B", t(language, "btn_cancel"))])


def draw_pokedex_prompt(screen, fonts, title, question, detail_lines, actions, language="pt", tone=WARN):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, title)
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 6)
    rect(screen, PANEL_2, right_panel, 6)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=6)

    status_screen = pygame.Rect(left_panel.x + 18, left_panel.y + 32, left_panel.w - 36, 132)
    rect(screen, SCREEN, status_screen, 6)
    pygame.draw.rect(screen, BORDER, status_screen, 2, border_radius=6)
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


def draw_deposit_confirm(screen, fonts, pokemon, language="pt"):
    name = pokemon_display_name(pokemon)
    level = (pokemon or {}).get("level")
    details = [t(language, "level_short", level=level)] if level else []
    details.extend([t(language, "deposit_help"), t(language, "backup_help")])
    draw_pokedex_prompt(
        screen,
        fonts,
        screen_title(language, "deposit_title"),
        t(language, "deposit_question", name=name),
        details,
        [("A", t(language, "btn_yes")), ("B", t(language, "btn_no"))],
        language,
        ACCENT,
    )


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
    rect(screen, PANEL, left_panel, 6)
    rect(screen, PANEL_2, right_panel, 6)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=6)
    rect(screen, SCREEN, pygame.Rect(left_panel.x + 20, left_panel.y + 36, left_panel.w - 40, 118), 6)
    text_center(screen, body_f, screen_title(language, "notice"), pygame.Rect(left_panel.x + 20, left_panel.y + 36, left_panel.w - 40, 118), SCREEN_TEXT)
    body_msg = translate_literal(language, (message or "").strip()) or t(language, "no_details")
    wrap_text(screen, small_f, body_msg, pygame.Rect(right_panel.x + 18, right_panel.y + 28, right_panel.w - 36, right_panel.h - 56), TEXT, max_lines=8)
    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok"))])


def draw_resolve_moves(screen, fonts, removed_move, replacement_index, current_idx, total, chosen_ids=None, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "incompatible_move_title", current=current_idx + 1, total=total))

    info_panel = layout.left_panel
    rect(screen, PANEL, info_panel, 6)
    pygame.draw.rect(screen, BORDER, info_panel, 2, border_radius=6)
    move_name_text = removed_move.get("name") or local_move_name(removed_move.get("move_id", 0))
    if is_move_number_label(move_name_text):
        move_name_text = local_move_name(removed_move.get("move_id", 0))
    status_screen = pygame.Rect(info_panel.x + 18, info_panel.y + 30, info_panel.w - 36, 122)
    rect(screen, SCREEN, status_screen, 6)
    pygame.draw.rect(screen, BORDER, status_screen, 2, border_radius=6)
    wrap_text(screen, body_f, t(language, "unsupported_move", move=move_name_text), pygame.Rect(status_screen.x + 14, status_screen.y + 26, status_screen.w - 28, 66), SCREEN_TEXT, max_lines=3)
    wrap_text(screen, small_f, t(language, "choose_replacement"), pygame.Rect(info_panel.x + 18, status_screen.bottom + 28, info_panel.w - 36, 62), MUTED, max_lines=3)

    chosen_set = set(int(x) for x in (chosen_ids or []) if x)
    replacements = [
        r for r in (removed_move.get("valid_replacements") or [])
        if int(r.get("move_id") or 0) not in chosen_set
    ]
    options = replacements + [{"move_id": 0, "name": t(language, "empty_move")}]
    list_panel = right_info_panel(layout)
    rect(screen, PANEL, list_panel, 6)
    pygame.draw.rect(screen, BORDER, list_panel, 2, border_radius=6)

    visible = 6
    row_h = 38
    scroll = list_scroll_offset(f"resolve_moves_{current_idx}", replacement_index, len(options), visible)
    first = max(0, int(scroll) - 1)
    last = min(len(options), int(scroll) + visible + 2)
    previous_clip = screen.get_clip()
    screen.set_clip(list_panel.inflate(-8, -8))
    for idx in range(first, last):
        option = options[idx]
        y = list_panel.y + 14 + int((idx - scroll) * row_h)
        row = pygame.Rect(list_panel.x + 8, y, list_panel.w - 24, 32)
        color = SCREEN if idx == replacement_index else TEXT
        if idx == replacement_index:
            rect(screen, ACCENT, row, 4)
        label = option.get("name") or local_move_name(option.get("move_id", 0))
        if is_move_number_label(label):
            label = local_move_name(option.get("move_id", 0))
        text(screen, small_f, label, row.x + 10, row.y + 7, color, row.w - 20)
    screen.set_clip(previous_clip)
    draw_scrollbar(screen, list_panel, scroll, len(options), visible)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_choose")), ("B", t(language, "btn_skip"))])


def draw_cancel_waiting_confirm(screen, fonts, language="pt"):
    draw_pokedex_prompt(
        screen,
        fonts,
        screen_title(language, "cancel_trade_title"),
        t(language, "cancel_trade_question"),
        [t(language, "save_not_modified"), t(language, "room_stays_open")],
        [("A", t(language, "btn_yes")), ("B", t(language, "btn_no"))],
        language,
        WARN,
    )


def draw_confirm_pokemon_visor(screen, fonts, area, label, pokemon, display_name, sprite, loading, language="pt"):
    _, _, _, tiny_f = fonts
    draw_digital_visor(screen, area, 1.0)
    pygame.draw.rect(screen, BORDER, area, 2)

    sprite_box = pygame.Rect(area.x + 2, area.y + 8, 80, 80)
    if sprite:
        scaled = pygame.transform.smoothscale(sprite, (80, 80))
        screen.blit(scaled, sprite_box.topleft)
    elif loading:
        wrap_text(screen, tiny_f, t(language, "loading_sprite"), pygame.Rect(sprite_box.x + 4, sprite_box.y + 30, sprite_box.w - 8, 18), MUTED, max_lines=2)
    else:
        text_center(screen, tiny_f, t(language, "no_sprite"), sprite_box, MUTED)

    text_x = sprite_box.right + 8
    text_w = area.right - text_x - 8
    name_area = pygame.Rect(text_x, area.y + 8, text_w, 18)
    level = int((pokemon or {}).get("level") or 0)
    name_f = font(11)
    wrap_text(screen, name_f, display_name, name_area, (0, 0, 0), line_gap=1, max_lines=1)

    level_y = area.y + 30
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
    rect(screen, (214, 214, 214), xp_bar, 4)
    pygame.draw.rect(screen, BORDER, xp_bar, 1, border_radius=4)
    if xp_fill > 0:
        fill_w = max(2, int((xp_bar.w - 2) * xp_fill))
        rect(screen, ACCENT, pygame.Rect(xp_bar.x + 1, xp_bar.y + 1, fill_w, xp_bar.h - 2), 3)


def draw_trade_confirm(screen, fonts, my_pokemon, opponent_pokemon, sprite_loader, language="pt"):
    title_f, body_f, small_f, tiny_f = fonts
    del title_f
    layout = draw_pokedex_shell(screen, screen_title(language, "confirm_trade"))

    mine = my_pokemon.get("name") or my_pokemon.get("nickname") or my_pokemon.get("species_name") or my_pokemon.get("display") or my_pokemon.get("display_summary") or "???"
    peer = opponent_pokemon.get("nickname") or opponent_pokemon.get("species_name") or opponent_pokemon.get("name") or opponent_pokemon.get("display_summary") or "???"

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
    rect(screen, PANEL, left_card, 6)
    rect(screen, PANEL, right_card, 6)
    pygame.draw.rect(screen, BORDER, left_card, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, right_card, 2, border_radius=6)

    peer_visor = right_visor_rect(right_card)
    my_visor = pygame.Rect(left_card.x + 16, peer_visor.y, left_card.w - 32, peer_visor.h)
    draw_confirm_pokemon_visor(screen, fonts, my_visor, t(language, "your_pokemon"), my_pokemon, mine, my_sprite, my_loading, language)
    draw_confirm_pokemon_visor(screen, fonts, peer_visor, t(language, "opponent"), opponent_pokemon, peer, peer_sprite, peer_loading, language)

    arrow_y = left_card.y + 146
    pygame.draw.circle(screen, BORDER, (SCREEN_W // 2, arrow_y - 13), 16)
    pygame.draw.circle(screen, ACCENT, (SCREEN_W // 2, arrow_y - 13), 12)
    pygame.draw.polygon(screen, SCREEN, [
        (SCREEN_W // 2 - 7, arrow_y - 19),
        (SCREEN_W // 2 + 3, arrow_y - 19),
        (SCREEN_W // 2 + 3, arrow_y - 24),
        (SCREEN_W // 2 + 11, arrow_y - 13),
        (SCREEN_W // 2 + 3, arrow_y - 2),
        (SCREEN_W // 2 + 3, arrow_y - 7),
        (SCREEN_W // 2 - 7, arrow_y - 7),
    ])
    pygame.draw.circle(screen, BORDER, (SCREEN_W // 2, arrow_y + 23), 16)
    pygame.draw.circle(screen, ACCENT, (SCREEN_W // 2, arrow_y + 23), 12)
    pygame.draw.polygon(screen, SCREEN, [
        (SCREEN_W // 2 + 7, arrow_y + 17),
        (SCREEN_W // 2 - 3, arrow_y + 17),
        (SCREEN_W // 2 - 3, arrow_y + 12),
        (SCREEN_W // 2 - 11, arrow_y + 23),
        (SCREEN_W // 2 - 3, arrow_y + 34),
        (SCREEN_W // 2 - 3, arrow_y + 29),
        (SCREEN_W // 2 + 7, arrow_y + 29),
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
    pygame.draw.rect(shadow, (0, 0, 0, 100), shadow.get_rect(), border_radius=16)
    screen.blit(shadow, (stage.x - 4, stage.y + 4))
    # bezel claro
    pygame.draw.rect(screen, (62, 76, 110), stage, border_radius=14)
    # borda escura
    pygame.draw.rect(screen, (12, 18, 32), stage.inflate(-10, -10), 3, border_radius=10)
    # tela
    crt = stage.inflate(-22, -22)
    pygame.draw.rect(screen, (10, 16, 30), crt, border_radius=8)

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
    pygame.draw.rect(screen, (240, 240, 230), textbox, border_radius=4)
    pygame.draw.rect(screen, (12, 18, 32), textbox, 2, border_radius=4)
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


def draw_evolution_cancel_prompt(screen, fonts, evolution, sprite_loader, frame, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "trade_evolution"))

    stage_panel = layout.left_panel
    decision_panel = right_info_panel(layout)
    rect(screen, PANEL, stage_panel, 6)
    rect(screen, PANEL_2, decision_panel, 6)
    pygame.draw.rect(screen, BORDER, stage_panel, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, decision_panel, 2, border_radius=6)
    source = evolution.get("source_name", "Pokemon")
    target = evolution.get("target_name", "evolucao")

    stage = pygame.Rect(stage_panel.x + 14, stage_panel.y + 20, stage_panel.w - 28, 180)
    draw_evolution_animation(screen, fonts, evolution, sprite_loader, frame, language=language, stage=stage)
    text_center(screen, tiny_f, screen_title(language, "trade_evolution"), pygame.Rect(stage_panel.x + 18, stage.bottom + 18, stage_panel.w - 36, 22), MUTED)

    rect(screen, SCREEN, pygame.Rect(decision_panel.x + 18, decision_panel.y + 22, decision_panel.w - 36, 48), 5)
    text_center(screen, small_f, source, pygame.Rect(decision_panel.x + 18, decision_panel.y + 22, decision_panel.w - 36, 48), SCREEN_TEXT)
    wrap_text(screen, body_f, t(language, "wants_evolve", source=source, target=target), pygame.Rect(decision_panel.x + 18, decision_panel.y + 92, decision_panel.w - 36, 70), TEXT, max_lines=3)
    wrap_text(screen, small_f, t(language, "cancel_evolution_question"), pygame.Rect(decision_panel.x + 18, decision_panel.y + 172, decision_panel.w - 36, 48), WARN, max_lines=2)
    wrap_text(screen, tiny_f, t(language, "cancel_evolution_hint"), pygame.Rect(decision_panel.x + 18, decision_panel.y + 226, decision_panel.w - 36, 36), MUTED, max_lines=2)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_let_evolve")), ("B", t(language, "btn_cancel_evo"))])


def draw_evolution_cancel_confirm(screen, fonts, evolution, sprite_loader, frame, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "confirm_cancel"))

    stage_panel = layout.left_panel
    decision_panel = right_info_panel(layout)
    rect(screen, PANEL, stage_panel, 6)
    rect(screen, PANEL_2, decision_panel, 6)
    pygame.draw.rect(screen, BORDER, stage_panel, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, decision_panel, 2, border_radius=6)
    source = evolution.get("source_name", "Pokemon")
    target = evolution.get("target_name", "evolucao")
    stage = pygame.Rect(stage_panel.x + 14, stage_panel.y + 20, stage_panel.w - 28, 180)
    draw_evolution_animation(screen, fonts, evolution, sprite_loader, frame, final_form="source", language=language, stage=stage)
    text_center(screen, tiny_f, screen_title(language, "confirm_cancel"), pygame.Rect(stage_panel.x + 18, stage.bottom + 18, stage_panel.w - 36, 22), MUTED)

    rect(screen, SCREEN, pygame.Rect(decision_panel.x + 18, decision_panel.y + 22, decision_panel.w - 36, 48), 5)
    text_center(screen, body_f, t(language, "are_you_sure"), pygame.Rect(decision_panel.x + 18, decision_panel.y + 22, decision_panel.w - 36, 48), WARN)
    wrap_text(screen, small_f, t(language, "cancel_evolution_confirm", source=source, target=target), pygame.Rect(decision_panel.x + 18, decision_panel.y + 92, decision_panel.w - 36, 82), TEXT, max_lines=4)
    wrap_text(screen, tiny_f, t(language, "cancel_evolution_result"), pygame.Rect(decision_panel.x + 18, decision_panel.y + 196, decision_panel.w - 36, 50), MUTED, max_lines=3)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_no_let_evolve")), ("B", t(language, "btn_yes_interrupt"))])


def draw_trading(screen, fonts, status, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "trading"))
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 6)
    rect(screen, PANEL_2, right_panel, 6)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=6)
    status_screen = pygame.Rect(left_panel.x + 18, left_panel.y + 34, left_panel.w - 36, 122)
    rect(screen, SCREEN, status_screen, 6)
    pygame.draw.rect(screen, BORDER, status_screen, 2, border_radius=6)
    wrap_text(screen, body_f, translate_literal(language, status) or t(language, "processing"), pygame.Rect(status_screen.x + 16, status_screen.y + 30, status_screen.w - 32, 64), SCREEN_TEXT, max_lines=3)
    text_center(screen, small_f, t(language, "processing"), pygame.Rect(right_panel.x + 18, right_panel.y + 34, right_panel.w - 36, 42), TEXT)
    for idx in range(6):
        y = right_panel.y + 98 + idx * 24
        bar_w = int((right_panel.w - 54) * (0.45 + (idx % 3) * 0.2))
        rect(screen, ACCENT if idx % 2 else OK, pygame.Rect(right_panel.x + 28, y, bar_w, 10), 3)
    draw_footer_bar(screen)
    text_center(screen, tiny_f, t(language, "processing"), pygame.Rect(0, SCREEN_H - 30, SCREEN_W, 24), MUTED)


def draw_trade_result(screen, fonts, success, data, language="pt"):
    _, body_f, small_f, tiny_f = fonts
    layout = draw_pokedex_shell(screen, screen_title(language, "result"))
    left_panel = layout.left_panel
    right_panel = right_info_panel(layout)
    rect(screen, PANEL, left_panel, 6)
    rect(screen, PANEL_2, right_panel, 6)
    pygame.draw.rect(screen, BORDER, left_panel, 2, border_radius=6)
    pygame.draw.rect(screen, BORDER, right_panel, 2, border_radius=6)
    status_screen = pygame.Rect(left_panel.x + 18, left_panel.y + 34, left_panel.w - 36, 120)
    rect(screen, SCREEN, status_screen, 6)
    pygame.draw.rect(screen, BORDER, status_screen, 2, border_radius=6)

    if success:
        text_center(screen, body_f, t(language, "trade_complete"), status_screen, SCREEN_TEXT)
        peer = data.get("peer", {}) if isinstance(data, dict) else {}
        received = data.get("received", {}) if isinstance(data, dict) else {}
        evolution = received.get("trade_evolution", {}) if isinstance(received, dict) else {}
        pokemon_display = (
            f"{evolution.get('source_name')} -> {evolution.get('target_name')}"
            if evolution.get("evolved")
            else t(language, "without_evolving", pokemon=evolution.get("source_name"))
            if evolution.get("cancelled")
            else received.get("display_summary") or peer.get("display_summary") or peer.get("nickname") or peer.get("species_name") or "Pokemon"
        )
        if isinstance(data, dict) and (data.get("backup_a") or data.get("backup_b")):
            backup_a = Path(data.get("backup_a", "")).name if data.get("backup_a") else t(language, "none")
            backup_b = Path(data.get("backup_b", "")).name if data.get("backup_b") else t(language, "none")
            backup_name = f"{backup_a} / {backup_b}"
        else:
            backup_name = Path(data.get("backup", "")).name if isinstance(data, dict) and data.get("backup") else t(language, "none")
        wrap_text(screen, small_f, t(language, "received", pokemon=pokemon_display), pygame.Rect(right_panel.x + 18, right_panel.y + 36, right_panel.w - 36, 80), TEXT, max_lines=3)
        wrap_text(screen, tiny_f, t(language, "backup", backup=backup_name), pygame.Rect(right_panel.x + 18, right_panel.y + 132, right_panel.w - 36, 86), MUTED, max_lines=4)
    else:
        text_center(screen, body_f, t(language, "error_cancelled"), status_screen, SCREEN_TEXT)
        wrap_text(screen, small_f, str(data or t(language, "trade_not_complete"))[:240], pygame.Rect(right_panel.x + 18, right_panel.y + 36, right_panel.w - 36, 152), RED, max_lines=6)

    draw_footer_actions(screen, tiny_f, [("A", t(language, "btn_ok"))])


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
    input_source_actions = {}
    pressed_input_actions = {}
    blocked_input_actions = set()
    input_guard_until = 0.0
    pending_removed_moves = []
    resolve_current_idx = 0
    resolve_replacement_idx = 0
    resolved_moves_choices = {}
    info_modal_data = {"title": "", "message": ""}
    pending_deposit_idx = -1
    pending_withdraw_pokemon = None
    pending_pc_return_screen = "select_pokemon"
    evolution_anim_start = None
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
    sprite_loader = SpriteLoader(state.server_url)

    def clear_input_source(source):
        action = input_source_actions.pop(source, None)
        if not action:
            return
        sources = pressed_input_actions.get(action)
        if sources:
            sources.discard(source)
            if not sources:
                pressed_input_actions.pop(action, None)
                blocked_input_actions.discard(action)

    def set_input_source(source, action):
        if action not in GUARDED_INPUT_ACTIONS:
            clear_input_source(source)
            return
        previous = input_source_actions.get(source)
        if previous == action:
            return
        clear_input_source(source)
        input_source_actions[source] = action
        pressed_input_actions.setdefault(action, set()).add(source)

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
        return action in blocked_input_actions or time.monotonic() < input_guard_until

    def switch_screen(new_screen, reason):
        nonlocal current_screen, input_guard_until
        if current_screen != new_screen:
            logger.info("SCREEN %s -> %s (%s)", current_screen, new_screen, reason)
            blocked_input_actions.update(pressed_input_actions.keys())
            input_guard_until = max(input_guard_until, time.monotonic() + INPUT_TRANSITION_GUARD_SECONDS)
            nav_hold["direction"] = None
            nav_hold["started"] = 0.0
            nav_hold["last_fire"] = 0.0
            action_state["last_action"] = None
            action_state["last_time"] = 0.0
        current_screen = new_screen

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

    def load_self_trade_source(save_path, source="party", *, target_save_path=None, require_compatible_to_target=False):
        nonlocal trade_status
        state.selected_save = Path(save_path)
        state.pokemon_source = source
        state.selected_pokemon = None
        state.get_pokemon_list(source, enrich=False)
        source_label = t(state.language, "party") if source == "party" else t(state.language, "pc")
        base_status = f"{source_label}: {Path(save_path).name}"
        if not require_compatible_to_target or not target_save_path or not self_trade_pokemon_a:
            trade_status = base_status
            return
        trade_status = base_status

    def load_self_trade_party(save_path, *, target_save_path=None, require_compatible_to_target=False):
        load_self_trade_source(
            save_path,
            "party",
            target_save_path=target_save_path,
            require_compatible_to_target=require_compatible_to_target,
        )

    def self_trade_source_label(slot, save_path):
        source = state.pokemon_source if state.pokemon_source in ("party", "boxes") else "party"
        if source == "party":
            key = "party_save_named" if save_path else "party_save"
        else:
            key = "pc_save_named" if save_path else "pc_save"
        if save_path:
            return t(state.language, key, slot=slot, name=Path(save_path).name)
        return t(state.language, key, slot=slot)

    def reload_after_pc_management(source):
        self_trade_local = str(pending_pc_return_screen or "").startswith("self_")
        state.get_pokemon_list(source, enrich=not self_trade_local)

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
            track_input_event(event, mapped)
            if event.type == pygame.JOYHATMOTION:
                hat_x, hat_y = event.value
                if hat_x == 0 and hat_y == 0:
                    nav_hold["direction"] = None
                elif mapped in ("up", "down", "left", "right") and not input_action_blocked(mapped):
                    now = time.monotonic()
                    nav_hold["direction"] = mapped
                    nav_hold["started"] = now
                    nav_hold["last_fire"] = now
            elif event.type == pygame.JOYAXISMOTION and event.axis in (AXIS_X, AXIS_Y):
                if abs(event.value) < AXIS_THRESHOLD:
                    if (event.axis == AXIS_Y and nav_hold["direction"] in ("up", "down")) or \
                       (event.axis == AXIS_X and nav_hold["direction"] in ("left", "right")):
                        nav_hold["direction"] = None
                elif mapped in ("up", "down", "left", "right") and not input_action_blocked(mapped):
                    now = time.monotonic()
                    nav_hold["direction"] = mapped
                    nav_hold["started"] = now
                    nav_hold["last_fire"] = now
            if input_action_blocked(mapped):
                logger.debug("Input action blocked after screen transition: %s", mapped)
                mapped = None
            mapped = debounce_action(mapped, action_state)
            if mapped and action is None:
                action = mapped

        if action is None and nav_hold["direction"]:
            now = time.monotonic()
            if now - nav_hold["started"] >= NAV_REPEAT_DELAY and \
               now - nav_hold["last_fire"] >= NAV_REPEAT_INTERVAL:
                repeated_action = nav_hold["direction"]
                if input_action_blocked(repeated_action):
                    nav_hold["direction"] = None
                else:
                    action = repeated_action
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

        if action and input_action_blocked(action):
            logger.debug("Input action blocked on active screen: %s", action)
            action = None

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
                    state.theme = next_theme(state.theme, -1 if action == "left" else 1)
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
                if state.pokemon_source != "party":
                    info_modal_data = {
                        "title": "Pokemon esta no PC",
                        "message": "Pressione X para retirar este Pokemon para a Party antes de troca-lo.",
                        "return_screen": "self_select_pokemon_a",
                    }
                    switch_screen("info_modal", "self_select_a_from_pc_blocked")
                else:
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
            elif action == "x" and state.pokemon_list:
                if state.trade_phase not in ("idle", "waiting"):
                    trade_status = "Aguarde a troca terminar antes de mover."
                elif state.pokemon_source == "party":
                    state.selected_save = Path(self_trade_save_a)
                    pending_deposit_idx = menu_index
                    pending_pc_return_screen = "self_select_pokemon_a"
                    logger.info("Self trade deposit requested for save A party slot %s", pending_deposit_idx)
                    switch_screen("deposit_confirm", "self_deposit_a_request")
                else:
                    state.selected_save = Path(self_trade_save_a)
                    pending_withdraw_pokemon = state.pokemon_list[menu_index]
                    pending_pc_return_screen = "self_select_pokemon_a"
                    logger.info("Self trade withdraw requested for save A %s", pending_withdraw_pokemon.get("location"))
                    switch_screen("withdraw_confirm", "self_withdraw_a_request")
            elif action == "y":
                new_source = "boxes" if state.pokemon_source == "party" else "party"
                try:
                    load_self_trade_source(self_trade_save_a, new_source)
                    menu_index = 0
                    logger.info("Self trade save A toggled source -> %s (%s entries)", new_source, len(state.pokemon_list))
                except SaveError as exc:
                    logger.error("Self trade save A source toggle failed: %s", exc)
                    info_modal_data = {
                        "title": "Erro",
                        "message": str(exc),
                        "return_screen": "self_select_pokemon_a",
                    }
                    switch_screen("info_modal", "self_source_a_toggle_failed")
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
                if state.pokemon_source != "party":
                    info_modal_data = {
                        "title": "Pokemon esta no PC",
                        "message": "Pressione X para retirar este Pokemon para a Party antes de troca-lo.",
                        "return_screen": "self_select_pokemon_b",
                    }
                    switch_screen("info_modal", "self_select_b_from_pc_blocked")
                else:
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
            elif action == "x" and state.pokemon_list:
                if state.trade_phase not in ("idle", "waiting"):
                    trade_status = "Aguarde a troca terminar antes de mover."
                elif state.pokemon_source == "party":
                    state.selected_save = Path(self_trade_save_b)
                    pending_deposit_idx = menu_index
                    pending_pc_return_screen = "self_select_pokemon_b"
                    logger.info("Self trade deposit requested for save B party slot %s", pending_deposit_idx)
                    switch_screen("deposit_confirm", "self_deposit_b_request")
                else:
                    state.selected_save = Path(self_trade_save_b)
                    pending_withdraw_pokemon = state.pokemon_list[menu_index]
                    pending_pc_return_screen = "self_select_pokemon_b"
                    logger.info("Self trade withdraw requested for save B %s", pending_withdraw_pokemon.get("location"))
                    switch_screen("withdraw_confirm", "self_withdraw_b_request")
            elif action == "y":
                new_source = "boxes" if state.pokemon_source == "party" else "party"
                try:
                    load_self_trade_source(self_trade_save_b, new_source)
                    menu_index = 0
                    logger.info("Self trade save B toggled source -> %s (%s entries)", new_source, len(state.pokemon_list))
                except SaveError as exc:
                    logger.error("Self trade save B source toggle failed: %s", exc)
                    info_modal_data = {
                        "title": "Erro",
                        "message": str(exc),
                        "return_screen": "self_select_pokemon_b",
                    }
                    switch_screen("info_modal", "self_source_b_toggle_failed")
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
                    pending_pc_return_screen = "select_pokemon"
                    logger.info("Deposit requested for party slot %s", pending_deposit_idx)
                    switch_screen("deposit_confirm", "deposit_request")
                else:
                    pending_withdraw_pokemon = state.pokemon_list[menu_index]
                    pending_pc_return_screen = "select_pokemon"
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
                        "return_screen": pending_pc_return_screen,
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
                        reload_after_pc_management(state.pokemon_source or "boxes")
                        trade_status = f"{result.get('species_name', 'Pokemon')} agora esta na Party."
                        menu_index = min(menu_index, max(0, len(state.pokemon_list) - 1))
                        switch_screen(pending_pc_return_screen, "withdraw_done")
                    except Exception as exc:
                        logger.exception("Withdraw failed: %s", exc)
                        info_modal_data = {
                            "title": "Nao foi possivel retirar",
                            "message": str(exc),
                            "return_screen": pending_pc_return_screen,
                        }
                        switch_screen("info_modal", "withdraw_failed")
                pending_withdraw_pokemon = None
            elif action == "back":
                pending_withdraw_pokemon = None
                switch_screen(pending_pc_return_screen, "withdraw_aborted")

        elif current_screen == "deposit_confirm" and action:
            if action == "select":
                save_model = state.get_selected_save_model()
                if not save_model:
                    info_modal_data = {
                        "title": "Erro",
                        "message": "Save nao carregado.",
                        "return_screen": pending_pc_return_screen,
                    }
                    switch_screen("info_modal", "deposit_no_save")
                else:
                    try:
                        _create_backup(state.selected_save)
                        result = save_model.deposit_party_to_pc(pending_deposit_idx)
                        save_model.write_to_disk()
                        state.expected_signature = save_model.signature()
                        state.refresh_selected_save()
                        reload_after_pc_management("party")
                        trade_status = f"{result.get('species_name', 'Pokemon')} movido para o PC."
                        menu_index = min(menu_index, max(0, len(state.pokemon_list) - 1))
                        switch_screen(pending_pc_return_screen, "deposit_done")
                    except Exception as exc:
                        logger.exception("Deposit failed: %s", exc)
                        info_modal_data = {
                            "title": "Nao foi possivel mover",
                            "message": str(exc),
                            "return_screen": pending_pc_return_screen,
                        }
                        switch_screen("info_modal", "deposit_failed")
                pending_deposit_idx = -1
            elif action == "back":
                pending_deposit_idx = -1
                switch_screen(pending_pc_return_screen, "deposit_aborted")

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
            draw_select_save(screen, fonts, menu_index, state.saves, language=state.language)
        elif current_screen == "self_select_save_a":
            draw_select_save(screen, fonts, menu_index, state.saves, screen_title(state.language, "self_save_1"), state.language)
        elif current_screen == "self_select_save_b":
            draw_select_save(screen, fonts, menu_index, state.saves, screen_title(state.language, "self_save_2"), state.language)
        elif current_screen == "self_select_pokemon_a":
            label = self_trade_source_label(1, self_trade_save_a)
            draw_select_pokemon(screen, fonts, menu_index, state.pokemon_list, label, sprite_loader, trade_status, True, state.language)
        elif current_screen == "self_select_pokemon_b":
            label = self_trade_source_label(2, self_trade_save_b)
            draw_select_pokemon(screen, fonts, menu_index, state.pokemon_list, label, sprite_loader, trade_status, True, state.language)
        elif current_screen == "select_pokemon_source":
            draw_select_pokemon_source(screen, fonts, menu_index, trade_status, state.room_name or room_name, state.room_password or room_password, state.language)
        elif current_screen == "select_pokemon":
            source_label = t(state.language, "your_party") if state.pokemon_source == "party" else t(state.language, "your_pc")
            draw_select_pokemon(screen, fonts, menu_index, state.pokemon_list, source_label, sprite_loader, trade_status, language=state.language)
        elif current_screen == "enter_room_name":
            draw_keyboard(screen, fonts, t(state.language, "room_name"), room_name, keyboard_index, False, keyboard_shift, state.language)
        elif current_screen == "enter_password":
            draw_keyboard(screen, fonts, t(state.language, "password"), room_password, keyboard_index, True, keyboard_shift, state.language)
        elif current_screen == "connecting":
            draw_connecting(screen, fonts, frame, state.language)
        elif current_screen == "waiting_partner":
            draw_waiting_partner(screen, fonts, trade_status, state.language)
        elif current_screen == "cancel_waiting_confirm":
            draw_cancel_waiting_confirm(screen, fonts, state.language)
        elif current_screen == "leave_room_confirm":
            draw_leave_room_confirm(screen, fonts, state.language)
        elif current_screen == "self_trade_confirm":
            draw_trade_confirm(
                screen,
                fonts,
                self_trade_pokemon_a or {},
                self_trade_context.get("payload_b", {}) if isinstance(self_trade_context, dict) else {},
                sprite_loader,
                state.language,
            )
        elif current_screen == "trade_confirm":
            draw_trade_confirm(
                screen,
                fonts,
                state.selected_pokemon or {},
                result_data if isinstance(result_data, dict) else {},
                sprite_loader,
                state.language,
            )
        elif current_screen == "info_modal":
            draw_info_modal(screen, fonts, info_modal_data.get("title", ""), info_modal_data.get("message", ""), state.language)
        elif current_screen == "deposit_confirm":
            target_pokemon = None
            if 0 <= pending_deposit_idx < len(state.pokemon_list):
                target_pokemon = state.pokemon_list[pending_deposit_idx]
            draw_deposit_confirm(screen, fonts, target_pokemon or {}, state.language)
        elif current_screen == "withdraw_confirm":
            draw_withdraw_confirm(screen, fonts, pending_withdraw_pokemon or {}, state.language)
        elif current_screen == "resolve_moves" and pending_removed_moves:
            draw_resolve_moves(
                screen,
                fonts,
                pending_removed_moves[resolve_current_idx],
                resolve_replacement_idx,
                resolve_current_idx,
                len(pending_removed_moves),
                set(resolved_moves_choices.values()),
                state.language,
            )
        elif current_screen == "evolution_cancel_prompt":
            anim_frame = max(0, frame - (evolution_anim_start if evolution_anim_start is not None else frame))
            draw_evolution_cancel_prompt(screen, fonts, result_data if isinstance(result_data, dict) else {}, sprite_loader, anim_frame, state.language)
        elif current_screen == "evolution_cancel_confirm":
            draw_evolution_cancel_confirm(screen, fonts, result_data if isinstance(result_data, dict) else {}, sprite_loader, frame, state.language)
        elif current_screen == "trading":
            draw_trading(screen, fonts, trade_status, state.language)
        elif current_screen == "trade_result":
            success = bool(isinstance(result_data, dict) and result_data.get("success"))
            data = result_data if success else result_data.get("error", trade_status) if isinstance(result_data, dict) else trade_status
            draw_trade_result(screen, fonts, success, data, state.language)

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
            text(screen, fonts[3], translate_literal(state.language, trade_status), 20, SCREEN_H - 78, WARN, SCREEN_W - 40)

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
