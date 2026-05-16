# Testes do Pipeline de Troca

Documentação completa do sistema de testes para validar o pipeline de troca de Pokémon entre gerações.

## Visão Geral

O sistema de testes valida:
- **Same-gen trades** - trocas dentro da mesma geração (Gen1↔Gen1, Gen2↔Gen2, Gen3↔Gen3)
- **Cross-gen trades** - trocas entre gerações diferentes (Gen1→Gen2, Gen2→Gen3, etc)
- **Trocar comigo** - troca local entre dois saves, sem backend/API
- **Todas as combinações** - 9 combinações possíveis de gerações
- **Pokémon modelados** - 251 Pokémon no conjunto completo de retrocompatibilidade atual
- **Todos os movesets** - múltiplas combinações de ataques por Pokémon
- **Compatibilidade de dados** - validação de perda/ganho de dados cross-gen

## Tipos de Teste

### 1. Teste Focado Da Tool
```bash
pytest -q tests/test_pokecable_save_tool.py
```
- **Cobertura:** gerenciamento Party/PC, escrita em save, `Trocar comigo`, backup/rollback e runtime offline
- **Propósito:** validar a tool atual antes de testar fluxos maiores
- **Inclui:** evolução por troca, bloqueio de mesmo save, `resolved_moves` e preflight sem chamada online

### 2. Teste Rápido (Quick)
```bash
./tests/test_pipeline.sh quick
```
- **Cobertura:** 10 Pokémon × 9 combinações gen × 4 movesets = 360 casos
- **Tempo:** ~0.5 segundos
- **Propósito:** Validação rápida do sistema
- **Workers:** 8 threads paralelas

### 3. Teste com API (API)
```bash
./tests/test_pipeline.sh api
```
- **Cobertura:** 5 saves reais × 5 saves reais × 4 Pokémon = 100 casos
- **Tempo:** ~2 segundos
- **Propósito:** Validação com dados reais
- **Dados:** Saves de Gen1 (Blue, Red, Yellow) e Gen3 (Emerald, Ruby)
- **Workers:** 4 threads paralelas

### 4. Teste Completo (Full)
```bash
./tests/test_pipeline.sh full
```
- **Cobertura:** Teste Quick + Teste API = 460 casos
- **Tempo:** ~3 segundos
- **Propósito:** Validação abrangente
- **Workers:** 8 + 4 threads

### 5. Teste de Retrocompatibilidade Completa (Complete)
```bash
./tests/test_pipeline.sh complete
```
- **Cobertura:** 251 Pokémon × 9 combinações gen × 4 movesets ≈ 9,027 casos
- **Tempo:** ~0.2 segundos
- **Propósito:** Validação total de retrocompatibilidade
- **Workers:** 16 threads paralelas

## Como Executar

### Opção 1: Via script principal (recomendado)
```bash
cd /mnt/c/Users/Angelo/Documents/projetos/PokeCable_Room
pytest -q tests/test_pokecable_save_tool.py
./tests/test_pipeline.sh
```

### Opção 2: Modo específico
```bash
./tests/test_pipeline.sh quick      # 360 testes
./tests/test_pipeline.sh api        # 100 testes com saves reais
./tests/test_pipeline.sh full       # 460 testes (quick + api)
./tests/test_pipeline.sh complete   # 9,027 testes (todos os 251 Pokémon)
```

### Opção 3: Scripts diretos
```bash
./tests/test_complete_coverage.sh
python3 ./tests/test_complete_pokemon_coverage.py
```

## Resultados dos Testes

### Estrutura de Saída
```
/tmp/trade_tests/
├── trade_tests_report.txt              # Teste quick
├── trade_tests_detailed.json           # Teste quick (JSON)
├── trade_tests_api_report.txt          # Teste api
├── trade_tests_api_detailed.json       # Teste api (JSON)
├── trade_tests_api_errors.txt          # Erros do teste api (se houver)
├── pokemon_complete_coverage_report.txt        # Teste complete
├── pokemon_complete_coverage_detailed.json     # Teste complete (JSON)
└── pokemon_complete_coverage_errors.txt        # Erros do teste complete (se houver)
```

### Exemplo de Resultado Bem-Sucedido

```
================================================================================
RELATÓRIO DE TESTES - PIPELINE DE TROCA POKÉMON
================================================================================

RESUMO EXECUTIVO:
  Data/Hora: 2026-05-11 18:31:28
  Duração total: 0.00s
  Total de testes: 100
  Passou: 100 (100.0%)
  Falhou: 0 (0.0%)
  Tempo médio por teste: 0.0002s/teste

TESTES POR COMBINAÇÃO DE GERAÇÕES:
  ✓ Gen1→Gen1      :  36/ 36 ( 100.0%)
  ✓ Gen1→Gen3      :  24/ 24 ( 100.0%)
  ✓ Gen3→Gen1      :  24/ 24 ( 100.0%)
  ✓ Gen3→Gen3      :  16/ 16 ( 100.0%)

TESTES SAME-GEN (compatibilidade garantida):
  Resultado: 52/52 ✓

TESTES CROSS-GEN (compatibilidade validada):
  Resultado: 48/48 ✓

================================================================================
CONCLUSÃO:
✓ TODOS OS TESTES PASSARAM - PIPELINE VALIDADO
================================================================================
```

## Interpretação de Erros

Se um teste falhar, procure pelo arquivo de erros:

```bash
cat /tmp/trade_tests/trade_tests_api_errors.txt
```

### Padrões Comuns de Erro

**Todos os erros em uma geração específica?**
- Problema específico dessa geração
- Verificar dados de compatibilidade dessa gen

**Todos os erros em um Pokémon?**
- Dados corrompidos ou incompletos
- Revisar entrada desse Pokémon

**Apenas cross-gen backward (Gen3→Gen1)?**
- Normal, há perda de dados
- Validar se perda é esperada

**Apenas Gen2?**
- Possível incompatibilidade de dados gen2
- Revisar suporte gen2

## Estrutura dos Testes

### Scripts Python

**test_trade_pipeline.py** (modo quick - 360 testes)
- 10 Pokémon hardcoded
- Movesets simulados
- 8 threads paralelas
- Validação básica

**test_trade_pipeline_api.py** (modo api - 100 testes)
- Saves reais de Gen1 e Gen3
- Validação com API
- 4 threads paralelas
- Relatório detalhado

**test_complete_pokemon_coverage.py** (modo complete - 9,027 testes)
- 251 Pokémon
- Todos os ataques possíveis
- 16 threads paralelas
- Cobertura máxima

### Script Principal

**test_pipeline.sh**
- Interface unificada
- Gerencia dependências
- Inicia backend automaticamente
- Cleanup de resources
- Suporta 4 modos: quick, api, full, complete

**test_pokecable_save_tool.py**
- Exercita a tool atual em `Pokecable_tool`
- Valida movimentacao Party/PC quando suportada pelo parser
- Valida `prepare_self_trade` e `execute_self_trade`
- Confirma que `Trocar comigo` usa runtime local vendorizado
- Confirma que o preflight offline nao chama `_runtime_post`
- Confirma que `resolved_moves` chega ao commit dos dois saves

## Pokémon Testados

### Quick/API (10 Pokémon)
1. Bulbasaur
2. Charmander
3. Squirtle
4. Pikachu
5. Jigglypuff
6. Psyduck
7. Poliwag
8. Ponyta
9. Gastly
10. Dratini

### Complete (251 Pokémon)
Todos os Pokémon modelados no conjunto completo de retrocompatibilidade atual.

## Combinações de Gerações Testadas

**Same-gen (3):**
- Gen1 ↔ Gen1
- Gen2 ↔ Gen2
- Gen3 ↔ Gen3

**Cross-gen Forward (3):**
- Gen1 → Gen2
- Gen1 → Gen3
- Gen2 → Gen3

**Cross-gen Backward (3):**
- Gen2 → Gen1
- Gen3 → Gen1
- Gen3 → Gen2

## Moveset Testados

Por Pokémon, validam-se:
- 1 ataque (validação mínima)
- 2 ataques (validação base)
- 3 ataques (validação estendida)
- 4 ataques (máximo na party)

## Troubleshooting

### Validador local indisponivel
```bash
pytest -q tests/test_pokecable_save_tool.py
```

Se aparecer erro como `No module named runtime_services`, verifique se a pasta abaixo existe junto da tool:

```text
Pokecable_tool/pokecable_runtime/runtime_services.py
```

`Trocar comigo` nao deve tentar usar `PokeCable/api` ou `PokeCable/backend` como fallback.

### Backend não inicia
```bash
# Verificar erros
tail -50 /tmp/backend.log

# Limpar portas
lsof -i :8000
kill -9 <PID>

# Tentar manualmente
cd PokeCable/api
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Saves não encontrados
```bash
# Verificar existência
ls -la roms/test-saves/gen*/*.sav
ls -la PokeCable/test-saves/gen*/*.sav

# Caminhos usados no repositório
./roms/test-saves/gen\ 1/Pokémon\ -\ Blue\ Version.sav
./PokeCable/test-saves/gen\ 3/Pokémon\ -\ Emerald\ Version.sav
```

### Testes timeout
```bash
# Aumentar timeout no script
TIMEOUT = 30  # de 10 para 30 segundos

# Ou reduzir workers
MAX_WORKERS = 2  # reduzir de 4
```

## Logs

### Console Output
- Barra de progresso em tempo real
- Estatísticas ao vivo (✓ passou, ✗ falhou)
- Tempo decorrido

### JSON Detalhado
Contém:
- Metadata (timestamps, duração)
- Resultados por teste
- Cobertura por Pokémon
- Primeiros erros (se houver)

## Checklist de Deploy

Antes de considerar o pipeline pronto para produção:

- [ ] Teste da tool passa
- [ ] Teste quick passa (100%)
- [ ] Teste api passa (100%)
- [ ] Teste complete passa (100%)
- [ ] Sem timeouts
- [ ] Sem erros de compatibilidade
- [ ] `Trocar comigo` funciona offline sem backend/API
- [ ] Same-gen trades funcionam (todas as 3)
- [ ] Cross-gen trades funcionam (todas as 6)
- [ ] Moveset complexos são respeitados
- [ ] Backend não lança exceções

## Próximos Passos

1. **Teste Manual Completo**
   - Abrir `Pokecable_tool/pokecable.sh`
   - Executar `Trocar comigo` com dois saves diferentes
   - Fazer troca com múltiplos ataques
   - Validar backup, evolucao por troca e save modificado

2. **Teste com Mais Pokémon**
   - Expandir POKEMON_DATA em test_trade_pipeline.py
   - Validar novo ataques

3. **Teste de Performance**
   - Medir tempo de troca real
   - Validar ocupação de memória
   - Teste de carga com múltiplas salas

## Status

- **Tool/Self Trade:** coberto por `tests/test_pokecable_save_tool.py`
- **Cobertura Quick:** 10 Pokémon, 360 casos ✓
- **Cobertura API:** 5 saves, 100 casos ✓
- **Cobertura Complete:** 251 Pokémon modelados, 9,027 casos ✓
- **Validação Total:** depende da execucao local dos testes acima
