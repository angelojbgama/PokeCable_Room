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
4. Escolha `Criar sala same-generation` ou `Entrar em sala`.
5. Escolha o save.
6. Escolha o Pokemon da party.
7. Aguarde o backup ser criado antes da gravacao.
8. Reabra o jogo somente depois da mensagem de sucesso.

Os modos Time Capsule Gen 1/2, Transfer para Gen 3 e Downconvert experimental aparecem no menu como preparacao do produto. Enquanto a feature guard local estiver desligada, eles mostram que a conversao ainda nao esta habilitada. Para testes controlados, edite `config.json` e habilite apenas o modo validado:

```json
"cross_generation": {
  "enabled": true,
  "enabled_modes": ["time_capsule_gen1_gen2"],
  "policy": "safe_default"
}
```

O servidor tambem precisa estar com o mesmo modo em `ENABLED_TRADE_MODES`.

## Backup E Restore

Backups ficam em:

```text
/roms/tools/pokecable_room/backups
```

O restore pode ser feito pelo menu `Ferramentas e backups`.
