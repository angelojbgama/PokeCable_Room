from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def capture_save_signature(save_path: str | Path) -> dict[str, Any]:
    path = Path(save_path)
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "size": stat.st_size,
        "mtime": int(stat.st_mtime),
        "sha256": digest.hexdigest(),
    }


def save_signature_matches(save_path: str | Path, signature: dict[str, Any] | None) -> bool:
    if signature is None:
        return True
    current = capture_save_signature(save_path)
    return current == signature


def create_backup(save_path: str | Path, backup_dir: str | Path, metadata: dict[str, Any]) -> tuple[Path, Path]:
    source = Path(save_path)
    if not source.is_file():
        raise FileNotFoundError(f"Save nao encontrado para backup: {source}")
    target_dir = Path(backup_dir)
    if target_dir.is_absolute() and len(target_dir.parts) > 1 and target_dir.parts[1] == "roms" and not Path("/roms").exists():
        target_dir = Path(__file__).resolve().parent / "backups"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        target_dir = Path(__file__).resolve().parent / "backups"
        target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = target_dir / f"{source.stem}_{timestamp}{source.suffix}.bak"
    metadata_path = target_dir / f"{source.stem}_{timestamp}.metadata.json"
    try:
        shutil.copy2(source, backup_path)
    except OSError:
        target_dir = Path(__file__).resolve().parent / "backups"
        target_dir.mkdir(parents=True, exist_ok=True)
        backup_path = target_dir / f"{source.stem}_{timestamp}{source.suffix}.bak"
        metadata_path = target_dir / f"{source.stem}_{timestamp}.metadata.json"
        shutil.copy2(source, backup_path)
    if backup_path.stat().st_size != source.stat().st_size:
        raise OSError("Backup foi gravado com tamanho diferente do save original.")
    metadata = dict(metadata)
    metadata.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
    metadata.setdefault("original_signature", capture_save_signature(source))
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return backup_path, metadata_path


def list_backups(backup_dir: str | Path) -> list[Path]:
    path = Path(backup_dir)
    if not path.is_dir():
        return []
    return sorted(path.glob("*.bak"), reverse=True)


def restore_backup(backup_path: str | Path, destination: str | Path) -> None:
    backup = Path(backup_path)
    if not backup.is_file():
        raise FileNotFoundError(f"Backup nao encontrado: {backup}")
    destination_path = Path(destination)
    shutil.copy2(backup, destination_path)
