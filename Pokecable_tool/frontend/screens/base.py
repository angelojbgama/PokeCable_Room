from __future__ import annotations


class ScreenBase:
    screen_id = ""

    def handle_action(self, action, ctx, session, state, services):
        return None

    def render(self, ctx, session, state, services):
        return None


def show_info_modal(session, services, *, title, message, return_screen, reason):
    session.info_modal_data = {
        "title": title,
        "message": message,
        "return_screen": return_screen,
    }
    services.switch_screen("info_modal", reason)
