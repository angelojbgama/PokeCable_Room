#!/bin/bash
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/task_manager_pygame.py"
CONTROL_FILE="$SCRIPT_DIR/task_manager.gptk"
SCRIPT_NAME="$(basename "$0")"

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export TERM=linux
. /usr/local/bin/darkos-console-normalize.sh --clear

cleanup() {
  pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
  printf "\033[?25h" > /dev/tty1 2>/dev/null || true
  stty sane < /dev/tty1 2>/dev/null || true
}

trap cleanup EXIT INT TERM

if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  echo "This tool requires root."
  exit 1
fi

if ! python3 -c 'import pygame' >/dev/null 2>&1; then
  printf "\033cInstalling python3-pygame. Please wait...\n" > /dev/tty1 2>/dev/null || true
  if command -v apt-get >/dev/null 2>&1; then
    apt-get install -y python3-pygame >/tmp/task_manager_deps.log 2>&1 || true
  fi
fi

if ! python3 -c 'import pygame' >/dev/null 2>&1; then
  printf "python3-pygame is required. Check /tmp/task_manager_deps.log\n" > /dev/tty1 2>/dev/null || true
  sleep 3
  exit 1
fi

if [ -x /opt/inttools/gptokeyb ]; then
  [ -e /dev/uinput ] && chmod 666 /dev/uinput 2>/dev/null || true
  export SDL_GAMECONTROLLERCONFIG_FILE="/opt/inttools/gamecontrollerdb.txt"
  pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
  /opt/inttools/gptokeyb -1 "$SCRIPT_NAME" -c "$CONTROL_FILE" >/dev/null 2>&1 &
fi

exec python3 "$PYTHON_SCRIPT"
