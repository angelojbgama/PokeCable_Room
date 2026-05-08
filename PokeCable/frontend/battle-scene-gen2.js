(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.POKECABLE_BATTLE_SCENE_GEN2 = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : window, function () {
  const layout = {
    source: "reference/pret/pokecrystal/engine/battle/core.asm",
    tile: 8,
    screen: { x: 0, y: 0, width: 160, height: 144 },
    field: { x: 0, y: 0, width: 160, height: 96 },
    textbox: { x: 0, y: 96, width: 160, height: 48, asm: "hlcoord 0,12" },
    commandMenu: { x: 64, y: 96, width: 96, height: 48, asm: "menu_coords 8,12,19,17; dn 2,2; spacing 6" },
    moveMenu: { x: 32, y: 96, width: 112, height: 40, asm: "hlcoord 4,12; lb bc,4,14" },
    moveList: { x: 48, y: 104, asm: "hlcoord 6,13" },
    moveInfo: { x: 0, y: 64, width: 72, height: 32, asm: "hlcoord 0,8; lb bc,3,9" },
    enemy: {
      sprite: { x: 96, y: 0, width: 56, height: 56, asm: "hlcoord 12,0" },
      hud: { x: 8, y: 0, width: 88, height: 32, asm: "hlcoord 1,0; lb bc,4,11" },
      name: { x: 8, y: 0, asm: "hlcoord 1,0" },
      level: { x: 48, y: 8, asm: "hlcoord 6,1" },
      gender: { x: 72, y: 8, asm: "hlcoord 9,1" },
      hp: { x: 16, y: 16, width: 64, height: 8, asm: "hlcoord 2,2; HP_BAR_LENGTH" },
      balls: { x: 72, y: 32, direction: -8, asm: "ldpixel wPlaceBallsX, 9, 4" }
    },
    player: {
      sprite: { x: 16, y: 48, width: 56, height: 56, asm: "hlcoord 2,6" },
      hud: { x: 72, y: 56, width: 88, height: 40, asm: "hlcoord 9,7; lb bc,5,11" },
      name: { x: 80, y: 56, asm: "hlcoord 10,7" },
      level: { x: 112, y: 64, asm: "hlcoord 14,8" },
      gender: { x: 136, y: 64, asm: "hlcoord 17,8" },
      hp: { x: 80, y: 72, width: 64, height: 8, asm: "hlcoord 10,9; HP_BAR_LENGTH" },
      exp: { x: 80, y: 88, width: 72, height: 8, asm: "hlcoord 10,11" },
      balls: { x: 96, y: 96, direction: 8, asm: "ldpixel wPlaceBallsX, 12, 12" }
    }
  };

  const profile = {
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
  };

  const uiAssets = {
    balls: "gen2/ui/battle/balls.png",
    hudEnemy: "gen2/ui/battle/enemy_hp_bar_border.png",
    hudPlayer: "gen2/ui/battle/hp_exp_bar_border.png",
    dialogFrame: "gen2/ui/frames/1.png",
    dialog: null
  };

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function percent(value, total) {
    return `${(Number(value || 0) / total) * 100}%`;
  }

  function cssVariables() {
    const field = layout.field;
    const entries = {
      enemySpriteLeft: percent(layout.enemy.sprite.x, field.width),
      enemySpriteTop: percent(layout.enemy.sprite.y, field.height),
      enemySpriteWidth: percent(layout.enemy.sprite.width, field.width),
      enemySpriteHeight: percent(layout.enemy.sprite.height, field.height),
      playerSpriteLeft: percent(layout.player.sprite.x, field.width),
      playerSpriteTop: percent(layout.player.sprite.y, field.height),
      playerSpriteWidth: percent(layout.player.sprite.width, field.width),
      playerSpriteHeight: percent(layout.player.sprite.height, field.height),
      enemyHudLeft: percent(layout.enemy.hud.x, field.width),
      enemyHudTop: percent(layout.enemy.hud.y, field.height),
      enemyHudWidth: percent(layout.enemy.hud.width, field.width),
      enemyHudHeight: percent(layout.enemy.hud.height, field.height),
      playerHudLeft: percent(layout.player.hud.x, field.width),
      playerHudTop: percent(layout.player.hud.y, field.height),
      playerHudWidth: percent(layout.player.hud.width, field.width),
      playerHudHeight: percent(layout.player.hud.height, field.height),
      commandMenuLeft: percent(layout.commandMenu.x, layout.screen.width),
      commandMenuWidth: percent(layout.commandMenu.width, layout.screen.width),
      moveMenuLeft: percent(layout.moveMenu.x, layout.screen.width),
      moveMenuWidth: percent(layout.moveMenu.width, layout.screen.width),
      moveMenuHeight: percent(layout.moveMenu.height, layout.textbox.height),
      moveInfoLeft: percent(layout.moveInfo.x, layout.screen.width),
      moveInfoTopFromBottom: percent(layout.moveInfo.y - layout.textbox.y, layout.textbox.height),
      moveInfoWidth: percent(layout.moveInfo.width, layout.screen.width),
      moveInfoHeight: percent(layout.moveInfo.height, layout.textbox.height),
      enemyBallsLeft: percent(layout.enemy.balls.x, field.width),
      enemyBallsTop: percent(layout.enemy.balls.y, field.height),
      playerBallsLeft: percent(layout.player.balls.x, field.width),
      playerBallsTop: percent(layout.player.balls.y, field.height),
      ballStep: percent(layout.tile, field.width)
    };
    return Object.entries(entries)
      .map(([key, value]) => `--gen2-${key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}:${value};`)
      .join("");
  }

  function hpBarPixels(currentHp, maxHp) {
    const current = Math.max(0, Number(currentHp || 0));
    const max = Math.max(0, Number(maxHp || 0));
    const lengthPx = 6 * layout.tile;
    if (!current || !max) return 0;
    const pixels = Math.floor((current * lengthPx) / max);
    return Math.max(1, Math.min(lengthPx, pixels));
  }

  function hpClassForPixels(pixels) {
    const value = Math.max(0, Number(pixels || 0));
    if (value >= 24) return "is-high";
    if (value >= 10) return "is-mid";
    return "is-low";
  }

  function hpWidthPercent(currentHp, maxHp) {
    return `${(hpBarPixels(currentHp, maxHp) / (6 * layout.tile)) * 100}%`;
  }

  function asmNumber(value, fallback = 0) {
    const raw = String(value || "").trim();
    if (!raw) return fallback;
    if (raw.startsWith("$")) return Number.parseInt(raw.slice(1), 16);
    const parsed = Number.parseInt(raw, 10);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function framesToMs(frames) {
    return Math.max(0, Math.round(Number(frames || 0) * 1000 / 60));
  }

  function battleAnimTimeline(profile) {
    const script = Array.isArray(profile?.script) ? profile.script : [];
    const logic = profile?.logic || {};
    const objects = Array.isArray(logic.objects) ? logic.objects : [];
    const bgEffects = Array.isArray(logic.bg_effects) ? logic.bg_effects : [];
    const events = [];
    let frame = 0;
    let objectIndex = 0;
    let bgEffectIndex = 0;

    script.forEach((step, scriptIndex) => {
      const command = String(step?.command || "");
      const args = Array.isArray(step?.args) ? step.args : [];
      const base = {
        command,
        frame,
        script_index: scriptIndex,
        time_ms: framesToMs(frame)
      };
      if (command === "anim_wait") {
        const durationFrames = asmNumber(args[0], 0);
        events.push({
          ...base,
          duration_frames: durationFrames,
          duration_ms: framesToMs(durationFrames),
          type: "wait"
        });
        frame += durationFrames;
        return;
      }
      if (command === "anim_obj") {
        const object = objects[objectIndex] || {};
        events.push({
          ...base,
          args: args.slice(1),
          callback: object.callback || "",
          composite: object.composite || null,
          frameset: object.frameset || "",
          gfx: object.gfx || "",
          object: object.object || args[0] || "",
          object_index: objectIndex,
          type: "object"
        });
        objectIndex += 1;
        return;
      }
      if (command === "anim_bgeffect") {
        const effect = bgEffects[bgEffectIndex] || {};
        events.push({
          ...base,
          args: effect.args || args.slice(1),
          effect: effect.effect || args[0] || "",
          effect_index: bgEffectIndex,
          type: "bg_effect"
        });
        bgEffectIndex += 1;
        return;
      }
      if (command === "anim_incobj" || command === "anim_setobj") {
        const objectId = asmNumber(args[0], 0);
        const targetObjectIndex = objectId > 0 ? objectId - 1 : 0;
        events.push({
          ...base,
          args,
          object_id: objectId,
          state: command === "anim_setobj" ? asmNumber(args[1], 0) : null,
          target: args[0] || "",
          target_object_index: targetObjectIndex,
          type: command.replace(/^anim_/, "")
        });
        return;
      }
      if (command === "anim_incbgeffect") {
        const effectName = args[0] || "";
        const matchedEffectIndex = bgEffects.findIndex((effect) => effect.effect === effectName);
        events.push({
          ...base,
          args,
          effect: effectName,
          effect_index: matchedEffectIndex >= 0 ? matchedEffectIndex : null,
          target: effectName,
          type: "incbgeffect"
        });
        return;
      }
      if (command === "anim_clearobjs" || command === "anim_oamon" || command === "anim_oamoff") {
        events.push({ ...base, type: command.replace(/^anim_/, "") });
        return;
      }
      if (command === "anim_sound" || command === "anim_cry") {
        events.push({
          ...base,
          args,
          sound: args.at(-1) || "",
          type: command === "anim_cry" ? "cry" : "sound"
        });
        return;
      }
      if (command.endsWith("gfx")) {
        events.push({
          ...base,
          args,
          gfx: args.filter((arg) => String(arg).startsWith("BATTLE_ANIM_GFX_")),
          type: "gfx"
        });
        return;
      }
      if (command === "anim_ret") {
        events.push({ ...base, type: "ret" });
        return;
      }
      if (command) events.push({ ...base, args, type: "command" });
    });

    return {
      duration_frames: frame,
      duration_ms: framesToMs(frame),
      events,
      source: "reference/pret/pokecrystal/data/moves/animations.asm"
    };
  }

  function renderHud(context) {
    const levelHtml = context.showLevel ? `<span class="battle-scene-level">Lv${context.levelHtml || ""}</span>` : "";
    return `
      <div class="battle-scene-hud battle-scene-hud-gen2">
        <span class="battle-scene-name">${context.displayNameHtml || ""}</span>
        ${levelHtml}
        ${context.statusHtml || ""}
        <div class="battle-scene-hp-row">
          <span class="battle-scene-hp-label">HP</span>
          <div class="battle-scene-hpbar ${context.hpClass || ""}">
            <span style="width:${context.hpWidth || "0%"}"></span>
          </div>
        </div>
        ${context.hpTextHtml || ""}
      </div>
    `;
  }

  function renderDialogPanel(context) {
    return `
      <div class="battle-scene-bottom battle-scene-dialog-panel">
        <div class="battle-scene-dialog">
          <strong class="battle-scene-message">${context.messageHtml || ""}</strong>
          <span class="battle-scene-prompt" aria-hidden="true"></span>
        </div>
      </div>
    `;
  }

  function renderCommandPanel(context) {
    return `
      <div class="battle-scene-bottom battle-scene-command-panel">
        <div class="battle-scene-dialog">
          <strong class="battle-scene-message">${context.messageHtml || ""}</strong>
          <span class="battle-scene-prompt" aria-hidden="true"></span>
        </div>
        <div class="battle-scene-command-menu" role="group" aria-label="Menu de batalha">
          ${context.buttonsHtml || ""}
        </div>
      </div>
    `;
  }

  function renderFightPanel(context) {
    return `
      <div class="battle-scene-bottom battle-scene-fight-panel">
        <div class="battle-scene-move-menu" role="group" aria-label="Golpes">
          ${context.movesHtml || ""}
        </div>
        <div class="battle-scene-move-detail">
          ${context.detailHtml || ""}
        </div>
      </div>
    `;
  }

  function renderRunConfirmPanel(context) {
    return `
      <div class="battle-scene-bottom battle-scene-run-panel">
        <div class="battle-scene-dialog">
          <strong class="battle-scene-message">${context.messageHtml || ""}</strong>
        </div>
        <div class="battle-scene-confirm-menu">
          ${context.buttonsHtml || ""}
        </div>
      </div>
    `;
  }

  return {
    cssVariables,
    battleAnimTimeline,
    hpBarPixels,
    hpClassForPixels,
    hpWidthPercent,
    layout,
    layoutCopy: () => clone(layout),
    profile,
    renderCommandPanel,
    renderDialogPanel,
    renderFightPanel,
    renderHud,
    renderRunConfirmPanel,
    uiAssets
  };
});
