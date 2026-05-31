#!/bin/bash

# Offline/local test driver for PokeCable.
# Usage: ./tests/test_pipeline.sh [quick|api|full|complete]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}OK${NC} $1"
}

print_error() {
    echo -e "${RED}ERRO${NC} $1"
}

print_info() {
    echo -e "${YELLOW}INFO${NC} $1"
}

check_dependencies() {
    print_header "Verificando dependencias"

    if ! command -v python3 >/dev/null 2>&1; then
        print_error "Python 3 nao encontrado"
        exit 1
    fi
    print_success "Python 3: $(python3 --version)"

    if ! python3 -m pytest --version >/dev/null 2>&1; then
        print_error "pytest nao encontrado"
        print_info "Instale as dependencias de teste com: python3 -m pip install -r tests/requirements.txt pytest"
        exit 1
    fi
    print_success "pytest disponivel"
}

run_pytest() {
    cd "$REPO_DIR"
    PYTHONPATH="$REPO_DIR/Pokecable_tool:$REPO_DIR" python3 -m pytest "$@"
}

run_tests() {
    local test_type="${1:-api}"

    print_header "Executando testes locais: $test_type"

    case "$test_type" in
        quick)
            run_pytest tests/test_compatibility_matrix.py tests/test_trade_e2e_curated.py
            ;;
        api)
            print_info "Alias legado: 'api' agora executa o pipeline local sem backend."
            run_pytest tests/test_pokecable_save_tool.py tests/test_trade_e2e_curated.py
            ;;
        full)
            python3 tests/stress_cross_gen.py
            python3 tests/test_save_roundtrip.py
            python3 tests/test_full_coverage.py
            ;;
        complete)
            run_pytest tests/test_pokedex_complete.py tests/test_full_coverage.py
            ;;
        *)
            print_error "Tipo de teste desconhecido: $test_type"
            print_info "Tipos validos: quick, api, full, complete"
            exit 1
            ;;
    esac
}

main() {
    local test_mode="${1:-api}"

    print_header "Teste de pipeline PokeCable"
    print_info "Modo: $test_mode"

    check_dependencies
    run_tests "$test_mode"

    print_success "Testes completados"
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    echo "Uso: $0 [quick|api|full|complete]"
    echo ""
    echo "Modos de teste:"
    echo "  quick    - Testes locais rapidos de compatibilidade e troca"
    echo "  api      - Alias legado; roda testes locais sem backend"
    echo "  full     - Drivers principais: stress, roundtrip e cobertura"
    echo "  complete - Cobertura de Pokedex e cobertura geral"
    exit 0
fi

main "${1:-api}"
