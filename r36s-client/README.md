# PokeCable Room R36S Client

Client Python 3 com launcher Bash para ArkOS/dArkOS no R36S. A interface usa dialog/whiptail e teclado virtual, sem desktop e sem navegador.

## Instalar No R36S

Copie:

```text
r36s-client/PokeCable Room.sh -> /roms/tools/PokeCable Room.sh
r36s-client/pokecable_room -> /roms/tools/pokecable_room
```

Depois:

```bash
chmod +x "/roms/tools/PokeCable Room.sh"
```

Abra em `Options -> Tools`.

## Uso

1. Salve dentro do jogo.
2. Feche o emulador.
3. Abra PokeCable Room.
4. Escolha criar sala ou entrar em sala.
5. Escolha o save `.sav/.srm`.
6. Escolha um Pokemon da party.
7. Aguarde o outro jogador.
8. Confirme e deixe a tool criar o backup.
9. Se `auto_trade_evolution` estiver ligado, evolucoes simples por troca sao aplicadas no save antes de gravar.

## Sala Unica

O usuario nao escolhe modo de geracao ao criar sala. O app detecta a geracao de cada save e o servidor deriva automaticamente o caminho necessario para cada direcao da troca.

- Same-generation usa raw payload da propria geracao.
- Cross-generation usa payload canonico, preflight local e conversor local.
- Se algum Pokemon nao puder ser recebido pela geracao do outro jogador, a troca inteira e bloqueada antes do commit.
- Testar compatibilidade mostra bloqueios, avisos, transformacoes e perdas esperadas.

Suporte atual: party de Gen 1, party de Gen 2 Gold/Silver/Crystal e party de Gen 3. Boxes ainda nao estao habilitadas. Cross-generation fica desligado por padrao e exige flags no client e no servidor.

Evolucao por item esta implementada para Gen 2/3, mas `item_trade_evolutions_enabled` permanece `false` por padrao para testes controlados.
