from __future__ import annotations

import glob
from getpass import getpass
import os
import select
import struct
import sys
import termios
import time
from typing import Iterable, Sequence, TypeVar


T = TypeVar("T")

EV_KEY = 0x01
EV_ABS = 0x03
KEY_UP = 103
KEY_DOWN = 108
KEY_LEFT = 105
KEY_RIGHT = 106
KEY_ENTER = 28
KEY_ESC = 1
BTN_SOUTH = 304
BTN_EAST = 305
BTN_WEST = 308
BTN_SELECT = 314
BTN_START = 315
ABS_HAT0X = 16
ABS_HAT0Y = 17


class GamepadReader:
    def __init__(self) -> None:
        self._files = []
        self._event_size = struct.calcsize("llHHI")
        for path in sorted(glob.glob("/dev/input/event*")):
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            except OSError:
                continue
            self._files.append(os.fdopen(fd, "rb", buffering=0))

    def available(self) -> bool:
        return bool(self._files)

    def close(self) -> None:
        for file_obj in self._files:
            try:
                file_obj.close()
            except OSError:
                pass

    def wait_action(self) -> str:
        if not self._files:
            raise RuntimeError("Nenhum controle em /dev/input/event* ficou acessivel para o menu.")
        while True:
            readable, _, _ = select.select(self._files, [], [], 0.5)
            for file_obj in readable:
                while True:
                    try:
                        data = file_obj.read(self._event_size)
                    except BlockingIOError:
                        break
                    if not data or len(data) < self._event_size:
                        break
                    action = self._event_to_action(data)
                    if action:
                        time.sleep(0.08)
                        return action

    def _event_to_action(self, data: bytes) -> str | None:
        _sec, _usec, event_type, code, value = struct.unpack("llHHI", data)
        signed_value = struct.unpack("i", struct.pack("I", value))[0]
        if event_type == EV_KEY and signed_value == 1:
            if code in {KEY_UP}:
                return "up"
            if code in {KEY_DOWN}:
                return "down"
            if code in {KEY_LEFT}:
                return "left"
            if code in {KEY_RIGHT}:
                return "right"
            if code in {KEY_ENTER, BTN_SOUTH}:
                return "select"
            if code in {KEY_ESC, BTN_EAST}:
                return "back"
            if code in {BTN_START, BTN_WEST}:
                return "done"
            if code == BTN_SELECT:
                return "cancel"
        if event_type == EV_ABS:
            if code == ABS_HAT0Y and signed_value == -1:
                return "up"
            if code == ABS_HAT0Y and signed_value == 1:
                return "down"
            if code == ABS_HAT0X and signed_value == -1:
                return "left"
            if code == ABS_HAT0X and signed_value == 1:
                return "right"
        return None


class TerminalUI:
    def __init__(self) -> None:
        self._tty_reader = None
        self._tty_writer = None
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            try:
                self._tty_reader = open("/dev/tty", "r", encoding="utf-8", buffering=1)
                self._tty_writer = open("/dev/tty", "w", encoding="utf-8", buffering=1)
            except OSError:
                self._tty_reader = None
                self._tty_writer = None
        self._gamepad = GamepadReader()

    def print(self, message: str = "") -> None:
        stream = self._tty_writer or sys.stdout
        print(message, file=stream, flush=True)

    def _readline(self, prompt: str) -> str:
        stream = self._tty_writer or sys.stdout
        reader = self._tty_reader or sys.stdin
        if self._tty_reader is None and not sys.stdin.isatty():
            raise RuntimeError("stdin_unavailable")
        print(prompt, end="", file=stream, flush=True)
        value = reader.readline()
        if value == "":
            raise RuntimeError("stdin_unavailable")
        return value.rstrip("\n\r")

    def input_text(self, prompt: str, default: str | None = None) -> str:
        suffix = f" [{default}]" if default else ""
        try:
            value = self._readline(f"{prompt}{suffix}: ").strip()
        except RuntimeError as exc:
            if str(exc) != "stdin_unavailable":
                raise
            value = self._gamepad_text(prompt, default=default, password=False)
        return value or (default or "")

    def input_password(self, prompt: str) -> str:
        if self._tty_reader is None and sys.stdin.isatty():
            try:
                return getpass(f"{prompt}: ")
            except EOFError as exc:
                raise RuntimeError("Terminal sem entrada interativa. Abra pelo Options -> Tools ou por SSH/terminal.") from exc
        if self._tty_reader is None and not sys.stdin.isatty():
            return self._gamepad_text(prompt, default="", password=True)
        return self._read_password_from_tty(f"{prompt}: ")

    def _read_password_from_tty(self, prompt: str) -> str:
        stream = self._tty_writer or sys.stdout
        reader = self._tty_reader or sys.stdin
        fd = reader.fileno()
        old_settings = None
        try:
            if os.isatty(fd):
                old_settings = termios.tcgetattr(fd)
                new_settings = old_settings[:]
                new_settings[3] = new_settings[3] & ~termios.ECHO
                termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
            print(prompt, end="", file=stream, flush=True)
            value = reader.readline()
            print("", file=stream, flush=True)
            if value == "":
                raise RuntimeError("Terminal sem entrada interativa. Abra pelo Options -> Tools ou por SSH/terminal.")
            return value.rstrip("\n\r")
        finally:
            if old_settings is not None:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def confirm(self, prompt: str, default: bool = False) -> bool:
        suffix = "S/n" if default else "s/N"
        try:
            value = self._readline(f"{prompt} ({suffix}): ").strip().lower()
        except RuntimeError as exc:
            if str(exc) != "stdin_unavailable":
                raise
            return self._gamepad_confirm(prompt, default)
        if not value:
            return default
        return value in {"s", "sim", "y", "yes"}

    def choose(self, prompt: str, options: Sequence[T], labels: Iterable[str] | None = None) -> T:
        if not options:
            raise ValueError("Nao ha opcoes disponiveis.")
        labels_list = list(labels) if labels is not None else [str(option) for option in options]
        self.print(prompt)
        for index, label in enumerate(labels_list, start=1):
            self.print(f"{index}. {label}")
        while True:
            try:
                value = self._readline("Escolha: ").strip()
            except RuntimeError as exc:
                if str(exc) != "stdin_unavailable":
                    raise
                return self._gamepad_choose(prompt, options, labels_list)
            try:
                option_index = int(value) - 1
            except ValueError:
                self.print("Digite um numero valido.")
                continue
            if 0 <= option_index < len(options):
                return options[option_index]
            self.print("Opcao fora da lista.")

    def _clear(self) -> None:
        stream = self._tty_writer or sys.stdout
        print("\033[2J\033[H", end="", file=stream, flush=True)

    def _gamepad_choose(self, prompt: str, options: Sequence[T], labels: list[str]) -> T:
        if not self._gamepad.available():
            raise RuntimeError(
                "Sem teclado e sem acesso a /dev/input/event*. Execute por SSH ou ajuste permissoes dos eventos de input."
            )
        index = 0
        while True:
            self._clear()
            self.print(prompt)
            self.print("D-pad: mover | A: confirmar | B: voltar")
            self.print("")
            for item_index, label in enumerate(labels):
                marker = ">" if item_index == index else " "
                self.print(f"{marker} {label}")
            action = self._gamepad.wait_action()
            if action == "up":
                index = (index - 1) % len(options)
            elif action == "down":
                index = (index + 1) % len(options)
            elif action in {"select", "done"}:
                return options[index]
            elif action in {"back", "cancel"}:
                raise RuntimeError("Operacao cancelada no controle.")

    def _gamepad_confirm(self, prompt: str, default: bool) -> bool:
        return self._gamepad_choose(prompt, [True, False], ["Sim", "Nao"])

    def _gamepad_text(self, prompt: str, default: str | None, password: bool) -> str:
        if not self._gamepad.available():
            raise RuntimeError(
                "Sem teclado e sem acesso a /dev/input/event*. Execute por SSH ou ajuste permissoes dos eventos de input."
            )
        keys = list("abcdefghijklmnopqrstuvwxyz") + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + list("0123456789") + [
            "-",
            "_",
            ".",
            " ",
            "/",
            ":",
            "<DEL>",
            "<OK>",
        ]
        columns = 8
        index = 0
        value = default or ""
        while True:
            self._clear()
            shown = "*" * len(value) if password else value
            self.print(prompt)
            self.print(f"Valor: {shown}")
            self.print("D-pad: mover | A: adicionar | B: apagar | START/X: OK")
            self.print("")
            for row_start in range(0, len(keys), columns):
                row = keys[row_start : row_start + columns]
                rendered = []
                for offset, key in enumerate(row):
                    key_index = row_start + offset
                    label = key
                    if key_index == index:
                        rendered.append(f"[{label}]")
                    else:
                        rendered.append(f" {label} ")
                self.print(" ".join(rendered))
            action = self._gamepad.wait_action()
            if action == "left":
                index = (index - 1) % len(keys)
            elif action == "right":
                index = (index + 1) % len(keys)
            elif action == "up":
                index = (index - columns) % len(keys)
            elif action == "down":
                index = (index + columns) % len(keys)
            elif action == "back":
                value = value[:-1]
            elif action in {"done"}:
                return value
            elif action == "cancel":
                return default or ""
            elif action == "select":
                key = keys[index]
                if key == "<OK>":
                    return value
                if key == "<DEL>":
                    value = value[:-1]
                else:
                    value += key
