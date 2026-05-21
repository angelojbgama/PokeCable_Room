from __future__ import annotations

import queue


def dispatch_ui_queue(session, services, logger):
    try:
        while True:
            msg_type, payload = services.ui_queue.get_nowait()
            if msg_type == "status":
                session.trade_status = payload
                logger.info("QUEUE status: %s", payload)
            elif msg_type == "screen":
                logger.info("QUEUE screen: %s", payload)
                services.switch_screen(payload, "ui_queue")
            elif msg_type == "confirm_prompt":
                session.result_data = payload if isinstance(payload, dict) else {}
                logger.info("QUEUE confirm_prompt: %s", session.result_data)
                services.switch_screen("trade_confirm", "confirm_prompt")
            elif msg_type == "info_modal":
                data = payload if isinstance(payload, dict) else {}
                session.reset_info_modal()
                session.info_modal_data.update({"title": data.get("title", ""), "message": data.get("message", "")})
                logger.info("QUEUE info_modal: %s", session.info_modal_data)
                services.switch_screen("info_modal", "info_modal_prompt")
            elif msg_type == "resolve_moves_prompt":
                data = payload if isinstance(payload, dict) else {}
                session.pending_removed_moves = list(data.get("removed_moves") or [])
                session.resolve_current_idx = 0
                session.resolve_replacement_idx = 0
                session.resolved_moves_choices = {}
                logger.info("QUEUE resolve_moves_prompt: %s moves", len(session.pending_removed_moves))
                if session.pending_removed_moves:
                    services.switch_screen("resolve_moves", "resolve_moves_prompt")
                else:
                    services.confirm_queue.put({})
            elif msg_type == "evolution_cancel_prompt":
                session.result_data = payload if isinstance(payload, dict) else {}
                logger.info("QUEUE evolution_cancel_prompt: %s", session.result_data)
                session.evolution_anim_start = session.frame
                services.switch_screen("evolution_cancel_prompt", "evolution_cancel_prompt")
            elif msg_type == "result":
                session.result_data = payload if isinstance(payload, dict) else {"success": True}
                logger.info("QUEUE result: %s", session.result_data)
                services.switch_screen("trade_result", "result")
            elif msg_type == "error":
                session.trade_status = f"Erro: {payload}"
                session.result_data = {"success": False, "error": payload}
                logger.error("QUEUE error: %s", payload)
                services.switch_screen("trade_result", "error")
    except queue.Empty:
        pass
