# PokeCable Showdown Worker

Worker Node local para o servidor PokeCable Room. Ele fala JSON-lines por
`stdin/stdout` e mantém as batalhas em memória usando o simulador
`pokemon-showdown`.

## Instalação

```bash
cd /srv/pokecable-showdown-worker
npm install
```

## Execução manual

```bash
node worker.js
```

O processo fica aguardando uma linha JSON por comando. Em produção, o servidor
FastAPI inicia o worker automaticamente quando `SHOWDOWN_PROCESS_CMD` estiver
configurado:

```text
SHOWDOWN_ENABLED=true
SHOWDOWN_PROCESS_CMD=node /srv/pokecable-showdown-worker/worker.js
```

Se o pacote `pokemon-showdown` não estiver instalado ou o processo falhar, o
servidor usa o adapter local de fallback para não derrubar o WebSocket.
