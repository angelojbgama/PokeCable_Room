# PokeCable Room

PokeCable Room e uma tool para R36S/ArkOS/dArkOS que permite dois usuarios trocarem Pokemon pela internet usando um VPS como servidor de salas privadas.

Nao e emulacao de cabo link. A troca e feita por edicao local e segura do arquivo de save, sempre com backup antes de qualquer escrita. O servidor apenas orquestra sala, compatibilidade, ofertas e confirmacao.

## Direcao Do Produto

Same-generation trade e o modo estavel inicial: Gen 1 com Gen 1, Gen 2 com Gen 2 e Gen 3 com Gen 3 usando payload raw da mesma geracao.

Cross-generation trade e objetivo do projeto. Ele fica protegido por feature guard enquanto a camada de modelo canonico e conversores locais seguros esta em desenvolvimento. Nenhum raw payload de uma geracao deve ser escrito diretamente em save de outra geracao.

Roadmap:

- Same-generation stable mode.
- Gen 1 <-> Gen 2 Time Capsule mode.
- Gen 1/2 -> Gen 3 Transfer mode.
- Gen 3 -> Gen 1/2 Experimental downconvert mode.

## Suporte Atual

- Servidor FastAPI/WebSocket em `/ws`.
- Salas privadas com nome e senha.
- Maximo de dois jogadores por sala.
- `trade_mode` e `compatibility_status` preparados no contrato de sala.
- Payload v2 com raw, summary, canonical e compatibility_report.
- Modelo canonico separando National Dex, ID nativo da geracao e espaco de ID.
- Tabelas locais de especies, moves e held items usadas pela compatibilidade.
- Conversores locais para Gen 1 <-> Gen 2, Gen 1/2 -> Gen 3 e Gen 3 -> Gen 1/2, todos atras de feature flag por modo.
- Client R36S sem desktop, usando dialog/whiptail, terminal e teclado virtual por controle.
- Frontend web em `https://9kernel.vps-kinghost.net/`.
- Parser Gen 1 Red/Blue/Yellow para party.
- Parser Gen 2 Gold/Silver/Crystal para party.
- Parser Gen 3 Ruby/Sapphire/Emerald/FireRed/LeafGreen para party.
- Backup automatico antes de alterar save.
- Evolucao simples por troca aplicada localmente depois da troca, quando `auto_trade_evolution` esta ligado.
- Evolucao por item com IDs validados para Gen 2/3, desligada por padrao por `item_trade_evolutions_enabled=false`.

## O Que Nao Faz

- Nao baixa ROMs.
- Nao distribui ROMs.
- Nao distribui BIOS.
- Nao armazena ROMs.
- Nao envia save completo ao servidor.
- Nao escreve raw de uma geracao em save de outra geracao.
- Nao aplica evolucao por item por padrao.
- Nao implementa boxes ainda.

## Seguranca De Geracao

- Same-generation usa raw payload da propria geracao.
- Cross-generation usa modelo canonico, `CompatibilityReport` e conversores locais.
- O servidor bloqueia cross-generation enquanto a feature guard global estiver desligada ou o modo nao estiver em `ENABLED_TRADE_MODES`.
- O client tambem rejeita payload recebido de geracao diferente antes de gravar.

## Feature Flags

Config local do client:

```json
{
  "auto_trade_evolution": true,
  "item_trade_evolutions_enabled": false,
  "cross_generation": {
    "enabled": false,
    "enabled_modes": [],
    "policy": "safe_default"
  }
}
```

Servidor:

```text
ALLOW_CROSS_GENERATION=false
ENABLED_TRADE_MODES=
```

`ALLOW_CROSS_GENERATION=true` sozinho nao libera tudo. Cada modo precisa aparecer em `ENABLED_TRADE_MODES`, por exemplo `time_capsule_gen1_gen2`.

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
