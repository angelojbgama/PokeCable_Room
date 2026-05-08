(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.POKECABLE_BATTLE_SCENE = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : window, function () {
  const MANIFEST_URL = "/generated/battle-assets/manifest.json";
  const ANIMATION_MAP_URL = "/generated/battle-assets/animation-map.json";
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
    2: {
      generation: 2,
      baseWidth: 160,
      baseHeight: 144,
      title: "GEN 2 LINK BATTLE",
      commandQuestion: "What will {pokemon} do?",
      defaultMessage: "Waiting for battle.",
      waitingMessage: "Waiting for the other player.",
      itemBlockedMessage: "Items can't be used here!",
      commandLabels: [
        { key: "fight", label: "FIGHT" },
        { key: "party", label: "<PKMN>" },
        { key: "bag", label: "PACK" },
        { key: "run", label: "RUN" }
      ],
      bagTitle: "PACK",
      partyTitle: "POKéMON",
      moveTypeLabel: "TYPE",
      ppLabel: "PP",
      cancelLabel: "CANCEL",
      backLabel: "BACK",
      enemyShowsHpText: false,
      uppercaseText: true,
      pockets: [
        { key: "items", label: "ITEM" },
        { key: "balls", label: "BALL" },
        { key: "key_items", label: "KEY" },
        { key: "tmhm", label: "TM/HM" }
      ]
    },
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

  function battleProfileForGeneration(generation) {
    return BATTLE_PROFILES[Number(generation)] || BATTLE_PROFILES[1];
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
    const assets = Array.isArray(profile?.assets) ? profile.assets.filter((asset) => asset?.path) : [];
    const logic = profile?.logic || {};
    const waitFrames = Number(logic.total_wait_frames || logic.total_delay_frames || 0);
    const objectSignals = [
      assets.length,
      Array.isArray(logic.objects) ? logic.objects.length : 0,
      Array.isArray(logic.sprites) ? logic.sprites.length : 0,
      Number(profile?.command_count || commands.length || 1)
    ];
    const family = profile?.family || animationFamilyFromMove(moveName);
    const count = Math.max(...objectSignals, 1);
    const renderedAssetCount = Math.min(12, assets.length);
    return {
      family,
      duration: Math.max(440, Math.min(1800, 320 + Number(profile?.command_count || count) * 46 + waitFrames * 8)),
      objectCount: Math.max(renderedAssetCount || 1, Math.min(12, count || 1)),
      assets: assets.slice(0, 12),
      flash: ["flash", "electric", "psychic", "explosion", "ice"].includes(family) || /bgeffect|blend|alpha|flash|palette|monbg/.test(commandText),
      shake: ["ground", "rock", "explosion", "impact"].includes(family) || /shake|earthquake|magnitude/.test(commandText),
      background: /bgeffect|monbg|setalpha|blend|battle_anim/.test(commandText)
    };
  }

  function framePlanForRecord(record) {
    const frame = record?.frame || {};
    const dimensions = record?.dimensions || {};
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

  function frameDataAttributes(plan, frameMs) {
    if (!plan || plan.count <= 1) return "";
    return [
      `data-battle-frame-count="${plan.count}"`,
      `data-battle-frame-columns="${plan.columns}"`,
      `data-battle-frame-rows="${plan.rows}"`,
      `data-battle-frame-ms="${Math.max(35, Number(frameMs || plan.frameMs || 90))}"`
    ].join(" ");
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

    function stopFrameAnimations() {
      frameTimers.forEach((timer) => window.clearInterval(timer));
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
        let index = 0;
        const draw = () => {
          const column = index % columns;
          const row = Math.floor(index / columns) % rows;
          const x = columns > 1 ? (column / (columns - 1)) * 100 : 0;
          const y = rows > 1 ? (row / (rows - 1)) * 100 : 0;
          node.style.backgroundPosition = `${x}% ${y}%`;
          index = (index + 1) % count;
        };
        draw();
        frameTimers.push(window.setInterval(draw, frameMs));
      });
      const composites = element.querySelectorAll("[data-battle-composite-count]");
      composites.forEach((node) => {
        const count = Math.max(1, Number(node.dataset.battleCompositeCount || 1));
        if (count <= 1) return;
        const frameMs = Math.max(35, Number(node.dataset.battleCompositeMs || 90));
        const frames = Array.from(node.querySelectorAll("[data-battle-composite-frame]"));
        let index = 0;
        const draw = () => {
          frames.forEach((frame, frameIndex) => {
            frame.hidden = frameIndex !== index;
          });
          index = (index + 1) % count;
        };
        draw();
        frameTimers.push(window.setInterval(draw, frameMs));
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
      if (moveProfile) return moveProfile;
      return {
        label: key || "unknown",
        family: animationFamilyFromMove(moveName),
        command_count: 0,
        commands: []
      };
    }

    function render() {
      stopFrameAnimations();
      const genProfile = profile();
      const fieldClasses = [
        "battle-scene-field",
        state.effect?.visual?.flash ? "is-bg-flashing" : "",
        state.effect?.visual?.shake ? "is-shaking" : "",
        state.effect?.visual?.background ? "has-bg-effect" : ""
      ].filter(Boolean).join(" ");
      element.className = `battle-scene battle-scene-gen${generation}${state.locked ? " is-locked" : ""}`;
      element.innerHTML = `
        <div class="battle-scene-screen" data-generation="${generation}" style="--battle-base-width:${genProfile.baseWidth};--battle-base-height:${genProfile.baseHeight};">
          <div class="${fieldClasses}">
            <div class="battle-scene-grid" aria-hidden="true"></div>
            <div class="battle-scene-bg-layer" aria-hidden="true"></div>
            ${renderSide("p2", genProfile)}
            ${renderSide("p1", genProfile)}
            ${renderEffect()}
          </div>
          ${renderBottomPanel(genProfile)}
          ${renderOverlay(genProfile)}
        </div>
      `;
      startFrameAnimations();
    }

    function renderSide(side, genProfile) {
      const pokemon = state[side];
      const percent = hpPercent(pokemon);
      const details = pokemon.species
        ? `${pokemonDisplayName(pokemon.nickname || pokemon.species, generation)}${pokemon.level ? ` Lv${pokemon.level}` : ""}`
        : side === "p1" ? "POKéMON" : "FOE";
      const hpText = side === "p1" || genProfile.enemyShowsHpText
        ? `<div class="battle-scene-hptext">${pokemon.maxHp ? `${pokemon.currentHp}/${pokemon.maxHp}` : "--/--"}</div>`
        : "";
      return `
        <div class="battle-scene-side battle-scene-${side}${pokemon.fainted ? " is-fainted" : ""}" data-scene-side="${side}">
          <div class="battle-scene-hud">
            <div class="battle-scene-name-row">
              <span class="battle-scene-name">${escapeHtml(details)}</span>
              ${renderStatusBadge(pokemon.status)}
            </div>
            <div class="battle-scene-hp-row">
              <span class="battle-scene-hp-label">HP</span>
              <div class="battle-scene-hpbar ${hpClass(percent)}">
                <span style="width:${percent}%"></span>
              </div>
            </div>
            ${hpText}
          </div>
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
        return `
          <span
            class="battle-scene-sprite battle-scene-sprite-frame"
            aria-hidden="true"
            ${frameDataAttributes(plan, plan.frameMs)}
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
      if (plan && plan.count > 1) {
        const scale = effectFrameScale(asset, plan);
        return `
          <span
            class="battle-scene-effect-asset battle-scene-effect-frame battle-scene-effect-asset-${escapeAttribute(role)}"
            aria-hidden="true"
            data-battle-anim-tag="${escapeAttribute(tag)}"
            ${frameDataAttributes(plan, plan.frameMs)}
            style="${escapeAttribute(`${frameStyle(asset, src, { width: plan.width * scale, height: plan.height * scale })};--battle-effect-index:${index};--battle-effect-total:${total}`)}"
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
          style="--battle-effect-index:${index};--battle-effect-total:${total};"
        />
      `;
    }

    function renderCompositeEffectAsset(asset, src, role, tag, index, total) {
      const composites = asset.composites.slice(0, 8);
      const nodes = composites.map((composite, compositeIndex) => renderCompositeSequence(asset, composite, src, compositeIndex)).join("");
      return `
        <span
          class="battle-scene-effect-asset battle-scene-effect-composite battle-scene-effect-asset-${escapeAttribute(role)}"
          aria-hidden="true"
          data-battle-anim-tag="${escapeAttribute(tag)}"
          style="--battle-effect-index:${index};--battle-effect-total:${total};"
        >${nodes}</span>
      `;
    }

    function renderCompositeSequence(asset, composite, src, compositeIndex) {
      const scale = compositeScale(asset, composite);
      const bounds = composite.bounds || { width: 8, height: 8 };
      const frames = Array.isArray(composite.frames) ? composite.frames : [];
      const frameNodes = frames.map((frame, frameIndex) => renderCompositeFrame(asset, composite, frame, src, scale, frameIndex)).join("");
      const offset = compositeIndex * 4;
      return `
        <span
          class="battle-scene-oam-composite"
          data-battle-composite-count="${Math.max(1, frames.length)}"
          data-battle-composite-ms="${Math.max(35, Number(composite.frame_ms || 70))}"
          style="width:${Math.round(Number(bounds.width || 8) * scale)}px;height:${Math.round(Number(bounds.height || 8) * scale)}px;left:${offset}px;top:${offset}px;"
        >${frameNodes}</span>
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
      return `
        <div class="battle-scene-bottom battle-scene-dialog-panel">
          <div class="battle-scene-dialog">
            <span class="battle-scene-turn">${state.turn ? `TURN ${state.turn}` : genProfile.title}</span>
            <strong class="battle-scene-message">${escapeHtml(message || genProfile.defaultMessage)}</strong>
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
      return `
        <div class="battle-scene-bottom battle-scene-command-panel">
          <div class="battle-scene-dialog">
            <strong class="battle-scene-message">${escapeHtml(questionText)}</strong>
            <span class="battle-scene-prompt" aria-hidden="true"></span>
          </div>
          <div class="battle-scene-command-menu" role="group" aria-label="Menu de batalha">
            ${genProfile.commandLabels.map((item, index) => `
              <button type="button" data-battle-visual-menu="${escapeAttribute(item.key)}" ${disabled ? "disabled" : ""}>
                <span class="battle-scene-cursor">${index === 0 ? "▶" : ""}</span>${escapeHtml(item.label)}
              </button>
            `).join("")}
          </div>
        </div>
      `;
    }

    function renderFightPanel(genProfile) {
      const groups = actionGroupsFromRequest(state.request);
      const moves = groups.moves.length ? groups.moves : [{ action: "move 1", label: "----", pp: 0, maxpp: 0, type: "--", disabled: true }];
      const firstAvailable = moves.find((move) => !move.disabled) || moves[0];
      return `
        <div class="battle-scene-bottom battle-scene-fight-panel">
          <div class="battle-scene-move-menu" role="group" aria-label="Golpes">
            ${moves.map((move, index) => `
              <button type="button" data-battle-visual-action="${escapeAttribute(move.action)}" ${move.disabled || state.locked ? "disabled" : ""}>
                <span class="battle-scene-cursor">${index === 0 ? "▶" : ""}</span>
                <span>${escapeHtml(humanizeMoveName(move.label, generation))}</span>
                <small>${escapeHtml(genProfile.ppLabel)} ${Number(move.pp || 0)}/${Number(move.maxpp || 0)}</small>
              </button>
            `).join("")}
          </div>
          <div class="battle-scene-move-detail">
            <span>${escapeHtml(genProfile.moveTypeLabel)}</span>
            <strong>${escapeHtml(String(firstAvailable?.type || "--").toUpperCase())}</strong>
            <button type="button" data-battle-visual-menu="command">${escapeHtml(genProfile.backLabel)}</button>
          </div>
        </div>
      `;
    }

    function renderRunConfirmPanel(genProfile) {
      const message = genProfile.uppercaseText ? "FORFEIT THIS LINK BATTLE?" : "Forfeit this link battle?";
      return `
        <div class="battle-scene-bottom battle-scene-run-panel">
          <div class="battle-scene-dialog">
            <strong class="battle-scene-message">${escapeHtml(message)}</strong>
          </div>
          <div class="battle-scene-confirm-menu">
            <button type="button" data-battle-visual-menu="run-yes">YES</button>
            <button type="button" data-battle-visual-menu="command">NO</button>
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
          return `<div class="battle-scene-party-row is-empty"><span class="battle-scene-party-icon"></span><strong>---</strong><small>EMPTY</small></div>`;
        }
        const switchEntry = switchByIndex.get(index);
        const disabled = state.locked || !switchEntry || switchEntry.disabled;
        const condition = parseCondition(entry.condition || "", { currentHp: entry.currentHp || 0, maxHp: entry.maxHp || 0, status: entry.status || "ok" });
        const percent = hpPercent(condition);
        const label = pokemonDisplayName(entry.name || entry.nickname || entry.species || `Pokémon ${index + 1}`, generation);
        return `
          <button type="button" class="battle-scene-party-row${entry.active ? " is-active" : ""}${entry.fainted || switchEntry?.fainted ? " is-fainted" : ""}" data-battle-visual-action="${switchEntry ? escapeAttribute(switchEntry.action) : ""}" ${disabled ? "disabled" : ""}>
            <span class="battle-scene-party-icon"></span>
            <strong>${escapeHtml(label)}</strong>
            <small>${entry.level ? `Lv${entry.level}` : levelFromDetails(entry.details) || ""}</small>
            ${renderStatusBadge(condition.status)}
            <span class="battle-scene-party-hp"><i class="${hpClass(percent)}" style="width:${percent}%"></i></span>
            <em>${condition.maxHp ? `${condition.currentHp}/${condition.maxHp}` : entry.condition || ""}</em>
          </button>
        `;
      }).join("");
      return `
        <div class="battle-scene-overlay battle-scene-party-overlay">
          <div class="battle-scene-overlay-head">
            <strong>${escapeHtml(genProfile.partyTitle)}</strong>
            <button type="button" data-battle-visual-menu="command">${escapeHtml(genProfile.backLabel)}</button>
          </div>
          <div class="battle-scene-party-list">${rows}</div>
          <div class="battle-scene-overlay-footer">${escapeHtml(groups.forcedSwitch ? "Choose a POKéMON." : "Choose a POKéMON or cancel.")}</div>
        </div>
      `;
    }

    function renderBagOverlay(genProfile) {
      const grouped = groupedInventory(genProfile);
      const pocket = selectedPocket(genProfile, grouped);
      const entries = grouped[pocket] || [];
      const selected = state.selectedBagItem;
      const pocketTabs = genProfile.pockets.map((item) => `
        <button type="button" class="${item.key === pocket ? "is-active" : ""}" data-battle-visual-pocket="${escapeAttribute(item.key)}">${escapeHtml(item.label)}</button>
      `).join("");
      const rows = entries.length ? entries.slice(0, generation === 3 ? 8 : 6).map((entry, index) => `
        <button type="button" class="battle-scene-bag-row${selected?.item_id === entry.item_id && selected?.pocket_name === entry.pocket_name ? " is-selected" : ""}" data-battle-visual-item="${index}">
          <span class="battle-scene-cursor">${index === 0 ? "▶" : ""}</span>
          <strong>${escapeHtml(itemDisplayName(entry, generation))}</strong>
          <small>×${Number(entry.quantity || 0)}</small>
        </button>
      `).join("") : `<div class="battle-scene-bag-empty">No items.</div>`;
      return `
        <div class="battle-scene-overlay battle-scene-bag-overlay">
          <div class="battle-scene-overlay-head">
            <strong>${escapeHtml(genProfile.bagTitle)}</strong>
            <button type="button" data-battle-visual-menu="command">${escapeHtml(genProfile.backLabel)}</button>
          </div>
          <div class="battle-scene-bag-shell">
            <div class="battle-scene-pocket-tabs">${pocketTabs}</div>
            <div class="battle-scene-bag-list">${rows}</div>
            <div class="battle-scene-bag-art" aria-hidden="true"><span></span></div>
            <div class="battle-scene-bag-detail">
              <strong>${escapeHtml(selected ? itemDisplayName(selected, generation) : genProfile.bagTitle)}</strong>
              <span>${escapeHtml(selected ? itemDescription(selected, genProfile) : "Choose an item pocket.")}</span>
              <button type="button" data-battle-visual-menu="bag-use" ${selected ? "" : "disabled"}>USE</button>
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
    framePlanForRecord,
    battleProfileForGeneration,
    actionGroupsFromRequest,
    effectVisualProfile,
    humanizeMoveName,
    parseBattleIdent,
    parseBattleLogLine,
    parseCondition,
    tileSheetPosition,
    tileStyle,
    compositeScale
  };
});
