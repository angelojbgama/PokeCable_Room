@echo off
setlocal

echo ==================================================
echo Iniciando PokeCable Room (Desenvolvimento)...
echo ==================================================

:: 1. Iniciar Backend em uma nova janela
echo Iniciando Backend na porta 8000...
start "PokeCable Backend" cmd /k "cd PokeCable\api && (if not exist .venv python -m venv .venv) && call .venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: 2. Iniciar Frontend em uma nova janela
echo Iniciando Frontend na porta 8080...
start "PokeCable Frontend" cmd /k "cd PokeCable\frontend && python -m http.server 8080"

echo.
echo ==================================================
echo Servidores iniciando em janelas separadas!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:8080
echo.
echo Pressione qualquer tecla para finalizar este script.
echo (Os servidores continuarao rodando nas outras janelas)
echo ==================================================
pause
