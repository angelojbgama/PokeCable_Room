# Scripts de Teste - PokeCable Room

## Teste Completo de Retrocompatibilidade

Executa todos os 251 Pokémon com todas as combinações de ataques (~9,000 casos).

### Linux / macOS

```bash
./test_complete_coverage.sh
```

### Windows

**Opção 1: Command Prompt (CMD)**
```cmd
test_complete_coverage.bat
```

**Opção 2: PowerShell**
```powershell
.\test_complete_coverage.ps1
```

Se receber erro de execução no PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Pipeline de Testes

Executa diferentes tipos de testes (quick, api, full, complete).

### Linux / macOS

```bash
./test_pipeline.sh [quick|api|full|complete]
```

Exemplos:
```bash
./test_pipeline.sh           # Teste padrão (api)
./test_pipeline.sh quick     # Teste rápido
./test_pipeline.sh full      # Testes completos
./test_pipeline.sh complete  # Todos os Pokémon
```

### Windows

Não existe versão Windows do `test_pipeline.sh` no momento. Use:
```cmd
test_complete_coverage.bat
```

## Resultados

Todos os testes salvam resultados em:

```
./test_results/
```

(Local: `PokeCable_Room/tests/test_results/`)

Arquivos gerados:
- `pokemon_complete_coverage_report.txt` - Resumo dos testes
- `pokemon_complete_coverage_detailed.json` - Detalhes em JSON
- `pokemon_complete_coverage_errors.txt` - Erros (se houver)

## Requisitos

- **Python 3.12+**
- Dependências instaladas: `python3 -m pip install -r tests/requirements.txt pytest`

## Troubleshooting

### Python não encontrado

Windows:
```cmd
python --version
```

Se não funcionar, instale Python de https://www.python.org

### Permissão negada (bash)

```bash
chmod +x test_complete_coverage.sh
chmod +x test_pipeline.sh
```

### Erro no PowerShell

Se receber erro de execução, execute como administrador:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
