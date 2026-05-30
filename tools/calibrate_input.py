#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_ROOT = ROOT / "Pokecable_tool"
sys.path.insert(0, str(TOOL_ROOT))

import pygame  # noqa: E402
from frontend.input_mapping import save_calibrated_mapping  # noqa: E402


ACTIONS = [
    ("up", "CIMA"),
    ("down", "BAIXO"),
    ("left", "ESQUERDA"),
    ("right", "DIREITA"),
    ("select", "CONFIRMAR / A"),
    ("back", "VOLTAR / B"),
    ("x", "X / MENU"),
    ("y", "Y"),
]


def main() -> int:
    pygame.init()
    pygame.joystick.init()
    screen = pygame.display.set_mode((640, 220))
    pygame.display.set_caption("PokeCable input calibration")
    font = pygame.font.Font(None, 28)
    small = pygame.font.Font(None, 22)

    joysticks = []
    for index in range(pygame.joystick.get_count()):
        joy = pygame.joystick.Joystick(index)
        joy.init()
        joysticks.append(joy)

    if not joysticks:
        print("Nenhum joystick/gamepad detectado.")
        return 1

    mappings: dict[str, list[dict[str, int | str]]] = {}
    current = 0
    running = True

    while running and current < len(ACTIONS):
        action, label = ACTIONS[current]
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 1
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return 1
            if event.type == pygame.JOYBUTTONDOWN:
                mappings[action] = [{"type": "button", "id": int(event.button)}]
                print(f"{action}: button {event.button}")
                current += 1
            elif event.type == pygame.JOYHATMOTION and event.value != (0, 0):
                mappings[action] = [{"type": "hat", "id": int(getattr(event, "hat", 0)), "value": list(event.value)}]
                print(f"{action}: hat {getattr(event, 'hat', 0)} {event.value}")
                current += 1

        screen.fill((24, 28, 36))
        title = font.render(f"Pressione: {label}", True, (255, 255, 255))
        detail = small.render("ESC cancela. Use o controle que sera usado no dispositivo.", True, (190, 198, 210))
        device = small.render(f"Dispositivo: {joysticks[0].get_name()}", True, (190, 198, 210))
        progress = small.render(f"{current + 1}/{len(ACTIONS)}", True, (190, 198, 210))
        screen.blit(title, (24, 42))
        screen.blit(detail, (24, 94))
        screen.blit(device, (24, 126))
        screen.blit(progress, (24, 158))
        pygame.display.flip()
        pygame.time.wait(16)

    payload = {
        "name": "user_calibrated",
        "match": [joysticks[0].get_name()],
        "start_button": 13,
        "select_button": 12,
        "actions": mappings,
    }
    save_calibrated_mapping(payload)
    print("Mapeamento salvo em Pokecable_tool/config/input_map.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
