@echo off
REM Script de Teste Completo de Retrocompatibilidade (Windows)
REM Sempre executa TODOS os 251 Pokémon com TODAS as combinações de ataques

setlocal enabledelayedexpansion

REM Determinar diretórios
for %%I in ("%~dp0.") do set "SCRIPT_DIR=%%~fI"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_DIR=%%~fI"
set "TEST_DIR=%TEMP%\trade_tests"

REM Criar diretório de testes
if not exist "%TEST_DIR%" mkdir "%TEST_DIR%"

REM Cores (usando modo simples - Windows não suporta ANSI por padrão)
set "RESET=[0m"
set "BLUE=[34m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "RED=[31m"

cls
echo.
echo ========================================================================
echo   TESTE COMPLETO DE RETROCOMPATIBILIDADE
echo ========================================================================
echo.
echo Modo: COMPLETE (sempre)
echo Testando: 251 Pokemon x 9 combinacoes de geracoes x 1-4 ataques
echo Total esperado: ~9,000 casos de teste
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Erro: Python 3 nao encontrado
    echo Instale Python 3 e adicione ao PATH antes de continuar
    exit /b 1
)

echo [i] Executando teste completo...
echo.

cd /d "%REPO_DIR%"
python tests\test_complete_pokemon_coverage.py

if errorlevel 1 (
    echo.
    echo Erro: Teste falhou
    exit /b 1
)

echo.
echo ========================================================================
echo   RESULTADOS
echo ========================================================================
echo.

if exist "%TEST_DIR%\pokemon_complete_coverage_report.txt" (
    type "%TEST_DIR%\pokemon_complete_coverage_report.txt"
) else (
    echo Erro: Relatorio nao gerado
    exit /b 1
)

echo.
echo [OK] Teste completo finalizado!
echo.
echo Arquivos salvos em: %TEST_DIR%
echo   - pokemon_complete_coverage_report.txt
echo   - pokemon_complete_coverage_detailed.json
echo   - pokemon_complete_coverage_errors.txt (se houver)
echo.

endlocal
