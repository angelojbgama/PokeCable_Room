# Battle Engine Gen 2 - Progress

## Status Atual

- Gen 2 está isolada em arquivos próprios e sem retrocompatibilidade dentro da engine de batalha.
- Suíte específica da Gen 2 passando.
- Batalha real 6v6 com saves de Gold / Silver / Crystal validada.

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
- Expansão da cobertura para Fly, Disable, Encore, Leech Seed, Bide, Counter, Mirror Coat, Rollout, Fury Cutter, Metronome, Mimic, Mirror Move, Transform, Conversion e weather.
- Cobertura de testes para type chart, comportamento básico da engine e mecânicas principais.
- Adição de teste de integração com saves reais de Gen 2, usando batalha 6v6 até a exaustão.

## O Que Foi Validado

- `python3 -m pytest -q tests/test_gen2_types.py tests/test_gen2_battle_engine.py`
- `python3 -m pytest -q tests/test_gen2_types.py tests/test_gen2_battle_engine.py tests/test_gen2_mechanics.py tests/test_gen2_real_save_battle.py`
- Resultado: `18 passed`
- `python3 -m py_compile` nos arquivos alterados da Gen 2 e nas suítes de teste

## O Que Falta

- Extensões futuras de fidelidade para famílias de movimentos mais raras ou mais complexas, como Protect / Detect, Spikes, Pain Split, Heal Bell, Future Sight, Pursuit, Endure, Present, Attract, Swagger / Charm, Belly Drum e outros edge cases raros da Gen 2.
- Novos testes devem ser adicionados sempre que esses casos forem implementados.

## Observações

- A normalização de save continua fora da engine de batalha.
- A Gen 2 deve permanecer separada das outras gerações em arquivos e fluxos próprios.
