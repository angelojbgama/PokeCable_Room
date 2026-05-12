#!/bin/bash
# PokeCable Room - R36S launcher
# Fast launcher for the R36S frontend.
# Installs Python dependencies only as a fallback when imports are missing.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "$0")"
PYTHON_SCRIPT="$SCRIPT_DIR/r36s_pokecable_ui.py"
CONTROL_FILE="$SCRIPT_DIR/pokecable.gptk"
DEPS_FLAG="$SCRIPT_DIR/.deps_installed"
LOG_ROOT="$SCRIPT_DIR/logs"
SESSION_ID="$(date +%Y%m%d_%H%M%S)"
SESSION_DIR="$LOG_ROOT/sessions/$SESSION_ID"
DEPS_LOG="$SESSION_DIR/deps_install.log"
LAUNCHER_LOG="$SESSION_DIR/launcher.log"
PYTHON_STDOUT_LOG="$SESSION_DIR/python.stdout.log"
RUN_LOG="$LOG_ROOT/last_run.log"
TTY="/dev/tty1"

mkdir -p "$SESSION_DIR" 2>/dev/null || true
mkdir -p "$LOG_ROOT" 2>/dev/null || true
printf "%s\n" "$SESSION_DIR" > "$LOG_ROOT/latest_session.txt"
ln -sfn "$SESSION_DIR" "$LOG_ROOT/latest" 2>/dev/null || true

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export TERM=linux
export PYGAME_HIDE_SUPPORT_PROMPT=1
export POKECABLE_LOG_ROOT="$LOG_ROOT"
export POKECABLE_LOG_SESSION="$SESSION_ID"
export POKECABLE_LOG_DIR="$SESSION_DIR"

# Try to normalize console (dArkOS-specific, ignore if not available)
. /usr/local/bin/darkos-console-normalize.sh --clear 2>/dev/null || true

# ---- Helper: print to TTY and stdout ----
ttyprint() {
  local msg="$*"
  echo "$msg"
  printf "%s %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$msg" >> "$LAUNCHER_LOG" 2>/dev/null || true
  if [ -w "$TTY" ]; then
    printf "%s\n" "$msg" > "$TTY" 2>/dev/null || true
  fi
}

ttyclear() {
  if [ -w "$TTY" ]; then
    printf "\033c" > "$TTY" 2>/dev/null || true
  fi
}

# ---- Cleanup on exit ----
cleanup() {
  pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
  if [ -w "$TTY" ]; then
    printf "\033[?25h" > "$TTY" 2>/dev/null || true
    stty sane < "$TTY" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# ---- Dependency installation ----
install_apt_package() {
  local pkg="$1"
  ttyprint "  apt-get install $pkg ..."
  if apt-get install -y "$pkg" >> "$DEPS_LOG" 2>&1; then
    ttyprint "    OK"
    return 0
  fi
  ttyprint "    FALHOU"
  return 1
}

install_pip_package() {
  local mod="$1"
  local pkg="${2:-$1}"
  ttyprint "  pip3 install $pkg ..."
  if pip3 install --quiet --no-cache-dir "$pkg" >> "$DEPS_LOG" 2>&1; then
    ttyprint "    OK"
    return 0
  fi
  if pip3 install --quiet --no-cache-dir --break-system-packages "$pkg" >> "$DEPS_LOG" 2>&1; then
    ttyprint "    OK (--break-system-packages)"
    return 0
  fi
  ttyprint "    FALHOU"
  return 1
}

check_python_module() {
  python3 -c "import $1" >/dev/null 2>&1
}

install_dependencies() {
  ttyclear
  ttyprint "=== Instalando dependências PokeCable ==="
  ttyprint ""
  ttyprint "Log: $DEPS_LOG"
  ttyprint ""

  : > "$DEPS_LOG"

  # Step 1: pygame (system package)
  ttyprint "[1/4] pygame..."
  if check_python_module pygame; then
    ttyprint "  já instalado"
  else
    apt-get update >> "$DEPS_LOG" 2>&1 || ttyprint "  AVISO: apt-get update falhou (continuando)"
    install_apt_package "python3-pygame" || true
    if ! check_python_module pygame; then
      install_pip_package "pygame" "pygame" || true
    fi
  fi

  # Step 2: pip3
  ttyprint "[2/4] pip3..."
  if command -v pip3 >/dev/null 2>&1; then
    ttyprint "  já instalado"
  else
    install_apt_package "python3-pip" || true
  fi

  # Step 3: websockets
  ttyprint "[3/4] websockets..."
  if check_python_module websockets; then
    ttyprint "  já instalado"
  else
    install_apt_package "python3-websockets" || install_pip_package "websockets" "websockets" || true
  fi

  # Step 4: sanity check for the app
  ttyprint "[4/4] app..."
  if python3 -m py_compile "$PYTHON_SCRIPT" >> "$DEPS_LOG" 2>&1; then
    ttyprint "  OK"
  else
    ttyprint "  FALHOU"
  fi

  ttyprint ""
  ttyprint "=== Verificação final ==="
  local missing=""
  for mod in pygame websockets; do
    if check_python_module "$mod"; then
      ttyprint "  $mod ... OK"
    else
      ttyprint "  $mod ... AUSENTE"
      missing="$missing $mod"
    fi
  done

  if [ -n "$missing" ]; then
    ttyprint ""
    ttyprint "ERRO: módulos ausentes:$missing"
    ttyprint "Veja: cat $DEPS_LOG"
    ttyprint "(aguardando 10s antes de sair...)"
    sleep 10
    return 1
  fi

  # Mark as installed
  touch "$DEPS_FLAG"
  ttyprint ""
  ttyprint "Todas as dependências instaladas com sucesso!"
  sleep 2
  return 0
}

# ---- Quick dependency check ----
deps_ready() {
  check_python_module pygame && check_python_module websockets
}

if ! deps_ready; then
  install_dependencies || exit 1
fi

# ---- Optional gptokeyb bridge ----
if [ "${POKECABLE_USE_GPTOKEYB:-0}" = "1" ] && [ -x /opt/inttools/gptokeyb ]; then
  [ -e /dev/uinput ] && chmod 666 /dev/uinput 2>/dev/null || true
  export SDL_GAMECONTROLLERCONFIG_FILE="/opt/inttools/gamecontrollerdb.txt"
  pkill -f "gptokeyb -1 $SCRIPT_NAME" 2>/dev/null || true
  if [ -f "$CONTROL_FILE" ]; then
    /opt/inttools/gptokeyb -1 "$SCRIPT_NAME" -c "$CONTROL_FILE" >/dev/null 2>&1 &
    sleep 0.5
  fi
fi

# ---- Launch the app, capturing errors ----
ttyclear
ttyprint "Iniciando PokeCable..."
ttyprint "Sessão de logs: $SESSION_DIR"

: > "$PYTHON_STDOUT_LOG"
printf "session=%s\n" "$SESSION_DIR" > "$RUN_LOG"
if python3 "$PYTHON_SCRIPT" >> "$PYTHON_STDOUT_LOG" 2>&1; then
  exit 0
else
  EXIT_CODE=$?
  ttyclear
  ttyprint "=== ERRO NA EXECUÇÃO ==="
  ttyprint "Exit code: $EXIT_CODE"
  ttyprint ""
  ttyprint "Sessão: $SESSION_DIR"
  ttyprint "Resumo do erro:"
  if [ -f "$SESSION_DIR/errors.log" ]; then
    tail -20 "$SESSION_DIR/errors.log" 2>/dev/null | while IFS= read -r line; do
      ttyprint "  $line"
    done
  else
    tail -20 "$PYTHON_STDOUT_LOG" 2>/dev/null | while IFS= read -r line; do
      ttyprint "  $line"
    done
  fi
  ttyprint ""
  ttyprint "Arquivos:"
  ttyprint "  launcher: $LAUNCHER_LOG"
  ttyprint "  python:   $PYTHON_STDOUT_LOG"
  ttyprint "  ui:       $SESSION_DIR/ui.log"
  ttyprint "  core:     $SESSION_DIR/core.log"
  ttyprint "  save:     $SESSION_DIR/save.log"
  ttyprint "  errors:   $SESSION_DIR/errors.log"
  ttyprint "(aguardando 15s antes de sair...)"
  sleep 15
  exit "$EXIT_CODE"
fi
