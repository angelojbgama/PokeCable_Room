import pytest
from app.engines.gen2.types import get_type_multiplier_gen2

def test_gen2_dark_type_immunity():
    # Dark é imune a Psychic
    multiplier = get_type_multiplier_gen2("psychic", ["dark"])
    assert multiplier == 0.0

def test_gen2_steel_type_resistances():
    # Steel resiste a Normal
    multiplier = get_type_multiplier_gen2("normal", ["steel"])
    assert multiplier == 0.5
    
    # Steel é imune a Poison
    multiplier = get_type_multiplier_gen2("poison", ["steel"])
    assert multiplier == 0.0

def test_gen2_ghost_vs_psychic_fix():
    # Ghost agora é super eficaz contra Psychic
    multiplier = get_type_multiplier_gen2("ghost", ["psychic"])
    assert multiplier == 2.0

def test_gen2_bug_vs_poison_nerf():
    # Bug vs. Poison não é mais super eficaz
    multiplier = get_type_multiplier_gen2("bug", ["poison"])
    assert multiplier == 1.0 # Em vez de 2.0
    
    # Poison vs. Bug também é neutro na Gen 2.
    multiplier = get_type_multiplier_gen2("poison", ["bug"])
    assert multiplier == 1.0

def test_gen2_ice_vs_fire_nerf():
    # Ice vs. Fire agora é 0.5x
    multiplier = get_type_multiplier_gen2("ice", ["fire"])
    assert multiplier == 0.5
