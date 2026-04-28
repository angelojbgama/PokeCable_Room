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
  "game": "pokemon_crystal"
}
```

Entrar:

```json
{
  "type": "join_room",
  "room_name": "crystal-paqueta",
  "password": "senha",
  "generation": 2,
  "game": "pokemon_crystal"
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

## Oferta

```json
{
  "type": "offer_pokemon",
  "payload": {
    "generation": 2,
    "game": "pokemon_crystal",
    "species_id": 64,
    "species_name": "Kadabra",
    "level": 32,
    "nickname": "KADABRA",
    "ot_name": "ANGELO",
    "trainer_id": 12345,
    "raw_data_base64": "...",
    "display_summary": "Kadabra Lv. 32"
  }
}
```

O servidor encaminha ao outro jogador:

```json
{"type": "peer_offer_received", "offer": {"generation": 2}}
```

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

## Regra De Geracao

Ao criar a sala, o servidor grava `generation`. Ao entrar, o segundo jogador precisa informar a mesma geracao. Se for diferente:

```json
{
  "type": "generation_mismatch",
  "code": "generation_mismatch",
  "message": "Esta sala e Gen 2. Seu save e Gen 3. Trocas entre geracoes diferentes ainda nao sao suportadas."
}
```

O servidor tambem valida `generation` no `offer_pokemon`.

