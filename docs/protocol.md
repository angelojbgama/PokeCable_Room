# Protocolo WebSocket

Endpoint:

```text
GET /health
WS  /ws
```

O servidor envia primeiro:

```json
{"type": "connected", "client_id": "..."}
```

## Fluxo De Sala

Criar:

```json
{
  "type": "create_room",
  "room_name": "crystal-paqueta",
  "password": "senha",
  "generation": 2,
  "game": "pokemon_crystal",
  "supported_protocols": ["raw_same_generation", "canonical_cross_generation"],
  "supported_trade_modes": ["same_generation", "time_capsule_gen1_gen2", "forward_transfer_to_gen3"]
}
```

`trade_mode` nao e necessario para criar sala. Se um client legado enviar esse campo, o servidor trata apenas como debug/compatibilidade; a logica real deriva os modos quando os dois jogadores estao na sala.

Entrar:

```json
{
  "type": "join_room",
  "room_name": "crystal-paqueta",
  "password": "senha",
  "generation": 2,
  "game": "pokemon_crystal",
  "supported_protocols": ["raw_same_generation", "canonical_cross_generation"],
  "supported_trade_modes": ["same_generation", "time_capsule_gen1_gen2", "forward_transfer_to_gen3"]
}
```

Respostas principais:

- `room_created`
- `room_joined`
- `room_waiting`
- `room_ready`
- `generation_mismatch`
- `game_mismatch`
- `error`

## Sala

`room` inclui:

```json
{
  "room_name": "crystal-paqueta",
  "generation": 2,
  "trade_mode": "same_generation",
  "derived_modes": {
    "A": "same_generation",
    "B": "same_generation"
  },
  "preflight_ok": {
    "A": false,
    "B": false
  },
  "compatibility_status": {
    "compatible": true,
    "mode": "same_generation",
    "blocking_reasons": []
  },
  "players": {}
}
```

`derived_modes["A"]` representa o modo necessario para o Pokemon que o jogador A vai receber. `derived_modes["B"]` representa o modo necessario para o Pokemon que o jogador B vai receber.

Exemplo Gen 1 <-> Gen 3:

```json
{
  "derived_modes": {
    "A": "legacy_downconvert_experimental",
    "B": "forward_transfer_to_gen3"
  }
}
```

## Payload V2

Same-generation mantem raw data:

```json
{
  "type": "offer_pokemon",
  "payload": {
    "payload_version": 2,
    "generation": 2,
    "game": "pokemon_crystal",
    "source_generation": 2,
    "source_game": "pokemon_crystal",
    "target_generation": 2,
    "trade_mode": "same_generation",
    "species_id": 64,
    "species_name": "Kadabra",
    "level": 32,
    "nickname": "KADABRA",
    "ot_name": "ANGELO",
    "trainer_id": 12345,
    "raw_data_base64": "...",
    "raw": {
      "format": "gen2-crystal-party-v1",
      "data_base64": "...",
      "checksum": "..."
    },
    "summary": {
      "display_summary": "Kadabra Lv. 32"
    },
    "canonical": {},
    "compatibility_report": {}
  }
}
```

Cross-generation usa o mesmo envelope com escrita local por conversor. `payload.trade_mode` e opcional/legado; o servidor deriva o modo pela geracao de origem e destino. O servidor nao converte e nao grava save.

Payload cross-generation usa `canonical` como dado principal. `raw_data_base64` nao deve ser usado para escrita direta no destino quando `source_generation != target_generation`:

```json
{
  "payload_version": 2,
  "generation": 2,
  "game": "pokemon_crystal",
  "source_generation": 2,
  "source_game": "pokemon_crystal",
  "target_generation": 3,
  "species_id": 64,
  "species_name": "Kadabra",
  "summary": {
    "display_summary": "KADABRA Lv. 32"
  },
  "canonical": {
    "source_generation": 2,
    "source_game": "pokemon_crystal",
    "species": {
      "national_dex_id": 64,
      "source_species_id": 64,
      "source_species_id_space": "national_dex",
      "name": "Kadabra"
    }
  },
  "raw": {},
  "compatibility_report": {
    "compatible": true,
    "mode": "forward_transfer_to_gen3",
    "warnings": [],
    "data_loss": [],
    "transformations": []
  }
}
```

## Preflight

Depois que os dois jogadores enviam oferta, o servidor envia `preflight_required` para cada client com o Pokemon que aquele client receberia:

```json
{
  "type": "preflight_required",
  "received_payload": {},
  "source_generation": 3,
  "target_generation": 1,
  "derived_mode": "legacy_downconvert_experimental"
}
```

O client valida localmente o payload recebido. Same-generation valida raw da mesma geracao. Cross-generation exige `canonical`, gera `CompatibilityReport` e verifica moves, items, species e perdas de dados.

Resultado compativel:

```json
{
  "type": "preflight_result",
  "compatible": true,
  "requires_user_confirmation": false,
  "report": {}
}
```

Resultado bloqueado:

```json
{
  "type": "preflight_result",
  "compatible": false,
  "report": {
    "blocking_reasons": [
      "Treecko National Dex #252 nao existe na Gen 1."
    ]
  }
}
```

Se qualquer lado falhar, o servidor envia `trade_blocked` para os dois jogadores e ninguem recebe commit. Se os dois lados passarem, o servidor envia `preflight_ready` e somente entao aceita `confirm_trade`.

## Confirmacao

```json
{"type": "confirm_trade"}
```

Quando os dois preflights passam e os dois confirmam, o servidor nao manda a escrita final imediatamente. Primeiro ele pede preparo local:

```json
{
  "type": "prepare_write",
  "received_payload": {},
  "sent_payload": {},
  "message": "Preparo de escrita autorizado."
}
```

Cada client valida novamente a assinatura forte do save local, cria backup e responde:

```json
{
  "type": "write_ready",
  "ready": true,
  "metadata": {
    "backup_path": "/tmp/exemplo.sav.bak",
    "save_signature": {
      "size": 131072,
      "mtime": 1714435200.0,
      "sha256": "..."
    }
  }
}
```

Se qualquer lado falhar nessa fase, os dois recebem:

```json
{
  "type": "trade_write_failed",
  "stage": "prepare_write",
  "message": "Falha antes da escrita local."
}
```

Se os dois lados responderem `write_ready`, o servidor envia:

```json
{
  "type": "trade_commit_write",
  "received_payload": {},
  "sent_payload": {},
  "message": "Escrita liberada para os dois jogadores."
}
```

Depois da gravacao local, cada client responde com `write_done` ou `write_failed`. Quando os dois lados concluem com sucesso, o servidor fecha a operacao com:

```json
{
  "type": "trade_completed",
  "message": "Troca concluida com sucesso nos dois lados."
}
```

A sala e removida apos `trade_completed`, e os payloads sao apagados da memoria do servidor.

## Cancelamento

```json
{"type": "cancel_trade"}
```

Ou desconexao de um jogador:

```json
{"type": "trade_cancelled", "reason": "peer_disconnected"}
```

## Guardas Cross-Generation

O client atualizado sempre anuncia suporte tecnico a `canonical_cross_generation`. O servidor ainda protege cross-generation por flags de producao: se a flag global estiver desligada, geracoes diferentes retornam erro claro no join:

```json
{
  "type": "generation_mismatch",
  "code": "generation_mismatch",
  "message": "Este servidor nao habilitou troca entre geracoes."
}
```

O client valida o Pokemon recebido no preflight antes de qualquer gravacao. Species inexistente no destino bloqueia a troca inteira; perdas removiveis sao registradas no `CompatibilityReport`.

Para liberar um modo cross-generation no servidor:

```text
ALLOW_CROSS_GENERATION=true
ENABLED_TRADE_MODES=time_capsule_gen1_gen2,forward_transfer_to_gen3,legacy_downconvert_experimental
```

Modos que nao aparecem em `ENABLED_TRADE_MODES` continuam bloqueados mesmo com a flag global ligada.
