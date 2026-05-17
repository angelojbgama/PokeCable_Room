# PokeCable Room Server

Servidor FastAPI/WebSocket para salas privadas de troca por payload de Pokemon. O servidor nao edita saves, nao converte Pokemon e nao armazena ROMs ou saves completos.

O servidor participa apenas do fluxo online `Acessar sala`. A opcao `Trocar comigo`, implementada na `Pokecable_tool`, roda 100% offline entre dois saves locais e nao usa API, WebSocket nem fallback online.

## Rodar Localmente

```bash
cd PokeCable/api
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
- Cross-generation usa modos derivados automaticamente por geracao dos dois jogadores.
- O servidor mantem `trade_mode` e `compatibility_status`, mas a escrita e conversao acontecem no client.
- Quando um client envia `resolved_moves` na confirmacao, o servidor apenas encaminha essa escolha dentro do fluxo da sala.
- O `/health` retorna apenas o status da API.

Na `Pokecable_tool`, o mesmo preflight/conversao necessario para escrita local tambem existe em `pokecable_runtime`, permitindo `Trocar comigo` sem depender deste servidor.
