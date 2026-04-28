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
4. Escolha criar sala same-generation ou entrar em sala.
5. Escolha o save `.sav/.srm`.
6. Escolha um Pokemon da party.
7. Aguarde o outro jogador.
8. Confirme e deixe a tool criar o backup.
9. Se `auto_trade_evolution` estiver ligado, evolucoes simples por troca sao aplicadas no save antes de gravar.

## Modos

- Criar sala same-generation: modo estavel atual.
- Criar sala Time Capsule Gen 1/2: preparado no menu, protegido por feature guard.
- Criar sala Transfer para Gen 3: preparado no menu, protegido por feature guard.
- Testar compatibilidade: mostra o modo planejado, bloqueios, avisos e perdas esperadas.

Suporte atual: party de Gen 1, party de Gen 2 Gold/Silver/Crystal e party de Gen 3. Boxes ainda nao estao habilitadas. Cross-generation e objetivo do produto, mas a escrita fica bloqueada ate os conversores locais serem validados.

Evolucao por item fica preparada em regras, mas `item_trade_evolutions_enabled` permanece `false` por padrao porque os IDs de item precisam ser validados em saves reais.
