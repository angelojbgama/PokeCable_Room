from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_dir: str | Path) -> Path:
    path = Path(log_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        path = Path(__file__).resolve().parent / "logs"
        path.mkdir(parents=True, exist_ok=True)
    log_file = path / "client.log"
    try:
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            force=True,
        )
    except OSError:
        path = Path(__file__).resolve().parent / "logs"
        path.mkdir(parents=True, exist_ok=True)
        log_file = path / "client.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            force=True,
        )
    return log_file
