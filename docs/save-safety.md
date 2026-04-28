# Seguranca De Save

Regras obrigatorias:

- Nunca edite save com o emulador aberto.
- Sempre crie backup antes de escrever.
- Verifique se o backup foi gravado corretamente.
- Nunca sobrescreva save sem backup.
- Rejeite payload recebido de outra geracao enquanto a feature guard cross-generation estiver desligada.
- Nao converta automaticamente entre geracoes sem `CanonicalPokemon`, `CompatibilityReport` e conversor local validado.
- Recalcule checksums apenas no parser correto da geracao.
- Mantenha Gen 1, Gen 2 e Gen 3 em parsers separados.
- Cancele a gravacao se o save mudou enquanto a sala estava aberta.
- Aplique evolucao simples por troca somente depois do backup e antes de salvar.
- Mantenha evolucao por item desligada ate validar IDs reais de item por geracao.

## Por Que Fechar O Jogo

Emuladores podem manter o save em memoria e gravar por cima do arquivo depois. Editar o arquivo enquanto o jogo esta aberto pode perder a troca ou corromper dados.

## Servidor

O servidor nao e editor de save. Ele recebe apenas o payload do Pokemon escolhido, encaminha ao outro jogador e apaga os dados ao finalizar/cancelar.

Cross-generation deve acontecer localmente no client. O servidor apenas valida modo, compatibilidade declarada, ofertas e confirmacao.
