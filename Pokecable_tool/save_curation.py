from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _path in (str(REPO_ROOT), str(RUNTIME)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from data.moves import move_exists  # noqa: E402
from data.species import native_to_national, species_exists_in_generation  # noqa: E402
from parsers.gen4 import BOX_CAPACITY, BOX_COUNT, Gen4Parser, _u16, decrypt_pk4  # noqa: E402


TEST_SAVES_ROOT = REPO_ROOT.parent / "roms" / "test-saves"
GEN4_SAVE_DIR = TEST_SAVES_ROOT / "gen 4"


@dataclass(frozen=True, slots=True)
class Gen4CuratedSave:
    path: Path
    approved_for_analysis: bool
    has_box_residue: bool
    notes: str = ""


def _iter_gen4_save_paths() -> list[Path]:
    if not GEN4_SAVE_DIR.exists():
        return []
    return sorted(path for path in GEN4_SAVE_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".sav")


def _box_residue_count(parser: Gen4Parser) -> int:
    invalid_count = 0
    for box_index in range(BOX_COUNT):
        for slot_index in range(BOX_CAPACITY):
            decrypted = decrypt_pk4(parser._read_box_raw(box_index, slot_index))
            species_id = _u16(decrypted, 0x08)
            if species_id <= 0:
                continue
            try:
                national_dex_id = native_to_national(4, species_id)
            except Exception:
                invalid_count += 1
                continue
            if not species_exists_in_generation(national_dex_id, 4):
                invalid_count += 1
                continue
            for move_slot in range(4):
                move_id = _u16(decrypted, 0x28 + (move_slot * 2))
                pp_ups = int(decrypted[0x34 + move_slot])
                if move_id and not move_exists(move_id, 4):
                    invalid_count += 1
                    break
                if pp_ups > 3:
                    invalid_count += 1
                    break
    return invalid_count


def _functional_integrity_notes(parser: Gen4Parser) -> str | None:
    if not parser.validate():
        return "parser.validate() falhou"
    for summary in parser.list_party() + parser.list_boxes():
        if summary.held_item_name and "?" in str(summary.held_item_name):
            return f"held item invalido em {summary.location}"
        try:
            canonical = parser.export_canonical(summary.location)
        except Exception as exc:
            return f"export_canonical falhou em {summary.location}: {type(exc).__name__}: {exc}"
        if canonical.held_item and canonical.held_item.name and "?" in str(canonical.held_item.name):
            return f"held item canonico invalido em {summary.location}"
        for move in canonical.moves:
            name = str(move.name or "")
            if not name or name.startswith("Move #"):
                return f"move invalido em {summary.location}"
            if int(move.pp_ups or 0) > 3:
                return f"pp ups invalido em {summary.location}"
            if int(move.pp or 0) > int(move.max_pp or 0):
                return f"pp invalido em {summary.location}"
    return None


@lru_cache(maxsize=1)
def get_gen4_save_audit() -> tuple[Gen4CuratedSave, ...]:
    records: list[Gen4CuratedSave] = []
    for path in _iter_gen4_save_paths():
        parser = Gen4Parser()
        if not parser.detect(path):
            records.append(Gen4CuratedSave(path=path, approved_for_analysis=False, has_box_residue=False, notes="parser.detect() falhou"))
            continue
        try:
            parser.load(path)
        except Exception as exc:
            records.append(Gen4CuratedSave(path=path, approved_for_analysis=False, has_box_residue=False, notes=f"load falhou: {type(exc).__name__}: {exc}"))
            continue
        failure = _functional_integrity_notes(parser)
        residue_count = _box_residue_count(parser)
        approved = failure is None
        if failure is not None:
            notes = failure
        elif residue_count:
            notes = f"{residue_count} slots de box com residuo cru"
        else:
            notes = "sem residuo detectado"
        records.append(
            Gen4CuratedSave(
                path=path,
                approved_for_analysis=approved,
                has_box_residue=residue_count > 0,
                notes=notes,
            )
        )
    return tuple(records)


def get_curated_gen4_saves() -> list[Path]:
    return [record.path for record in get_gen4_save_audit() if record.approved_for_analysis]


def filter_dev_test_save_corpus(paths: list[Path]) -> list[Path]:
    curated_gen4 = {path.resolve() for path in get_curated_gen4_saves()}
    filtered: list[Path] = []
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            filtered.append(path)
            continue
        try:
            in_curated_gen4_dir = resolved.parent == GEN4_SAVE_DIR.resolve()
        except OSError:
            in_curated_gen4_dir = False
        if in_curated_gen4_dir and resolved not in curated_gen4:
            continue
        filtered.append(path)
    return filtered
