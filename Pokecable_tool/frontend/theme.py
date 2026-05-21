from __future__ import annotations

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


def palette_for_theme(theme_name):
    return THEMES.get(str(theme_name or "").strip().lower(), THEMES["pokedex_white"])

