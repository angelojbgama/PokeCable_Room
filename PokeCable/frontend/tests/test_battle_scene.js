const test = require("node:test");
const assert = require("node:assert/strict");

const {
  actionGroupsFromRequest,
  animationFamilyFromMove,
  battleProfileForGeneration,
  battleEffectBackgroundAssetForMove,
  battleUiAssetUrl,
  battleUiAssetsForGeneration,
  battleTextAssetsForGeneration,
  compositeFrameDurations,
  compositeScale,
  effectAssetsForProfile,
  effectVisualProfile,
  framePlanForRecord,
  gen2BattleAnimTimeline,
  gen2BattleCssVariables,
  gen2BattleLayout,
  gen2HpBarPixels,
  gen2HpClassForPixels,
  gen2BattleAnimFunctionProfile,
  humanizeMoveName,
  isGen2TileSheetAsset,
  renderBattleText,
  normalizeAssetSpeciesKey,
  normalizeMoveKey,
  normalizeSpeciesKey,
  parseBattleIdent,
  parseBattleLogLine,
  parseCondition,
  pokemonSpriteFramePlaybackForRecord,
  pokemonSpriteMotionProfile,
  tileFrameStyle,
  tileSheetPosition,
  tileStyle
} = require("../battle-scene.js");

const animationMap = require("../generated/battle-assets/animation-map.json");
const gen2Scene = require("../battle-scene-gen2.js");
const gen2FrontAnimSequences = require("../generated/battle-assets/gen2/pokemon-front-anim-sequences.json");
const gen3FrontAnimSequences = require("../generated/battle-assets/gen3/pokemon-front-anim-sequences.json");

test("normalizes species keys for generated battle assets", () => {
  assert.equal(normalizeSpeciesKey("Mr. Mime"), "mrmime");
  assert.equal(normalizeSpeciesKey("Farfetch'd"), "farfetchd");
  assert.equal(normalizeSpeciesKey("Nidoran♀"), "nidoranf");
  assert.equal(normalizeAssetSpeciesKey("Ho-Oh"), "ho_oh");
  assert.equal(normalizeAssetSpeciesKey("Mr. Mime"), "mr_mime");
  assert.equal(normalizeMoveKey("Thunder Punch"), "thunderpunch");
});

test("infers browser animation families from move names", () => {
  assert.equal(animationFamilyFromMove("Thunderbolt"), "electric");
  assert.equal(animationFamilyFromMove("Flamethrower"), "fire");
  assert.equal(animationFamilyFromMove("Surf"), "water");
  assert.equal(animationFamilyFromMove("Recover"), "status");
  assert.equal(animationFamilyFromMove("Pound"), "impact");
});

test("provides generation-specific battle UI profiles", () => {
  assert.equal(battleProfileForGeneration(1).baseWidth, 160);
  assert.deepEqual(battleProfileForGeneration(1).commandLabels.map(item => item.label), ["FIGHT", "PKMN", "ITEM", "RUN"]);
  assert.deepEqual(battleProfileForGeneration(2).commandLabels.map(item => item.label), ["FIGHT", "<PKMN>", "PACK", "RUN"]);
  assert.deepEqual(battleProfileForGeneration(3).commandLabels.map(item => item.label), ["FIGHT", "BAG", "POKéMON", "RUN"]);
  assert.equal(battleProfileForGeneration(3).baseWidth, 240);
});

test("resolves generation-specific battle ui assets", () => {
  assert.deepEqual(battleUiAssetsForGeneration(1), {
    balls: "gen1/ui/battle/balls.png",
    hudEnemy: "gen1/ui/battle/battle_hud_1.png",
    hudPlayer: "gen1/ui/battle/battle_hud_2.png",
    dialog: "gen1/ui/battle/battle_hud_3.png"
  });
  assert.deepEqual(battleUiAssetsForGeneration(2), {
    balls: "gen2/ui/battle/balls.png",
    hudEnemy: "gen2/ui/battle/enemy_hp_bar_border.png",
    hudPlayer: "gen2/ui/battle/hp_exp_bar_border.png",
    dialogFrame: "gen2/ui/frames/1.png",
    dialog: null
  });
  assert.deepEqual(battleUiAssetsForGeneration(3, "singles"), {
    ballStatusBar: "gen3/ui/battle_interface/ball_status_bar.png",
    hpBar: "gen3/ui/battle_interface/hpbar.png",
    hpBarAnim: "gen3/ui/battle_interface/hpbar_anim.png",
    hudEnemy: "gen3/ui/battle_interface/healthbox_singles_opponent.png",
    hudPlayer: "gen3/ui/battle_interface/healthbox_singles_player.png",
    numbers1: "gen3/ui/battle_interface/numbers1.png",
    numbers2: "gen3/ui/battle_interface/numbers2.png",
    status: "gen3/ui/battle_interface/status.png",
    status2: "gen3/ui/battle_interface/status2.png",
    status3: "gen3/ui/battle_interface/status3.png",
    status4: "gen3/ui/battle_interface/status4.png",
    bag: "gen3/ui/battle_anims/sprites/item_bag.png",
    dialog: "gen3/ui/battle_interface/textbox.png"
  });
  assert.deepEqual(battleUiAssetsForGeneration(3, "doubles"), {
    ballStatusBar: "gen3/ui/battle_interface/ball_status_bar.png",
    hpBar: "gen3/ui/battle_interface/hpbar.png",
    hpBarAnim: "gen3/ui/battle_interface/hpbar_anim.png",
    hudEnemy: "gen3/ui/battle_interface/healthbox_doubles_opponent.png",
    hudPlayer: "gen3/ui/battle_interface/healthbox_doubles_player.png",
    numbers1: "gen3/ui/battle_interface/numbers1.png",
    numbers2: "gen3/ui/battle_interface/numbers2.png",
    status: "gen3/ui/battle_interface/status.png",
    status2: "gen3/ui/battle_interface/status2.png",
    status3: "gen3/ui/battle_interface/status3.png",
    status4: "gen3/ui/battle_interface/status4.png",
    bag: "gen3/ui/battle_anims/sprites/item_bag.png",
    dialog: "gen3/ui/battle_interface/textbox.png"
  });
  assert.equal(battleUiAssetUrl("gen3/ui/battle_interface/textbox.png"), "/generated/battle-assets/gen3/ui/battle_interface/textbox.png");
});

test("exposes gen 2 battle layout coordinates from pokecrystal asm", () => {
  const layout = gen2BattleLayout();
  assert.deepEqual(layout.screen, { x: 0, y: 0, width: 160, height: 144 });
  assert.deepEqual(layout.field, { x: 0, y: 0, width: 160, height: 96 });
  assert.deepEqual(layout.textbox, { x: 0, y: 96, width: 160, height: 48, asm: "hlcoord 0,12" });
  assert.deepEqual(layout.enemy.sprite, { x: 96, y: 0, width: 56, height: 56, asm: "hlcoord 12,0" });
  assert.deepEqual(layout.player.sprite, { x: 16, y: 48, width: 56, height: 56, asm: "hlcoord 2,6" });
  assert.deepEqual(layout.enemy.hud, { x: 8, y: 0, width: 88, height: 32, asm: "hlcoord 1,0; lb bc,4,11" });
  assert.deepEqual(layout.player.hud, { x: 72, y: 56, width: 88, height: 40, asm: "hlcoord 9,7; lb bc,5,11" });
  assert.deepEqual(layout.enemy.hp, { x: 16, y: 16, width: 64, height: 8, asm: "hlcoord 2,2; HP_BAR_LENGTH" });
  assert.deepEqual(layout.player.hp, { x: 80, y: 72, width: 64, height: 8, asm: "hlcoord 10,9; HP_BAR_LENGTH" });
  assert.deepEqual(layout.enemy.balls, { x: 72, y: 32, direction: -8, asm: "ldpixel wPlaceBallsX, 9, 4" });
  assert.deepEqual(layout.player.balls, { x: 96, y: 96, direction: 8, asm: "ldpixel wPlaceBallsX, 12, 12" });
  assert.deepEqual(layout.commandMenu, { x: 64, y: 96, width: 96, height: 48, asm: "menu_coords 8,12,19,17; dn 2,2; spacing 6" });
  assert.deepEqual(layout.moveMenu, { x: 32, y: 96, width: 112, height: 40, asm: "hlcoord 4,12; lb bc,4,14" });
  assert.deepEqual(layout.moveInfo, { x: 0, y: 64, width: 72, height: 32, asm: "hlcoord 0,8; lb bc,3,9" });
});

test("exports gen 2 css coordinates from asm layout", () => {
  const css = gen2BattleCssVariables();
  assert.match(css, /--gen2-enemy-sprite-left:60%/);
  assert.match(css, /--gen2-player-sprite-left:10%/);
  assert.match(css, /--gen2-player-sprite-top:50%/);
  assert.match(css, /--gen2-enemy-hud-left:5%/);
  assert.match(css, /--gen2-player-hud-left:45%/);
  assert.match(css, /--gen2-player-hud-top:58\.333333333333336%/);
  assert.match(css, /--gen2-command-menu-left:40%/);
  assert.match(css, /--gen2-move-menu-left:20%/);
  assert.match(css, /--gen2-move-info-top-from-bottom:-66\.66666666666666/);
  assert.match(css, /--gen2-enemy-balls-left:45%/);
  assert.match(css, /--gen2-enemy-balls-top:33\.33333333333333/);
  assert.match(css, /--gen2-player-balls-left:60%/);
  assert.match(css, /--gen2-player-balls-top:100%/);
});

test("matches pokecrystal gen 2 hp bar pixel and palette thresholds", () => {
  assert.equal(gen2HpBarPixels(0, 100), 0);
  assert.equal(gen2HpBarPixels(1, 999), 1);
  assert.equal(gen2HpBarPixels(50, 100), 24);
  assert.equal(gen2HpBarPixels(21, 100), 10);
  assert.equal(gen2HpBarPixels(20, 100), 9);
  assert.equal(gen2HpBarPixels(100, 100), 48);
  assert.equal(gen2HpClassForPixels(24), "is-high");
  assert.equal(gen2HpClassForPixels(23), "is-mid");
  assert.equal(gen2HpClassForPixels(10), "is-mid");
  assert.equal(gen2HpClassForPixels(9), "is-low");
});

test("renders gen 2 hud and textbox through the isolated asm renderer", () => {
  const hud = gen2Scene.renderHud({
    displayNameHtml: "AMPHAROS",
    hpClass: "is-high",
    hpTextHtml: "<div>120/120</div>",
    hpWidth: "100%",
    levelHtml: "50",
    showLevel: true,
    statusHtml: ""
  });
  assert.match(hud, /battle-scene-hud-gen2/);
  assert.match(hud, /battle-scene-level/);
  assert.match(hud, /Lv50/);
  assert.match(hud, /width:100%/);

  const dialog = gen2Scene.renderDialogPanel({ messageHtml: "AMPHAROS used THUNDER!" });
  assert.match(dialog, /battle-scene-dialog-panel/);
  assert.doesNotMatch(dialog, /battle-scene-turn/);
  assert.match(dialog, /AMPHAROS used THUNDER!/);
});

test("builds gen 2 battle animation timeline from asm script order", () => {
  const thunderbolt = animationMap.generations["2"].moves.thunderbolt;
  const timeline = gen2BattleAnimTimeline(thunderbolt);
  assert.equal(timeline.duration_frames, 144);
  assert.equal(timeline.duration_ms, 2400);
  assert.deepEqual(timeline.events.slice(0, 6).map((event) => event.type), [
    "gfx",
    "object",
    "wait",
    "bg_effect",
    "sound",
    "object"
  ]);
  assert.deepEqual(timeline.events.filter((event) => event.type === "wait").map((event) => event.duration_frames), [16, 64, 64]);
  assert.equal(timeline.events.find((event) => event.type === "bg_effect").frame, 16);
  assert.equal(timeline.events.find((event) => event.object_index === 1).frame, 16);
  assert.equal(timeline.events.at(-1).type, "ret");
  assert.equal(timeline.events.at(-1).frame, 144);
});

test("derives gen 2 background effect timing from asm timeline", () => {
  const thunderbolt = animationMap.generations["2"].moves.thunderbolt;
  const profile = effectVisualProfile(thunderbolt, "Thunderbolt");
  assert.equal(profile.backgroundAsset, "gen2/ui/battle_anims/lightning.png");
  assert.equal(profile.backgroundStartFrame, 16);
  assert.equal(profile.backgroundStartMs, 267);

  const acidArmor = effectVisualProfile(animationMap.generations["2"].moves.acidarmor, "Acid Armor");
  assert.equal(acidArmor.backgroundStartFrame, 0);
  assert.equal(acidArmor.backgroundEndFrame, 64);
  assert.equal(acidArmor.backgroundDurationMs, 1067);
  assert.deepEqual(acidArmor.backgroundEvents.map((event) => event.type), ["bg_effect", "incbgeffect"]);
});

test("resolves generation-specific battle text assets", () => {
  assert.deepEqual(battleTextAssetsForGeneration(1), {
    font: "gen1/ui/font/font.png",
    extra: "gen1/ui/font/font_extra.png",
    columns: 16,
    rows: 8,
    baseCode: 0x80
  });
  assert.deepEqual(battleTextAssetsForGeneration(2), {
    font: "gen2/ui/font/font.png",
    extra: "gen2/ui/font/font_extra.png",
    columns: 16,
    rows: 8,
    baseCode: 0x80
  });
  assert.deepEqual(battleTextAssetsForGeneration(3), {
    font: "gen3/ui/font/latin_short.png",
    columns: 32,
    rows: 64,
    baseCode: 0x00
  });
});

test("resolves effect background assets from original battle graphics", () => {
  assert.equal(
    battleEffectBackgroundAssetForMove(2, "Surf", { background: true, family: "water" }),
    "gen2/ui/battle_anims/water.png"
  );
  assert.equal(
    battleEffectBackgroundAssetForMove(3, "Thunderbolt", { background: true, family: "electric" }),
    "gen3/ui/battle_anims/backgrounds/thunder.png"
  );
  assert.equal(
    battleEffectBackgroundAssetForMove(1, "Tackle", { background: true, family: "impact" }),
    ""
  );
});

test("renders sprite text for gen 1 and gen 2 labels", () => {
  const html = renderBattleText("FIGHT", 1);
  assert.match(html, /battle-scene-text-sprite/);
  assert.match(html, /battle-scene-text-glyph/);
  assert.match(html, /generated\/battle-assets\/gen1\/ui\/font\/font\.png/);
  assert.match(renderBattleText("FIGHT", 3), /generated\/battle-assets\/gen3\/ui\/font\/latin_short\.png/);
  assert.doesNotMatch(renderBattleText("×3", 1), /battle-scene-text-glyph-missing/);
  assert.doesNotMatch(renderBattleText("×3", 2), /battle-scene-text-glyph-missing/);
  assert.doesNotMatch(renderBattleText("×3", 3), /battle-scene-text-glyph-missing/);
});

test("formats names for generation text surfaces", () => {
  assert.equal(humanizeMoveName("thunderbolt", 1), "THUNDERBOLT");
  assert.equal(humanizeMoveName("flame-wheel", 2), "FLAME WHEEL");
  assert.equal(humanizeMoveName("mud shot", 3), "Mud Shot");
});

test("parses switch battle logs", () => {
  const parsed = parseBattleLogLine("|switch|p1a: CHARIZARD|Charizard, L100|359/359");
  assert.deepEqual(parsed, {
    event: "switch",
    side: "p1",
    slot: "a",
    nickname: "CHARIZARD",
    species: "Charizard",
    level: 100,
    condition: "359/359"
  });
});

test("parses move, damage, miss, faint and win logs", () => {
  assert.deepEqual(parseBattleLogLine("|move|p2a: BLASTOISE|surf|p1a"), {
    event: "move",
    side: "p2",
    slot: "a",
    actor: "BLASTOISE",
    move: "surf",
    targetSide: "p1",
    target: "p1a"
  });
  assert.deepEqual(parseBattleLogLine("|-damage|p1a: CHARIZARD|120/359|[from] brn"), {
    event: "-damage",
    side: "p1",
    slot: "a",
    nickname: "CHARIZARD",
    condition: "120/359",
    source: "[from] brn"
  });
  assert.deepEqual(parseBattleLogLine("|-miss|p1a: CHARIZARD|p2a: BLASTOISE"), {
    event: "-miss",
    side: "p1",
    slot: "a",
    actor: "CHARIZARD",
    targetSide: "p2",
    target: "BLASTOISE"
  });
  assert.deepEqual(parseBattleLogLine("|faint|p1a: CHARIZARD"), {
    event: "faint",
    side: "p1",
    slot: "a",
    nickname: "CHARIZARD"
  });
  assert.deepEqual(parseBattleLogLine("|win|Mattia?"), {
    event: "win",
    winner: "Mattia?"
  });
});

test("parses battle idents and secondary battle text events", () => {
  assert.deepEqual(parseBattleIdent("p2a: BLASTOISE"), {
    side: "p2",
    slot: "a",
    nickname: "BLASTOISE"
  });
  assert.deepEqual(parseBattleLogLine("|-supereffective|p1a: CHARIZARD"), {
    event: "-supereffective",
    side: "p1",
    slot: "a",
    nickname: "CHARIZARD",
    arg1: "",
    arg2: "",
    raw: "|-supereffective|p1a: CHARIZARD"
  });
  assert.deepEqual(parseBattleLogLine("|cant|p1a: CHARIZARD|slp"), {
    event: "cant",
    side: "p1",
    slot: "a",
    nickname: "CHARIZARD",
    reason: "slp",
    move: ""
  });
});

test("parses hp and faint conditions", () => {
  assert.deepEqual(parseCondition("42/120 PAR"), {
    currentHp: 42,
    maxHp: 120,
    status: "par"
  });
  assert.deepEqual(parseCondition("0 fnt", { maxHp: 120 }), {
    currentHp: 0,
    maxHp: 120,
    status: "fnt"
  });
});

test("builds visual action groups from battle requests", () => {
  const groups = actionGroupsFromRequest({
    active: [{
      moves: [
        { move: "Surf", pp: 12, maxpp: 15, type: "Water" },
        { move: "Fly", pp: 0, maxpp: 15, type: "Flying" },
        { move: "Slash", pp: 20, maxpp: 20, type: "Normal", disabled: true }
      ]
    }],
    side: {
      pokemon: [
        { ident: "p1a: LAPRAS", details: "Lapras, L50", condition: "180/180", active: true },
        { ident: "p1b: RAICHU", details: "Raichu, L50", condition: "120/120" },
        { ident: "p1c: PIDGEOT", details: "Pidgeot, L50", condition: "0 fnt" }
      ]
    }
  });
  assert.equal(groups.moves.length, 3);
  assert.equal(groups.moves[0].action, "move 1");
  assert.equal(groups.moves[1].disabled, true);
  assert.equal(groups.moves[2].disabled, true);
  assert.equal(groups.switches[1].action, "switch 2");
  assert.equal(groups.switches[1].disabled, false);
  assert.equal(groups.switches[2].disabled, true);
});

test("derives richer browser effect profiles from animation metadata", () => {
  const profile = effectVisualProfile({
    family: "electric",
    command_count: 6,
    commands: ["anim_2gfx", "anim_bgeffect", "anim_obj", "anim_wait"],
    script: [
      { command: "anim_obj", args: ["BATTLE_ANIM_OBJ_THUNDERBOLT_BALL"] },
      { command: "anim_bgeffect", args: ["ANIM_BG_FLASH_INVERTED"] }
    ],
    assets: [
      { role: "gen2_anim_gfx", tag: "BATTLE_ANIM_GFX_LIGHTNING", path: "gen2/ui/battle_anims/lightning.png" }
    ],
    logic: {
      objects: [{ object: "BATTLE_ANIM_OBJ_THUNDERBOLT_BALL", gfx: "BATTLE_ANIM_GFX_LIGHTNING" }],
      total_wait_frames: 12
    }
  }, "Thunderbolt");
  assert.equal(profile.family, "electric");
  assert.equal(profile.flash, true);
  assert.equal(profile.background, true);
  assert.ok(profile.duration > 440);
  assert.ok(profile.objectCount >= 1);
  assert.deepEqual(profile.assets.map((asset) => asset.path), ["gen2/ui/battle_anims/lightning.png"]);
});

test("normalizes sprite sheet frame metadata for browser playback", () => {
  const plan = framePlanForRecord({
    dimensions: { width: 32, height: 160 },
    frame: { width: 32, height: 32, columns: 1, rows: 5, count: 5, frame_ms: 65, layout: "vertical_strip" }
  });
  assert.deepEqual(plan, {
    width: 32,
    height: 32,
    columns: 1,
    rows: 5,
    count: 5,
    frameMs: 65,
    layout: "vertical_strip"
  });
  assert.equal(framePlanForRecord({ dimensions: { width: 64, height: 64 } }).count, 1);
});

test("infers gen 2 front pokemon sprite sheets from vertical frame images", () => {
  const plan = framePlanForRecord({
    path: "gen2/pokemon/ampharos/front.png",
    dimensions: { width: 56, height: 392 },
    frame: { width: 56, height: 392, columns: 1, rows: 1, count: 1, frame_ms: 160, layout: "static" }
  });
  assert.deepEqual(plan, {
    width: 56,
    height: 56,
    columns: 1,
    rows: 7,
    count: 7,
    frameMs: 160,
    layout: "pokemon_front"
  });
  assert.deepEqual(pokemonSpriteFramePlaybackForRecord({
    path: "gen2/pokemon/ampharos/front.png",
    dimensions: { width: 56, height: 392 },
    frame: { width: 56, height: 392, columns: 1, rows: 1, count: 1, frame_ms: 160, layout: "static" }
  }), {
    mode: "once",
    sequence: [0, 1, 2, 3, 4, 5, 6, 0],
    frameMs: 160
  });
});

test("uses extracted pokecrystal front animation frame order for gen 2 pokemon", () => {
  const playback = pokemonSpriteFramePlaybackForRecord({
    path: "gen2/pokemon/ampharos/front.png",
    dimensions: { width: 56, height: 392 },
    frame: { width: 56, height: 392, columns: 1, rows: 1, count: 1, frame_ms: 160, layout: "static" }
  }, {
    species: "Ampharos",
    animations: gen2FrontAnimSequences
  });
  assert.deepEqual(playback.sequence, [1, 2, 2, 3, 2, 3, 2, 3, 2, 3, 2, 3, 2, 3, 2, 3, 1, 4, 0]);
  assert.deepEqual(playback.durations.slice(0, 4), [167, 133, 33, 33]);
  assert.equal(playback.frameMs, 167);
  assert.equal(playback.source, "gfx/pokemon/ampharos/anim.asm");
});

test("uses extracted pokecrystal idle animation frame order for gen 2 pokemon", () => {
  const playback = pokemonSpriteFramePlaybackForRecord({
    path: "gen2/pokemon/ampharos/front.png",
    dimensions: { width: 56, height: 392 },
    frame: { width: 56, height: 392, columns: 1, rows: 1, count: 1, frame_ms: 160, layout: "static" }
  }, {
    species: "Ampharos",
    animations: gen2FrontAnimSequences,
    animationKind: "idle"
  });
  assert.deepEqual(playback.sequence, [4, 5, 6, 5, 6]);
  assert.deepEqual(playback.durations, [167, 100, 100, 100, 100]);
  assert.equal(playback.mode, "loop");
  assert.equal(playback.source, "gfx/pokemon/ampharos/anim_idle.asm");
});

test("uses finite playback for pokemon front sprite frames", () => {
  const playback = pokemonSpriteFramePlaybackForRecord({
    dimensions: { width: 64, height: 128 },
    frame: { width: 64, height: 64, columns: 1, rows: 2, count: 2, frame_ms: 150, layout: "pokemon_front" }
  });
  assert.deepEqual(playback, {
    mode: "once",
    sequence: [0, 1, 0],
    frameMs: 150
  });
  assert.equal(pokemonSpriteFramePlaybackForRecord({ dimensions: { width: 64, height: 64 } }), null);
});

test("uses extracted pokeemerald front animation timing for gen 3 pokemon", () => {
  const playback = pokemonSpriteFramePlaybackForRecord({
    path: "gen3/pokemon/pikachu/anim_front.png",
    dimensions: { width: 64, height: 128 },
    frame: { width: 64, height: 64, columns: 1, rows: 2, count: 2, frame_ms: 150, layout: "pokemon_front" }
  }, {
    species: "Pikachu",
    animations: gen3FrontAnimSequences
  });
  assert.deepEqual(playback.sequence, [0, 1, 0, 1, 0]);
  assert.deepEqual(playback.durations, [250, 333, 250, 333, 250]);
  assert.equal(playback.motion, "ANIM_FLASH_YELLOW");
  assert.equal(playback.source, "sAnim_Pikachu_1");
});

test("maps pokeemerald pokemon motion ids to browser motion profiles", () => {
  assert.deepEqual(pokemonSpriteMotionProfile("ANIM_H_SHAKE").steps.map((step) => step.transform), [
    "translateX(0)",
    "translateX(-3px)",
    "translateX(3px)",
    "translateX(-2px)",
    "translateX(0)"
  ]);
  assert.match(pokemonSpriteMotionProfile("ANIM_FLASH_YELLOW").steps[1].filter, /brightness/);
  assert.match(pokemonSpriteMotionProfile("ANIM_SWING_CONCAVE").steps[1].transform, /rotate/);
  assert.match(pokemonSpriteMotionProfile("ANIM_CONVEX_DOUBLE_ARC").steps[2].transform, /translate/);
  assert.match(pokemonSpriteMotionProfile("ANIM_TWIST").steps[1].transform, /skewX/);
  assert.match(pokemonSpriteMotionProfile("ANIM_SPIN").steps[2].transform, /180deg/);
  assert.match(pokemonSpriteMotionProfile("ANIM_FRONT_FLIP").steps[2].transform, /-1/);
  assert.match(pokemonSpriteMotionProfile("ANIM_FIGURE_8").steps[4].transform, /translate/);
  assert.match(pokemonSpriteMotionProfile("ANIM_CIRCLE_C_CLOCKWISE_SLOW").steps[2].transform, /translate/);
  assert.match(pokemonSpriteMotionProfile("ANIM_H_SPRING").steps[2].transform, /scale/);
  assert.equal(pokemonSpriteMotionProfile("ANIM_UNKNOWN"), null);
});

test("covers every front pokemon motion extracted from pokeemerald", () => {
  const motions = new Set(Object.values(gen3FrontAnimSequences.species).map((entry) => entry.motion));
  const missing = [...motions].filter((motion) => !pokemonSpriteMotionProfile(motion));
  assert.deepEqual(missing, []);
});

test("computes OAM tile sheet positions and composed tile styles", () => {
  assert.deepEqual(tileSheetPosition(5, 4, 4), { x: 33.33333333333333, y: 33.33333333333333 });
  const asset = {
    role: "gen2_anim_gfx",
    dimensions: { width: 32, height: 32 },
    frame: { width: 8, height: 8, columns: 4, rows: 4, count: 16 }
  };
  const composite = { bounds: { x: -8, y: -8, width: 16, height: 16 }, tile_size: 8 };
  const scale = compositeScale(asset, composite);
  const style = tileStyle(asset, composite, { tile: 5, x: 0, y: 8, xflip: true, yflip: false }, "/generated/battle-assets/gen2/ui/battle_anims/hit.png", scale);
  assert.equal(scale, 2.125);
  assert.match(style, /left:17px/);
  assert.match(style, /top:34px/);
  assert.match(style, /background-size:400% 400%/);
  assert.match(style, /background-position:33\.33333333333333% 33\.33333333333333%/);
  assert.match(style, /transform:scaleX\(-1\)/);
});

test("treats gen 2 battle animation graphics as cropped tile sheets", () => {
  const asset = {
    role: "gen2_anim_gfx",
    dimensions: { width: 16, height: 104 },
    frame: { width: 8, height: 8, columns: 2, rows: 13, count: 26, layout: "gb_tile_sheet" }
  };
  assert.equal(isGen2TileSheetAsset(asset), true);
  assert.equal(isGen2TileSheetAsset({ path: "gen2/ui/battle_anims/water.png", frame: { layout: "gb_tile_sheet" } }), true);
  assert.equal(isGen2TileSheetAsset({ path: "gen2/ui/battle/hp_bar.png", frame: { layout: "static" } }), false);
  assert.equal(isGen2TileSheetAsset({ role: "gen3_anim_sprite", frame: { layout: "horizontal_strip" } }), false);

  const style = tileFrameStyle(asset, "/generated/battle-assets/gen2/ui/battle_anims/hit.png", 5, 4);
  assert.match(style, /width:32px/);
  assert.match(style, /height:32px/);
  assert.match(style, /background-size:200% 1300%/);
  assert.match(style, /background-position:100% 16\.666666666666664%/);
});

test("uses original gen 2 frameset durations for OAM composite playback", () => {
  assert.deepEqual(compositeFrameDurations({
    frame_ms: 70,
    frames: [
      { duration_frames: 2 },
      { duration_frames: 8 },
      { duration_frames: 0 }
    ]
  }), [33, 133, 70]);
});

test("builds gen 2 object effect assets from real anim_obj instances", () => {
  const quickAttack = animationMap.generations["2"].moves.quickattack;
  const assets = effectAssetsForProfile(quickAttack, quickAttack.assets);
  assert.equal(assets.length, quickAttack.logic.objects.length);
  assert.equal(assets[0].object, "BATTLE_ANIM_OBJ_SPEED_LINE");
  assert.equal(assets[0].callback, "BATTLE_ANIM_FUNC_SPEED_LINE");
  assert.deepEqual(assets[0].composites[0].args, ["24", "88", "$2"]);
  assert.equal(assets[0].composites[0].frames.length, 1);
  assert.equal(assets.at(-1).object, "BATTLE_ANIM_OBJ_HIT_YFIX");
});

test("applies gen 2 asm object timeline timing to effect assets", () => {
  const thunderbolt = animationMap.generations["2"].moves.thunderbolt;
  const assets = effectAssetsForProfile(thunderbolt, thunderbolt.assets);
  assert.equal(assets.length, thunderbolt.logic.objects.length);
  assert.equal(assets[0].object, "BATTLE_ANIM_OBJ_THUNDERBOLT_BALL");
  assert.equal(assets[0].startFrame, 0);
  assert.equal(assets[0].startMs, 0);
  assert.equal(assets[1].object, "BATTLE_ANIM_OBJ_SPARKS_CIRCLE_BIG");
  assert.equal(assets[1].startFrame, 16);
  assert.equal(assets[1].startMs, 267);
});

test("uses gen 2 anim_obj asm coordinates for effect asset positions", () => {
  const thunderbolt = animationMap.generations["2"].moves.thunderbolt;
  const assets = effectAssetsForProfile(thunderbolt, thunderbolt.assets);
  assert.equal(assets[0].position.x, 136);
  assert.equal(assets[0].position.y, 56);
  assert.equal(assets[0].position.leftPercent, 85);
  assert.equal(assets[0].position.topPercent, 58.333333333333336);

  const bubblebeam = animationMap.generations["2"].moves.bubblebeam;
  const bubbleAssets = effectAssetsForProfile(bubblebeam, bubblebeam.assets);
  assert.equal(bubbleAssets[0].position.x, 64);
  assert.equal(bubbleAssets[0].position.y, 92);
  assert.equal(bubbleAssets[0].position.leftPercent, 40);
  assert.equal(bubbleAssets[0].position.topPercent, 95.83333333333334);
});

test("normalizes gen 2 object state timeline commands from asm ids", () => {
  const emberTimeline = gen2BattleAnimTimeline(animationMap.generations["2"].moves.ember);
  const emberIncEvents = emberTimeline.events.filter((event) => event.type === "incobj");
  assert.deepEqual(emberIncEvents.map((event) => event.object_id), [1, 2, 3]);
  assert.deepEqual(emberIncEvents.map((event) => event.target_object_index), [0, 1, 2]);
  assert.deepEqual(emberIncEvents.map((event) => event.frame), [24, 24, 24]);

  const jumpKickTimeline = gen2BattleAnimTimeline(animationMap.generations["2"].moves.jumpkick);
  const setEvents = jumpKickTimeline.events.filter((event) => event.type === "setobj");
  assert.deepEqual(setEvents.map((event) => event.object_id), [1, 2]);
  assert.deepEqual(setEvents.map((event) => event.target_object_index), [0, 1]);
  assert.deepEqual(setEvents.map((event) => event.state), [2, 2]);
});

test("attaches gen 2 object state events to effect assets", () => {
  const ember = animationMap.generations["2"].moves.ember;
  const assets = effectAssetsForProfile(ember, ember.assets);
  assert.equal(assets.length, ember.logic.objects.length);
  assert.deepEqual(assets.slice(0, 3).map((asset) => asset.stateEvents[0].type), ["incobj", "incobj", "incobj"]);
  assert.deepEqual(assets.slice(0, 3).map((asset) => asset.stateEvents[0].frame), [24, 24, 24]);
  assert.deepEqual(assets.slice(0, 3).map((asset) => asset.stateEvents[0].objectId), [1, 2, 3]);
  assert.equal(assets[3].stateEvents.length, 0);
});

test("applies gen 2 anim_clearobjs timing to effect asset lifetimes", () => {
  const bubblebeam = animationMap.generations["2"].moves.bubblebeam;
  const assets = effectAssetsForProfile(bubblebeam, bubblebeam.assets);
  assert.equal(assets.length, 3);
  assert.deepEqual(assets.map((asset) => asset.startFrame), [0, 6, 12]);
  assert.deepEqual(assets.map((asset) => asset.endFrame), [84, 84, 84]);
  assert.deepEqual(assets.map((asset) => asset.durationMs), [1400, 1300, 1200]);
});

test("maps gen 2 battle animation callbacks to step-based motion profiles", () => {
  const circle = gen2BattleAnimFunctionProfile("BATTLE_ANIM_FUNC_MOVE_IN_CIRCLE", 0x82);
  assert.equal(circle.steps.length, 9);
  assert.match(circle.steps[0].transform, /translate\(-2px, 0px\)/);
  assert.match(circle.steps[2].transform, /translate\(0px, -?2px\)|translate\(0px, 2px\)/);

  const speedLine = gen2BattleAnimFunctionProfile("BATTLE_ANIM_FUNC_SPEED_LINE", 0x80);
  assert.match(speedLine.steps[2].transform, /translateX\(-4px\)/);
  assert.equal(speedLine.steps.at(-1).opacity, "0");

  const ember = gen2BattleAnimFunctionProfile("BATTLE_ANIM_FUNC_EMBER", 0x12);
  assert.match(ember.steps[2].transform, /translate\(16px, -12px\)/);

  const fireBlast = gen2BattleAnimFunctionProfile("BATTLE_ANIM_FUNC_FIRE_BLAST", 4);
  assert.match(fireBlast.steps[2].transform, /translate\(-8px, 8px\)/);
});

test("covers all non-null gen 2 object callbacks present in animation-map", () => {
  const missing = [];
  for (const profile of Object.values(animationMap.generations["2"].moves)) {
    for (const object of profile.logic?.objects || []) {
      if (object.callback === "BATTLE_ANIM_FUNC_NULL") continue;
      const param = String(object.args?.[2] || "").startsWith("$")
        ? Number.parseInt(String(object.args[2]).slice(1), 16)
        : Number(object.args?.[2] || 0);
      if (!gen2BattleAnimFunctionProfile(object.callback, param)) missing.push(`${profile.label}:${object.callback}:${object.args?.[2] || "0"}`);
    }
  }
  assert.deepEqual(missing, []);
});

test("loads real pokecrystal OAM composite metadata for gen 2 moves", () => {
  const thunderbolt = animationMap.generations["2"].moves.thunderbolt;
  const lightning = thunderbolt.assets.find((asset) => asset.tag === "BATTLE_ANIM_GFX_LIGHTNING");
  assert.equal(lightning.frame.layout, "gb_tile_sheet");
  assert.equal(isGen2TileSheetAsset(lightning), true);
  assert.ok(lightning.composites.length > 0);
  assert.deepEqual(lightning.composites[0].frames.slice(0, 3).map((frame) => frame.duration_frames), [2, 2, 2]);
  assert.ok(lightning.composites[0].frames[0].tiles.length > 0);
  assert.ok(lightning.composites[0].frames[0].tiles.every((tile) => Number.isInteger(tile.tile)));
});
