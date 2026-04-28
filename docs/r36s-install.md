# Instalacao No R36S

Copie os arquivos:

```text
r36s-client/PokeCable Room.sh -> /roms/tools/PokeCable Room.sh
r36s-client/pokecable_room -> /roms/tools/pokecable_room
```

Permissao:

```bash
chmod +x "/roms/tools/PokeCable Room.sh"
```

Abra pelo menu:

```text
Options -> Tools -> PokeCable Room
```

## Configurar Servidor

No menu:

```text
Ferramentas e backups -> Configurar servidor VPS
```

Use:

```text
wss://9kernel.vps-kinghost.net/ws
```

## Antes De Trocar

1. Salve dentro do jogo.
2. Feche o emulador.
3. Abra PokeCable Room.
4. Escolha `Criar sala` ou `Entrar em sala`.
5. Escolha o save.
6. Escolha o Pokemon da party.
7. Aguarde o backup ser criado antes da gravacao.
8. Reabra o jogo somente depois da mensagem de sucesso.

O menu nao pede para escolher Time Capsule, Transfer ou Downconvert. A sala e unica: cada jogador escolhe o save e o Pokemon, e o sistema valida automaticamente se a troca e same-generation ou cross-generation.

Para testes cross-generation, use `Configurar cross-generation` no menu ou edite `config.json` e habilite somente os modos validados:

```json
"cross_generation": {
  "enabled": true,
  "enabled_modes": ["time_capsule_gen1_gen2", "forward_transfer_to_gen3", "legacy_downconvert_experimental"],
  "policy": "safe_default",
  "unsafe_auto_confirm_data_loss": false
}
```

O servidor tambem precisa estar com os mesmos modos em `ENABLED_TRADE_MODES`. Se qualquer lado falhar no preflight, a troca inteira e bloqueada antes de gravar save.

## Backup E Restore

Backups ficam em:

```text
/roms/tools/pokecable_room/backups
```

O restore pode ser feito pelo menu `Ferramentas e backups`.
