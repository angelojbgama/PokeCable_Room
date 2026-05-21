"""Battery R: render every major draw_* function offscreen → PNG. Smoke check (must not crash)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "pokecable_runtime"))

import pygame  # noqa: E402

from tests._roundtrip.report import BatteryReport  # noqa: E402

SNAPSHOTS_DIR = REPO_ROOT / "tests" / "_snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _setup_pygame():
    pygame.init()
    pygame.font.init()
    return pygame.display.set_mode((640, 480))


def run() -> BatteryReport:
    report = BatteryReport(name="R: UI snapshots (smoke)")
    screen = _setup_pygame()
    from frontend.app import (  # noqa: E402
        draw_menu,
        draw_select_save,
        draw_config_menu,
        draw_pokedex_shell,
    )
    from frontend.fonts import font, title_font  # noqa: E402

    fonts = (title_font(28), font(14), font(12), font(10))

    targets = [
        ("menu_index_0", lambda: draw_menu(screen, fonts, 0, "pt")),
        ("menu_index_1", lambda: draw_menu(screen, fonts, 1, "pt")),
        ("config_menu_lang", lambda: draw_config_menu(screen, fonts, 0, "pt", "default")),
        ("select_save_empty", lambda: draw_select_save(screen, fonts, 0, [], None, "pt", None, 1.0)),
        ("pokedex_shell_only", lambda: draw_pokedex_shell(screen, "PokeCable", "", 1.0, False)),
    ]

    for name, fn in targets:
        screen.fill((0, 0, 0))
        try:
            fn()
        except Exception as exc:
            report.add_fail(f"{name}: render raised {type(exc).__name__}: {exc}")
            continue
        out_path = SNAPSHOTS_DIR / f"{name}.png"
        try:
            pygame.image.save(screen, str(out_path))
        except Exception as exc:
            report.add_fail(f"{name}: image.save raised {exc}")
            continue
        if out_path.stat().st_size <= 100:
            report.add_fail(f"{name}: PNG seems empty ({out_path.stat().st_size} bytes)")
        else:
            report.add_pass()
            report.note(f"{name} → {out_path.relative_to(REPO_ROOT)} ({out_path.stat().st_size} B)")

    pygame.quit()
    return report
