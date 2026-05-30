from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from frontend.paths import CONFIG_DIR


logger = logging.getLogger("pokecable.input_mapping")

DEFAULT_ACTIONS = ("select", "back", "x", "y", "up", "down", "left", "right")
DEFAULT_START_BUTTON = 13
DEFAULT_SELECT_BUTTON = 12

DEFAULT_BUTTON_MAP = {
    "select": {1},
    "back": {0},
    "x": {2},
    "y": {3},
    "up": {8},
    "down": {9},
    "left": {10},
    "right": {11},
}

DEFAULT_PROFILE_PATH = CONFIG_DIR / "device_profiles.json"
DEFAULT_USER_MAP_PATH = CONFIG_DIR / "input_map.json"


@dataclass
class InputMapping:
    button_map: dict[str, set[int]] = field(default_factory=lambda: {k: set(v) for k, v in DEFAULT_BUTTON_MAP.items()})
    start_button: int = DEFAULT_START_BUTTON
    select_button: int = DEFAULT_SELECT_BUTTON
    profile_name: str = "default"
    device_name: str = ""

    def apply_profile(self, profile: dict[str, Any], device_name: str = "") -> None:
        actions = profile.get("actions") if isinstance(profile.get("actions"), dict) else {}
        button_map: dict[str, set[int]] = {action: set() for action in DEFAULT_ACTIONS}
        for action in DEFAULT_ACTIONS:
            entries = actions.get(action, [])
            if isinstance(entries, dict):
                entries = [entries]
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("type") != "button":
                    continue
                try:
                    button_map[action].add(int(entry.get("id")))
                except (TypeError, ValueError):
                    continue
        for action in DEFAULT_ACTIONS:
            if not button_map[action]:
                button_map[action] = set(DEFAULT_BUTTON_MAP.get(action, set()))
        self.button_map = button_map
        self.start_button = _int_value(profile.get("start_button"), DEFAULT_START_BUTTON)
        self.select_button = _int_value(profile.get("select_button"), DEFAULT_SELECT_BUTTON)
        self.profile_name = str(profile.get("name") or "custom")
        self.device_name = device_name

    def translate_button(self, button_id: int) -> str | None:
        for action, ids in self.button_map.items():
            if int(button_id) in ids:
                return action
        return None


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            logger.warning("Ignoring JSON config with invalid root type: %s", path)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to read JSON config %s: %s", path, exc)
        return {}
    return {}


def _profile_matches(profile: dict[str, Any], joystick_names: list[str]) -> bool:
    matches = profile.get("match") or []
    if isinstance(matches, str):
        matches = [matches]
    match_terms = [str(item).lower() for item in matches if str(item).strip()]
    if not match_terms:
        return False
    for name in joystick_names:
        name_lower = str(name or "").lower()
        if any(term in name_lower for term in match_terms):
            return True
    return False


def ensure_default_profiles(path: Path = DEFAULT_PROFILE_PATH) -> None:
    if path.exists():
        logger.info("Device profile file found: %s", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "profiles": [
            {
                "name": "r36s_default",
                "match": ["r36s", "rk3326", "gamepad"],
                "start_button": 13,
                "select_button": 12,
                "actions": _actions_from_button_map(DEFAULT_BUTTON_MAP),
            },
            {
                "name": "rg35xx_knulli_deeplay",
                "match": ["deeplay", "rg35xx", "knulli"],
                "start_button": 10,
                "select_button": 9,
                "actions": _actions_from_button_map(
                    {
                        "select": {3},
                        "back": {4},
                        "x": {6},
                        "y": {5},
                        "up": set(),
                        "down": set(),
                        "left": set(),
                        "right": set(),
                    }
                ),
            },
        ]
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    logger.info("Created default device profile file: %s", path)


def _actions_from_button_map(button_map: dict[str, set[int]]) -> dict[str, list[dict[str, int | str]]]:
    actions: dict[str, list[dict[str, int | str]]] = {}
    for action, ids in button_map.items():
        actions[action] = [{"type": "button", "id": int(button_id)} for button_id in sorted(ids)]
    return actions


def load_input_mapping(joystick_names: list[str], override: str | None = None) -> InputMapping:
    ensure_default_profiles()
    mapping = InputMapping()
    logger.info("Input mapping load start: joysticks=%s override=%s", joystick_names, override or "")

    user_map_path = Path(os.getenv("POKECABLE_INPUT_MAP", str(DEFAULT_USER_MAP_PATH)))
    user_profile = _read_json(user_map_path)
    if user_profile:
        mapping.apply_profile(user_profile, joystick_names[0] if joystick_names else "")
        logger.info(
            "Input mapping source=user file=%s profile=%s device=%s map=%s start=%s select=%s",
            user_map_path,
            mapping.profile_name,
            mapping.device_name,
            {action: sorted(ids) for action, ids in mapping.button_map.items()},
            mapping.start_button,
            mapping.select_button,
        )
        return mapping

    profile_path = Path(os.getenv("POKECABLE_DEVICE_PROFILES", str(DEFAULT_PROFILE_PATH)))
    profiles_payload = _read_json(profile_path)
    profiles = profiles_payload.get("profiles") if isinstance(profiles_payload.get("profiles"), list) else []
    selected: dict[str, Any] | None = None
    if override:
        for profile in profiles:
            if isinstance(profile, dict) and str(profile.get("name") or "").lower() == override.lower():
                selected = profile
                break
    if selected is None:
        for profile in profiles:
            if isinstance(profile, dict) and _profile_matches(profile, joystick_names):
                selected = profile
                break
    if selected:
        mapping.apply_profile(selected, joystick_names[0] if joystick_names else "")
        logger.info(
            "Input mapping source=profile file=%s profile=%s device=%s map=%s start=%s select=%s",
            profile_path,
            mapping.profile_name,
            mapping.device_name,
            {action: sorted(ids) for action, ids in mapping.button_map.items()},
            mapping.start_button,
            mapping.select_button,
        )
    else:
        logger.warning(
            "Input mapping source=default reason=no_profile_match file=%s joysticks=%s map=%s start=%s select=%s",
            profile_path,
            joystick_names,
            {action: sorted(ids) for action, ids in mapping.button_map.items()},
            mapping.start_button,
            mapping.select_button,
        )
    return mapping


def save_calibrated_mapping(profile: dict[str, Any], path: Path = DEFAULT_USER_MAP_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    logger.info("Saved calibrated input mapping: %s", path)
