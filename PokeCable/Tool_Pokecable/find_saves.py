#!/usr/bin/env python3
"""
Ferramenta para encontrar saves de Pokémon no R36S
Procura por arquivos .sav e .srm com "pokemon" no nome
"""

import os
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "find_saves.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("Finding Pokémon Save Files")
logger.info("=" * 80)

# Diretórios comuns para procurar
SEARCH_PATHS = [
    Path.home(),  # Home directory
    Path("/"),     # Root
    Path("/opt"),  # Opções do sistema
    Path("/tmp"),  # Temp files
    Path("/mnt"),  # Mounted drives
]

# Extensões de save
SAVE_EXTENSIONS = {".sav", ".srm"}


def find_saves(max_depth=5):
    """Procura por arquivos de save com 'pokemon' no nome"""
    found_saves = []

    for search_path in SEARCH_PATHS:
        if not search_path.exists():
            logger.debug(f"Skipping (not found): {search_path}")
            continue

        logger.info(f"Searching in: {search_path}")

        try:
            # Usar glob para buscar recursivamente
            for pattern in ["**/*pokemon*.sav", "**/*pokemon*.srm", "**/*Pokemon*.sav", "**/*Pokemon*.srm"]:
                for save_file in search_path.glob(pattern):
                    if save_file.is_file():
                        size = save_file.stat().st_size
                        found_saves.append({
                            "path": save_file,
                            "name": save_file.name,
                            "size": size,
                            "gen": detect_generation(size)
                        })
                        logger.info(f"Found: {save_file} (Gen{detect_generation(size)}, {size} bytes)")

        except PermissionError:
            logger.debug(f"Permission denied: {search_path}")
        except Exception as e:
            logger.error(f"Error searching {search_path}: {e}")

    return found_saves


def detect_generation(size):
    """Detecta geração pelo tamanho"""
    if size == 32768:
        return 1
    elif size in (32816,):
        return 2
    elif size == 131072:
        return 3
    else:
        return "?"


def main():
    logger.info("Starting save file search...")

    saves = find_saves()

    logger.info(f"\n{'='*80}")
    logger.info(f"Found {len(saves)} save files:")
    logger.info(f"{'='*80}\n")

    if not saves:
        logger.warning("No save files found!")
        print("\nNenhum save encontrado com 'pokemon' no nome.")
        print("Procurado em:")
        for path in SEARCH_PATHS:
            print(f"  - {path}")
        return 1

    # Ordenar por geração
    saves.sort(key=lambda x: (x["gen"], x["name"]))

    for idx, save in enumerate(saves, 1):
        gen_str = f"Gen{save['gen']}" if save['gen'] != "?" else "Unknown"
        logger.info(f"{idx}. {save['name']:40s} ({gen_str:5s}) {save['size']:>10d} bytes")
        logger.info(f"   Path: {save['path']}")
        print(f"{idx}. {save['name']:40s} ({gen_str:5s}) {save['size']:>10d} bytes")
        print(f"   {save['path']}\n")

    # Salvar lista em arquivo de configuração
    saves_list_file = Path(__file__).parent / "saves_found.txt"
    with open(saves_list_file, "w") as f:
        for save in saves:
            f.write(f"{save['path']}\n")

    logger.info(f"\nSaves list saved to: {saves_list_file}")
    logger.info(f"Log file: {LOG_FILE}")

    return 0


if __name__ == "__main__":
    exit(main())
