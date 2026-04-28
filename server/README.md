# PokeCable Room Server

Servidor FastAPI/WebSocket para salas privadas de troca por payload de Pokemon. O servidor nao edita saves, nao converte Pokemon e nao armazena ROMs ou saves completos.

## Rodar Localmente

```bash
cd server
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Healthcheck:

```bash
curl http://127.0.0.1:8000/health
```

WebSocket:

```text
ws://127.0.0.1:8000/ws
```

## Regras

- Cada sala tem no maximo 2 jogadores.
- A senha da sala e armazenada com hash PBKDF2.
- O servidor recebe apenas o payload do Pokemon selecionado.
- Payload raw e canonical nao devem ser logados completos.
- Same-generation e o modo estavel atual.
- Cross-generation fica protegido por feature guard global e por `ENABLED_TRADE_MODES`.
- O servidor mantem `trade_mode` e `compatibility_status`, mas a escrita e conversao acontecem no client.

## Cross-Generation

O servidor nunca converte e nunca grava save. Para liberar um modo em teste:

```bash
ALLOW_CROSS_GENERATION=true ENABLED_TRADE_MODES=time_capsule_gen1_gen2 docker compose up -d
```

Se `ALLOW_CROSS_GENERATION=true` mas o modo nao estiver em `ENABLED_TRADE_MODES`, o servidor continua bloqueando a sala.
