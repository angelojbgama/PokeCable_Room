from __future__ import annotations

from pathlib import Path

from frontend.i18n import t


def load_self_trade_source(session, state, save_path, source="party", *, target_save_path=None, require_compatible_to_target=False):
    state.selected_save = Path(save_path)
    state.pokemon_source = source
    state.selected_pokemon = None
    state.get_pokemon_list(source, enrich=False)
    source_label = t(state.language, "party") if source == "party" else t(state.language, "pc")
    base_status = f"{source_label}: {Path(save_path).name}"
    if not require_compatible_to_target or not target_save_path or not session.self_trade_pokemon_a:
        session.trade_status = base_status
        return
    session.trade_status = base_status


def load_self_trade_party(session, state, save_path, *, target_save_path=None, require_compatible_to_target=False):
    load_self_trade_source(
        session,
        state,
        save_path,
        "party",
        target_save_path=target_save_path,
        require_compatible_to_target=require_compatible_to_target,
    )


def self_trade_source_label(session, state, slot, save_path):
    source = state.pokemon_source if state.pokemon_source in ("party", "boxes") else "party"
    if source == "party":
        key = "party_save_named" if save_path else "party_save"
    else:
        key = "pc_save_named" if save_path else "pc_save"
    if save_path:
        return t(state.language, key, slot=slot, name=Path(save_path).name)
    return t(state.language, key, slot=slot)


def reload_after_pc_management(session, state, source):
    self_trade_local = str(session.pending_pc_return_screen or "").startswith("self_")
    state.get_pokemon_list(source, enrich=not self_trade_local and state.action != "lan")


def advance_self_trade_prompts(session, state, services, logger):
    preflight_to_a = session.self_trade_context.get("preflight_to_a", {}) if isinstance(session.self_trade_context, dict) else {}
    preflight_to_b = session.self_trade_context.get("preflight_to_b", {}) if isinstance(session.self_trade_context, dict) else {}
    evolution_to_a = session.self_trade_context.get("trade_evolution_to_a", {}) if isinstance(session.self_trade_context, dict) else {}
    evolution_to_b = session.self_trade_context.get("trade_evolution_to_b", {}) if isinstance(session.self_trade_context, dict) else {}

    if not session.self_trade_decisions.get("_evolution_to_a_done"):
        session.self_trade_decisions["_evolution_to_a_done"] = True
        evolution = evolution_to_a if isinstance(evolution_to_a, dict) and evolution_to_a else {}
        if not evolution and isinstance(preflight_to_a, dict):
            evolution = preflight_to_a.get("trade_evolution") or {}
            logger.warning("Self-trade evolution fallback used for save A preflight payload")
        if isinstance(evolution, dict) and evolution.get("evolved"):
            session.result_data = evolution
            session.self_trade_pending_decision = "cancel_evolution_to_a"
            session.evolution_anim_start = session.frame
            session.trade_status = f"{Path(session.self_trade_save_a).name}: decidir evolucao"
            services.switch_screen("evolution_cancel_prompt", "self_trade_evolution_to_a")
            return
        logger.info("Self-trade no evolution prompt for save A: evolved=%s reason=%s", evolution.get("evolved"), evolution.get("reason"))

    if not session.self_trade_decisions.get("_item_to_a_done"):
        session.self_trade_decisions["_item_to_a_done"] = True
        relocation = session.self_trade_context.get("outgoing_item_relocation_a", {}) if isinstance(session.self_trade_context, dict) else {}
        relocation = relocation if isinstance(relocation, dict) else {}
        if relocation.get("status") == "choose_destination":
            session.pending_item_relocation = dict(relocation)
            session.pending_item_relocation_pokemon = dict(session.self_trade_context.get("payload_a", {}) or {})
            session.item_relocation_index = 0
            session.self_trade_pending_decision = "item_relocation_choice_to_a"
            session.trade_status = f"{Path(session.self_trade_save_a).name}: guardar item"
            services.switch_screen("resolve_item_relocation", "self_trade_item_to_a")
            return

    if not session.self_trade_decisions.get("_moves_to_a_done"):
        session.self_trade_decisions["_moves_to_a_done"] = True
        removed = list(preflight_to_a.get("removed_moves") or []) if isinstance(preflight_to_a, dict) else []
        if removed:
            session.pending_removed_moves = removed
            session.resolve_current_idx = 0
            session.resolve_replacement_idx = 0
            session.resolved_moves_choices = {}
            session.self_trade_pending_decision = "resolved_moves_to_a"
            session.trade_status = f"{Path(session.self_trade_save_a).name}: resolver movimentos"
            services.switch_screen("resolve_moves", "self_trade_moves_to_a")
            return

    if not session.self_trade_decisions.get("_evolution_to_b_done"):
        session.self_trade_decisions["_evolution_to_b_done"] = True
        evolution = evolution_to_b if isinstance(evolution_to_b, dict) and evolution_to_b else {}
        if not evolution and isinstance(preflight_to_b, dict):
            evolution = preflight_to_b.get("trade_evolution") or {}
            logger.warning("Self-trade evolution fallback used for save B preflight payload")
        if isinstance(evolution, dict) and evolution.get("evolved"):
            session.result_data = evolution
            session.self_trade_pending_decision = "cancel_evolution_to_b"
            session.evolution_anim_start = session.frame
            session.trade_status = f"{Path(session.self_trade_save_b).name}: decidir evolucao"
            services.switch_screen("evolution_cancel_prompt", "self_trade_evolution_to_b")
            return
        logger.info("Self-trade no evolution prompt for save B: evolved=%s reason=%s", evolution.get("evolved"), evolution.get("reason"))

    if not session.self_trade_decisions.get("_item_to_b_done"):
        session.self_trade_decisions["_item_to_b_done"] = True
        relocation = session.self_trade_context.get("outgoing_item_relocation_b", {}) if isinstance(session.self_trade_context, dict) else {}
        relocation = relocation if isinstance(relocation, dict) else {}
        if relocation.get("status") == "choose_destination":
            session.pending_item_relocation = dict(relocation)
            session.pending_item_relocation_pokemon = dict(session.self_trade_context.get("payload_b", {}) or {})
            session.item_relocation_index = 0
            session.self_trade_pending_decision = "item_relocation_choice_to_b"
            session.trade_status = f"{Path(session.self_trade_save_b).name}: guardar item"
            services.switch_screen("resolve_item_relocation", "self_trade_item_to_b")
            return

    if not session.self_trade_decisions.get("_moves_to_b_done"):
        session.self_trade_decisions["_moves_to_b_done"] = True
        removed = list(preflight_to_b.get("removed_moves") or []) if isinstance(preflight_to_b, dict) else []
        if removed:
            session.pending_removed_moves = removed
            session.resolve_current_idx = 0
            session.resolve_replacement_idx = 0
            session.resolved_moves_choices = {}
            session.self_trade_pending_decision = "resolved_moves_to_b"
            session.trade_status = f"{Path(session.self_trade_save_b).name}: resolver movimentos"
            services.switch_screen("resolve_moves", "self_trade_moves_to_b")
            return

    state.selected_pokemon = session.self_trade_pokemon_a
    session.result_data = session.self_trade_context.get("payload_b", {}) if isinstance(session.self_trade_context, dict) else {}
    session.trade_status = "Validacoes concluidas. Confirme a troca local."
    session.menu_index = 0
    services.switch_screen("self_trade_confirm", "self_trade_ready_to_confirm")


def finish_self_trade(session, state, services, logger):
    session.trade_status = "Aplicando troca local..."
    services.switch_screen("trading", "self_trade_commit")
    try:
        session.result_data = services.execute_self_trade(
            session.self_trade_context,
            cancel_evolution_to_a=bool(session.self_trade_decisions.get("cancel_evolution_to_a")),
            cancel_evolution_to_b=bool(session.self_trade_decisions.get("cancel_evolution_to_b")),
            resolved_moves_to_a=dict(session.self_trade_decisions.get("resolved_moves_to_a") or {}),
            resolved_moves_to_b=dict(session.self_trade_decisions.get("resolved_moves_to_b") or {}),
            item_relocation_choice_to_a=str(session.self_trade_decisions.get("item_relocation_choice_to_a") or ""),
            item_relocation_choice_to_b=str(session.self_trade_decisions.get("item_relocation_choice_to_b") or ""),
        )
        session.trade_status = "Troca local concluida!"
        state.save_analysis.clear()
        services.switch_screen("trade_result", "self_trade_done")
        session.menu_index = 0
    except Exception as exc:
        logger.exception("Self trade failed: %s", exc)
        session.trade_status = f"Erro: {exc}"
        session.result_data = {"success": False, "error": str(exc)}
        services.switch_screen("trade_result", "self_trade_failed")
        session.menu_index = 0
