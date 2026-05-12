#!/bin/bash
# PokeCable Room - R36S launcher (fast path)
# Fast first check: if deps flag exists AND module check passes, launch immediately.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "$0")"
PYTHON_SCRIPT="$SCRIPT_DIR/r36s_pokecable_ui.py"
CONTROL_FILE="$SCRIPT_DIR/pokecable.gptk"
DEPS_FLAG="$SCRIPT_DIR/.deps_installed"
LOG_DIR="$SCRIPT_DIR/logs"
DEPS_LOG="$LOG_DIR/deps_install.log"
RUN_LOG="$LOG_DIR/last_run.log"
TTY="/dev/tty1"

mkdir -p "$LOG_DIR" 2>/dev/null || true

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export TERM=linux
export PYGAME_HIDE_SUPPORT_PROMPT=1

ttyprint() {
  echo "$*"
  [ -w "$TTY" ] && printf "%s\n" "$*" > "$TTY" 2>/dev/null || true
}

cleanup() {
  pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
  if [ -w "$TTY" ]; then
    printf "\033[?25h" > "$TTY" 2>/dev/null || true
    stty sane < "$TTY" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# ---- FAST PATH: single python check (one process, ~80ms) ----
check_deps_fast() {
  python3 -c "import pygame, requests, websockets" 2>/dev/null
}

# ---- Try fast path first ----
if [ -f "$DEPS_FLAG" ] && check_deps_fast; then
  # Skip darkos normalize (not critical, was slow)
  # Skip privilege check (gptokeyb works as user if uinput is set)

  # Set up gptokeyb if available (background, no wait)
  if [ -x /opt/inttools/gptokeyb ] && [ -f "$CONTROL_FILE" ]; then
    [ -e /dev/uinput ] && chmod 666 /dev/uinput 2>/dev/null || true
    export SDL_GAMECONTROLLERCONFIG_FILE="/opt/inttools/gamecontrollerdb.txt"
    pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
    /opt/inttools/gptokeyb -1 "$SCRIPT_NAME" -c "$CONTROL_FILE" >/dev/null 2>&1 &
  fi

  # Launch directly
  exec python3 "$PYTHON_SCRIPT"
fi

# ---- SLOW PATH: deps missing or first run ----
# Need root to install
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  ttyprint "ERRO: necessita root para instalar deps."
  sleep 3
  exit 1
fi

ttyprint "=== Instalando dependências ==="
: > "$DEPS_LOG"

# Single python check to know which are missing
MISSING=$(python3 -c "
import sys
mods = ['pygame', 'requests', 'websockets']
missing = []
for m in mods:
    try:
        __import__(m)
    except ImportError:
        missing.append(m)
print(' '.join(missing))
" 2>/dev/null)

if [ -z "$MISSING" ]; then
  ttyprint "Tudo já instalado, criando flag..."
  touch "$DEPS_FLAG"
else
  ttyprint "Faltando:$MISSING"

  # Only run apt-get update if we need apt at all
  NEED_APT=0
  for m in $MISSING; do
    case "$m" in
      pygame) NEED_APT=1 ;;
    esac
  done

  if [ "$NEED_APT" -eq 1 ]; then
    ttyprint "apt-get update..."
    apt-get update >> "$DEPS_LOG" 2>&1 || ttyprint "  (continuando mesmo com erro)"
  fi

  # Install each missing module
  for m in $MISSING; do
    ttyprint "Instalando $m..."
    case "$m" in
      pygame)
        apt-get install -y python3-pygame >> "$DEPS_LOG" 2>&1 \
          || pip3 install --quiet --no-cache-dir --break-system-packages pygame >> "$DEPS_LOG" 2>&1 \
          || pip3 install --quiet --no-cache-dir pygame >> "$DEPS_LOG" 2>&1 \
          || true
        ;;
      requests|websockets)
        # pip3 first (faster than apt)
        pip3 install --quiet --no-cache-dir --break-system-packages "$m" >> "$DEPS_LOG" 2>&1 \
          || pip3 install --quiet --no-cache-dir "$m" >> "$DEPS_LOG" 2>&1 \
          || apt-get install -y "python3-$m" >> "$DEPS_LOG" 2>&1 \
          || true
        ;;
    esac
  done

  # Final verification
  if check_deps_fast; then
    touch "$DEPS_FLAG"
    ttyprint "OK"
  else
    ttyprint "ERRO: deps ainda ausentes. Veja: $DEPS_LOG"
    sleep 5
    exit 1
  fi
fi

# ---- Set up gptokeyb ----
if [ -x /opt/inttools/gptokeyb ] && [ -f "$CONTROL_FILE" ]; then
  [ -e /dev/uinput ] && chmod 666 /dev/uinput 2>/dev/null || true
  export SDL_GAMECONTROLLERCONFIG_FILE="/opt/inttools/gamecontrollerdb.txt"
  pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
  /opt/inttools/gptokeyb -1 "$SCRIPT_NAME" -c "$CONTROL_FILE" >/dev/null 2>&1 &
fi

# ---- Launch ----
: > "$RUN_LOG"
if python3 "$PYTHON_SCRIPT" 2>&1 | tee "$RUN_LOG"; then
  exit 0
else
  EXIT_CODE=$?
  ttyprint "=== ERRO (exit $EXIT_CODE) ==="
  tail -15 "$RUN_LOG" 2>/dev/null | while IFS= read -r line; do
    ttyprint "  $line"
  done
  ttyprint "Log: $RUN_LOG"
  sleep 10
  exit "$EXIT_CODE"
fi
