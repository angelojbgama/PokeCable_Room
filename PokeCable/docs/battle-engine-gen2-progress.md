# Battle Engine Gen 2 - Progress

## Status Atual

- Gen 2 está isolada em arquivos próprios e sem retrocompatibilidade dentro da engine de batalha.
- Suíte específica da Gen 2 passando.
- Batalha real 6v6 com saves de Gold / Silver / Crystal validada.
- Escopo atual da Gen 2 concluído no código e nos testes.

## O Que Foi Feito

- Separação da engine por geração com roteamento explícito para Gen 2.
- Bloqueio de batalhas entre gerações diferentes.
- Correção do parser Gen 2 para exportar `CanonicalStats` sem quebrar `export_canonical()`.
- Implementação da formula de dano da Gen 2 com split de Attack / Special Attack e Defense / Special Defense.
- Correção e validação do type chart Gen 2.
- Consumo de PP com fallback para `Struggle` quando o movimento selecionado está vazio.
- Tratamento de status majoritários e voláteis usados na engine atual.
- Implementação de Hyper Beam com recharge.
- Implementação de efeitos comuns usados pelos saves reais: Thunder Wave, Toxic, Poison Powder, Rest, Reflect, Light Screen, Agility, Swords Dance, Confuse Ray, drain, recoil, trap e screens.
- Expansão da cobertura para Fly, Disable, Encore, Leech Seed, Bide, Counter, Mirror Coat, Rollout, Fury Cutter, Metronome, Mimic, Mirror Move, Transform, Conversion, weather, Protect / Detect, Endure, Future Sight, Pursuit, Spikes, Pain Split, Heal Bell, Attract, Swagger / Charm, Belly Drum, Foresight, Lock On / Mind Reader, Dream Eater, Substitute, Selfdestruct / Explosion e Baton Pass.
- Cobertura de testes para type chart, comportamento básico da engine, mecânicas principais e interações reais de batalha.
- Adição de teste de integração com saves reais de Gen 2, usando batalha 6v6 até a exaustão.
- Adição de uma matriz exaustiva de validação com saves reais, cobrindo todos os Pokémon e movimentos disponíveis nas equipes de Gold e Silver, com relatório em `docs/battle-validation/gen2-matrix.txt`.

## O Que Foi Validado

- `python3 -m pytest -q tests/test_gen2_types.py tests/test_gen2_battle_engine.py`
- `python3 -m pytest -q tests/test_gen2_types.py tests/test_gen2_battle_engine.py tests/test_gen2_mechanics.py tests/test_gen2_real_save_battle.py`
- Resultado: `27 passed`
- `python3 -m pytest -q tests/test_gen2_validation_matrix.py`
- Resultado: `1 passed`
- Relatório da matriz: `pass=288 fail=0 total=288`
- `python3 -m py_compile` nos arquivos alterados da Gen 2 e nas suítes de teste

## O Que Falta

- Somente novas regressões ou quirks que apareçam em traces futuros de save real.
- Novos testes devem ser adicionados sempre que um caso novo aparecer.

## Observações

- A normalização de save continua fora da engine de batalha.
- A Gen 2 deve permanecer separada das outras gerações em arquivos e fluxos próprios.
