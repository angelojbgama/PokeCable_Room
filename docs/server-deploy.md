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
```

`ALLOW_CROSS_GENERATION` permanece `false`. Alterar a variavel nao habilita a feature.

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
