#!/bin/bash

# Script de Teste Completo de Retrocompatibilidade
# Testa TODOS os 251 Pokémon com TODAS as combinações de ataques

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TEST_DIR="/tmp/trade_tests"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

main() {
    print_header "TESTE COMPLETO DE RETROCOMPATIBILIDADE"
    echo "Testando: 251 Pokémon × 9 combinações de gerações × 1-4 ataques"
    echo "Total esperado: ~9,000 casos de teste"
    echo ""

    if [ ! -f "/tmp/test_complete_pokemon_coverage.py" ]; then
        echo "Erro: test_complete_pokemon_coverage.py não encontrado"
        echo "Verifique se foi criado em /tmp/"
        exit 1
    fi

    echo "Iniciando teste..."
    python3 /tmp/test_complete_pokemon_coverage.py

    echo ""
    print_header "RESULTADOS"

    if [ -f "$TEST_DIR/pokemon_complete_coverage_report.txt" ]; then
        cat "$TEST_DIR/pokemon_complete_coverage_report.txt"
    else
        echo "Erro: Relatório não gerado"
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
