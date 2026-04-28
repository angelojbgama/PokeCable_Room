from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .parsers import Gen1Parser, Gen2Parser, Gen3Parser


DEFAULT_CONFIG = {
    "server_url": "wss://9kernel.vps-kinghost.net/ws",
    "default_save_dirs": [
        "/roms/gb",
        "/roms/gbc",
        "/roms/gba",
        "/roms/saves",
        "/roms2/gb",
        "/roms2/gbc",
        "/roms2/gba",
        "/roms2/saves",
    ],
    "backup_dir": "/roms/tools/pokecable_room/backups",
    "log_dir": "/roms/tools/pokecable_room/logs",
    "auto_trade_evolution": True,
    "item_trade_evolutions_enabled": False,
    "cross_generation": {
        "enabled": False,
        "enabled_modes": [],
        "policy": "safe_default",
        "unsafe_auto_confirm_data_loss": False,
    },
    "allow_cross_generation": False,
}


def config_path() -> Path:
    return Path(__file__).with_name("config.json")


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    config = dict(DEFAULT_CONFIG)
    config.update(loaded)
    cross_generation = dict(DEFAULT_CONFIG["cross_generation"])
    cross_generation.update(loaded.get("cross_generation") or {})
    config["cross_generation"] = cross_generation
    config["allow_cross_generation"] = False
    return config


def save_config(config: dict[str, Any]) -> None:
    config = dict(config)
    config["allow_cross_generation"] = False
    cross_generation = dict(DEFAULT_CONFIG["cross_generation"])
    cross_generation.update(config.get("cross_generation") or {})
    if not cross_generation.get("enabled"):
        cross_generation["enabled_modes"] = []
    config["cross_generation"] = cross_generation
    config_path().write_text(json.dumps(config, indent=2), encoding="utf-8")


def find_save_files(save_dirs: list[str]) -> list[Path]:
    results: list[Path] = []
    for directory in save_dirs:
        path = Path(directory)
        if not path.is_dir():
            continue
        for suffix in ("*.sav", "*.srm"):
            results.extend(path.rglob(suffix))
    return sorted(set(results))


def detect_parser(save_path: str | Path):
    path = Path(save_path)
    for parser in (Gen1Parser(), Gen2Parser(), Gen3Parser()):
        if parser.detect(path):
            parser.load(path)
            return parser
    raise ValueError(
        "Nenhum parser suportado detectou este save. Suporte atual: party de Gen 1, "
        "Gold/Silver/Crystal Gen 2 e party de Gen 3."
    )
