#!/bin/bash
# PokeCable Room - R36S launcher
# Installs Python dependencies on first run, then starts the pygame UI.

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

# Try to normalize console (dArkOS-specific, ignore if not available)
. /usr/local/bin/darkos-console-normalize.sh --clear 2>/dev/null || true

# ---- Helper: print to TTY and stdout ----
ttyprint() {
  local msg="$*"
  echo "$msg"
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

# ---- Privilege check: re-exec with sudo if not root ----
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    exec sudo -E bash "$0" "$@"
  fi
  ttyprint "ERROR: Requires root to install dependencies."
  sleep 3
  exit 1
fi

# ---- Internet check ----
check_internet() {
  ttyprint "Verificando conexão..."
  if ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
    ttyprint "  Internet OK"
    return 0
  fi
  if ping -c 1 -W 3 9kernel.vps-kinghost.net >/dev/null 2>&1; then
    ttyprint "  Backend acessível"
    return 0
  fi
  ttyprint "  AVISO: Sem internet detectada"
  return 1
}

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

  check_internet || true

  # Step 1: apt update (may fail offline, that's ok if packages exist)
  ttyprint "[1/5] Atualizando repositórios..."
  apt-get update >> "$DEPS_LOG" 2>&1 || ttyprint "  AVISO: apt-get update falhou (continuando)"

  # Step 2: pygame (system package)
  ttyprint "[2/5] pygame..."
  if check_python_module pygame; then
    ttyprint "  já instalado"
  else
    install_apt_package "python3-pygame" || true
    if ! check_python_module pygame; then
      install_pip_package "pygame" "pygame" || true
    fi
  fi

  # Step 3: pip3
  ttyprint "[3/5] pip3..."
  if command -v pip3 >/dev/null 2>&1; then
    ttyprint "  já instalado"
  else
    install_apt_package "python3-pip" || true
  fi

  # Step 4: requests
  ttyprint "[4/5] requests..."
  if check_python_module requests; then
    ttyprint "  já instalado"
  else
    install_apt_package "python3-requests" || install_pip_package "requests" "requests" || true
  fi

  # Step 5: websockets
  ttyprint "[5/5] websockets..."
  if check_python_module websockets; then
    ttyprint "  já instalado"
  else
    install_apt_package "python3-websockets" || install_pip_package "websockets" "websockets" || true
  fi

  ttyprint ""
  ttyprint "=== Verificação final ==="
  local missing=""
  for mod in pygame requests websockets; do
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

# ---- Check / install deps ----
ALL_DEPS_OK=1
for mod in pygame requests websockets; do
  if ! check_python_module "$mod"; then
    ALL_DEPS_OK=0
    break
  fi
done

if [ "$ALL_DEPS_OK" -ne 1 ] || [ ! -f "$DEPS_FLAG" ]; then
  install_dependencies || exit 1
fi

# ---- Set up gptokeyb (R36S gamepad-to-keyboard mapping) ----
if [ -x /opt/inttools/gptokeyb ]; then
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

: > "$RUN_LOG"
if python3 "$PYTHON_SCRIPT" 2>&1 | tee "$RUN_LOG"; then
  exit 0
else
  EXIT_CODE=$?
  ttyclear
  ttyprint "=== ERRO NA EXECUÇÃO ==="
  ttyprint "Exit code: $EXIT_CODE"
  ttyprint ""
  ttyprint "Últimas linhas do log:"
  tail -20 "$RUN_LOG" 2>/dev/null | while IFS= read -r line; do
    ttyprint "  $line"
  done
  ttyprint ""
  ttyprint "Log completo: $RUN_LOG"
  ttyprint "(aguardando 15s antes de sair...)"
  sleep 15
  exit "$EXIT_CODE"
fi
