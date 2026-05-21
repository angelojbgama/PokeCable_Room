from __future__ import annotations

import threading

from frontend.i18n import screen_title
from frontend.screens.base import ScreenBase, show_info_modal


class MenuScreen(ScreenBase):
    screen_id = "menu"

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = (session.menu_index - 1) % 4
        elif action == "down":
            session.menu_index = (session.menu_index + 1) % 4
        elif action == "select":
            if session.menu_index == 0:
                services.reset_flow_state(state)
                state.find_saves()
                ctx.logger.info("Menu select: access room")
                services.switch_screen("load_save", "menu_access_room")
                session.menu_index = 0
            elif session.menu_index == 1:
                services.reset_flow_state(state)
                services.reset_self_trade_state()
                state.find_saves()
                ctx.logger.info("Menu select: self trade")
                services.switch_screen("self_select_save_a", "menu_self_trade")
                session.menu_index = 0
            elif session.menu_index == 2:
                ctx.logger.info("Menu select: config")
                services.switch_screen("config", "menu_config")
                session.menu_index = 0
            elif session.menu_index == 3:
                ctx.logger.info("Menu select: exit")
                session.running = False
        elif action == "back":
            ctx.logger.info("Menu back: exit")
            session.running = False

    def render(self, ctx, session, state, services):
        ctx.draw.draw_menu(ctx.screen, ctx.fonts, session.menu_index, state.language)


class ConfigScreen(ScreenBase):
    screen_id = "config"

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = (session.menu_index - 1) % 2
        elif action == "down":
            session.menu_index = (session.menu_index + 1) % 2
        elif action in ("left", "right"):
            if session.menu_index == 0:
                order = ["pt", "en", "es"]
                index = order.index(state.language) if state.language in order else 0
                direction = -1 if action == "left" else 1
                state.language = order[(index + direction) % len(order)]
                session.config_dirty = True
            else:
                state.theme = ctx.draw.next_theme(state.theme, -1 if action == "left" else 1)
                services.apply_theme(state.theme)
                session.config_dirty = True
        elif action == "select":
            state.save_ui_config(state.language, state.theme)
            session.config_dirty = False
            services.switch_screen("menu", "config_saved")
            session.menu_index = 0
        elif action == "back":
            if session.config_dirty:
                state.save_ui_config(state.language, state.theme)
                session.config_dirty = False
            services.switch_screen("menu", "back_from_config")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        ctx.draw.draw_config_menu(ctx.screen, ctx.fonts, session.menu_index, state.language, state.theme)


class LoadSaveScreen(ScreenBase):
    screen_id = "load_save"

    def __init__(self):
        super().__init__()
        self._preload_thread = None
        self._valid_saves = []
        self._preload_done = False
        self._preload_progress = 0.0

    def _preload_saves_thread(self, state, ctx):
        """Thread para pré-carregar análise dos saves."""
        try:
            ctx.logger.info("Pre-analyzing saves in background...")
            total = len(state.saves)

            for idx, save_path in enumerate(state.saves):
                try:
                    state.analyze_save(save_path)
                except Exception as exc:
                    ctx.logger.debug("Failed to pre-analyze %s: %s", save_path.name, exc)
                finally:
                    self._preload_progress = (idx + 1) / total if total > 0 else 0

            self._valid_saves = []
            for save_path in state.saves:
                try:
                    analysis = state.analyze_save(save_path)
                    if analysis and analysis.get("party_count", 0) > 0:
                        self._valid_saves.append(save_path)
                except Exception:
                    pass

            ctx.logger.info("Pre-analysis complete: %d valid saves", len(self._valid_saves))
            self._preload_done = True
        except Exception as exc:
            ctx.logger.error("Error during preload: %s", exc)
            self._preload_done = True

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            max_idx = len(self._valid_saves) - 1 if self._valid_saves else len(state.saves) - 1
            session.menu_index = max(0, session.menu_index - 1)
            if session.menu_index > max_idx:
                session.menu_index = max_idx
        elif action == "down":
            max_idx = len(self._valid_saves) - 1 if self._valid_saves else len(state.saves) - 1
            session.menu_index = min(max_idx, session.menu_index + 1)
        elif action == "select":
            saves_to_use = self._valid_saves if self._valid_saves else state.saves
            if saves_to_use and 0 <= session.menu_index < len(saves_to_use):
                state.selected_save = saves_to_use[session.menu_index]
                state.selected_pokemon = None
                state.pokemon_list = []
                state.room_name = "Sala LAN"
                state.room_password = ""
                state.lan_manual_endpoint = ""
                state.action = "lan"
                ctx.logger.info("Save selected: %s", state.selected_save)
                services.trade_thread_ref.current = services.start_lan_trade_thread(
                    state,
                    services.ui_queue,
                    services.confirm_queue,
                )
                services.switch_screen("connecting", "lan_trade_thread_started")
                session.keyboard_index = 0
                session.keyboard_shift = False
                session.room_name = ""
                session.room_password = ""
                session.trade_status = "Procurando sala local na rede..."
                session.menu_index = 0
        elif action == "back":
            services.switch_screen("menu", "back_from_load_save")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        if self._preload_thread is None and state.saves:
            self._preload_thread = threading.Thread(
                target=self._preload_saves_thread,
                args=(state, ctx),
                daemon=True
            )
            self._preload_thread.start()

        progress = 1.0
        if self._preload_thread is not None and not self._preload_done:
            progress = self._preload_progress

        saves_to_show = self._valid_saves if self._preload_done and self._valid_saves else state.saves

        if session.menu_index >= len(saves_to_show):
            session.menu_index = max(0, len(saves_to_show) - 1)

        ctx.draw.draw_select_save(ctx.screen, ctx.fonts, session.menu_index, saves_to_show, language=state.language, state=state, is_loading=progress)

        if self._preload_done and progress >= 1.0:
            import time
            if not hasattr(self, '_pulse_start'):
                self._pulse_start = time.perf_counter()
            pulse_elapsed = time.perf_counter() - self._pulse_start
            pulse_duration = 0.9
            if pulse_elapsed <= pulse_duration:
                from frontend.components.primitives import draw_lens_pulse
                draw_lens_pulse(ctx.screen, (55, 57), pulse_elapsed / pulse_duration)


class SelfSelectSaveAScreen(ScreenBase):
    screen_id = "self_select_save_a"

    def __init__(self):
        super().__init__()
        self._preload_thread = None
        self._preload_done = False
        self._preload_progress = 0.0

    def _preload_saves_thread(self, state, ctx):
        """Thread para pré-carregar análise dos saves."""
        try:
            ctx.logger.info("Pre-analyzing saves in background...")
            total = len(state.saves)

            for idx, save_path in enumerate(state.saves):
                try:
                    state.analyze_save(save_path)
                except Exception as exc:
                    ctx.logger.debug("Failed to pre-analyze %s: %s", save_path.name, exc)
                finally:
                    self._preload_progress = (idx + 1) / total if total > 0 else 0

            ctx.logger.info("Pre-analysis complete for save A")
            self._preload_done = True
        except Exception as exc:
            ctx.logger.error("Error during preload: %s", exc)
            self._preload_done = True

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = max(0, session.menu_index - 1)
        elif action == "down":
            session.menu_index = min(max(0, len(state.saves) - 1), session.menu_index + 1)
        elif action == "select" and state.saves:
            session.self_trade_save_a = state.saves[session.menu_index]
            ctx.logger.info("Self trade save A selected: %s", session.self_trade_save_a)
            services.switch_screen("self_select_save_b", "self_save_a_selected")
            session.menu_index = 0
        elif action == "back":
            services.reset_self_trade_state()
            services.switch_screen("menu", "back_from_self_save_a")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        if self._preload_thread is None and state.saves:
            self._preload_thread = threading.Thread(
                target=self._preload_saves_thread,
                args=(state, ctx),
                daemon=True
            )
            self._preload_thread.start()

        progress = 1.0
        if self._preload_thread is not None and not self._preload_done:
            progress = self._preload_progress

        ctx.draw.draw_select_save(
            ctx.screen,
            ctx.fonts,
            session.menu_index,
            state.saves,
            screen_title(state.language, "self_save_1"),
            state.language,
            state=state,
            is_loading=progress,
        )

        if self._preload_done and progress >= 1.0:
            import time
            if not hasattr(self, '_pulse_start'):
                self._pulse_start = time.perf_counter()
            pulse_elapsed = time.perf_counter() - self._pulse_start
            pulse_duration = 0.9
            if pulse_elapsed <= pulse_duration:
                from frontend.components.primitives import draw_lens_pulse
                draw_lens_pulse(ctx.screen, (55, 57), pulse_elapsed / pulse_duration)
            else:
                self._pulse_start = time.perf_counter()


class SelfSelectSaveBScreen(ScreenBase):
    screen_id = "self_select_save_b"

    def __init__(self):
        super().__init__()
        self._preload_thread = None
        self._preload_done = False
        self._preload_progress = 0.0

    def _preload_saves_thread(self, state, ctx):
        """Thread para pré-carregar análise dos saves."""
        try:
            ctx.logger.info("Pre-analyzing saves in background...")
            total = len(state.saves)

            for idx, save_path in enumerate(state.saves):
                try:
                    state.analyze_save(save_path)
                except Exception as exc:
                    ctx.logger.debug("Failed to pre-analyze %s: %s", save_path.name, exc)
                finally:
                    self._preload_progress = (idx + 1) / total if total > 0 else 0

            ctx.logger.info("Pre-analysis complete for save B")
            self._preload_done = True
        except Exception as exc:
            ctx.logger.error("Error during preload: %s", exc)
            self._preload_done = True

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = max(0, session.menu_index - 1)
        elif action == "down":
            session.menu_index = min(max(0, len(state.saves) - 1), session.menu_index + 1)
        elif action == "select" and state.saves:
            candidate = state.saves[session.menu_index]
            if services.same_save_path(session.self_trade_save_a, candidate):
                show_info_modal(
                    session,
                    services,
                    title="Save repetido",
                    message="Escolha dois arquivos de save diferentes para trocar comigo.",
                    return_screen="self_select_save_b",
                    reason="self_same_save_blocked",
                )
            else:
                session.self_trade_save_b = candidate
                ctx.logger.info("Self trade save B selected: %s", session.self_trade_save_b)
                try:
                    services.load_self_trade_party(session.self_trade_save_a)
                    services.switch_screen("self_select_pokemon_a", "self_save_b_selected")
                    session.menu_index = 0
                except Exception as exc:
                    ctx.logger.exception("Failed to load self trade party A: %s", exc)
                    show_info_modal(
                        session,
                        services,
                        title="Falha ao carregar Party",
                        message=str(exc),
                        return_screen="self_select_save_a",
                        reason="self_party_a_failed",
                    )
        elif action == "back":
            session.self_trade_save_b = None
            services.switch_screen("self_select_save_a", "back_from_self_save_b")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        if self._preload_thread is None and state.saves:
            self._preload_thread = threading.Thread(
                target=self._preload_saves_thread,
                args=(state, ctx),
                daemon=True
            )
            self._preload_thread.start()

        progress = 1.0
        if self._preload_thread is not None and not self._preload_done:
            progress = self._preload_progress

        ctx.draw.draw_select_save(
            ctx.screen,
            ctx.fonts,
            session.menu_index,
            state.saves,
            screen_title(state.language, "self_save_2"),
            state.language,
            state=state,
            is_loading=progress,
        )

        if self._preload_done and progress >= 1.0:
            import time
            if not hasattr(self, '_pulse_start'):
                self._pulse_start = time.perf_counter()
            pulse_elapsed = time.perf_counter() - self._pulse_start
            pulse_duration = 0.9
            if pulse_elapsed <= pulse_duration:
                from frontend.components.primitives import draw_lens_pulse
                draw_lens_pulse(ctx.screen, (55, 57), pulse_elapsed / pulse_duration)
            else:
                self._pulse_start = time.perf_counter()
