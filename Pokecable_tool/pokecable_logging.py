#!/usr/bin/env python3
"""Small logging setup for the standalone PokeCable tool."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict


def _enabled(value: str | None) -> bool:
    return str(value or "").lower() in ("1", "true", "yes", "on")


def resolve_log_paths() -> Dict[str, Path | str]:
    log_root = Path(os.getenv("POKECABLE_LOG_ROOT", str(Path(__file__).parent / "logs"))).expanduser()
    log_root.mkdir(parents=True, exist_ok=True)
    return {
        "root": log_root,
        "session_dir": log_root,
        "error_log": Path(os.getenv("POKECABLE_ERROR_LOG", str(log_root / "error.log"))).expanduser(),
        "debug_log": Path(os.getenv("POKECABLE_DEBUG_LOG", str(log_root / "debug.log"))).expanduser(),
        "debug": "1" if _enabled(os.getenv("POKECABLE_DEBUG")) else "0",
    }


def configure_logging() -> Dict[str, Path | str]:
    root = logging.getLogger()
    if getattr(root, "_pokecable_logging_ready", False):
        return getattr(root, "_pokecable_logging_paths")

    paths = resolve_log_paths()
    debug_enabled = paths["debug"] == "1"
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s")

    root.handlers.clear()
    root.setLevel(logging.DEBUG if debug_enabled else logging.ERROR)

    error_log = Path(paths["error_log"])
    error_log.parent.mkdir(parents=True, exist_ok=True)
    error_handler = RotatingFileHandler(error_log, maxBytes=128 * 1024, backupCount=1, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    if debug_enabled:
        debug_log = Path(paths["debug_log"])
        debug_log.parent.mkdir(parents=True, exist_ok=True)
        debug_handler = RotatingFileHandler(debug_log, maxBytes=512 * 1024, backupCount=1, encoding="utf-8")
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        root.addHandler(debug_handler)

    logging.captureWarnings(True)
    root._pokecable_logging_ready = True
    root._pokecable_logging_paths = paths
    return paths
