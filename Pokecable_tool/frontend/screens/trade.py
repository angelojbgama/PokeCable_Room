from __future__ import annotations

from frontend.session import default_info_modal, default_self_trade_decisions
from frontend.screens.base import ScreenBase, show_info_modal


def _without_held_item(pokemon):
    preview = dict(pokemon or {})
    if not preview:
        return preview
    preview["held_item_id"] = None
    preview["held_item_name"] = None
    preview["held_item_category"] = None
    raw = dict(preview.get("raw") or {})
    raw["held_item_id"] = None
    raw["held_item_name"] = None
    raw["held_item_category"] = None
    preview["raw"] = raw
    summary = dict(preview.get("summary") or {})
    summary["held_item_id"] = None
    summary["held_item_name"] = None
    preview["summary"] = summary
    canonical = dict(preview.get("canonical") or {})
    canonical["held_item"] = None
    preview["canonical"] = canonical
    return preview


class ConnectingScreen(ScreenBase):
    screen_id = "connecting"

    def render(self, ctx, session, state, services):
        ctx.draw.draw_connecting(ctx.screen, ctx.fonts, session.frame, state.language)


class WaitingPartnerScreen(ScreenBase):
    screen_id = "waiting_partner"

    def handle_action(self, action, ctx, session, state, services):
        if action == "back":
            ctx.logger.info("Cancel from waiting_partner requested")
            services.switch_screen("cancel_waiting_confirm", "cancel_requested")
        elif action == "x" and state.action == "lan" and getattr(state, "_lan_connection", None) is None:
            ctx.logger.info("Manual LAN endpoint requested")
            session.lan_endpoint = ""
            session.keyboard_index = 0
            session.keyboard_shift = False
            services.switch_screen("enter_lan_endpoint", "manual_lan_endpoint")

    def render(self, ctx, session, state, services):
        ctx.draw.draw_waiting_partner(ctx.screen, ctx.fonts, session.trade_status, state.language)


class CancelWaitingConfirmScreen(ScreenBase):
    screen_id = "cancel_waiting_confirm"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            ok = services.request_trade_cancel(state)
            ctx.logger.info("Cancel from waiting confirmed: scheduled=%s", ok)
            if ok:
                session.trade_status = "Cancelando..."
                services.switch_screen("waiting_partner", "cancel_pending")
            else:
                session.trade_status = "Nao foi possivel cancelar agora."
                services.switch_screen("waiting_partner", "cancel_failed")
        elif action == "back":
            ctx.logger.info("Cancel from waiting aborted")
            services.switch_screen("waiting_partner", "cancel_aborted")

    def render(self, ctx, session, state, services):
        ctx.draw.draw_cancel_waiting_confirm(
            ctx.screen,
            ctx.fonts,
            state.selected_pokemon or {},
            ctx.sprite_loader,
            state.language,
        )


class LeaveRoomConfirmScreen(ScreenBase):
    screen_id = "leave_room_confirm"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            ctx.logger.info("Leave room confirmed")
            services.request_leave_room(state)
            session.trade_status = "Saindo da sala..."
            services.switch_screen("menu", "leave_room_yes")
            session.menu_index = 0
            services.reset_flow_state(state)
        elif action == "back":
            ctx.logger.info("Leave room aborted")
            services.switch_screen("select_pokemon", "leave_room_no")

    def render(self, ctx, session, state, services):
        ctx.draw.draw_leave_room_confirm(ctx.screen, ctx.fonts, state.language)


class SelfTradeConfirmScreen(ScreenBase):
    screen_id = "self_trade_confirm"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            ctx.logger.info("Self trade confirmation accepted")
            services.finish_self_trade()
        elif action == "back":
            ctx.logger.info("Self trade confirmation declined")
            session.result_data = {}
            session.trade_status = "Troca local cancelada."
            services.reset_self_trade_state()
            services.reset_flow_state(state)
            services.switch_screen("menu", "self_trade_confirm_no")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        pokemon_a = dict(session.self_trade_pokemon_a or {})
        payload_b = session.self_trade_context.get("payload_b", {}) if isinstance(session.self_trade_context, dict) else {}
        pokemon_b = dict(payload_b or {})
        if session.self_trade_save_a is not None:
            pokemon_a.setdefault("save_name", session.self_trade_save_a.name)
        if session.self_trade_save_b is not None:
            pokemon_b.setdefault("save_name", session.self_trade_save_b.name)
        ctx.draw.draw_trade_confirm(
            ctx.screen,
            ctx.fonts,
            pokemon_a,
            pokemon_b,
            ctx.sprite_loader,
            state.language,
        )


class TradeConfirmScreen(ScreenBase):
    screen_id = "trade_confirm"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            ctx.logger.info("Trade confirmation accepted")
            services.confirm_queue.put(True)
            services.switch_screen("trading", "trade_confirm_yes")
        elif action == "back":
            ctx.logger.info("Trade confirmation declined")
            services.confirm_queue.put(False)
            services.switch_screen("menu", "trade_confirm_no")
            session.menu_index = 0
            session.result_data = {}
            services.reset_flow_state(state)

    def render(self, ctx, session, state, services):
        mine = dict(state.selected_pokemon or {})
        peer = dict(session.result_data if isinstance(session.result_data, dict) else {})
        if state.selected_save is not None:
            mine.setdefault("save_name", state.selected_save.name)
        peer.setdefault("save_name", state.room_name or "Sala LAN")
        ctx.draw.draw_trade_confirm(
            ctx.screen,
            ctx.fonts,
            mine,
            peer,
            ctx.sprite_loader,
            state.language,
        )


class InfoModalScreen(ScreenBase):
    screen_id = "info_modal"

    def handle_action(self, action, ctx, session, state, services):
        if action in ("select", "back"):
            ctx.logger.info("Info modal acknowledged")
            return_screen = session.info_modal_data.get("return_screen") if isinstance(session.info_modal_data, dict) else ""
            session.info_modal_data = default_info_modal()
            if return_screen:
                services.switch_screen(return_screen, "info_modal_ack")
            else:
                services.confirm_queue.put(True)

    def render(self, ctx, session, state, services):
        ctx.draw.draw_info_modal(
            ctx.screen,
            ctx.fonts,
            session.info_modal_data.get("title", ""),
            session.info_modal_data.get("message", ""),
            state.language,
        )


class ResolveMovesScreen(ScreenBase):
    screen_id = "resolve_moves"

    def handle_action(self, action, ctx, session, state, services):
        if not action or not session.pending_removed_moves:
            return
        current_move = session.pending_removed_moves[session.resolve_current_idx]
        chosen_set = set(int(x) for x in session.resolved_moves_choices.values() if x)
        replacements = [
            replacement
            for replacement in (current_move.get("valid_replacements") or [])
            if int(replacement.get("move_id") or 0) not in chosen_set
        ]
        total_options = len(replacements) + 1
        if action == "up":
            session.resolve_replacement_idx = (session.resolve_replacement_idx - 1) % total_options
        elif action == "down":
            session.resolve_replacement_idx = (session.resolve_replacement_idx + 1) % total_options
        elif action in ("select", "back"):
            if action == "select" and session.resolve_replacement_idx < len(replacements):
                move_id = int(current_move.get("move_id") or 0)
                replacement_id = int(replacements[session.resolve_replacement_idx].get("move_id") or 0)
                if move_id and replacement_id:
                    session.resolved_moves_choices[move_id] = replacement_id
            session.resolve_current_idx += 1
            session.resolve_replacement_idx = 0
            if session.resolve_current_idx >= len(session.pending_removed_moves):
                ctx.logger.info("Move resolution complete: %s", session.resolved_moves_choices)
                if session.self_trade_pending_decision in ("resolved_moves_to_a", "resolved_moves_to_b"):
                    session.self_trade_decisions[session.self_trade_pending_decision] = dict(session.resolved_moves_choices)
                    session.self_trade_pending_decision = ""
                    session.pending_removed_moves = []
                    services.advance_self_trade_prompts()
                else:
                    services.confirm_queue.put(dict(session.resolved_moves_choices))
                    session.pending_removed_moves = []

    def render(self, ctx, session, state, services):
        if not session.pending_removed_moves:
            return
        pokemon = dict(state.selected_pokemon or {})
        ctx.draw.draw_resolve_moves(
            ctx.screen,
            ctx.fonts,
            session.pending_removed_moves[session.resolve_current_idx],
            session.resolve_replacement_idx,
            session.resolve_current_idx,
            len(session.pending_removed_moves),
            set(session.resolved_moves_choices.values()),
            ctx.sprite_loader,
            pokemon,
            state.language,
        )


class ResolveItemRelocationScreen(ScreenBase):
    screen_id = "resolve_item_relocation"

    def handle_action(self, action, ctx, session, state, services):
        if not action or not session.pending_item_relocation:
            return
        options = [str(option) for option in (session.pending_item_relocation.get("options") or []) if str(option)]
        if not options:
            return
        if action == "up":
            session.item_relocation_index = (session.item_relocation_index - 1) % len(options)
        elif action == "down":
            session.item_relocation_index = (session.item_relocation_index + 1) % len(options)
        elif action == "select":
            choice = options[session.item_relocation_index]
            ctx.logger.info("Item relocation choice: %s", choice)
            preview_pokemon = _without_held_item(session.pending_item_relocation_pokemon or state.selected_pokemon or {})
            if session.self_trade_pending_decision in ("item_relocation_choice_to_a", "item_relocation_choice_to_b"):
                if session.self_trade_pending_decision == "item_relocation_choice_to_a":
                    session.self_trade_pokemon_a = preview_pokemon
                    if isinstance(session.self_trade_context, dict):
                        session.self_trade_context["payload_a"] = preview_pokemon
                else:
                    session.self_trade_pokemon_b = preview_pokemon
                    if isinstance(session.self_trade_context, dict):
                        session.self_trade_context["payload_b"] = preview_pokemon
                session.self_trade_decisions[session.self_trade_pending_decision] = choice
                session.self_trade_pending_decision = ""
                session.pending_item_relocation = {}
                session.pending_item_relocation_pokemon = {}
                services.advance_self_trade_prompts()
            else:
                state.selected_pokemon = preview_pokemon
                services.confirm_queue.put(choice)
                session.pending_item_relocation = {}
                session.pending_item_relocation_pokemon = {}
        elif action == "back":
            ctx.logger.info("Item relocation cancelled by user")
            session.pending_item_relocation = {}
            session.pending_item_relocation_pokemon = {}
            pending_decision = str(session.self_trade_pending_decision or "")
            session.self_trade_pending_decision = ""
            if pending_decision == "item_relocation_choice_to_a":
                session.trade_status = "Troca local cancelada. Escolha outro Pokemon."
                session.self_trade_context = {}
                session.self_trade_pokemon_a = None
                session.self_trade_pokemon_b = None
                session.self_trade_decisions = default_self_trade_decisions()
                try:
                    services.load_self_trade_party(session.self_trade_save_a)
                except Exception as exc:
                    ctx.logger.warning("Failed to reload self trade party A after item cancellation: %s", exc)
                services.switch_screen("self_select_pokemon_a", "item_relocation_back_to_a")
                session.menu_index = 0
                return
            if pending_decision == "item_relocation_choice_to_b":
                session.trade_status = "Troca local cancelada. Escolha outro Pokemon."
                session.self_trade_context = {}
                session.self_trade_pokemon_b = None
                session.self_trade_decisions = default_self_trade_decisions()
                try:
                    services.load_self_trade_party(session.self_trade_save_b)
                except Exception as exc:
                    ctx.logger.warning("Failed to reload self trade party B after item cancellation: %s", exc)
                services.switch_screen("self_select_pokemon_b", "item_relocation_back_to_b")
                session.menu_index = 0
                return
            state.selected_pokemon = None
            services.request_trade_cancel(state)
            session.trade_status = "Troca cancelada. Escolha outro Pokemon."
            services.switch_screen("select_pokemon", "item_relocation_back")
            session.menu_index = 0

    def render(self, ctx, session, state, services):
        if not session.pending_item_relocation:
            return
        pokemon = dict(session.pending_item_relocation_pokemon or state.selected_pokemon or {})
        ctx.draw.draw_resolve_item_relocation(
            ctx.screen,
            ctx.fonts,
            session.pending_item_relocation,
            session.item_relocation_index,
            ctx.sprite_loader,
            pokemon,
            state.language,
        )


class EvolutionCancelPromptScreen(ScreenBase):
    screen_id = "evolution_cancel_prompt"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            ctx.logger.info("Evolution cancellation skipped (A = let evolve)")
            if session.self_trade_pending_decision in ("cancel_evolution_to_a", "cancel_evolution_to_b"):
                session.self_trade_decisions[session.self_trade_pending_decision] = False
                session.self_trade_pending_decision = ""
                services.switch_screen("trading", "self_evolution_cancel_no")
                services.advance_self_trade_prompts()
            else:
                services.confirm_queue.put(False)
                services.switch_screen("trading", "evolution_cancel_no")
        elif action == "back":
            ctx.logger.info("Evolution cancellation requested (B = interrupt)")
            services.switch_screen("evolution_cancel_confirm", "evolution_cancel_requested")

    def render(self, ctx, session, state, services):
        anim_frame = max(0, session.frame - (session.evolution_anim_start if session.evolution_anim_start is not None else session.frame))
        ctx.draw.draw_evolution_cancel_prompt(
            ctx.screen,
            ctx.fonts,
            session.result_data if isinstance(session.result_data, dict) else {},
            ctx.sprite_loader,
            anim_frame,
            state.language,
        )


class EvolutionCancelConfirmScreen(ScreenBase):
    screen_id = "evolution_cancel_confirm"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            ctx.logger.info("Evolution cancellation rejected (A = let evolve)")
            if session.self_trade_pending_decision in ("cancel_evolution_to_a", "cancel_evolution_to_b"):
                session.self_trade_decisions[session.self_trade_pending_decision] = False
                session.self_trade_pending_decision = ""
                services.switch_screen("trading", "self_evolution_cancel_rejected")
                services.advance_self_trade_prompts()
            else:
                services.confirm_queue.put(False)
                services.switch_screen("trading", "evolution_cancel_rejected")
        elif action == "back":
            ctx.logger.info("Evolution cancellation confirmed (B = interrupt)")
            if session.self_trade_pending_decision in ("cancel_evolution_to_a", "cancel_evolution_to_b"):
                session.self_trade_decisions[session.self_trade_pending_decision] = True
                session.self_trade_pending_decision = ""
                services.switch_screen("trading", "self_evolution_cancel_yes")
                services.advance_self_trade_prompts()
            else:
                services.confirm_queue.put(True)
                services.switch_screen("trading", "evolution_cancel_yes")

    def render(self, ctx, session, state, services):
        ctx.draw.draw_evolution_cancel_confirm(
            ctx.screen,
            ctx.fonts,
            session.result_data if isinstance(session.result_data, dict) else {},
            ctx.sprite_loader,
            session.frame,
            state.language,
        )


class WithdrawConfirmScreen(ScreenBase):
    screen_id = "withdraw_confirm"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            save_model = state.get_selected_save_model()
            if not save_model or not session.pending_withdraw_pokemon:
                show_info_modal(
                    session,
                    services,
                    title="Erro",
                    message="Slot do PC nao encontrado.",
                    return_screen=session.pending_pc_return_screen,
                    reason="withdraw_no_target",
                )
            else:
                try:
                    services.create_backup(state.selected_save)
                    location = str(session.pending_withdraw_pokemon.get("location") or "")
                    parts = location.split(":")
                    if len(parts) >= 3 and parts[0] == "box":
                        box_idx = int(parts[1])
                        slot_idx = int(parts[2])
                    else:
                        box_idx = int(session.pending_withdraw_pokemon.get("box_index") or 0)
                        slot_idx = int(session.pending_withdraw_pokemon.get("slot_index") or 0)
                    ctx.logger.info("Withdraw target: location=%s box=%s slot=%s", location, box_idx, slot_idx)
                    result = save_model.withdraw_box_to_party(box_idx, slot_idx)
                    save_model.write_to_disk()
                    state.expected_signature = save_model.signature()
                    state.refresh_selected_save()
                    services.reload_after_pc_management(state.pokemon_source or "boxes")
                    session.menu_index = min(session.menu_index, max(0, len(state.pokemon_list) - 1))
                    session.trade_status = ""
                    services.switch_screen(session.pending_pc_return_screen, "withdraw_done")
                except Exception as exc:
                    ctx.logger.exception("Withdraw failed: %s", exc)
                    show_info_modal(
                        session,
                        services,
                        title="Nao foi possivel retirar",
                        message=str(exc),
                        return_screen=session.pending_pc_return_screen,
                        reason="withdraw_failed",
                    )
            session.pending_withdraw_pokemon = None
        elif action == "back":
            session.pending_withdraw_pokemon = None
            services.switch_screen(session.pending_pc_return_screen, "withdraw_aborted")

    def render(self, ctx, session, state, services):
        ctx.draw.draw_withdraw_confirm(
            ctx.screen,
            ctx.fonts,
            session.pending_withdraw_pokemon or {},
            state.language,
        )


class DepositConfirmScreen(ScreenBase):
    screen_id = "deposit_confirm"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            save_model = state.get_selected_save_model()
            if not save_model:
                show_info_modal(
                    session,
                    services,
                    title="Erro",
                    message="Save nao carregado.",
                    return_screen=session.pending_pc_return_screen,
                    reason="deposit_no_save",
                )
            else:
                try:
                    services.create_backup(state.selected_save)
                    result = save_model.deposit_party_to_pc(session.pending_deposit_idx)
                    save_model.write_to_disk()
                    state.expected_signature = save_model.signature()
                    state.refresh_selected_save()
                    services.reload_after_pc_management("party")
                    session.menu_index = min(session.menu_index, max(0, len(state.pokemon_list) - 1))
                    session.trade_status = ""
                    services.switch_screen(session.pending_pc_return_screen, "deposit_done")
                except Exception as exc:
                    ctx.logger.exception("Deposit failed: %s", exc)
                    show_info_modal(
                        session,
                        services,
                        title="Nao foi possivel mover",
                        message=str(exc),
                        return_screen=session.pending_pc_return_screen,
                        reason="deposit_failed",
                    )
            session.pending_deposit_idx = -1
        elif action == "back":
            session.pending_deposit_idx = -1
            services.switch_screen(session.pending_pc_return_screen, "deposit_aborted")

    def render(self, ctx, session, state, services):
        target_pokemon = None
        if 0 <= session.pending_deposit_idx < len(state.pokemon_list):
            target_pokemon = state.pokemon_list[session.pending_deposit_idx]
        ctx.draw.draw_deposit_confirm(ctx.screen, ctx.fonts, target_pokemon or {}, ctx.sprite_loader, state.language)


class TradingScreen(ScreenBase):
    screen_id = "trading"

    def render(self, ctx, session, state, services):
        ctx.draw.draw_trading(ctx.screen, ctx.fonts, session.trade_status, state.language)


class TradeResultScreen(ScreenBase):
    screen_id = "trade_result"

    def handle_action(self, action, ctx, session, state, services):
        if action not in ("select", "back"):
            return
        ctx.logger.info("Trade result acknowledged: %s", session.result_data)
        success = bool(isinstance(session.result_data, dict) and session.result_data.get("success"))
        staying_in_room = bool(success and services.trade_thread_ref.current and services.trade_thread_ref.current.is_alive())
        session.result_data = {}
        session.trade_status = ""
        session.menu_index = 0
        if staying_in_room:
            services.switch_screen("select_pokemon", "trade_result_ack_continue")
        else:
            services.switch_screen("menu", "trade_result_ack")
            services.reset_flow_state(state)
            services.reset_self_trade_state()

    def render(self, ctx, session, state, services):
        success = bool(isinstance(session.result_data, dict) and session.result_data.get("success"))
        data = session.result_data if success else session.result_data.get("error", session.trade_status) if isinstance(session.result_data, dict) else session.trade_status
        ctx.draw.draw_trade_result(ctx.screen, ctx.fonts, success, data, ctx.sprite_loader, state.language)
