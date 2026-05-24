from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from frontend.i18n import screen_title
from frontend.screens.base import ScreenBase, show_info_modal


class MenuScreen(ScreenBase):
    screen_id = "menu"

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = (session.menu_index - 1) % 6
        elif action == "down":
            session.menu_index = (session.menu_index + 1) % 6
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
                ctx.logger.info("Menu select: infos")
                services.switch_screen("infos_topics", "menu_infos")
                session.menu_index = 0
            elif session.menu_index == 4:
                ctx.logger.info("Menu select: check for update")
                services.switch_screen("update_check", "menu_update")
                session.menu_index = 0
            elif session.menu_index == 5:
                ctx.logger.info("Menu select: exit")
                session.running = False
        elif action == "back":
            ctx.logger.info("Menu back: exit")
            session.running = False

    def render(self, ctx, session, state, services):
        ctx.draw.draw_menu(ctx.screen, ctx.fonts, session.menu_index, state.language)


class InfosTopicsScreen(ScreenBase):
    screen_id = "infos_topics"

    def handle_action(self, action, ctx, session, state, services):
        from frontend.infos_content import get_topics
        topics = get_topics(state.language)
        if action == "up":
            session.menu_index = (session.menu_index - 1) % len(topics)
        elif action == "down":
            session.menu_index = (session.menu_index + 1) % len(topics)
        elif action == "select":
            topic_key = topics[session.menu_index][0]
            session.infos_topic_key = topic_key
            session.infos_scroll = 0
            services.switch_screen("infos_reader", f"infos_open:{topic_key}")
        elif action == "back":
            services.go_back("menu", "back_from_infos")
            session.menu_index = 3  # back to "Infos" item

    def render(self, ctx, session, state, services):
        ctx.draw.draw_infos_topics(ctx.screen, ctx.fonts, session.menu_index, state.language)


class InfosReaderScreen(ScreenBase):
    screen_id = "infos_reader"
    SCROLL_STEP = 18  # px per up/down press

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.infos_scroll = max(0, getattr(session, "infos_scroll", 0) - self.SCROLL_STEP)
        elif action == "down":
            session.infos_scroll = getattr(session, "infos_scroll", 0) + self.SCROLL_STEP
        elif action == "back":
            services.go_back("infos_topics", "back_to_infos_topics")

    def render(self, ctx, session, state, services):
        topic_key = getattr(session, "infos_topic_key", "retrocompat") or "retrocompat"
        scroll = getattr(session, "infos_scroll", 0)
        # Clamp scroll on render so we never go past the content's actual height
        max_scroll = ctx.draw.draw_infos_reader(
            ctx.screen, ctx.fonts, topic_key, scroll, state.language
        )
        if scroll > max_scroll:
            session.infos_scroll = max_scroll


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
            services.go_back("menu", "back_from_config")

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
        self._session_menu_index = 0

    def _preload_saves_thread(self, state, ctx):
        """Thread para pré-carregar análise dos saves em paralelo."""
        try:
            ctx.logger.info("Pre-analyzing saves in background (parallel)...")
            total = len(state.saves)

            if not state.saves:
                self._preload_done = True
                return

            # Priorizar o save selecionado
            selected_idx = self._session_menu_index
            selected_save = state.saves[selected_idx] if selected_idx < len(state.saves) else None
            other_saves = state.saves[:selected_idx] + state.saves[selected_idx + 1:]

            # Analisar o save selecionado primeiro
            if selected_save:
                try:
                    state.analyze_save(selected_save)
                    self._preload_progress = 1 / total if total > 0 else 0
                except Exception as exc:
                    ctx.logger.debug("Failed to pre-analyze %s: %s", selected_save.name, exc)

            # Analisar os outros saves em paralelo
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(state.analyze_save, save): idx for idx, save in enumerate(other_saves)}
                completed = 1

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        save_idx = futures[future]
                        ctx.logger.debug("Failed to pre-analyze %s: %s", other_saves[save_idx].name, exc)
                    finally:
                        completed += 1
                        self._preload_progress = completed / total if total > 0 else 0

            self._valid_saves = []
            for save_path in state.saves:
                try:
                    key = str(save_path.resolve())
                    analysis = state.save_analysis.get(key)
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
            services.go_back("menu", "back_from_load_save")

    def render(self, ctx, session, state, services):
        if self._preload_thread is None and state.saves:
            self._session_menu_index = session.menu_index
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
                draw_lens_pulse(ctx.screen, (49, 47), pulse_elapsed / pulse_duration)


class SelfSelectSaveAScreen(ScreenBase):
    screen_id = "self_select_save_a"

    def __init__(self):
        super().__init__()
        self._preload_thread = None
        self._preload_done = False
        self._preload_progress = 0.0
        self._session_menu_index = 0

    def _preload_saves_thread(self, state, ctx):
        """Thread para pré-carregar análise dos saves em paralelo."""
        try:
            ctx.logger.info("Pre-analyzing saves in background (parallel)...")
            total = len(state.saves)

            if not state.saves:
                self._preload_done = True
                return

            # Priorizar o save selecionado
            selected_idx = self._session_menu_index
            selected_save = state.saves[selected_idx] if selected_idx < len(state.saves) else None
            other_saves = state.saves[:selected_idx] + state.saves[selected_idx + 1:]

            # Analisar o save selecionado primeiro
            if selected_save:
                try:
                    state.analyze_save(selected_save)
                    self._preload_progress = 1 / total if total > 0 else 0
                except Exception as exc:
                    ctx.logger.debug("Failed to pre-analyze %s: %s", selected_save.name, exc)

            # Analisar os outros saves em paralelo
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(state.analyze_save, save): idx for idx, save in enumerate(other_saves)}
                completed = 1

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        save_idx = futures[future]
                        ctx.logger.debug("Failed to pre-analyze %s: %s", other_saves[save_idx].name, exc)
                    finally:
                        completed += 1
                        self._preload_progress = completed / total if total > 0 else 0

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
            services.go_back("menu", "back_from_self_save_a")

    def render(self, ctx, session, state, services):
        if self._preload_thread is None and state.saves:
            self._session_menu_index = session.menu_index
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
                draw_lens_pulse(ctx.screen, (49, 47), pulse_elapsed / pulse_duration)
            else:
                self._pulse_start = time.perf_counter()


class SelfSelectSaveBScreen(ScreenBase):
    screen_id = "self_select_save_b"

    def __init__(self):
        super().__init__()
        self._preload_thread = None
        self._preload_done = False
        self._preload_progress = 0.0
        self._session_menu_index = 0

    def _preload_saves_thread(self, state, ctx):
        """Thread para pré-carregar análise dos saves em paralelo."""
        try:
            ctx.logger.info("Pre-analyzing saves in background (parallel)...")
            total = len(state.saves)

            if not state.saves:
                self._preload_done = True
                return

            # Priorizar o save selecionado
            selected_idx = self._session_menu_index
            selected_save = state.saves[selected_idx] if selected_idx < len(state.saves) else None
            other_saves = state.saves[:selected_idx] + state.saves[selected_idx + 1:]

            # Analisar o save selecionado primeiro
            if selected_save:
                try:
                    state.analyze_save(selected_save)
                    self._preload_progress = 1 / total if total > 0 else 0
                except Exception as exc:
                    ctx.logger.debug("Failed to pre-analyze %s: %s", selected_save.name, exc)

            # Analisar os outros saves em paralelo
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(state.analyze_save, save): idx for idx, save in enumerate(other_saves)}
                completed = 1

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        save_idx = futures[future]
                        ctx.logger.debug("Failed to pre-analyze %s: %s", other_saves[save_idx].name, exc)
                    finally:
                        completed += 1
                        self._preload_progress = completed / total if total > 0 else 0

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
            services.go_back("self_select_save_a", "back_from_self_save_b")

    def render(self, ctx, session, state, services):
        if self._preload_thread is None and state.saves:
            self._session_menu_index = session.menu_index
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
                draw_lens_pulse(ctx.screen, (49, 47), pulse_elapsed / pulse_duration)
            else:
                self._pulse_start = time.perf_counter()


class UpdateScreen(ScreenBase):
    screen_id = "update_check"

    def __init__(self):
        super().__init__()
        self._check_thread = None
        self._apply_thread = None

    def on_enter(self, ctx, session, state, services):
        ctx.logger.info("=" * 80)
        ctx.logger.info("UI SCREEN: UpdateScreen entered")
        ctx.logger.info(f"UI SCREEN: current update_status: '{session.update_status}'")

        if not session.update_status or session.update_status == "":
            ctx.logger.info("UI SCREEN: iniciando verificação de atualização em background")
            session.update_status = "checking"
            session.update_data = {}
            self._check_thread = threading.Thread(
                target=self._background_check,
                args=(session, ctx),
                daemon=True,
            )
            ctx.logger.debug("UI SCREEN: thread criada")
            self._check_thread.start()
            ctx.logger.info("UI SCREEN: thread iniciada")
        else:
            ctx.logger.info(f"UI SCREEN: reutilizando status anterior: {session.update_status}")

    def _background_check(self, session, ctx):
        from r36s_pokecable_core import check_for_update
        try:
            ctx.logger.info("UI BACKGROUND: iniciando check_for_update()")
            result = check_for_update()

            ctx.logger.info(f"UI BACKGROUND: resultado recebido:")
            ctx.logger.info(f"  - current: {result.get('current')}")
            ctx.logger.info(f"  - latest: {result.get('latest')}")
            ctx.logger.info(f"  - up_to_date: {result.get('up_to_date')}")
            ctx.logger.info(f"  - error: {result.get('error')}")

            if result.get("error"):
                ctx.logger.warning(f"UI BACKGROUND: erro na verificação: {result.get('error')}")
                session.update_status = "error"
                session.update_data = result
            elif result.get("up_to_date"):
                ctx.logger.info("UI BACKGROUND: sistema está atualizado")
                session.update_status = "up_to_date"
                session.update_data = result
            else:
                ctx.logger.info(f"UI BACKGROUND: nova versão disponível: {result.get('latest')}")
                session.update_status = "available"
                session.update_data = result

            ctx.logger.info(f"UI BACKGROUND: estado alterado para '{session.update_status}'")

        except Exception as e:
            ctx.logger.error(f"UI BACKGROUND: exceção não capturada: {e}")
            import traceback
            ctx.logger.error(f"UI BACKGROUND: traceback:\n{traceback.format_exc()}")
            session.update_status = "error"
            session.update_data = {"error": str(e)[:100]}

    def _background_apply(self, session, ctx):
        from r36s_pokecable_core import apply_update
        try:
            ctx.logger.info("UI BACKGROUND: iniciando apply_update()")
            result = apply_update()

            ctx.logger.info(f"UI BACKGROUND: resultado do update:")
            ctx.logger.info(f"  - success: {result.get('success')}")
            ctx.logger.info(f"  - message: {result.get('message')}")

            if result.get("success"):
                ctx.logger.info("UI BACKGROUND: update aplicado com sucesso")
                session.update_status = "done"
            else:
                ctx.logger.error(f"UI BACKGROUND: falha no update: {result.get('message')}")
                session.update_status = "error"

            session.update_data = result
            ctx.logger.info(f"UI BACKGROUND: estado alterado para '{session.update_status}'")

        except Exception as e:
            ctx.logger.error(f"UI BACKGROUND: exceção não capturada: {e}")
            import traceback
            ctx.logger.error(f"UI BACKGROUND: traceback:\n{traceback.format_exc()}")
            session.update_status = "error"
            session.update_data = {"error": str(e)[:100]}

    def handle_action(self, action, ctx, session, state, services):
        if action == "back":
            ctx.logger.info("UI ACTION: usuário pressionou BACK")
            ctx.logger.info(f"UI ACTION: retornando ao menu (update_status era: {session.update_status})")
            session.update_status = ""
            session.update_data = {}
            services.go_back("menu", "back_from_update")
            session.menu_index = 4
            ctx.logger.info("=" * 80)

        elif action == "select" and session.update_status == "available":
            ctx.logger.info("UI ACTION: usuário pressionou A (confirmar update)")
            ctx.logger.info("UI ACTION: iniciando aplicação de atualização em background")
            session.update_status = "updating"
            self._apply_thread = threading.Thread(
                target=self._background_apply,
                args=(session, ctx),
                daemon=True,
            )
            ctx.logger.debug("UI ACTION: thread criada")
            self._apply_thread.start()
            ctx.logger.info("UI ACTION: thread iniciada")

        elif action == "select":
            ctx.logger.debug(f"UI ACTION: select pressionado, mas update_status é '{session.update_status}' (ignorado)")

    def render(self, ctx, session, state, services):
        ctx.draw.draw_update_screen(ctx.screen, ctx.fonts, session.update_status, session.update_data, state.language)
