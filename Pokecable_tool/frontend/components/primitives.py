from __future__ import annotations

from dataclasses import dataclass, field
import time
import math
import hashlib

import pygame


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


def text(surface, fnt, value, x, y, color, max_w=None):
    value = str(value or "")
    if max_w is not None:
        value = fit_text(fnt, value, max_w)
    surface.blit(fnt.render(value, True, color), (x, y))


def text_center(surface, fnt, value, area, color):
    label = fit_text(fnt, value, max(1, area.w - 4))
    rendered = fnt.render(label, True, color)
    surface.blit(rendered, rendered.get_rect(center=area.center))


def text_right(surface, fnt, value, area, color):
    label = fit_text(fnt, value, area.w)
    rendered = fnt.render(label, True, color)
    screen_area = rendered.get_rect()
    screen_area.midright = area.midright
    surface.blit(rendered, screen_area)


def wrap_text(surface, fnt, value, area, color, line_gap=4, max_lines=None):
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
        return None
    safe_radius = max(0, min(int(radius or 0), min(normalized.w, normalized.h) // 2))
    return pygame.draw.rect(surface, color, normalized, border_radius=safe_radius)


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
    pygame.draw.rect(glass, (255, 255, 255, 54), glass.get_rect(), 1, border_radius=0)
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


def draw_digital_visor(screen, area, progress, tint=None):
    visor = pygame.Surface(area.size, pygame.SRCALPHA)
    base_color = tint if tint else (196, 206, 214, 255)
    visor.fill(base_color if len(base_color) == 4 else (*base_color, 255))
    glow_color = tint[:3] if tint else (170, 232, 206)
    glow_span = area.w + area.h
    glow_pos = int(progress * (glow_span + 40)) - 20
    for x in range(area.w):
        for y in range(0, area.h, 2):
            distance = abs((x + y) - glow_pos)
            if distance > 18:
                continue
            strength = 1.0 - (distance / 18.0)
            alpha = int(180 * strength) if tint else int(128 * strength)
            pygame.draw.line(visor, (*glow_color, alpha), (x, y), (x, min(area.h, y + 1)))
    for y in range(2, area.h - 2, 6):
        pygame.draw.line(visor, (236, 242, 236, 36), (2, y), (area.w - 3, y), 1)
    pygame.draw.rect(visor, (255, 255, 255, 70), visor.get_rect(), 1)
    screen.blit(visor, area.topleft)


def draw_type_badges(surface, font_obj, type_names, x, y, max_width, type_label, type_colors, muted_color):
    cursor_x = x
    for type_name in type_names[:2]:
        label = type_label(type_name)
        badge_w = min(82, max(42, font_obj.size(label)[0] + 14))
        if cursor_x + badge_w > x + max_width:
            break
        badge = pygame.Rect(cursor_x, y, badge_w, 18)
        rect(surface, type_colors.get(type_name, muted_color), badge, 0)
        text(surface, font_obj, label, badge.x + 7, badge.y + 4, (8, 12, 16), badge.w - 12)
        cursor_x += badge_w + 6


def draw_item_icon(surface, area, item_info, selected=False, selected_fill=(0, 0, 0), fill=(255, 255, 255), muted=(155, 155, 155), text_color=(23, 27, 63)):
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
    rect(surface, selected_fill if selected else fill, area, 0)
    if not item_info:
        pygame.draw.line(surface, muted, (area.x + 7, area.centery), (area.right - 7, area.centery), 2)
        return
    color = category_colors.get(str(item_info.get("category") or "item"), category_colors["item"])
    pygame.draw.circle(surface, color, area.center, min(area.w, area.h) // 3)
    pygame.draw.circle(surface, text_color, (area.centerx - 3, area.centery - 3), 2)


@dataclass(slots=True)
class SelectableListItemStyle:
    fill_color: tuple[int, int, int] = (222, 239, 253)
    selected_fill_color: tuple[int, int, int] = (18, 173, 218)
    border_color: tuple[int, int, int] = (31, 73, 124)
    selected_inner_color: tuple[int, int, int] = (255, 255, 255)
    radius: int = 0
    border_width: int = 2
    selected_inner_inset: int = 6


def draw_selectable_list_item(surface, area, selected=False, style=None):
    style = style or SelectableListItemStyle()
    area = pygame.Rect(area)
    fill = style.selected_fill_color if selected else style.fill_color
    rect(surface, fill, area, style.radius)
    pygame.draw.rect(surface, style.border_color, area, style.border_width, border_radius=style.radius)
    if selected and style.selected_inner_inset > 0:
        inner = area.inflate(-style.selected_inner_inset, -style.selected_inner_inset)
        if inner.w > 0 and inner.h > 0:
            inner_radius = max(0, style.radius - 1)
            pygame.draw.rect(surface, style.selected_inner_color, inner, 1, border_radius=inner_radius)
    return area


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


@dataclass(slots=True)
class FooterActionStyle:
    """Style and layout values for footer action hints."""

    screen_size: tuple[int, int] = (640, 480)
    footer_margin_x: int = 22
    footer_bottom_offset: int = 32
    button_height: int = 26
    gap: int = 6
    min_button_width: int = 64
    max_button_width: int = 132
    compressed_button_width: int = 60
    label_pad_width: int = 42
    shadow_color: tuple[int, int, int] = (209, 230, 248)
    fill_color: tuple[int, int, int] = (247, 252, 255)
    border_color: tuple[int, int, int] = (40, 36, 93)
    cap_color: tuple[int, int, int] = (24, 212, 242)
    cap_text_color: tuple[int, int, int] = (234, 251, 255)
    text_color: tuple[int, int, int] = (23, 27, 63)

    def footer_rect(self) -> pygame.Rect:
        screen_w, screen_h = self.screen_size
        return pygame.Rect(
            self.footer_margin_x,
            screen_h - self.footer_bottom_offset,
            screen_w - self.footer_margin_x * 2,
            self.button_height,
        )


def draw_footer_action_button(surface, action, area, button_font, cap_font, style):
    label, desc = action
    desc = compact_action_label(desc)
    area = pygame.Rect(area)
    rect(surface, style.shadow_color, area.move(1, 1), 4)
    rect(surface, style.fill_color, area, 4)
    pygame.draw.rect(surface, style.border_color, area, 1, border_radius=4)

    cap = pygame.Rect(area.x + 4, area.y + 3, 20, max(1, area.h - 6))
    rect(surface, style.cap_color, cap, 4)
    text_center(surface, cap_font, label, cap, style.cap_text_color)

    desc_area = pygame.Rect(cap.right + 6, area.y + 1, area.right - cap.right - 10, area.h - 2)
    text_center(surface, button_font, desc, desc_area, style.text_color)


def draw_footer_actions(surface, actions, button_font, cap_font, style=None):
    style = style or FooterActionStyle()
    footer = style.footer_rect()
    compact_actions = [(label, compact_action_label(desc)) for label, desc in actions]
    widths = [
        max(
            style.min_button_width,
            min(style.max_button_width, button_font.size(str(desc or ""))[0] + style.label_pad_width),
        )
        for _, desc in compact_actions
    ]
    total = sum(widths) + style.gap * max(0, len(widths) - 1)
    if total > footer.w:
        width = max(
            style.compressed_button_width,
            (footer.w - style.gap * max(0, len(widths) - 1)) // max(1, len(widths)),
        )
        widths = [width] * len(widths)

    x = footer.x
    for action, width in zip(compact_actions, widths):
        area = pygame.Rect(x, footer.y, width, style.button_height)
        draw_footer_action_button(surface, action, area, button_font, cap_font, style)
        x += width + style.gap


@dataclass(slots=True)
class PokedexStyle:
    screen_size: tuple[int, int] = (640, 480)
    header_height: int = 44
    footer_height: int = 60
    bg: tuple[int, int, int] = (239, 248, 255)
    shell: tuple[int, int, int] = (244, 249, 254)
    shell_2: tuple[int, int, int] = (35, 103, 183)
    panel_2: tuple[int, int, int] = (222, 239, 253)
    screen: tuple[int, int, int] = (18, 44, 83)
    screen_text: tuple[int, int, int] = (238, 248, 255)
    border: tuple[int, int, int] = (31, 73, 124)
    shadow: tuple[int, int, int] = (168, 196, 224)
    muted: tuple[int, int, int] = (83, 111, 141)
    accent: tuple[int, int, int] = (18, 173, 218)
    ok: tuple[int, int, int] = (32, 125, 207)
    red: tuple[int, int, int] = (224, 55, 76)
    warn: tuple[int, int, int] = (232, 169, 37)


@dataclass(slots=True)
class PokedexFrame:
    screen_size: tuple[int, int] = (640, 480)
    header_height: int = 44
    footer_height: int = 60
    content: pygame.Rect = field(init=False)
    left_panel: pygame.Rect = field(init=False)
    right_panel: pygame.Rect = field(init=False)
    side_screen: pygame.Rect = field(init=False)
    keypad: pygame.Rect = field(init=False)
    footer: pygame.Rect = field(init=False)
    modal: pygame.Rect = field(init=False)

    def __post_init__(self):
        screen_w, screen_h = self.screen_size
        self.content = pygame.Rect(24, 84, screen_w - 48, screen_h - self.header_height - self.footer_height - 56)
        self.left_panel = pygame.Rect(20, 98, 286, 323)
        self.right_panel = pygame.Rect(337, 98, 286, 323)
        self.side_screen = pygame.Rect(390, 124, 168, 54)
        self.keypad = pygame.Rect(342, 214, 256, 144)
        self.footer = pygame.Rect(22, screen_h - 28, screen_w - 44, 22)
        self.modal = pygame.Rect(58, 118, screen_w - 116, 220)

    def __getattr__(self, name):
        return getattr(self.content, name)

    def __getitem__(self, name):
        return getattr(self, name)


def right_info_panel(layout, top_offset=0, inset_x=0, bottom_pad=0):
    base = layout.right_panel
    return pygame.Rect(base.x + inset_x, base.y + top_offset, base.w - inset_x * 2, base.h - bottom_pad)


def draw_right_panel_frame(screen, panel, style, progress=None, glass=False):
    if glass:
        draw_glass_panel(screen, panel, progress if progress is not None else 0.0)
    else:
        rect(screen, style.panel_2, panel, 0)
    pygame.draw.rect(screen, style.border, panel, 2, border_radius=0)


def draw_pokedex_shell(
    screen,
    title="",
    subtitle="",
    style=None,
    font_func=None,
    title_font_func=None,
    lens_state=None,
    title_state=None,
    loading_progress=0.0,
    pulsing=False,
    ok_pulse=False,
    warn_pulse=False,
    shell_status="neutral",
):
    style = style or PokedexStyle()
    lens_state = lens_state if lens_state is not None else {"start_time": 0.0, "title": None}
    title_state = title_state if title_state is not None else {"start_time": 0.0}
    screen.fill(style.bg)
    frame = PokedexFrame(style.screen_size, style.header_height, style.footer_height)

    left_body = pygame.Rect(10, 8, 300, 418)
    right_points = [
        (330, 38), (418, 38), (436, 39), (454, 43), (472, 50), (490, 60), (510, 72), (530, 84), (554, 92), (630, 92),
        (630, 426), (330, 426),
    ]
    hinge = pygame.Rect(308, 38, 25, 388)

    rect(screen, style.shadow, left_body.move(0, 8), 0)
    pygame.draw.polygon(screen, style.shadow, [(x, y + 8) for x, y in right_points])
    rect(screen, style.shell, left_body, 0)
    pygame.draw.polygon(screen, style.shell_2, right_points)
    pygame.draw.lines(screen, style.border, True, right_points, 2)
    pygame.draw.rect(screen, style.border, left_body, 2, border_radius=0)

    compartment_points = [
        (310, 38), (222, 38), (204, 39), (186, 43), (168, 50), (150, 60),
        (130, 72), (110, 84), (86, 92), (10, 92),
        (10, 426), (310, 426),
    ]
    pygame.draw.polygon(screen, style.shadow, compartment_points)
    inner_compartment = [(x + 2, y + 2) for (x, y) in compartment_points]
    pygame.draw.polygon(screen, style.shell_2, inner_compartment)
    pygame.draw.lines(screen, style.border, True, compartment_points, 2)

    hinge_body = pygame.Rect(hinge.x + 1, hinge.y + 1, hinge.w - 2, hinge.h - 2)
    pygame.draw.rect(screen, style.shell_2, hinge_body, border_radius=0)
    highlight = pygame.Rect(hinge.x + 4, hinge.y + 4, 4, hinge.h - 8)
    pygame.draw.rect(screen, style.shell, highlight, border_radius=0)
    for offset in (18, hinge.h - 18):
        pygame.draw.line(screen, style.border, (hinge.x + 2, hinge.y + offset), (hinge.right - 2, hinge.y + offset), 2)
    pygame.draw.rect(screen, style.border, hinge_body, 2, border_radius=0)

    if lens_state["title"] != title:
        lens_state["title"] = title
        lens_state["start_time"] = time.perf_counter()

    if shell_status == "neutral":
        if pulsing:
            shell_status = "loading"
        elif ok_pulse:
            shell_status = "success"
        elif warn_pulse:
            shell_status = "confirm"

    current_time = time.perf_counter()
    loading_active = shell_status == "loading" or loading_progress < 1.0
    confirm_active = shell_status == "confirm"
    success_active = shell_status == "success"
    error_active = shell_status == "error"

    muted_color = (155, 155, 155)
    accent_color = style.accent

    if loading_active:
        progress = min(1.0, loading_progress)
        pulse = 0.5 + 0.5 * math.sin(current_time * 5.0)
        if loading_progress >= 1.0:
            progress = 0.55 + 0.45 * pulse
        accent_color = (
            int(muted_color[0] + (style.accent[0] - muted_color[0]) * progress),
            int(muted_color[1] + (style.accent[1] - muted_color[1]) * progress),
            int(muted_color[2] + (style.accent[2] - muted_color[2]) * progress),
        )
    else:
        accent_color = style.accent

    pygame.draw.circle(screen, style.screen, (49, 47), 33)
    pygame.draw.circle(screen, (237, 249, 255), (49, 47), 28)
    pygame.draw.circle(screen, accent_color, (49, 47), 23)

    lens_elapsed = max(0.0, time.perf_counter() - lens_state["start_time"])
    lens_duration = 0.9
    if shell_status in {"loading", "confirm", "success", "error"} and lens_elapsed <= lens_duration:
        draw_lens_pulse(screen, (49, 47), lens_elapsed / lens_duration)
    elif shell_status in {"loading", "confirm", "success", "error"}:
        lens_state["start_time"] = time.perf_counter()

    pygame.draw.circle(screen, (144, 229, 252), (41, 38), 8)
    pygame.draw.circle(screen, (255, 255, 255), (36, 31), 5)

    led_specs = (
        ("error", 100, style.red, (255, 80, 100), (80, 20, 30)),
        ("confirm", 128, style.warn, (255, 220, 70), (100, 80, 20)),
        ("success", 156, style.ok, (70, 235, 120), (25, 90, 45)),
    )
    for led_name, x, color, bright_color, dim_color in led_specs:
        pygame.draw.circle(screen, style.border, (x, 32), 12)
        led_color = color
        highlight = False
        if loading_active:
            hash_val = int(hashlib.md5(str(x).encode()).hexdigest(), 16)
            cycle_offset = (hash_val % 10) / 10.0
            is_on = ((current_time * 3.0 + cycle_offset) % 1.0) < 0.3
            led_color = bright_color if is_on else dim_color
            highlight = is_on
        elif (
            (error_active and led_name == "error")
            or (confirm_active and led_name == "confirm")
            or (success_active and led_name == "success")
        ):
            pulse = 0.5 + 0.5 * math.sin(current_time * 4.0)
            led_color = tuple(int(dim_color[idx] + (bright_color[idx] - dim_color[idx]) * pulse) for idx in range(3))
            highlight = pulse > 0.7
        pygame.draw.circle(screen, led_color, (x, 32), 9)
        if highlight:
            pygame.draw.circle(screen, (255, 255, 255), (x - 2, 29), 3)

    title_panel = pygame.Rect(202, 4, 418, 30)
    if not title_state["start_time"]:
        title_state["start_time"] = time.perf_counter()
    sweep_elapsed = max(0.0, time.perf_counter() - title_state["start_time"])
    sweep_duration = 1.1
    if title and title_font_func is not None:
        title_f = title_font_func(24)
        title_label = fit_text(title_f, str(title), title_panel.w - 18)
        title_surface = title_f.render(title_label, True, (255, 255, 255))
        sweep_surface = render_title_sweep(title_surface, (sweep_elapsed % sweep_duration) / sweep_duration)
        title_y = title_panel.y + max(0, (title_panel.h - title_surface.get_height()) // 2)
        title_x = title_panel.right - 9 - title_surface.get_width()
        screen.blit(sweep_surface, (title_x, title_y))
    if subtitle and font_func is not None:
        subtitle_font = font_func(13)
        subtitle_surface = subtitle_font.render(str(subtitle), True, style.muted)
        subtitle_x = max(title_panel.x + 10, title_panel.right - 10 - subtitle_surface.get_width())
        screen.blit(subtitle_surface, (subtitle_x, title_panel.bottom + 3))

    return frame


@dataclass(slots=True)
class Scrollbar:
    """Reusable scrollbar component for list-style screens."""

    thumb_color: tuple[int, int, int] = (24, 212, 242)
    border_color: tuple[int, int, int] = (40, 36, 93)
    rail_color: tuple[int, int, int] = (238, 248, 255)
    hinge_rect: tuple[int, int, int, int] = (308, 38, 25, 388)
    track_width: int = 11
    rail_width: int = 7
    thumb_min_height: int = 24

    def _track_rect(self) -> pygame.Rect:
        hinge = pygame.Rect(self.hinge_rect)
        return pygame.Rect(
            hinge.x + (hinge.w - self.track_width) // 2,
            hinge.y + 22,
            self.track_width,
            hinge.h - 44,
        )

    def _draw_track(self, surface, track, offset, total, visible) -> None:
        if total <= visible:
            return

        max_offset = max(1, total - visible)
        rail = pygame.Rect(track.x + (track.w - self.rail_width) // 2, track.y + 1, self.rail_width, track.h - 2)
        thumb_h = max(self.thumb_min_height, int(track.h * visible / total))
        thumb_y = track.y + int((track.h - thumb_h) * min(max(offset, 0), max_offset) / max_offset)
        thumb = pygame.Rect(track.x + 1, thumb_y, track.w - 2, thumb_h)

        pygame.draw.rect(surface, self.border_color, track, border_radius=4)
        pygame.draw.rect(surface, self.rail_color, rail, border_radius=2)

        pygame.draw.rect(surface, self.thumb_color, thumb, border_radius=5)
        pygame.draw.rect(surface, self.border_color, thumb, 1, border_radius=5)

    def draw(
        self,
        surface,
        offset,
        total,
        visible=6,
    ) -> None:
        track = self._track_rect()
        self._draw_track(surface, track, offset, total, visible)


LIST_SCROLLBAR = Scrollbar()

__all__ = [
    "FooterActionStyle",
    "PokedexFrame",
    "PokedexStyle",
    "SelectableListItemStyle",
    "Scrollbar",
    "LIST_SCROLLBAR",
    "compact_action_label",
    "draw_digital_visor",
    "draw_footer_action_button",
    "draw_footer_actions",
    "draw_glass_panel",
    "draw_item_icon",
    "draw_lens_pulse",
    "draw_pokedex_shell",
    "draw_right_panel_frame",
    "draw_selectable_list_item",
    "draw_type_badges",
    "fit_text",
    "normalized_rect",
    "rect",
    "render_title_sweep",
    "right_info_panel",
    "text",
    "text_center",
    "text_right",
    "wrap_text",
]
