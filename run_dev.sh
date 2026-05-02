#!/bin/bash
# Script para subir o backend e o frontend simultaneamente

# Cores para o output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Iniciando PokeCable Room (Desenvolvimento)...${NC}"

# Função para encerrar os processos ao sair
cleanup() {
    echo -e "\n${BLUE}Encerrando servidores...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT

# 1. Iniciar Backend (API)
echo -e "${GREEN}Iniciando Backend na porta 8000...${NC}"
cd PokeCable/api
if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual Python..."
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt --quiet
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# 2. Iniciar Frontend
echo -e "${GREEN}Iniciando Frontend na porta 8080...${NC}"
cd PokeCable/frontend
# Usa o módulo http.server do Python para servir os arquivos estáticos
python3 -m http.server 8080 &
FRONTEND_PID=$!
cd ../..

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}Backend rodando em:  http://localhost:8000${NC}"
echo -e "${BLUE}Frontend rodando em: http://localhost:8080${NC}"
echo -e "${BLUE}Pressione Ctrl+C para parar ambos os servidores.${NC}"
echo -e "${BLUE}==================================================${NC}"

# Aguarda os processos em segundo plano
wait
