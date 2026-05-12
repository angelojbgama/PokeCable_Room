#!/usr/bin/env python3
"""
Shared logging setup for PokeCable.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict


class _LoggerPrefixFilter(logging.Filter):
    def __init__(self, *prefixes: str):
        super().__init__()
        self.prefixes = prefixes

    def filter(self, record: logging.LogRecord) -> bool:
        for prefix in self.prefixes:
            if record.name == prefix or record.name.startswith(prefix + "."):
                return True
        return False


def resolve_log_session() -> Dict[str, Path | str]:
    log_root = Path(os.getenv("POKECABLE_LOG_ROOT", str(Path(__file__).parent / "logs")))
    session_id = os.getenv("POKECABLE_LOG_SESSION", "").strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(os.getenv("POKECABLE_LOG_DIR", str(log_root / "sessions" / session_id)))
    session_dir.mkdir(parents=True, exist_ok=True)
    return {
        "root": log_root,
        "session_id": session_id,
        "session_dir": session_dir,
    }


def configure_logging() -> Dict[str, Path | str]:
    root = logging.getLogger()
    if getattr(root, "_pokecable_logging_ready", False):
        return getattr(root, "_pokecable_logging_paths")

    paths = resolve_log_session()
    session_dir = paths["session_dir"]
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s")

    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    all_handler = logging.FileHandler(session_dir / "all.log", encoding="utf-8")
    all_handler.setLevel(logging.DEBUG)
    all_handler.setFormatter(formatter)
    root.addHandler(all_handler)

    error_handler = logging.FileHandler(session_dir / "errors.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    ui_handler = logging.FileHandler(session_dir / "ui.log", encoding="utf-8")
    ui_handler.setLevel(logging.DEBUG)
    ui_handler.setFormatter(formatter)
    ui_handler.addFilter(_LoggerPrefixFilter("r36s_pokecable_ui", "__main__"))
    root.addHandler(ui_handler)

    core_handler = logging.FileHandler(session_dir / "core.log", encoding="utf-8")
    core_handler.setLevel(logging.DEBUG)
    core_handler.setFormatter(formatter)
    core_handler.addFilter(_LoggerPrefixFilter("r36s_pokecable_core"))
    root.addHandler(core_handler)

    save_handler = logging.FileHandler(session_dir / "save.log", encoding="utf-8")
    save_handler.setLevel(logging.DEBUG)
    save_handler.setFormatter(formatter)
    save_handler.addFilter(_LoggerPrefixFilter("pokecable_save"))
    root.addHandler(save_handler)

    logging.captureWarnings(True)
    root._pokecable_logging_ready = True
    root._pokecable_logging_paths = paths
    return paths
