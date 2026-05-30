from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


def default_info_modal():
    return {"title": "", "message": ""}


def default_self_trade_decisions():
    return {
        "cancel_evolution_to_a": False,
        "cancel_evolution_to_b": False,
        "item_relocation_choice_to_a": "",
        "item_relocation_choice_to_b": "",
        "resolved_moves_to_a": {},
        "resolved_moves_to_b": {},
        "evolved_species_a": 0,
        "evolved_species_b": 0,
        "evolved_native_species_a": 0,
        "evolved_native_species_b": 0,
        "evolved_generation_a": 0,
        "evolved_generation_b": 0,
        "evolved_name_a": "",
        "evolved_name_b": "",
        "evolved_consumed_item_a": False,
        "evolved_consumed_item_b": False,
        "_evolution_to_a_done": False,
        "_evolution_to_b_done": False,
        "_item_to_a_done": False,
        "_item_to_b_done": False,
        "_moves_to_a_done": False,
        "_moves_to_b_done": False,
    }


@dataclass
class MutableRef:
    current: Any = None


@dataclass
class NavigationEntry:
    screen_id: str
    menu_index: int = 0
    keyboard_index: int = 0
    keyboard_shift: bool = False
    infos_scroll: int = 0
    infos_topic_key: str = "retrocompat"
    item_relocation_index: int = 0
    resolve_current_idx: int = 0
    resolve_replacement_idx: int = 0


@dataclass
class UiSessionState:
    current_screen: str = "menu"
    navigation_history: list[NavigationEntry] = field(default_factory=list)
    trade_return_context: dict[str, Any] = field(default_factory=dict)
    self_trade_return_context: dict[str, Any] = field(default_factory=dict)
    prompt_return_context: dict[str, Any] = field(default_factory=dict)
    menu_index: int = 0
    config_dirty: bool = False
    keyboard_index: int = 0
    keyboard_shift: bool = False
    room_name: str = ""
    room_password: str = ""
    lan_endpoint: str = ""
    frame: int = 0
    running: bool = True
    trade_status: str = ""
    result_data: dict[str, Any] = field(default_factory=dict)
    pending_removed_moves: list[dict[str, Any]] = field(default_factory=list)
    pending_removed_moves_pokemon: dict[str, Any] = field(default_factory=dict)
    pending_removed_moves_target_generation: int = 0
    pending_removed_moves_target_game: str = ""
    pending_removed_moves_trade_evolution: dict[str, Any] = field(default_factory=dict)
    pending_removed_moves_cancel_evolution: bool = False
    pending_item_relocation: dict[str, Any] = field(default_factory=dict)
    pending_item_relocation_pokemon: dict[str, Any] = field(default_factory=dict)
    resolve_current_idx: int = 0
    resolve_replacement_idx: int = 0
    item_relocation_index: int = 0
    resolved_moves_choices: dict[int, int] = field(default_factory=dict)
    info_modal_data: dict[str, Any] = field(default_factory=default_info_modal)
    pending_deposit_idx: int = -1
    pending_withdraw_pokemon: dict[str, Any] | None = None
    pending_pc_return_screen: str = "select_pokemon"
    evolution_anim_start: int | None = None
    self_trade_save_a: Any = None
    self_trade_save_b: Any = None
    self_trade_pokemon_a: dict[str, Any] | None = None
    self_trade_pokemon_b: dict[str, Any] | None = None
    self_trade_context: dict[str, Any] = field(default_factory=dict)
    self_trade_pending_decision: str = ""
    self_trade_decisions: dict[str, Any] = field(default_factory=default_self_trade_decisions)
    infos_topic_key: str = "retrocompat"
    infos_scroll: int = 0
    update_status: str = ""
    update_data: dict[str, Any] = field(default_factory=dict)
    extras_save_path: str = ""
    extras_events: list[dict[str, Any]] = field(default_factory=list)
    extras_utilities: list[dict[str, Any]] = field(default_factory=list)
    extras_event_index: int = 0
    extras_utility_index: int = 0
    extras_category: str = ""
    extras_result: dict[str, Any] = field(default_factory=dict)
    extras_ereader_slots: list[dict[str, Any]] = field(default_factory=list)
    extras_ereader_index: int = 0
    extras_ereader_slot_index: int = 0
    extras_events_scroll: float = 0.0
    extras_utilities_scroll: float = 0.0
    extras_ereader_scroll: float = 0.0
    extras_applied_ids: set = field(default_factory=set)
    extras_utilities_active: set = field(default_factory=set)
    extras_utilities_reversible: set = field(default_factory=set)
    extras_item_groups: list = field(default_factory=list)  # [(bucket_key, [(item_id, name), ...]), ...]
    extras_item_bucket_index: int = 0
    extras_item_index: int = 0
    extras_item_qty: int = 1
    extras_item_max_stack: int = 99

    def reset_info_modal(self) -> None:
        self.info_modal_data = default_info_modal()

    def reset_self_trade(self) -> None:
        self.navigation_history = []
        self.trade_return_context = {}
        self.self_trade_return_context = {}
        self.prompt_return_context = {}
        self.self_trade_save_a = None
        self.self_trade_save_b = None
        self.self_trade_pokemon_a = None
        self.self_trade_pokemon_b = None
        self.self_trade_context = {}
        self.self_trade_pending_decision = ""
        self.self_trade_decisions = default_self_trade_decisions()


@dataclass
class InputSessionState:
    axis_state: dict[Any, Any] = field(default_factory=dict)
    combo_state: dict[str, Any] = field(
        default_factory=lambda: {"pressed": set(), "last_down": {}, "suppress_until": 0.0}
    )
    action_state: dict[str, Any] = field(default_factory=lambda: {"last_action": None, "last_time": 0.0})
    nav_hold: dict[str, Any] = field(
        default_factory=lambda: {"direction": None, "started": 0.0, "last_fire": 0.0}
    )
    input_source_actions: dict[str, str] = field(default_factory=dict)
    pressed_input_actions: dict[str, set[str]] = field(default_factory=dict)
    blocked_input_actions: set[str] = field(default_factory=set)
    input_guard_until: float = 0.0


@dataclass
class UiContext:
    screen: Any
    fonts: Any
    state: Any
    sprite_loader: Any
    logger: Any
    draw: Any


@dataclass
class UiServices:
    ui_queue: Any
    confirm_queue: Any
    trade_thread_ref: MutableRef
    apply_theme: Callable[[str], None]
    reset_flow_state: Callable[[Any], None]
    reset_self_trade_state: Callable[[], None]
    same_save_path: Callable[[Any, Any], bool]
    load_self_trade_source: Callable[..., None]
    load_self_trade_party: Callable[..., None]
    self_trade_source_label: Callable[[int, Any], str]
    reload_after_pc_management: Callable[[str], None]
    advance_self_trade_prompts: Callable[[], None]
    finish_self_trade: Callable[[], None]
    keyboard_chars: Callable[[bool], list[str]]
    keyboard_limits: Callable[[bool], int]
    random_room_name: Callable[[], str]
    start_lan_trade_thread: Callable[..., Any]
    request_trade_cancel: Callable[[Any], bool]
    request_leave_room: Callable[[Any], None]
    create_backup: Callable[[Any], None]
    prepare_self_trade: Callable[..., Any]
    validate_self_trade_candidate: Callable[..., Any]
    execute_self_trade: Callable[..., Any]
    switch_screen: Callable[..., None]
    go_back: Callable[[str, str], None]
    capture_selection_context: Callable[..., dict[str, Any]]
    restore_selection_context: Callable[..., bool]
