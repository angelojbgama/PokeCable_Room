from __future__ import annotations

import importlib.util
import json
import struct
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "export_pret_battle_assets.py"


def load_exporter_module():
    spec = importlib.util.spec_from_file_location("export_pret_battle_assets", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fake_png(path: Path, *, width: int = 8, height: int = 8) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x06\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def test_export_pret_battle_assets_builds_manifest(tmp_path: Path) -> None:
    exporter = load_exporter_module()
    reference = tmp_path / "reference" / "pret"
    output = tmp_path / "frontend" / "generated" / "battle-assets"

    write_fake_png(reference / "pokered" / "gfx" / "pokemon" / "front" / "abra.png")
    write_fake_png(reference / "pokered" / "gfx" / "pokemon" / "back" / "abrab.png")
    write_fake_png(reference / "pokered" / "gfx" / "battle" / "battle_hud_1.png")
    write_fake_png(reference / "pokered" / "gfx" / "battle" / "move_anim_0.png", width=128, height=40)
    (reference / "pokered" / "engine" / "battle").mkdir(parents=True)
    (reference / "pokered" / "engine" / "battle" / "core.asm").write_text("BattleCore:\n", encoding="utf-8")
    (reference / "pokered" / "constants").mkdir(parents=True, exist_ok=True)
    (reference / "pokered" / "constants" / "move_animation_constants.asm").write_text(
        """\tconst SUBANIM_0_STAR_TWICE
DEF NUM_SUBANIMS EQU const_value
\tconst FRAMEBLOCK_01
DEF NUM_FRAMEBLOCKS EQU const_value
""",
        encoding="utf-8",
    )
    (reference / "pokered" / "data" / "battle_anims").mkdir(parents=True)
    (reference / "pokered" / "data" / "battle_anims" / "frame_blocks.asm").write_text(
        """FrameBlockPointers:
\tdw FrameBlock01
\tassert_table_length NUM_FRAMEBLOCKS
FrameBlock01:
\tdb 1 ; #
\tdbsprite 0, 0, 0, 0, $2c, OAM_XFLIP
""",
        encoding="utf-8",
    )
    (reference / "pokered" / "data" / "battle_anims" / "subanimations.asm").write_text(
        """SubanimationPointers:
\tdw Subanim_0StarTwice
\tassert_table_length NUM_SUBANIMS
Subanim_0StarTwice:
\tsubanim SUBANIMTYPE_HFLIP, 1
\tdb FRAMEBLOCK_01, BASECOORD_0F, FRAMEBLOCKMODE_00
""",
        encoding="utf-8",
    )
    (reference / "pokered" / "data" / "moves").mkdir(parents=True)
    (reference / "pokered" / "data" / "moves" / "animations.asm").write_text(
        """AttackAnimationPointers:
\ttable_width 2
\tdw PoundAnim
\tassert_table_length NUM_ATTACKS
PoundAnim:
\tbattle_anim POUND, SUBANIM_0_STAR_TWICE, 0, 8
\tdb -1 ; end
""",
        encoding="utf-8",
    )

    write_fake_png(reference / "pokecrystal" / "gfx" / "pokemon" / "abra" / "front.png")
    write_fake_png(reference / "pokecrystal" / "gfx" / "pokemon" / "abra" / "back.png")
    write_fake_png(reference / "pokecrystal" / "gfx" / "battle" / "hp_exp_bar_border.png")
    write_fake_png(reference / "pokecrystal" / "gfx" / "pack" / "pack.png")
    write_fake_png(reference / "pokecrystal" / "gfx" / "pack" / "pack_menu.png")
    write_fake_png(reference / "pokecrystal" / "gfx" / "stats" / "stats_tiles.png")
    write_fake_png(reference / "pokecrystal" / "gfx" / "battle_anims" / "hit.png", width=16, height=104)
    (reference / "pokecrystal" / "engine" / "battle").mkdir(parents=True)
    (reference / "pokecrystal" / "engine" / "battle" / "core.asm").write_text("BattleCore:\n", encoding="utf-8")
    (reference / "pokecrystal" / "constants").mkdir(parents=True, exist_ok=True)
    (reference / "pokecrystal" / "constants" / "battle_anim_constants.asm").write_text(
        """\tconst BATTLE_ANIM_GFX_HIT        ; 01
\tDEF NUM_BATTLE_ANIM_GFX EQU const_value
\tconst BATTLE_ANIM_OBJ_HIT_BIG_YFIX
\tDEF NUM_BATTLE_ANIM_OBJS EQU const_value
\tconst BATTLE_ANIM_FRAMESET_HIT_BIG
\tDEF NUM_BATTLE_ANIM_FRAMESETS EQU const_value
\tconst BATTLE_ANIM_OAMSET_00
\tDEF NUM_BATTLE_ANIM_OAMSETS EQU const_value
""",
        encoding="utf-8",
    )
    (reference / "pokecrystal" / "gfx" / "battle_anims.asm").write_text(
        'AnimObjHitGFX:       INCBIN "gfx/battle_anims/hit.2bpp.lz"\n',
        encoding="utf-8",
    )
    (reference / "pokecrystal" / "data" / "battle_anims").mkdir(parents=True)
    (reference / "pokecrystal" / "data" / "battle_anims" / "object_gfx.asm").write_text(
        "\tanim_obj_gfx  0, AnimObj00GFX\n\tanim_obj_gfx 21, AnimObjHitGFX\n",
        encoding="utf-8",
    )
    (reference / "pokecrystal" / "data" / "battle_anims" / "objects.asm").write_text(
        "; BATTLE_ANIM_OBJ_HIT_BIG_LEGACY_NAME\n\tbattleanimobj RELATIVE_X, $ff, BATTLE_ANIM_FRAMESET_HIT_BIG, BATTLE_ANIM_FUNC_NULL, PAL_BATTLE_OB_GRAY, BATTLE_ANIM_GFX_HIT\n",
        encoding="utf-8",
    )
    (reference / "pokecrystal" / "data" / "battle_anims" / "framesets.asm").write_text(
        """BattleAnimFrameData:
\tdw .Frameset_HitBig
\tassert_table_length NUM_BATTLE_ANIM_FRAMESETS
.Frameset_HitBig:
\toamframe BATTLE_ANIM_OAMSET_00, 6
\toamdelete
""",
        encoding="utf-8",
    )
    (reference / "pokecrystal" / "data" / "battle_anims" / "oam.asm").write_text(
        """BattleAnimOAMData:
\tbattleanimoam $00, 1, .OAMData_00 ; BATTLE_ANIM_OAMSET_00
\tassert_table_length NUM_BATTLE_ANIM_OAMSETS
.OAMData_00:
\tdbsprite -1, -1, 0, 0, $00, $0
""",
        encoding="utf-8",
    )
    (reference / "pokecrystal" / "data" / "moves").mkdir(parents=True)
    (reference / "pokecrystal" / "data" / "moves" / "animations.asm").write_text(
        """BattleAnimations::
\tdw BattleAnim_0
\tdw BattleAnim_Pound
\tassert_table_length NUM_ATTACKS + 1
BattleAnim_Pound:
\tanim_1gfx BATTLE_ANIM_GFX_HIT
\tanim_obj BATTLE_ANIM_OBJ_HIT_BIG_YFIX, 136, 56, $0
\tanim_wait 6
\tanim_ret
""",
        encoding="utf-8",
    )

    write_fake_png(reference / "pokeemerald" / "graphics" / "pokemon" / "abra" / "front.png")
    write_fake_png(reference / "pokeemerald" / "graphics" / "pokemon" / "abra" / "anim_front.png", width=64, height=128)
    write_fake_png(reference / "pokeemerald" / "graphics" / "pokemon" / "abra" / "back.png")
    write_fake_png(reference / "pokeemerald" / "graphics" / "battle_interface" / "textbox.png")
    write_fake_png(reference / "pokeemerald" / "graphics" / "battle_anims" / "sprites" / "impact.png", width=32, height=160)
    (reference / "pokeemerald" / "src").mkdir(parents=True)
    (reference / "pokeemerald" / "src" / "battle_main.c").write_text("void BattleMain(void) {}\n", encoding="utf-8")
    (reference / "pokeemerald" / "src" / "graphics.c").write_text(
        'const u32 gBattleAnimSpriteGfx_Impact[] = INCGFX_U32("graphics/battle_anims/sprites/impact.png", ".4bpp.lz");\n',
        encoding="utf-8",
    )
    (reference / "pokeemerald" / "src" / "data").mkdir(parents=True)
    (reference / "pokeemerald" / "src" / "data" / "battle_anim.h").write_text(
        "const struct CompressedSpriteSheet gBattleAnimPicTable[] =\n{\n    {gBattleAnimSpriteGfx_Impact, 0x0200, ANIM_TAG_IMPACT},\n};\n",
        encoding="utf-8",
    )
    (reference / "pokeemerald" / "data").mkdir(parents=True)
    (reference / "pokeemerald" / "data" / "battle_anim_scripts.s").write_text(
        """gBattleAnims_Moves::
\t.4byte Move_NONE
\t.4byte Move_POUND
\t.align 2
gBattleAnims_StatusConditions::
Move_POUND:
\tloadspritegfx ANIM_TAG_IMPACT
\tcreatesprite gBasicHitSplatSpriteTemplate, ANIM_TARGET, 2, 0, 0
\tdelay 4
\tend
""",
        encoding="utf-8",
    )

    manifest_path = exporter.export_assets(reference, output)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    animation_map = json.loads((output / "animation-map.json").read_text(encoding="utf-8"))
    assert manifest["generations"]["1"]["pokemon"]["species"]["abra"]["front"]["path"] == "gen1/pokemon/abra/front.png"
    assert manifest["generations"]["1"]["pokemon"]["species"]["abra"]["back"]["path"] == "gen1/pokemon/abra/back.png"
    assert manifest["generations"]["2"]["pokemon"]["count"] == 1
    assert manifest["generations"]["3"]["battle_assets"]["count"] == 2
    assert "src/battle_main.c" in manifest["generations"]["3"]["behavior_sources"]["files"]
    assert animation_map["schema"] == 1
    assert animation_map["generations"]["1"]["moves"]["pound"]["assets"][0]["path"] == "gen1/ui/battle/move_anim_0.png"
    assert animation_map["generations"]["1"]["moves"]["pound"]["assets"][0]["frame"]["layout"] == "gb_tile_sheet"
    assert animation_map["generations"]["1"]["moves"]["pound"]["assets"][0]["composites"][0]["frames"][0]["tiles"][0]["tile"] == 44
    assert animation_map["generations"]["2"]["moves"]["pound"]["assets"][0]["path"] == "gen2/ui/battle_anims/hit.png"
    assert animation_map["generations"]["2"]["moves"]["pound"]["assets"][0]["frame"]["count"] == 26
    assert animation_map["generations"]["2"]["moves"]["pound"]["assets"][0]["composites"][0]["frames"][0]["tiles"][0]["x"] == -8
    assert animation_map["generations"]["2"]["moves"]["pound"]["logic"]["objects"][0]["frameset"] == "BATTLE_ANIM_FRAMESET_HIT_BIG"
    assert animation_map["generations"]["2"]["moves"]["pound"]["logic"]["total_wait_frames"] == 6
    assert animation_map["generations"]["3"]["moves"]["pound"]["assets"][0]["path"] == "gen3/ui/battle_anims/sprites/impact.png"
    assert animation_map["generations"]["3"]["moves"]["pound"]["assets"][0]["frame"]["count"] == 5
    assert animation_map["generations"]["3"]["moves"]["pound"]["logic"]["loaded_tags"] == ["ANIM_TAG_IMPACT"]
    assert manifest["generations"]["3"]["pokemon"]["species"]["abra"]["anim_front"]["frame"]["count"] == 2
    assert (output / "gen2" / "ui" / "pack" / "pack.png").exists()
    assert (output / "gen2" / "ui" / "pack" / "pack_menu.png").exists()
    assert (output / "gen2" / "ui" / "stats" / "stats_tiles.png").exists()
    assert (output / "gen1" / "pokemon" / "abra" / "front.png").exists()
