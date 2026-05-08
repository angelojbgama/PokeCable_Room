(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./battle-scene-gen2.js"));
  } else {
    root.POKECABLE_BATTLE_SCENE = factory(root.POKECABLE_BATTLE_SCENE_GEN2);
  }
})(typeof globalThis !== "undefined" ? globalThis : window, function (gen2BattleScene) {
  const MANIFEST_URL = "/generated/battle-assets/manifest.json";
  const ANIMATION_MAP_URL = "/generated/battle-assets/animation-map.json";
  const POKEMON_FRAME_ANIMATION_URLS = {
    2: "/generated/battle-assets/gen2/pokemon-front-anim-sequences.json",
    3: "/generated/battle-assets/gen3/pokemon-front-anim-sequences.json"
  };
  const SIDE_LABELS = { p1: "Você", p2: "Oponente" };

  const STATUS_LABELS = {
    ok: "",
    brn: "BRN",
    frz: "FRZ",
    par: "PAR",
    psn: "PSN",
    slp: "SLP",
    tox: "TOX",
    fnt: "FNT"
  };

  if (!gen2BattleScene) throw new Error("POKECABLE_BATTLE_SCENE_GEN2 must be loaded before battle-scene.js");

  const BATTLE_PROFILES = {
    1: {
      generation: 1,
      baseWidth: 160,
      baseHeight: 144,
      title: "GEN 1 LINK BATTLE",
      commandQuestion: "What will {pokemon} do?",
      defaultMessage: "Waiting for battle.",
      waitingMessage: "Waiting for the other player.",
      itemBlockedMessage: "This can't be used in a link battle!",
      commandLabels: [
        { key: "fight", label: "FIGHT" },
        { key: "party", label: "PKMN" },
        { key: "bag", label: "ITEM" },
        { key: "run", label: "RUN" }
      ],
      bagTitle: "ITEM",
      partyTitle: "POKéMON",
      moveTypeLabel: "TYPE",
      ppLabel: "PP",
      cancelLabel: "CANCEL",
      backLabel: "CANCEL",
      enemyShowsHpText: false,
      uppercaseText: true,
      pockets: [{ key: "all", label: "ITEMS" }]
    },
    2: gen2BattleScene.profile,
    3: {
      generation: 3,
      baseWidth: 240,
      baseHeight: 160,
      title: "GEN 3 LINK BATTLE",
      commandQuestion: "What will {pokemon} do?",
      defaultMessage: "Waiting for battle.",
      waitingMessage: "Waiting for the other player.",
      itemBlockedMessage: "It won't have any effect.",
      commandLabels: [
        { key: "fight", label: "FIGHT" },
        { key: "bag", label: "BAG" },
        { key: "party", label: "POKéMON" },
        { key: "run", label: "RUN" }
      ],
      bagTitle: "BAG",
      partyTitle: "POKéMON",
      moveTypeLabel: "TYPE",
      ppLabel: "PP",
      cancelLabel: "CANCEL",
      backLabel: "BACK",
      enemyShowsHpText: false,
      uppercaseText: false,
      pockets: [
        { key: "items", label: "ITEMS" },
        { key: "balls", label: "POKé BALLS" },
        { key: "tmhm", label: "TMs & HMs" },
        { key: "berries", label: "BERRIES" },
        { key: "key_items", label: "KEY ITEMS" }
      ]
    }
  };

  const BATTLE_UI_ASSETS = {
    1: {
      balls: "gen1/ui/battle/balls.png",
      hudEnemy: "gen1/ui/battle/battle_hud_1.png",
      hudPlayer: "gen1/ui/battle/battle_hud_2.png",
      dialog: "gen1/ui/battle/battle_hud_3.png"
    },
    2: gen2BattleScene.uiAssets,
    3: {
      singles: {
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
      },
      doubles: {
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
      }
    }
  };

  const BATTLE_TEXT_ASSETS = {
    1: {
      font: "gen1/ui/font/font.png",
      extra: "gen1/ui/font/font_extra.png",
      columns: 16,
      rows: 8,
      baseCode: 0x80
    },
    2: {
      font: "gen2/ui/font/font.png",
      extra: "gen2/ui/font/font_extra.png",
      columns: 16,
      rows: 8,
      baseCode: 0x80
    },
    3: {
      font: "gen3/ui/font/latin_short.png",
      columns: 32,
      rows: 64,
      baseCode: 0x00
    },
  };

  function battleProfileForGeneration(generation) {
    return BATTLE_PROFILES[Number(generation)] || BATTLE_PROFILES[1];
  }

  function gen2BattleLayout() {
    return gen2BattleScene.layoutCopy();
  }

  function gen2BattleCssVariables() {
    return gen2BattleScene.cssVariables();
  }

  function gen2HpBarPixels(currentHp, maxHp) {
    return gen2BattleScene.hpBarPixels(currentHp, maxHp);
  }

  function gen2HpClassForPixels(pixels) {
    return gen2BattleScene.hpClassForPixels(pixels);
  }

  function gen2BattleAnimTimeline(profile) {
    return gen2BattleScene.battleAnimTimeline(profile);
  }

  function battleUiAssetsForGeneration(generation, battleFormat = "singles") {
    const gen = Number(generation) || 1;
    const profile = BATTLE_UI_ASSETS[gen] || BATTLE_UI_ASSETS[1];
    if (gen === 3) {
      return battleFormat === "doubles" ? profile.doubles : profile.singles;
    }
    return profile;
  }

  function battleUiAssetUrl(path) {
    return path ? `/generated/battle-assets/${path}` : "";
  }

  function battleTextAssetsForGeneration(generation) {
    return BATTLE_TEXT_ASSETS[Number(generation)] || null;
  }

  function battleEffectBackgroundAssetForMove(generation, moveName, visual = {}) {
    const gen = Number(generation) || 1;
    if (!visual.background) return "";
    const key = normalizeMoveKey(moveName);
    const family = String(visual.family || animationFamilyFromMove(moveName) || "").toLowerCase();
    const matches = (needles) => needles.some((needle) => key.includes(needle));
    if (gen === 2) {
      if (family === "water" || matches(["water", "surf", "bubble", "hydro", "whirlpool", "rain"])) return "gen2/ui/battle_anims/water.png";
      if (family === "ground" || matches(["sand", "earthquake", "dig", "mud", "magnitude", "fissure", "rock", "bone"])) return "gen2/ui/battle_anims/sand.png";
      if (family === "electric" || matches(["thunder", "spark", "shock", "volt", "zap", "electric"])) return "gen2/ui/battle_anims/lightning.png";
      if (family === "ice" || matches(["ice", "blizzard", "freeze", "aurora", "hail"])) return "gen2/ui/battle_anims/ice.png";
      if (family === "psychic" || matches(["psy", "mind", "dream", "hypnosis", "calm", "teleport"])) return "gen2/ui/battle_anims/psychic.png";
      if (family === "explosion" || matches(["explosion", "selfdestruct", "boom", "blast"])) return "gen2/ui/battle_anims/explosion.png";
      return "gen2/ui/battle_anims/shine.png";
    }
    if (gen === 3) {
      if (family === "water" || matches(["water", "surf", "bubble", "hydro", "whirlpool", "rain"])) return "gen3/ui/battle_anims/backgrounds/water.png";
      if (family === "ground" || matches(["sand", "earthquake", "dig", "mud", "magnitude", "fissure", "drill"])) return "gen3/ui/battle_anims/backgrounds/sandstorm_brew.png";
      if (family === "electric" || matches(["thunder", "spark", "shock", "volt", "zap", "electric"])) return "gen3/ui/battle_anims/backgrounds/thunder.png";
      if (family === "ice" || matches(["ice", "blizzard", "freeze", "aurora", "hail"])) return "gen3/ui/battle_anims/backgrounds/ice.png";
      if (family === "psychic" || matches(["psy", "mind", "dream", "hypnosis", "calm", "teleport"])) return "gen3/ui/battle_anims/backgrounds/psychic.png";
      if (family === "wind" || matches(["fly", "air", "sky", "gust", "wing"])) return "gen3/ui/battle_anims/backgrounds/in_air.png";
      if (family === "ghost" || matches(["ghost", "curse", "spirit", "shadow"])) return "gen3/ui/battle_anims/backgrounds/ghost.png";
      if (family === "explosion" || matches(["explosion", "selfdestruct", "boom", "blast", "impact"])) return "gen3/ui/battle_anims/backgrounds/impact.png";
      if (family === "dark" || matches(["dark", "night", "scary", "fear"])) return "gen3/ui/battle_anims/backgrounds/dark.png";
      return "gen3/ui/battle_anims/backgrounds/impact.png";
    }
    return "";
  }

  function normalizeSpeciesKey(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/♀/g, "f")
      .replace(/♂/g, "m")
      .replace(/[^a-z0-9]+/g, "");
  }

  function normalizeAssetSpeciesKey(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/♀/g, "_f")
      .replace(/♂/g, "_m")
      .replace(/'/g, "")
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");
  }

  function speciesKeyCandidates(value) {
    const key = normalizeSpeciesKey(value);
    const candidates = [key, normalizeAssetSpeciesKey(value)];
    if (key === "nidoranf") candidates.push("nidoran_f");
    if (key === "nidoranm") candidates.push("nidoran_m");
    if (key === "mrmime") candidates.push("mr_mime");
    if (key === "farfetchd") candidates.push("farfetchd", "farfetch_d");
    return [...new Set(candidates)];
  }

  function normalizeMoveKey(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "");
  }

  function parseBattleIdent(value) {
    const ident = String(value || "");
    const slotMatch = ident.match(/^(p[12])([a-z]?)/i);
    const nickname = ident.includes(":") ? ident.split(":").slice(1).join(":").trim() : ident.trim();
    return {
      side: slotMatch ? slotMatch[1].toLowerCase() : ident.slice(0, 2).toLowerCase(),
      slot: slotMatch ? slotMatch[2].toLowerCase() : "",
      nickname
    };
  }

  function parseCondition(condition, previous = {}) {
    const text = String(condition || "").trim();
    const hpMatch = text.match(/(\d+)\/(\d+)/);
    if (hpMatch) {
      return {
        currentHp: Number(hpMatch[1]),
        maxHp: Number(hpMatch[2]),
        status: normalizeStatus(text.replace(hpMatch[0], "").trim() || previous.status || "ok")
      };
    }
    if (/fnt/i.test(text)) {
      return {
        currentHp: 0,
        maxHp: previous.maxHp || 0,
        status: "fnt"
      };
    }
    return {
      currentHp: previous.currentHp || 0,
      maxHp: previous.maxHp || 0,
      status: normalizeStatus(text || previous.status || "ok")
    };
  }

  function parseBattleLogLine(line) {
    const raw = String(line || "");
    const parts = raw.split("|");
    const event = parts[1] || "";
    if (!event) return null;

    if (event === "switch" || event === "drag") {
      const ident = parseBattleIdent(parts[2] || "");
      const details = parts[3] || "";
      const condition = parts[4] || "";
      const species = details.split(",")[0].trim();
      const levelMatch = details.match(/L(\d+)/i);
      return {
        event,
        side: ident.side,
        slot: ident.slot,
        nickname: ident.nickname,
        species,
        level: levelMatch ? Number(levelMatch[1]) : null,
        condition
      };
    }

    if (event === "move") {
      const actor = parseBattleIdent(parts[2] || "");
      const target = parseBattleIdent(parts[4] || "");
      return {
        event,
        side: actor.side,
        slot: actor.slot,
        actor: actor.nickname,
        move: parts[3] || "",
        targetSide: target.side,
        target: target.nickname
      };
    }

    if (["damage", "-damage", "heal", "-heal"].includes(event)) {
      const ident = parseBattleIdent(parts[2] || "");
      return {
        event,
        side: ident.side,
        slot: ident.slot,
        nickname: ident.nickname,
        condition: parts[3] || "",
        source: parts[4] || ""
      };
    }

    if (event === "faint") {
      const ident = parseBattleIdent(parts[2] || "");
      return {
        event,
        side: ident.side,
        slot: ident.slot,
        nickname: ident.nickname
      };
    }

    if (event === "-miss") {
      const actor = parseBattleIdent(parts[2] || "");
      const target = parseBattleIdent(parts[3] || "");
      return {
        event,
        side: actor.side,
        slot: actor.slot,
        actor: actor.nickname,
        targetSide: target.side,
        target: target.nickname
      };
    }

    if (event === "-status" || event === "status" || event === "-curestatus") {
      const ident = parseBattleIdent(parts[2] || "");
      return {
        event,
        side: ident.side,
        slot: ident.slot,
        nickname: ident.nickname,
        status: parts[3] || "",
        source: parts[4] || ""
      };
    }

    if (event === "cant") {
      const ident = parseBattleIdent(parts[2] || "");
      return {
        event,
        side: ident.side,
        slot: ident.slot,
        nickname: ident.nickname,
        reason: parts[3] || "",
        move: parts[4] || ""
      };
    }

    if (event === "-boost" || event === "-unboost") {
      const ident = parseBattleIdent(parts[2] || "");
      return {
        event,
        side: ident.side,
        slot: ident.slot,
        nickname: ident.nickname,
        stat: parts[3] || "",
        amount: Number(parts[4] || 0)
      };
    }

    if (["-crit", "-supereffective", "-resisted", "-immune", "-fail", "-blocked", "-activate", "-start", "-end", "-item", "-enditem"].includes(event)) {
      const ident = parseBattleIdent(parts[2] || "");
      return {
        event,
        side: ident.side,
        slot: ident.slot,
        nickname: ident.nickname,
        arg1: parts[3] || "",
        arg2: parts[4] || "",
        raw
      };
    }

    if (event === "win") {
      return { event, winner: parts[2] || "" };
    }

    if (event === "turn") {
      return { event, turn: Number(parts[2] || 0) };
    }

    if (event === "request") {
      return { event, message: parts.slice(2).join("|") };
    }

    return { event, raw };
  }

  function hpPercent(pokemon) {
    if (!pokemon || !pokemon.maxHp) return 0;
    return Math.max(0, Math.min(100, Math.round((pokemon.currentHp / pokemon.maxHp) * 100)));
  }

  function hpClass(percent) {
    if (percent <= 20) return "is-low";
    if (percent <= 50) return "is-mid";
    return "is-high";
  }

  function normalizeStatus(status) {
    const value = String(status || "ok").toLowerCase();
    if (!value || value === "healthy") return "ok";
    if (value.includes("fnt")) return "fnt";
    if (value.includes("tox")) return "tox";
    if (value.includes("psn")) return "psn";
    if (value.includes("brn")) return "brn";
    if (value.includes("par")) return "par";
    if (value.includes("frz")) return "frz";
    if (value.includes("slp")) return "slp";
    return value;
  }

  function statusLabel(status) {
    return STATUS_LABELS[normalizeStatus(status)] || String(status || "").toUpperCase();
  }

  function animationFamilyFromMove(moveName) {
    const key = normalizeMoveKey(moveName);
    const checks = [
      ["electric", ["thunder", "spark", "zap", "shock", "volt"]],
      ["fire", ["fire", "flame", "ember", "burn", "blast", "eruption"]],
      ["water", ["water", "surf", "bubble", "hydro", "whirlpool", "rain"]],
      ["ice", ["ice", "blizzard", "snow", "freeze", "aurora"]],
      ["grass", ["leaf", "vine", "petal", "seed", "spore", "powder", "razorleaf"]],
      ["psychic", ["psy", "confusion", "hypnosis", "dream", "calm", "teleport"]],
      ["poison", ["poison", "toxic", "sludge", "smog", "acid", "gas"]],
      ["ground", ["earthquake", "dig", "mud", "sand", "fissure", "magnitude"]],
      ["rock", ["rock", "rollout", "bone", "boulder", "tomb"]],
      ["wind", ["gust", "fly", "wing", "aero", "sky", "twister"]],
      ["explosion", ["explosion", "selfdestruct", "blastburn"]],
      ["drain", ["drain", "absorb", "leech"]],
      ["status", ["recover", "reflect", "screen", "protect", "detect", "dance", "harden", "growl", "tailwhip"]]
    ];
    for (const [family, needles] of checks) {
      if (needles.some((needle) => key.includes(needle))) return family;
    }
    return "impact";
  }

  function effectVisualProfile(profile, moveName) {
    const commands = profile?.commands || [];
    const script = Array.isArray(profile?.script) ? profile.script : [];
    const scriptText = script.map((step) => `${step.command || ""} ${(step.args || []).join(" ")} ${step.raw || ""}`).join(" ");
    const commandText = `${commands.join(" ")} ${scriptText}`.toLowerCase();
    const baseAssets = Array.isArray(profile?.assets) ? profile.assets.filter((asset) => asset?.path) : [];
    const logic = profile?.logic || {};
    const isGen2Profile = isGen2BattleAnimationProfile(profile);
    const effectGeneration = Number(profile?.generation || profile?.logic?.generation || 0) || (isGen2Profile ? 2 : 0);
    const assets = effectAssetsForProfile(profile, baseAssets);
    const timelineProfile = isGen2Profile ? gen2BattleAnimTimeline(profile) : null;
    const timedTimeline = timelineProfile && Number(timelineProfile.duration_frames || 0) > 0 ? timelineProfile : null;
    const waitFrames = timedTimeline ? timedTimeline.duration_frames : Number(logic.total_wait_frames || logic.total_delay_frames || 0);
    const objectSignals = [
      assets.length,
      Array.isArray(logic.objects) ? logic.objects.length : 0,
      Array.isArray(logic.sprites) ? logic.sprites.length : 0,
      Number(profile?.command_count || commands.length || 1)
    ];
    const family = profile?.family || animationFamilyFromMove(moveName);
    const backgroundStartEvent = timelineProfile?.events?.find((event) => event?.type === "bg_effect") || null;
    const backgroundEndEvent = timelineProfile?.events?.find((event) => (
      event?.type === "incbgeffect"
      && backgroundStartEvent
      && event.frame >= backgroundStartEvent.frame
      && event.effect === backgroundStartEvent.effect
    )) || null;
    const backgroundStartMs = Number(backgroundStartEvent?.time_ms || 0);
    const backgroundEndMs = Number(backgroundEndEvent?.time_ms || timedTimeline?.duration_ms || 0);
    const backgroundAsset = battleEffectBackgroundAssetForMove(effectGeneration, moveName, {
      ...logic,
      background: /bgeffect|monbg|setalpha|blend|battle_anim/.test(commandText),
      family
    });
    const count = Math.max(...objectSignals, 1);
    const renderedAssetCount = Math.min(12, assets.length);
    return {
      family,
      duration: timedTimeline ? Math.max(440, Math.min(2400, timedTimeline.duration_ms)) : Math.max(440, Math.min(1800, 320 + Number(profile?.command_count || count) * 46 + waitFrames * 8)),
      objectCount: Math.max(renderedAssetCount || 1, Math.min(12, count || 1)),
      assets: assets.slice(0, 12),
      flash: ["flash", "electric", "psychic", "explosion", "ice"].includes(family) || /bgeffect|blend|alpha|flash|palette|monbg/.test(commandText),
      shake: ["ground", "rock", "explosion", "impact"].includes(family) || /shake|earthquake|magnitude/.test(commandText),
      background: /bgeffect|monbg|setalpha|blend|battle_anim/.test(commandText),
      backgroundAsset,
      backgroundStartFrame: Number(backgroundStartEvent?.frame || 0),
      backgroundStartMs,
      backgroundEndFrame: Number(backgroundEndEvent?.frame || timedTimeline?.duration_frames || 0),
      backgroundEndMs,
      backgroundDurationMs: backgroundEndMs > backgroundStartMs ? Math.max(35, backgroundEndMs - backgroundStartMs) : 0,
      backgroundEvents: (timelineProfile?.events || [])
        .filter((event) => event?.type === "bg_effect" || event?.type === "incbgeffect")
        .map((event) => ({
          args: Array.isArray(event.args) ? event.args.slice() : [],
          effect: event.effect || "",
          effectIndex: event.effect_index ?? null,
          frame: Number(event.frame || 0),
          timeMs: Number(event.time_ms || 0),
          type: event.type
        })),
      timeline: timelineProfile ? timelineProfile.events : []
    };
  }

  function isGen2BattleAnimationProfile(profile) {
    if (Number(profile?.generation || profile?.logic?.generation || 0) === 2) return true;
    const script = Array.isArray(profile?.script) ? profile.script : [];
    if (!script.length) return false;
    const hasGen2Commands = script.some((step) => String(step?.command || "").startsWith("anim_"));
    const hasGen2Objects = Array.isArray(profile?.logic?.objects) || Array.isArray(profile?.logic?.bg_effects);
    return hasGen2Commands && hasGen2Objects;
  }

  function effectAssetsForProfile(profile, baseAssets) {
    const assets = Array.isArray(baseAssets) ? baseAssets : [];
    const objects = Array.isArray(profile?.logic?.objects) ? profile.logic.objects : [];
    if (!objects.length) return assets;
    const timeline = isGen2BattleAnimationProfile(profile) ? gen2BattleAnimTimeline(profile) : null;
    const objectEvents = new Map();
    const clearEvents = (timeline?.events || [])
      .filter((event) => event?.type === "clearobjs")
      .map((event) => ({
        frame: Number(event.frame || 0),
        timeMs: Number(event.time_ms || 0)
      }))
      .sort((left, right) => left.frame - right.frame);
    const timelineEndFrame = Number(timeline?.duration_frames || 0);
    const timelineEndMs = Number(timeline?.duration_ms || 0);
    const usesGen2Coordinates = isGen2BattleAnimationProfile(profile);
    (timeline?.events || []).forEach((event) => {
      if (event?.type !== "object") return;
      const objectIndex = Number(event.object_index);
      if (!Number.isFinite(objectIndex)) return;
      objectEvents.set(objectIndex, event);
    });
    const assetsByGfx = new Map();
    assets.forEach((asset) => {
      const keys = [asset.tag, asset.symbol, asset.gfx].filter(Boolean);
      keys.forEach((key) => assetsByGfx.set(String(key), asset));
    });
    const objectAssets = objects.map((object, index) => {
      const base = assetsByGfx.get(String(object.gfx || "")) || assetsByGfx.get(String(object.composite?.gfx || ""));
      if (!base?.path) return null;
      const objectEvent = objectEvents.get(index);
      const startFrame = Number(objectEvent?.frame || 0);
      const startMs = Number(objectEvent?.time_ms || 0);
      const clearEvent = clearEvents.find((event) => event.frame >= startFrame);
      const endFrame = clearEvent ? clearEvent.frame : timelineEndFrame;
      const endMs = clearEvent ? clearEvent.timeMs : timelineEndMs;
      const durationMs = endMs > startMs ? Math.max(35, endMs - startMs) : 0;
      const stateEvents = (timeline?.events || [])
        .filter((event) => (
          (event?.type === "incobj" || event?.type === "setobj")
          && Number(event.target_object_index) === index
        ))
        .map((event) => ({
          frame: Number(event.frame || 0),
          objectId: Number(event.object_id || index + 1),
          state: event.state === null || event.state === undefined ? null : Number(event.state || 0),
          timeMs: Number(event.time_ms || 0),
          type: event.type
        }));
      const composite = object.composite ? {
        ...object.composite,
        args: object.args || [],
        callback: object.callback || object.composite.callback || "",
        frameset: object.frameset || object.composite.frameset || "",
        gfx: object.gfx || object.composite.gfx || "",
        object: object.object || object.composite.object || ""
      } : null;
      const position = usesGen2Coordinates ? gen2ObjectPosition(object.args || []) : null;
      return {
        ...base,
        args: object.args || [],
        callback: object.callback || composite?.callback || "",
        composites: composite ? [composite] : [],
        frameset: object.frameset || composite?.frameset || "",
        gfx: object.gfx || composite?.gfx || "",
        object: object.object || composite?.object || "",
        instanceIndex: index,
        startFrame,
        startMs,
        endFrame,
        endMs,
        durationMs,
        position,
        stateEvents,
        timelineScriptIndex: objectEvents.has(index) ? Number(objectEvents.get(index).script_index || 0) : null
      };
    }).filter(Boolean);
    return objectAssets.length ? objectAssets : assets;
  }

  function gen2ObjectPosition(args) {
    if (!Array.isArray(args) || args.length < 2) return null;
    const x = parseBattleAnimNumber(args[0]);
    const y = parseBattleAnimNumber(args[1]);
    return {
      x,
      y,
      leftPercent: (x / 160) * 100,
      topPercent: (y / 96) * 100
    };
  }

  function framePlanForRecord(record) {
    const frame = record?.frame || {};
    const dimensions = record?.dimensions || {};
    const inferred = inferredPokemonFramePlan(record, frame, dimensions);
    if (inferred) return inferred;
    const width = Number(frame.width || dimensions.width || 0);
    const height = Number(frame.height || dimensions.height || 0);
    const columns = Math.max(1, Number(frame.columns || 1));
    const rows = Math.max(1, Number(frame.rows || 1));
    const count = Math.max(1, Math.min(Number(frame.count || columns * rows || 1), columns * rows || 1));
    if (!width || !height) return null;
    return {
      width,
      height,
      columns,
      rows,
      count,
      frameMs: Math.max(35, Number(frame.frame_ms || 90)),
      layout: frame.layout || "static"
    };
  }

  function inferredPokemonFramePlan(record, frame, dimensions) {
    const path = String(record?.path || "");
    const width = Number(dimensions.width || frame.width || 0);
    const height = Number(dimensions.height || frame.height || 0);
    if (!width || !height) return null;
    if (!path.startsWith("gen2/pokemon/") || !path.endsWith("/front.png")) return null;
    if (String(frame.layout || "") !== "static" || Number(frame.count || 1) !== 1) return null;
    if (height <= width || height % width !== 0) return null;
    const rows = Math.max(1, height / width);
    if (rows <= 1) return null;
    return {
      width,
      height: width,
      columns: 1,
      rows,
      count: rows,
      frameMs: Math.max(90, Number(frame.frame_ms || 160)),
      layout: "pokemon_front"
    };
  }

  function frameDataAttributes(plan, frameMs, options = {}) {
    if (!plan || plan.count <= 1) return "";
    const attributes = [
      `data-battle-frame-count="${plan.count}"`,
      `data-battle-frame-columns="${plan.columns}"`,
      `data-battle-frame-rows="${plan.rows}"`,
      `data-battle-frame-ms="${Math.max(35, Number(frameMs || plan.frameMs || 90))}"`
    ];
    if (options.mode) attributes.push(`data-battle-frame-mode="${escapeAttribute(options.mode)}"`);
    if (Array.isArray(options.sequence) && options.sequence.length) {
      attributes.push(`data-battle-frame-sequence="${escapeAttribute(options.sequence.join(","))}"`);
    }
    if (Array.isArray(options.durations) && options.durations.length) {
      attributes.push(`data-battle-frame-durations="${escapeAttribute(options.durations.join(","))}"`);
    }
    if (options.motion) attributes.push(`data-battle-mon-motion="${escapeAttribute(options.motion)}"`);
    return attributes.join(" ");
  }

  function pokemonFrameAnimationSpeciesKeys(record, species) {
    const keys = [];
    if (species) keys.push(normalizeAssetSpeciesKey(species), normalizeSpeciesKey(species));
    const pathMatch = String(record?.path || "").match(/gen[23]\/pokemon\/([^/]+)/);
    if (pathMatch) keys.push(normalizeAssetSpeciesKey(pathMatch[1]), normalizeSpeciesKey(pathMatch[1]));
    return [...new Set(keys.filter(Boolean))];
  }

  function pokemonSpriteFramePlaybackForRecord(record, options = {}) {
    const plan = framePlanForRecord(record);
    if (!plan || plan.count <= 1) return null;
    if (String(plan.layout || "") === "pokemon_front") {
      const animationKind = String(options.animationKind || "front");
      const animationMap = animationKind === "idle"
        ? (options.animations?.idle_species || options.animations?.idle || {})
        : (options.animations?.species || options.animations || {});
      for (const key of pokemonFrameAnimationSpeciesKeys(record, options.species)) {
        const entry = animationMap[key];
        if (!entry) continue;
        const sequence = (entry.sequence || []).map(Number).filter((frame) => Number.isFinite(frame) && frame >= 0 && frame < plan.count);
        if (!sequence.length) continue;
        const isGen2Front = String(record?.path || "").startsWith("gen2/pokemon/");
        const playbackSequence = isGen2Front && animationKind !== "idle" && sequence.at(-1) !== 0 ? sequence.concat(0) : sequence;
        const durations = (entry.durations_ms || []).slice(0, playbackSequence.length).map((duration) => Math.max(16, Number(duration || 0)));
        if (isGen2Front && animationKind !== "idle" && durations.length < playbackSequence.length) durations.push(plan.frameMs);
        return {
          mode: animationKind === "idle" ? "loop" : "once",
          sequence: playbackSequence,
          durations,
          frameMs: durations[0] || plan.frameMs,
          motion: entry.motion || "",
          source: entry.anim || ""
        };
      }
      const sequence = plan.count === 2 ? [0, 1, 0] : Array.from({ length: plan.count }, (_, index) => index).concat(0);
      return {
        mode: "once",
        sequence,
        frameMs: Math.max(35, Math.min(220, Number(plan.frameMs || 150)))
      };
    }
    return {
      mode: String(record?.path || "").startsWith("gen2/pokemon/") ? "once" : "loop",
      sequence: Array.from({ length: plan.count }, (_, index) => index),
      frameMs: plan.frameMs
    };
  }

  function pokemonSpriteMotionProfile(motionName) {
    const motion = String(motionName || "").toUpperCase();
    const make = (steps, frameMs = 70) => ({ motion, frameMs, steps });
    if (!motion) return null;
    if (motion.includes("FIGURE_8")) {
      return make([
        { transform: "translate(0, 0)" },
        { transform: "translate(5px, -5px)" },
        { transform: "translate(0, -9px)" },
        { transform: "translate(-5px, -5px)" },
        { transform: "translate(0, 0)" },
        { transform: "translate(5px, 5px)" },
        { transform: "translate(0, 8px)" },
        { transform: "translate(-5px, 5px)" },
        { transform: "translate(0, 0)" }
      ], 46);
    }
    if (motion.includes("FOUR_PETAL")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(4px, -5px) rotate(5deg)" },
        { transform: "translate(-4px, -5px) rotate(-5deg)" },
        { transform: "translate(-4px, 4px) rotate(5deg)" },
        { transform: "translate(4px, 4px) rotate(-5deg)" },
        { transform: "translate(0, 0) rotate(0deg)" }
      ], 58);
    }
    if (motion.includes("CIRCLE") || motion.includes("CIRCULAR")) {
      return make([
        { transform: "translate(0, 0) scale(1, 1)" },
        { transform: "translate(5px, -4px) scale(1.05, 0.96)" },
        { transform: "translate(0, -8px) scale(0.96, 1.05)" },
        { transform: "translate(-5px, -4px) scale(1.05, 0.96)" },
        { transform: "translate(0, 0) scale(1, 1)" }
      ], motion.includes("SLOW") ? 92 : 62);
    }
    if (motion.includes("SPIN")) {
      return make([
        { transform: "rotate(0deg)" },
        { transform: "rotate(90deg)" },
        { transform: "rotate(180deg)" },
        { transform: "rotate(270deg)" },
        { transform: "rotate(360deg)" }
      ], motion.includes("LONG") ? 82 : 48);
    }
    if (motion.includes("FLIP")) {
      const axis = motion.includes("BACK") ? "scaleY" : "scaleX";
      return make([
        { transform: `${axis}(1) translateY(0)` },
        { transform: `${axis}(0.35) translateY(-5px)` },
        { transform: `${axis}(-1) translateY(-8px)` },
        { transform: `${axis}(0.35) translateY(-5px)` },
        { transform: `${axis}(1) translateY(0)` }
      ], motion.includes("BIG") ? 76 : 58);
    }
    if (motion.includes("TWIST")) {
      return make([
        { transform: "skewX(0deg) scaleX(1)" },
        { transform: "skewX(-10deg) scaleX(0.9)" },
        { transform: "skewX(10deg) scaleX(0.9)" },
        { transform: "skewX(-6deg) scaleX(0.96)" },
        { transform: "skewX(0deg) scaleX(1)" }
      ], motion.includes("TWICE") ? 50 : 66);
    }
    if (motion.includes("SWING_CONCAVE")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(-4px, -5px) rotate(-5deg)" },
        { transform: "translate(0, -8px) rotate(0deg)" },
        { transform: "translate(4px, -5px) rotate(5deg)" },
        { transform: "translate(0, 0) rotate(0deg)" }
      ], motion.includes("FAST") ? 44 : 68);
    }
    if (motion.includes("SWING_CONVEX")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(4px, 5px) rotate(5deg)" },
        { transform: "translate(0, 8px) rotate(0deg)" },
        { transform: "translate(-4px, 5px) rotate(-5deg)" },
        { transform: "translate(0, 0) rotate(0deg)" }
      ], motion.includes("FAST") ? 44 : 68);
    }
    if (motion.includes("CONCAVE_ARC")) {
      return make([
        { transform: "translate(0, 0)" },
        { transform: "translate(-6px, -5px)" },
        { transform: "translate(0, -9px)" },
        { transform: "translate(6px, -5px)" },
        { transform: "translate(0, 0)" }
      ], motion.includes("SLOW") ? 96 : 62);
    }
    if (motion.includes("CONVEX_DOUBLE_ARC")) {
      return make([
        { transform: "translate(0, 0)" },
        { transform: "translate(5px, 5px)" },
        { transform: "translate(0, 9px)" },
        { transform: "translate(-5px, 5px)" },
        { transform: "translate(0, 0)" },
        { transform: "translate(5px, -5px)" },
        { transform: "translate(0, -7px)" },
        { transform: "translate(-5px, -5px)" },
        { transform: "translate(0, 0)" }
      ], motion.includes("SLOW") ? 88 : 56);
    }
    if (motion.includes("TRIANGLE")) {
      return make([
        { transform: "translate(0, 0)" },
        { transform: "translate(-6px, -6px)" },
        { transform: "translate(6px, -6px)" },
        { transform: "translate(0, 0)" }
      ], motion.includes("SLOW") ? 90 : 58);
    }
    if (motion.includes("ZIGZAG")) {
      return make([
        { transform: "translate(0, 0)" },
        { transform: "translate(6px, -5px)" },
        { transform: "translate(-6px, -2px)" },
        { transform: "translate(5px, 3px)" },
        { transform: "translate(0, 0)" }
      ], motion.includes("SLOW") ? 86 : 42);
    }
    if (motion.includes("SPRING")) {
      return make([
        { transform: "translateY(0) scale(1, 1)" },
        { transform: "translateY(4px) scale(1.04, 0.86)" },
        { transform: "translateY(-9px) scale(0.95, 1.14)" },
        { transform: "translateY(2px) scale(1.02, 0.94)" },
        { transform: "translateY(0) scale(1, 1)" }
      ], motion.includes("SLOW") ? 96 : 58);
    }
    if (motion.includes("RISING_WOBBLE")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(-3px, -4px) rotate(-4deg)" },
        { transform: "translate(3px, -8px) rotate(4deg)" },
        { transform: "translate(-2px, -11px) rotate(-2deg)" },
        { transform: "translate(0, 0) rotate(0deg)" }
      ], 64);
    }
    if (motion.includes("H_HOPS")) {
      return make([
        { transform: "translateX(0) translateY(0)" },
        { transform: "translateX(5px) translateY(-5px)" },
        { transform: "translateX(10px) translateY(0)" },
        { transform: "translateX(5px) translateY(-4px)" },
        { transform: "translateX(0) translateY(0)" }
      ], motion.includes("RAPID") ? 38 : 58);
    }
    if (motion.includes("WOBBLE")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(-3px, -3px) rotate(-3deg)" },
        { transform: "translate(3px, -5px) rotate(3deg)" },
        { transform: "translate(-2px, -2px) rotate(-2deg)" },
        { transform: "translate(0, 0) rotate(0deg)" }
      ], motion.includes("SLOW") ? 92 : 58);
    }
    if (motion.includes("JUMPS") && !motion.includes("V_JUMPS_H_JUMPS")) {
      const jump = motion.includes("BIG") ? -12 : motion.includes("SMALL") ? -5 : -8;
      return make([
        { transform: "translate(0, 0) scale(1, 1)" },
        { transform: `translate(0, ${jump}px) scale(0.98, 1.05)` },
        { transform: "translate(4px, 0) scale(1.04, 0.96)" },
        { transform: `translate(4px, ${Math.round(jump * 0.7)}px) scale(0.98, 1.05)` },
        { transform: "translate(0, 0) scale(1, 1)" }
      ], motion.includes("SLOW") ? 92 : 58);
    }
    if (motion.includes("STRETCH")) {
      const vertical = motion.includes("V_STRETCH") || motion.includes("VERTICAL");
      return make([
        { transform: "scale(1, 1)" },
        { transform: vertical ? "scale(0.9, 1.18)" : "scale(1.18, 0.92)" },
        { transform: vertical ? "scale(1.06, 0.92)" : "scale(0.94, 1.06)" },
        { transform: "scale(1, 1)" }
      ], motion.includes("SLOW") ? 96 : 64);
    }
    if (motion.includes("SHRINK_GROW")) {
      return make([
        { transform: "scale(1)" },
        { transform: "scale(0.82)" },
        { transform: "scale(1.12)" },
        { transform: "scale(0.96)" },
        { transform: "scale(1)" }
      ], motion.includes("FAST") ? 46 : motion.includes("SLOW") ? 96 : 64);
    }
    if (motion.includes("BACK_AND_LUNGE") || motion.includes("LUNGE")) {
      return make([
        { transform: "translateX(0) scale(1)" },
        { transform: "translateX(-7px) scale(0.96)" },
        { transform: "translateX(10px) scale(1.06)" },
        { transform: "translateX(0) scale(1)" }
      ], 58);
    }
    if (motion.includes("TIP")) {
      return make([
        { transform: "rotate(0deg) translate(0, 0)" },
        { transform: "rotate(-8deg) translate(-3px, 0)" },
        { transform: "rotate(5deg) translate(4px, -2px)" },
        { transform: "rotate(0deg) translate(0, 0)" }
      ], 62);
    }
    if (motion.includes("FLICKER")) {
      return make([
        { opacity: "1" },
        { opacity: "0.35" },
        { opacity: "1" },
        { opacity: "0.55" },
        { opacity: "1" }
      ], motion.includes("INCREASING") ? 54 : 46);
    }
    if (motion.includes("V_JUMPS_H_JUMPS")) {
      return make([
        { transform: "translate(0, 0)" },
        { transform: "translate(2px, -6px)" },
        { transform: "translate(-2px, 0)" },
        { transform: "translate(2px, -4px)" },
        { transform: "translate(0, 0)" }
      ], 65);
    }
    if (motion.includes("V_SQUISH_AND_BOUNCE")) {
      return make([
        { transform: "translateY(0) scale(1, 1)" },
        { transform: "translateY(3px) scale(1.08, 0.88)" },
        { transform: "translateY(-5px) scale(0.94, 1.1)" },
        { transform: "translateY(0) scale(1, 1)" }
      ], motion.includes("SLOW") ? 105 : 72);
    }
    if (motion.includes("H_VIBRATE") || motion.includes("H_SHAKE")) {
      return make([
        { transform: "translateX(0)" },
        { transform: "translateX(-3px)" },
        { transform: "translateX(3px)" },
        { transform: "translateX(-2px)" },
        { transform: "translateX(0)" }
      ], motion.includes("FAST") ? 42 : 60);
    }
    if (motion.includes("V_SHAKE")) {
      return make([
        { transform: "translateY(0)" },
        { transform: "translateY(-4px)" },
        { transform: "translateY(3px)" },
        { transform: "translateY(-2px)" },
        { transform: "translateY(0)" }
      ], motion.includes("SLOW") ? 90 : 58);
    }
    if (motion.includes("H_SLIDE")) {
      return make([
        { transform: "translateX(0)" },
        { transform: "translateX(8px)" },
        { transform: "translateX(-4px)" },
        { transform: "translateX(0)" }
      ], motion.includes("SLOW") ? 95 : 62);
    }
    if (motion.includes("V_SLIDE")) {
      return make([
        { transform: "translateY(0)" },
        { transform: "translateY(-8px)" },
        { transform: "translateY(4px)" },
        { transform: "translateY(0)" }
      ], motion.includes("SLOW") ? 95 : 62);
    }
    if (motion.includes("ROTATE") || motion.includes("PIVOT")) {
      return make([
        { transform: "rotate(0deg)" },
        { transform: "rotate(-4deg)" },
        { transform: "rotate(4deg)" },
        { transform: "rotate(0deg)" }
      ], motion.includes("FAST") ? 46 : 70);
    }
    if (motion.includes("GROW")) {
      return make([
        { transform: "scale(1)" },
        { transform: "scale(1.08)" },
        { transform: "scale(0.98)" },
        { transform: "scale(1)" }
      ], motion.includes("SLOW") ? 95 : 68);
    }
    if (motion.includes("FLASH") || motion.includes("GLOW")) {
      return make([
        { filter: "brightness(1)" },
        { filter: "brightness(1.85)" },
        { filter: "brightness(1)" },
        { filter: "brightness(1.55)" },
        { filter: "brightness(1)" }
      ], motion.includes("FAST") ? 44 : 72);
    }
    return null;
  }

  function frameStyle(record, url, extra = {}) {
    const plan = framePlanForRecord(record);
    if (!plan) return "";
    const declarations = [
      `--battle-frame-columns:${plan.columns}`,
      `--battle-frame-rows:${plan.rows}`,
      `--battle-frame-bg-width:${plan.columns * 100}%`,
      `--battle-frame-bg-height:${plan.rows * 100}%`,
      `background-image:url('${escapeAttribute(url)}')`,
      `aspect-ratio:${plan.width}/${plan.height}`
    ];
    if (extra.width) declarations.push(`width:${Math.round(extra.width)}px`);
    if (extra.height) declarations.push(`height:${Math.round(extra.height)}px`);
    return declarations.join(";");
  }

  function effectFrameScale(asset, plan) {
    const role = String(asset?.role || "");
    if (role === "gen1_tileset" || role === "gen2_anim_gfx") return Math.max(3, Math.min(5, 32 / Math.max(1, Math.min(plan.width, plan.height))));
    if (plan.width <= 8 || plan.height <= 8) return 4;
    if (plan.width <= 16 || plan.height <= 16) return 3;
    if (plan.width >= 96 || plan.height >= 96) return 1.15;
    return 2;
  }

  function humanizeMoveName(value, generation = 3) {
    const raw = String(value || "").trim();
    if (!raw) return "---";
    const spaced = raw
      .replace(/_/g, " ")
      .replace(/-/g, " ")
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/\s+/g, " ")
      .trim();
    if (generation <= 2) return spaced.toUpperCase();
    if (spaced === spaced.toUpperCase()) return spaced;
    return spaced.replace(/\b[a-z]/g, (letter) => letter.toUpperCase());
  }

  function pokemonDisplayName(value, generation = 3) {
    const name = String(value || "").trim() || "POKéMON";
    return generation <= 2 ? name.toUpperCase() : name;
  }

  function battleGlyphCodeForGeneration(character, generation) {
    const gen = Number(generation) || 1;
    const map = gen === 1 ? BATTLE_GLYPH_CODES_GEN1 : gen === 2 ? BATTLE_GLYPH_CODES_GEN2 : BATTLE_GLYPH_CODES_GEN3;
    if (character in map) return map[character];
    if (character.toUpperCase() in map) return map[character.toUpperCase()];
    if (character.toLowerCase() in map) return map[character.toLowerCase()];
    return null;
  }

  function renderBattleText(text, generation = 3, options = {}) {
    const raw = String(text ?? "");
    const gen = Number(generation) || 1;
    const assets = battleTextAssetsForGeneration(gen);
    if (!assets) return escapeHtml(raw);
    const fontUrl = battleUiAssetUrl(assets.font);
    if (!fontUrl) return escapeHtml(raw);
    const chars = Array.from(raw);
    const glyphs = chars.map((character) => {
      if (character === " ") return `<span class="battle-scene-text-gap" aria-hidden="true"></span>`;
      const code = battleGlyphCodeForGeneration(character, gen);
      if (code == null) return `<span class="battle-scene-text-glyph battle-scene-text-glyph-missing">${escapeHtml(character)}</span>`;
      const baseCode = Number(assets.baseCode || 0);
      const columns = Math.max(1, Number(assets.columns || 16));
      const rows = Math.max(1, Number(assets.rows || 8));
      const index = Math.max(0, code - baseCode);
      const column = index % columns;
      const row = Math.floor(index / columns);
      const x = columns > 1 ? (column / (columns - 1)) * 100 : 0;
      const y = rows > 1 ? (row / (rows - 1)) * 100 : 0;
      return `<span class="battle-scene-text-glyph" aria-hidden="true" style="background-image:url('${escapeAttribute(fontUrl)}');background-size:${columns * 100}% ${rows * 100}%;background-position:${x}% ${y}%;"></span>`;
    }).join("");
    return `<span class="battle-scene-text-sprite${options.className ? ` ${escapeAttribute(options.className)}` : ""}" aria-label="${escapeAttribute(raw)}">${glyphs}</span>`;
  }

  const BATTLE_GLYPH_CODES_GEN1 = {
    " ": 0x7f,
    A: 0x80, B: 0x81, C: 0x82, D: 0x83, E: 0x84, F: 0x85, G: 0x86, H: 0x87, I: 0x88, J: 0x89,
    K: 0x8a, L: 0x8b, M: 0x8c, N: 0x8d, O: 0x8e, P: 0x8f, Q: 0x90, R: 0x91, S: 0x92, T: 0x93,
    U: 0x94, V: 0x95, W: 0x96, X: 0x97, Y: 0x98, Z: 0x99,
    a: 0xa0, b: 0xa1, c: 0xa2, d: 0xa3, e: 0xa4, f: 0xa5, g: 0xa6, h: 0xa7, i: 0xa8, j: 0xa9,
    k: 0xaa, l: 0xab, m: 0xac, n: 0xad, o: 0xae, p: 0xaf, q: 0xb0, r: 0xb1, s: 0xb2, t: 0xb3,
    u: 0xb4, v: 0xb5, w: 0xb6, x: 0xb7, y: 0xb8, z: 0xb9,
    "é": 0xba, "-": 0xe3, "?": 0xe6, "!": 0xe7, ".": 0xe8, "▶": 0xed, "▼": 0xee, "×": 0xf1,
    "/": 0xf3, ",": 0xf4, "♀": 0xf5, "0": 0xf6, "1": 0xf7, "2": 0xf8, "3": 0xf9,
    "4": 0xfa, "5": 0xfb, "6": 0xfc, "7": 0xfd, "8": 0xfe, "9": 0xff
  };

  const BATTLE_GLYPH_CODES_GEN2 = {
    " ": 0x7f,
    A: 0x80, B: 0x81, C: 0x82, D: 0x83, E: 0x84, F: 0x85, G: 0x86, H: 0x87, I: 0x88, J: 0x89,
    K: 0x8a, L: 0x8b, M: 0x8c, N: 0x8d, O: 0x8e, P: 0x8f, Q: 0x90, R: 0x91, S: 0x92, T: 0x93,
    U: 0x94, V: 0x95, W: 0x96, X: 0x97, Y: 0x98, Z: 0x99,
    a: 0xa0, b: 0xa1, c: 0xa2, d: 0xa3, e: 0xa4, f: 0xa5, g: 0xa6, h: 0xa7, i: 0xa8, j: 0xa9,
    k: 0xaa, l: 0xab, m: 0xac, n: 0xad, o: 0xae, p: 0xaf, q: 0xb0, r: 0xb1, s: 0xb2, t: 0xb3,
    u: 0xb4, v: 0xb5, w: 0xb6, x: 0xb7, y: 0xb8, z: 0xb9,
    "é": 0xea, "-": 0xe3, "?": 0xe6, "!": 0xe7, ".": 0xe8, "▶": 0xed, "▼": 0xee, "×": 0xf1,
    "/": 0xf3, ",": 0xf4, "♀": 0xf5, "0": 0xf6, "1": 0xf7, "2": 0xf8, "3": 0xf9,
    "4": 0xfa, "5": 0xfb, "6": 0xfc, "7": 0xfd, "8": 0xfe, "9": 0xff,
    "(": 0x9a, ")": 0x9b, ":": 0x9c
  };

  const BATTLE_GLYPH_CODES_GEN3 = {
    " ": 0x00,
    "0": 0xa1, "1": 0xa2, "2": 0xa3, "3": 0xa4, "4": 0xa5, "5": 0xa6, "6": 0xa7, "7": 0xa8, "8": 0xa9, "9": 0xaa,
    "!": 0xab, "?": 0xac, ".": 0xad, "-": 0xae, "·": 0xaf, "…": 0xb0, "/": 0xba, "&": 0xe9, ":": 0xf0, ",": 0xf4,
    "(": 0x9a, ")": 0x9b, "A": 0xbb, "B": 0xbc, "C": 0xbd, "D": 0xbe, "E": 0xbf, "F": 0xc0, "G": 0xc1, "H": 0xc2,
    "I": 0xc3, "J": 0xc4, "K": 0xc5, "L": 0xc6, "M": 0xc7, "N": 0xc8, "O": 0xc9, "P": 0xca, "Q": 0xcb, "R": 0xcc,
    "S": 0xcd, "T": 0xce, "U": 0xcf, "V": 0xd0, "W": 0xd1, "X": 0xd2, "Y": 0xd3, "Z": 0xd4,
    "a": 0xda, "b": 0xdb, "c": 0xdc, "d": 0xdd, "e": 0xde, "f": 0xdf, "g": 0xe0, "h": 0xe1, "i": 0xe2, "j": 0xe3,
    "k": 0xe4, "l": 0xe5, "m": 0xe6, "n": 0xe7, "o": 0xe8, "p": 0xe9, "q": 0xea, "r": 0xeb, "s": 0xec, "t": 0xed,
    "u": 0xee, "v": 0xef, "w": 0xf0, "x": 0xf1, "y": 0xf2, "z": 0xf3,
    "é": 0xea, "▶": 0xed, "▼": 0xee, "♀": 0xf5, "♂": 0xef, "×": 0xb9, "¥": 0xf0
  };

  function actionGroupsFromRequest(request) {
    const moves = [];
    const switches = [];
    const active = request?.active?.[0];
    if (active && Array.isArray(active.moves)) {
      active.moves.forEach((move, index) => {
        moves.push({
          action: `move ${index + 1}`,
          label: move.move || `Move ${index + 1}`,
          pp: Number(move.pp ?? 0),
          maxpp: Number(move.maxpp ?? move.pp ?? 0),
          type: move.type || move.moveType || move.category || "--",
          disabled: Boolean(move.disabled) || Number(move.pp ?? 1) <= 0,
          reason: move.disabledSource || move.disabled || ""
        });
      });
    }
    if (request?.side && Array.isArray(request.side.pokemon)) {
      request.side.pokemon.forEach((pokemon, index) => {
        const details = String(pokemon.details || "");
        const condition = String(pokemon.condition || "");
        switches.push({
          action: `switch ${index + 1}`,
          index,
          ident: pokemon.ident || "",
          name: parseBattleIdent(pokemon.ident || "").nickname || details.split(",")[0] || `Pokémon ${index + 1}`,
          details,
          condition,
          active: Boolean(pokemon.active),
          disabled: Boolean(pokemon.active) || /fnt/i.test(condition) || /egg/i.test(details),
          fainted: /fnt/i.test(condition) || condition.startsWith("0/")
        });
      });
    }
    return {
      moves,
      switches,
      forcedSwitch: Boolean(request?.forceSwitch)
    };
  }

  function createBattleSceneController({ element, getGeneration, manifestUrl = MANIFEST_URL, animationMapUrl = ANIMATION_MAP_URL }) {
    if (!element || typeof document === "undefined") {
      return null;
    }

    let manifest = null;
    let manifestPromise = null;
    let animationMap = null;
    let animationMapPromise = null;
    let pokemonFrameAnimations = {};
    let pokemonFrameAnimationsPromise = {};
    let generation = Number(getGeneration?.() || 1);
    let animationQueue = Promise.resolve();
    let frameTimers = [];
    const state = {
      p1: emptyPokemon("p1"),
      p2: emptyPokemon("p2"),
      turn: 0,
      message: battleProfileForGeneration(generation).defaultMessage,
      effect: null,
      ready: false,
      request: null,
      menuMode: "message",
      locked: false,
      selectedPocket: "",
      selectedBagItem: null,
      context: {
        playerName: "",
        party: [],
        inventory: []
      }
    };

    function emptyPokemon(side) {
      return {
        side,
        nickname: SIDE_LABELS[side],
        species: "",
        level: null,
        currentHp: 0,
        maxHp: 0,
        status: "ok",
        sprite: "",
        spriteRecord: null,
        fainted: false
      };
    }

    function profile() {
      return battleProfileForGeneration(generation);
    }

    function loadManifest() {
      if (manifest || manifestPromise) return manifestPromise || Promise.resolve(manifest);
      manifestPromise = fetch(manifestUrl)
        .then((response) => {
          if (!response.ok) throw new Error(`manifest ${response.status}`);
          return response.json();
        })
        .then((data) => {
          manifest = data;
          state.ready = true;
          render();
          return manifest;
        })
        .catch(() => {
          state.ready = false;
          render();
          return null;
        });
      return manifestPromise;
    }

    function loadAnimationMap() {
      if (animationMap || animationMapPromise) return animationMapPromise || Promise.resolve(animationMap);
      animationMapPromise = fetch(animationMapUrl)
        .then((response) => {
          if (!response.ok) throw new Error(`animation-map ${response.status}`);
          return response.json();
        })
        .then((data) => {
          animationMap = data;
          return animationMap;
        })
        .catch(() => null);
      return animationMapPromise;
    }

    function loadPokemonFrameAnimations() {
      const url = POKEMON_FRAME_ANIMATION_URLS[generation];
      if (!url) return Promise.resolve(null);
      if (pokemonFrameAnimations[generation] || pokemonFrameAnimationsPromise[generation]) {
        return pokemonFrameAnimationsPromise[generation] || Promise.resolve(pokemonFrameAnimations[generation]);
      }
      pokemonFrameAnimationsPromise[generation] = fetch(url)
        .then((response) => {
          if (!response.ok) throw new Error(`pokemon-frame-animation ${response.status}`);
          return response.json();
        })
        .then((data) => {
          pokemonFrameAnimations[generation] = data;
          render();
          return pokemonFrameAnimations[generation];
        })
        .catch(() => null);
      return pokemonFrameAnimationsPromise[generation];
    }

    function stopFrameAnimations() {
      frameTimers.forEach((timer) => {
        window.clearInterval(timer);
        window.clearTimeout(timer);
      });
      frameTimers = [];
    }

    function startFrameAnimations() {
      const nodes = element.querySelectorAll("[data-battle-frame-count]");
      nodes.forEach((node) => {
        const count = Math.max(1, Number(node.dataset.battleFrameCount || 1));
        if (count <= 1) return;
        const columns = Math.max(1, Number(node.dataset.battleFrameColumns || count));
        const rows = Math.max(1, Number(node.dataset.battleFrameRows || Math.ceil(count / columns)));
        const frameMs = Math.max(35, Number(node.dataset.battleFrameMs || 90));
        const mode = node.dataset.battleFrameMode || "loop";
        const sequence = String(node.dataset.battleFrameSequence || "")
          .split(",")
          .map((item) => Number(item.trim()))
          .filter((item) => Number.isFinite(item) && item >= 0 && item < count);
        const durations = String(node.dataset.battleFrameDurations || "")
          .split(",")
          .map((item) => Number(item.trim()))
          .filter((item) => Number.isFinite(item) && item > 0);
        const frames = sequence.length ? sequence : Array.from({ length: count }, (_, frame) => frame);
        let index = 0;
        const stepDuration = (stepIndex) => Math.max(16, Number(durations[stepIndex] || frameMs));
        const drawFrame = (frame) => {
          const column = frame % columns;
          const row = Math.floor(frame / columns) % rows;
          const x = columns > 1 ? (column / (columns - 1)) * 100 : 0;
          const y = rows > 1 ? (row / (rows - 1)) * 100 : 0;
          node.style.backgroundPosition = `${x}% ${y}%`;
        };
        const draw = () => {
          drawFrame(frames[index] ?? 0);
          index += 1;
          if (mode !== "once") index %= frames.length;
        };
        draw();
        if (mode === "once") {
          const advanceOnce = () => {
            if (index >= frames.length) return;
            draw();
            if (index < frames.length) {
              frameTimers.push(window.setTimeout(advanceOnce, stepDuration(index - 1)));
            }
          };
          frameTimers.push(window.setTimeout(advanceOnce, stepDuration(0)));
        } else {
          const loop = () => {
            draw();
            frameTimers.push(window.setTimeout(loop, stepDuration((index - 1 + frames.length) % frames.length)));
          };
          frameTimers.push(window.setTimeout(loop, stepDuration(0)));
        }
      });
      const composites = element.querySelectorAll("[data-battle-composite-count]");
      composites.forEach((node) => {
        const count = Math.max(1, Number(node.dataset.battleCompositeCount || 1));
        if (count <= 1) return;
        const frameMs = Math.max(35, Number(node.dataset.battleCompositeMs || 90));
        const durations = String(node.dataset.battleCompositeDurations || "")
          .split(",")
          .map((item) => Number(item.trim()))
          .filter((item) => Number.isFinite(item) && item > 0);
        const frames = Array.from(node.querySelectorAll("[data-battle-composite-frame]"));
        let index = 0;
        const stepDuration = (stepIndex) => Math.max(16, Number(durations[stepIndex] || frameMs));
        const draw = () => {
          frames.forEach((frame, frameIndex) => {
            frame.hidden = frameIndex !== index;
          });
          index = (index + 1) % count;
        };
        draw();
        const loop = () => {
          draw();
          frameTimers.push(window.setTimeout(loop, stepDuration((index - 1 + count) % count)));
        };
        frameTimers.push(window.setTimeout(loop, stepDuration(0)));
      });
      startGen2OamMotionAnimations();
      startPokemonMotionAnimations();
    }

    function startGen2OamMotionAnimations() {
      const nodes = element.querySelectorAll("[data-battle-oam-motion]");
      nodes.forEach((node) => {
        const profile = gen2BattleAnimFunctionProfile(node.dataset.battleOamMotion, Number(node.dataset.battleOamParam || 0));
        if (!profile?.steps?.length) return;
        const baseTransform = node.style.transform || "";
        const baseOpacity = node.style.opacity || "";
        let index = 0;
        const draw = () => {
          const step = profile.steps[index] || {};
          if (step.transform != null) node.style.transform = step.transform;
          if (step.opacity != null) node.style.opacity = step.opacity;
          index += 1;
          if (index >= profile.steps.length) {
            frameTimers.push(window.setTimeout(() => {
              node.style.transform = baseTransform;
              node.style.opacity = baseOpacity;
            }, Number(step.duration || profile.frameMs || 70)));
            return;
          }
          frameTimers.push(window.setTimeout(draw, Number(step.duration || profile.frameMs || 70)));
        };
        draw();
      });
    }

    function startPokemonMotionAnimations() {
      const nodes = element.querySelectorAll("[data-battle-mon-motion]");
      nodes.forEach((node) => {
        const profile = pokemonSpriteMotionProfile(node.dataset.battleMonMotion);
        if (!profile?.steps?.length) return;
        const baseTransform = node.style.transform || "";
        const baseFilter = node.style.filter || "";
        const baseOpacity = node.style.opacity || "";
        let index = 0;
        const draw = () => {
          const step = profile.steps[index] || {};
          if (step.transform != null) node.style.transform = step.transform;
          if (step.filter != null) node.style.filter = step.filter;
          if (step.opacity != null) node.style.opacity = step.opacity;
          index += 1;
          if (index >= profile.steps.length) {
            frameTimers.push(window.setTimeout(() => {
              node.style.transform = baseTransform;
              node.style.filter = baseFilter;
              node.style.opacity = baseOpacity;
            }, Number(step.duration || profile.frameMs || 70)));
            return;
          }
          frameTimers.push(window.setTimeout(draw, Number(step.duration || profile.frameMs || 70)));
        };
        draw();
      });
    }

    function spriteAssetFor(side, species) {
      const genManifest = manifest?.generations?.[String(generation)];
      const speciesMap = genManifest?.pokemon?.species || {};
      const preferredSides = side === "p1" ? ["back", "front"] : generation === 3 ? ["anim_front", "front", "back"] : ["front", "back"];
      for (const candidate of speciesKeyCandidates(species)) {
        const speciesRecord = speciesMap[candidate] || {};
        const record = preferredSides.map((key) => speciesRecord[key]).find((item) => item?.path);
        if (record?.path) {
          return {
            url: `/generated/battle-assets/${record.path}`,
            record
          };
        }
      }
      const dex = window.POKECABLE_SPECIES_DATA?.find?.((entry) => normalizeSpeciesKey(entry.name) === normalizeSpeciesKey(species))?.id;
      return {
        url: dex ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${dex}.png` : "pokemon-fallback.svg",
        record: null
      };
    }

    function spriteUrlFor(side, species) {
      return spriteAssetFor(side, species).url;
    }

    function profileForMove(moveName) {
      const key = normalizeMoveKey(moveName);
      const moveProfile = animationMap?.generations?.[String(generation)]?.moves?.[key];
      if (moveProfile) return { ...moveProfile, generation };
      return {
        label: key || "unknown",
        family: animationFamilyFromMove(moveName),
        command_count: 0,
        commands: [],
        generation
      };
    }

    function render() {
      stopFrameAnimations();
      const genProfile = profile();
      const uiAssets = battleUiAssetsForGeneration(generation, Array.isArray(state.request?.active) && state.request.active.length > 1 ? "doubles" : "singles");
      const hudPlayerUrl = battleUiAssetUrl(uiAssets.hudPlayer);
      const hudEnemyUrl = battleUiAssetUrl(uiAssets.hudEnemy);
      const dialogUrl = battleUiAssetUrl(uiAssets.dialog);
      const dialogFrameUrl = battleUiAssetUrl(uiAssets.dialogFrame);
      const ballsUrl = battleUiAssetUrl(uiAssets.balls);
      const hpBarUrl = battleUiAssetUrl(uiAssets.hpBar);
      const hpBarAnimUrl = battleUiAssetUrl(uiAssets.hpBarAnim);
      const numbersUrl = battleUiAssetUrl(uiAssets.numbers1);
      const fontUrl = battleUiAssetUrl((battleTextAssetsForGeneration(generation) || {}).font);
      const ballStatusBarUrl = battleUiAssetUrl(uiAssets.ballStatusBar);
      const statusUrl = battleUiAssetUrl(uiAssets.status);
      const status2Url = battleUiAssetUrl(uiAssets.status2);
      const status3Url = battleUiAssetUrl(uiAssets.status3);
      const status4Url = battleUiAssetUrl(uiAssets.status4);
      const bagUrl = battleUiAssetUrl(uiAssets.bag);
      const battleBgUrl = battleUiAssetUrl(state.effect?.visual?.backgroundAsset || "");
      const battleBgDelay = Math.max(0, Number(state.effect?.visual?.backgroundStartMs || 0));
      const battleBgDuration = Math.max(220, Number(state.effect?.visual?.backgroundDurationMs || 0) || (Number(state.effect?.visual?.duration || 520) - battleBgDelay));
      const fieldClasses = [
        "battle-scene-field",
        state.effect?.visual?.flash ? "is-bg-flashing" : "",
        state.effect?.visual?.shake ? "is-shaking" : "",
        state.effect?.visual?.background ? "has-bg-effect" : "",
        battleBgUrl ? "has-asset-bg" : ""
      ].filter(Boolean).join(" ");
      element.className = `battle-scene battle-scene-gen${generation}${state.locked ? " is-locked" : ""}`;
      element.innerHTML = `
        <div class="battle-scene-screen" data-generation="${generation}" style="--battle-base-width:${genProfile.baseWidth};--battle-base-height:${genProfile.baseHeight};${generation === 2 ? gen2BattleCssVariables() : ""}${hudPlayerUrl ? `--battle-hud-player-url:url('${escapeAttribute(hudPlayerUrl)}');` : ""}${hudEnemyUrl ? `--battle-hud-enemy-url:url('${escapeAttribute(hudEnemyUrl)}');` : ""}${dialogUrl ? `--battle-dialog-url:url('${escapeAttribute(dialogUrl)}');` : ""}${dialogFrameUrl ? `--battle-dialog-frame-url:url('${escapeAttribute(dialogFrameUrl)}');` : ""}${ballsUrl ? `--battle-balls-url:url('${escapeAttribute(ballsUrl)}');` : ""}${hpBarUrl ? `--battle-hpbar-url:url('${escapeAttribute(hpBarUrl)}');` : ""}${hpBarAnimUrl ? `--battle-hpbar-anim-url:url('${escapeAttribute(hpBarAnimUrl)}');` : ""}${numbersUrl ? `--battle-numbers-url:url('${escapeAttribute(numbersUrl)}');` : ""}${fontUrl ? `--battle-font-url:url('${escapeAttribute(fontUrl)}');` : ""}${ballStatusBarUrl ? `--battle-ball-status-url:url('${escapeAttribute(ballStatusBarUrl)}');` : ""}${statusUrl ? `--battle-status-url:url('${escapeAttribute(statusUrl)}');` : ""}${status2Url ? `--battle-status2-url:url('${escapeAttribute(status2Url)}');` : ""}${status3Url ? `--battle-status3-url:url('${escapeAttribute(status3Url)}');` : ""}${status4Url ? `--battle-status4-url:url('${escapeAttribute(status4Url)}');` : ""}${bagUrl ? `--battle-bag-url:url('${escapeAttribute(bagUrl)}');` : ""}${battleBgUrl ? `--battle-bg-effect-url:url('${escapeAttribute(battleBgUrl)}');--battle-bg-effect-delay:${battleBgDelay}ms;--battle-bg-effect-duration:${battleBgDuration}ms;` : ""}">
          <div class="${fieldClasses}">
            <div class="battle-scene-grid" aria-hidden="true"></div>
            <div class="battle-scene-bg-layer" aria-hidden="true"></div>
            ${renderSide("p2", genProfile, uiAssets)}
            ${renderSide("p1", genProfile, uiAssets)}
            ${renderEffect()}
          </div>
          ${renderBottomPanel(genProfile)}
          ${renderOverlay(genProfile)}
        </div>
      `;
      startFrameAnimations();
    }

    function renderSide(side, genProfile, uiAssets = {}) {
      const pokemon = state[side];
      const percent = hpPercent(pokemon);
      const gen2HpPixels = generation === 2 ? gen2HpBarPixels(pokemon.currentHp, pokemon.maxHp) : null;
      const hpBarClass = generation === 2 ? gen2HpClassForPixels(gen2HpPixels) : hpClass(percent);
      const hpBarWidth = generation === 2 ? `${(gen2HpPixels / 48) * 100}%` : `${percent}%`;
      const displayName = pokemon.species
        ? pokemonDisplayName(pokemon.nickname || pokemon.species, generation)
        : side === "p1" ? "POKéMON" : "FOE";
      const details = pokemon.species
        ? `${displayName}${pokemon.level ? ` Lv${pokemon.level}` : ""}`
        : side === "p1" ? "POKéMON" : "FOE";
      const hpText = side === "p1" || genProfile.enemyShowsHpText
        ? generation === 3 && uiAssets.numbers1
          ? `<div class="battle-scene-hptext battle-scene-hptext-sprite" aria-label="${pokemon.maxHp ? `${pokemon.currentHp}/${pokemon.maxHp}` : "--/--"}">${renderSpriteGlyphs(pokemon.maxHp ? `${pokemon.currentHp}/${pokemon.maxHp}` : "--/--", battleUiAssetUrl(uiAssets.numbers1), "0123456789/")}</div>`
          : `<div class="battle-scene-hptext">${pokemon.maxHp ? `${pokemon.currentHp}/${pokemon.maxHp}` : "--/--"}</div>`
        : "";
      const gen2Hud = generation === 2
        ? gen2BattleScene.renderHud({
          displayNameHtml: escapeHtml(displayName),
          hpClass: hpBarClass,
          hpTextHtml: hpText,
          hpWidth: hpBarWidth,
          levelHtml: pokemon.level ? escapeHtml(String(pokemon.level)) : "",
          showLevel: Boolean(pokemon.level && !statusLabel(pokemon.status)),
          statusHtml: renderStatusBadge(pokemon.status)
        })
        : "";
      return `
        <div class="battle-scene-side battle-scene-${side}${pokemon.fainted ? " is-fainted" : ""}" data-scene-side="${side}">
          ${gen2Hud || `<div class="battle-scene-hud">
            <div class="battle-scene-name-row">
              <span class="battle-scene-name">${escapeHtml(details)}</span>
              ${renderStatusBadge(pokemon.status)}
            </div>
            <div class="battle-scene-hp-row">
              <span class="battle-scene-hp-label">HP</span>
              <div class="battle-scene-hpbar ${hpBarClass}">
                <span style="width:${hpBarWidth}"></span>
              </div>
            </div>
            ${hpText}
          </div>`}
          ${renderPartyBalls(side)}
          <div class="battle-scene-platform"></div>
          ${renderPokemonSprite(pokemon)}
        </div>
      `;
    }

    function renderPokemonSprite(pokemon) {
      const sprite = pokemon.sprite || "pokemon-fallback.svg";
      const plan = framePlanForRecord(pokemon.spriteRecord);
      if (plan && plan.count > 1) {
        const playback = pokemonSpriteFramePlaybackForRecord(pokemon.spriteRecord, {
          species: pokemon.species,
          animations: pokemonFrameAnimations[generation] || null
        }) || {};
        return `
          <span
            class="battle-scene-sprite battle-scene-sprite-frame"
            aria-hidden="true"
            ${frameDataAttributes(plan, playback.frameMs || plan.frameMs, playback)}
            style="${escapeAttribute(frameStyle(pokemon.spriteRecord, sprite))}"
          ></span>
        `;
      }
      return `<img class="battle-scene-sprite" src="${escapeAttribute(sprite)}" alt="" aria-hidden="true" />`;
    }

    function renderStatusBadge(status) {
      const label = statusLabel(status);
      if (!label) return "";
      return `<span class="battle-scene-status battle-scene-status-${escapeAttribute(normalizeStatus(status))}">${escapeHtml(label)}</span>`;
    }

    function renderSpriteGlyphs(text, sheetUrl, alphabet) {
      const chars = String(text || "");
      const sheet = String(sheetUrl || "");
      const charsMap = String(alphabet || "");
      if (!sheet || !charsMap) return escapeHtml(chars);
      const count = charsMap.length;
      return Array.from(chars).map((char) => {
        const index = charsMap.indexOf(char);
        if (index < 0) return `<span class="battle-scene-hp-glyph battle-scene-hp-glyph-missing">${escapeHtml(char)}</span>`;
        const position = count > 1 ? (index / (count - 1)) * 100 : 0;
        return `<span class="battle-scene-hp-glyph" aria-hidden="true" style="background-image:url('${escapeAttribute(sheet)}');background-size:${count * 100}% 100%;background-position:${position}% 0%;"></span>`;
      }).join("");
    }

    function renderPartyBalls(side) {
      const party = side === "p1" ? partyEntriesForRender() : [];
      const count = Math.max(6, party.length || 0);
      const balls = Array.from({ length: Math.min(6, count) }, (_, index) => {
        const pokemon = party[index];
        const className = pokemon
          ? pokemon.fainted ? "is-fainted" : pokemon.active ? "is-active" : normalizeStatus(pokemon.status || "") !== "ok" ? "has-status" : "is-healthy"
          : "is-empty";
        return `<span class="${className}" aria-hidden="true"></span>`;
      }).join("");
      return `<div class="battle-scene-party-balls battle-scene-party-balls-${side}" aria-hidden="true">${balls}</div>`;
    }

    function renderEffect() {
      if (!state.effect) return "";
      const effect = state.effect;
      const assets = effect.visual.assets || [];
      if (!assets.length) return "";
      const assetNodes = assets.map((asset, index) => renderEffectAsset(asset, index, assets.length)).join("");
      return `
        <div class="battle-scene-effect battle-scene-effect-${escapeAttribute(effect.family)} battle-scene-effect-from-${escapeAttribute(effect.side)} is-running" style="--battle-effect-duration:${effect.visual.duration}ms;--battle-effect-assets:${assets.length};" aria-hidden="true">
          ${assetNodes}
        </div>
      `;
    }

    function renderEffectAsset(asset, index, total) {
      const src = `/generated/battle-assets/${asset.path}`;
      const role = asset.role || "anim_asset";
      const tag = asset.tag || asset.symbol || "";
      if (Array.isArray(asset.composites) && asset.composites.length) {
        return renderCompositeEffectAsset(asset, src, role, tag, index, total);
      }
      const plan = framePlanForRecord(asset);
      if (isGen2TileSheetAsset(asset) && plan) {
        return renderTileSheetEffectAsset(asset, src, role, tag, index, total);
      }
      if (plan && plan.count > 1) {
        const scale = effectFrameScale(asset, plan);
        return `
          <span
            class="battle-scene-effect-asset battle-scene-effect-frame battle-scene-effect-asset-${escapeAttribute(role)}"
            aria-hidden="true"
            data-battle-anim-tag="${escapeAttribute(tag)}"
            ${effectAssetStateAttributes(asset)}
            ${frameDataAttributes(plan, plan.frameMs)}
            style="${escapeAttribute(`${frameStyle(asset, src, { width: plan.width * scale, height: plan.height * scale })};--battle-effect-index:${index};--battle-effect-total:${total}${effectAssetTimingStyle(asset)}`)}"
          ></span>
        `;
      }
      return `
        <img
          class="battle-scene-effect-asset battle-scene-effect-asset-${escapeAttribute(role)}"
          src="${escapeAttribute(src)}"
          alt=""
          loading="eager"
          decoding="sync"
          data-battle-anim-tag="${escapeAttribute(tag)}"
          ${effectAssetStateAttributes(asset)}
          style="--battle-effect-index:${index};--battle-effect-total:${total}${effectAssetTimingStyle(asset)};"
        />
      `;
    }

    function effectAssetStateAttributes(asset) {
      const events = Array.isArray(asset?.stateEvents) ? asset.stateEvents : [];
      if (!events.length) return "";
      const encoded = events.map((event) => [
        event.type || "",
        Number(event.frame || 0),
        Number(event.timeMs || 0),
        event.state === null || event.state === undefined ? "" : Number(event.state || 0)
      ].join(":")).join("|");
      return `data-battle-state-events="${escapeAttribute(encoded)}"`;
    }

    function effectAssetTimingStyle(asset) {
      const delay = Math.max(0, Number(asset?.startMs || 0));
      const duration = Math.max(0, Number(asset?.durationMs || 0));
      const firstStateEvent = Array.isArray(asset?.stateEvents) ? asset.stateEvents[0] : null;
      const stateDelay = firstStateEvent ? Math.max(0, Number(firstStateEvent.timeMs || 0)) : 0;
      const position = asset?.position || null;
      const declarations = [];
      if (delay) declarations.push(`--battle-effect-delay:${Math.round(delay)}ms`);
      if (duration) declarations.push(`--battle-effect-asset-duration:${Math.round(duration)}ms`);
      if (stateDelay) declarations.push(`--battle-effect-state-delay:${Math.round(stateDelay)}ms`);
      if (position) {
        declarations.push(`--battle-effect-left:${Number(position.leftPercent || 0)}%`);
        declarations.push(`--battle-effect-top:${Number(position.topPercent || 0)}%`);
      }
      return declarations.length ? `;${declarations.join(";")}` : "";
    }

    function renderCompositeEffectAsset(asset, src, role, tag, index, total) {
      const composites = asset.composites.slice(0, 8);
      const nodes = composites.map((composite, compositeIndex) => renderCompositeSequence(asset, composite, src, compositeIndex)).join("");
      return `
        <span
          class="battle-scene-effect-asset battle-scene-effect-composite battle-scene-effect-asset-${escapeAttribute(role)}"
          aria-hidden="true"
          data-battle-anim-tag="${escapeAttribute(tag)}"
          ${effectAssetStateAttributes(asset)}
          style="--battle-effect-index:${index};--battle-effect-total:${total}${effectAssetTimingStyle(asset)};"
        >${nodes}</span>
      `;
    }

    function renderCompositeSequence(asset, composite, src, compositeIndex) {
      const scale = compositeScale(asset, composite);
      const bounds = composite.bounds || { width: 8, height: 8 };
      const frames = Array.isArray(composite.frames) ? composite.frames : [];
      const frameNodes = frames.map((frame, frameIndex) => renderCompositeFrame(asset, composite, frame, src, scale, frameIndex)).join("");
      const durations = compositeFrameDurations(composite);
      const param = battleAnimObjectParam(composite.args || asset.args);
      const motion = gen2BattleAnimFunctionProfile(composite.callback || asset.callback, param);
      const offset = compositeIndex * 4;
      return `
        <span
          class="battle-scene-oam-composite"
          data-battle-composite-count="${Math.max(1, frames.length)}"
          data-battle-composite-ms="${Math.max(35, Number(composite.frame_ms || 70))}"
          ${durations.length ? `data-battle-composite-durations="${escapeAttribute(durations.join(","))}"` : ""}
          ${motion ? `data-battle-oam-motion="${escapeAttribute(motion.callback)}" data-battle-oam-param="${motion.param}"` : ""}
          style="width:${Math.round(Number(bounds.width || 8) * scale)}px;height:${Math.round(Number(bounds.height || 8) * scale)}px;left:${offset}px;top:${offset}px;"
        >${frameNodes}</span>
      `;
    }

    function renderTileSheetEffectAsset(asset, src, role, tag, index, total) {
      const style = `${tileFrameStyle(asset, src, 0, effectFrameScale(asset, framePlanForRecord(asset)))};--battle-effect-index:${index};--battle-effect-total:${total}${effectAssetTimingStyle(asset)}`;
      return `
        <span
          class="battle-scene-effect-asset battle-scene-effect-frame battle-scene-effect-tile-frame battle-scene-effect-asset-${escapeAttribute(role)}"
          aria-hidden="true"
          data-battle-anim-tag="${escapeAttribute(tag)}"
          ${effectAssetStateAttributes(asset)}
          style="${escapeAttribute(style)}"
        ></span>
      `;
    }

    function renderCompositeFrame(asset, composite, frame, src, scale, frameIndex) {
      const tiles = Array.isArray(frame.tiles) ? frame.tiles : [];
      const tileNodes = tiles.map((tile) => `
        <span class="battle-scene-oam-tile" style="${escapeAttribute(tileStyle(asset, composite, tile, src, scale))}"></span>
      `).join("");
      return `<span class="battle-scene-oam-frame" data-battle-composite-frame="${frameIndex}" ${frameIndex ? "hidden" : ""}>${tileNodes}</span>`;
    }

    function renderBottomPanel(genProfile) {
      if (state.menuMode === "fight") return renderFightPanel(genProfile);
      if (state.menuMode === "run") return renderRunConfirmPanel(genProfile);
      if (state.menuMode === "command") return renderCommandPanel(genProfile);
      return renderDialogPanel(genProfile, state.message);
    }

    function renderDialogPanel(genProfile, message) {
      const messageHtml = renderBattleText(message || genProfile.defaultMessage, generation);
      if (generation === 2) {
        return gen2BattleScene.renderDialogPanel({ messageHtml });
      }
      return `
        <div class="battle-scene-bottom battle-scene-dialog-panel">
          <div class="battle-scene-dialog">
            <span class="battle-scene-turn">${state.turn ? `TURN ${state.turn}` : genProfile.title}</span>
            <strong class="battle-scene-message">${messageHtml}</strong>
            <span class="battle-scene-prompt" aria-hidden="true"></span>
          </div>
        </div>
      `;
    }

    function renderCommandPanel(genProfile) {
      const activeName = pokemonDisplayName(state.p1.nickname || state.p1.species || "POKéMON", generation);
      const question = genProfile.commandQuestion.replace("{pokemon}", activeName);
      const questionText = genProfile.uppercaseText ? question.toUpperCase() : question;
      const disabled = state.locked || !state.request;
      const buttonsHtml = genProfile.commandLabels.map((item, index) => `
        <button type="button" data-battle-visual-menu="${escapeAttribute(item.key)}" ${disabled ? "disabled" : ""}>
          <span class="battle-scene-cursor">${index === 0 ? "▶" : ""}</span>${renderBattleText(item.label, generation)}
        </button>
      `).join("");
      if (generation === 2) {
        return gen2BattleScene.renderCommandPanel({
          buttonsHtml,
          messageHtml: renderBattleText(questionText, generation)
        });
      }
      return `
        <div class="battle-scene-bottom battle-scene-command-panel">
          <div class="battle-scene-dialog">
            <strong class="battle-scene-message">${renderBattleText(questionText, generation)}</strong>
            <span class="battle-scene-prompt" aria-hidden="true"></span>
          </div>
          <div class="battle-scene-command-menu" role="group" aria-label="Menu de batalha">
            ${buttonsHtml}
          </div>
        </div>
      `;
    }

    function renderFightPanel(genProfile) {
      const groups = actionGroupsFromRequest(state.request);
      const moves = groups.moves.length ? groups.moves : [{ action: "move 1", label: "----", pp: 0, maxpp: 0, type: "--", disabled: true }];
      const firstAvailable = moves.find((move) => !move.disabled) || moves[0];
      const movesHtml = moves.map((move, index) => `
        <button type="button" data-battle-visual-action="${escapeAttribute(move.action)}" ${move.disabled || state.locked ? "disabled" : ""}>
          <span class="battle-scene-cursor">${index === 0 ? "▶" : ""}</span>
          <span>${renderBattleText(humanizeMoveName(move.label, generation), generation)}</span>
          <small>${escapeHtml(genProfile.ppLabel)} ${Number(move.pp || 0)}/${Number(move.maxpp || 0)}</small>
        </button>
      `).join("");
      const detailHtml = `
        <span>${renderBattleText(genProfile.moveTypeLabel, generation)}</span>
        <strong>${renderBattleText(String(firstAvailable?.type || "--").toUpperCase(), generation)}</strong>
        <button type="button" data-battle-visual-menu="command">${renderBattleText(genProfile.backLabel, generation)}</button>
      `;
      if (generation === 2) {
        return gen2BattleScene.renderFightPanel({ detailHtml, movesHtml });
      }
      return `
        <div class="battle-scene-bottom battle-scene-fight-panel">
          <div class="battle-scene-move-menu" role="group" aria-label="Golpes">
            ${movesHtml}
          </div>
          <div class="battle-scene-move-detail">
            ${detailHtml}
          </div>
        </div>
      `;
    }

    function renderRunConfirmPanel(genProfile) {
      const message = genProfile.uppercaseText ? "FORFEIT THIS LINK BATTLE?" : "Forfeit this link battle?";
      const buttonsHtml = `
        <button type="button" data-battle-visual-menu="run-yes">${renderBattleText("YES", generation)}</button>
        <button type="button" data-battle-visual-menu="command">${renderBattleText("NO", generation)}</button>
      `;
      if (generation === 2) {
        return gen2BattleScene.renderRunConfirmPanel({
          buttonsHtml,
          messageHtml: renderBattleText(message, generation)
        });
      }
      return `
        <div class="battle-scene-bottom battle-scene-run-panel">
          <div class="battle-scene-dialog">
            <strong class="battle-scene-message">${renderBattleText(message, generation)}</strong>
          </div>
          <div class="battle-scene-confirm-menu">
            ${buttonsHtml}
          </div>
        </div>
      `;
    }

    function renderOverlay(genProfile) {
      if (state.menuMode === "party") return renderPartyOverlay(genProfile);
      if (state.menuMode === "bag") return renderBagOverlay(genProfile);
      return "";
    }

    function renderPartyOverlay(genProfile) {
      const entries = partyEntriesForRender();
      const groups = actionGroupsFromRequest(state.request);
      const switchByIndex = new Map(groups.switches.map((entry) => [entry.index, entry]));
      const rows = Array.from({ length: 6 }, (_, index) => {
        const entry = entries[index] || switchByIndex.get(index);
        if (!entry) {
          return `<div class="battle-scene-party-row is-empty"><span class="battle-scene-party-icon"></span><strong>${renderBattleText("---", generation)}</strong><small>${renderBattleText("EMPTY", generation)}</small></div>`;
        }
        const switchEntry = switchByIndex.get(index);
        const disabled = state.locked || !switchEntry || switchEntry.disabled;
        const condition = parseCondition(entry.condition || "", { currentHp: entry.currentHp || 0, maxHp: entry.maxHp || 0, status: entry.status || "ok" });
        const percent = hpPercent(condition);
        const label = pokemonDisplayName(entry.name || entry.nickname || entry.species || `Pokémon ${index + 1}`, generation);
        return `
          <button type="button" class="battle-scene-party-row${entry.active ? " is-active" : ""}${entry.fainted || switchEntry?.fainted ? " is-fainted" : ""}" data-battle-visual-action="${switchEntry ? escapeAttribute(switchEntry.action) : ""}" ${disabled ? "disabled" : ""}>
            <span class="battle-scene-party-icon"></span>
            <strong>${renderBattleText(label, generation)}</strong>
            <small>${renderBattleText(entry.level ? `Lv${entry.level}` : levelFromDetails(entry.details) || "", generation)}</small>
            ${renderStatusBadge(condition.status)}
            <span class="battle-scene-party-hp"><i class="${hpClass(percent)}" style="width:${percent}%"></i></span>
            <em>${renderBattleText(condition.maxHp ? `${condition.currentHp}/${condition.maxHp}` : entry.condition || "", generation)}</em>
          </button>
        `;
      }).join("");
      return `
        <div class="battle-scene-overlay battle-scene-party-overlay">
          <div class="battle-scene-overlay-head">
            <strong>${renderBattleText(genProfile.partyTitle, generation)}</strong>
            <button type="button" data-battle-visual-menu="command">${renderBattleText(genProfile.backLabel, generation)}</button>
          </div>
          <div class="battle-scene-party-list">${rows}</div>
          <div class="battle-scene-overlay-footer">${renderBattleText(groups.forcedSwitch ? "Choose a POKéMON." : "Choose a POKéMON or cancel.", generation)}</div>
        </div>
      `;
    }

    function renderBagOverlay(genProfile) {
      const grouped = groupedInventory(genProfile);
      const pocket = selectedPocket(genProfile, grouped);
      const entries = grouped[pocket] || [];
      const selected = state.selectedBagItem;
      const pocketTabs = genProfile.pockets.map((item) => `
        <button type="button" class="${item.key === pocket ? "is-active" : ""}" data-battle-visual-pocket="${escapeAttribute(item.key)}">${renderBattleText(item.label, generation)}</button>
      `).join("");
      const rows = entries.length ? entries.slice(0, generation === 3 ? 8 : 6).map((entry, index) => `
        <button type="button" class="battle-scene-bag-row${selected?.item_id === entry.item_id && selected?.pocket_name === entry.pocket_name ? " is-selected" : ""}" data-battle-visual-item="${index}">
          <span class="battle-scene-cursor">${index === 0 ? "▶" : ""}</span>
          <strong>${renderBattleText(itemDisplayName(entry, generation), generation)}</strong>
          <small>${renderBattleText(`×${Number(entry.quantity || 0)}`, generation)}</small>
        </button>
      `).join("") : `<div class="battle-scene-bag-empty">${renderBattleText(generation <= 2 ? "NO ITEMS." : "No items.", generation)}</div>`;
      return `
        <div class="battle-scene-overlay battle-scene-bag-overlay">
          <div class="battle-scene-overlay-head">
            <strong>${renderBattleText(genProfile.bagTitle, generation)}</strong>
            <button type="button" data-battle-visual-menu="command">${renderBattleText(genProfile.backLabel, generation)}</button>
          </div>
          <div class="battle-scene-bag-shell">
            <div class="battle-scene-pocket-tabs">${pocketTabs}</div>
            <div class="battle-scene-bag-list">${rows}</div>
            <div class="battle-scene-bag-art" aria-hidden="true"><span></span></div>
            <div class="battle-scene-bag-detail">
              <strong>${renderBattleText(selected ? itemDisplayName(selected, generation) : genProfile.bagTitle, generation)}</strong>
              <span>${renderBattleText(selected ? itemDescription(selected, genProfile) : "Choose an item pocket.", generation)}</span>
              <button type="button" data-battle-visual-menu="bag-use" ${selected ? "" : "disabled"}>${renderBattleText("USE", generation)}</button>
            </div>
          </div>
        </div>
      `;
    }

    function partyEntriesForRender() {
      if (state.request?.side?.pokemon) {
        return state.request.side.pokemon.map((pokemon, index) => {
          const ident = parseBattleIdent(pokemon.ident || "");
          const details = String(pokemon.details || "");
          const condition = parseCondition(pokemon.condition || "");
          return {
            index,
            ident: pokemon.ident,
            name: ident.nickname || details.split(",")[0],
            details,
            condition: pokemon.condition || "",
            currentHp: condition.currentHp,
            maxHp: condition.maxHp,
            status: condition.status,
            active: Boolean(pokemon.active),
            fainted: condition.status === "fnt" || condition.currentHp <= 0
          };
        });
      }
      return (state.context.party || []).filter((pokemon) => !pokemon.is_egg).slice(0, 6).map((pokemon, index) => ({
        index,
        name: pokemon.nickname || pokemon.species_name || pokemon.species || pokemon.name,
        species: pokemon.species_name || pokemon.species,
        level: pokemon.level,
        currentHp: pokemon.current_hp || pokemon.hp || pokemon.stats?.hp || 0,
        maxHp: pokemon.max_hp || pokemon.maxHp || pokemon.stats?.hp || 0,
        status: pokemon.status || "ok",
        condition: pokemon.condition || "",
        active: index === 0 && state.p1.species && normalizeSpeciesKey(state.p1.species) === normalizeSpeciesKey(pokemon.species_name || pokemon.species),
        fainted: normalizeStatus(pokemon.status) === "fnt"
      }));
    }

    function groupedInventory(genProfile) {
      const groups = {};
      for (const pocket of genProfile.pockets) groups[pocket.key] = [];
      for (const entry of state.context.inventory || []) {
        if (entry.storage && entry.storage !== "bag") continue;
        if (Number(entry.quantity || 0) <= 0) continue;
        const pocket = generation === 1 ? "all" : pocketKeyForEntry(entry);
        if (!groups[pocket]) groups[pocket] = [];
        groups[pocket].push(entry);
      }
      return groups;
    }

    function selectedPocket(genProfile, grouped) {
      if (state.selectedPocket && grouped[state.selectedPocket]) return state.selectedPocket;
      const firstWithItems = genProfile.pockets.find((pocket) => grouped[pocket.key]?.length);
      return firstWithItems?.key || genProfile.pockets[0]?.key || "all";
    }

    function pocketKeyForEntry(entry) {
      const pocketName = String(entry.pocket_name || "").toLowerCase();
      const category = String(entry.category || "").toLowerCase();
      if (/ball/.test(pocketName) || /ball/.test(category)) return "balls";
      if (/berry|berries/.test(pocketName) || /berry/.test(category)) return "berries";
      if (/tm|hm/.test(pocketName) || /machine/.test(category)) return "tmhm";
      if (/key/.test(pocketName)) return "key_items";
      return "items";
    }

    function itemDisplayName(entry, gen) {
      const name = String(entry?.item_name || entry?.name || `Item #${entry?.item_id || "?"}`);
      return gen <= 2 ? name.toUpperCase() : name;
    }

    function itemDescription(entry, genProfile) {
      if (!entry) return "";
      const category = entry.category ? `${entry.category}. ` : "";
      return `${category}${genProfile.itemBlockedMessage}`;
    }

    function levelFromDetails(details) {
      const match = String(details || "").match(/L(\d+)/i);
      return match ? `Lv${match[1]}` : "";
    }

    function updatePokemonFromSwitch(parsed) {
      const side = parsed.side;
      if (!state[side]) return;
      const genProfile = profile();
      const condition = parseCondition(parsed.condition, state[side]);
      const spriteAsset = spriteAssetFor(side, parsed.species);
      state[side] = {
        ...state[side],
        nickname: parsed.nickname || parsed.species,
        species: parsed.species,
        level: parsed.level,
        ...condition,
        fainted: false,
        sprite: spriteAsset.url,
        spriteRecord: spriteAsset.record
      };
      state.message = side === "p1"
        ? `Go! ${pokemonDisplayName(state[side].nickname, generation)}!`
        : `Foe ${pokemonDisplayName(state[side].nickname, generation)} appeared!`;
      if (genProfile.uppercaseText) state.message = state.message.toUpperCase();
      state.menuMode = "message";
      render();
      animate(side, "is-entering");
    }

    function updateCondition(parsed) {
      const side = parsed.side;
      if (!state[side]) return;
      const condition = parseCondition(parsed.condition, state[side]);
      state[side] = {
        ...state[side],
        ...condition,
        fainted: condition.currentHp <= 0 || condition.status === "fnt"
      };
      const name = pokemonDisplayName(state[side].nickname || parsed.nickname, generation);
      state.message = parsed.event.includes("heal") ? `${name} regained health!` : `${name} took damage!`;
      if (profile().uppercaseText) state.message = state.message.toUpperCase();
      state.menuMode = "message";
      render();
      animate(side, parsed.event.includes("heal") ? "is-healing" : "is-hit");
    }

    function genericMessage(parsed) {
      const targetName = pokemonDisplayName(state[parsed.side]?.nickname || parsed.nickname || "POKéMON", generation);
      const arg1 = humanizeMoveName(parsed.arg1 || parsed.reason || parsed.stat || "", generation);
      const messages = {
        "-crit": "A critical hit!",
        "-supereffective": "It's super effective!",
        "-resisted": "It's not very effective...",
        "-immune": `It doesn't affect ${targetName}!`,
        "-fail": "But it failed!",
        "-blocked": "The move was blocked!",
        "-activate": `${targetName}'s effect activated!`,
        "-start": `${targetName} is affected by ${arg1}!`,
        "-end": `${targetName}'s ${arg1} ended!`,
        "-item": `${targetName} used its item!`,
        "-enditem": `${targetName}'s item was used up!`
      };
      if (parsed.event === "cant") return `${targetName} can't move!`;
      if (parsed.event === "-boost") return `${targetName}'s ${String(parsed.stat || "").toUpperCase()} rose!`;
      if (parsed.event === "-unboost") return `${targetName}'s ${String(parsed.stat || "").toUpperCase()} fell!`;
      return messages[parsed.event] || parsed.raw || "";
    }

    function applyParsed(parsed) {
      if (!parsed) return;
      if (parsed.event === "turn") {
        state.turn = parsed.turn || state.turn;
        state.message = `Turn ${state.turn}`;
        state.menuMode = "message";
        render();
        return;
      }
      if (parsed.event === "request") {
        state.message = parsed.message || profile().waitingMessage;
        render();
        return;
      }
      if (parsed.event === "switch" || parsed.event === "drag") {
        updatePokemonFromSwitch(parsed);
        return;
      }
      if (parsed.event === "move") {
        const side = parsed.side;
        if (state[side]) {
          const moveProfile = profileForMove(parsed.move);
          const visual = effectVisualProfile(moveProfile, parsed.move);
          state.effect = {
            side,
            family: visual.family || "impact",
            label: moveProfile.label || parsed.move,
            commands: moveProfile.commands || [],
            script: moveProfile.script || [],
            assets: visual.assets || [],
            visual
          };
          const actor = pokemonDisplayName(state[side].nickname || parsed.actor, generation);
          state.message = `${actor} used ${humanizeMoveName(parsed.move, generation)}!`;
          if (profile().uppercaseText) state.message = state.message.toUpperCase();
          state.menuMode = "message";
          render();
          animate(side, "is-attacking");
          animateEffect(visual.duration);
        }
        return;
      }
      if (["damage", "-damage", "heal", "-heal"].includes(parsed.event)) {
        updateCondition(parsed);
        return;
      }
      if (parsed.event === "faint") {
        const side = parsed.side;
        if (state[side]) {
          state[side].currentHp = 0;
          state[side].fainted = true;
          state[side].status = "fnt";
          state.message = `${pokemonDisplayName(state[side].nickname || parsed.nickname, generation)} fainted!`;
          if (profile().uppercaseText) state.message = state.message.toUpperCase();
          state.menuMode = "message";
          render();
          animate(side, "is-fainting");
        }
        return;
      }
      if (parsed.event === "-miss") {
        state.message = "The attack missed!";
        if (profile().uppercaseText) state.message = state.message.toUpperCase();
        state.menuMode = "message";
        render();
        animate(parsed.targetSide || parsed.side, "is-evading");
        return;
      }
      if (parsed.event === "-status" || parsed.event === "status") {
        const side = parsed.side;
        if (state[side]) {
          state[side].status = normalizeStatus(parsed.status);
          state.message = `${pokemonDisplayName(state[side].nickname || parsed.nickname, generation)} is ${statusLabel(parsed.status)}!`;
          if (profile().uppercaseText) state.message = state.message.toUpperCase();
          state.menuMode = "message";
          render();
        }
        return;
      }
      if (parsed.event === "-curestatus") {
        const side = parsed.side;
        if (state[side]) {
          state[side].status = "ok";
          state.message = `${pokemonDisplayName(state[side].nickname || parsed.nickname, generation)} became healthy!`;
          if (profile().uppercaseText) state.message = state.message.toUpperCase();
          state.menuMode = "message";
          render();
        }
        return;
      }
      if (parsed.event === "win") {
        state.message = `${parsed.winner} won the battle!`;
        state.menuMode = "message";
        state.locked = true;
        render();
        return;
      }
      const message = genericMessage(parsed);
      if (message) {
        state.message = profile().uppercaseText ? message.toUpperCase() : message;
        state.menuMode = "message";
        render();
      }
    }

    function animate(side, className) {
      animationQueue = animationQueue.then(() => {
        const node = element.querySelector(`[data-scene-side="${side}"]`);
        if (!node) return null;
        node.classList.remove(className);
        void node.offsetWidth;
        node.classList.add(className);
        return new Promise((resolve) => {
          window.setTimeout(() => {
            node.classList.remove(className);
            resolve();
          }, 460);
        });
      });
    }

    function animateEffect(duration = 520) {
      animationQueue = animationQueue.then(() => new Promise((resolve) => {
        window.setTimeout(() => {
          state.effect = null;
          render();
          resolve();
        }, duration);
      }));
    }

    function reset(nextGeneration) {
      generation = Number(nextGeneration || getGeneration?.() || generation || 1);
      state.p1 = emptyPokemon("p1");
      state.p2 = emptyPokemon("p2");
      state.turn = 0;
      state.message = profile().defaultMessage;
      state.effect = null;
      state.request = null;
      state.menuMode = "message";
      state.locked = false;
      state.selectedPocket = "";
      state.selectedBagItem = null;
      render();
      loadManifest();
      loadAnimationMap();
      loadPokemonFrameAnimations();
    }

    function pushLog(line) {
      const parsed = parseBattleLogLine(line);
      applyParsed(parsed);
    }

    function setRequest(request) {
      state.request = request || null;
      state.locked = false;
      state.selectedBagItem = null;
      if (request?.forceSwitch) {
        state.menuMode = "party";
        state.message = "Choose a POKéMON.";
      } else if (request) {
        state.menuMode = "command";
        state.message = profile().commandQuestion.replace("{pokemon}", pokemonDisplayName(state.p1.nickname || state.p1.species || "POKéMON", generation));
      } else {
        state.menuMode = "message";
        state.message = profile().waitingMessage;
      }
      if (request?.side?.pokemon) {
        for (const pokemon of request.side.pokemon) {
          if (!pokemon.active) continue;
          const side = String(pokemon.ident || "").slice(0, 2) || "p1";
          if (!state[side]) continue;
          const species = String(pokemon.details || "").split(",")[0].trim() || state[side].species;
          const condition = parseCondition(pokemon.condition, state[side]);
          const spriteAsset = spriteAssetFor(side, species);
          state[side] = {
            ...state[side],
            species,
            nickname: String(pokemon.ident || "").split(":").slice(1).join(":").trim() || species,
            ...condition,
            sprite: spriteAsset.url,
            spriteRecord: spriteAsset.record,
            fainted: condition.currentHp <= 0 || condition.status === "fnt"
          };
        }
      }
      render();
    }

    function setTrainerContext(context = {}) {
      state.context = {
        playerName: context.playerName || state.context.playerName,
        party: Array.isArray(context.party) ? context.party : state.context.party,
        inventory: Array.isArray(context.inventory) ? context.inventory : state.context.inventory
      };
      if (state.menuMode === "party" || state.menuMode === "bag") render();
    }

    function setWaiting(message) {
      state.locked = true;
      state.request = null;
      state.menuMode = "message";
      state.message = message || profile().waitingMessage;
      render();
    }

    function handleSceneClick(event) {
      const actionButton = event.target.closest("[data-battle-visual-action]");
      if (actionButton && element.contains(actionButton)) {
        event.preventDefault();
        if (actionButton.disabled || state.locked) return;
        const action = actionButton.dataset.battleVisualAction;
        if (!action) return;
        dispatchAction(action);
        return;
      }

      const pocketButton = event.target.closest("[data-battle-visual-pocket]");
      if (pocketButton && element.contains(pocketButton)) {
        event.preventDefault();
        state.selectedPocket = pocketButton.dataset.battleVisualPocket || "";
        state.selectedBagItem = null;
        render();
        return;
      }

      const itemButton = event.target.closest("[data-battle-visual-item]");
      if (itemButton && element.contains(itemButton)) {
        event.preventDefault();
        const genProfile = profile();
        const grouped = groupedInventory(genProfile);
        const pocket = selectedPocket(genProfile, grouped);
        state.selectedBagItem = (grouped[pocket] || [])[Number(itemButton.dataset.battleVisualItem || 0)] || null;
        render();
        return;
      }

      const menuButton = event.target.closest("[data-battle-visual-menu]");
      if (!menuButton || !element.contains(menuButton)) return;
      event.preventDefault();
      if (menuButton.disabled) return;
      const menu = menuButton.dataset.battleVisualMenu;
      if (menu === "fight" || menu === "party" || menu === "bag" || menu === "run") {
        if (!state.request && menu !== "run") {
          state.message = profile().waitingMessage;
          state.menuMode = "message";
        } else {
          state.menuMode = menu;
        }
        render();
        return;
      }
      if (menu === "command") {
        state.menuMode = state.request ? "command" : "message";
        render();
        return;
      }
      if (menu === "run-yes") {
        dispatchAction("forfeit");
        return;
      }
      if (menu === "bag-use") {
        state.message = profile().itemBlockedMessage;
        if (profile().uppercaseText) state.message = state.message.toUpperCase();
        state.menuMode = "message";
        render();
      }
    }

    function dispatchAction(action) {
      const label = actionLabel(action);
      setWaiting(label ? `${label} selected. ${profile().waitingMessage}` : profile().waitingMessage);
      element.dispatchEvent(new CustomEvent("pokecable:battle-action", {
        bubbles: true,
        detail: { action }
      }));
    }

    function actionLabel(action) {
      if (action === "forfeit") return "RUN";
      const groups = actionGroupsFromRequest(state.request);
      const move = groups.moves.find((entry) => entry.action === action);
      if (move) return humanizeMoveName(move.label, generation);
      const switchEntry = groups.switches.find((entry) => entry.action === action);
      if (switchEntry) return pokemonDisplayName(switchEntry.name, generation);
      return action;
    }

    element.addEventListener("click", handleSceneClick);
    reset(generation);
    return {
      reset,
      pushLog,
      setRequest,
      setTrainerContext,
      setWaiting,
      parseBattleLogLine,
      normalizeSpeciesKey
    };
  }

  function tileSheetPosition(tileIndex, columns, rows) {
    const count = Math.max(1, columns * rows);
    const safeIndex = ((Number(tileIndex || 0) % count) + count) % count;
    const column = safeIndex % columns;
    const row = Math.floor(safeIndex / columns);
    return {
      x: columns > 1 ? (column / (columns - 1)) * 100 : 0,
      y: rows > 1 ? (row / (rows - 1)) * 100 : 0
    };
  }

  function tileStyle(asset, composite, tile, sourceUrl, scale) {
    const plan = framePlanForRecord(asset);
    const columns = Math.max(1, plan?.columns || 1);
    const rows = Math.max(1, plan?.rows || 1);
    const tileSize = Number(composite?.tile_size || 8);
    const bounds = composite?.bounds || { x: 0, y: 0 };
    const position = tileSheetPosition(tile.tile, columns, rows);
    const transforms = [];
    if (tile.xflip) transforms.push("scaleX(-1)");
    if (tile.yflip) transforms.push("scaleY(-1)");
    return [
      `left:${Math.round((Number(tile.x || 0) - Number(bounds.x || 0)) * scale)}px`,
      `top:${Math.round((Number(tile.y || 0) - Number(bounds.y || 0)) * scale)}px`,
      `width:${Math.round(tileSize * scale)}px`,
      `height:${Math.round(tileSize * scale)}px`,
      `background-image:url('${escapeAttribute(sourceUrl)}')`,
      `background-size:${columns * 100}% ${rows * 100}%`,
      `background-position:${position.x}% ${position.y}%`,
      transforms.length ? `transform:${transforms.join(" ")}` : ""
    ].filter(Boolean).join(";");
  }

  function isGen2TileSheetAsset(asset) {
    const frame = asset?.frame || {};
    return String(asset?.role || "") === "gen2_anim_gfx"
      || (String(asset?.path || "").startsWith("gen2/") && String(frame.layout || "") === "gb_tile_sheet");
  }

  function tileFrameStyle(asset, sourceUrl, tileIndex = 0, scale = 1) {
    const plan = framePlanForRecord(asset);
    if (!plan) return "";
    const columns = Math.max(1, plan.columns || 1);
    const rows = Math.max(1, plan.rows || 1);
    const position = tileSheetPosition(tileIndex, columns, rows);
    return [
      `width:${Math.round(plan.width * scale)}px`,
      `height:${Math.round(plan.height * scale)}px`,
      `background-image:url('${escapeAttribute(sourceUrl)}')`,
      `background-size:${columns * 100}% ${rows * 100}%`,
      `background-position:${position.x}% ${position.y}%`
    ].join(";");
  }

  function frameDurationMs(frame, fallbackMs = 70) {
    const durationFrames = Number(frame?.duration_frames || 0);
    if (durationFrames > 0) return Math.max(16, Math.round(durationFrames * 1000 / 60));
    return Math.max(35, Number(fallbackMs || 70));
  }

  function compositeFrameDurations(composite) {
    const frames = Array.isArray(composite?.frames) ? composite.frames : [];
    const fallbackMs = Number(composite?.frame_ms || 70);
    return frames.map((frame) => frameDurationMs(frame, fallbackMs));
  }

  function parseBattleAnimNumber(value) {
    const raw = String(value ?? "").trim().toLowerCase();
    if (!raw) return 0;
    const parsed = raw.startsWith("$") ? Number.parseInt(raw.slice(1), 16)
      : raw.startsWith("0x") ? Number.parseInt(raw, 16)
        : Number(raw);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function battleAnimObjectParam(args) {
    if (Array.isArray(args)) return parseBattleAnimNumber(args[2]);
    return parseBattleAnimNumber(args);
  }

  function gen2BattleAnimFunctionProfile(callback, param = 0) {
    const name = String(callback || "").toUpperCase();
    const value = Number(param || 0);
    const make = (steps, frameMs = 42) => ({ callback: name, param: value, frameMs, steps });
    if (!name || name === "BATTLE_ANIM_FUNC_NULL") return null;
    if (name.includes("MOVE_IN_CIRCLE")) {
      const radius = Math.max(2, value & 0x7f);
      const start = value & 0x80 ? Math.PI : 0;
      const steps = Array.from({ length: 9 }, (_, index) => {
        const angle = start + (Math.PI * 2 * index) / 8;
        return {
          transform: `translate(${Math.round(Math.cos(angle) * radius)}px, ${Math.round(Math.sin(angle) * radius)}px)`
        };
      });
      return make(steps, 34);
    }
    if (name.includes("SPEED_LINE")) {
      const direction = value & 0x80 ? -1 : 1;
      return make([0, 2, 4, 6, 8, 10].map((distance) => ({
        transform: `translateX(${direction * distance}px)`,
        opacity: distance >= 10 ? "0" : "1"
      })), 28);
    }
    if (name.includes("EMBER")) {
      const mode = (value >> 4) & 0xf;
      const speed = Math.max(2, value & 0xf);
      if (mode === 1) {
        return make([
          { transform: "translate(0, 0)", opacity: "1" },
          { transform: `translate(${speed * 4}px, ${-speed * 3}px)`, opacity: "1" },
          { transform: `translate(${speed * 8}px, ${-speed * 6}px)`, opacity: "0.65" },
          { transform: `translate(${speed * 11}px, ${-speed * 8}px)`, opacity: "0" }
        ], 36);
      }
      if (mode === 3) {
        return make([
          { transform: "translate(0, 0) scale(1)" },
          { transform: "translate(1px, -2px) scale(1.1)" },
          { transform: "translate(-1px, 1px) scale(0.95)" },
          { transform: "translate(0, 0) scale(1)" }
        ], 45);
      }
    }
    if (name.includes("FIRE_BLAST")) {
      const fireBlastVectors = {
        1: [0, -1],
        2: [-1, 0],
        3: [1, 0],
        4: [-1, 1],
        5: [1, 1]
      };
      if (value === 7) {
        return make([
          { transform: "translate(0, 0)" },
          { transform: "translate(10px, -5px)" },
          { transform: "translate(20px, -10px)" },
          { transform: "translate(24px, -8px) rotate(45deg)" },
          { transform: "translate(20px, -2px) rotate(90deg)" }
        ], 40);
      }
      const vector = fireBlastVectors[value];
      if (vector) {
        return make([0, 4, 8, 12].map((distance) => ({
          transform: `translate(${vector[0] * distance}px, ${vector[1] * distance}px)`
        })), 38);
      }
    }
    if (name.includes("RAZOR_LEAF")) {
      const radius = Math.max(8, value & 0x3f);
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: `translate(${Math.round(radius * 0.35)}px, ${Math.round(-radius * 0.55)}px) rotate(45deg)` },
        { transform: `translate(${Math.round(radius * 0.75)}px, ${Math.round(-radius * 0.45)}px) rotate(110deg)` },
        { transform: `translate(${Math.round(radius * 1.05)}px, ${Math.round(radius * 0.1)}px) rotate(180deg)` },
        { transform: `translate(${Math.round(radius * 1.25)}px, ${Math.round(radius * 0.35)}px) rotate(240deg)`, opacity: "0" }
      ], 34);
    }
    if (name.includes("SHAKE") || name.includes("KICK")) {
      return make([
        { transform: "translate(0, 0)" },
        { transform: "translate(-3px, 1px)" },
        { transform: "translate(4px, -1px)" },
        { transform: "translate(-2px, 0)" },
        { transform: "translate(0, 0)" }
      ], name.includes("KICK") ? 30 : 24);
    }
    if (name.includes("USER_TO_TARGET_SPIN")) {
      const speed = Math.max(3, value & 0xf);
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: `translate(${speed * 4}px, ${-speed * 2}px) rotate(120deg)` },
        { transform: `translate(${speed * 8}px, ${-speed * 4}px) rotate(240deg)` },
        { transform: `translate(${speed * 12}px, ${-speed * 5}px) rotate(360deg)` }
      ], 34);
    }
    if (name.includes("ABSORB_CIRCLE") || name.includes("CONFUSE_RAY") || name.includes("DIZZY")) {
      const radius = Math.max(8, value & 0x1f);
      return make([
        { transform: `translate(${radius}px, 0)`, opacity: "1" },
        { transform: `translate(0, ${-radius}px)`, opacity: "1" },
        { transform: `translate(${-radius}px, 0)`, opacity: "1" },
        { transform: `translate(0, ${radius}px)`, opacity: "0.8" },
        { transform: `translate(${radius}px, 0)`, opacity: "0" }
      ], 40);
    }
    if (name.includes("ABSORB")) {
      return make([
        { transform: "translate(18px, -10px) scale(0.8)", opacity: "0" },
        { transform: "translate(10px, -6px) scale(1)", opacity: "1" },
        { transform: "translate(3px, -2px) scale(1.08)", opacity: "1" },
        { transform: "translate(0, 0) scale(0.9)", opacity: "0" }
      ], 46);
    }
    if (name.includes("MOVE_UP") || name.includes("FLOAT_UP") || name.includes("RECOVER")) {
      return make([
        { transform: "translateY(10px)", opacity: "0" },
        { transform: "translateY(4px)", opacity: "1" },
        { transform: "translateY(-4px)", opacity: "1" },
        { transform: "translateY(-12px)", opacity: name.includes("RECOVER") ? "1" : "0" }
      ], 44);
    }
    if (name.includes("POWDER")) {
      return make([
        { transform: "translate(0, -4px)", opacity: "0" },
        { transform: "translate(5px, 2px)", opacity: "1" },
        { transform: "translate(-3px, 8px)", opacity: "0.9" },
        { transform: "translate(2px, 14px)", opacity: "0" }
      ], 46);
    }
    if (name.includes("RAIN_SANDSTORM")) {
      return make([
        { transform: "translate(-8px, -14px)", opacity: "0" },
        { transform: "translate(-2px, -4px)", opacity: "1" },
        { transform: "translate(5px, 7px)", opacity: "1" },
        { transform: "translate(12px, 18px)", opacity: "0" }
      ], 34);
    }
    if (name.includes("SPIRAL_DESCENT") || name.includes("POISON_GAS")) {
      return make([
        { transform: "translate(0, -16px) rotate(0deg)", opacity: "0" },
        { transform: "translate(7px, -8px) rotate(80deg)", opacity: "1" },
        { transform: "translate(-6px, 0) rotate(160deg)", opacity: "1" },
        { transform: "translate(4px, 8px) rotate(240deg)", opacity: "0.8" },
        { transform: "translate(0, 16px) rotate(320deg)", opacity: "0" }
      ], 42);
    }
    if (name.includes("STRING") || name.includes("WRAP")) {
      return make([
        { transform: "scaleX(0.35) translateX(-14px)", opacity: "0.75" },
        { transform: "scaleX(0.7) translateX(-6px)", opacity: "1" },
        { transform: "scaleX(1) translateX(0)", opacity: "1" },
        { transform: "scaleX(0.82) translateX(4px)", opacity: "0.85" }
      ], 42);
    }
    if (name.includes("SHINY") || name.includes("METRONOME_SPARKLE") || name.includes("LOCK_ON_MIND_READER")) {
      return make([
        { transform: "scale(0.45) rotate(0deg)", opacity: "0" },
        { transform: "scale(1.05) rotate(45deg)", opacity: "1" },
        { transform: "scale(0.82) rotate(90deg)", opacity: "0.85" },
        { transform: "scale(1.2) rotate(135deg)", opacity: "1" },
        { transform: "scale(0.55) rotate(180deg)", opacity: "0" }
      ], 40);
    }
    if (name.includes("AGILITY") || name.includes("SPEED")) {
      return make([
        { transform: "translateX(-18px)", opacity: "0" },
        { transform: "translateX(-8px)", opacity: "1" },
        { transform: "translateX(8px)", opacity: "1" },
        { transform: "translateX(18px)", opacity: "0" }
      ], 28);
    }
    if (name.includes("GROWTH_SWORDS_DANCE") || name.includes("ENCORE_BELLY_DRUM") || name.includes("SAFEGUARD_PROTECT") || name.includes("CONVERSION") || name.includes("SWAGGER_MORNING_SUN")) {
      return make([
        { transform: "translateY(8px) scale(0.82)", opacity: "0" },
        { transform: "translateY(2px) scale(1)", opacity: "1" },
        { transform: "translateY(-5px) scale(1.14)", opacity: "1" },
        { transform: "translateY(-10px) scale(0.95)", opacity: "0.72" }
      ], 48);
    }
    if (name.includes("HORN") || name.includes("NEEDLE")) {
      const speed = Math.max(3, value & 0xf);
      return make([
        { transform: "translate(0, 0)", opacity: "1" },
        { transform: `translate(${speed * 5}px, ${-speed}px)`, opacity: "1" },
        { transform: `translate(${speed * 10}px, ${-speed * 2}px)`, opacity: "0" }
      ], 32);
    }
    if (name.includes("GUST") || name.includes("RAZOR_WIND")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(8px, -4px) rotate(80deg)" },
        { transform: "translate(16px, 2px) rotate(170deg)" },
        { transform: "translate(24px, -3px) rotate(260deg)" },
        { transform: "translate(30px, 0) rotate(360deg)", opacity: "0" }
      ], 32);
    }
    if (name.includes("SOLAR_BEAM")) {
      return make([
        { transform: "scale(0.5)", opacity: "0.5" },
        { transform: "scale(0.85)", opacity: "1" },
        { transform: "scale(1.15)", opacity: "1" },
        { transform: "scale(0.75)", opacity: "0.7" }
      ], 52);
    }
    if (name.includes("ANCIENT_POWER") || name.includes("ROCK_SMASH")) {
      return make([
        { transform: "translateY(-14px) rotate(0deg)", opacity: "1" },
        { transform: "translateY(0) rotate(18deg)", opacity: "1" },
        { transform: "translate(-5px, 4px) rotate(-16deg)", opacity: "0.75" },
        { transform: "translate(6px, 8px) rotate(28deg)", opacity: "0" }
      ], 38);
    }
    if (name.includes("HIDDEN_POWER")) {
      return make([
        { transform: "scale(0.35) rotate(0deg)", opacity: "0" },
        { transform: "scale(0.85) rotate(90deg)", opacity: "1" },
        { transform: "scale(1.15) rotate(180deg)", opacity: "1" },
        { transform: "scale(1.45) rotate(270deg)", opacity: "0.65" },
        { transform: "scale(1.8) rotate(360deg)", opacity: "0" }
      ], 38);
    }
    if (name.includes("PERISH_SONG") || name.includes("HEAL_BELL_NOTES") || name.includes("SING") || name.includes("SOUND")) {
      return make([
        { transform: "translate(0, 6px) rotate(0deg)", opacity: "0" },
        { transform: "translate(5px, 0) rotate(6deg)", opacity: "1" },
        { transform: "translate(-4px, -8px) rotate(-6deg)", opacity: "1" },
        { transform: "translate(4px, -16px) rotate(4deg)", opacity: "0" }
      ], 58);
    }
    if (name.includes("AMNESIA") || name.includes("PSYCH_UP")) {
      return make([
        { transform: "translateY(8px) scale(0.75)", opacity: "0" },
        { transform: "translateY(2px) scale(1)", opacity: "1" },
        { transform: "translateY(-6px) scale(1.08)", opacity: "1" },
        { transform: "translateY(-14px) scale(0.85)", opacity: "0" }
      ], 50);
    }
    if (name.includes("BITE") || name.includes("CLAMP_ENCORE")) {
      return make([
        { transform: "scale(1.35, 0.35)", opacity: "0.8" },
        { transform: "scale(1, 1)", opacity: "1" },
        { transform: "scale(1.25, 0.45)", opacity: "1" },
        { transform: "scale(0.8, 0.8)", opacity: "0" }
      ], 36);
    }
    if (name.includes("EGG")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(8px, -10px) rotate(18deg)" },
        { transform: "translate(16px, -3px) rotate(-14deg)" },
        { transform: "translate(20px, 4px) rotate(12deg)", opacity: "0" }
      ], 44);
    }
    if (name.includes("SMOKE_FLAME_WHEEL") || name.includes("PRESENT_SMOKESCREEN")) {
      return make([
        { transform: "translate(0, 0) scale(0.65)", opacity: "0" },
        { transform: "translate(-4px, -5px) scale(1)", opacity: "0.9" },
        { transform: "translate(5px, -11px) scale(1.25)", opacity: "0.65" },
        { transform: "translate(0, -18px) scale(1.5)", opacity: "0" }
      ], 52);
    }
    if (name.includes("LEECH_SEED") || name.includes("SPIKES")) {
      return make([
        { transform: "translate(0, -12px)", opacity: "1" },
        { transform: "translate(7px, -4px)", opacity: "1" },
        { transform: "translate(3px, 3px)", opacity: "1" },
        { transform: "translate(0, 7px)", opacity: "0.8" }
      ], 42);
    }
    if (name.includes("WATER_GUN") || name.includes("THUNDER_WAVE") || name.includes("PARALYZED")) {
      const speed = Math.max(3, value & 0xf);
      return make([
        { transform: "translate(0, 0)" },
        { transform: `translate(${speed * 4}px, -3px)` },
        { transform: `translate(${speed * 8}px, 3px)` },
        { transform: `translate(${speed * 12}px, 0)`, opacity: "0" }
      ], 34);
    }
    if (name.includes("THIEF_PAYDAY")) {
      return make([
        { transform: "translate(0, -12px) rotate(0deg)", opacity: "1" },
        { transform: "translate(8px, -5px) rotate(90deg)", opacity: "1" },
        { transform: "translate(15px, 3px) rotate(180deg)", opacity: "0.85" },
        { transform: "translate(19px, 8px) rotate(270deg)", opacity: "0" }
      ], 38);
    }
    if (name.includes("STRENGTH_SEISMIC_TOSS")) {
      return make([
        { transform: "translateY(-20px) scale(0.9)", opacity: "1" },
        { transform: "translateY(-6px) scale(1)", opacity: "1" },
        { transform: "translateY(6px) scale(1.08)", opacity: "1" },
        { transform: "translateY(0) scale(1)", opacity: "0" }
      ], 44);
    }
    if (name.includes("BATON_PASS")) {
      return make([
        { transform: "translate(-16px, 4px)" },
        { transform: "translate(-5px, -6px)" },
        { transform: "translate(7px, -6px)" },
        { transform: "translate(16px, 4px)", opacity: "0" }
      ], 42);
    }
    if (name.includes("BONEMERANG")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(18px, -8px) rotate(160deg)" },
        { transform: "translate(30px, 0) rotate(320deg)" },
        { transform: "translate(12px, 8px) rotate(520deg)" },
        { transform: "translate(0, 0) rotate(720deg)", opacity: "0" }
      ], 36);
    }
    if (name.includes("CURSE")) {
      return make([
        { transform: "translateY(-4px)", opacity: "1" },
        { transform: "translateY(3px)", opacity: "0.75" },
        { transform: "translateY(8px)", opacity: "0.5" },
        { transform: "translateY(12px)", opacity: "0" }
      ], 54);
    }
    if (name.includes("DIG")) {
      return make([
        { transform: "translateY(8px) scaleY(0.6)", opacity: "0" },
        { transform: "translateY(2px) scaleY(1)", opacity: "1" },
        { transform: "translateY(-3px) scaleY(0.85)", opacity: "0.8" },
        { transform: "translateY(5px) scaleY(0.5)", opacity: "0" }
      ], 38);
    }
    if (name.includes("METRONOME_HAND")) {
      return make([
        { transform: "rotate(-18deg)" },
        { transform: "rotate(18deg)" },
        { transform: "rotate(-14deg)" },
        { transform: "rotate(14deg)" },
        { transform: "rotate(0deg)" }
      ], 44);
    }
    if (name.includes("RAPID_SPIN")) {
      return make([
        { transform: "rotate(0deg) scale(1)" },
        { transform: "rotate(180deg) scale(1.05)" },
        { transform: "rotate(360deg) scale(1)" },
        { transform: "rotate(540deg) scale(1.05)" },
        { transform: "rotate(720deg) scale(1)", opacity: "0" }
      ], 28);
    }
    if (name.includes("SACRED_FIRE") || name.includes("SKY_ATTACK")) {
      return make([
        { transform: "translate(0, 10px) scale(0.75)", opacity: "0" },
        { transform: "translate(8px, -2px) scale(1)", opacity: "1" },
        { transform: "translate(18px, -12px) scale(1.18)", opacity: "1" },
        { transform: "translate(28px, -20px) scale(0.95)", opacity: "0" }
      ], 36);
    }
    if (name.includes("PETAL_DANCE") || name.includes("COTTON")) {
      return make([
        { transform: "translate(0, 0) rotate(0deg)" },
        { transform: "translate(7px, -8px) rotate(70deg)" },
        { transform: "translate(-5px, -13px) rotate(140deg)" },
        { transform: "translate(4px, -18px) rotate(220deg)", opacity: "0" }
      ], 44);
    }
    if (name.includes("USER_TO_TARGET") || name.includes("THROW_TO_TARGET")) {
      const speed = Math.max(2, value & 0xf);
      return make([
        { transform: "translate(0, 0)", opacity: "1" },
        { transform: `translate(${speed * 5}px, ${-speed * 2}px)`, opacity: "1" },
        { transform: `translate(${speed * 10}px, ${-speed * 4}px)`, opacity: name.includes("DISAPPEAR") ? "0" : "1" }
      ], 34);
    }
    if (name.includes("WAVE_TO_TARGET")) {
      const speed = Math.max(3, value & 0xf);
      return make([
        { transform: "translate(0, 0)" },
        { transform: `translate(${speed * 3}px, -6px)` },
        { transform: `translate(${speed * 6}px, 5px)` },
        { transform: `translate(${speed * 9}px, -4px)` },
        { transform: `translate(${speed * 12}px, 0)` }
      ], 36);
    }
    if (name.includes("DROP")) {
      return make([
        { transform: "translateY(-18px)" },
        { transform: "translateY(0)" },
        { transform: "translateY(-6px)" },
        { transform: "translateY(0)" }
      ], 42);
    }
    if (name.includes("BUBBLE")) {
      return make([
        { transform: "translate(0, 0) scale(1)" },
        { transform: "translate(8px, -5px) scale(1.08)" },
        { transform: "translate(16px, -9px) scale(0.95)" },
        { transform: "translate(24px, -14px) scale(1.1)" }
      ], 42);
    }
    if (name.includes("SURF")) {
      return make([
        { transform: "translateY(12px)" },
        { transform: "translateY(4px)" },
        { transform: "translateY(-3px)" },
        { transform: "translateY(6px)" },
        { transform: "translateY(16px)", opacity: "0" }
      ], 48);
    }
    return null;
  }

  function compositeScale(asset, composite) {
    const role = String(asset?.role || "");
    const bounds = composite?.bounds || {};
    const shorter = Math.max(1, Math.min(Number(bounds.width || 8), Number(bounds.height || 8)));
    if (role === "gen1_tileset" || role === "gen2_anim_gfx") return Math.max(2, Math.min(4, 34 / shorter));
    return Math.max(1, Math.min(3, 40 / shorter));
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/`/g, "&#96;");
  }

  return {
    createBattleSceneController,
    normalizeSpeciesKey,
    normalizeAssetSpeciesKey,
    normalizeMoveKey,
    animationFamilyFromMove,
    battleEffectBackgroundAssetForMove,
    pokemonSpriteFramePlaybackForRecord,
    pokemonSpriteMotionProfile,
    gen2BattleLayout,
    gen2BattleCssVariables,
    gen2BattleAnimTimeline,
    gen2HpBarPixels,
    gen2HpClassForPixels,
    framePlanForRecord,
    battleProfileForGeneration,
    battleUiAssetsForGeneration,
    battleUiAssetUrl,
    battleTextAssetsForGeneration,
    renderBattleText,
    actionGroupsFromRequest,
    effectVisualProfile,
    effectAssetsForProfile,
    gen2BattleAnimFunctionProfile,
    humanizeMoveName,
    parseBattleIdent,
    parseBattleLogLine,
    parseCondition,
    compositeFrameDurations,
    isGen2TileSheetAsset,
    tileFrameStyle,
    tileSheetPosition,
    tileStyle,
    compositeScale
  };
});
