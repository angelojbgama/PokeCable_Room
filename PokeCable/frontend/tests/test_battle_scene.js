const test = require("node:test");
const assert = require("node:assert/strict");

const {
  actionGroupsFromRequest,
  animationFamilyFromMove,
  battleProfileForGeneration,
  compositeScale,
  effectVisualProfile,
  framePlanForRecord,
  humanizeMoveName,
  normalizeAssetSpeciesKey,
  normalizeMoveKey,
  normalizeSpeciesKey,
  parseBattleIdent,
  parseBattleLogLine,
  parseCondition,
  tileSheetPosition,
  tileStyle
} = require("../battle-scene.js");

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
