#!/bin/bash
# Development launcher for the current offline/local PokeCable UI.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export POKECABLE_DEV=1

echo "Iniciando PokeCable Room (Desenvolvimento local)..."
exec ./Pokecable_tool/pokecable.sh "$@"
