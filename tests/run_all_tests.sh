#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TESTS_DIR="$ROOT_DIR/tests"
RESULTS_DIR="$TESTS_DIR/test_results"
MODE="${1:-api}"

SAVE_DIR_OVERRIDE="${POKECABLE_TEST_SAVE_DIR:-$ROOT_DIR/roms/test-saves}"
API_URL_OVERRIDE="${POKECABLE_TEST_API_URL:-http://localhost:8000}"

mkdir -p "$RESULTS_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
SUMMARY_FILE="$RESULTS_DIR/run_all_tests_summary_${TS}.txt"

run_step() {
  local name="$1"
  shift
  local log_file="$RESULTS_DIR/${name}_${TS}.log"
  echo "[RUN] $name" | tee -a "$SUMMARY_FILE"
  echo "[CMD] $*" | tee -a "$SUMMARY_FILE"
  if POKECABLE_TEST_SAVE_DIR="$SAVE_DIR_OVERRIDE" POKECABLE_TEST_API_URL="$API_URL_OVERRIDE" "$@" >"$log_file" 2>&1; then
    echo "[PASS] $name" | tee -a "$SUMMARY_FILE"
    return 0
  else
    local code=$?
    echo "[FAIL] $name (exit=$code)" | tee -a "$SUMMARY_FILE"
    echo "[LOG] $log_file" | tee -a "$SUMMARY_FILE"
    return $code
  fi
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 nao encontrado no PATH" | tee -a "$SUMMARY_FILE"
  exit 1
fi

cd "$ROOT_DIR" || exit 1

echo "PokeCable tests runner" > "$SUMMARY_FILE"
echo "Root: $ROOT_DIR" >> "$SUMMARY_FILE"
echo "Mode: $MODE" >> "$SUMMARY_FILE"
echo "Save dir: $SAVE_DIR_OVERRIDE" >> "$SUMMARY_FILE"
echo "API URL: $API_URL_OVERRIDE" >> "$SUMMARY_FILE"
echo "Timestamp: $TS" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

failures=0

case "$MODE" in
  quick)
    run_step "trade_pipeline" python3 tests/test_trade_pipeline.py || failures=$((failures + 1))
    run_step "trade_pipeline_api" python3 tests/test_trade_pipeline_api.py || failures=$((failures + 1))
    ;;
  api)
    run_step "trade_pipeline_api" python3 tests/test_trade_pipeline_api.py || failures=$((failures + 1))
    ;;
  full)
    run_step "trade_pipeline" python3 tests/test_trade_pipeline.py || failures=$((failures + 1))
    run_step "trade_pipeline_api" python3 tests/test_trade_pipeline_api.py || failures=$((failures + 1))
    run_step "cross_generation_trades" python3 tests/test_cross_generation_trades.py || failures=$((failures + 1))
    run_step "moves_compatibility" python3 tests/test_moves_compatibility.py || failures=$((failures + 1))
    run_step "real_saves_coverage" python3 tests/test_real_saves_coverage.py || failures=$((failures + 1))
    ;;
  complete)
    run_step "complete_coverage" bash tests/test_complete_coverage.sh || failures=$((failures + 1))
    ;;
  *)
    echo "Modo invalido: $MODE" | tee -a "$SUMMARY_FILE"
    echo "Use: quick | api | full | complete" | tee -a "$SUMMARY_FILE"
    exit 2
    ;;
esac

echo "" | tee -a "$SUMMARY_FILE"
if [ "$failures" -eq 0 ]; then
  echo "RESULTADO FINAL: PASS" | tee -a "$SUMMARY_FILE"
  echo "Resumo: $SUMMARY_FILE"
  exit 0
else
  echo "RESULTADO FINAL: FAIL ($failures etapa(s))" | tee -a "$SUMMARY_FILE"
  echo "Resumo: $SUMMARY_FILE"
  exit 1
fi
