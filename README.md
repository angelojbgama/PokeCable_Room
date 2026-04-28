# PokeCable Room

PokeCable Room e uma tool para R36S/ArkOS/dArkOS que permite dois usuarios trocarem Pokemon pela internet usando um VPS como servidor de salas privadas.

Nao e emulacao de cabo link. A troca e feita por edicao local e segura do arquivo de save, sempre com backup antes de qualquer escrita.

## Suporte Atual

- Servidor FastAPI/WebSocket em `/ws`.
- Salas privadas com nome e senha.
- Maximo de dois jogadores por sala.
- Bloqueio obrigatorio de troca entre geracoes diferentes.
- Client R36S sem desktop, usando dialog/whiptail e teclado virtual.
- Frontend web em `https://9kernel.vps-kinghost.net/`.
- Parser Gen 1 Red/Blue/Yellow para party.
- Parser Gen 2 Gold/Silver/Crystal para party.
- Parser Gen 3 Ruby/Sapphire/Emerald/FireRed/LeafGreen para party.
- Backup automatico antes de alterar save.

## O Que Nao Faz

- Nao baixa ROMs.
- Nao distribui ROMs.
- Nao distribui BIOS.
- Nao armazena ROMs.
- Nao envia save completo ao servidor.
- Nao troca Pokemon entre geracoes diferentes.
- Nao implementa boxes ainda.
- Nao implementa modo Gen 1 <-> Gen 2 estilo Time Capsule ainda.

## Regra De Geracao

- Gen 1 troca somente com Gen 1.
- Gen 2 troca somente com Gen 2.
- Gen 3 troca somente com Gen 3.
- O servidor bloqueia cross-generation mesmo que alguem altere config local.
- O client tambem rejeita payload recebido com geracao diferente do save local.

## Rodar Servidor

```bash
cd server
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Ou com Docker:

```bash
cd server
docker compose up -d --build
```

## Client No PC

```bash
PYTHONPATH=r36s-client python3 r36s-client/pokecable_room/client.py \
  --action create \
  --server ws://127.0.0.1:8000/ws \
  --room teste \
  --password 123 \
  --save /caminho/para/save.srm \
  --pokemon-location party:0
```

Use `--action join` no segundo terminal.

## Testes

```bash
PYTHONPATH=server python3 -m unittest discover server/tests
PYTHONPATH=r36s-client python3 -m unittest discover r36s-client/pokecable_room/tests
```
