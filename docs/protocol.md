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
  "trade_mode": "same_generation",
  "supported_trade_modes": ["same_generation", "time_capsule_gen1_gen2", "forward_transfer_to_gen3"]
}
```

Entrar:

```json
{
  "type": "join_room",
  "room_name": "crystal-paqueta",
  "password": "senha",
  "generation": 2,
  "game": "pokemon_crystal",
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
  "compatibility_status": {
    "compatible": true,
    "mode": "same_generation",
    "blocking_reasons": []
  },
  "players": {}
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

Cross-generation usara o mesmo envelope com `trade_mode` diferente e escrita local por conversor. O servidor nao converte e nao grava save.

## Confirmacao

```json
{"type": "confirm_trade"}
```

Quando os dois confirmam:

```json
{
  "type": "trade_committed",
  "received_payload": {},
  "sent_payload": {},
  "message": "Troca confirmada pelos dois jogadores."
}
```

A sala e removida apos `trade_committed`, e os payloads sao apagados da memoria do servidor.

## Cancelamento

```json
{"type": "cancel_trade"}
```

Ou desconexao de um jogador:

```json
{"type": "trade_cancelled", "reason": "peer_disconnected"}
```

## Feature Guard Cross-Generation

Enquanto a feature guard estiver desligada, gerações diferentes retornam:

```json
{
  "type": "generation_mismatch",
  "code": "generation_mismatch",
  "message": "Esta sala e Gen 2. Seu save e Gen 3. Cross-generation esta protegido por bloqueio de seguranca enquanto a camada de conversao local esta em desenvolvimento."
}
```

O client tambem valida o payload recebido antes de gravar.
