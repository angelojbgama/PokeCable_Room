# PokeCable Room

PokeCable Room e uma tool para R36S/ArkOS/dArkOS que permite dois usuarios trocarem Pokemon pela internet usando um VPS como servidor de salas privadas.

Nao e emulacao de cabo link. A troca e feita por edicao local e segura do arquivo de save, sempre com backup antes de qualquer escrita. O servidor apenas orquestra sala, compatibilidade, ofertas e confirmacao.

O projeto tambem possui modo de batalha separado do fluxo de troca. A batalha usa o modelo canonico dos Pokemon da party e um adapter compativel com Pokemon Showdown; ela nao escreve save, nao envia ROM e nao envia save completo ao servidor.

## Direcao Do Produto

Same-generation trade e o modo estavel: Gen 1 com Gen 1, Gen 2 com Gen 2 e Gen 3 com Gen 3 usando payload raw da mesma geracao.

Cross-generation trade tambem faz parte do produto. A sala e unica: o usuario cria ou entra em uma sala, escolhe o save e o Pokemon, e o sistema deriva automaticamente o caminho de conversao necessario para cada direcao. O usuario nao escolhe sala especial e nao precisa aceitar um passo tecnico extra de perda de dados. Nenhum raw payload de uma geracao deve ser escrito diretamente em save de outra geracao.

Roadmap:

- Same-generation stable mode.
- Sala unica com preflight automatico.
- Gen 1 <-> Gen 2 via conversor canonico.
- Gen 1/2 -> Gen 3 via conversor canonico.
- Gen 3 -> Gen 1/2 com downconvert protegido por relatorio de perda de dados.

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
- Sala unica: criar sala, entrar sala, escolher save e Pokemon.
- Same-generation trade usando raw payload somente entre saves da mesma geracao.
- Cross-generation trade usando payload canonico, preflight local e conversores locais.
- Evolucao simples por troca aplicada localmente depois da troca, quando `auto_trade_evolution` esta ligado.
- Display normalizado no R36S e web: National Dex, nome, level, held item, sexo quando existir e apelido quando for diferente.
- Salas de batalha separadas das salas de troca.
- Exportacao de times canonicos para formato de time Pokemon Showdown.
- Battle room via WebSocket com dois jogadores, oferta de times, confirmacao, logs, acoes basicas e desistir.

Experimental protegido por flags:

- Modos derivados por direcao no estado interno da sala.
- Preflight obrigatorio antes de confirmar troca.
- Payload v2 com raw, summary, canonical e compatibility_report.
- Modelo canonico separando National Dex, ID nativo da geracao e espaco de ID.
- Tabelas locais de especies, moves e held items usadas pela compatibilidade.
- Conversores locais para Gen 1 <-> Gen 2, Gen 1/2 -> Gen 3 e Gen 3 -> Gen 1/2.
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
- Cross-generation deve ser testado com backup.
- Downconvert Gen 3 -> Gen 1/2 pode perder ability, nature, parte do trainer ID, held item e moves modernos.
- O jogo/emulador precisa estar fechado antes de gravar no save.
- O client Python compara `size`, `mtime` e `SHA-256` do save antes de gravar.
- O adapter real de Pokemon Showdown depende de Node/processo separado. Sem `SHOWDOWN_PROCESS_CMD`, o servidor usa um adapter local deterministico para fluxo e testes.

## Seguranca De Geracao

- Same-generation usa raw payload da propria geracao.
- Cross-generation usa modelo canonico, `CompatibilityReport` e conversores locais.
- O servidor bloqueia cross-generation se a flag global estiver desligada ou se algum modo derivado da troca nao estiver em `ENABLED_TRADE_MODES`.
- O client anuncia suporte tecnico a `canonical_cross_generation`; a compatibilidade real e decidida no preflight.
- A compatibilidade e calculada por Pokemon recebido durante o preflight, antes da confirmacao final.

## Cross-Generation Trade

Same-generation e o modo estavel: os dois saves sao da mesma geracao e o client escreve o raw payload daquela mesma geracao. Cross-generation usa payload canonico e conversores locais; o servidor apenas valida sala, senha, ofertas, preflight e confirmacoes.

A sala e unica. O usuario nao escolhe Time Capsule, Transfer ou Downconvert ao criar a sala. Depois que os dois jogadores oferecem seus Pokemon, o servidor solicita preflight para os dois clients:

- Cada client valida localmente o Pokemon que vai receber.
- Se qualquer lado falhar, o servidor envia `trade_blocked` e ninguem grava save.
- Se os dois lados passarem, o servidor envia `preflight_ready`.
- Depois da confirmacao dos dois jogadores, o servidor entra em escrita em duas fases:
  - `prepare_write`
  - `write_ready`
  - `trade_commit_write`
  - `write_done`
  - `trade_completed`
- Se qualquer lado falhar antes ou durante a gravacao, o servidor envia `trade_write_failed`.

Modos derivados internamente e protegidos por flags:

- `time_capsule_gen1_gen2`: Gen 1 <-> Gen 2 para Pokemon compativeis.
- `forward_transfer_to_gen3`: Gen 1 -> Gen 3 e Gen 2 -> Gen 3.
- `legacy_downconvert_experimental`: Gen 3 -> Gen 1 e Gen 3 -> Gen 2.

Em uma troca de duas vias entre Gen 1/2 e Gen 3, cada direcao respeita seu proprio modo interno. Por exemplo, para o jogador Gen 1 enviar ao Gen 3 e tambem receber do Gen 3, o servidor precisa habilitar `forward_transfer_to_gen3` e `legacy_downconvert_experimental`.

Compatibilidade por National Dex:

- Um Pokemon cross-generation so e aceito se seu National Dex existir na geracao destino.
- Mew Gen 3 -> Gen 1 e permitido: Mew e National Dex #151 e vira species interno Gen 1 `21`.
- Mew Gen 3 -> Gen 2 e permitido: Mew e National Dex #151 e continua `151`.
- Kadabra Gen 3 -> Gen 1/2 e permitido porque Kadabra #64 existe nessas geracoes.
- Mew Gen 1 -> Gen 3 e Mew Gen 2 -> Gen 3 sao permitidos quando moves e campos removiveis passam pela politica escolhida.
- Chikorita Gen 2 -> Gen 1 e bloqueado porque Chikorita #152 nao existe na Gen 1.
- Clamperl Gen 3 -> Gen 2 e bloqueado porque Clamperl #366 nao existe na Gen 2.
- Treecko Gen 3 -> Gen 1/2 e bloqueado porque Treecko #252 nao existe nesses destinos.

Exemplos:

- Permitido: Gen 1 Pikachu <-> Gen 3 Mew.
- Bloqueado: Gen 1 Pikachu <-> Gen 3 Treecko, porque Treecko #252 nao existe na Gen 1.
- Permitido: Gen 2 Mew <-> Gen 3 Mew.
- Bloqueado: Gen 2 Chikorita -> Gen 1, porque Chikorita #152 nao existe na Gen 1.

Servidor:

```text
ALLOW_CROSS_GENERATION=true
ENABLED_TRADE_MODES=time_capsule_gen1_gen2,forward_transfer_to_gen3,legacy_downconvert_experimental
```

Client:

```json
{
  "cross_generation": {
    "policy": "auto_retrocompat",
    "unsafe_auto_confirm_data_loss": false
  }
}
```

Politicas:

- `strict`: bloqueia perdas de dados relevantes.
- `safe_default`: bloqueia species/moves incompativeis, permite perdas removiveis com confirmacao.
- `permissive`: remove o que puder ser removido, registra `data_loss` e exige confirmacao.
- `auto_retrocompat`: padrao do produto; remove/normaliza automaticamente moves, held item e campos modernos quando a species existe no destino.

Perdas conhecidas:

- Species inexistente na geracao destino bloqueia sempre.
- Egg bloqueia sempre.
- Move inexistente bloqueia em `safe_default`/`strict`; em `permissive` e `auto_retrocompat` pode ser removido.
- Held item indo para Gen 1 e removido com `data_loss`.
- Held item sem equivalente em Gen 2/3 e removido ou bloqueado conforme a politica.
- Ability/nature indo para Gen 1/2 sao removidas com `data_loss`.
- Trainer ID Gen 3 pode ser reduzido para 16 bits ao ir para Gen 1/2.
- Em `auto_retrocompat`, essas perdas sao registradas no relatorio/log, mas nao exigem confirmacao extra alem da confirmacao normal da troca.

Seguranca:

- Backup antes de salvar.
- Se o save mudar enquanto a sala esta aberta, a troca e abortada antes da gravacao.
- A atomicidade e de protocolo: se algum preflight falhar, nenhum client recebe commit; depois do commit, cada client protege seu arquivo local com backup.
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

## Battle Mode Via Showdown

O modo de batalha e separado da troca por save:

- Troca por save altera o arquivo local com backup.
- Batalha nao altera save.
- Batalha envia somente `CanonicalPokemon` sanitizado do time escolhido.
- `original_data.raw_data_base64` e removido do payload de batalha antes de ir ao servidor.
- O servidor cria uma `BattleRoom`, recebe dois times, espera confirmacao dos dois jogadores e passa eventos para um `ShowdownAdapter`.

Formatos iniciais:

- Gen 1: `gen1customgame`
- Gen 2: `gen2customgame`
- Gen 3: `gen3customgame`

Eventos WebSocket de batalha:

- `create_battle_room`
- `join_battle_room`
- `offer_battle_team`
- `confirm_battle`
- `battle_action`
- `battle_forfeit`
- `battle_room_created`
- `battle_room_joined`
- `battle_team_received`
- `battle_ready`
- `battle_started`
- `battle_log`
- `battle_request_action`
- `battle_finished`
- `battle_error`

Adapter Showdown:

- `SHOWDOWN_ENABLED=true` por padrao.
- `SHOWDOWN_REQUIRED=true` faz o servidor falhar no startup se o worker/bridge real nao estiver pronto.
- `SHOWDOWN_SERVER_URL` fica reservado para bridge HTTP externa.
- `SHOWDOWN_PROCESS_CMD` aponta para um worker Node/Pokemon Showdown local persistente, por exemplo `node /srv/pokecable-showdown-worker/worker.js`.
- Se o processo nao estiver configurado ou falhar, o servidor nao bloqueia startup; usa o adapter local para manter o fluxo de sala, logs e testes funcionando.
- O adapter local nao e simulacao competitiva completa de Pokemon Showdown; ele e o fallback de protocolo. Para batalha real completa, instale o worker em `/srv/pokecable-showdown-worker` e configure `SHOWDOWN_PROCESS_CMD`.

Worker Node local:

```bash
cd /srv/pokecable-showdown-worker
npm install
npm run check
```

Configuracao do servidor:

```text
SHOWDOWN_ENABLED=true
SHOWDOWN_REQUIRED=false
SHOWDOWN_PROCESS_CMD=node /srv/pokecable-showdown-worker/worker.js
```

O worker usa JSON-lines por `stdin/stdout` e guarda o estado da batalha em
memoria. O FastAPI inicia o processo automaticamente quando a primeira batalha
precisar do adapter real.

Observacao para Docker: a imagem Python padrao nao instala Node nem copia o
worker. Em Docker, use `SHOWDOWN_SERVER_URL` para um bridge externo ou monte um
worker Node dentro do container antes de definir `SHOWDOWN_PROCESS_CMD`.

Client R36S:

```bash
PYTHONPATH=r36s-client python3 r36s-client/pokecable_room/client.py \
  --mode battle \
  --action create \
  --server ws://127.0.0.1:8000/ws \
  --room batalha \
  --password 123 \
  --save /caminho/para/save.sav
```

O menu do R36S tambem possui:

- Criar sala de batalha
- Entrar em sala de batalha
- Escolher time do save
- Ver time Showdown
- Confirmar batalha
- Enviar acao simplificada
- Receber acoes reais por jogador a partir do `request` do Showdown

Frontend web:

- Cria/entra em sala de troca.
- Cria/entra em sala de batalha.
- Mostra party com display normalizado.
- Envia time canonico para batalha.
- Mostra logs de batalha.

Limites atuais:

- A UI visual de batalha ainda e simplificada.
- Sprites, animacoes e seletores completos de move/switch podem ser adicionados depois.
- A batalha real completa depende de um processo Pokemon Showdown externo.
- O front web continua sem editar save no servidor; ele edita localmente no navegador apenas no fluxo de troca.

## Feature Flags

Config local do client:

```json
{
  "auto_trade_evolution": true,
  "item_trade_evolutions_enabled": false,
  "cross_generation": {
    "enabled": true,
    "enabled_modes": ["time_capsule_gen1_gen2", "forward_transfer_to_gen3", "legacy_downconvert_experimental"],
    "policy": "auto_retrocompat",
    "unsafe_auto_confirm_data_loss": false
  }
}
```

Servidor em producao/cross-generation:

```text
ALLOW_CROSS_GENERATION=true
ENABLED_TRADE_MODES=time_capsule_gen1_gen2,forward_transfer_to_gen3,legacy_downconvert_experimental
SHOWDOWN_ENABLED=true
SHOWDOWN_REQUIRED=false
SHOWDOWN_SERVER_URL=
SHOWDOWN_PROCESS_CMD=node /srv/pokecable-showdown-worker/worker.js
```

`ALLOW_CROSS_GENERATION=true` sozinho nao libera tudo. Cada modo derivado precisa aparecer em `ENABLED_TRADE_MODES`.

Variaveis e opcoes:

- `ALLOW_CROSS_GENERATION`: liga a feature guard global do servidor.
- `ENABLED_TRADE_MODES`: lista os modos cross-generation permitidos no servidor.
- `item_trade_evolutions_enabled`: liga evolucoes por item no client; padrao `false`.
- `cross_generation.policy`: `auto_retrocompat`, `safe_default`, `strict` ou `permissive`.
- `cross_generation.unsafe_auto_confirm_data_loss`: permite auto-confirm com perda de dados; padrao `false` e nao recomendado.
- `SHOWDOWN_REQUIRED`: exige worker/bridge real no startup do servidor.

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
python3 -m compileall server r36s-client
node --check frontend/app.js
```
