from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pokecable_room.backups import create_backup, restore_backup
from pokecable_room.parsers.base import PokemonPayload
from pokecable_room.trade import validate_payload_for_local_save


class ClientSafetyTests(unittest.TestCase):
    def test_client_rejects_payload_from_other_generation(self) -> None:
        payload = PokemonPayload(
            generation=3,
            game="pokemon_emerald",
            species_id=64,
            species_name="Kadabra",
            level=32,
            nickname="KADABRA",
            ot_name="TEST",
            trainer_id=1,
            raw_data_base64="ZmFrZQ==",
            display_summary="Kadabra Lv. 32",
        )
        with self.assertRaises(ValueError):
            validate_payload_for_local_save(payload, local_generation=2)

    def test_backup_and_restore_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            save = root / "Pokemon Crystal.sav"
            save.write_bytes(b"synthetic-save")
            backup_dir = root / "backups"
            backup, metadata = create_backup(
                save,
                backup_dir,
                {
                    "original_save": str(save),
                    "generation": 2,
                    "game": "pokemon_crystal",
                    "room": "room",
                    "sent": {"species": "Kadabra", "level": 32, "nickname": "KADABRA"},
                    "received": {"species": "Machoke", "level": 35, "nickname": "MACHOKE"},
                },
            )
            self.assertTrue(backup.exists())
            self.assertTrue(metadata.exists())
            save.write_bytes(b"changed")
            restore_backup(backup, save)
            self.assertEqual(save.read_bytes(), b"synthetic-save")


if __name__ == "__main__":
    unittest.main()
