#!/usr/bin/env python3
import os
import signal
import time
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame


SCREEN_W = 640
SCREEN_H = 480
HEADER_H = 42
FOOTER_H = 48
LIST_W = 292
ROW_H = 26
LIST_RECT = pygame.Rect(10, HEADER_H + 10, LIST_W, SCREEN_H - HEADER_H - FOOTER_H - 20)
DETAIL_RECT = pygame.Rect(LIST_W + 20, HEADER_H + 10, SCREEN_W - LIST_W - 30, SCREEN_H - HEADER_H - FOOTER_H - 20)
APP_DIR = Path(__file__).resolve().parent
LOG_FILE = APP_DIR / "task_manager.log"
CLK_TICKS = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
CPU_COUNT = max(1, os.cpu_count() or 1)
REFRESH_SECONDS = 1.0
SORTS = ["cpu", "mem", "pid", "name"]

BG = (14, 18, 24)
PANEL = (25, 31, 40)
PANEL_2 = (34, 42, 52)
TEXT = (230, 236, 242)
MUTED = (145, 157, 171)
ACCENT = (72, 176, 255)
OK = (80, 210, 142)
WARN = (255, 190, 88)
BAD = (240, 96, 96)
BLACK = (0, 0, 0)


def log(msg):
    try:
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%F %T')} {msg}\n")
    except Exception:
        pass


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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


def read_mem_total_kb():
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1])
    except Exception:
        pass
    return 1


MEM_TOTAL_KB = max(1, read_mem_total_kb())


def read_total_cpu_ticks():
    with open("/proc/stat", "r", encoding="utf-8") as handle:
        parts = handle.readline().split()[1:]
    return sum(int(value) for value in parts)


def read_process_info(pid):
    stat_path = f"/proc/{pid}/stat"
    status_path = f"/proc/{pid}/status"
    with open(stat_path, "r", encoding="utf-8") as handle:
        raw = handle.read().strip()
    right = raw.rfind(")")
    left = raw.find("(")
    name = raw[left + 1:right]
    fields = raw[right + 2:].split()
    state = fields[0]
    utime = int(fields[11])
    stime = int(fields[12])
    threads = int(fields[17])
    rss_pages = int(fields[21])
    ppid = int(fields[1])
    mem_kb = max(0, rss_pages * PAGE_SIZE // 1024)
    uid = "?"
    cmdline = ""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as handle:
            cmdline = handle.read().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
    except Exception:
        pass
    try:
        with open(status_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("Uid:"):
                    uid = line.split()[1]
                    break
    except Exception:
        pass
    return {
        "pid": pid,
        "ppid": ppid,
        "name": name,
        "state": state,
        "threads": threads,
        "mem_kb": mem_kb,
        "mem_pct": mem_kb * 100.0 / MEM_TOTAL_KB,
        "ticks": utime + stime,
        "cmdline": cmdline or name,
        "uid": uid,
        "cpu_pct": 0.0,
    }


class ProcessModel:
    def __init__(self):
        self.prev_total = None
        self.prev_proc = {}
        self.items = []
        self.last_error = ""

    def refresh(self):
        total_ticks = read_total_cpu_ticks()
        entries = []
        current_ticks = {}
        for name in os.listdir("/proc"):
            if not name.isdigit():
                continue
            pid = int(name)
            try:
                info = read_process_info(pid)
            except Exception:
                continue
            current_ticks[pid] = info["ticks"]
            if self.prev_total is not None and pid in self.prev_proc:
                proc_delta = info["ticks"] - self.prev_proc[pid]
                total_delta = max(1, total_ticks - self.prev_total)
                info["cpu_pct"] = max(0.0, proc_delta * 100.0 * CPU_COUNT / total_delta)
            entries.append(info)
        self.prev_total = total_ticks
        self.prev_proc = current_ticks
        self.items = entries
        self.last_error = ""


def sort_items(items, mode):
    if mode == "name":
        return sorted(items, key=lambda item: (item["name"].lower(), item["pid"]))
    if mode == "pid":
        return sorted(items, key=lambda item: item["pid"])
    if mode == "mem":
        return sorted(items, key=lambda item: (-item["mem_kb"], -item["cpu_pct"], item["pid"]))
    return sorted(items, key=lambda item: (-item["cpu_pct"], -item["mem_kb"], item["pid"]))


def visible_rows():
    return max(1, (LIST_RECT.h - 34) // ROW_H)


def clamp_state(state):
    items = state["items"]
    if not items:
        state["selected"] = 0
        state["top"] = 0
        return
    state["selected"] = max(0, min(state["selected"], len(items) - 1))
    vis = visible_rows()
    if state["selected"] < state["top"]:
        state["top"] = state["selected"]
    if state["selected"] >= state["top"] + vis:
        state["top"] = state["selected"] - vis + 1
    state["top"] = max(0, min(state["top"], max(0, len(items) - vis)))


def format_mem(mem_kb):
    if mem_kb >= 1024 * 1024:
        return f"{mem_kb / (1024 * 1024):.2f}G"
    if mem_kb >= 1024:
        return f"{mem_kb / 1024:.1f}M"
    return f"{mem_kb}K"


def kill_process(pid, sig):
    try:
        os.kill(pid, sig)
        return True, f"signal {sig} sent to {pid}"
    except ProcessLookupError:
        return False, f"process {pid} already exited"
    except PermissionError:
        return False, f"permission denied for {pid}"
    except Exception as exc:
        return False, str(exc)


def draw_ui(screen, fonts, state):
    title_f, body_f, small_f, tiny_f = fonts
    screen.fill(BG)
    rect(screen, PANEL, pygame.Rect(0, 0, SCREEN_W, HEADER_H))
    text(screen, title_f, "Task Manager", 14, 9)
    text(screen, body_f, f"Sort: {state['sort'].upper()}", SCREEN_W - 150, 13, ACCENT)

    rect(screen, PANEL, LIST_RECT, 6)
    text(screen, small_f, f"Processes ({len(state['items'])})", LIST_RECT.x + 12, LIST_RECT.y + 10, MUTED)

    vis = visible_rows()
    for row_idx in range(vis):
        idx = state["top"] + row_idx
        if idx >= len(state["items"]):
            break
        item = state["items"][idx]
        y = LIST_RECT.y + 34 + row_idx * ROW_H
        row = pygame.Rect(LIST_RECT.x + 8, y, LIST_RECT.w - 16, ROW_H - 4)
        selected = idx == state["selected"]
        rect(screen, ACCENT if selected else PANEL_2, row, 4)
        color = (5, 11, 18) if selected else TEXT
        text(screen, tiny_f, f"{item['pid']:>5}", row.x + 8, row.y + 5, color)
        text(screen, tiny_f, item["name"], row.x + 56, row.y + 5, color, 116)
        text(screen, tiny_f, f"{item['cpu_pct']:4.1f}%", row.right - 106, row.y + 5, color)
        text(screen, tiny_f, format_mem(item["mem_kb"]), row.right - 54, row.y + 5, color)

    rect(screen, PANEL, DETAIL_RECT, 6)
    if state["items"]:
        item = state["items"][state["selected"]]
        y = DETAIL_RECT.y + 16
        text(screen, body_f, item["name"], DETAIL_RECT.x + 14, y, TEXT, DETAIL_RECT.w - 28)
        y += 28
        text(screen, small_f, f"PID {item['pid']}  PPID {item['ppid']}  UID {item['uid']}", DETAIL_RECT.x + 14, y, MUTED)
        y += 24
        text(screen, small_f, f"CPU: {item['cpu_pct']:.1f}%   RAM: {format_mem(item['mem_kb'])} ({item['mem_pct']:.1f}%)", DETAIL_RECT.x + 14, y, TEXT)
        y += 24
        text(screen, small_f, f"State: {item['state']}   Threads: {item['threads']}", DETAIL_RECT.x + 14, y, TEXT)
        y += 30
        text(screen, small_f, "Command", DETAIL_RECT.x + 14, y, MUTED)
        y += 20
        cmd = item["cmdline"] or item["name"]
        max_w = DETAIL_RECT.w - 28
        line_h = 18
        while cmd and y < DETAIL_RECT.bottom - 50:
            chunk = cmd
            while chunk and small_f.size(chunk)[0] > max_w:
                chunk = chunk[:-1]
            if not chunk:
                break
            text(screen, small_f, chunk, DETAIL_RECT.x + 14, y, TEXT, max_w)
            cmd = cmd[len(chunk):].lstrip()
            y += line_h
    else:
        text(screen, body_f, "No processes", DETAIL_RECT.x + 20, DETAIL_RECT.y + 24, MUTED)

    status = state.get("status", "")
    if status:
        color = BAD if "denied" in status or "error" in status else (WARN if "signal" in status else MUTED)
        text(screen, small_f, status, 14, SCREEN_H - FOOTER_H - 22, color, SCREEN_W - 28)

    rect(screen, PANEL, pygame.Rect(0, SCREEN_H - FOOTER_H, SCREEN_W, FOOTER_H))
    button(screen, tiny_f, "A", "terminate", 12, SCREEN_H - 36)
    button(screen, tiny_f, "X", "force kill", 132, SCREEN_H - 36)
    button(screen, tiny_f, "Y", "refresh", 256, SCREEN_H - 36)
    button(screen, tiny_f, "B", "exit", 350, SCREEN_H - 36)
    text(screen, tiny_f, "Left/Right: sort  L1/R1: page", 430, SCREEN_H - 30, MUTED)

    modal = state.get("confirm")
    if modal:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        box = pygame.Rect(88, 166, 464, 142)
        rect(screen, PANEL_2, box, 8)
        text(screen, body_f, modal["title"], box.x + 20, box.y + 18, TEXT)
        text(screen, small_f, modal["line1"], box.x + 20, box.y + 56, MUTED, box.w - 40)
        text(screen, small_f, modal["line2"], box.x + 20, box.y + 80, MUTED, box.w - 40)
        text(screen, small_f, "A confirma   B cancela", box.x + 20, box.y + 110, ACCENT)

    pygame.display.flip()


def build_confirm(item, sig_name):
    return {
        "title": f"{sig_name} {item['name']}?",
        "line1": f"PID {item['pid']}  CPU {item['cpu_pct']:.1f}%  RAM {format_mem(item['mem_kb'])}",
        "line2": item["cmdline"][:72],
    }


def main():
    pygame.init()
    pygame.font.init()
    try:
        pygame.joystick.init()
    except Exception:
        pass
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Task Manager")
    fonts = (font(24, True), font(19, True), font(17), font(15))
    clock = pygame.time.Clock()

    model = ProcessModel()
    state = {
        "items": [],
        "selected": 0,
        "top": 0,
        "sort": "cpu",
        "status": "",
        "confirm": None,
        "confirm_signal": None,
        "last_refresh": 0.0,
    }

    def refresh():
        model.refresh()
        state["items"] = sort_items(model.items, state["sort"])
        clamp_state(state)
        state["last_refresh"] = time.time()

    refresh()
    state["status"] = "A encerra, X forca, Y atualiza"
    running = True

    while running:
        now = time.time()
        if now - state["last_refresh"] >= REFRESH_SECONDS and not state["confirm"]:
            refresh()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state["confirm"]:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        item = state["items"][state["selected"]] if state["items"] else None
                        sig = state["confirm_signal"]
                        state["confirm"] = None
                        state["confirm_signal"] = None
                        if item:
                            if item["pid"] in (1, os.getpid()):
                                state["status"] = f"blocked pid {item['pid']}"
                            else:
                                ok, msg = kill_process(item["pid"], sig)
                                state["status"] = msg
                                refresh()
                    elif event.key in (pygame.K_BACKSPACE, pygame.K_ESCAPE):
                        state["confirm"] = None
                        state["confirm_signal"] = None
                    continue

                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    running = False
                elif event.key == pygame.K_DOWN:
                    state["selected"] += 1
                    clamp_state(state)
                elif event.key == pygame.K_UP:
                    state["selected"] -= 1
                    clamp_state(state)
                elif event.key == pygame.K_PAGEUP:
                    state["selected"] -= visible_rows()
                    clamp_state(state)
                elif event.key == pygame.K_PAGEDOWN:
                    state["selected"] += visible_rows()
                    clamp_state(state)
                elif event.key == pygame.K_LEFT:
                    idx = (SORTS.index(state["sort"]) - 1) % len(SORTS)
                    state["sort"] = SORTS[idx]
                    state["items"] = sort_items(model.items, state["sort"])
                    clamp_state(state)
                elif event.key == pygame.K_RIGHT:
                    idx = (SORTS.index(state["sort"]) + 1) % len(SORTS)
                    state["sort"] = SORTS[idx]
                    state["items"] = sort_items(model.items, state["sort"])
                    clamp_state(state)
                elif event.key == pygame.K_y:
                    refresh()
                    state["status"] = "list refreshed"
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if state["items"]:
                        item = state["items"][state["selected"]]
                        state["confirm"] = build_confirm(item, "Terminate")
                        state["confirm_signal"] = signal.SIGTERM
                elif event.key == pygame.K_x:
                    if state["items"]:
                        item = state["items"][state["selected"]]
                        state["confirm"] = build_confirm(item, "Force kill")
                        state["confirm_signal"] = signal.SIGKILL

        draw_ui(screen, fonts, state)
        clock.tick(30)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
