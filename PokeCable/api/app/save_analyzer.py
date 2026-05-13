"""
Save file analyzer - provides REST endpoint to analyze save files
"""
import logging
from pathlib import Path
import tempfile
from typing import Optional

logger = logging.getLogger("pokecable.save_analyzer")


def analyze_save_file(save_bytes: bytes, filename: str) -> Optional[dict]:
    """
    Analyze a save file and return pokemon list

    Args:
        save_bytes: Raw bytes of the save file
        filename: Original filename (.sav or .srm)

    Returns:
        Dict with 'generation', 'game', and 'pokemon' list, or None if failed
    """
    try:
        # Write to temp file for analysis
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as tmp:
            tmp.write(save_bytes)
            tmp_path = Path(tmp.name)

        try:
            from saves import detect_parser

            logger.debug(f"Analyzing save: {filename} ({len(save_bytes)} bytes)")
            parser = detect_parser(tmp_path)

            if not parser:
                logger.error(f"Cannot detect parser for: {filename}")
                return None

            generation = parser.get_generation()
            game = parser.get_game_id()

            # Load party pokemon
            try:
                party = parser.list_party()
            except Exception as e:
                logger.warning(f"Failed to load party: {e}")
                party = []

            # Load boxes
            try:
                boxes = parser.list_boxes()
            except Exception as e:
                logger.warning(f"Failed to load boxes: {e}")
                boxes = []

            pokemon_data = []

            # Add party pokemon
            for idx, pokemon in enumerate(party):
                pokemon_data.append({
                    "source": "party",
                    "index": idx,
                    "location": getattr(pokemon, 'location', f"party:{idx}"),
                    "species_name": getattr(pokemon, 'species_name', 'Unknown'),
                    "level": getattr(pokemon, 'level', 0),
                    "nickname": getattr(pokemon, 'nickname', ''),
                    "display_summary": getattr(pokemon, 'display_summary', f"Pokémon {idx+1}"),
                })

            # Add box pokemon
            for idx, pokemon in enumerate(boxes):
                pokemon_data.append({
                    "source": "boxes",
                    "index": idx,
                    "location": getattr(pokemon, 'location', f"box:{idx}"),
                    "species_name": getattr(pokemon, 'species_name', 'Unknown'),
                    "level": getattr(pokemon, 'level', 0),
                    "nickname": getattr(pokemon, 'nickname', ''),
                    "display_summary": getattr(pokemon, 'display_summary', f"Pokémon {idx+1}"),
                })

            result = {
                "generation": generation,
                "game": game,
                "pokemon": pokemon_data,
                "party_count": len(party),
                "box_count": len(boxes),
            }

            logger.info(
                f"Analyzed {filename}: Gen{generation}, {len(party)} party, {len(boxes)} boxes"
            )
            return result

        finally:
            # Clean up temp file
            try:
                tmp_path.unlink()
            except Exception:
                pass

    except ImportError as e:
        logger.error(f"Backend not available: {e}")
        return None
    except Exception as e:
        logger.exception(f"Error analyzing save: {e}")
        return None
