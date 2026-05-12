#!/bin/bash
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/r36s_pokecable_ui.py"
CONTROL_FILE="$SCRIPT_DIR/pokecable.gptk"
SCRIPT_NAME="$(basename "$0")"

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export TERM=linux
. /usr/local/bin/darkos-console-normalize.sh --clear 2>/dev/null || true

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

LOG_FILE="/tmp/pokecable_deps.log"
rm -f "$LOG_FILE"

# Check and install pygame
if ! python3 -c 'import pygame' >/dev/null 2>&1; then
  printf "\033c=== Instalando dependências ===\n" > /dev/tty1 2>/dev/null || true
  printf "pygame... " > /dev/tty1 2>/dev/null || true
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update >> "$LOG_FILE" 2>&1 || true
    apt-get install -y python3-pygame >> "$LOG_FILE" 2>&1 || true
  fi
  if python3 -c 'import pygame' >/dev/null 2>&1; then
    printf "OK\n" > /dev/tty1 2>/dev/null || true
  else
    printf "ERRO\n" > /dev/tty1 2>/dev/null || true
  fi
fi

# Check and install requests
if ! python3 -c 'import requests' >/dev/null 2>&1; then
  printf "requests... " > /dev/tty1 2>/dev/null || true
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --quiet requests >> "$LOG_FILE" 2>&1 || true
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get install -y python3-requests >> "$LOG_FILE" 2>&1 || true
  fi
  if python3 -c 'import requests' >/dev/null 2>&1; then
    printf "OK\n" > /dev/tty1 2>/dev/null || true
  else
    printf "ERRO\n" > /dev/tty1 2>/dev/null || true
  fi
fi

# Verify all dependencies are available
if ! python3 -c 'import pygame; import requests' >/dev/null 2>&1; then
  printf "\033c=== ERRO: Dependências ausentes ===\n" > /dev/tty1 2>/dev/null || true
  printf "Necessário: pygame, requests\n" > /dev/tty1 2>/dev/null || true
  printf "Log: cat %s\n" "$LOG_FILE" > /dev/tty1 2>/dev/null || true
  printf "Pressione qualquer tecla para sair...\n" > /dev/tty1 2>/dev/null || true
  sleep 5
  exit 1
fi

if [ -x /opt/inttools/gptokeyb ]; then
  [ -e /dev/uinput ] && chmod 666 /dev/uinput 2>/dev/null || true
  export SDL_GAMECONTROLLERCONFIG_FILE="/opt/inttools/gamecontrollerdb.txt"
  pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
  /opt/inttools/gptokeyb -1 "$SCRIPT_NAME" -c "$CONTROL_FILE" >/dev/null 2>&1 &
  sleep 0.5
fi

# Run the app and show error if it crashes
if python3 "$PYTHON_SCRIPT" 2>/tmp/pokecable_error.log; then
  exit 0
else
  EXIT_CODE=$?
  printf "\033c=== ERRO NA EXECUÇÃO ===\n" > /dev/tty1 2>/dev/null || true
  printf "Exit code: %d\n" "$EXIT_CODE" > /dev/tty1 2>/dev/null || true
  printf "\nLog de erro:\n" > /dev/tty1 2>/dev/null || true
  cat /tmp/pokecable_error.log >> /dev/tty1 2>/dev/null || true
  printf "\nPressione qualquer tecla para sair...\n" > /dev/tty1 2>/dev/null || true
  sleep 10
  exit $EXIT_CODE
fi
