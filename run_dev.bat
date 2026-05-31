@echo off
setlocal

set "POKECABLE_DEV=1"
set "PYTHONPATH=%CD%\Pokecable_tool;%PYTHONPATH%"

echo ==================================================
echo Iniciando PokeCable Room (Desenvolvimento local)...
echo ==================================================

python -B -m frontend.app %*
