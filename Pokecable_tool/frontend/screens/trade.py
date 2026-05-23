from __future__ import annotations

from pokecable_save import _ensure_backend_import_path

from frontend.session import default_info_modal, default_self_trade_decisions
from frontend.screens.base import ScreenBase, show_info_modal


def _as_int(value, default=0):
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _native_to_national(generation, species_id):
    generation = _as_int(generation)
    species_id = _as_int(species_id)
    if generation <= 0 or species_id <= 0:
        return species_id
    try:
        _ensure_backend_import_path()
        from data.species import native_to_national  # type: ignore

        return int(native_to_national(generation, species_id) or 0)
    except Exception:
        return species_id


def _species_name_by_national(national_id):
    national_id = _as_int(national_id)
    if national_id <= 0:
        return ""
    try:
        _ensure_backend_import_path()
        from data.species import SPECIES_NAMES_BY_NATIONAL  # type: ignore

        return str(SPECIES_NAMES_BY_NATIONAL.get(national_id) or "")
    except Exception:
        return ""


def _pokemon_generation(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    return _as_int(
        (pokemon or {}).get("generation")
        or (raw.get("generation") if isinstance(raw, dict) else 0)
        or (canonical.get("source_generation") if isinstance(canonical, dict) else 0)
    )


def _pokemon_native_species_id(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    species = canonical.get("species", {}) if isinstance(canonical, dict) else {}
    return _as_int(
        (pokemon or {}).get("species_id")
        or (raw.get("species_id") if isinstance(raw, dict) else 0)
        or (species.get("source_species_id") if isinstance(species, dict) else 0)
    )


def _pokemon_national_dex_id(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    species = canonical.get("species", {}) if isinstance(canonical, dict) else {}
    for value in (
        (pokemon or {}).get("national_dex_id") if isinstance(pokemon, dict) else None,
        raw.get("national_dex_id") if isinstance(raw, dict) else None,
        canonical.get("species_national_id") if isinstance(canonical, dict) else None,
        species.get("national_dex_id") if isinstance(species, dict) else None,
    ):
        national_id = _as_int(value)
        if national_id > 0:
            return national_id
    return _native_to_national(_pokemon_generation(pokemon), _pokemon_native_species_id(pokemon))


def _pokemon_level(pokemon):
    raw = (pokemon or {}).get("raw", {}) if isinstance(pokemon, dict) else {}
    summary = (pokemon or {}).get("summary", {}) if isinstance(pokemon, dict) else {}
    canonical = (pokemon or {}).get("canonical", {}) if isinstance(pokemon, dict) else {}
    for value in (
        (pokemon or {}).get("level") if isinstance(pokemon, dict) else None,
        raw.get("level") if isinstance(raw, dict) else None,
        summary.get("level") if isinstance(summary, dict) else None,
        canonical.get("level") if isinstance(canonical, dict) else None,
    ):
        level = _as_int(value)
        if level > 0:
            return level
    return 100


def _evolution_target_ids(evolution):
    evolution = evolution if isinstance(evolution, dict) else {}
    generation = _as_int(evolution.get("generation"))
    native_id = _as_int(evolution.get("target_species_id"))
    national_id = _as_int(
        evolution.get("target_national_id")
        or evolution.get("target_national_dex_id")
        or evolution.get("target_species_national_id")
    )
    if national_id <= 0 and native_id > 0:
        national_id = _native_to_national(generation, native_id)
    return generation, native_id, national_id


def _apply_evolution_display(
    pokemon,
    evolved_species,
    evolved_name,
    *,
    generation=0,
    native_species_id=0,
    consume_item=False,
):
    """Atualiza pokemon dict com forma evoluída para exibição."""
    pokemon = dict(pokemon or {})
    evolved_species = _as_int(evolved_species)
    native_species_id = _as_int(native_species_id)
    generation = _as_int(generation) or _pokemon_generation(pokemon)
    if evolved_species:
        evolved_name = evolved_name or _species_name_by_national(evolved_species) or pokemon.get("species_name")
        # Atualizar top-level
        pokemon["national_dex_id"] = evolved_species
        pokemon["species_name"] = evolved_name
        pokemon["nickname"] = None  # Força exibição de species_name
        if native_species_id > 0:
            pokemon["species_id"] = native_species_id
        if generation > 0:
            pokemon["generation"] = generation

        # Limpar campos cacheados que podem ter dados da forma original
        # Isso força o código de display a recalcular usando national_dex_id atualizado
        pokemon.pop("types", None)
        pokemon.pop("type_text", None)
        pokemon.pop("sprite", None)
        pokemon.pop("sprite_data", None)

        # Atualizar dados canônicos se existem
        if "canonical" in pokemon and isinstance(pokemon["canonical"], dict):
            canonical = dict(pokemon["canonical"])
            canonical["species_national_id"] = evolved_species
            canonical["species_name"] = evolved_name or canonical.get("species_name")
            if generation > 0:
                canonical["source_generation"] = generation
            if "species" in canonical and isinstance(canonical["species"], dict):
                species = dict(canonical["species"])
                species["national_dex_id"] = evolved_species
                species["name"] = evolved_name or species.get("name")
                if native_species_id > 0:
                    species["source_species_id"] = native_species_id
                    species["target_species_id"] = native_species_id
                canonical["species"] = species
            pokemon["canonical"] = canonical

        # Atualizar raw se existe
        if "raw" in pokemon and isinstance(pokemon["raw"], dict):
            raw = dict(pokemon["raw"])
            raw["national_dex_id"] = evolved_species
            if native_species_id > 0:
                raw["species_id"] = native_species_id
            if generation > 0:
                raw["generation"] = generation
            # Limpar tipos cacheados em raw também
            raw.pop("types", None)
            pokemon["raw"] = raw
        if "summary" in pokemon and isinstance(pokemon["summary"], dict):
            summary = dict(pokemon["summary"])
            summary["national_dex_id"] = evolved_species
            if native_species_id > 0:
                summary["species_id"] = native_species_id
            summary["species_name"] = evolved_name or summary.get("species_name")
            pokemon["summary"] = summary
        if consume_item:
            pokemon["held_item_id"] = None
            pokemon["held_item_name"] = None
            pokemon["held_item_category"] = None
            raw = dict(pokemon.get("raw") or {})
            raw["held_item_id"] = None
            raw["held_item_name"] = None
            raw["held_item_category"] = None
            pokemon["raw"] = raw
            summary = dict(pokemon.get("summary") or {})
            summary["held_item_id"] = None
            summary["held_item_name"] = None
            pokemon["summary"] = summary
            canonical = dict(pokemon.get("canonical") or {})
            canonical["held_item"] = None
            pokemon["canonical"] = canonical
    return pokemon


def _apply_evolution_display_from_payload(pokemon, evolution, cancel_evolution=False):
    if cancel_evolution or not isinstance(evolution, dict) or not evolution.get("evolved"):
        return dict(pokemon or {})
    generation, native_id, national_id = _evolution_target_ids(evolution)
    if national_id <= 0:
        return dict(pokemon or {})
    return _apply_evolution_display(
        pokemon,
        national_id,
        evolution.get("target_name"),
        generation=generation,
        native_species_id=native_id,
        consume_item=bool(evolution.get("consumed_item_id")),
    )


def _store_accepted_self_trade_evolution(session):
    pending = session.self_trade_pending_decision or ""
    if pending not in ("cancel_evolution_to_a", "cancel_evolution_to_b"):
        return
    if not isinstance(session.result_data, dict) or not session.result_data.get("evolved"):
        return
    suffix = pending.split("_")[-1]
    generation, native_id, national_id = _evolution_target_ids(session.result_data)
    if national_id > 0:
        session.self_trade_decisions[f"evolved_species_{suffix}"] = national_id
    if native_id > 0:
        session.self_trade_decisions[f"evolved_native_species_{suffix}"] = native_id
    if generation > 0:
        session.self_trade_decisions[f"evolved_generation_{suffix}"] = generation
    session.self_trade_decisions[f"evolved_name_{suffix}"] = session.result_data.get("target_name")
    session.self_trade_decisions[f"evolved_consumed_item_{suffix}"] = bool(session.result_data.get("consumed_item_id"))


def _valid_replacements_for_preview(pokemon, target_generation, target_game=""):
    target_generation = _as_int(target_generation) or _pokemon_generation(pokemon)
    national_id = _pokemon_national_dex_id(pokemon)
    if target_generation <= 0 or national_id <= 0:
        return None
    try:
        _ensure_backend_import_path()
        from data.learnsets import get_level_up_replacements  # type: ignore

        return get_level_up_replacements(
            str(target_game or ""),
            national_id,
            _pokemon_level(pokemon),
            generation=target_generation,
        )
    except Exception:
        return None


def _rebuild_removed_moves_for_preview(removed_moves, pokemon, target_generation, target_game=""):
    replacements = _valid_replacements_for_preview(pokemon, target_generation, target_game)
    rebuilt = []
    for removed_move in removed_moves or []:
        entry = dict(removed_move or {})
        if replacements is not None:
            entry["valid_replacements"] = list(replacements)
        rebuilt.append(entry)
    return rebuilt


def _apply_moves_display(pokemon, resolved_moves, move_names):
    """Cria cópia do pokemon com moves substituídos para exibição (não afeta dados do backend)."""
    pokemon = dict(pokemon or {})
    if not pokemon:
        return pokemon
    moves = list(pokemon.get("moves") or [])
    names = list(pokemon.get("move_names") or [])
    details = list(pokemon.get("move_details") or [])
    for old_id_raw, new_id_raw in (resolved_moves or {}).items():
        old_id = int(old_id_raw)
        new_id = int(new_id_raw) if new_id_raw else 0
        try:
            idx = moves.index(old_id)
            if new_id > 0:
                moves[idx] = new_id
                new_name = (move_names or {}).get(old_id) or (move_names or {}).get(str(old_id)) or f"Move #{new_id}"
                if idx < len(names):
                    names[idx] = new_name
            else:
                moves.pop(idx)
                if idx < len(names):
                    names.pop(idx)
                if idx < len(details):
                    details.pop(idx)
        except (ValueError, TypeError):
            pass
    pokemon["moves"] = moves
    pokemon["move_names"] = names
    pokemon["move_details"] = details
    return pokemon


def _resolved_move_names_for_preview(removed_moves, resolved_moves, explicit_names=None):
    names = dict(explicit_names or {})
    chosen = resolved_moves or {}
    if not chosen:
        return names
    for removed_move in removed_moves or []:
        old_id = _as_int((removed_move or {}).get("move_id"))
        if old_id <= 0:
            continue
        new_id = _as_int(chosen.get(old_id) or chosen.get(str(old_id)))
        if new_id <= 0:
            continue
        if old_id in names or str(old_id) in names:
            continue
        for replacement in (removed_move.get("valid_replacements") or []):
            replacement_id = _as_int((replacement or {}).get("move_id"))
            if replacement_id == new_id:
                names[old_id] = replacement.get("name") or f"Move #{new_id}"
                break
    return names


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
            services.go_back("waiting_partner", "cancel_aborted")

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
            session.self_trade_context = {}
            session.self_trade_pending_decision = ""
            session.self_trade_decisions = default_self_trade_decisions()
            services.restore_selection_context(
                session.self_trade_return_context,
                "self_trade_confirm_no",
                fallback_screen="self_select_pokemon_b",
            )
            session.prompt_return_context = {}

    def render(self, ctx, session, state, services):
        decisions = session.self_trade_decisions or {}
        ctx_data = session.self_trade_context if isinstance(session.self_trade_context, dict) else {}

        pokemon_a = dict(session.self_trade_pokemon_a or {})
        payload_b = ctx_data.get("payload_b") or {}
        pokemon_b = dict(payload_b)

        # Aplica evolução: evolved_species_a → pokemon_b (entra em save A, exibido à direita)
        if decisions.get("evolved_species_a") and not decisions.get("cancel_evolution_to_a"):
            pokemon_b = _apply_evolution_display(
                pokemon_b,
                decisions["evolved_species_a"],
                decisions.get("evolved_name_a"),
                generation=decisions.get("evolved_generation_a"),
                native_species_id=decisions.get("evolved_native_species_a"),
                consume_item=bool(decisions.get("evolved_consumed_item_a")),
            )

        # Aplica evolução: evolved_species_b → pokemon_a (entra em save B, exibido à esquerda)
        if decisions.get("evolved_species_b") and not decisions.get("cancel_evolution_to_b"):
            pokemon_a = _apply_evolution_display(
                pokemon_a,
                decisions["evolved_species_b"],
                decisions.get("evolved_name_b"),
                generation=decisions.get("evolved_generation_b"),
                native_species_id=decisions.get("evolved_native_species_b"),
                consume_item=bool(decisions.get("evolved_consumed_item_b")),
            )

        # Aplica moves resolvidos à direita (pokemon_b, vai para save A)
        pokemon_b = _apply_moves_display(
            pokemon_b,
            decisions.get("resolved_moves_to_a"),
            decisions.get("resolved_moves_names_to_a"),
        )

        # Aplica moves resolvidos à esquerda (pokemon_a, vai para save B)
        pokemon_a = _apply_moves_display(
            pokemon_a,
            decisions.get("resolved_moves_to_b"),
            decisions.get("resolved_moves_names_to_b"),
        )

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
            session.result_data = {}
            session.trade_status = "Troca cancelada. Escolha outro Pokemon."
            services.restore_selection_context(
                session.trade_return_context,
                "trade_confirm_no",
                fallback_screen="select_pokemon",
            )

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

    def _preview_context(self, session, state):
        pending_decision = session.self_trade_pending_decision or ""
        decisions = session.self_trade_decisions or {}
        ctx_data = session.self_trade_context if isinstance(session.self_trade_context, dict) else {}
        target_generation = 0
        target_game = ""
        resolved_name_overrides = {}

        if "moves_to_a" in pending_decision:
            pokemon = dict(ctx_data.get("payload_b") or session.self_trade_pokemon_b or {})
            preflight = ctx_data.get("preflight_to_a") if isinstance(ctx_data.get("preflight_to_a"), dict) else {}
            evolution = ctx_data.get("trade_evolution_to_a") if isinstance(ctx_data.get("trade_evolution_to_a"), dict) else {}
            if not evolution:
                evolution = preflight.get("trade_evolution") if isinstance(preflight, dict) else {}
            target_generation = _as_int(preflight.get("target_generation") if isinstance(preflight, dict) else 0)
            target_game = str(preflight.get("target_game") or "")
            if decisions.get("evolved_species_a") and not decisions.get("cancel_evolution_to_a"):
                pokemon = _apply_evolution_display(
                    pokemon,
                    decisions.get("evolved_species_a"),
                    decisions.get("evolved_name_a"),
                    generation=decisions.get("evolved_generation_a"),
                    native_species_id=decisions.get("evolved_native_species_a"),
                    consume_item=bool(decisions.get("evolved_consumed_item_a")),
                )
            else:
                pokemon = _apply_evolution_display_from_payload(
                    pokemon,
                    evolution,
                    bool(decisions.get("cancel_evolution_to_a")),
                )
            resolved_name_overrides = dict(decisions.get("resolved_moves_names_to_a") or {})
        elif "moves_to_b" in pending_decision:
            pokemon = dict(ctx_data.get("payload_a") or session.self_trade_pokemon_a or {})
            preflight = ctx_data.get("preflight_to_b") if isinstance(ctx_data.get("preflight_to_b"), dict) else {}
            evolution = ctx_data.get("trade_evolution_to_b") if isinstance(ctx_data.get("trade_evolution_to_b"), dict) else {}
            if not evolution:
                evolution = preflight.get("trade_evolution") if isinstance(preflight, dict) else {}
            target_generation = _as_int(preflight.get("target_generation") if isinstance(preflight, dict) else 0)
            target_game = str(preflight.get("target_game") or "")
            if decisions.get("evolved_species_b") and not decisions.get("cancel_evolution_to_b"):
                pokemon = _apply_evolution_display(
                    pokemon,
                    decisions.get("evolved_species_b"),
                    decisions.get("evolved_name_b"),
                    generation=decisions.get("evolved_generation_b"),
                    native_species_id=decisions.get("evolved_native_species_b"),
                    consume_item=bool(decisions.get("evolved_consumed_item_b")),
                )
            else:
                pokemon = _apply_evolution_display_from_payload(
                    pokemon,
                    evolution,
                    bool(decisions.get("cancel_evolution_to_b")),
                )
            resolved_name_overrides = dict(decisions.get("resolved_moves_names_to_b") or {})
        else:
            pokemon = dict(session.pending_removed_moves_pokemon or state.selected_pokemon or {})
            target_generation = _as_int(session.pending_removed_moves_target_generation)
            if not target_generation and session.pending_removed_moves:
                target_generation = _as_int(session.pending_removed_moves[0].get("target_generation"))
            target_game = str(session.pending_removed_moves_target_game or "")
            if not target_game and session.pending_removed_moves:
                target_game = str(session.pending_removed_moves[0].get("target_game") or "")
            pokemon = _apply_evolution_display_from_payload(
                pokemon,
                session.pending_removed_moves_trade_evolution,
                bool(session.pending_removed_moves_cancel_evolution),
            )

        moves = _rebuild_removed_moves_for_preview(session.pending_removed_moves, pokemon, target_generation, target_game)
        pokemon = _apply_moves_display(
            pokemon,
            session.resolved_moves_choices,
            _resolved_move_names_for_preview(
                moves,
                session.resolved_moves_choices,
                resolved_name_overrides,
            ),
        )
        return pokemon, moves

    def _clear_pending(self, session):
        session.pending_removed_moves = []
        session.pending_removed_moves_pokemon = {}
        session.pending_removed_moves_target_generation = 0
        session.pending_removed_moves_target_game = ""
        session.pending_removed_moves_trade_evolution = {}
        session.pending_removed_moves_cancel_evolution = False

    def handle_action(self, action, ctx, session, state, services):
        if not action or not session.pending_removed_moves:
            return
        _, preview_moves = self._preview_context(session, state)
        if not preview_moves:
            return
        session.resolve_current_idx = min(session.resolve_current_idx, len(preview_moves) - 1)
        current_move = preview_moves[session.resolve_current_idx]
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
        elif action == "select":
            if action == "select" and session.resolve_replacement_idx < len(replacements):
                move_id = int(current_move.get("move_id") or 0)
                replacement_id = int(replacements[session.resolve_replacement_idx].get("move_id") or 0)
                if move_id and replacement_id:
                    session.resolved_moves_choices[move_id] = replacement_id
                    # Guardar nome do move substituto para a tela de confirmação
                    pending = session.self_trade_pending_decision or ""
                    if pending in ("resolved_moves_to_a", "resolved_moves_to_b") or "moves_to_" in pending:
                        names_key = "resolved_moves_names_to_a" if "moves_to_a" in pending else "resolved_moves_names_to_b"
                        if names_key not in session.self_trade_decisions:
                            session.self_trade_decisions[names_key] = {}
                        session.self_trade_decisions[names_key][move_id] = (
                            replacements[session.resolve_replacement_idx].get("name") or f"Move #{replacement_id}"
                        )
            session.resolve_current_idx += 1
            session.resolve_replacement_idx = 0
            if session.resolve_current_idx >= len(preview_moves):
                ctx.logger.info("Move resolution complete: %s", session.resolved_moves_choices)
                if session.self_trade_pending_decision in ("resolved_moves_to_a", "resolved_moves_to_b"):
                    session.self_trade_decisions[session.self_trade_pending_decision] = dict(session.resolved_moves_choices)
                    session.self_trade_pending_decision = ""
                    self._clear_pending(session)
                    services.advance_self_trade_prompts()
                else:
                    services.confirm_queue.put(dict(session.resolved_moves_choices))
                    self._clear_pending(session)
        elif action == "back":
            ctx.logger.info("Move resolution cancelled by user")
            pending_decision = str(session.self_trade_pending_decision or "")
            session.resolved_moves_choices = {}
            self._clear_pending(session)
            if pending_decision in ("resolved_moves_to_a", "resolved_moves_to_b"):
                session.self_trade_pending_decision = ""
                session.self_trade_context = {}
                session.self_trade_decisions = default_self_trade_decisions()
                services.restore_selection_context(
                    session.prompt_return_context,
                    "resolve_moves_back",
                    fallback_screen="self_select_pokemon_b" if pending_decision == "resolved_moves_to_a" else "self_select_pokemon_a",
                )
                session.prompt_return_context = {}
                return
            session.self_trade_pending_decision = ""
            state.selected_pokemon = None
            services.request_trade_cancel(state)
            session.trade_status = "Troca cancelada. Escolha outro Pokemon."
            services.restore_selection_context(
                session.prompt_return_context,
                "resolve_moves_back",
                fallback_screen="select_pokemon",
            )
            session.prompt_return_context = {}

    def render(self, ctx, session, state, services):
        if not session.pending_removed_moves:
            return
        pokemon, preview_moves = self._preview_context(session, state)
        if not preview_moves:
            return
        session.resolve_current_idx = min(session.resolve_current_idx, len(preview_moves) - 1)
        ctx.draw.draw_resolve_moves(
            ctx.screen,
            ctx.fonts,
            preview_moves[session.resolve_current_idx],
            session.resolve_replacement_idx,
            session.resolve_current_idx,
            len(preview_moves),
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
                services.restore_selection_context(
                    session.prompt_return_context,
                    "item_relocation_back_to_a",
                    fallback_screen="self_select_pokemon_a",
                )
                session.prompt_return_context = {}
                return
            if pending_decision == "item_relocation_choice_to_b":
                session.trade_status = "Troca local cancelada. Escolha outro Pokemon."
                session.self_trade_context = {}
                session.self_trade_pokemon_b = None
                session.self_trade_decisions = default_self_trade_decisions()
                services.restore_selection_context(
                    session.prompt_return_context,
                    "item_relocation_back_to_b",
                    fallback_screen="self_select_pokemon_b",
                )
                session.prompt_return_context = {}
                return
            state.selected_pokemon = None
            services.request_trade_cancel(state)
            session.trade_status = "Troca cancelada. Escolha outro Pokemon."
            services.restore_selection_context(
                session.prompt_return_context,
                "item_relocation_back",
                fallback_screen="select_pokemon",
            )
            session.prompt_return_context = {}

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
                _store_accepted_self_trade_evolution(session)
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

        # Extrair pokemon_data do contexto da sessão
        pokemon_data = None
        ctx_data = session.self_trade_context if isinstance(session.self_trade_context, dict) else {}
        pending = session.self_trade_pending_decision

        if pending == "cancel_evolution_to_a":
            pokemon_data = ctx_data.get("payload_b")
        elif pending == "cancel_evolution_to_b":
            pokemon_data = ctx_data.get("payload_a")

        ctx.draw.draw_evolution_cancel_prompt(
            ctx.screen,
            ctx.fonts,
            session.result_data if isinstance(session.result_data, dict) else {},
            ctx.sprite_loader,
            anim_frame,
            state.language,
            pokemon_data=pokemon_data,
        )


class EvolutionCancelConfirmScreen(ScreenBase):
    screen_id = "evolution_cancel_confirm"

    def handle_action(self, action, ctx, session, state, services):
        if action == "select":
            ctx.logger.info("Evolution cancellation rejected (A = let evolve)")
            if session.self_trade_pending_decision in ("cancel_evolution_to_a", "cancel_evolution_to_b"):
                session.self_trade_decisions[session.self_trade_pending_decision] = False
                _store_accepted_self_trade_evolution(session)
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
        # Extrair pokemon_data do contexto da sessão
        pokemon_data = None
        ctx_data = session.self_trade_context if isinstance(session.self_trade_context, dict) else {}
        pending = session.self_trade_pending_decision

        if pending == "cancel_evolution_to_a":
            pokemon_data = ctx_data.get("payload_b")
        elif pending == "cancel_evolution_to_b":
            pokemon_data = ctx_data.get("payload_a")

        ctx.draw.draw_evolution_cancel_confirm(
            ctx.screen,
            ctx.fonts,
            session.result_data if isinstance(session.result_data, dict) else {},
            ctx.sprite_loader,
            session.frame,
            state.language,
            pokemon_data=pokemon_data,
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
