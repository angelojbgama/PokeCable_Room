# PokeCable Room R36S Client

Client Python 3 com launcher Bash para ArkOS/dArkOS no R36S. A interface usa dialog/whiptail e teclado virtual, sem desktop e sem navegador.

Este client em `PokeCable/backend` representa o fluxo de sala online. A tool atual com interface Pygame, `Trocar comigo` e runtime offline fica em `Pokecable_tool`.

## Instalar No R36S

Para a tool atual, copie:

```text
Pokecable_tool/ -> /roms/tools/Pokecable_tool/
```

Depois:

```bash
chmod +x "/roms/tools/Pokecable_tool/pokecable.sh"
```

Abra em `Options -> Tools`.

## Uso

1. Salve dentro do jogo.
2. Feche o emulador.
3. Abra PokeCable Room.
4. Escolha `Acessar sala` para online ou `Trocar comigo` para dois saves locais.
5. Escolha o save `.sav/.srm`.
6. Escolha um Pokemon da party.
7. No online, aguarde o outro jogador.
8. Confirme evolucao por troca e movimentos removidos quando a tool pedir.
9. Deixe a tool criar backup antes de gravar.

## Sala Unica

O usuario nao escolhe modo de geracao ao criar sala. O app detecta a geracao de cada save e o servidor deriva automaticamente o caminho necessario para cada direcao da troca online.

- Same-generation usa raw payload da propria geracao.
- Cross-generation usa payload canonico, preflight local e conversor local.
- Se algum Pokemon nao puder ser recebido pela geracao do outro jogador, a troca inteira e bloqueada antes do commit.
- Testar compatibilidade mostra bloqueios, avisos, transformacoes e perdas esperadas.

Suporte de troca atual: party de Gen 1, party de Gen 2 Gold/Silver/Crystal e party de Gen 3. A tool tambem lista PC/boxes para gerenciamento local de saves quando o parser da geracao suporta essa leitura/movimentacao.

Use `Configurar cross-generation` no menu apenas para trocar a politica ou desligar testes. Na politica padrao, campos incompatíveis com geracoes antigas sao removidos/normalizados automaticamente e registrados no relatorio/log.

Evolucao por item esta implementada para Gen 2/3, mas `item_trade_evolutions_enabled` permanece `false` por padrao para testes controlados.

## Trocar Comigo

`Trocar comigo` fica em `Pokecable_tool` e executa a troca entre dois saves diferentes sem servidor.

Esse fluxo reutiliza o pipeline local da sala online:

- gera payload para cada Pokemon selecionado;
- executa preflight local nos dois destinos;
- aplica evolucao por troca quando confirmada;
- permite substituir movimentos que nao existem na geracao destino;
- cria backup dos dois saves;
- grava os dois lados e restaura os backups se uma escrita falhar.

Nao ha fallback online nesse modo. O validador e os conversores ficam vendorizados em `Pokecable_tool/pokecable_runtime`.
