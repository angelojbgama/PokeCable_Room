#!/usr/bin/env bash
# PokeCable Room launcher for R36S/Linux and WSL development.
#
# Uso:
#   ./pokecable.sh                # Inicia no menu (tela padrão)
#   ./pokecable.sh select_pokemon # Abre direto em uma tela específica
#
# Telas disponíveis para debug:
#   menu, load_save, select_pokemon, entering_room_name,
#   enter_password, connecting, waiting_partner, trading,
#   trade_confirm, trade_result, deposit_confirm, withdraw_confirm, etc.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_MODULE="frontend.app"
LOG_ROOT="$SCRIPT_DIR/logs"
ERROR_LOG="$LOG_ROOT/error.log"
DEBUG_LOG="$LOG_ROOT/debug.log"
DEPS_LOG="${POKECABLE_DEPS_LOG:-/tmp/pokecable_deps.log}"
TTY="${POKECABLE_TTY:-/dev/tty1}"
DEPENDENCE_DIR="$SCRIPT_DIR/dependence"
DEPENDENCE_PYTHON_DIR="$DEPENDENCE_DIR/python"
DEPENDENCE_LIB_DIR="$DEPENDENCE_DIR/lib/aarch64-linux-gnu"
DEPENDENCE_ARCH="aarch64"
DEPENDENCE_PYTHON_VERSION="3.13"

mkdir -p "$LOG_ROOT" 2>/dev/null || true
touch "$ERROR_LOG" 2>/dev/null || true

export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export TERM="${TERM:-linux}"
export PYGAME_HIDE_SUPPORT_PROMPT=1
export PYTHONDONTWRITEBYTECODE=1
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"
export AUDIODEV="${AUDIODEV:-null}"
export POKECABLE_LOG_ROOT="$LOG_ROOT"
export POKECABLE_ERROR_LOG="$ERROR_LOG"
export POKECABLE_DEBUG_LOG="$DEBUG_LOG"
export POKECABLE_SAVE_DIRS="${POKECABLE_SAVE_DIRS:-$PROJECT_DIR/roms/test-saves}"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

. /usr/local/bin/darkos-console-normalize.sh --clear 2>/dev/null || true

debug_enabled() {
  case "${POKECABLE_DEBUG:-0}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

ttyprint() {
  local msg="$*"
  echo "$msg"
  if debug_enabled; then
    printf "%s %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$msg" >> "$DEBUG_LOG" 2>/dev/null || true
  fi
  if [ -w "$TTY" ]; then
    printf "%s\n" "$msg" > "$TTY" 2>/dev/null || true
  fi
}

ttyclear() {
  if [ -w "$TTY" ]; then
    printf "\033c" > "$TTY" 2>/dev/null || true
  fi
}

find_python() {
  if [ -n "${POKECABLE_PYTHON:-}" ] && command -v "$POKECABLE_PYTHON" >/dev/null 2>&1; then
    printf "%s\n" "$POKECABLE_PYTHON"
    return 0
  fi

  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf "%s\n" "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python || true)"
if [ -z "$PYTHON_BIN" ]; then
  ttyprint "ERRO: Python nao encontrado."
  ttyprint "Instale python3 no sistema e execute ./pokecable.sh novamente."
  exit 1
fi

enable_dependence_bundle() {
  local arch
  local py_version
  arch="$(uname -m 2>/dev/null || true)"
  py_version="$("$PYTHON_BIN" -B -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  if [ "$arch" = "$DEPENDENCE_ARCH" ] && [ "$py_version" = "$DEPENDENCE_PYTHON_VERSION" ]; then
    if [ -d "$DEPENDENCE_LIB_DIR" ]; then
      export LD_LIBRARY_PATH="$DEPENDENCE_LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    fi
    if [ -d "$DEPENDENCE_PYTHON_DIR" ]; then
      export PYTHONPATH="$DEPENDENCE_PYTHON_DIR${PYTHONPATH:+:$PYTHONPATH}"
    fi
    return 0
  fi

  ttyprint "Dependencias locais ignoradas: alvo $DEPENDENCE_ARCH/Python $DEPENDENCE_PYTHON_VERSION, atual ${arch:-?}/Python ${py_version:-?}."
}

enable_dependence_bundle

cleanup() {
  if [ -w "$TTY" ]; then
    printf "\033[?25h" > "$TTY" 2>/dev/null || true
    stty sane < "$TTY" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

online_install_enabled() {
  case "${POKECABLE_ALLOW_ONLINE_INSTALL:-0}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

install_apt_package() {
  local pkg="$1"
  if ! online_install_enabled; then
    ttyprint "  instalacao online desativada para $pkg"
    return 1
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    ttyprint "  apt-get indisponivel para $pkg"
    return 1
  fi

  ttyprint "  apt-get install $pkg ..."
  if apt-get install -y "$pkg" >> "$DEPS_LOG" 2>&1; then
    ttyprint "    OK"
    return 0
  fi
  ttyprint "    FALHOU"
  return 1
}

ensure_pip() {
  if "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    return 0
  fi

  if ! online_install_enabled; then
    ttyprint "  pip ausente e instalacao online desativada"
    return 1
  fi

  ttyprint "  pip nao encontrado; tentando habilitar..."
  "$PYTHON_BIN" -m ensurepip --upgrade >> "$DEPS_LOG" 2>&1 && return 0
  install_apt_package "python3-pip" || true
  "$PYTHON_BIN" -m pip --version >/dev/null 2>&1
}

install_pip_package() {
  local mod="$1"
  local pkg="${2:-$1}"
  if ! ensure_pip; then
    ttyprint "  pip indisponivel; nao foi possivel instalar $pkg"
    return 1
  fi

  ttyprint "  $PYTHON_BIN -m pip install $pkg ..."
  if "$PYTHON_BIN" -m pip install --user --quiet --no-cache-dir "$pkg" >> "$DEPS_LOG" 2>&1; then
    ttyprint "    OK"
    return 0
  fi
  if "$PYTHON_BIN" -m pip install --quiet --no-cache-dir --break-system-packages "$pkg" >> "$DEPS_LOG" 2>&1; then
    ttyprint "    OK (--break-system-packages)"
    return 0
  fi
  ttyprint "    FALHOU"
  return 1
}

check_python_module() {
  "$PYTHON_BIN" -B -c "import $1" >/dev/null 2>&1
}

install_dependencies() {
  ttyclear
  ttyprint "=== Verificando dependencias PokeCable ==="
  ttyprint "Python: $PYTHON_BIN"
  ttyprint "Dependencias Python: $DEPENDENCE_PYTHON_DIR"
  ttyprint "Bibliotecas nativas: $DEPENDENCE_LIB_DIR"
  ttyprint "Log de instalacao: $DEPS_LOG"
  : > "$DEPS_LOG" 2>/dev/null || true

  ttyprint "[1/2] pygame (obrigatorio)..."
  if check_python_module pygame; then
    ttyprint "  OK"
  else
    install_apt_package "python3-pygame" || install_pip_package "pygame" "pygame" || true
  fi

  ttyprint "[2/2] websockets (modo remoto legado opcional)..."
  if check_python_module websockets; then
    ttyprint "  OK"
  else
    install_apt_package "python3-websockets" || install_pip_package "websockets" "websockets" || true
  fi

  local missing=""
  if check_python_module pygame; then
    ttyprint "  pygame ... OK"
  else
    ttyprint "  pygame ... AUSENTE"
    missing="$missing pygame"
  fi
  if check_python_module websockets; then
    ttyprint "  websockets ... OK"
  else
    ttyprint "  websockets ... AUSENTE (sala LAN local continua disponivel)"
  fi

  if [ -n "$missing" ]; then
    ttyprint "ERRO: modulos ausentes:$missing"
    ttyprint "Inclua as dependencias em: $DEPENDENCE_DIR"
    ttyprint "No R36S alvo, o bundle local deve conter python/ e lib/aarch64-linux-gnu/."
    ttyprint "Para permitir download manualmente, use POKECABLE_ALLOW_ONLINE_INSTALL=1."
    ttyprint "Veja o log em: $DEPS_LOG"
    sleep 10
    return 1
  fi
  return 0
}

deps_ready() {
  check_python_module pygame
}

if ! deps_ready; then
  install_dependencies || exit 1
fi

ttyclear
ttyprint "                                .::.              "
ttyprint "                  .;:**'                          "
ttyprint "                              \`                  0"
ttyprint "  .:XHHHHk.              db.   .;;.     dH  MX   0"
ttyprint "oMMMMMMMMMMM       ~MM  dMMP :MMMMMR   MMM  MR      ~MRMN"
ttyprint "QMMMMMb  \"MMX       MMMMMMP !MX' :M~   MMM MMM  .oo. XMMM 'MMM"
ttyprint "  \`MMMM.  )M> :X!Hk. MMMM   XMM.o\"  .  MMMMMMM X?XMMM MMM>!MMP"
ttyprint "   'MMMb.dM! XM M'?M MMMMMX.\`MMMMMMMM~ MM MMM XM \`\" MX MMXXMM"
ttyprint "    ~MMMMM~ XMM. .XM XM\`\"MMMb.~*?**~ .MMX M t MMbooMM XMMMMMP"
ttyprint "     ?MMM>  YMMMMMM! MM   \`?MMRb.    \`\"\"\"   !L\"MMMMM XM IMMM"
ttyprint "      MMMX   \"MMMM\"  MM       ~%:           !Mh.\"\"\" dMI IMMP"
ttyprint "      'MMM.                                             IMX"
ttyprint "       ~M!M                                             IMP"
ttyprint ""
sleep 2

if "$PYTHON_BIN" -B -m "$PYTHON_MODULE" "$@" >> "$ERROR_LOG" 2>&1; then
  exit 0
fi

EXIT_CODE=$?
ttyclear
ttyprint "=== ERRO NA EXECUCAO ==="
ttyprint "Exit code: $EXIT_CODE"
ttyprint "Resumo do erro:"
tail -20 "$ERROR_LOG" 2>/dev/null | while IFS= read -r line; do
  ttyprint "  $line"
done
ttyprint "Log completo: $ERROR_LOG"
sleep 15
exit "$EXIT_CODE"
