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

# Display header
printf "\033c" > /dev/tty1 2>/dev/null || true
printf "=== PokeCable - Verificando Dependências ===\n\n" > /dev/tty1 2>/dev/null || true

# Ensure apt-get is available
if ! command -v apt-get >/dev/null 2>&1; then
  printf "ERRO: apt-get não encontrado\n" > /dev/tty1 2>/dev/null || true
  exit 1
fi

# Update package list
printf "Atualizando repositórios..." > /dev/tty1 2>/dev/null || true
apt-get update >> "$LOG_FILE" 2>&1 || {
  printf " ERRO\n" > /dev/tty1 2>/dev/null || true
  printf "Falha ao atualizar repositórios. Ver: cat %s\n" "$LOG_FILE" > /dev/tty1 2>/dev/null || true
  sleep 3
  exit 1
}
printf " OK\n" > /dev/tty1 2>/dev/null || true

# Install pygame
printf "Instalando pygame..." > /dev/tty1 2>/dev/null || true
if ! python3 -c 'import pygame' >/dev/null 2>&1; then
  apt-get install -y python3-pygame >> "$LOG_FILE" 2>&1 || {
    printf " ERRO\n" > /dev/tty1 2>/dev/null || true
    printf "Falha ao instalar pygame. Ver: cat %s\n" "$LOG_FILE" > /dev/tty1 2>/dev/null || true
    sleep 3
    exit 1
  }
fi
printf " OK\n" > /dev/tty1 2>/dev/null || true

# Install pip3 if needed
if ! command -v pip3 >/dev/null 2>&1; then
  printf "Instalando pip3..." > /dev/tty1 2>/dev/null || true
  apt-get install -y python3-pip >> "$LOG_FILE" 2>&1 || {
    printf " ERRO\n" > /dev/tty1 2>/dev/null || true
  }
  printf " OK\n" > /dev/tty1 2>/dev/null || true
fi

# Install requests via pip3
printf "Instalando requests..." > /dev/tty1 2>/dev/null || true
if ! python3 -c 'import requests' >/dev/null 2>&1; then
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --quiet --no-cache-dir requests >> "$LOG_FILE" 2>&1 || {
      printf " (tentando apt-get)..." > /dev/tty1 2>/dev/null || true
      apt-get install -y python3-requests >> "$LOG_FILE" 2>&1 || {
        printf " ERRO\n" > /dev/tty1 2>/dev/null || true
        printf "Falha ao instalar requests. Ver: cat %s\n" "$LOG_FILE" > /dev/tty1 2>/dev/null || true
        sleep 3
        exit 1
      }
    }
  else
    printf " (tentando apt-get)..." > /dev/tty1 2>/dev/null || true
    apt-get install -y python3-requests >> "$LOG_FILE" 2>&1 || {
      printf " ERRO\n" > /dev/tty1 2>/dev/null || true
      printf "Falha ao instalar requests. Ver: cat %s\n" "$LOG_FILE" > /dev/tty1 2>/dev/null || true
      sleep 3
      exit 1
    }
  fi
fi
printf " OK\n" > /dev/tty1 2>/dev/null || true

# Final verification
printf "\nVerificando instalação..." > /dev/tty1 2>/dev/null || true
if python3 -c 'import pygame; import requests' >/dev/null 2>&1; then
  printf " OK\n\n" > /dev/tty1 2>/dev/null || true
  printf "Todas as dependências instaladas!\n" > /dev/tty1 2>/dev/null || true
  sleep 1
else
  printf " ERRO\n" > /dev/tty1 2>/dev/null || true
  printf "ERRO: Não foi possível instalar as dependências\n" > /dev/tty1 2>/dev/null || true
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
