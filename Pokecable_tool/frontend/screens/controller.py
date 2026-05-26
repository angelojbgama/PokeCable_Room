from __future__ import annotations

import time

from frontend.session import NavigationEntry
from frontend.screens.menu import (
    ConfigScreen,
    InfosReaderScreen,
    InfosTopicsScreen,
    LoadSaveScreen,
    MenuScreen,
    SelfSelectSaveAScreen,
    SelfSelectSaveBScreen,
    UpdateScreen,
    ExtrasSelectSaveScreen,
    ExtrasCategoryScreen,
    ExtrasEventsScreen,
    ExtrasUtilitiesScreen,
    ExtrasEreaderScreen,
    ExtrasResultScreen,
    ExtrasItemCategoryScreen,
    ExtrasItemSelectScreen,
)
from frontend.screens.selection import (
    EnterLanEndpointScreen,
    SelectPokemonScreen,
    SelfSelectPokemonAScreen,
    SelfSelectPokemonBScreen,
)
from frontend.screens.trade import (
    CancelWaitingConfirmScreen,
    ConnectingScreen,
    DepositConfirmScreen,
    EvolutionCancelConfirmScreen,
    EvolutionCancelPromptScreen,
    InfoModalScreen,
    LeaveRoomConfirmScreen,
    ResolveItemRelocationScreen,
    ResolveMovesScreen,
    SelfTradeConfirmScreen,
    TradeConfirmScreen,
    TradeResultScreen,
    TradingScreen,
    WaitingPartnerScreen,
    WithdrawConfirmScreen,
)


class ScreenController:
    NON_HISTORIC_SCREENS = {
        "connecting",
        "trading",
        "trade_result",
        "trade_confirm",
        "self_trade_confirm",
        "info_modal",
        "resolve_moves",
        "resolve_item_relocation",
        "evolution_cancel_prompt",
        "evolution_cancel_confirm",
        "withdraw_confirm",
        "deposit_confirm",
        "leave_room_confirm",
    }

    def __init__(self, session, input_state, logger, transition_guard_seconds):
        self.session = session
        self.input_state = input_state
        self.logger = logger
        self.transition_guard_seconds = transition_guard_seconds
        self.screens = {}

    def register(self, screen):
        self.screens[screen.screen_id] = screen

    def _snapshot_current(self):
        return NavigationEntry(
            screen_id=str(self.session.current_screen or ""),
            menu_index=int(self.session.menu_index or 0),
            keyboard_index=int(self.session.keyboard_index or 0),
            keyboard_shift=bool(self.session.keyboard_shift),
            infos_scroll=int(self.session.infos_scroll or 0),
            infos_topic_key=str(self.session.infos_topic_key or "retrocompat"),
            item_relocation_index=int(self.session.item_relocation_index or 0),
            resolve_current_idx=int(self.session.resolve_current_idx or 0),
            resolve_replacement_idx=int(self.session.resolve_replacement_idx or 0),
        )

    def _restore_snapshot(self, entry):
        self.session.current_screen = str(entry.screen_id or "menu")
        self.session.menu_index = int(entry.menu_index or 0)
        self.session.keyboard_index = int(entry.keyboard_index or 0)
        self.session.keyboard_shift = bool(entry.keyboard_shift)
        self.session.infos_scroll = int(entry.infos_scroll or 0)
        self.session.infos_topic_key = str(entry.infos_topic_key or "retrocompat")
        self.session.item_relocation_index = int(entry.item_relocation_index or 0)
        self.session.resolve_current_idx = int(entry.resolve_current_idx or 0)
        self.session.resolve_replacement_idx = int(entry.resolve_replacement_idx or 0)

    def switch_screen(self, new_screen, reason, nav_mode="auto"):
        current_screen = str(self.session.current_screen or "")
        if nav_mode == "auto":
            if current_screen in self.NON_HISTORIC_SCREENS or str(new_screen or "") in self.NON_HISTORIC_SCREENS:
                nav_mode = "replace"
            else:
                nav_mode = "push"
        if self.session.current_screen != new_screen:
            self.logger.info("SCREEN %s -> %s (%s)", self.session.current_screen, new_screen, reason)
            if nav_mode == "clear":
                self.session.navigation_history = []
            elif nav_mode == "push" and current_screen:
                entry = self._snapshot_current()
                history = self.session.navigation_history
                if not history or history[-1] != entry:
                    history.append(entry)
            self.input_state.blocked_input_actions.update(self.input_state.pressed_input_actions.keys())
            self.input_state.input_guard_until = max(
                self.input_state.input_guard_until,
                time.monotonic() + self.transition_guard_seconds,
            )
            self.input_state.nav_hold["direction"] = None
            self.input_state.nav_hold["started"] = 0.0
            self.input_state.nav_hold["last_fire"] = 0.0
            self.input_state.action_state["last_action"] = None
            self.input_state.action_state["last_time"] = 0.0
        self.session.current_screen = new_screen

    def go_back(self, fallback_screen, reason):
        while self.session.navigation_history:
            entry = self.session.navigation_history.pop()
            if str(entry.screen_id or "") in self.NON_HISTORIC_SCREENS:
                continue
            self.logger.info("SCREEN %s -> %s (%s)", self.session.current_screen, entry.screen_id, reason)
            self.input_state.blocked_input_actions.update(self.input_state.pressed_input_actions.keys())
            self.input_state.input_guard_until = max(
                self.input_state.input_guard_until,
                time.monotonic() + self.transition_guard_seconds,
            )
            self.input_state.nav_hold["direction"] = None
            self.input_state.nav_hold["started"] = 0.0
            self.input_state.nav_hold["last_fire"] = 0.0
            self.input_state.action_state["last_action"] = None
            self.input_state.action_state["last_time"] = 0.0
            self._restore_snapshot(entry)
            return
        self.switch_screen(fallback_screen, reason, nav_mode="replace")

    def handle_current_action(self, action, ctx, state, services):
        screen = self.screens.get(self.session.current_screen)
        if screen:
            screen.handle_action(action, ctx, self.session, state, services)

    def render_current(self, ctx, state, services):
        screen = self.screens.get(self.session.current_screen)
        if screen:
            screen.render(ctx, self.session, state, services)


def register_default_screens(controller):
    for screen in (
        MenuScreen(),
        ConfigScreen(),
        UpdateScreen(),
        InfosTopicsScreen(),
        InfosReaderScreen(),
        LoadSaveScreen(),
        SelfSelectSaveAScreen(),
        SelfSelectSaveBScreen(),
        SelfSelectPokemonAScreen(),
        SelfSelectPokemonBScreen(),
        SelectPokemonScreen(),
        EnterLanEndpointScreen(),
        ConnectingScreen(),
        WaitingPartnerScreen(),
        CancelWaitingConfirmScreen(),
        LeaveRoomConfirmScreen(),
        SelfTradeConfirmScreen(),
        TradeConfirmScreen(),
        InfoModalScreen(),
        ResolveItemRelocationScreen(),
        ResolveMovesScreen(),
        EvolutionCancelPromptScreen(),
        EvolutionCancelConfirmScreen(),
        WithdrawConfirmScreen(),
        DepositConfirmScreen(),
        TradingScreen(),
        TradeResultScreen(),
        ExtrasSelectSaveScreen(),
        ExtrasCategoryScreen(),
        ExtrasEventsScreen(),
        ExtrasUtilitiesScreen(),
        ExtrasEreaderScreen(),
        ExtrasResultScreen(),
        ExtrasItemCategoryScreen(),
        ExtrasItemSelectScreen(),
    ):
        controller.register(screen)
    return controller
