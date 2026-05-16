# Seguranca De Save

Regras obrigatorias:

- Nunca edite save com o emulador aberto.
- Sempre crie backup antes de escrever.
- Verifique se o backup foi gravado corretamente.
- Nunca sobrescreva save sem backup.
- Rejeite payload recebido de outra geracao se o servidor bloquear cross-generation ou se o preflight local marcar a conversao como incompativel.
- Nao converta automaticamente entre geracoes sem `CanonicalPokemon`, `CompatibilityReport` e conversor local validado.
- Recalcule checksums apenas no parser correto da geracao.
- Mantenha Gen 1, Gen 2 e Gen 3 em parsers separados.
- Cancele a gravacao se o save mudou enquanto a sala estava aberta.
- Aplique evolucao simples por troca somente depois do backup e antes de salvar.
- Resolva movimentos incompativeis antes da escrita quando a politica permitir substituicao.
- Em troca entre dois saves locais, restaure os backups se qualquer lado falhar durante a gravacao.
- Mantenha evolucao por item desligada por padrao; os IDs de Gen 2/3 estao mapeados, mas o uso em saves reais deve ser opt-in por `item_trade_evolutions_enabled`.

## Por Que Fechar O Jogo

Emuladores podem manter o save em memoria e gravar por cima do arquivo depois. Editar o arquivo enquanto o jogo esta aberto pode perder a troca ou corromper dados.

## Servidor

O servidor nao e editor de save. Ele recebe apenas o payload do Pokemon escolhido, encaminha ao outro jogador e apaga os dados ao finalizar/cancelar.

Cross-generation deve acontecer localmente no client. O servidor apenas valida flags, protocolos, ofertas, preflight e confirmacao.

## Trocar Comigo

`Trocar comigo` nao usa servidor. A tool carrega dois saves locais diferentes e executa as mesmas etapas de seguranca sem rede:

- assina os dois saves antes do preparo;
- exporta payload dos dois Pokemon;
- roda preflight local em cada direcao;
- bloqueia antes de gravar se houver incompatibilidade nao resolvida;
- pede decisao para evolucao por troca e movimentos removidos;
- cria backup dos dois arquivos;
- grava os dois lados;
- restaura os backups se uma escrita falhar.

Esse modo depende de `Pokecable_tool/pokecable_runtime`, que contem os validadores e conversores necessarios para operar offline.

## Cross-Generation

Quando um modo cross-generation estiver habilitado, o client deve:

- gerar `CanonicalPokemon`;
- gerar `CompatibilityReport` para o save destino;
- bloquear species, egg ou moves incompatíveis conforme a politica;
- registrar `warnings`, `data_loss`, `removed_moves`, `removed_items` e `removed_fields`;
- aplicar substituicoes de moves escolhidas pelo usuario quando `removed_moves` for resolvivel;
- criar backup;
- aplicar conversor local;
- recalcular checksums no parser da geracao destino;
- cancelar se o save mudou enquanto a sala estava aberta.
