from __future__ import annotations

import time

from frontend.screens.menu import (
    ConfigScreen,
    InfosReaderScreen,
    InfosTopicsScreen,
    LoadSaveScreen,
    MenuScreen,
    SelfSelectSaveAScreen,
    SelfSelectSaveBScreen,
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
    def __init__(self, session, input_state, logger, transition_guard_seconds):
        self.session = session
        self.input_state = input_state
        self.logger = logger
        self.transition_guard_seconds = transition_guard_seconds
        self.screens = {}

    def register(self, screen):
        self.screens[screen.screen_id] = screen

    def switch_screen(self, new_screen, reason):
        if self.session.current_screen != new_screen:
            self.logger.info("SCREEN %s -> %s (%s)", self.session.current_screen, new_screen, reason)
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
    ):
        controller.register(screen)
    return controller
