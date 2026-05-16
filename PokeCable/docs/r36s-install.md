# Instalacao No R36S

## Tool Atual

A tool atual fica em `Pokecable_tool` e roda pelo launcher:

```text
Pokecable_tool/pokecable.sh
```

Copie a pasta inteira para o R36S, mantendo `pokecable_runtime` junto dos arquivos Python:

```text
Pokecable_tool/ -> /roms/tools/Pokecable_tool/
```

Opcionalmente crie um atalho em `/roms/tools` apontando para:

```text
/roms/tools/Pokecable_tool/pokecable.sh
```

O client antigo de sala online ainda existe em `PokeCable/backend`, mas a interface com `Trocar comigo` e runtime offline fica em `Pokecable_tool`.

## Permissao

```bash
chmod +x "/roms/tools/Pokecable_tool/pokecable.sh"
```

Abra pelo menu:

```text
Options -> Tools -> PokeCable
```

## Configurar Servidor Para Sala Online

O servidor so e necessario para `Acessar sala`.

```text
Ferramentas e backups -> Configurar servidor VPS
```

Use:

```text
wss://9kernel.vps-kinghost.net/ws
```

`Trocar comigo` nao usa servidor, WebSocket, API nem fallback online.

## Antes De Trocar

1. Salve dentro do jogo.
2. Feche o emulador.
3. Abra PokeCable Room.
4. Escolha `Acessar sala` para trocar online ou `Trocar comigo` para trocar entre dois saves locais.
5. Escolha o save.
6. Escolha o Pokemon da party.
7. Confirme as evolucoes por troca e substituicoes de movimentos quando a tool pedir.
8. Aguarde o backup ser criado antes da gravacao.
9. Reabra o jogo somente depois da mensagem de sucesso.

O menu nao pede para escolher Time Capsule, Transfer ou Downconvert. A sala e unica: cada jogador escolhe o save e o Pokemon, e o sistema valida automaticamente se a troca e same-generation ou cross-generation.

O client atualizado ja anuncia suporte tecnico a cross-generation. Use `Configurar cross-generation` no menu apenas para trocar a politica ou desligar testes. Config padrao:

```json
"cross_generation": {
  "enabled": true,
  "enabled_modes": ["time_capsule_gen1_gen2", "forward_transfer_to_gen3", "legacy_downconvert_experimental"],
  "policy": "auto_retrocompat",
  "unsafe_auto_confirm_data_loss": false
}
```

Na troca online, o servidor tambem precisa estar com os mesmos modos em `ENABLED_TRADE_MODES`. Se qualquer lado falhar no preflight, a troca inteira e bloqueada antes de gravar save.

Em `Trocar comigo`, a validacao roda localmente em `Pokecable_tool/pokecable_runtime`. Esse fluxo usa os mesmos validadores e conversores locais para retrocompatibilidade, evolucao por troca e movimentos incompatíveis, mas nunca chama o backend/API.

## Trocar Comigo

`Trocar comigo` permite selecionar dois arquivos de save diferentes no mesmo aparelho/PC e executar a troca localmente.

O fluxo faz:

- leitura dos dois saves;
- exportacao dos dois payloads;
- preflight local para cada direcao da troca;
- bloqueio antes da escrita se species, moves, itens ou campos obrigatorios forem incompativeis;
- tela de evolucao por troca quando aplicavel;
- tela para substituir movimentos que nao existem na geracao destino;
- backup dos dois saves;
- gravacao dos dois lados;
- rollback dos saves a partir do backup se alguma escrita falhar.

Esse modo e 100% offline. Se o runtime local estiver ausente, a troca falha com erro local em vez de tentar usar o backend.

## Backup E Restore

Backups ficam em:

```text
/roms/tools/Pokecable_tool/backups
```

O restore pode ser feito pelo menu `Ferramentas e backups`.
