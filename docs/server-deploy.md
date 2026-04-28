# Deploy Do Servidor

## Docker Compose

No VPS:

```bash
git clone <repo> pokecable-room
cd pokecable-room/server
cp .env.example .env
docker compose up -d --build
```

Variaveis:

```text
POKECABLE_SECRET_KEY=troque-isto
ROOM_TIMEOUT_SECONDS=900
MAX_ROOMS=200
LOG_LEVEL=INFO
ALLOW_CROSS_GENERATION=false
ENABLED_TRADE_MODES=
```

Para operar com troca automatica entre Gen 1/2/3, habilite a flag global e liste todos os modos derivados usados pelo servidor:

```text
ALLOW_CROSS_GENERATION=true
ENABLED_TRADE_MODES=time_capsule_gen1_gen2,forward_transfer_to_gen3,legacy_downconvert_experimental
```

`ALLOW_CROSS_GENERATION=true` sozinho nao libera cross-generation. Cada modo derivado precisa aparecer em `ENABLED_TRADE_MODES`. O client valida o Pokemon recebido no preflight e registra perdas removiveis no relatorio local.

## Nginx Reverse Proxy

Exemplo:

```nginx
server {
    server_name pokecable.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 900s;
    }
}
```

## HTTPS

Use Certbot:

```bash
sudo certbot --nginx -d pokecable.example.com
```

Client:

```text
wss://pokecable.example.com/ws
```

## Healthcheck

```bash
curl https://pokecable.example.com/health
```
