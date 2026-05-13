@echo off
setlocal

set "LOCAL_WS_URL=ws://127.0.0.1:8000/ws"
if not exist "%USERPROFILE%\.pokecable" mkdir "%USERPROFILE%\.pokecable"
> "%USERPROFILE%\.pokecable\server.conf" echo %LOCAL_WS_URL%
set "POKECABLE_DEV=1"

echo ==================================================
echo Iniciando PokeCable Room (Desenvolvimento)...
echo ==================================================
echo Cliente configurado para backend local: %LOCAL_WS_URL%

set "BACKEND_OK="
for /f "tokens=*" %%i in ('curl -s http://127.0.0.1:8000/openapi.json ^| findstr /c:"/runtime/enrich-pokemon"') do set "BACKEND_OK=1"
if "%BACKEND_OK%"=="1" (
  echo Backend PokeCable ja esta ativo na porta 8000; reutilizando.
  goto :START_FRONTEND
)

:: 1. Iniciar Backend em uma nova janela
echo Iniciando Backend na porta 8000...
start "PokeCable Backend" cmd /k "cd PokeCable\api && (if not exist .venv python -m venv .venv) && call .venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: 2. Iniciar Frontend em uma nova janela
:START_FRONTEND
echo Iniciando Frontend na porta 8080...
start "PokeCable Frontend" cmd /k "cd PokeCable\frontend && python -m http.server 8080"

echo.
echo ==================================================
echo Servidores iniciando em janelas separadas!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:8080
echo WebSocket alvo do cliente: %LOCAL_WS_URL%
echo.
echo Pressione qualquer tecla para finalizar este script.
echo (Os servidores continuarao rodando nas outras janelas)
echo ==================================================
pause
