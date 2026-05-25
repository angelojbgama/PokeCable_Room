from __future__ import annotations

import time

import pygame


AXIS_X = 0
AXIS_Y = 1
AXIS_THRESHOLD = 0.7
ACTION_DEBOUNCE = 0.05
QUIT_COMBO_WINDOW = 0.35
JOY_BUTTON_START = 13
JOY_BUTTON_SELECT = 12

JOY_MAP = {
    "select": {1},
    "back": {0},
    "x": {2},
    "y": {3},
    "up": {8},
    "down": {9},
    "left": {10},
    "right": {11},
}

_PROFILE_RG35XX_KNULLI = {
    "joy_map": {
        "select": {3},
        "back": {4},
        "x": {6},
        "y": {5},
        "up": set(),
        "down": set(),
        "left": set(),
        "right": set(),
    },
    "start": 10,
    "select_btn": 9,
}

_DEVICE_PROFILES = {
    "deeplay": _PROFILE_RG35XX_KNULLI,
    "rg35xx_knulli": _PROFILE_RG35XX_KNULLI,
}


def apply_detected_profile(joystick_names, override=None):
    global JOY_BUTTON_START, JOY_BUTTON_SELECT
    key = override
    if not key:
        for name in joystick_names:
            name_lower = name.lower()
            for profile_key in _DEVICE_PROFILES:
                if profile_key in name_lower:
                    key = profile_key
                    break
            if key:
                break
    if not key or key not in _DEVICE_PROFILES:
        return None
    profile = _DEVICE_PROFILES[key]
    JOY_MAP.clear()
    JOY_MAP.update({k: set(v) for k, v in profile["joy_map"].items()})
    JOY_BUTTON_START = profile["start"]
    JOY_BUTTON_SELECT = profile["select_btn"]
    return key


def translate_joy_button(button_id):
    for action, ids in JOY_MAP.items():
        if button_id in ids:
            return action
    return None


def translate_key(key):
    if key in (pygame.K_UP, pygame.K_w):
        return "up"
    if key in (pygame.K_DOWN, pygame.K_s):
        return "down"
    if key in (pygame.K_LEFT, pygame.K_a):
        return "left"
    if key in (pygame.K_RIGHT, pygame.K_d):
        return "right"
    if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        return "select"
    if key in (pygame.K_BACKSPACE, pygame.K_ESCAPE):
        return "back"
    if key == pygame.K_x:
        return "x"
    if key == pygame.K_y:
        return "y"
    return None


def event_to_action(event, axis_state, combo_state, logger):
    if event.type == pygame.KEYDOWN:
        logger.debug("KEYDOWN: key=%s name=%s", event.key, pygame.key.name(event.key))
        return translate_key(event.key)

    if event.type == pygame.JOYBUTTONDOWN:
        logger.debug("JOYBUTTONDOWN: %s", event.button)
        now = time.monotonic()
        combo_state["pressed"].add(event.button)
        combo_state["last_down"][event.button] = now
        if event.button in (JOY_BUTTON_START, JOY_BUTTON_SELECT):
            other = JOY_BUTTON_SELECT if event.button == JOY_BUTTON_START else JOY_BUTTON_START
            other_down = combo_state["last_down"].get(other, 0.0)
            if other in combo_state["pressed"] or (other_down and now - other_down <= QUIT_COMBO_WINDOW):
                logger.info("Quit combo detected: start+select")
                combo_state["pressed"].discard(JOY_BUTTON_START)
                combo_state["pressed"].discard(JOY_BUTTON_SELECT)
                combo_state["suppress_until"] = now + QUIT_COMBO_WINDOW
                return "quit_system"
            if now < combo_state.get("suppress_until", 0.0):
                return None
        return translate_joy_button(event.button)

    if event.type == pygame.JOYBUTTONUP:
        logger.debug("JOYBUTTONUP: %s", event.button)
        combo_state["pressed"].discard(event.button)
        return None

    if event.type == pygame.JOYHATMOTION:
        logger.debug("JOYHATMOTION: %s", event.value)
        hat_x, hat_y = event.value
        if hat_y > 0:
            return "up"
        if hat_y < 0:
            return "down"
        if hat_x < 0:
            return "left"
        if hat_x > 0:
            return "right"
        return None

    if event.type == pygame.JOYAXISMOTION:
        logger.debug("JOYAXISMOTION: axis=%s value=%.2f", event.axis, event.value)
        prev = axis_state.get(event.axis, 0.0)
        axis_state[event.axis] = event.value
        if event.axis == AXIS_Y:
            if event.value <= -AXIS_THRESHOLD and prev > -AXIS_THRESHOLD:
                return "up"
            if event.value >= AXIS_THRESHOLD and prev < AXIS_THRESHOLD:
                return "down"
        if event.axis == AXIS_X:
            if event.value <= -AXIS_THRESHOLD and prev > -AXIS_THRESHOLD:
                return "left"
            if event.value >= AXIS_THRESHOLD and prev < AXIS_THRESHOLD:
                return "right"
    return None


def debounce_action(action, action_state):
    if not action:
        return None
    now = time.monotonic()
    if action_state["last_action"] == action and now - action_state["last_time"] < ACTION_DEBOUNCE:
        return None
    action_state["last_action"] = action
    action_state["last_time"] = now
    return action

