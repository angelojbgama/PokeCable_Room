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

`ALLOW_CROSS_GENERATION=false` e o padrao recomendado. Para testar cross-generation em um modo especifico, habilite a flag global e liste somente o modo desejado:

```text
ALLOW_CROSS_GENERATION=true
ENABLED_TRADE_MODES=time_capsule_gen1_gen2
```

Cada modo precisa ser habilitado separadamente. Nao use `legacy_downconvert_experimental` em producao sem revisar os relatórios de perda de dados no client.

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
