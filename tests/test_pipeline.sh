#!/bin/bash

# Script de teste do pipeline de troca Pokémon PokeCable Room
# Uso: ./test_pipeline.sh [full|api|quick]

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
TEST_DIR="/tmp/trade_tests"
BACKEND_PID=""

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

cleanup() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        print_info "Parando backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Verificar dependências
check_dependencies() {
    print_header "Verificando Dependências"

    local missing=0

    # Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 não encontrado"
        missing=$((missing + 1))
    else
        print_success "Python 3: $(python3 --version)"
    fi

    # Node.js para validações
    if ! command -v node &> /dev/null; then
        print_info "Node.js não encontrado (opcional)"
    else
        print_success "Node.js: $(node --version)"
    fi

    if [ $missing -gt 0 ]; then
        print_error "Dependências faltando. Instale antes de continuar."
        exit 1
    fi

    print_success "Todas as dependências OK"
    echo ""
}

# Iniciar backend
start_backend() {
    print_header "Iniciando Backend"

    cd "$REPO_DIR/PokeCable/api"

    # Verificar se está rodando
    if curl -s http://localhost:8000/health | grep -q "ok"; then
        print_success "Backend já está rodando em localhost:8000"
        return 0
    fi

    # Instalar dependências se necessário
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt não encontrado"
        exit 1
    fi

    print_info "Backend não está rodando. Iniciando..."

    # Ativar venv se existir
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi

    # Instalar dependências
    python3 -m pip install -q fastapi uvicorn websockets 2>/dev/null || true

    # Iniciar backend em background
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!

    # Aguardar backend iniciar
    local attempts=0
    while [ $attempts -lt 10 ]; do
        if curl -s http://localhost:8000/health | grep -q "ok"; then
            print_success "Backend iniciado (PID: $BACKEND_PID)"
            echo ""
            return 0
        fi
        attempts=$((attempts + 1))
        sleep 1
    done

    print_error "Backend falhou ao iniciar"
    tail -20 /tmp/backend.log
    exit 1
}

# Executar testes
run_tests() {
    local test_type="${1:-api}"

    print_header "Executando Testes - Tipo: $test_type"

    mkdir -p "$TEST_DIR"

    case $test_type in
        quick)
            print_info "Modo Quick: Teste rápido (360 casos)"
            cd "$REPO_DIR"
            python3 tests/test_trade_pipeline.py
            ;;
        api)
            print_info "Modo API: Teste com saves reais (100 casos)"
            cd "$REPO_DIR"
            python3 tests/test_trade_pipeline_api.py
            ;;
        full)
            print_info "Modo Full: Testes abrangentes (460 casos)"
            cd "$REPO_DIR"
            python3 tests/test_trade_pipeline.py
            python3 tests/test_trade_pipeline_api.py
            ;;
        complete)
            print_info "Modo Complete: TODOS os 251 Pokémon (~9,000 casos)"
            cd "$REPO_DIR"
            python3 tests/test_complete_pokemon_coverage.py
            ;;
        *)
            print_error "Tipo de teste desconhecido: $test_type"
            print_info "Tipos válidos: quick, api, full, complete"
            exit 1
            ;;
    esac

    echo ""
}

# Exibir resultados
show_results() {
    print_header "Resultados dos Testes"

    if [ -f "$TEST_DIR/trade_tests_api_report.txt" ]; then
        cat "$TEST_DIR/trade_tests_api_report.txt"
    else
        print_error "Nenhum relatório encontrado"
        return 1
    fi

    echo ""
    print_success "Relatórios salvos em: $TEST_DIR"
    echo "  - trade_tests_api_report.txt (resumo)"
    echo "  - trade_tests_api_detailed.json (detalhes JSON)"
    echo ""
}

# Main
main() {
    local test_mode="${1:-api}"

    print_header "TESTE DE PIPELINE DE TROCA POKÉMON"
    print_info "Modo: $test_mode"
    echo ""

    check_dependencies
    start_backend
    run_tests "$test_mode"
    show_results

    print_success "Testes completados com sucesso!"
}

# Mostrar uso
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Uso: $0 [quick|api|full|complete]"
    echo ""
    echo "Modos de teste:"
    echo "  quick    - Teste rápido (360 casos, 10 Pokémon)"
    echo "  api      - Teste com API real e saves reais (100 casos)"
    echo "  full     - Testes completos (quick + api = 460 casos)"
    echo "  complete - TODOS os 251 Pokémon com todos os ataques (~9,000 casos)"
    echo ""
    echo "Exemplos:"
    echo "  $0           # Executa teste 'api' (padrão)"
    echo "  $0 quick     # Executa teste rápido"
    echo "  $0 full      # Executa testes completos"
    echo "  $0 complete  # Executa teste completo de retrocompatibilidade"
    exit 0
fi

main "$1"
