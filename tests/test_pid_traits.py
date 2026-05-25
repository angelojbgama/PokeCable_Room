from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent / "Pokecable_tool"
RUNTIME = REPO_ROOT / "pokecable_runtime"
for _path in (str(REPO_ROOT), str(RUNTIME)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from canonical import CanonicalMove, CanonicalPokemon, CanonicalSpecies, CanonicalStats  # noqa: E402
from compatibility.rules import build_compatibility_report  # noqa: E402
from data.pid_traits import (  # noqa: E402
    SPINDA_NATIONAL_DEX_ID,
    UNOWN_NATIONAL_DEX_ID,
    WURMPLE_NATIONAL_DEX_ID,
    gen3_spinda_pattern_key,
    gen3_spinda_spot_signature,
    gen3_species_pid_traits,
    gen3_wurmple_branch,
)
from data.unown_forms import gen3_unown_form_from_personality  # noqa: E402
from parsers.gen3 import Gen3Parser  # noqa: E402


TEST_SAVE = REPO_ROOT.parent / "roms" / "test-saves" / "gen 3" / "Pokémon - Emerald Version.sav"


def _canonical_gen3(national_dex_id: int, name: str, personality: int) -> CanonicalPokemon:
    return CanonicalPokemon(
        source_generation=3,
        source_game="pokemon_emerald",
        species_national_id=national_dex_id,
        species_name=name,
        nickname=name.upper()[:10],
        level=30,
        ot_name="STRESS",
        trainer_id=0x4242,
        experience=27000,
        moves=[CanonicalMove(move_id=33, pp=20, max_pp=20, pp_ups=0, source_generation=3)],
        ivs=CanonicalStats(hp=20, attack=20, defense=20, speed=20, special=20, special_attack=20, special_defense=20),
        evs=CanonicalStats(hp=0, attack=0, defense=0, speed=0, special=0, special_attack=0, special_defense=0),
        metadata={
            "is_shiny": False,
            "gender": None,
            "personality": personality,
        },
        species=CanonicalSpecies(
            national_dex_id=national_dex_id,
            source_species_id=national_dex_id,
            source_species_id_space="national_dex",
            name=name,
        ),
    )


def test_pid_helper_formulas():
    assert gen3_wurmple_branch(0) == "silcoon"
    assert gen3_wurmple_branch(5) == "cascoon"
    assert gen3_spinda_spot_signature(0x12345678) == ((0, -1), (-2, -3), (-4, -5), (-6, -7))
    assert gen3_spinda_pattern_key(0x12345678) == "+0,-1|-2,-3|-4,-5|-6,-7"
    assert gen3_species_pid_traits(UNOWN_NATIONAL_DEX_ID, 0x03030303)["unown_form"] == gen3_unown_form_from_personality(0x03030303)


@pytest.mark.skipif(not TEST_SAVE.exists(), reason="test save de Emerald nao disponivel")
def test_gen3_roundtrip_preserves_explicit_personality_traits(tmp_path: Path):
    local_save = tmp_path / TEST_SAVE.name
    shutil.copy2(TEST_SAVE, local_save)
    parser = Gen3Parser()
    parser.load(local_save)

    cases = [
        (SPINDA_NATIONAL_DEX_ID, "Spinda", 0x12345678),
        (WURMPLE_NATIONAL_DEX_ID, "Wurmple", 0x00000007),
        (UNOWN_NATIONAL_DEX_ID, "Unown", 0x03030303),
    ]
    for national_id, name, personality in cases:
        parser.import_canonical("party:0", _canonical_gen3(national_id, name, personality))
        exported = parser.export_canonical("party:0")
        assert exported.metadata["personality"] == personality
        assert exported.metadata.get("unown_form") == gen3_species_pid_traits(national_id, personality).get("unown_form")
        assert exported.metadata.get("wurmple_branch") == gen3_species_pid_traits(national_id, personality).get("wurmple_branch")
        assert exported.metadata.get("spinda_pattern") == gen3_species_pid_traits(national_id, personality).get("spinda_pattern")


def test_gen3_to_gen2_report_explains_pid_loss_and_species_blocks():
    pikachu = _canonical_gen3(25, "Pikachu", 0xCAFEBABE)
    pikachu_report = build_compatibility_report(pikachu, 2, cross_generation_enabled=True, policy="auto_retrocompat")
    assert any("PID/personality da Gen 3" in message for message in pikachu_report.transformations)

    wurmple = _canonical_gen3(WURMPLE_NATIONAL_DEX_ID, "Wurmple", 0x00000007)
    wurmple_report = build_compatibility_report(wurmple, 2, cross_generation_enabled=True, policy="auto_retrocompat")
    assert not wurmple_report.compatible
    assert any("nao existe na Gen 2" in message for message in wurmple_report.blocking_reasons)

    spinda = _canonical_gen3(SPINDA_NATIONAL_DEX_ID, "Spinda", 0x12345678)
    spinda_report = build_compatibility_report(spinda, 2, cross_generation_enabled=True, policy="auto_retrocompat")
    assert not spinda_report.compatible
    assert any("nao existe na Gen 2" in message for message in spinda_report.blocking_reasons)
