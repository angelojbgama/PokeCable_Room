from __future__ import annotations

from pathlib import Path

from pokecable_save import SaveError
from frontend.i18n import t
from frontend.screens.base import ScreenBase, show_info_modal


class SelfSelectPokemonAScreen(ScreenBase):
    screen_id = "self_select_pokemon_a"

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = max(0, session.menu_index - 1)
        elif action == "down":
            session.menu_index = min(max(0, len(state.pokemon_list) - 1), session.menu_index + 1)
        elif action == "select" and state.pokemon_list:
            if state.pokemon_source != "party":
                show_info_modal(
                    session,
                    services,
                    title="Pokemon esta no PC",
                    message="Pressione X para retirar este Pokemon para a Party antes de troca-lo.",
                    return_screen="self_select_pokemon_a",
                    reason="self_select_a_from_pc_blocked",
                )
            else:
                session.self_trade_pokemon_a = state.pokemon_list[session.menu_index]
                ctx.logger.info("Self trade pokemon A selected: %s", session.self_trade_pokemon_a.get("location"))
                try:
                    services.load_self_trade_party(session.self_trade_save_b)
                    services.switch_screen("self_select_pokemon_b", "self_pokemon_a_selected")
                    session.menu_index = 0
                except Exception as exc:
                    ctx.logger.exception("Failed to load self trade party B: %s", exc)
                    show_info_modal(
                        session,
                        services,
                        title="Falha ao carregar Party",
                        message=str(exc),
                        return_screen="self_select_save_b",
                        reason="self_party_b_failed",
                    )
        elif action == "x" and state.pokemon_list:
            if state.trade_phase not in ("idle", "waiting"):
                session.trade_status = "Aguarde a troca terminar antes de mover."
            elif state.pokemon_source == "party":
                state.selected_save = Path(session.self_trade_save_a)
                session.pending_deposit_idx = session.menu_index
                session.pending_pc_return_screen = "self_select_pokemon_a"
                ctx.logger.info("Self trade deposit requested for save A party slot %s", session.pending_deposit_idx)
                services.switch_screen("deposit_confirm", "self_deposit_a_request")
            else:
                state.selected_save = Path(session.self_trade_save_a)
                session.pending_withdraw_pokemon = state.pokemon_list[session.menu_index]
                session.pending_pc_return_screen = "self_select_pokemon_a"
                ctx.logger.info(
                    "Self trade withdraw requested for save A %s",
                    session.pending_withdraw_pokemon.get("location"),
                )
                services.switch_screen("withdraw_confirm", "self_withdraw_a_request")
        elif action == "y":
            new_source = "boxes" if state.pokemon_source == "party" else "party"
            try:
                services.load_self_trade_source(session.self_trade_save_a, new_source)
                session.menu_index = 0
                ctx.logger.info(
                    "Self trade save A toggled source -> %s (%s entries)",
                    new_source,
                    len(state.pokemon_list),
                )
            except SaveError as exc:
                ctx.logger.error("Self trade save A source toggle failed: %s", exc)
                show_info_modal(
                    session,
                    services,
                    title="Erro",
                    message=str(exc),
                    return_screen="self_select_pokemon_a",
                    reason="self_source_a_toggle_failed",
                )
        elif action == "back":
            session.self_trade_pokemon_a = None
            services.switch_screen("self_select_save_b", "back_from_self_pokemon_a", nav_mode="replace")
            if session.self_trade_save_b in state.saves:
                session.menu_index = state.saves.index(session.self_trade_save_b)
            else:
                session.menu_index = 0

    def render(self, ctx, session, state, services):
        label = services.self_trade_source_label(1, session.self_trade_save_a)
        ctx.draw.draw_select_pokemon(
            ctx.screen,
            ctx.fonts,
            session.menu_index,
            state.pokemon_list,
            label,
            ctx.sprite_loader,
            session.trade_status,
            True,
            state.language,
        )


class SelfSelectPokemonBScreen(ScreenBase):
    screen_id = "self_select_pokemon_b"

    def handle_action(self, action, ctx, session, state, services):
        if action == "up":
            session.menu_index = max(0, session.menu_index - 1)
        elif action == "down":
            session.menu_index = min(max(0, len(state.pokemon_list) - 1), session.menu_index + 1)
        elif action == "select" and state.pokemon_list:
            if state.pokemon_source != "party":
                show_info_modal(
                    session,
                    services,
                    title="Pokemon esta no PC",
                    message="Pressione X para retirar este Pokemon para a Party antes de troca-lo.",
                    return_screen="self_select_pokemon_b",
                    reason="self_select_b_from_pc_blocked",
                )
            else:
                session.self_trade_pokemon_b = state.pokemon_list[session.menu_index]
                ctx.logger.info("Self trade pokemon B selected: %s", session.self_trade_pokemon_b.get("location"))
                try:
                    preview = services.validate_self_trade_candidate(
                        state,
                        source_save_path=Path(session.self_trade_save_b),
                        source_pokemon_location=str(session.self_trade_pokemon_b.get("location") or "party:0"),
                        target_save_path=Path(session.self_trade_save_a),
                    )
                except Exception as exc:
                    ctx.logger.exception("Self trade candidate validation failed: %s", exc)
                    show_info_modal(
                        session,
                        services,
                        title="Falha na validacao",
                        message=str(exc),
                        return_screen="self_select_pokemon_b",
                        reason="self_candidate_validation_failed",
                    )
                    return
                if not preview.get("compatible"):
                    show_info_modal(
                        session,
                        services,
                        title="Pokemon incompativel",
                        message=str(preview.get("blocking_message") or "Pokemon incompativel com o save de destino."),
                        return_screen="self_select_pokemon_b",
                        reason="self_candidate_incompatible",
                    )
                    return
                session.self_trade_return_context = services.capture_selection_context(
                    "self_select_pokemon_b",
                    save_path=session.self_trade_save_b,
                    source=state.pokemon_source,
                    selected_location=session.self_trade_pokemon_b.get("location"),
                    selected_index=session.menu_index,
                    enrich=False,
                )
                session.trade_status = "Validando troca local..."
                services.switch_screen("trading", "self_trade_preflight")
                try:
                    session.self_trade_context = services.prepare_self_trade(
                        state,
                        session.self_trade_save_a,
                        str(session.self_trade_pokemon_a.get("location") or "party:0"),
                        session.self_trade_save_b,
                        str(session.self_trade_pokemon_b.get("location") or "party:0"),
                    )
                    services.advance_self_trade_prompts()
                except Exception as exc:
                    ctx.logger.exception("Self trade preflight failed: %s", exc)
                    show_info_modal(
                        session,
                        services,
                        title="Troca incompativel",
                        message=str(exc),
                        return_screen="self_select_pokemon_b",
                        reason="self_preflight_failed",
                    )
        elif action == "x" and state.pokemon_list:
            if state.trade_phase not in ("idle", "waiting"):
                session.trade_status = "Aguarde a troca terminar antes de mover."
            elif state.pokemon_source == "party":
                state.selected_save = Path(session.self_trade_save_b)
                session.pending_deposit_idx = session.menu_index
                session.pending_pc_return_screen = "self_select_pokemon_b"
                ctx.logger.info("Self trade deposit requested for save B party slot %s", session.pending_deposit_idx)
                services.switch_screen("deposit_confirm", "self_deposit_b_request")
            else:
                state.selected_save = Path(session.self_trade_save_b)
                session.pending_withdraw_pokemon = state.pokemon_list[session.menu_index]
                session.pending_pc_return_screen = "self_select_pokemon_b"
                ctx.logger.info(
                    "Self trade withdraw requested for save B %s",
                    session.pending_withdraw_pokemon.get("location"),
                )
                services.switch_screen("withdraw_confirm", "self_withdraw_b_request")
        elif action == "y":
            new_source = "boxes" if state.pokemon_source == "party" else "party"
            try:
                services.load_self_trade_source(session.self_trade_save_b, new_source)
                session.menu_index = 0
                ctx.logger.info(
                    "Self trade save B toggled source -> %s (%s entries)",
                    new_source,
                    len(state.pokemon_list),
                )
            except SaveError as exc:
                ctx.logger.error("Self trade save B source toggle failed: %s", exc)
                show_info_modal(
                    session,
                    services,
                    title="Erro",
                    message=str(exc),
                    return_screen="self_select_pokemon_b",
                    reason="self_source_b_toggle_failed",
                )
        elif action == "back":
            session.self_trade_pokemon_b = None
            try:
                services.load_self_trade_party(session.self_trade_save_a)
            except Exception:
                pass
            services.switch_screen("self_select_pokemon_a", "back_from_self_pokemon_b", nav_mode="replace")
            if session.self_trade_pokemon_a:
                selected_location = str(session.self_trade_pokemon_a.get("location") or "")
                for idx, pokemon in enumerate(state.pokemon_list):
                    if str((pokemon or {}).get("location") or "") == selected_location:
                        session.menu_index = idx
                        break
                else:
                    session.menu_index = 0
            else:
                session.menu_index = 0

    def render(self, ctx, session, state, services):
        label = services.self_trade_source_label(2, session.self_trade_save_b)
        ctx.draw.draw_select_pokemon(
            ctx.screen,
            ctx.fonts,
            session.menu_index,
            state.pokemon_list,
            label,
            ctx.sprite_loader,
            session.trade_status,
            True,
            state.language,
        )


class SelectPokemonScreen(ScreenBase):
    screen_id = "select_pokemon"

    def handle_action(self, action, ctx, session, state, services):
        in_room_selection = bool(services.trade_thread_ref.current and services.trade_thread_ref.current.is_alive() and state.room_name)
        if action == "up":
            session.menu_index = max(0, session.menu_index - 1)
        elif action == "down":
            session.menu_index = min(max(0, len(state.pokemon_list) - 1), session.menu_index + 1)
        elif action == "select" and state.pokemon_list:
            if state.pokemon_source != "party":
                show_info_modal(
                    session,
                    services,
                    title="Pokemon esta no PC",
                    message="Pressione X para retirar este Pokemon para a Party antes de troca-lo.",
                    return_screen="select_pokemon",
                    reason="select_from_pc_blocked",
                )
            else:
                state.selected_pokemon = state.pokemon_list[session.menu_index]
                session.trade_return_context = services.capture_selection_context(
                    "select_pokemon",
                    selected_location=state.selected_pokemon.get("location"),
                    selected_index=session.menu_index,
                    enrich=state.action != "lan",
                )
                ctx.logger.info(
                    "Pokemon selected: %s location=%s",
                    state.selected_pokemon.get("display"),
                    state.selected_pokemon.get("location"),
                )
                session.trade_status = f"Pokemon selecionado: {state.selected_pokemon.get('display', 'Pokemon')}"
                services.switch_screen("waiting_partner", "pokemon_selected")
        elif action == "x" and state.pokemon_list:
            if state.trade_phase not in ("idle", "waiting"):
                session.trade_status = "Aguarde a troca terminar antes de mover."
            elif state.pokemon_source == "party":
                session.pending_deposit_idx = session.menu_index
                session.pending_pc_return_screen = "select_pokemon"
                ctx.logger.info("Deposit requested for party slot %s", session.pending_deposit_idx)
                services.switch_screen("deposit_confirm", "deposit_request")
            else:
                session.pending_withdraw_pokemon = state.pokemon_list[session.menu_index]
                session.pending_pc_return_screen = "select_pokemon"
                ctx.logger.info("Withdraw requested for %s", session.pending_withdraw_pokemon.get("location"))
                services.switch_screen("withdraw_confirm", "withdraw_request")
        elif action == "y":
            new_source = "boxes" if state.pokemon_source == "party" else "party"
            try:
                state.pokemon_source = new_source
                state.get_pokemon_list(new_source, enrich=state.action != "lan")
                session.menu_index = 0
                ctx.logger.info("Toggled source -> %s (%s entries)", new_source, len(state.pokemon_list))
            except SaveError as exc:
                ctx.logger.error("Source toggle failed: %s", exc)
                show_info_modal(
                    session,
                    services,
                    title="Erro",
                    message=str(exc),
                    return_screen="select_pokemon",
                    reason="source_toggle_failed",
                )
        elif action == "back":
            state.selected_pokemon = None
            services.switch_screen("load_save", "back_from_pokemon", nav_mode="replace")
            if state.selected_save in state.saves:
                session.menu_index = state.saves.index(state.selected_save)
            else:
                session.menu_index = 0

    def render(self, ctx, session, state, services):
        source_label = t(state.language, "your_party") if state.pokemon_source == "party" else t(state.language, "your_pc")
        ctx.draw.draw_select_pokemon(
            ctx.screen,
            ctx.fonts,
            session.menu_index,
            state.pokemon_list,
            source_label,
            ctx.sprite_loader,
            session.trade_status,
            language=state.language,
        )


class EnterLanEndpointScreen(ScreenBase):
    screen_id = "enter_lan_endpoint"

    def handle_action(self, action, ctx, session, state, services):
        max_key_index = services.keyboard_limits(session.keyboard_shift)
        char_count = len(services.keyboard_chars(session.keyboard_shift))
        if action == "up":
            session.keyboard_index = max(0, session.keyboard_index - ctx.draw.KEYBOARD_GRID_W)
        elif action == "down":
            session.keyboard_index = min(max_key_index, session.keyboard_index + ctx.draw.KEYBOARD_GRID_W)
        elif action == "left":
            session.keyboard_index = max(0, session.keyboard_index - 1)
        elif action == "right":
            session.keyboard_index = min(max_key_index, session.keyboard_index + 1)
        elif action == "select":
            if session.keyboard_index == char_count:
                session.lan_endpoint = session.lan_endpoint[:-1]
            elif session.keyboard_index == char_count + 1:
                session.keyboard_shift = not session.keyboard_shift
                session.keyboard_index = min(session.keyboard_index, services.keyboard_limits(session.keyboard_shift))
            elif session.keyboard_index == char_count + 2:
                session.lan_endpoint += " "
            elif session.keyboard_index == char_count + 3:
                endpoint = session.lan_endpoint.strip()
                if endpoint:
                    state.lan_manual_endpoint = endpoint
                    session.trade_status = f"Conectando em {endpoint}..."
                    services.switch_screen("connecting", "manual_lan_endpoint_submitted")
                    session.keyboard_index = 0
                    session.keyboard_shift = False
            else:
                chars = services.keyboard_chars(session.keyboard_shift)
                if session.keyboard_index < len(chars):
                    session.lan_endpoint += chars[session.keyboard_index]
        elif action == "back":
            if session.lan_endpoint:
                session.lan_endpoint = session.lan_endpoint[:-1]
            else:
                services.switch_screen("waiting_partner", "back_from_lan_endpoint", nav_mode="replace")

    def render(self, ctx, session, state, services):
        ctx.draw.draw_keyboard(
            ctx.screen,
            ctx.fonts,
            t(state.language, "lan_endpoint"),
            session.lan_endpoint,
            session.keyboard_index,
            False,
            session.keyboard_shift,
            state.language,
        )
