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
BUNDLE_STATUS="not_checked"
CURRENT_ARCH=""
CURRENT_PYTHON_VERSION=""

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
  ttyprint "O PokeCable usa o Python do sistema R36S; inclua python3 na imagem/base do sistema."
  exit 1
fi

detect_runtime_target() {
  CURRENT_ARCH="$(uname -m 2>/dev/null || true)"
  CURRENT_PYTHON_VERSION="$("$PYTHON_BIN" -B -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
}

enable_dependence_bundle() {
  detect_runtime_target
  if [ "$CURRENT_ARCH" = "$DEPENDENCE_ARCH" ] && [ "$CURRENT_PYTHON_VERSION" = "$DEPENDENCE_PYTHON_VERSION" ]; then
    if [ -d "$DEPENDENCE_LIB_DIR" ]; then
      export LD_LIBRARY_PATH="$DEPENDENCE_LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    fi
    if [ -d "$DEPENDENCE_PYTHON_DIR" ]; then
      export PYTHONPATH="$DEPENDENCE_PYTHON_DIR${PYTHONPATH:+:$PYTHONPATH}"
    fi
    BUNDLE_STATUS="enabled"
    return 0
  fi

  BUNDLE_STATUS="incompatible"
  return 1
}

enable_dependence_bundle || true

cleanup() {
  if [ -w "$TTY" ]; then
    printf "\033[?25h" > "$TTY" 2>/dev/null || true
    stty sane < "$TTY" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

check_python_module() {
  "$PYTHON_BIN" -B -c "import $1" >/dev/null 2>&1
}

validate_local_dependencies() {
  ttyclear
  ttyprint "=== Verificando dependencias PokeCable ==="
  ttyprint "Python: $PYTHON_BIN"
  ttyprint "Alvo local: $DEPENDENCE_ARCH/Python $DEPENDENCE_PYTHON_VERSION"
  ttyprint "Ambiente atual: ${CURRENT_ARCH:-?}/Python ${CURRENT_PYTHON_VERSION:-?}"
  ttyprint "Dependencias Python locais: $DEPENDENCE_PYTHON_DIR"
  ttyprint "Bibliotecas nativas locais: $DEPENDENCE_LIB_DIR"
  ttyprint "Log de verificacao: $DEPS_LOG"
  : > "$DEPS_LOG" 2>/dev/null || true

  {
    echo "PokeCable dependency check"
    echo "python=$PYTHON_BIN"
    echo "target=$DEPENDENCE_ARCH/Python $DEPENDENCE_PYTHON_VERSION"
    echo "current=${CURRENT_ARCH:-?}/Python ${CURRENT_PYTHON_VERSION:-?}"
    echo "pythonpath=$PYTHONPATH"
    echo "ld_library_path=${LD_LIBRARY_PATH:-}"
  } >> "$DEPS_LOG" 2>/dev/null || true

  if [ "$BUNDLE_STATUS" != "enabled" ]; then
    ttyprint "ERRO: bundle local incompativel com este ambiente."
    ttyprint "Atual: ${CURRENT_ARCH:-?}/Python ${CURRENT_PYTHON_VERSION:-?}"
    ttyprint "Esperado: $DEPENDENCE_ARCH/Python $DEPENDENCE_PYTHON_VERSION"
    ttyprint "Use o Python do sistema R36S correto ou gere um bundle local compativel."
    ttyprint "O PokeCable nao instala dependencias pela internet."
    ttyprint "Veja o log em: $DEPS_LOG"
    sleep 10
    return 1
  fi

  local missing=""
  if [ ! -d "$DEPENDENCE_PYTHON_DIR" ]; then
    ttyprint "  python/ ... AUSENTE"
    missing="$missing python"
  else
    ttyprint "  python/ ... OK"
  fi
  if [ ! -d "$DEPENDENCE_LIB_DIR" ]; then
    ttyprint "  lib/aarch64-linux-gnu/ ... AUSENTE"
    missing="$missing lib"
  else
    ttyprint "  lib/aarch64-linux-gnu/ ... OK"
  fi

  ttyprint "[1/1] pygame local (obrigatorio)..."
  if check_python_module pygame; then
    ttyprint "  pygame ... OK"
    "$PYTHON_BIN" -B -c 'import pygame, pathlib; print("pygame_file=" + str(pathlib.Path(pygame.__file__).resolve()))' >> "$DEPS_LOG" 2>&1 || true
  else
    ttyprint "  pygame ... AUSENTE"
    missing="$missing pygame"
    "$PYTHON_BIN" -B -c 'import pygame' >> "$DEPS_LOG" 2>&1 || true
  fi

  if [ -n "$missing" ]; then
    ttyprint "ERRO: dependencias locais ausentes ou invalidas:$missing"
    ttyprint "Corrija o pacote em: $DEPENDENCE_DIR"
    ttyprint "O bundle deve conter pygame em python/ e libs nativas em lib/aarch64-linux-gnu/."
    ttyprint "Nenhuma instalacao via apt/pip sera tentada."
    ttyprint "Veja detalhes em: $DEPS_LOG"
    sleep 10
    return 1
  fi
  return 0
}

deps_ready() {
  [ "$BUNDLE_STATUS" = "enabled" ] && check_python_module pygame
}

if ! deps_ready; then
  validate_local_dependencies || exit 1
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
