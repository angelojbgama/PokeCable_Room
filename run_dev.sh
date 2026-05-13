#!/bin/bash
# Script para subir o backend e o frontend simultaneamente

# Cores para o output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Iniciando PokeCable Room (Desenvolvimento)...${NC}"

POKECABLE_CONFIG_DIR="$HOME/.pokecable"
mkdir -p "$POKECABLE_CONFIG_DIR"
export POKECABLE_DEV=1

port_in_use() {
    local port="$1"
    python3 - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    print("1")
else:
    print("0")
finally:
    sock.close()
PY
}

find_free_port() {
    local start="$1"
    local end="$2"
    local p
    for ((p=start; p<=end; p++)); do
        if [ "$(port_in_use "$p")" = "0" ]; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

is_pokecable_backend() {
    local port="$1"
    local openapi
    openapi="$(curl -fsS "http://127.0.0.1:${port}/openapi.json" 2>/dev/null || true)"
    if [ -z "$openapi" ]; then
        return 1
    fi
    if printf "%s" "$openapi" | grep -q '"/runtime/enrich-pokemon"'; then
        return 0
    fi
    return 1
}

BACKEND_PORT=8000
FRONTEND_PORT=8080
BACKEND_STARTED=0
FRONTEND_STARTED=0

# Funcao para encerrar os processos ao sair
cleanup() {
    echo -e "\n${BLUE}Encerrando servidores...${NC}"
    if [ "$BACKEND_STARTED" = "1" ] && [ -n "${BACKEND_PID:-}" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ "$FRONTEND_STARTED" = "1" ] && [ -n "${FRONTEND_PID:-}" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    exit
}

trap cleanup SIGINT

# 1. Resolver porta do backend
if [ "$(port_in_use "$BACKEND_PORT")" = "1" ]; then
    if is_pokecable_backend "$BACKEND_PORT"; then
        echo -e "${YELLOW}Backend PokeCable ja esta ativo em ${BACKEND_PORT}; reutilizando.${NC}"
    else
        NEW_BACKEND_PORT="$(find_free_port 8001 8099 || true)"
        if [ -z "${NEW_BACKEND_PORT:-}" ]; then
            echo -e "${YELLOW}Nao foi encontrada porta livre para backend (8001-8099).${NC}"
            exit 1
        fi
        BACKEND_PORT="$NEW_BACKEND_PORT"
        echo -e "${YELLOW}Porta 8000 ocupada por outro servico; usando backend em ${BACKEND_PORT}.${NC}"
    fi
fi

if ! is_pokecable_backend "$BACKEND_PORT"; then
    echo -e "${GREEN}Iniciando Backend na porta ${BACKEND_PORT}...${NC}"
    cd PokeCable/api
    if [ ! -d ".venv" ]; then
        echo "Criando ambiente virtual Python..."
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -r requirements.txt --quiet
    uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" &
    BACKEND_PID=$!
    BACKEND_STARTED=1
    cd ../..
fi

LOCAL_WS_URL="ws://127.0.0.1:${BACKEND_PORT}/ws"
printf "%s\n" "$LOCAL_WS_URL" > "$POKECABLE_CONFIG_DIR/server.conf"
echo -e "${GREEN}Cliente configurado para backend local: ${LOCAL_WS_URL}${NC}"

# 2. Resolver porta do frontend
if [ "$(port_in_use "$FRONTEND_PORT")" = "1" ]; then
    NEW_FRONTEND_PORT="$(find_free_port 8081 8180 || true)"
    if [ -z "${NEW_FRONTEND_PORT:-}" ]; then
        echo -e "${YELLOW}Nao foi encontrada porta livre para frontend (8081-8180).${NC}"
        exit 1
    fi
    FRONTEND_PORT="$NEW_FRONTEND_PORT"
    echo -e "${YELLOW}Porta 8080 ocupada; usando frontend em ${FRONTEND_PORT}.${NC}"
fi

echo -e "${GREEN}Iniciando Frontend na porta ${FRONTEND_PORT}...${NC}"
cd PokeCable/frontend
python3 -m http.server "$FRONTEND_PORT" &
FRONTEND_PID=$!
FRONTEND_STARTED=1
cd ../..

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}Backend rodando em:  http://localhost:${BACKEND_PORT}${NC}"
echo -e "${BLUE}Frontend rodando em: http://localhost:${FRONTEND_PORT}${NC}"
echo -e "${BLUE}WebSocket alvo do cliente: ${LOCAL_WS_URL}${NC}"
echo -e "${BLUE}Pressione Ctrl+C para parar ambos os servidores.${NC}"
echo -e "${BLUE}==================================================${NC}"

# Aguarda os processos em segundo plano
wait
