# Script de Teste Completo de Retrocompatibilidade (Windows PowerShell)
# Sempre executa TODOS os 251 Pokémon com TODAS as combinações de ataques

# Cores
$Colors = @{
    Reset  = "`e[0m"
    Blue   = "`e[34m"
    Green  = "`e[32m"
    Yellow = "`e[33m"
    Red    = "`e[31m"
}

function Print-Header {
    param([string]$Message)
    Write-Host "$($Colors.Blue)════════════════════════════════════════════════════════════════$($Colors.Reset)"
    Write-Host "$($Colors.Blue)  $Message$($Colors.Reset)"
    Write-Host "$($Colors.Blue)════════════════════════════════════════════════════════════════$($Colors.Reset)"
}

function Print-Success {
    param([string]$Message)
    Write-Host "$($Colors.Green)✓ $Message$($Colors.Reset)"
}

function Print-Error {
    param([string]$Message)
    Write-Host "$($Colors.Red)✗ $Message$($Colors.Reset)"
}

function Print-Info {
    param([string]$Message)
    Write-Host "$($Colors.Yellow)ℹ $Message$($Colors.Reset)"
}

# Determinar diretórios
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir = Split-Path -Parent $ScriptDir
$TestDir = Join-Path $env:TEMP "trade_tests"

# Criar diretório de testes
if (-not (Test-Path $TestDir)) {
    New-Item -ItemType Directory -Path $TestDir -Force | Out-Null
}

Clear-Host
Print-Header "TESTE COMPLETO DE RETROCOMPATIBILIDADE"
Print-Info "Modo: COMPLETE (sempre)"
Write-Host "Testando: 251 Pokemon x 9 combinacoes de geracoes x 1-4 ataques"
Write-Host "Total esperado: ~9,000 casos de teste"
Write-Host ""

# Verificar se Python está instalado
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3"
} else {
    Print-Error "Python 3 nao encontrado"
    Print-Info "Instale Python 3 e adicione ao PATH antes de continuar"
    exit 1
}

# Verificar versão do Python
$PythonVersion = & $PythonCmd --version 2>&1
Print-Success "Python: $PythonVersion"
Write-Host ""

Print-Info "Executando teste completo..."
Write-Host ""

# Executar teste
Push-Location $RepoDir
& $PythonCmd tests\test_complete_pokemon_coverage.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Print-Error "Teste falhou"
    Pop-Location
    exit 1
}
Pop-Location

Write-Host ""
Print-Header "RESULTADOS"
Write-Host ""

$ReportFile = Join-Path $TestDir "pokemon_complete_coverage_report.txt"
if (Test-Path $ReportFile) {
    Get-Content $ReportFile
} else {
    Print-Error "Relatorio nao gerado"
    exit 1
}

Write-Host ""
Print-Success "Teste completo finalizado!"
Write-Host ""
Write-Host "Arquivos salvos em: $TestDir"
Write-Host "  - pokemon_complete_coverage_report.txt"
Write-Host "  - pokemon_complete_coverage_detailed.json"
Write-Host "  - pokemon_complete_coverage_errors.txt (se houver)"
Write-Host ""
