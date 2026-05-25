from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pokecable_save import SaveError, load_save

GEN3_SECTOR_SIZE = 0x1000
GEN3_SLOT_SIZE = GEN3_SECTOR_SIZE * 14
GEN3_SIGNATURE = 0x08012025


@dataclass(frozen=True, slots=True)
class SectorMeta:
    base: int
    physical_index: int
    section_id: int
    counter: int
    raw: bytes


def analyze_gen3_save(path: str | Path) -> dict[str, Any]:
    save_path = Path(path)
    data = save_path.read_bytes()
    if len(data) < GEN3_SLOT_SIZE * 2:
        return {"success": False, "message": "Arquivo não parece ser save Gen 3 de 128 KiB."}

    slots = []
    all_sectors = []
    for slot_index, base in enumerate((0, GEN3_SLOT_SIZE)):
        valid: list[SectorMeta] = []
        unique_ids: set[int] = set()
        for physical_index in range(14):
            offset = base + physical_index * GEN3_SECTOR_SIZE
            raw = data[offset : offset + GEN3_SECTOR_SIZE]
            section_id = int.from_bytes(raw[0xFF4:0xFF6], "little")
            signature = int.from_bytes(raw[0xFF8:0xFFC], "little")
            counter = int.from_bytes(raw[0xFFC:0x1000], "little")
            if signature != GEN3_SIGNATURE or section_id >= 14:
                continue
            meta = SectorMeta(base=base, physical_index=physical_index, section_id=section_id, counter=counter, raw=raw)
            valid.append(meta)
            unique_ids.add(section_id)
            all_sectors.append(meta)
        slots.append(
            {
                "slot_index": slot_index,
                "base": base,
                "valid_sector_count": len(valid),
                "unique_section_ids": sorted(unique_ids),
                "unique_section_count": len(unique_ids),
                "has_section1": 1 in unique_ids,
                "max_counter": max((sector.counter for sector in valid), default=-1),
            }
        )
    return {"success": True, "path": str(save_path), "slots": slots, "sector_count": len(all_sectors)}


def repair_gen3_save_file(path: str | Path, *, write: bool = True) -> dict[str, Any]:
    save_path = Path(path)
    data = bytearray(save_path.read_bytes())
    if len(data) < GEN3_SLOT_SIZE * 2:
        return {"success": False, "changed": False, "message": "Arquivo não parece ser save Gen 3 de 128 KiB."}

    try:
        load_save(save_path)
        return {"success": True, "changed": False, "message": "Save já é válido."}
    except SaveError:
        pass

    sectors = _collect_valid_sectors(bytes(data))
    if not sectors:
        return {"success": False, "changed": False, "message": "Nenhum setor válido encontrado."}

    preferred_base = _choose_preferred_base(sectors)
    canonical = _build_canonical_slot(preferred_base, sectors)
    if canonical is None:
        return {"success": False, "changed": False, "message": "Não foi possível reconstruir todos os 14 setores."}

    rebuilt = bytearray(data)
    next_counter = max((sector.counter for sector in sectors), default=0) + 1
    _write_slot(rebuilt, 0, canonical, next_counter)
    _write_slot(rebuilt, GEN3_SLOT_SIZE, canonical, max(0, next_counter - 1))

    if write:
        save_path.write_bytes(bytes(rebuilt))
        try:
            load_save(save_path)
        except Exception as exc:
            save_path.write_bytes(bytes(data))
            return {"success": False, "changed": False, "message": f"Reparo revertido após verificação falhar: {exc}"}
    return {
        "success": True,
        "changed": True,
        "message": "Save Gen 3 reparado com setores existentes.",
        "preferred_base": preferred_base,
    }


def repair_save_corpus(root: str | Path) -> list[dict[str, Any]]:
    root_path = Path(root)
    results = []
    for path in sorted(root_path.rglob("*.sav")):
        if path.stat().st_size != GEN3_SLOT_SIZE * 2:
            continue
        analysis = analyze_gen3_save(path)
        if not analysis.get("success"):
            continue
        results.append({"path": str(path), "analysis": analysis, "repair": repair_gen3_save_file(path)})
    return results


def _collect_valid_sectors(data: bytes) -> list[SectorMeta]:
    sectors: list[SectorMeta] = []
    for base in (0, GEN3_SLOT_SIZE):
        for physical_index in range(14):
            offset = base + physical_index * GEN3_SECTOR_SIZE
            raw = data[offset : offset + GEN3_SECTOR_SIZE]
            section_id = int.from_bytes(raw[0xFF4:0xFF6], "little")
            signature = int.from_bytes(raw[0xFF8:0xFFC], "little")
            counter = int.from_bytes(raw[0xFFC:0x1000], "little")
            if signature != GEN3_SIGNATURE or section_id >= 14:
                continue
            sectors.append(SectorMeta(base=base, physical_index=physical_index, section_id=section_id, counter=counter, raw=raw))
    return sectors


def _choose_preferred_base(sectors: list[SectorMeta]) -> int:
    candidates = []
    for base in (0, GEN3_SLOT_SIZE):
        base_sectors = [sector for sector in sectors if sector.base == base]
        unique_ids = {sector.section_id for sector in base_sectors}
        candidates.append(
            (
                len(unique_ids),
                1 if 1 in unique_ids else 0,
                max((sector.counter for sector in base_sectors), default=-1),
                -base,
                base,
            )
        )
    candidates.sort(reverse=True)
    return candidates[0][-1]


def _build_canonical_slot(preferred_base: int, sectors: list[SectorMeta]) -> list[bytes] | None:
    ordered: list[bytes] = []
    for section_id in range(14):
        chosen = _choose_sector_for_section(preferred_base, sectors, section_id)
        if chosen is None:
            return None
        ordered.append(chosen.raw)
    return ordered


def _choose_sector_for_section(preferred_base: int, sectors: list[SectorMeta], section_id: int) -> SectorMeta | None:
    matching = [sector for sector in sectors if sector.section_id == section_id]
    if not matching:
        return None
    matching.sort(
        key=lambda sector: (
            1 if sector.base == preferred_base else 0,
            sector.counter,
        ),
        reverse=True,
    )
    return matching[0]


def _write_slot(buffer: bytearray, base: int, sectors: list[bytes], counter: int) -> None:
    for physical_index, raw in enumerate(sectors):
        sector = bytearray(raw)
        sector[0xFF4:0xFF6] = physical_index.to_bytes(2, "little")
        sector[0xFF8:0xFFC] = GEN3_SIGNATURE.to_bytes(4, "little")
        sector[0xFFC:0x1000] = int(counter).to_bytes(4, "little")
        offset = base + physical_index * GEN3_SECTOR_SIZE
        buffer[offset : offset + GEN3_SECTOR_SIZE] = sector
