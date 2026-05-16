#!/bin/bash
# Button Mapper Launcher

TOOL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$TOOL_DIR"

export PYTHONPATH="${TOOL_DIR}/.."

python3 button_mapper.py "$@"
