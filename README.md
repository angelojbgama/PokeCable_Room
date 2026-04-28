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

Estavel:

- Servidor FastAPI/WebSocket em `/ws`.
- Salas privadas com nome e senha.
- Maximo de dois jogadores por sala.
- Client R36S sem desktop, usando dialog/whiptail, terminal e teclado virtual por controle.
- Frontend web em `https://9kernel.vps-kinghost.net/`.
- Parser Gen 1 Red/Blue/Yellow para party.
- Parser Gen 2 Gold/Silver/Crystal para party.
- Parser Gen 3 Ruby/Sapphire/Emerald/FireRed/LeafGreen para party.
- Backup automatico antes de alterar save.
- Same-generation trade usando raw payload somente entre saves da mesma geracao.
- Evolucao simples por troca aplicada localmente depois da troca, quando `auto_trade_evolution` esta ligado.

Experimental protegido por flags:

- `trade_mode` e `compatibility_status` no contrato de sala.
- Payload v2 com raw, summary, canonical e compatibility_report.
- Modelo canonico separando National Dex, ID nativo da geracao e espaco de ID.
- Tabelas locais de especies, moves e held items usadas pela compatibilidade.
- Conversores locais para Gen 1 <-> Gen 2, Gen 1/2 -> Gen 3 e Gen 3 -> Gen 1/2.
- Cross-generation usando canonical payload, `CompatibilityReport` e conversor local.
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

## Limitacoes Conhecidas

- Boxes ainda nao estao implementadas; o fluxo atual opera em party.
- Validacao completa de learnset nao e objetivo inicial; moves sao validados por existencia na geracao destino.
- Cross-generation deve ser testado com backup e feature flags por modo.
- Downconvert Gen 3 -> Gen 1/2 pode perder ability, nature, parte do trainer ID, held item e moves modernos.
- O jogo/emulador precisa estar fechado antes de gravar no save.

## Seguranca De Geracao

- Same-generation usa raw payload da propria geracao.
- Cross-generation usa modelo canonico, `CompatibilityReport` e conversores locais.
- O servidor bloqueia cross-generation enquanto a feature guard global estiver desligada ou o modo nao estiver em `ENABLED_TRADE_MODES`.
- O client tambem rejeita payload recebido de geracao diferente antes de gravar.

## Cross-Generation Trade

Same-generation e o modo estavel: os dois saves sao da mesma geracao e o client escreve o raw payload daquela mesma geracao. Cross-generation usa payload canonico e conversores locais; o servidor apenas valida sala, senha, modo, ofertas e confirmacoes.

Modos protegidos por flags:

- `time_capsule_gen1_gen2`: Gen 1 <-> Gen 2 para Pokemon compativeis.
- `forward_transfer_to_gen3`: Gen 1 -> Gen 3 e Gen 2 -> Gen 3.
- `legacy_downconvert_experimental`: Gen 3 -> Gen 1 e Gen 3 -> Gen 2.

Em uma troca de duas vias entre Gen 1/2 e Gen 3, cada direcao respeita sua propria flag. Por exemplo, para o jogador Gen 1 enviar ao Gen 3 e tambem receber do Gen 3, servidor e clients precisam habilitar `forward_transfer_to_gen3` e `legacy_downconvert_experimental`.

Compatibilidade por National Dex:

- Um Pokemon cross-generation so e aceito se seu National Dex existir na geracao destino.
- Mew Gen 3 -> Gen 1 e permitido: Mew e National Dex #151 e vira species interno Gen 1 `21`.
- Mew Gen 3 -> Gen 2 e permitido: Mew e National Dex #151 e continua `151`.
- Kadabra Gen 3 -> Gen 1/2 e permitido porque Kadabra #64 existe nessas geracoes.
- Mew Gen 1 -> Gen 3 e Mew Gen 2 -> Gen 3 sao permitidos quando moves e campos removiveis passam pela politica escolhida.
- Chikorita Gen 2 -> Gen 1 e bloqueado porque Chikorita #152 nao existe na Gen 1.
- Clamperl Gen 3 -> Gen 2 e bloqueado porque Clamperl #366 nao existe na Gen 2.
- Treecko Gen 3 -> Gen 1/2 e bloqueado porque Treecko #252 nao existe nesses destinos.

Servidor:

```text
ALLOW_CROSS_GENERATION=true
ENABLED_TRADE_MODES=time_capsule_gen1_gen2
```

Client:

```json
{
  "cross_generation": {
    "enabled": true,
    "enabled_modes": ["time_capsule_gen1_gen2"],
    "policy": "safe_default",
    "unsafe_auto_confirm_data_loss": false
  }
}
```

Politicas:

- `strict`: bloqueia perdas de dados relevantes.
- `safe_default`: bloqueia species/moves incompativeis, permite perdas removiveis com confirmacao.
- `permissive`: remove o que puder ser removido, registra `data_loss` e exige confirmacao.

Perdas conhecidas:

- Species inexistente na geracao destino bloqueia sempre.
- Egg bloqueia sempre.
- Move inexistente bloqueia em `safe_default`/`strict`; em `permissive` pode ser removido.
- Held item indo para Gen 1 e removido com `data_loss`.
- Held item sem equivalente em Gen 2/3 e removido ou bloqueado conforme a politica.
- Ability/nature indo para Gen 1/2 sao removidas com `data_loss`.
- Trainer ID Gen 3 pode ser reduzido para 16 bits ao ir para Gen 1/2.

Seguranca:

- Backup antes de salvar.
- Se o save mudar enquanto a sala esta aberta, a troca e abortada antes da gravacao.
- Nenhum save completo vai ao servidor.
- Nenhuma ROM e usada.
- Nenhum raw payload cross-generation e escrito em save local.

## Trade Evolutions

Evolucao por troca e aplicada localmente no client depois que o Pokemon recebido e escrito no slot do save. A engine altera apenas o parser em memoria; o fluxo do client cria backup antes da gravacao, valida o save e entao salva o arquivo.

`auto_trade_evolution=true` liga evolucoes simples por troca. `item_trade_evolutions_enabled=false` e o padrao: evolucoes por item existem para testes/beta, mas so acontecem quando essa opcao e ativada no `config.json`. Gen 1 nao possui held item.

Quando a evolucao por item acontece, o item correto e consumido no save local. Se o item estiver errado ou a flag estiver desligada, o Pokemon recebido permanece sem evoluir e a troca continua normalmente.

Suporte Gen 1:

- Kadabra -> Alakazam
- Machoke -> Machamp
- Graveler -> Golem
- Haunter -> Gengar

Suporte Gen 2:

- Kadabra -> Alakazam
- Machoke -> Machamp
- Graveler -> Golem
- Haunter -> Gengar
- Poliwhirl + King's Rock -> Politoed
- Slowpoke + King's Rock -> Slowking
- Onix + Metal Coat -> Steelix
- Scyther + Metal Coat -> Scizor
- Seadra + Dragon Scale -> Kingdra
- Porygon + Up-Grade -> Porygon2

Suporte Gen 3:

- Kadabra -> Alakazam
- Machoke -> Machamp
- Graveler -> Golem
- Haunter -> Gengar
- Poliwhirl + King's Rock -> Politoed
- Slowpoke + King's Rock -> Slowking
- Onix + Metal Coat -> Steelix
- Scyther + Metal Coat -> Scizor
- Seadra + Dragon Scale -> Kingdra
- Porygon + Up-Grade -> Porygon2
- Clamperl + Deep Sea Tooth -> Huntail
- Clamperl + Deep Sea Scale -> Gorebyss

## Feature Flags

Config local do client:

```json
{
  "auto_trade_evolution": true,
  "item_trade_evolutions_enabled": false,
  "cross_generation": {
    "enabled": false,
    "enabled_modes": [],
    "policy": "safe_default",
    "unsafe_auto_confirm_data_loss": false
  }
}
```

Servidor:

```text
ALLOW_CROSS_GENERATION=false
ENABLED_TRADE_MODES=
```

`ALLOW_CROSS_GENERATION=true` sozinho nao libera tudo. Cada modo precisa aparecer em `ENABLED_TRADE_MODES`, por exemplo `time_capsule_gen1_gen2`.

Variaveis e opcoes:

- `ALLOW_CROSS_GENERATION`: liga a feature guard global do servidor.
- `ENABLED_TRADE_MODES`: lista os modos cross-generation permitidos no servidor.
- `item_trade_evolutions_enabled`: liga evolucoes por item no client; padrao `false`.
- `cross_generation.enabled`: liga cross-generation no client.
- `cross_generation.enabled_modes`: modos cross-generation permitidos no client.
- `cross_generation.policy`: `safe_default`, `strict` ou `permissive`.
- `cross_generation.unsafe_auto_confirm_data_loss`: permite auto-confirm com perda de dados; padrao `false` e nao recomendado.

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
