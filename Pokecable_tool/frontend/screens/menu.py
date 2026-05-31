from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from frontend.i18n import screen_title, t
from frontend.screens.base import ScreenBase, show_info_modal


class MenuScreen(ScreenBase):
    screen_id = "menu"

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = (session.menu_index - 1) % 7
        elif action == "down":
            session.menu_index = (session.menu_index + 1) % 7
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
                ctx.logger.info("Menu select: extras")
                services.reset_flow_state(state)
                state.find_saves()
                services.switch_screen("extras_select_save", "menu_extras")
                session.menu_index = 0
            elif session.menu_index == 6:
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
            session.menu_index = 0
        elif action == "down":
            session.menu_index = 0
        elif action in ("left", "right"):
            order = ["pt", "en", "es"]
            index = order.index(state.language) if state.language in order else 0
            direction = -1 if action == "left" else 1
            state.language = order[(index + direction) % len(order)]
            state.theme = "pokedex_red"
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


class UpdateScreen(ScreenBase):
    screen_id = "update_check"

    def __init__(self):
        super().__init__()
        self._check_thread = None
        self._apply_thread = None
        self._check_started = False

    def _background_check(self, session, ctx):
        from r36s_pokecable_core import check_for_update
        try:
            # Executa verificação
            result = check_for_update()

            # Atualiza estado baseado no resultado
            if result.get("error"):
                session.update_status = "error"
                session.update_data = result
            elif result.get("up_to_date"):
                session.update_status = "up_to_date"
                session.update_data = result
            else:
                session.update_status = "available"
                session.update_data = result

        except Exception as e:
            session.update_status = "error"
            session.update_data = {"error": str(e)[:100]}

    def _background_apply(self, session, ctx):
        from r36s_pokecable_core import apply_update
        try:
            result = apply_update(session.update_data.get("zipball_url") if isinstance(session.update_data, dict) else None)
            if result.get("success"):
                session.update_status = "done"
            else:
                ctx.logger.error(f"Update failed: {result.get('message')}")
                session.update_status = "error"
            session.update_data = result
        except Exception as e:
            ctx.logger.error(f"Update error: {e}")
            import traceback
            ctx.logger.error(f"Traceback:\n{traceback.format_exc()}")
            session.update_status = "error"
            session.update_data = {"error": str(e)[:100]}

    def handle_action(self, action, ctx, session, state, services):
        if action == "back":
            session.update_status = ""
            session.update_data = {}
            self._check_started = False
            services.go_back("menu", "back_from_update")
            session.menu_index = 4

        elif action == "select" and session.update_status == "available":
            session.update_status = "updating"
            self._apply_thread = threading.Thread(
                target=self._background_apply,
                args=(session, ctx),
                daemon=True,
            )
            self._apply_thread.start()

        elif action == "select" and session.update_status == "done":
            session.update_status = ""
            session.update_data = {}
            self._check_started = False
            session.running = False

    def render(self, ctx, session, state, services):
        # Iniciar verificação na primeira renderização
        if not self._check_started and not session.update_status:
            self._check_started = True
            session.update_status = "checking"
            session.update_data = {}
            self._check_thread = threading.Thread(
                target=self._background_check,
                args=(session, ctx),
                daemon=True,
            )
            self._check_thread.start()

        ctx.draw.draw_update_screen(ctx.screen, ctx.fonts, session.update_status, session.update_data, state.language)


class ExtrasSelectSaveScreen(ScreenBase):
    screen_id = "extras_select_save"

    def __init__(self):
        super().__init__()
        self._preload_thread = None
        self._preload_done = False
        self._preload_progress = 0.0

    def _preload_saves_thread(self, state, ctx):
        """Pré-carrega saves em background (análise rápida)."""
        try:
            ctx.logger.info("Pre-analyzing saves for Extras...")
            total = len(state.saves)

            if not state.saves:
                self._preload_done = True
                return

            # Analisar todos os saves em paralelo
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(state.analyze_save, save): idx for idx, save in enumerate(state.saves)}
                completed = 0

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        save_idx = futures[future]
                        ctx.logger.debug("Failed to pre-analyze %s: %s", state.saves[save_idx].name, exc)
                    finally:
                        completed += 1
                        self._preload_progress = completed / total if total > 0 else 0

            ctx.logger.info("Pre-analysis complete for Extras")
            self._preload_done = True
        except Exception as exc:
            ctx.logger.error("Error during Extras preload: %s", exc)
            self._preload_done = True

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = max(0, session.menu_index - 1)
        elif action == "down":
            max_idx = len(state.saves) - 1 if state.saves else 0
            session.menu_index = min(max_idx, session.menu_index + 1)
        elif action == "select":
            if state.saves and 0 <= session.menu_index < len(state.saves):
                save_path = state.saves[session.menu_index]
                session.extras_save_path = save_path
                session.menu_index = 0
                services.switch_screen("extras_category", "extras_select_save")
        elif action == "back":
            services.go_back("menu", "back_from_extras")
            session.menu_index = 5

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

        if session.menu_index >= len(state.saves):
            session.menu_index = max(0, len(state.saves) - 1)

        ctx.draw.draw_select_save(
            ctx.screen,
            ctx.fonts,
            session.menu_index,
            state.saves,
            title=screen_title(state.language, "extras_select_save"),
            language=state.language,
            state=state,
            is_loading=progress
        )


class ExtrasCategoryScreen(ScreenBase):
    screen_id = "extras_category"

    def __init__(self):
        super().__init__()
        self._categories = []
        self._load_thread = None
        self._load_started = False
        self._error_message = None
        self._last_loaded_save_path = None

    def handle_action(self, action, ctx, session, state, services):
        if self._error_message:
            if action in ("select", "back"):
                services.go_back("extras_select_save", "back_from_category")
                session.menu_index = 0
            return

        if not self._categories:
            if action == "back":
                services.go_back("extras_select_save", "back_from_category")
                session.menu_index = 0
            return

        if action == "up":
            session.menu_index = (session.menu_index - 1) % len(self._categories)
        elif action == "down":
            session.menu_index = (session.menu_index + 1) % len(self._categories)
        elif action == "select":
            if self._categories and session.menu_index < len(self._categories):
                category = self._categories[session.menu_index]
                session.extras_category = category
                if category == "ereader":
                    services.switch_screen("extras_ereader", "extras_category")
                elif category == "utilities":
                    services.switch_screen("extras_utilities", "extras_category")
                elif category == "additem":
                    session.extras_item_bucket_index = 0
                    services.switch_screen("extras_item_category", "extras_category")
                else:
                    services.switch_screen("extras_events", "extras_category")
                session.menu_index = 0
        elif action == "back":
            services.go_back("extras_select_save", "back_from_category")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        # Reset if save path changed
        if session.extras_save_path != self._last_loaded_save_path:
            self._load_started = False
            self._categories = []
            self._error_message = None
            self._last_loaded_save_path = session.extras_save_path

        if not self._load_started:
            self._load_started = True
            self._load_thread = threading.Thread(
                target=self._load_events_bg,
                args=(session, state),
                daemon=True,
            )
            self._load_thread.start()

        ctx.draw.draw_extras_category(ctx.screen, ctx.fonts, self._categories, session.menu_index, state.language, self._error_message)

    def _load_events_bg(self, session, state):
        from r36s_pokecable_core import (
            get_applied_events,
            get_applied_utilities,
            get_available_events,
            get_available_utilities,
            get_consumable_item_groups,
        )

        save_path = session.extras_save_path
        events_result = get_available_events(save_path)
        utilities_result = get_available_utilities(save_path)

        if events_result.get("success") or utilities_result.get("success"):
            events = events_result.get("events", []) if events_result.get("success") else []
            utilities = utilities_result.get("utilities", []) if utilities_result.get("success") else []
            has_ticket = any(e["category"] == "ticket" for e in events)
            has_ereader = any(e["category"] == "ereader" for e in events)
            self._categories = []
            if has_ticket:
                self._categories.append("tickets")
            if has_ereader:
                self._categories.append("ereader")
            if utilities:
                self._categories.append("utilities")
            # Adicionar item consumível está sempre disponível (qualquer save com mochila).
            item_groups_result = get_consumable_item_groups(save_path)
            item_groups = item_groups_result.get("groups", []) if item_groups_result.get("success") else []
            if item_groups:
                self._categories.append("additem")
                session.extras_item_groups = item_groups
                session.extras_item_max_stack = item_groups_result.get("max_stack", 99)
            session.extras_events = events
            session.extras_utilities = utilities

            if events_result.get("success"):
                applied_result = get_applied_events(save_path)
                session.extras_applied_ids = applied_result.get("applied", set())
            else:
                session.extras_applied_ids = set()

            if utilities:
                applied_utils = get_applied_utilities(save_path)
                session.extras_utilities_active = applied_utils.get("active", set())
                session.extras_utilities_reversible = applied_utils.get("reversible", set())
            else:
                session.extras_utilities_active = set()
                session.extras_utilities_reversible = set()

            self._error_message = None
        else:
            self._error_message = t(state.language, "extras_load_error")


class ExtrasEventsScreen(ScreenBase):
    screen_id = "extras_events"

    def handle_action(self, action, ctx, session, state, services):
        events = [e for e in session.extras_events if e["category"] == "ticket"]
        if action == "up":
            session.extras_event_index = (session.extras_event_index - 1) % len(events)
        elif action == "down":
            session.extras_event_index = (session.extras_event_index + 1) % len(events)
        elif action == "select":
            if events and session.extras_event_index < len(events):
                from r36s_pokecable_core import (
                    apply_event_to_save,
                    get_applied_events,
                    remove_event_from_save,
                )

                event = events[session.extras_event_index]
                if event["id"] in session.extras_applied_ids:
                    result = remove_event_from_save(session.extras_save_path, event["id"])
                else:
                    result = apply_event_to_save(session.extras_save_path, event["id"])
                session.extras_result = result

                # Atualiza o estado aplicado para refletir o toggle ao voltar.
                applied_result = get_applied_events(session.extras_save_path)
                if applied_result.get("success"):
                    session.extras_applied_ids = applied_result.get("applied", set())

                services.switch_screen("extras_result", "extras_apply")
        elif action == "back":
            services.go_back("extras_category", "back_from_events")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        events = [e for e in session.extras_events if e["category"] == "ticket"]
        # Ensure index is valid if event list changed
        if session.extras_event_index >= len(events):
            session.extras_event_index = max(0, len(events) - 1)
        ctx.draw.draw_extras_events(ctx.screen, ctx.fonts, events, session.extras_event_index, state.language, applied_ids=session.extras_applied_ids)


class ExtrasUtilitiesScreen(ScreenBase):
    screen_id = "extras_utilities"

    def handle_action(self, action, ctx, session, state, services):
        utilities = list(session.extras_utilities or [])
        if action == "up" and utilities:
            session.extras_utility_index = (session.extras_utility_index - 1) % len(utilities)
        elif action == "down" and utilities:
            session.extras_utility_index = (session.extras_utility_index + 1) % len(utilities)
        elif action == "select":
            if utilities and session.extras_utility_index < len(utilities):
                from r36s_pokecable_core import (
                    apply_utility_to_save,
                    get_applied_utilities,
                    remove_utility_from_save,
                )

                utility = utilities[session.extras_utility_index]
                if utility["id"] in session.extras_utilities_active:
                    result = remove_utility_from_save(session.extras_save_path, utility["id"])
                else:
                    result = apply_utility_to_save(session.extras_save_path, utility["id"])
                session.extras_result = result

                # Atualiza o estado dos utilitários reversíveis para refletir o toggle.
                applied_utils = get_applied_utilities(session.extras_save_path)
                if applied_utils.get("success"):
                    session.extras_utilities_active = applied_utils.get("active", set())
                    session.extras_utilities_reversible = applied_utils.get("reversible", set())

                services.switch_screen("extras_result", "extras_apply")
        elif action == "back":
            services.go_back("extras_category", "back_from_utilities")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        utilities = list(session.extras_utilities or [])
        if session.extras_utility_index >= len(utilities):
            session.extras_utility_index = max(0, len(utilities) - 1)
        ctx.draw.draw_extras_utilities(
            ctx.screen,
            ctx.fonts,
            utilities,
            session.extras_utility_index,
            state.language,
            active_ids=session.extras_utilities_active,
            reversible_ids=session.extras_utilities_reversible,
        )


class ExtrasEreaderScreen(ScreenBase):
    screen_id = "extras_ereader"

    def __init__(self):
        super().__init__()
        self._slots_load_thread = None
        self._slots_load_started = False
        self._last_loaded_save_path = None

    def handle_action(self, action, ctx, session, state, services):
        from pokecable_runtime.events.ereader_battles import list_ereader_battles

        battles = list_ereader_battles()
        if action == "up":
            session.extras_ereader_index = (session.extras_ereader_index - 1) % len(battles)
        elif action == "down":
            session.extras_ereader_index = (session.extras_ereader_index + 1) % len(battles)
        elif action == "left" and session.extras_ereader_slots:
            session.extras_ereader_slot_index = (session.extras_ereader_slot_index - 1) % len(session.extras_ereader_slots)
        elif action == "right" and session.extras_ereader_slots:
            session.extras_ereader_slot_index = (session.extras_ereader_slot_index + 1) % len(session.extras_ereader_slots)
        elif action == "select":
            from r36s_pokecable_core import apply_ereader_to_save, remove_ereader_from_save

            if battles and session.extras_ereader_index < len(battles):
                battle = battles[session.extras_ereader_index]
                existing_slot = None
                for slot_info in (session.extras_ereader_slots or []):
                    if slot_info.get("battle_id") == battle["id"]:
                        existing_slot = int(slot_info["slot"])
                        break
                if existing_slot is not None:
                    result = remove_ereader_from_save(session.extras_save_path, existing_slot)
                else:
                    target_slot = session.extras_ereader_slot_index if session.extras_ereader_slots else 0
                    result = apply_ereader_to_save(session.extras_save_path, target_slot, battle["id"])
                session.extras_result = result
                # Recarrega os slots para refletir o toggle ao voltar.
                self._slots_load_started = False
                services.switch_screen("extras_result", "extras_apply")
        elif action == "back":
            services.go_back("extras_category", "back_from_ereader")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        from pokecable_runtime.events.ereader_battles import list_ereader_battles

        # Reset if save path changed
        if session.extras_save_path != self._last_loaded_save_path:
            self._slots_load_started = False
            self._last_loaded_save_path = session.extras_save_path

        if not self._slots_load_started:
            self._slots_load_started = True
            self._slots_load_thread = threading.Thread(
                target=self._load_slots_bg,
                args=(session,),
                daemon=True,
            )
            self._slots_load_thread.start()

        battles = list_ereader_battles()
        if session.extras_ereader_slots and session.extras_ereader_slot_index >= len(session.extras_ereader_slots):
            session.extras_ereader_slot_index = max(0, len(session.extras_ereader_slots) - 1)
        ctx.draw.draw_extras_ereader(
            ctx.screen,
            ctx.fonts,
            session.extras_ereader_slots,
            battles,
            session.extras_ereader_index,
            state.language,
            selected_slot=session.extras_ereader_slot_index,
        )

    def _load_slots_bg(self, session):
        from r36s_pokecable_core import get_ereader_slots

        slots_result = get_ereader_slots(session.extras_save_path)
        if slots_result.get("success"):
            session.extras_ereader_slots = slots_result.get("slots", [])
            for idx, slot in enumerate(session.extras_ereader_slots):
                if slot.get("is_empty"):
                    session.extras_ereader_slot_index = idx
                    break


class ExtrasResultScreen(ScreenBase):
    screen_id = "extras_result"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select" or action == "back":
            if session.extras_category == "ereader":
                services.go_back("extras_ereader", "back_from_result")
            elif session.extras_category == "utilities":
                services.go_back("extras_utilities", "back_from_result")
            elif session.extras_category == "additem":
                services.go_back("extras_item_select", "back_from_result")
            else:
                services.go_back("extras_events", "back_from_result")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        ctx.draw.draw_extras_result(ctx.screen, ctx.fonts, session.extras_result, state.language)


class ExtrasItemCategoryScreen(ScreenBase):
    screen_id = "extras_item_category"

    def handle_action(self, action, ctx, session, state, services):
        groups = session.extras_item_groups or []
        if not groups:
            if action == "back":
                services.go_back("extras_category", "back_from_item_category")
                session.menu_index = 0
            return
        if action == "up":
            session.extras_item_bucket_index = (session.extras_item_bucket_index - 1) % len(groups)
        elif action == "down":
            session.extras_item_bucket_index = (session.extras_item_bucket_index + 1) % len(groups)
        elif action == "select":
            session.extras_item_index = 0
            session.extras_item_qty = 1
            services.switch_screen("extras_item_select", "extras_item_category")
        elif action == "back":
            services.go_back("extras_category", "back_from_item_category")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        groups = session.extras_item_groups or []
        if session.extras_item_bucket_index >= len(groups):
            session.extras_item_bucket_index = max(0, len(groups) - 1)
        ctx.draw.draw_extras_item_category(
            ctx.screen, ctx.fonts, groups, session.extras_item_bucket_index, state.language
        )


class ExtrasItemSelectScreen(ScreenBase):
    screen_id = "extras_item_select"

    def _items(self, session):
        groups = session.extras_item_groups or []
        if 0 <= session.extras_item_bucket_index < len(groups):
            return groups[session.extras_item_bucket_index][1]
        return []

    def handle_action(self, action, ctx, session, state, services):
        items = self._items(session)
        max_stack = max(1, int(session.extras_item_max_stack or 99))
        if not items:
            if action == "back":
                services.go_back("extras_item_category", "back_from_item_select")
            return
        if action == "up":
            session.extras_item_index = (session.extras_item_index - 1) % len(items)
        elif action == "down":
            session.extras_item_index = (session.extras_item_index + 1) % len(items)
        elif action == "left":
            session.extras_item_qty = max_stack if session.extras_item_qty <= 1 else session.extras_item_qty - 1
        elif action == "right":
            session.extras_item_qty = 1 if session.extras_item_qty >= max_stack else session.extras_item_qty + 1
        elif action == "select":
            from r36s_pokecable_core import add_item_to_save

            item_id = items[session.extras_item_index][0]
            qty = max(1, min(int(session.extras_item_qty), max_stack))
            session.extras_result = add_item_to_save(session.extras_save_path, item_id, qty)
            services.switch_screen("extras_result", "extras_item_add")
        elif action == "back":
            services.go_back("extras_item_category", "back_from_item_select")

    def render(self, ctx, session, state, services):
        items = self._items(session)
        if session.extras_item_index >= len(items):
            session.extras_item_index = max(0, len(items) - 1)
        ctx.draw.draw_extras_item_select(
            ctx.screen,
            ctx.fonts,
            items,
            session.extras_item_index,
            session.extras_item_qty,
            state.language,
        )
