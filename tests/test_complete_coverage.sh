#!/bin/bash

# Script de Teste Completo de Retrocompatibilidade
# Sempre executa TODOS os 251 Pokémon com TODAS as combinações de ataques

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
TEST_DIR="$SCRIPT_DIR/test_results"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

main() {
    print_header "TESTE COMPLETO DE RETROCOMPATIBILIDADE"
    print_info "Modo: COMPLETE (sempre)"
    echo "Testando: 251 Pokémon × 9 combinações de gerações × 1-4 ataques"
    echo "Total esperado: ~9,000 casos de teste"
    echo ""

    mkdir -p "$TEST_DIR"

    print_info "Executando teste completo..."
    cd "$REPO_DIR"
    python3 tests/test_complete_pokemon_coverage.py

    echo ""
    print_header "RESULTADOS"

    if [ -f "$TEST_DIR/pokemon_complete_coverage_report.txt" ]; then
        cat "$TEST_DIR/pokemon_complete_coverage_report.txt"
    else
        print_error "Relatório não gerado"
        exit 1
    fi

    echo ""
    print_success "Teste completo finalizado!"
    echo "Arquivos salvos em: $TEST_DIR"
    echo "  - pokemon_complete_coverage_report.txt"
    echo "  - pokemon_complete_coverage_detailed.json"
    echo "  - pokemon_complete_coverage_errors.txt (se houver)"
}

main
