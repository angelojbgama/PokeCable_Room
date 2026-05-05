# Battle Engine Gen 1 - Progress

## Status Atual

- Gen 1 concluída.
- Suíte específica da Gen 1 passando.
- Nenhuma pendência conhecida dentro do escopo atual.

## O Que Foi Feito

- Separação da engine por geração.
- Bloqueio de batalha cruzada: Gen 1 só enfrenta Gen 1.
- Remoção da retrocompatibilidade dentro da batalha.
- Estrutura própria para modelos, dano, utilidades e engine da Gen 1.
- Implementação da formula de dano da Gen 1.
- Implementação de críticos, accuracy glitch e imunidades de tipo.
- Implementação de status majoritários: sleep, paralysis, burn, poison, toxic e freeze.
- Implementação de efeitos voláteis: confusion, flinch, partial trap, leech seed, disable, recharge, substitute e semi-invulnerabilidade.
- Implementação de movimentos e comportamentos da Gen 1: Bide, Rage, Counter, Metronome, Mimic, Mirror Move, Transform, Conversion, Disable, Leech Seed, Hyper Beam, charge moves, drain, recoil e OHKO.
- Implementação de efeitos de campo: Reflect, Light Screen, Mist e Haze.
- Cobertura de testes para dano, status, immunidades, efeitos de turno e mecânicas especiais.
- Adição de um teste de integração com saves reais de Gen 1, usando Yellow e Red, com batalha 6v6 até a exaustão.
- Normalização de PP no harness do teste real para forçar `Struggle` e manter a execução determinística.

## O Que Foi Validado

- `python3 -m pytest -q tests/test_gen1_battle_engine.py`
- `python3 -m pytest -q tests/test_gen1_battle_engine.py tests/test_gen1_real_save_battle.py`
- Resultado: `37 passed`
- `python3 -m py_compile` nos arquivos alterados da Gen 1 e nas duas suítes de teste

## O Que Falta

- Nada pendente dentro da Gen 1 neste recorte.
- Próximos passos naturais ficam na Gen 2 e Gen 3.

## Observações

- A normalização de payloads continua fora da engine de batalha.
- A fidelidade mecânica da Gen 1 deve ser mantida por regressão sempre que novas alterações forem adicionadas.
