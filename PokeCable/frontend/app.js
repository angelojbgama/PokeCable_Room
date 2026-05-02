window.POKECABLE_TRADE_EVOLUTION_ENABLED = true;

const statusEl = document.querySelector("#connectionStatus");
const tradeStatusEl = document.querySelector("#tradeStatus");
const localOfferEl = document.querySelector("#localOffer");
const peerOfferEl = document.querySelector("#peerOffer");
const localOfferDetailsEl = document.querySelector("#localOfferDetails");
const peerOfferDetailsEl = document.querySelector("#peerOfferDetails");
const tradeCompatibilityPreviewEl = document.querySelector("#tradeCompatibilityPreview");
const tradeEvolutionPreviewEl = document.querySelector("#tradeEvolutionPreview");
const eventLogEl = document.querySelector("#eventLog");
const pokemonChoiceEl = document.querySelector("#pokemonChoice");
const saveFileEl = document.querySelector("#saveFile");
const saveSummaryEl = document.querySelector("#saveSummary");
const setupSaveStageEl = document.querySelector("#setupSaveStage");
const setupRoomStageEl = document.querySelector("#setupRoomStage");
const setupChoiceStageEl = document.querySelector("#setupChoiceStage");
const setupHeaderEl = document.querySelector("#setupHeader");
const setupFooterEl = document.querySelector("#setupFooter");
const noticeEl = document.querySelector(".notice");
const accessSessionButton = document.querySelector("#accessSession");
const leaveSessionButton = document.querySelector("#leaveSession");
const openTradeTabButton = document.querySelector("#openTradeTab");
const openBattleTabButton = document.querySelector("#openBattleTab");
const backToModeFromTradeButton = document.querySelector("#backToModeFromTrade");
const backToModeFromBattleButton = document.querySelector("#backToModeFromBattle");
const sessionStatusEl = document.querySelector("#sessionStatus");
const sessionDetailEl = document.querySelector("#sessionDetail");
const sendTradeOfferButton = document.querySelector("#sendTradeOffer");
const confirmButton = document.querySelector("#confirmTrade");
const cancelButton = document.querySelector("#cancelTrade");
const downloadArea = document.querySelector("#downloadArea");
const sendBattleTeamButton = document.querySelector("#sendBattleTeam");
const confirmBattleButton = document.querySelector("#confirmBattle");
const forfeitBattleButton = document.querySelector("#forfeitBattle");
const battleLogEl = document.querySelector("#battleLog");
const battleStatusEl = document.querySelector("#battleStatus");
const battleSaveStatusEl = document.querySelector("#battleSaveStatus");
const battleFormatEl = document.querySelector("#battleFormat");
const battleTeamCountEl = document.querySelector("#battleTeamCount");
const battleTeamPreviewEl = document.querySelector("#battleTeamPreview");
const battleActionsEl = document.querySelector("#battleActions");
const tabButtons = Array.from(document.querySelectorAll("[data-tab]"));
const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
const setupStatusEl = document.querySelector("#setupStatus");
const setupSelectedSummaryEl = document.querySelector("#setupSelectedSummary");
const setupSelectionDetailEl = document.querySelector("#setupSelectionDetail");
const saveManagementStatusEl = document.querySelector("#saveManagementStatus");
window.POKECABLE_SAVE_MANAGEMENT_STATUS_EL = saveManagementStatusEl;
const selectedInventoryItemStatusEl = document.querySelector("#selectedInventoryItemStatus");
const setupPartyPreviewEl = document.querySelector("#setupPartyPreview");
const setupBagPreviewEl = document.querySelector("#setupBagPreview");
const setupPcPreviewEl = document.querySelector("#setupPcPreview");
const setupPokemonPcPreviewEl = document.querySelector("#setupPokemonPcPreview");
const setupTogglePokemonPcButton = document.querySelector("#setupTogglePokemonPc");
const pokemonDetailDrawerEl = document.querySelector("#pokemonDetailDrawer");
const pokemonDetailDrawerBackdropEl = document.querySelector("#pokemonDetailDrawerBackdrop");
const pokemonDetailDrawerTitleEl = document.querySelector("#pokemonDetailDrawerTitle");
const pokemonDetailDrawerBodyEl = document.querySelector("#pokemonDetailDrawerBody");
const closePokemonDetailDrawerButton = document.querySelector("#closePokemonDetailDrawer");
const startMovePokemonButton = document.querySelector("#startMovePokemon");
const cancelMovePokemonButton = document.querySelector("#cancelMovePokemon");
const removeHeldItemButton = document.querySelector("#removeHeldItem");
const applyHeldItemButton = document.querySelector("#applyHeldItem");
const tradeSelectedSummaryEl = document.querySelector("#tradeSelectedSummary");
const tradePartyLabelEl = document.querySelector("#tradePartyLabel");
const tradePartyPreviewEl = document.querySelector("#tradePartyPreview");
const tradeBoxPreviewEl = document.querySelector("#tradeBoxPreview");
const tradeTogglePokemonPcButton = document.querySelector("#tradeTogglePokemonPc");

const roomNameEl = document.querySelector("#roomName");
const roomPasswordEl = document.querySelector("#roomPassword");

const speciesData = window.POKECABLE_SPECIES_DATA;
if (!speciesData) {
  console.error("POKECABLE_SPECIES_DATA nao foi carregado. Verifique PokeCable/frontend/species-data.js.");
}
const genderRates = window.POKECABLE_GENDER_RATES;
if (!genderRates) {
  console.error("POKECABLE_GENDER_RATES nao foi carregado. Verifique PokeCable/frontend/gender-rates.js.");
}
const growthRatesModule = window.POKECABLE_GROWTH_RATES;
if (!growthRatesModule) {
  console.error("POKECABLE_GROWTH_RATES nao foi carregado. Verifique PokeCable/frontend/growth-rates.js.");
}
const speciesNames = speciesData?.speciesNames || Object.create(null);
const gen1InternalNames = speciesData?.gen1InternalNames || Object.create(null);
const gen1InternalToNational = speciesData?.gen1InternalToNational || Object.create(null);
const nationalToGen1Internal = speciesData?.nationalToGen1Internal || Object.create(null);
const gen3NativeToNational = speciesData?.gen3NativeToNational || Object.create(null);
const nationalToGen3Native = speciesData?.nationalToGen3Native || Object.create(null);
const tradeRules = window.POKECABLE_TRADE_RULES;
if (!tradeRules) {
  console.error("POKECABLE_TRADE_RULES nao foi carregado. Verifique PokeCable/frontend/trade-rules.js.");
}
const saveMovementModule = window.POKECABLE_SAVE_MOVEMENT;
if (!saveMovementModule) {
  console.error("POKECABLE_SAVE_MOVEMENT nao foi carregado. Verifique PokeCable/frontend/save-movement.js.");
}
const simpleTradeEvolutionByNational = tradeRules?.simpleTradeEvolutionByNational || Object.create(null);
const itemTradeEvolutionRules = tradeRules?.itemTradeEvolutionRules || [];
const tradePreviewModule = window.POKECABLE_TRADE_PREVIEW;
if (!tradePreviewModule) {
  console.error("POKECABLE_TRADE_PREVIEW nao foi carregado. Verifique PokeCable/frontend/trade-preview.js.");
}
const pokemonUiModule = window.POKECABLE_POKEMON_UI;
if (!pokemonUiModule) {
  console.error("POKECABLE_POKEMON_UI nao foi carregado. Verifique PokeCable/frontend/pokemon-ui.js.");
}
const inventoryUiModule = window.POKECABLE_INVENTORY_UI;
if (!inventoryUiModule) {
  console.error("POKECABLE_INVENTORY_UI nao foi carregado. Verifique PokeCable/frontend/inventory-ui.js.");
}
const saveManagementModule = window.POKECABLE_SAVE_MANAGEMENT;
if (!saveManagementModule) {
  console.error("POKECABLE_SAVE_MANAGEMENT nao foi carregado. Verifique PokeCable/frontend/save-management.js.");
}
const webCompatibilityModule = window.POKECABLE_WEB_COMPATIBILITY;
if (!webCompatibilityModule) {
  console.error("POKECABLE_WEB_COMPATIBILITY nao foi carregado. Verifique PokeCable/frontend/web-compatibility.js.");
}
const tradeFlowModule = window.POKECABLE_TRADE_FLOW;
if (!tradeFlowModule) {
  console.error("POKECABLE_TRADE_FLOW nao foi carregado. Verifique PokeCable/frontend/trade-flow.js.");
}
const battleFlowModule = window.POKECABLE_BATTLE_FLOW;
if (!battleFlowModule) {
  console.error("POKECABLE_BATTLE_FLOW nao foi carregado. Verifique PokeCable/frontend/battle-flow.js.");
}
const wsClientModule = window.POKECABLE_WS_CLIENT;
if (!wsClientModule) {
  console.error("POKECABLE_WS_CLIENT nao foi carregado. Verifique PokeCable/frontend/websocket-client.js.");
}

const LOCAL_FALLBACK_SPRITE = "pokemon-fallback.svg";

const moveNames = window.POKECABLE_MOVE_NAMES;
if (!moveNames) {
  console.error("POKECABLE_MOVE_NAMES nao foi carregado. Verifique PokeCable/frontend/move-names.js.");
}
const abilityNames = window.POKECABLE_ABILITY_NAMES;
if (!abilityNames) {
  console.error("POKECABLE_ABILITY_NAMES nao foi carregado. Verifique PokeCable/frontend/ability-names.js.");
}
const itemNames = window.POKECABLE_ITEM_NAMES;
if (!itemNames) {
  console.error("POKECABLE_ITEM_NAMES nao foi carregado. Verifique PokeCable/frontend/item-names.js.");
}
const itemCategories = window.POKECABLE_ITEM_CATEGORIES;
if (!itemCategories) {
  console.error("POKECABLE_ITEM_CATEGORIES nao foi carregado. Verifique PokeCable/frontend/item-categories.js.");
}

function nativeToNational(generation, speciesId) {
  if (generation === 1) return gen1InternalToNational[speciesId] || speciesId;
  if (generation === 3) return gen3NativeToNational[speciesId] || speciesId;
  return speciesId;
}

function nationalToNative(generation, nationalId) {
  if (generation === 1) return nationalToGen1Internal[nationalId] || 0;
  if (generation === 2) return nationalId >= 1 && nationalId <= 251 ? nationalId : 0;
  if (generation === 3) {
    if (nationalId >= 1 && nationalId <= 251) return nationalId;
    return nationalToGen3Native[nationalId] || 0;
  }
  return 0;
}

function speciesExistsInGeneration(nationalId, generation) {
  return nationalToNative(generation, nationalId) > 0;
}

function levelFromSpeciesExperience(nationalDexId, experience) {
  return growthRatesModule?.levelFromSpeciesExperience(Number(nationalDexId || 0), Number(experience || 0)) || 1;
}

function genderRateForSpecies(nationalDexId) {
  const dexId = Number(nationalDexId || 0);
  if (!dexId || !genderRates || dexId >= genderRates.length) return null;
  return Number(genderRates[dexId]);
}

function genderFromGen2AttackDv(nationalDexId, attackDv) {
  const rate = genderRateForSpecies(nationalDexId);
  if (rate === null || rate < 0) return null;
  if (rate === 0) return "♂";
  if (rate >= 8) return "♀";
  return Number(attackDv || 0) <= (rate * 2 - 1) ? "♀" : "♂";
}

function isShinyGen2(attackDv, defenseDv, speedDv, specialDv) {
  if (defenseDv !== 10 || speedDv !== 10 || specialDv !== 10) return false;
  return [2, 3, 6, 7, 10, 11, 14, 15].includes(attackDv);
}

function genderFromGen3Personality(nationalDexId, personality) {
  const rate = genderRateForSpecies(nationalDexId);
  if (rate === null || rate < 0) return null;
  if (rate === 0) return "♂";
  if (rate >= 8) return "♀";
  return (Number(personality || 0) & 0xff) < rate * 32 ? "♀" : "♂";
}

function isShinyGen3(personality, trainerId) {
  const tid = Number(trainerId || 0) & 0xffff;
  const sid = (Number(trainerId || 0) >>> 16) & 0xffff;
  const pidLow = Number(personality || 0) & 0xffff;
  const pidHigh = (Number(personality || 0) >>> 16) & 0xffff;
  return (tid ^ sid ^ pidLow ^ pidHigh) < 8;
}

const unownFormNames = "ABCDEFGHIJKLMNOPQRSTUVWXYZ!?".split("");
const natureNames = [
  "Hardy", "Lonely", "Brave", "Adamant", "Naughty",
  "Bold", "Docile", "Relaxed", "Impish", "Lax",
  "Timid", "Hasty", "Serious", "Jolly", "Naive",
  "Modest", "Mild", "Quiet", "Bashful", "Rash",
  "Calm", "Gentle", "Sassy", "Careful", "Quirky"
];

function unownFormFromGen2Dvs(attackDv, defenseDv, speedDv, specialDv) {
  const value = (
    ((Number(attackDv || 0) & 0x6) << 5)
    | ((Number(defenseDv || 0) & 0x6) << 3)
    | ((Number(speedDv || 0) & 0x6) << 1)
    | ((Number(specialDv || 0) & 0x6) >> 1)
  );
  return unownFormNames[Math.min(25, Math.floor(value / 10))] || null;
}

function unownFormFromGen3Personality(personality) {
  const value = (
    ((Number(personality || 0) & 0x03000000) >>> 18)
    | ((Number(personality || 0) & 0x00030000) >>> 12)
    | ((Number(personality || 0) & 0x00000300) >>> 6)
    | (Number(personality || 0) & 0x00000003)
  ) % 28;
  return unownFormNames[value] || null;
}

function unownFormFromGen3Species(speciesId, personality) {
  const numericSpeciesId = Number(speciesId || 0);
  if (numericSpeciesId === 201) return unownFormFromGen3Personality(personality);
  if (numericSpeciesId >= 252 && numericSpeciesId <= 276) return unownFormNames[numericSpeciesId - 251] || null;
  return null;
}

function itemName(itemId, generation) {
  if (!itemId) return null;
  return (itemNames && itemNames[generation]?.[Number(itemId)]) || null;
}

function itemCategory(itemId, generation) {
  if (!itemId) return null;
  return (itemCategories && itemCategories[generation]?.[Number(itemId)]) || null;
}

function moveName(moveId) {
  const numericId = Number(moveId || 0);
  if (!numericId) return null;
  return (moveNames && moveNames[numericId]) || `Move #${numericId}`;
}

function abilityName(value) {
  if (value == null || value === "") return null;
  if (typeof value === "object") {
    const named = cleanName(value.name || value.ability_name || "");
    if (named) return named;
    const objectId = Number(value.ability_id || value.id || 0);
    if (objectId) return (abilityNames && abilityNames[objectId]) || `Ability #${objectId}`;
    return null;
  }
  if (typeof value === "number") {
    return (abilityNames && abilityNames[value]) || `Ability #${value}`;
  }
  const text = cleanName(value);
  if (!text) return null;
  if (/^\d+$/.test(text)) {
    const numericId = Number(text);
    return (abilityNames && abilityNames[numericId]) || `Ability #${numericId}`;
  }
  return text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/"/g, "&quot;");
}

function cleanName(value) {
  return String(value || "").replace(/\0/g, "").trim().replace(/\s+/g, " ");
}

function isSpeciesPlaceholder(value) {
  return /^species\s*#?\s*\d+$/i.test(cleanName(value));
}

function speciesNameFor(generation, speciesId, fallback = "") {
  const nationalId = nativeToNational(generation, speciesId);
  const fallbackName = cleanName(fallback);
  if (fallbackName && !isSpeciesPlaceholder(fallbackName)) return fallbackName;
  return speciesNames[nationalId] || fallbackName || (nationalId ? `Species #${nationalId}` : "Pokemon");
}

function pokemonSpriteUrl(nationalDexId, form = "", isShiny = false) {
  const dex = Number(nationalDexId || 0);
  if (!dex) return "";
  const shinyPath = isShiny ? "shiny/" : "";
  let url = `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${shinyPath}${dex}`;
  if (dex === 201 && form) {
    const f = String(form).toLowerCase().trim();
    if (f === "!") url += "-exclamation";
    else if (f === "?") url += "-question";
    else if (f !== "a") url += `-${f}`;
  }
  return url + ".png";
}

function pokemonSpriteImgHtml(nationalDexId, altText, className = "pokemon-sprite", form = "", isShiny = false) {
  const remoteSprite = pokemonSpriteUrl(nationalDexId, form, isShiny);
  const sprite = remoteSprite || LOCAL_FALLBACK_SPRITE;
  const escapedSrc = escapeAttribute(sprite);
  const escapedFallback = escapeAttribute(LOCAL_FALLBACK_SPRITE);
  return `<img class="${className}" src="${escapedSrc}" alt="" aria-hidden="true" loading="lazy" onerror="if(!this.dataset.fallbackApplied){this.dataset.fallbackApplied='1';this.src='${escapedFallback}';return;}this.style.display='none';" />`;
}

function sameName(left, right) {
  return cleanName(left).toLowerCase().replace(/[^a-z0-9]/g, "") === cleanName(right).toLowerCase().replace(/[^a-z0-9]/g, "");
}

function normalizePokemonDisplay(pokemonLike) {
  const { national_dex_id, species_name, level, nickname, gender, held_item_name, unown_form, metadata, is_shiny, canonical } = pokemonLike;
  let speciesName = cleanName(species_name);
  if ((!speciesName || isSpeciesPlaceholder(speciesName)) && national_dex_id && speciesNames[national_dex_id]) {
    speciesName = speciesNames[national_dex_id];
  }
  if (!speciesName) speciesName = national_dex_id ? `Species #${national_dex_id}` : "Pokemon";
  const form = cleanName(unown_form || metadata?.unown_form);
  if (Number(national_dex_id || 0) === 201 && form) {
    speciesName = `${speciesName} (${form})`;
  }
  const shiny = Boolean(is_shiny || metadata?.is_shiny || canonical?.is_shiny);
  let text = `${national_dex_id ? `#${national_dex_id} ` : ""}${speciesName}${shiny ? ' ★' : ''}${gender ? ` ${gender}` : ""} Lv. ${Number(level || 1)}`;
  text += held_item_name ? ` — Item: ${held_item_name}` : " — Sem item";
  const nick = cleanName(nickname);
  if (nick && !sameName(nick, speciesName)) text += ` "${nick}"`;
  return text;
}

function parseLocation(location) {
  const text = String(location || "");
  const parts = text.split(":");
  if (parts[0] === "party" && parts.length === 2) {
    return { kind: "party", index: Number(parts[1]) };
  }
  if (parts[0] === "box" && parts.length === 3) {
    return { kind: "box", boxIndex: Number(parts[1]), slotIndex: Number(parts[2]) };
  }
  throw new Error(`Localização inválida: ${location}`);
}

function isPartyLocation(location) {
  return String(location || "").startsWith("party:");
}

function isBoxLocation(location) {
  return String(location || "").startsWith("box:");
}

function locationLabel(location, boxState = null) {
  try {
    const parsed = parseLocation(location);
    if (parsed.kind === "party") return `Party · slot ${parsed.index + 1}`;
    const boxName = boxState?.box_names?.[parsed.boxIndex] || `Box ${parsed.boxIndex + 1}`;
    return `${boxName} · slot ${parsed.slotIndex + 1}`;
  } catch (_error) {
    return String(location || "");
  }
}

function payloadNationalDexId(payload) {
  if (!payload) return null;
  if (payload.canonical && payload.canonical.species && payload.canonical.species.national_dex_id) {
    return Number(payload.canonical.species.national_dex_id);
  }
  if (payload.national_dex_id) return Number(payload.national_dex_id);
  return nativeToNational(Number(payload.generation || 0), Number(payload.species_id || 0)) || null;
}

function pokemonByLocation(save, location) {
  if (!save || !location) return null;
  if (isPartyLocation(location)) return (save.party || []).find((pokemon) => pokemon.location === location) || null;
  if (isBoxLocation(location)) return (save.boxes?.pokemon || []).find((pokemon) => pokemon.location === location) || null;
  return null;
}

function renderPokemonSummaryHtml(pokemonLike, textOverride = "", options = {}) {
  if (!pokemonLike) return "-";
  const variant = String(options.variant || "default");
  const payloadDexId = payloadNationalDexId(pokemonLike);
  const explicitDexId = Number(pokemonLike.national_dex_id || 0) || null;
  const nationalDexId = payloadDexId ?? explicitDexId;
  const unownForm = cleanName(pokemonLike.unown_form || pokemonLike.metadata?.unown_form);
  const isShiny = Boolean(pokemonLike.is_shiny || pokemonLike.canonical?.is_shiny || pokemonLike.metadata?.is_shiny);

  let text = textOverride || pokemonLike.display_summary || normalizePokemonDisplay(pokemonLike);

  // Remove redundant item info from summary text for the trade variant
  if (variant === "trade") {
    text = text.split(" — ")[0]; // Remove everything after the species/nickname part
  }

  const escapedText = escapeHtml(text);
  const summaryClass = variant === "trade" ? "pokemon-summary pokemon-summary-trade" : "pokemon-summary";
  const spriteClass = variant === "trade" ? "pokemon-sprite pokemon-sprite-trade" : "pokemon-sprite";
  return `
    <span class="${summaryClass}${isShiny ? ' is-shiny' : ''}">
      ${pokemonSpriteImgHtml(nationalDexId, text, spriteClass, unownForm, isShiny)}
      <span class="pokemon-summary-text">${escapedText}</span>
    </span>
  `;
}
function canonicalSpeciesFor(generation, speciesId, speciesName) {
  const nationalId = nativeToNational(generation, speciesId);
  const resolvedName = speciesNameFor(generation, speciesId, speciesName);
  return {
    national_dex_id: nationalId || speciesId,
    source_species_id: speciesId,
    source_species_id_space: generation === 1 ? "gen1_internal" : generation === 2 ? "national_dex" : "gen3_internal",
    name: resolvedName
  };
}

function canonicalFromPayload(payload) {
  if (!payload.canonical) return null;
  const canonical = payload.canonical;
  const species = canonical.species || {
    national_dex_id: canonical.species_national_id || nativeToNational(payload.generation, payload.species_id),
    source_species_id: payload.species_id,
    source_species_id_space: payload.generation === 1 ? "gen1_internal" : payload.generation === 2 ? "national_dex" : "gen3_internal",
    name: canonical.species_name || payload.species_name
  };
  return {
    source_generation: canonical.source_generation || payload.generation,
    source_game: canonical.source_game || payload.game,
    species,
    species_national_id: species.national_dex_id,
    species_name: species.name || canonical.species_name || payload.species_name,
    nickname: canonical.nickname || payload.nickname || species.name || payload.species_name,
    level: Number(canonical.level || payload.level || 1),
    experience: Number(canonical.experience || payload.experience || 0),
    ot_name: canonical.ot_name || payload.ot_name || "TRAINER",
    trainer_id: Number(canonical.trainer_id || payload.trainer_id || 0),
    moves: canonical.moves || [],
    held_item: canonical.held_item || null,
    ability: canonical.ability || null,
    nature: canonical.nature || null,
    metadata: canonical.metadata || {}
  };
}

let loadedSave = null;
let selectedLocation = "party:0";
let selectedInventoryItem = null;
let pendingMoveSourceLocation = null;
const sessionState = {
  action: null,
  pending: false,
  joined: false,
  tradeJoined: false,
  battleJoined: false,
  saveLocked: false
};
const tradeState = {
  localPayload: null,
  peerPayload: null,
  preparedTradeBackup: null,
  pendingTradePayload: null,
  hasJoinedRoom: false,
  roomReady: false,
  roundActive: false
};
const battleState = {
  hasJoinedBattleRoom: false,
  roomReady: false,
  readyToConfirm: false,
  currentBattleId: null,
  currentBattleRequest: null
};
const nonHoldableCategories = new Set(["badge", "system", "key_item", "tm", "hm", "tmhm", "unused"]);

const pokemonUiRenderer = pokemonUiModule?.createPokemonUiRenderer({
  canonicalFromPayload,
  itemName,
  moveName,
  abilityName,
  cleanName,
  escapeHtml,
  normalizePokemonDisplay,
  payloadNationalDexId,
  renderPokemonSummaryHtml,
  getLoadedSaveGeneration: () => loadedSave?.generation,
  getLoadedSaveGame: () => loadedSave?.game
});

function renderOfferCard(summaryEl, detailsEl, pokemonLike, textOverride = "", options = {}) {
  pokemonUiRenderer?.renderOfferCard(summaryEl, detailsEl, pokemonLike, textOverride, options);
}

const tradePreviewRenderer = tradePreviewModule?.createTradePreviewRenderer({
  elements: {
    tradeCompatibilityPreviewEl,
    tradeEvolutionPreviewEl,
    localOfferDetailsEl,
    peerOfferDetailsEl
  },
  canonicalFromPayload,
  payloadNationalDexId,
  itemName,
  sameName,
  cleanName,
  escapeHtml,
  normalizePokemonDisplay,
  renderPokemonSummaryHtml,
  speciesNames,
  simpleTradeEvolutionByNational,
  itemTradeEvolutionRules,
  getLoadedSaveGeneration: () => loadedSave?.generation,
  pokemonSpriteUrl
});

const buildWebCompatibilityReport = webCompatibilityModule?.createCompatibilityBuilder({
  canonicalFromPayload,
  payloadNationalDexId,
  nationalToNative,
  speciesExistsInGeneration,
  itemName,
  itemCategory,
  moveName,
  getLoadedSaveGeneration: () => loadedSave?.generation,
  getLoadedSave: () => loadedSave,
  resolveItemTransferDecisionForSave
});

// Bridge para controladores acessarem funções do app.js
window.POKECABLE_APP_CONTROLLER_BRIDGE = {
  setSelectedTradePokemon: (loc) => setSelectedTradePokemon(loc)
};

const inventoryUiController = inventoryUiModule?.createInventoryUiController({
  getLoadedSave: () => loadedSave,
  getSelectedLocation: () => selectedLocation,
  getSelectedInventoryItem: () => selectedInventoryItem,
  getPendingMoveSourceLocation: () => pendingMoveSourceLocation,
  getTradeState: () => tradeState,
  getPartyCapacity: () => loadedSave?.generation === 3 ? gen3.partyCapacity : Number(loadedSave?.layout?.partyCapacity || gen1.partyCapacity),
  getBoxCapacity: () => loadedSave?.generation === 3 ? gen3.boxCapacity : Number(loadedSave?.layout?.boxCapacity || gen1.boxCapacity),
  cleanName,
  abilityName,
  escapeHtml,
  escapeAttribute,
  renderPokemonSummaryHtml,
  relocatePokemonWithinSave,
  syncAfterSaveMutation: () => updatePokemonOptions(),
  elements: {
    setupBagPreviewEl,
    setupPcPreviewEl,
    setupPokemonPcPreviewEl,
    tradeBoxPreviewEl,
    setupTogglePokemonPcButton,
    tradeTogglePokemonPcButton,
    pokemonDetailDrawerEl,
    pokemonDetailDrawerBackdropEl,
    pokemonDetailDrawerTitleEl,
    pokemonDetailDrawerBodyEl
  }
});

const saveManagementController = saveManagementModule?.createSaveManagementController({
  getLoadedSave: () => loadedSave,
  getSelectedLocation: () => selectedLocation,
  setSelectedLocation: (value) => { selectedLocation = value; pokemonChoiceEl.value = value; },
  getSelectedInventoryItem: () => selectedInventoryItem,
  setSelectedInventoryItem: (value) => { selectedInventoryItem = value; },
  getPendingMoveSourceLocation: () => pendingMoveSourceLocation,
  setPendingMoveSourceLocation: (value) => { pendingMoveSourceLocation = value; },
  getTradeState: () => tradeState,
  parseLocation,
  pokemonByLocation,
  locationLabel,
  cleanName,
  normalizePokemonDisplay,
  renderPokemonSummaryHtml,
  renderOfferCard,
  clearTradePreviews,
  relocatePokemonWithinSave,
  hasBagSpaceInSave,
  hasPcSpaceInSave,
  storeItemInBagForSave,
  storeItemInPcForSave,
  clearHeldItemInSave,
  setHeldItemInSave,
  removeItemFromPocket,
  refreshLoadedSaveCollections,
  nonHoldableCategories,
  syncTransientUi: () => {
    updateInventoryPreview();
    updatePokemonPcPreview();
    updateSelectionUi();
    tradeFlowController?.syncButtons();
    refreshSessionUi();
  },
  syncAfterSaveMutation: () => updatePokemonOptions(),
  activateTab,
  elements: {
    tradeSelectedSummaryEl,
    setupSelectedSummaryEl,
    setupSelectionDetailEl,
    selectedInventoryItemStatusEl,
    saveManagementStatusEl,
    startMovePokemonButton,
    cancelMovePokemonButton,
    removeHeldItemButton,
    applyHeldItemButton,
    setupPartyPreviewEl,
    tradePartyPreviewEl,
    localOfferEl,
    localOfferDetailsEl
  }
});

const tradeFlowController = tradeFlowModule?.createTradeFlowController({
  state: tradeState,
  getLoadedSave: () => loadedSave,
  getSelectedLocation: () => selectedLocation,
  getSelectedPokemon: () => pokemonByLocation(loadedSave, selectedLocation),
  getRoomCredentials: () => ({
    roomName: document.querySelector("#roomName").value.trim(),
    password: document.querySelector("#roomPassword").value
  }),
  getSessionAction: () => sessionState.action,
  selectedPayload,
  supportedTradeModes,
  supportedProtocols,
  renderOfferCard,
  buildWebCompatibilityReport,
  renderTradeCompatibilityPreview,
  renderTradeEvolutionPreview,
  clearTradePreviews,
  send,
  setStatus,
  log,
  sha256Hex,
  downloadBlob,
  afterLocalSaveApplied: () => updatePokemonOptions(),
  elements: {
    sendOfferButton: sendTradeOfferButton,
    confirmButton,
    cancelButton,
    downloadArea,
    peerOfferEl,
    peerOfferDetailsEl,
    localOfferEl,
    localOfferDetailsEl
  }
});

const battleFlowController = battleFlowModule?.createBattleFlowController({
  state: battleState,
  getLoadedSave: () => loadedSave,
  getRoomCredentials: () => ({
    roomName: document.querySelector("#roomName").value.trim(),
    password: document.querySelector("#roomPassword").value
  }),
  send,
  setStatus,
  setBattleStatus,
  log,
  battleLog,
  elements: {
    battleLogEl,
    battleActionsEl,
    battleFormatEl,
    battleTeamCountEl,
    sendBattleTeamButton,
    confirmBattleButton,
    forfeitBattleButton
  }
});

function clearTradePreviews() {
  tradePreviewRenderer?.clearTradePreviews();
}

function renderTradeCompatibilityPreview(payload, report) {
  tradePreviewRenderer?.renderTradeCompatibilityPreview(payload, report);
}

function renderTradeEvolutionPreview(payload, report) {
  tradePreviewRenderer?.renderTradeEvolutionPreview(payload, report);
}

const gen1 = {
  playerNameOffset: 0x2598,
  partyOffset: 0x2f2c,
  dataOffset: 0x2f34,
  otOffset: 0x303c,
  nickOffset: 0x307e,
  currentBoxOffset: 0x284c,
  currentBoxDataOffset: 0x30c0,
  checksumStart: 0x2598,
  checksumEnd: 0x3522,
  checksumOffset: 0x3523,
  partyCapacity: 6,
  boxCapacity: 20,
  monSize: 44,
  boxMonSize: 33,
  boxCount: 12,
  boxDataSize: 0x462,
  boxOtOffset: 0x2aa,
  boxNickOffset: 0x386,
  nameSize: 11
};
gen1.storedBoxOffsets = Array.from({ length: 12 }, (_, index) => (index < 6 ? 0x4000 : 0x6000) + (index % 6) * gen1.boxDataSize);

const gen2 = {
  playerNameOffset: 0x200b,
  partyOffset: 0x2865,
  primaryStart: 0x2009,
  primaryEnd: 0x2b82,
  primaryChecksum: 0x2d0d,
  secondaryStart: 0x1209,
  secondaryEnd: 0x1d82,
  secondaryChecksum: 0x1f0d,
  currentBoxOffset: 0x2700,
  boxNamesOffset: 0x2703,
  currentBoxDataOffset: 0x2d10,
  partyCapacity: 6,
  boxCapacity: 20,
  monSize: 48,
  boxMonSize: 32,
  boxCount: 14,
  boxNameSize: 9,
  boxOtOffset: 0x296,
  boxNickOffset: 0x372,
  nameSize: 11
};
gen2.headerSize = 1 + gen2.partyCapacity + 1;
gen2.dataOffset = gen2.partyOffset + gen2.headerSize;
gen2.otOffset = gen2.dataOffset + gen2.partyCapacity * gen2.monSize;
gen2.nickOffset = gen2.otOffset + gen2.partyCapacity * gen2.nameSize;
gen2.storedBoxOffsets = [...Array.from({ length: 7 }, (_, index) => 0x4000 + index * 0x450), ...Array.from({ length: 7 }, (_, index) => 0x6000 + index * 0x450)];

const gen2GoldSilver = {
  playerNameOffset: 0x200b,
  partyOffset: 0x288a,
  primaryStart: 0x2009,
  primaryEnd: 0x2d68,
  primaryChecksum: 0x2d69,
  currentBoxOffset: 0x2724,
  boxNamesOffset: 0x2727,
  currentBoxDataOffset: 0x2d6c,
  partyCapacity: 6,
  boxCapacity: 20,
  monSize: 48,
  boxMonSize: 32,
  boxCount: 14,
  boxNameSize: 9,
  boxOtOffset: 0x296,
  boxNickOffset: 0x372,
  nameSize: 11
};
gen2GoldSilver.headerSize = 1 + gen2GoldSilver.partyCapacity + 1;
gen2GoldSilver.dataOffset = gen2GoldSilver.partyOffset + gen2GoldSilver.headerSize;
gen2GoldSilver.otOffset = gen2GoldSilver.dataOffset + gen2GoldSilver.partyCapacity * gen2GoldSilver.monSize;
gen2GoldSilver.nickOffset = gen2GoldSilver.otOffset + gen2GoldSilver.partyCapacity * gen2GoldSilver.nameSize;
gen2GoldSilver.storedBoxOffsets = [...Array.from({ length: 7 }, (_, index) => 0x4000 + index * 0x450), ...Array.from({ length: 7 }, (_, index) => 0x6000 + index * 0x450)];

const gen3 = {
  playerNameOffset: 0x0000,
  sectorDataSize: 3968,
  sectorSize: 4096,
  sectorsPerSlot: 14,
  signature: 0x08012025,
  monSize: 100,
  secureOffset: 32,
  secureSize: 48,
  partyCapacity: 6,
  boxMonSize: 80,
  boxCount: 14,
  boxCapacity: 30,
  pcBufferBoxesOffset: 0x0004,
  pcBufferNamesOffset: 0x8344,
  boxNameSize: 9,
  layouts: [
    { name: "rse", game: "pokemon_emerald", partyCountOffset: 0x234, partyOffset: 0x238 },
    { name: "frlg", game: "pokemon_firered", partyCountOffset: 0x34, partyOffset: 0x38 }
  ],
  substructOrders: [
    [0, 1, 2, 3], [0, 1, 3, 2], [0, 2, 1, 3], [0, 3, 1, 2],
    [0, 2, 3, 1], [0, 3, 2, 1], [1, 0, 2, 3], [1, 0, 3, 2],
    [2, 0, 1, 3], [3, 0, 1, 2], [2, 0, 3, 1], [3, 0, 2, 1],
    [1, 2, 0, 3], [1, 3, 0, 2], [2, 1, 0, 3], [3, 1, 0, 2],
    [2, 3, 0, 1], [3, 2, 0, 1], [1, 2, 3, 0], [1, 3, 2, 0],
    [2, 1, 3, 0], [3, 1, 2, 0], [2, 3, 1, 0], [3, 2, 1, 0]
  ]
};

const inventoryLayouts = {
  pokemon_red: {
    generation: 1,
    pockets: {
      bag_items: { storage: "bag", offset: 0x25c9, capacity: 20, encoding: "counted_item_pairs_u8", maxStack: 99 },
      pc_items: { storage: "pc", offset: 0x27e6, capacity: 50, encoding: "counted_item_pairs_u8", maxStack: 99 }
    }
  },
  pokemon_blue: {
    generation: 1,
    pockets: {
      bag_items: { storage: "bag", offset: 0x25c9, capacity: 20, encoding: "counted_item_pairs_u8", maxStack: 99 },
      pc_items: { storage: "pc", offset: 0x27e6, capacity: 50, encoding: "counted_item_pairs_u8", maxStack: 99 }
    }
  },
  pokemon_yellow: {
    generation: 1,
    pockets: {
      bag_items: { storage: "bag", offset: 0x25c9, capacity: 20, encoding: "counted_item_pairs_u8", maxStack: 99 },
      pc_items: { storage: "pc", offset: 0x27e6, capacity: 50, encoding: "counted_item_pairs_u8", maxStack: 99 }
    }
  },
  pokemon_gold: {
    generation: 2,
    pockets: {
      tm_hm: { storage: "bag", offset: 0x23e6, capacity: 57, encoding: "tmhm_quantity_array", maxStack: 99 },
      items: { storage: "bag", offset: 0x241f, capacity: 20, encoding: "counted_item_pairs_u8", maxStack: 99 },
      key_items: { storage: "bag", offset: 0x2449, capacity: 26, encoding: "counted_item_ids", maxStack: 1 },
      balls: { storage: "bag", offset: 0x2464, capacity: 12, encoding: "counted_item_pairs_u8", maxStack: 99 },
      pc_items: { storage: "pc", offset: 0x247e, capacity: 50, encoding: "counted_item_pairs_u8", maxStack: 99 }
    }
  },
  pokemon_silver: {
    generation: 2,
    pockets: {
      tm_hm: { storage: "bag", offset: 0x23e6, capacity: 57, encoding: "tmhm_quantity_array", maxStack: 99 },
      items: { storage: "bag", offset: 0x241f, capacity: 20, encoding: "counted_item_pairs_u8", maxStack: 99 },
      key_items: { storage: "bag", offset: 0x2449, capacity: 26, encoding: "counted_item_ids", maxStack: 1 },
      balls: { storage: "bag", offset: 0x2464, capacity: 12, encoding: "counted_item_pairs_u8", maxStack: 99 },
      pc_items: { storage: "pc", offset: 0x247e, capacity: 50, encoding: "counted_item_pairs_u8", maxStack: 99 }
    }
  },
  pokemon_crystal: {
    generation: 2,
    pockets: {
      tm_hm: { storage: "bag", offset: 0x23e7, capacity: 57, encoding: "tmhm_quantity_array", maxStack: 99 },
      items: { storage: "bag", offset: 0x2420, capacity: 20, encoding: "counted_item_pairs_u8", maxStack: 99 },
      key_items: { storage: "bag", offset: 0x244a, capacity: 26, encoding: "counted_item_ids", maxStack: 1 },
      balls: { storage: "bag", offset: 0x2465, capacity: 12, encoding: "counted_item_pairs_u8", maxStack: 99 },
      pc_items: { storage: "pc", offset: 0x247f, capacity: 50, encoding: "counted_item_pairs_u8", maxStack: 99 }
    }
  },
  pokemon_ruby: {
    generation: 3,
    pockets: {
      pc_items: { storage: "pc", offset: 0x0498, capacity: 50, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: false },
      items: { storage: "bag", offset: 0x0560, capacity: 20, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      key_items: { storage: "bag", offset: 0x05b0, capacity: 20, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      balls: { storage: "bag", offset: 0x0600, capacity: 16, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      tm_hm: { storage: "bag", offset: 0x0640, capacity: 64, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      berries: { storage: "bag", offset: 0x0740, capacity: 46, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true }
    }
  },
  pokemon_sapphire: {
    generation: 3,
    pockets: {
      pc_items: { storage: "pc", offset: 0x0498, capacity: 50, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: false },
      items: { storage: "bag", offset: 0x0560, capacity: 20, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      key_items: { storage: "bag", offset: 0x05b0, capacity: 20, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      balls: { storage: "bag", offset: 0x0600, capacity: 16, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      tm_hm: { storage: "bag", offset: 0x0640, capacity: 64, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      berries: { storage: "bag", offset: 0x0740, capacity: 46, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true }
    }
  },
  pokemon_emerald: {
    generation: 3,
    pockets: {
      pc_items: { storage: "pc", offset: 0x0498, capacity: 50, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: false },
      items: { storage: "bag", offset: 0x0560, capacity: 30, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      key_items: { storage: "bag", offset: 0x05d8, capacity: 30, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      balls: { storage: "bag", offset: 0x0650, capacity: 16, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      tm_hm: { storage: "bag", offset: 0x0690, capacity: 64, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      berries: { storage: "bag", offset: 0x0790, capacity: 46, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true }
    }
  },
  pokemon_firered: {
    generation: 3,
    pockets: {
      pc_items: { storage: "pc", offset: 0x0298, capacity: 30, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: false },
      items: { storage: "bag", offset: 0x0310, capacity: 42, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      key_items: { storage: "bag", offset: 0x03b8, capacity: 30, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      balls: { storage: "bag", offset: 0x0430, capacity: 13, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      tm_hm: { storage: "bag", offset: 0x0464, capacity: 58, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      berries: { storage: "bag", offset: 0x054c, capacity: 43, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true }
    }
  },
  pokemon_leafgreen: {
    generation: 3,
    pockets: {
      pc_items: { storage: "pc", offset: 0x0298, capacity: 30, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: false },
      items: { storage: "bag", offset: 0x0310, capacity: 42, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      key_items: { storage: "bag", offset: 0x03b8, capacity: 30, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      balls: { storage: "bag", offset: 0x0430, capacity: 13, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      tm_hm: { storage: "bag", offset: 0x0464, capacity: 58, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true },
      berries: { storage: "bag", offset: 0x054c, capacity: 43, encoding: "item_slots_u16_quantity_u16", maxStack: 999, xorQuantity: true }
    }
  }
};

function log(message) {
  const time = new Date().toLocaleTimeString();
  eventLogEl.textContent += `[${time}] ${message}\n`;
  eventLogEl.scrollTop = eventLogEl.scrollHeight;
}

function battleLog(message) {
  if (!battleLogEl) return;
  battleLogEl.textContent += `${message}\n`;
  battleLogEl.scrollTop = battleLogEl.scrollHeight;
}

function setStatus(message) {
  tradeStatusEl.textContent = message;
}

function setBattleStatus(message) {
  if (battleStatusEl) battleStatusEl.textContent = message;
}

function setSessionStatus(message, detail = "") {
  if (sessionStatusEl) sessionStatusEl.textContent = message;
  if (sessionDetailEl) sessionDetailEl.textContent = detail || "A mesma sessão web mantém troca e batalha sob o mesmo nome de sala.";
}

function supportedTradeModes(generation) {
  void generation;
  return ["same_generation", "time_capsule_gen1_gen2", "forward_transfer_to_gen3", "legacy_downconvert_experimental"];
}

function supportedProtocols() {
  return ["raw_same_generation", "canonical_cross_generation"];
}

function roomCredentialsReady() {
  const roomName = roomNameEl.value.trim();
  const password = roomPasswordEl.value;
  return Boolean(roomName && password);
}

function clearLoadedSave() {
  loadedSave = null;
  selectedLocation = "party:0";
  selectedInventoryItem = null;
  pendingMoveSourceLocation = null;
  sessionState.saveLocked = false;
  saveFileEl.disabled = false;
  saveFileEl.value = "";
  saveSummaryEl.innerHTML = "<span>Nenhum save carregado</span><strong>Gen 1, Gen 2 e Gen 3 são detectadas pelo arquivo.</strong>";
  setupSaveStageEl?.classList.remove("setup-stage-hidden");
  setupRoomStageEl?.classList.add("setup-stage-hidden");
  setupChoiceStageEl?.classList.add("setup-stage-hidden");
  if (tradePartyLabelEl) tradePartyLabelEl.textContent = "Sua Party";
  if (battleSaveStatusEl) battleSaveStatusEl.textContent = "Nenhum save carregado.";
}

function loadedSaveHeadline(save) {
  if (!save) return "Nenhum save carregado";
  const playerName = cleanName(save.player_name || "");
  return playerName ? `${save.label} · ${playerName}` : save.label;
}

function getActiveTab() {
  const activeTabButton = tabButtons.find((button) => button.classList.contains("active"));
  return activeTabButton ? activeTabButton.dataset.tab : "setup";
}

function refreshSessionUi() {
  const hasLoadedSave = Boolean(loadedSave);
  const credentialsReady = roomCredentialsReady();
  const canPrepareSession = hasLoadedSave && credentialsReady && !sessionState.joined && !sessionState.pending;
  const roomChoiceReady = hasLoadedSave && sessionState.joined;
  const isSetupTab = getActiveTab() === "setup";

  if (hasLoadedSave && tradePartyLabelEl) {
    const playerName = cleanName(loadedSave.player_name || "");
    tradePartyLabelEl.textContent = playerName ? `Party de ${playerName}` : "Sua Party";
  }

  accessSessionButton.disabled = !canPrepareSession;
  leaveSessionButton.disabled = !(sessionState.joined || sessionState.pending);
  
  const inputsDisabled = sessionState.joined || sessionState.pending;
  roomNameEl.disabled = inputsDisabled;
  roomPasswordEl.disabled = inputsDisabled;

  tabButtons.forEach((button) => {
    if (button.dataset.tab === "trade" || button.dataset.tab === "battle") {
      button.disabled = !roomChoiceReady;
    }
  });

  if (setupSaveStageEl) setupSaveStageEl.classList.toggle("setup-stage-hidden", hasLoadedSave);
  if (setupRoomStageEl) setupRoomStageEl.classList.toggle("setup-stage-hidden", !hasLoadedSave || sessionState.joined);
  if (setupChoiceStageEl) setupChoiceStageEl.classList.toggle("setup-stage-hidden", !roomChoiceReady);
  
  // Garantir que os previews sejam atualizados
  if (hasLoadedSave) {
    if (isSetupTab) updateSetupPartyPreview();
    if (getActiveTab() === "trade") updateTradePartyPreview();
  }

  tradeFlowController?.syncButtons();
  battleFlowController?.syncButtons();
  
  if (!loadedSave) {
    setSessionStatus("Carregue um save local.");
    return;
  }
  if (!sessionState.joined) {
    if (sessionState.pending) {
      setSessionStatus("Conectando ao servidor...", "Aguardando confirmação da sala.");
      return;
    }
    setSessionStatus("Save carregado.", "Defina a sala e senha para acessar.");
    return;
  }
  setSessionStatus("Sessão ativa.", "Escolha troca ou batalha.");
}

function activateTab(tabName) {
  const targetButton = tabButtons.find((button) => button.dataset.tab === tabName);
  if (targetButton?.disabled) return;
  tabButtons.forEach((button) => {
    const active = button.dataset.tab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  });
  tabPanels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.tabPanel === tabName);
  });
  refreshSessionUi();
}

function wsUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  // Se estiver rodando localmente na porta 8080 (servidor estático), 
  // tenta conectar no backend na porta 8000 por padrão.
  if (window.location.port === "8080" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    if (window.location.port === "8080") {
      return `${protocol}//${window.location.hostname}:8000/ws`;
    }
  }
  return `${protocol}//${window.location.host}/ws`;
}

const wsClient = wsClientModule?.createWsClient({
  wsUrl,
  statusEl,
  onMessage: (message) => {
    handleMessage(message);
  },
  onClosed: () => {
    resetSessionState();
    confirmButton.disabled = true;
    cancelButton.disabled = true;
    sendTradeOfferButton.disabled = true;
    sendBattleTeamButton.disabled = true;
    confirmBattleButton.disabled = true;
    forfeitBattleButton.disabled = true;
    setStatus("Conexao encerrada.");
    setSessionStatus("Conexão encerrada.", "Reabra a sessão para continuar usando a mesma sala.");
    battleFlowController?.handleBattleSocketClosed();
  }
});

function readLe16(data, offset) {
  return data[offset] | (data[offset + 1] << 8);
}

function writeLe16(data, offset, value) {
  data[offset] = value & 0xff;
  data[offset + 1] = (value >> 8) & 0xff;
}

function readLe32(data, offset) {
  return (data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16) | (data[offset + 3] << 24)) >>> 0;
}

function writeLe32(data, offset, value) {
  data[offset] = value & 0xff;
  data[offset + 1] = (value >>> 8) & 0xff;
  data[offset + 2] = (value >>> 16) & 0xff;
  data[offset + 3] = (value >>> 24) & 0xff;
}

function bytesToBase64(bytes) {
  let binary = "";
  for (let index = 0; index < bytes.length; index += 8192) {
    binary += String.fromCharCode(...bytes.slice(index, index + 8192));
  }
  return btoa(binary);
}

async function sha256Hex(bytes) {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest)).map((value) => value.toString(16).padStart(2, "0")).join("");
}

function base64ToBytes(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

function decodeGbcText(bytes) {
  const chars = [];
  for (const byte of bytes) {
    if (byte === 0x50 || byte === 0xff || byte === 0x00) break;
    if (byte >= 0x80 && byte <= 0x99) chars.push(String.fromCharCode(65 + byte - 0x80));
    else if (byte >= 0xa0 && byte <= 0xb9) chars.push(String.fromCharCode(97 + byte - 0xa0));
    else if (byte === 0x7f) chars.push(" ");
    else if (byte === 0xe3) chars.push("-");
    else if (byte >= 0xf6) chars.push(String(byte - 0xf6));
    else chars.push("?");
  }
  return chars.join("").trim();
}

function decodeGen3Text(bytes) {
  const chars = [];
  for (const byte of bytes) {
    if (byte === 0xff) break;
    if (byte >= 0xbb && byte <= 0xd4) chars.push(String.fromCharCode(65 + byte - 0xbb));
    else if (byte >= 0xd5 && byte <= 0xee) chars.push(String.fromCharCode(97 + byte - 0xd5));
    else if (byte >= 0xa1 && byte <= 0xaa) chars.push(String(byte - 0xa1));
    else if (byte === 0x00) chars.push(" ");
    else if (byte === 0xad) chars.push(".");
    else if (byte === 0xae) chars.push("-");
    else if (byte === 0xb8) chars.push(",");
    else chars.push("?");
  }
  return chars.join("").trim();
}

function encodeGbcText(text, size = 11) {
  const bytes = new Uint8Array(size);
  bytes.fill(0x50);
  const value = String(text || "").slice(0, size - 1);
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 65 && code <= 90) bytes[index] = 0x80 + code - 65;
    else if (code >= 97 && code <= 122) bytes[index] = 0xa0 + code - 97;
    else if (code >= 48 && code <= 57) bytes[index] = 0xf6 + code - 48;
    else if (value[index] === " ") bytes[index] = 0x7f;
    else if (value[index] === "-") bytes[index] = 0xe3;
    else bytes[index] = 0x7f;
  }
  return bytes;
}

function encodeGen3Text(text, size) {
  const bytes = new Uint8Array(size);
  bytes.fill(0xff);
  const value = String(text || "").slice(0, size);
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 65 && code <= 90) bytes[index] = 0xbb + code - 65;
    else if (code >= 97 && code <= 122) bytes[index] = 0xd5 + code - 97;
    else if (code >= 48 && code <= 57) bytes[index] = 0xa1 + code - 48;
    else if (value[index] === " ") bytes[index] = 0x00;
    else if (value[index] === ".") bytes[index] = 0xad;
    else if (value[index] === "-") bytes[index] = 0xae;
    else bytes[index] = 0x00;
  }
  return bytes;
}

function sumRange(data, start, end) {
  let sum = 0;
  for (let index = start; index <= end; index += 1) sum = (sum + data[index]) & 0xffff;
  return sum;
}

function gen1Checksum(data) {
  let value = 0xff;
  for (let index = gen1.checksumStart; index <= gen1.checksumEnd; index += 1) {
    value = (value - data[index]) & 0xff;
  }
  return value;
}

function validateGen1Save(data) {
  if (data.length !== 0x8000) return false;
  const count = data[gen1.partyOffset];
  if (count > gen1.partyCapacity) return false;
  if (data[gen1.partyOffset + 1 + count] !== 0xff) return false;
  return gen1Checksum(data) === data[gen1.checksumOffset];
}

function validateGen2Save(data, constants) {
  if (data.length !== 0x8000) return false;
  const count = data[constants.partyOffset];
  if (count > constants.partyCapacity) return false;
  if (data[constants.partyOffset + 1 + count] !== 0xff) return false;
  const primary = sumRange(data, constants.primaryStart, constants.primaryEnd);
  const storedPrimary = readLe16(data, constants.primaryChecksum);
  if (primary === storedPrimary) return true;
  if (constants.secondaryStart === undefined) return false;
  const secondary = sumRange(data, constants.secondaryStart, constants.secondaryEnd);
  const storedSecondary = readLe16(data, constants.secondaryChecksum);
  return secondary === storedSecondary;
}

function parseGen1Party(save) {
  const party = [];
  const count = save.bytes[gen1.partyOffset];
  for (let index = 0; index < count; index += 1) {
    const monStart = gen1.dataOffset + index * gen1.monSize;
    const otStart = gen1.otOffset + index * gen1.nameSize;
    const nickStart = gen1.nickOffset + index * gen1.nameSize;
    const speciesId = save.bytes[monStart];
    const nationalId = nativeToNational(1, speciesId);
    const speciesName = speciesNameFor(1, speciesId, gen1InternalNames[speciesId]);
    const pokemon = {
      location: `party:${index}`,
      generation: 1,
      game: save.game,
      source_generation: 1,
      source_game: save.game,
      species_id: speciesId,
      species_name: speciesName,
      national_dex_id: nationalId,
      gender: null,
      level: save.bytes[monStart + 0x21],
      experience: (save.bytes[monStart + 0x0e] << 16) | (save.bytes[monStart + 0x0f] << 8) | save.bytes[monStart + 0x10],
      nickname: decodeGbcText(save.bytes.slice(nickStart, nickStart + gen1.nameSize)) || speciesName,
      ot_name: decodeGbcText(save.bytes.slice(otStart, otStart + gen1.nameSize)),
      trainer_id: (save.bytes[monStart + 0x0c] << 8) | save.bytes[monStart + 0x0d],
      moves: Array.from(save.bytes.slice(monStart + 0x08, monStart + 0x0c)).filter(Boolean)
    };
    pokemon.display_summary = normalizePokemonDisplay(pokemon);
    party.push(pokemon);
  }
  return party;
}

function parseGen1PlayerName(save) {
  return decodeGbcText(save.bytes.slice(gen1.playerNameOffset, gen1.playerNameOffset + gen1.nameSize)) || "Player";
}

function parseGen2Party(save) {
  const constants = save.layout;
  const count = save.bytes[constants.partyOffset];
  const party = [];
  for (let index = 0; index < count; index += 1) {
    const speciesEntry = save.bytes[constants.partyOffset + 1 + index];
    const monStart = constants.dataOffset + index * constants.monSize;
    const otStart = constants.otOffset + index * constants.nameSize;
    const nickStart = constants.nickOffset + index * constants.nameSize;
    const speciesId = save.bytes[monStart];
    const heldItemId = save.bytes[monStart + 0x01] || null;
    const attackDv = save.bytes[monStart + 0x15] >> 4;
    const defenseDv = save.bytes[monStart + 0x15] & 0x0f;
    const speedDv = save.bytes[monStart + 0x16] >> 4;
    const specialDv = save.bytes[monStart + 0x16] & 0x0f;
    const pokemon = {
      location: `party:${index}`,
      generation: 2,
      game: save.game,
      source_generation: 2,
      source_game: save.game,
      species_id: speciesId,
      species_name: speciesEntry === 0xfd ? "Egg" : speciesNameFor(2, speciesId),
      national_dex_id: speciesEntry === 0xfd ? null : speciesId,
      is_shiny: speciesEntry === 0xfd ? false : isShinyGen2(attackDv, defenseDv, speedDv, specialDv),
      gender: speciesEntry === 0xfd ? null : genderFromGen2AttackDv(speciesId, attackDv),
      unown_form: speciesEntry === 0xfd || speciesId !== 201 ? null : unownFormFromGen2Dvs(attackDv, defenseDv, speedDv, specialDv),
      level: save.bytes[monStart + 0x1f],
      experience: (save.bytes[monStart + 0x08] << 16) | (save.bytes[monStart + 0x09] << 8) | save.bytes[monStart + 0x0a],
      nickname: decodeGbcText(save.bytes.slice(nickStart, nickStart + constants.nameSize)),
      ot_name: decodeGbcText(save.bytes.slice(otStart, otStart + constants.nameSize)),
      trainer_id: (save.bytes[monStart + 0x06] << 8) | save.bytes[monStart + 0x07],
      held_item_id: heldItemId,
      held_item_name: itemName(heldItemId, 2),
      moves: Array.from(save.bytes.slice(constants.partyOffset + 1 + index === 0xfd ? 0 : monStart + 0x02, constants.partyOffset + 1 + index === 0xfd ? 0 : monStart + 0x06)).filter(Boolean),
      is_egg: speciesEntry === 0xfd
    };
    pokemon.display_summary = normalizePokemonDisplay(pokemon);
    party.push(pokemon);
  }
  return party;
}

function parseGen2PlayerName(save) {
  const constants = save.layout;
  return decodeGbcText(save.bytes.slice(constants.playerNameOffset, constants.playerNameOffset + constants.nameSize)) || "Player";
}

function parseGen1BoxSummary(save, raw, boxIndex, slotIndex, nicknameBytes, otBytes) {
  const speciesId = raw[0];
  const nationalId = nativeToNational(1, speciesId);
  const speciesName = speciesNameFor(1, speciesId, gen1InternalNames[speciesId]);
  const pokemon = {
    location: `box:${boxIndex}:${slotIndex}`,
    box_index: boxIndex,
    slot_index: slotIndex,
    generation: 1,
    game: save.game,
    source_generation: 1,
    source_game: save.game,
    species_id: speciesId,
    species_name: speciesName,
    national_dex_id: nationalId,
    gender: null,
    level: raw[0x03],
    experience: (raw[0x0e] << 16) | (raw[0x0f] << 8) | raw[0x10],
    nickname: decodeGbcText(nicknameBytes) || speciesName,
    ot_name: decodeGbcText(otBytes),
    trainer_id: (raw[0x0c] << 8) | raw[0x0d],
    moves: Array.from(raw.slice(0x08, 0x0c)).filter(Boolean)
  };
  pokemon.display_summary = normalizePokemonDisplay(pokemon);
  return pokemon;
}

function parseGen1Boxes(save) {
  const currentBox = save.bytes[gen1.currentBoxOffset] & 0x7f;
  const pokemon = [];
  for (let boxIndex = 0; boxIndex < gen1.boxCount; boxIndex += 1) {
    const offset = boxIndex === currentBox ? gen1.currentBoxDataOffset : gen1.storedBoxOffsets[boxIndex];
    const count = save.bytes[offset];
    if (count > gen1.boxCapacity) continue;
    for (let slotIndex = 0; slotIndex < count; slotIndex += 1) {
      const speciesId = save.bytes[offset + 1 + slotIndex];
      if (!speciesId || speciesId === 0xff) continue;
      const monStart = offset + 0x16 + slotIndex * gen1.boxMonSize;
      const otStart = offset + gen1.boxOtOffset + slotIndex * gen1.nameSize;
      const nickStart = offset + gen1.boxNickOffset + slotIndex * gen1.nameSize;
      pokemon.push(
        parseGen1BoxSummary(
          save,
          save.bytes.slice(monStart, monStart + gen1.boxMonSize),
          boxIndex,
          slotIndex,
          save.bytes.slice(nickStart, nickStart + gen1.nameSize),
          save.bytes.slice(otStart, otStart + gen1.nameSize)
        )
      );
    }
  }
  return {
    current_box: currentBox >= 0 && currentBox < gen1.boxCount ? currentBox : 0,
    box_names: Array.from({ length: gen1.boxCount }, (_, index) => `Box ${index + 1}`),
    pokemon
  };
}

function parseGen2BoxSummary(save, raw, boxIndex, slotIndex, nicknameBytes, otBytes, isEgg) {
  const speciesId = raw[0];
  const heldItemId = raw[0x01] || null;
  const speciesName = isEgg ? "Egg" : speciesNameFor(2, speciesId);
  const attackDv = raw[0x15] >> 4;
  const defenseDv = raw[0x15] & 0x0f;
  const speedDv = raw[0x16] >> 4;
  const specialDv = raw[0x16] & 0x0f;
  const pokemon = {
    location: `box:${boxIndex}:${slotIndex}`,
    box_index: boxIndex,
    slot_index: slotIndex,
    generation: 2,
    game: save.game,
    source_generation: 2,
    source_game: save.game,
    species_id: speciesId,
    species_name: speciesName,
    national_dex_id: isEgg ? null : speciesId,
    is_shiny: isEgg ? false : isShinyGen2(attackDv, defenseDv, speedDv, specialDv),
    gender: isEgg ? null : genderFromGen2AttackDv(speciesId, attackDv),
    unown_form: isEgg || speciesId !== 201 ? null : unownFormFromGen2Dvs(attackDv, defenseDv, speedDv, specialDv),
    level: raw[0x1f],
    experience: (raw[0x08] << 16) | (raw[0x09] << 8) | raw[0x0a],
    nickname: decodeGbcText(nicknameBytes) || speciesName,
    ot_name: decodeGbcText(otBytes),
    trainer_id: (raw[0x06] << 8) | raw[0x07],
    held_item_id: heldItemId,
    held_item_name: itemName(heldItemId, 2),
    moves: Array.from(raw.slice(0x02, 0x06)).filter(Boolean),
    is_egg: isEgg
  };
  pokemon.display_summary = normalizePokemonDisplay(pokemon);
  return pokemon;
}

function parseGen2Boxes(save) {
  const constants = save.layout;
  const currentBox = save.bytes[constants.currentBoxOffset] & 0x0f;
  const boxNames = Array.from({ length: constants.boxCount }, (_, index) => {
    const start = constants.boxNamesOffset + index * constants.boxNameSize;
    return decodeGbcText(save.bytes.slice(start, start + constants.boxNameSize)) || `Box ${index + 1}`;
  });
  const pokemon = [];
  for (let boxIndex = 0; boxIndex < constants.boxCount; boxIndex += 1) {
    const offset = boxIndex === currentBox ? constants.currentBoxDataOffset : constants.storedBoxOffsets[boxIndex];
    const count = save.bytes[offset];
    if (count > constants.boxCapacity) continue;
    for (let slotIndex = 0; slotIndex < count; slotIndex += 1) {
      const speciesEntry = save.bytes[offset + 1 + slotIndex];
      const isEgg = speciesEntry === 0xfd;
      const monStart = offset + 0x16 + slotIndex * constants.boxMonSize;
      const otStart = offset + constants.boxOtOffset + slotIndex * constants.nameSize;
      const nickStart = offset + constants.boxNickOffset + slotIndex * constants.nameSize;
      const raw = save.bytes.slice(monStart, monStart + constants.boxMonSize);
      if (!raw[0]) continue;
      pokemon.push(parseGen2BoxSummary(save, raw, boxIndex, slotIndex, save.bytes.slice(nickStart, nickStart + constants.nameSize), save.bytes.slice(otStart, otStart + constants.nameSize), isEgg));
    }
  }
  return {
    current_box: currentBox >= 0 && currentBox < constants.boxCount ? currentBox : 0,
    box_names: boxNames,
    pokemon
  };
}

function inventoryLayoutForSave(save) {
  return inventoryLayouts[save.game] || null;
}

function readCountedItemPairs(bytes, offset) {
  const count = bytes[offset];
  const items = [];
  let cursor = offset + 1;
  for (let index = 0; index < count; index += 1) {
    const itemId = bytes[cursor];
    const quantity = bytes[cursor + 1];
    if (itemId === 0xff) break;
    items.push([itemId, quantity]);
    cursor += 2;
  }
  return items;
}

function writeCountedItemPairs(bytes, offset, capacity, items) {
  if (items.length > capacity) throw new Error("Pocket excedeu a capacidade suportada.");
  bytes[offset] = items.length;
  let cursor = offset + 1;
  for (const [itemId, quantity] of items) {
    bytes[cursor] = itemId;
    bytes[cursor + 1] = quantity;
    cursor += 2;
  }
  bytes[cursor] = 0xff;
  cursor += 1;
  const limit = offset + 1 + capacity * 2 + 1;
  while (cursor < limit) {
    bytes[cursor] = 0;
    cursor += 1;
  }
}

function readCountedItemIds(bytes, offset) {
  const count = bytes[offset];
  const items = [];
  let cursor = offset + 1;
  for (let index = 0; index < count; index += 1) {
    const itemId = bytes[cursor];
    if (itemId === 0xff) break;
    items.push(itemId);
    cursor += 1;
  }
  return items;
}

function writeCountedItemIds(bytes, offset, capacity, items) {
  if (items.length > capacity) throw new Error("Pocket excedeu a capacidade suportada.");
  bytes[offset] = items.length;
  let cursor = offset + 1;
  for (const itemId of items) {
    bytes[cursor] = itemId;
    cursor += 1;
  }
  bytes[cursor] = 0xff;
  cursor += 1;
  const limit = offset + 1 + capacity + 1;
  while (cursor < limit) {
    bytes[cursor] = 0;
    cursor += 1;
  }
}

function readTmhmQuantities(bytes, offset) {
  const items = {};
  for (let itemId = 0xbf; itemId < 0xbf + 57; itemId += 1) {
    const quantity = bytes[offset + (itemId - 0xbf)];
    if (quantity) items[itemId] = quantity;
  }
  return items;
}

function writeTmhmQuantity(bytes, offset, itemId, quantity) {
  if (itemId < 0xbf || itemId >= 0xbf + 57) throw new Error("Item nao pertence ao pocket TM/HM da Gen 2.");
  bytes[offset + (itemId - 0xbf)] = quantity;
}

function gen3SecurityKeyForSave(save) {
  return readLe32(save.bytes, save.slot.sectionOffsets[0] + 0xac);
}

function readGen3ItemSlots(save, pocketName) {
  const layout = inventoryLayoutForSave(save);
  const pocket = layout?.pockets?.[pocketName];
  if (!pocket) return {};
  const base = save.slot.sectionOffsets[1] + pocket.offset;
  const key = pocket.xorQuantity ? gen3SecurityKeyForSave(save) : 0;
  const items = {};
  for (let index = 0; index < pocket.capacity; index += 1) {
    const slotOffset = base + index * 4;
    const itemId = readLe16(save.bytes, slotOffset);
    const quantity = readLe16(save.bytes, slotOffset + 2) ^ key;
    if (itemId) items[itemId] = quantity;
  }
  return items;
}

function writeGen3ItemSlots(save, pocketName, items) {
  const layout = inventoryLayoutForSave(save);
  const pocket = layout?.pockets?.[pocketName];
  if (!pocket) throw new Error(`Pocket Gen 3 desconhecido: ${pocketName}`);
  if (items.length > pocket.capacity) throw new Error("Pocket excedeu a capacidade suportada.");
  const base = save.slot.sectionOffsets[1] + pocket.offset;
  const key = pocket.xorQuantity ? gen3SecurityKeyForSave(save) : 0;
  for (let index = 0; index < pocket.capacity; index += 1) {
    const slotOffset = base + index * 4;
    if (index < items.length) {
      const [itemId, quantity] = items[index];
      writeLe16(save.bytes, slotOffset, itemId);
      writeLe16(save.bytes, slotOffset + 2, quantity ^ key);
    } else {
      writeLe16(save.bytes, slotOffset, 0);
      writeLe16(save.bytes, slotOffset + 2, 0);
    }
  }
  writeLe16(save.bytes, save.slot.sectionOffsets[1] + 0xff6, gen3SectorChecksum(save.bytes, save.slot.sectionOffsets[1]));
}

function parseGen1Inventory(save) {
  const layout = inventoryLayoutForSave(save);
  const entries = [];
  for (const pocketName of ["bag_items", "pc_items"]) {
    const pocket = layout.pockets[pocketName];
    for (const [itemId, quantity] of readCountedItemPairs(save.bytes, pocket.offset)) {
      entries.push({
        item_id: itemId,
        item_name: itemName(itemId, 1) || `Item #${itemId}`,
        quantity,
        generation: 1,
        storage: pocket.storage,
        pocket_name: pocketName,
        category: itemCategory(itemId, 1)
      });
    }
  }
  return entries;
}

function parseGen2Inventory(save) {
  const layout = inventoryLayoutForSave(save);
  const entries = [];
  for (const pocketName of ["items", "balls", "pc_items"]) {
    const pocket = layout.pockets[pocketName];
    for (const [itemId, quantity] of readCountedItemPairs(save.bytes, pocket.offset)) {
      entries.push({
        item_id: itemId,
        item_name: itemName(itemId, 2) || `Item #${itemId}`,
        quantity,
        generation: 2,
        storage: pocket.storage,
        pocket_name: pocketName,
        category: itemCategory(itemId, 2)
      });
    }
  }
  for (const itemId of readCountedItemIds(save.bytes, layout.pockets.key_items.offset)) {
    entries.push({
      item_id: itemId,
      item_name: itemName(itemId, 2) || `Item #${itemId}`,
      quantity: 1,
      generation: 2,
      storage: "bag",
      pocket_name: "key_items",
      category: itemCategory(itemId, 2)
    });
  }
  const tmhmQuantities = readTmhmQuantities(save.bytes, layout.pockets.tm_hm.offset);
  for (const [itemIdText, quantity] of Object.entries(tmhmQuantities)) {
    const itemId = Number(itemIdText);
    entries.push({
      item_id: itemId,
      item_name: itemName(itemId, 2) || `Item #${itemId}`,
      quantity,
      generation: 2,
      storage: "bag",
      pocket_name: "tm_hm",
      category: itemCategory(itemId, 2)
    });
  }
  return entries;
}

function parseGen3Inventory(save) {
  const entries = [];
  for (const pocketName of ["pc_items", "items", "key_items", "balls", "tm_hm", "berries"]) {
    const pocket = inventoryLayoutForSave(save).pockets[pocketName];
    const items = readGen3ItemSlots(save, pocketName);
    for (const [itemIdText, quantity] of Object.entries(items)) {
      const itemId = Number(itemIdText);
      entries.push({
        item_id: itemId,
        item_name: itemName(itemId, 3) || `Item #${itemId}`,
        quantity,
        generation: 3,
        storage: pocket.storage,
        pocket_name: pocketName,
        category: itemCategory(itemId, 3)
      });
    }
  }
  return entries;
}

function parseInventory(save) {
  if (save.generation === 1) return parseGen1Inventory(save);
  if (save.generation === 2) return parseGen2Inventory(save);
  if (save.generation === 3) return parseGen3Inventory(save);
  return [];
}

function refreshLoadedSaveCollections(save) {
  if (!save) return;
  save.party = save.generation === 1 ? parseGen1Party(save) : save.generation === 2 ? parseGen2Party(save) : parseGen3Party(save);
  save.inventory = parseInventory(save);
  save.boxes = save.generation === 1 ? parseGen1Boxes(save) : save.generation === 2 ? parseGen2Boxes(save) : parseGen3Boxes(save);
}

function pocketEntries(save, pocketName) {
  const inventory = save.inventory || [];
  return inventory.filter((entry) => entry.pocket_name === pocketName);
}

function preferredBagPocketForItem(generation, itemId) {
  const category = itemCategory(itemId, generation);
  if (generation === 1) return "bag_items";
  if (generation === 2) {
    const name = itemName(itemId, 2) || "";
    if (name.startsWith("TM") || name.startsWith("HM")) return "tm_hm";
    if (category === "key_item") return "key_items";
    if (category === "ball") return "balls";
    return "items";
  }
  if (generation === 3) {
    if (category === "ball") return "balls";
    if (category === "berry") return "berries";
    if (category === "key_item") return "key_items";
    if (category === "tm" || category === "hm" || category === "tmhm") return "tm_hm";
    return "items";
  }
  return "items";
}

function hasSpaceInPocket(save, pocketName, itemId, quantity = 1) {
  const layout = inventoryLayoutForSave(save);
  const pocket = layout?.pockets?.[pocketName];
  if (!pocket) return false;
  const normalizedQuantity = Number(quantity || 0);
  if (normalizedQuantity <= 0) return true;
  if (save.generation === 1 || (save.generation === 2 && pocket.encoding === "counted_item_pairs_u8")) {
    const items = readCountedItemPairs(save.bytes, pocket.offset);
    for (const [currentItemId, currentQuantity] of items) {
      if (currentItemId === itemId) return currentQuantity + normalizedQuantity <= pocket.maxStack;
    }
    return items.length < pocket.capacity;
  }
  if (save.generation === 2 && pocket.encoding === "counted_item_ids") {
    const items = readCountedItemIds(save.bytes, pocket.offset);
    return items.includes(itemId) || items.length < pocket.capacity;
  }
  if (save.generation === 2 && pocket.encoding === "tmhm_quantity_array") {
    const current = readTmhmQuantities(save.bytes, pocket.offset)[itemId] || 0;
    return current + normalizedQuantity <= pocket.maxStack;
  }
  if (save.generation === 3) {
    const items = readGen3ItemSlots(save, pocketName);
    const current = items[itemId];
    if (current != null) return current + normalizedQuantity <= pocket.maxStack;
    return Object.keys(items).length < pocket.capacity;
  }
  return false;
}

function hasBagSpaceInSave(save, itemId, quantity = 1) {
  return hasSpaceInPocket(save, preferredBagPocketForItem(save.generation, itemId), itemId, quantity);
}

function hasPcSpaceInSave(save, itemId, quantity = 1) {
  const pocketName = save.generation === 1 ? "pc_items" : "pc_items";
  return hasSpaceInPocket(save, pocketName, itemId, quantity);
}

function storeItemInPocket(save, pocketName, itemId, quantity = 1) {
  const layout = inventoryLayoutForSave(save);
  const pocket = layout?.pockets?.[pocketName];
  if (!pocket) throw new Error(`Pocket desconhecido: ${pocketName}`);
  const normalizedQuantity = Number(quantity || 0);
  if (normalizedQuantity <= 0) throw new Error("Quantidade de item precisa ser positiva.");
  if (save.generation === 1 || (save.generation === 2 && pocket.encoding === "counted_item_pairs_u8")) {
    const items = readCountedItemPairs(save.bytes, pocket.offset);
    let updated = false;
    for (let index = 0; index < items.length; index += 1) {
      const [currentItemId, currentQuantity] = items[index];
      if (currentItemId === itemId) {
        const nextQuantity = currentQuantity + normalizedQuantity;
        if (nextQuantity > pocket.maxStack) throw new Error("Stack de itens excedeu o limite suportado.");
        items[index] = [currentItemId, nextQuantity];
        updated = true;
        break;
      }
    }
    if (!updated) {
      if (items.length >= pocket.capacity) throw new Error(`Pocket ${pocketName} esta cheio.`);
      items.push([itemId, normalizedQuantity]);
    }
    writeCountedItemPairs(save.bytes, pocket.offset, pocket.capacity, items);
    return { storage: pocket.storage, pocket_name: pocketName, quantity_added: normalizedQuantity };
  }
  if (save.generation === 2 && pocket.encoding === "counted_item_ids") {
    const items = readCountedItemIds(save.bytes, pocket.offset);
    if (!items.includes(itemId)) {
      if (items.length >= pocket.capacity) throw new Error(`Pocket ${pocketName} esta cheio.`);
      items.push(itemId);
      writeCountedItemIds(save.bytes, pocket.offset, pocket.capacity, items);
    }
    return { storage: pocket.storage, pocket_name: pocketName, quantity_added: 1 };
  }
  if (save.generation === 2 && pocket.encoding === "tmhm_quantity_array") {
    const items = readTmhmQuantities(save.bytes, pocket.offset);
    const nextQuantity = (items[itemId] || 0) + normalizedQuantity;
    if (nextQuantity > pocket.maxStack) throw new Error("Stack de TM/HM excedeu o limite suportado.");
    writeTmhmQuantity(save.bytes, pocket.offset, itemId, nextQuantity);
    writeLe16(save.bytes, save.layout.primaryChecksum, sumRange(save.bytes, save.layout.primaryStart, save.layout.primaryEnd));
    if (save.layout.secondaryStart !== undefined) {
      save.bytes.set(save.bytes.slice(save.layout.primaryStart, save.layout.primaryEnd + 1), save.layout.secondaryStart);
      writeLe16(save.bytes, save.layout.secondaryChecksum, sumRange(save.bytes, save.layout.secondaryStart, save.layout.secondaryEnd));
    }
    return { storage: pocket.storage, pocket_name: pocketName, quantity_added: normalizedQuantity };
  }
  if (save.generation === 3) {
    const items = readGen3ItemSlots(save, pocketName);
    const nextQuantity = (items[itemId] || 0) + normalizedQuantity;
    if (nextQuantity > pocket.maxStack) throw new Error("Stack de itens excedeu o limite suportado.");
    items[itemId] = nextQuantity;
    const orderedItems = Object.entries(items).map(([id, qty]) => [Number(id), qty]).sort((left, right) => left[0] - right[0]);
    writeGen3ItemSlots(save, pocketName, orderedItems);
    return { storage: pocket.storage, pocket_name: pocketName, quantity_added: normalizedQuantity };
  }
  throw new Error("Geracao de inventario nao suportada.");
}

function storeItemInBagForSave(save, itemId, quantity = 1) {
  return storeItemInPocket(save, preferredBagPocketForItem(save.generation, itemId), itemId, quantity);
}

function storeItemInPcForSave(save, itemId, quantity = 1) {
  return storeItemInPocket(save, "pc_items", itemId, quantity);
}

function removeItemFromPocket(save, pocketName, itemId, quantity = 1) {
  const layout = inventoryLayoutForSave(save);
  const pocket = layout?.pockets?.[pocketName];
  if (!pocket) throw new Error(`Pocket desconhecido: ${pocketName}`);
  const normalizedQuantity = Number(quantity || 0);
  if (normalizedQuantity <= 0) throw new Error("Quantidade de item precisa ser positiva.");
  if (save.generation === 1 || (save.generation === 2 && pocket.encoding === "counted_item_pairs_u8")) {
    const items = readCountedItemPairs(save.bytes, pocket.offset);
    const index = items.findIndex(([currentItemId]) => currentItemId === itemId);
    if (index < 0) throw new Error("Item não encontrado no pocket.");
    const nextQuantity = items[index][1] - normalizedQuantity;
    if (nextQuantity < 0) throw new Error("Quantidade insuficiente.");
    if (nextQuantity === 0) items.splice(index, 1);
    else items[index][1] = nextQuantity;
    writeCountedItemPairs(save.bytes, pocket.offset, pocket.capacity, items);
    return;
  }
  if (save.generation === 2 && pocket.encoding === "counted_item_ids") {
    if (normalizedQuantity !== 1) throw new Error("Key items só podem ser removidos uma unidade por vez.");
    const items = readCountedItemIds(save.bytes, pocket.offset);
    const index = items.indexOf(itemId);
    if (index < 0) throw new Error("Item não encontrado no pocket.");
    items.splice(index, 1);
    writeCountedItemIds(save.bytes, pocket.offset, pocket.capacity, items);
    return;
  }
  if (save.generation === 2 && pocket.encoding === "tmhm_quantity_array") {
    const items = readTmhmQuantities(save.bytes, pocket.offset);
    const current = items[itemId] || 0;
    if (current < normalizedQuantity) throw new Error("Quantidade insuficiente.");
    writeTmhmQuantity(save.bytes, pocket.offset, itemId, current - normalizedQuantity);
    writeLe16(save.bytes, save.layout.primaryChecksum, sumRange(save.bytes, save.layout.primaryStart, save.layout.primaryEnd));
    if (save.layout.secondaryStart !== undefined) {
      save.bytes.set(save.bytes.slice(save.layout.primaryStart, save.layout.primaryEnd + 1), save.layout.secondaryStart);
      writeLe16(save.bytes, save.layout.secondaryChecksum, sumRange(save.bytes, save.layout.secondaryStart, save.layout.secondaryEnd));
    }
    return;
  }
  if (save.generation === 3) {
    const items = readGen3ItemSlots(save, pocketName);
    const current = items[itemId] || 0;
    if (current < normalizedQuantity) throw new Error("Quantidade insuficiente.");
    const next = current - normalizedQuantity;
    if (next > 0) items[itemId] = next;
    else delete items[itemId];
    const orderedItems = Object.entries(items).map(([id, qty]) => [Number(id), qty]).sort((left, right) => left[0] - right[0]);
    writeGen3ItemSlots(save, pocketName, orderedItems);
    return;
  }
  throw new Error("Geração de inventário não suportada.");
}

function clearHeldItemInSave(save, location) {
  const parsed = parseLocation(location);
  if (save.generation === 1) return;
  if (save.generation === 2) {
    const data = readGbcLocationData(save, save.layout, location);
    data.mon[0x01] = 0;
    writeGbcLocationData(save, save.layout, location, 2, data.mon, data.ot, data.nickname);
    return;
  }
  if (save.generation === 3) {
    const data = readGen3LocationRaw(save, location);
    const raw = new Uint8Array(parsed.kind === "party" ? data.raw : (() => {
      const party = new Uint8Array(gen3.monSize);
      party.set(data.raw.slice(0, gen3.boxMonSize), 0);
      party[84] = pokemonByLocation(save, location)?.level || 1;
      return party;
    })());
    const personality = readLe32(raw, 0);
    const trainerId = readLe32(raw, 4);
    const secure = decryptGen3Secure(raw);
    const growth = gen3.substructOrders[personality % 24][0] * 12;
    writeLe16(secure, growth + 2, 0);
    writeLe16(raw, 28, gen3BoxChecksum(secure));
    raw.set(encryptGen3Secure(secure, personality, trainerId), gen3.secureOffset);
    writeGen3LocationRaw(save, location, parsed.kind === "party" ? raw : raw.slice(0, gen3.boxMonSize));
  }
}

function setHeldItemInSave(save, location, itemId) {
  const parsed = parseLocation(location);
  if (save.generation === 1) return;
  if (save.generation === 2) {
    const data = readGbcLocationData(save, save.layout, location);
    data.mon[0x01] = itemId & 0xff;
    writeGbcLocationData(save, save.layout, location, 2, data.mon, data.ot, data.nickname);
    return;
  }
  if (save.generation === 3) {
    const data = readGen3LocationRaw(save, location);
    const raw = new Uint8Array(parsed.kind === "party" ? data.raw : (() => {
      const party = new Uint8Array(gen3.monSize);
      party.set(data.raw.slice(0, gen3.boxMonSize), 0);
      party[84] = pokemonByLocation(save, location)?.level || 1;
      return party;
    })());
    const personality = readLe32(raw, 0);
    const trainerId = readLe32(raw, 4);
    const secure = decryptGen3Secure(raw);
    const growth = gen3.substructOrders[personality % 24][0] * 12;
    writeLe16(secure, growth + 2, itemId);
    writeLe16(raw, 28, gen3BoxChecksum(secure));
    raw.set(encryptGen3Secure(secure, personality, trainerId), gen3.secureOffset);
    writeGen3LocationRaw(save, location, parsed.kind === "party" ? raw : raw.slice(0, gen3.boxMonSize));
  }
}

function itemExists(itemId, generation) {
  return Boolean(itemName(itemId, generation));
}

function equivalentItemId(sourceItemId, sourceGeneration, targetGeneration) {
  const sourceName = itemName(sourceItemId, sourceGeneration);
  if (!sourceName || !itemNames?.[targetGeneration]) return null;
  const normalized = cleanName(sourceName).toLowerCase();
  for (const [targetItemIdText, targetName] of Object.entries(itemNames[targetGeneration])) {
    if (cleanName(targetName).toLowerCase() === normalized) return Number(targetItemIdText);
  }
  return null;
}

function resolveItemTransferDecisionForSave(payload, save) {
  const canonical = canonicalFromPayload(payload);
  const heldItem = canonical?.held_item;
  if (!heldItem?.item_id) return null;
  const sourceGeneration = Number(heldItem.source_generation || canonical.source_generation || payload.generation);
  const targetGeneration = save.generation;
  const resolvedItemId = equivalentItemId(heldItem.item_id, sourceGeneration, targetGeneration);
  if (!resolvedItemId || !itemExists(resolvedItemId, targetGeneration)) {
    return {
      source_item_id: heldItem.item_id,
      source_generation: sourceGeneration,
      target_generation: targetGeneration,
      resolved_item_id: null,
      resolved_item_name: null,
      resolved_category: null,
      disposition: "remove",
      fallback_disposition: null,
      reason: "item_absent_in_target_generation",
      stored_in: null
    };
  }
  const resolvedCategory = itemCategory(resolvedItemId, targetGeneration);
  const targetSupportsHeldItems = targetGeneration !== 1;
  if (targetSupportsHeldItems && !nonHoldableCategories.has(resolvedCategory || "")) {
    return {
      source_item_id: heldItem.item_id,
      source_generation: sourceGeneration,
      target_generation: targetGeneration,
      resolved_item_id: resolvedItemId,
      resolved_item_name: itemName(resolvedItemId, targetGeneration),
      resolved_category: resolvedCategory,
      disposition: "keep_held",
      fallback_disposition: null,
      reason: sourceGeneration === targetGeneration ? "same_item_available" : "equivalent_held_item_available",
      stored_in: null
    };
  }
  const canBag = hasBagSpaceInSave(save, resolvedItemId, 1);
  const canPc = hasPcSpaceInSave(save, resolvedItemId, 1);
  return {
    source_item_id: heldItem.item_id,
    source_generation: sourceGeneration,
    target_generation: targetGeneration,
    resolved_item_id: resolvedItemId,
    resolved_item_name: itemName(resolvedItemId, targetGeneration),
    resolved_category: resolvedCategory,
    disposition: canBag ? "move_to_bag" : canPc ? "move_to_pc" : "remove",
    fallback_disposition: canBag && canPc ? "move_to_pc" : null,
    reason: !targetSupportsHeldItems ? "item_exists_but_target_cannot_hold" : "item_exists_but_category_not_holdable",
    stored_in: canBag ? { storage: "bag", pocket_name: preferredBagPocketForItem(targetGeneration, resolvedItemId), quantity_added: 1 } : canPc ? { storage: "pc", pocket_name: "pc_items", quantity_added: 1 } : null
  };
}

function applyReceivedItemTransferForSave(save, location, payload) {
  if (payload.generation === save.generation) return null;
  const decision = resolveItemTransferDecisionForSave(payload, save);
  if (!decision) return null;
  if (decision.disposition === "keep_held") {
    setHeldItemInSave(save, location, decision.resolved_item_id);
    return decision;
  }
  if (save.generation !== 1) clearHeldItemInSave(save, location);
  if (decision.disposition === "move_to_bag") {
    const stored = storeItemInBagForSave(save, decision.resolved_item_id, 1);
    return { ...decision, stored_in: stored };
  }
  if (decision.disposition === "move_to_pc") {
    const stored = storeItemInPcForSave(save, decision.resolved_item_id, 1);
    return { ...decision, stored_in: stored };
  }
  return decision;
}

function readGbcLocationData(save, constants, location) {
  const parsed = parseLocation(location);
  if (parsed.kind === "party") {
    const monStart = constants.dataOffset + parsed.index * constants.monSize;
    const otStart = constants.otOffset + parsed.index * constants.nameSize;
    const nickStart = constants.nickOffset + parsed.index * constants.nameSize;
    return {
      kind: "party",
      mon: save.bytes.slice(monStart, monStart + constants.monSize),
      ot: save.bytes.slice(otStart, otStart + constants.nameSize),
      nickname: save.bytes.slice(nickStart, nickStart + constants.nameSize)
    };
  }
  const boxOffset = parsed.boxIndex === save.boxes?.current_box ? constants.currentBoxDataOffset : constants.storedBoxOffsets[parsed.boxIndex];
  const monStart = boxOffset + 0x16 + parsed.slotIndex * constants.boxMonSize;
  const otStart = boxOffset + constants.boxOtOffset + parsed.slotIndex * constants.nameSize;
  const nickStart = boxOffset + constants.boxNickOffset + parsed.slotIndex * constants.nameSize;
  return {
    kind: "box",
    boxOffset,
    mon: save.bytes.slice(monStart, monStart + constants.boxMonSize),
    ot: save.bytes.slice(otStart, otStart + constants.nameSize),
    nickname: save.bytes.slice(nickStart, nickStart + constants.nameSize)
  };
}

function writeGbcChecksums(save, constants, generation) {
  if (generation === 1) {
    save.bytes[gen1.checksumOffset] = gen1Checksum(save.bytes);
    return;
  }
  if (constants.secondaryStart !== undefined) {
    save.bytes.set(save.bytes.slice(constants.primaryStart, constants.primaryEnd + 1), constants.secondaryStart);
    writeLe16(save.bytes, constants.secondaryChecksum, sumRange(save.bytes, constants.secondaryStart, constants.secondaryEnd));
  }
  writeLe16(save.bytes, constants.primaryChecksum, sumRange(save.bytes, constants.primaryStart, constants.primaryEnd));
}

function writeGbcLocationData(save, constants, location, generation, mon, ot, nickname) {
  const parsed = parseLocation(location);
  if (parsed.kind === "party") {
    const monStart = constants.dataOffset + parsed.index * constants.monSize;
    const otStart = constants.otOffset + parsed.index * constants.nameSize;
    const nickStart = constants.nickOffset + parsed.index * constants.nameSize;
    save.bytes[constants.partyOffset + 1 + parsed.index] = mon[0];
    save.bytes.set(mon, monStart);
    save.bytes.set(ot, otStart);
    save.bytes.set(nickname, nickStart);
    writeGbcChecksums(save, constants, generation);
    return;
  }
  const boxOffset = parsed.boxIndex === save.boxes?.current_box ? constants.currentBoxDataOffset : constants.storedBoxOffsets[parsed.boxIndex];
  save.bytes[boxOffset + 1 + parsed.slotIndex] = mon[0];
  const monStart = boxOffset + 0x16 + parsed.slotIndex * constants.boxMonSize;
  const otStart = boxOffset + constants.boxOtOffset + parsed.slotIndex * constants.nameSize;
  const nickStart = boxOffset + constants.boxNickOffset + parsed.slotIndex * constants.nameSize;
  save.bytes.set(mon, monStart);
  save.bytes.set(ot, otStart);
  save.bytes.set(nickname, nickStart);
  writeGbcChecksums(save, constants, generation);
}

function gbcCanonicalPayload(save, generation, game, summary, location, mon, format) {
  const canonicalSpecies = canonicalSpeciesFor(generation, summary.species_id, summary.species_name);
  const heldItemId = generation === 2 ? (summary.held_item_id || null) : null;
  const moves = generation === 1 ? Array.from(mon.slice(0x08, 0x0c)).filter(Boolean) : Array.from(mon.slice(0x02, 0x06)).filter(Boolean);
  const experience = generation === 1
    ? ((mon[0x0e] << 16) | (mon[0x0f] << 8) | mon[0x10])
    : ((mon[0x08] << 16) | (mon[0x09] << 8) | mon[0x0a]);
  return {
    source_generation: generation,
    source_game: game,
    species: canonicalSpecies,
    species_national_id: canonicalSpecies.national_dex_id,
    species_name: summary.species_name,
    nickname: summary.nickname || summary.species_name,
    level: summary.level,
    ot_name: summary.ot_name,
    trainer_id: summary.trainer_id,
    moves: moves.map((moveId) => ({ move_id: moveId, source_generation: generation })),
    held_item: heldItemId ? { item_id: heldItemId, name: summary.held_item_name || itemName(heldItemId, generation), source_generation: generation } : null,
    metadata: { source_species_id_space: generation === 1 ? "gen1_internal" : "national_dex", source_species_id: summary.species_id, gender: summary.gender || null, unown_form: summary.unown_form || null },
    original_data: { generation, game, format, location, raw_data_base64: "" },
    experience
  };
}

function extractGbcBoxMonForParty(generation, rawPartyMon) {
  return generation === 1 ? rawPartyMon.slice(0, gen1.boxMonSize) : rawPartyMon.slice(0, gen2.boxMonSize);
}

function exportGbcPayload(save, constants, location, generation, game, format) {
  const pokemon = pokemonByLocation(save, location);
  if (!pokemon || pokemon.is_egg) throw new Error("Ovos ainda nao sao suportados para troca real.");
  const data = readGbcLocationData(save, constants, location);
  const formatName = data.kind === "party" ? format : format.replace("-party-v1", "-box-v1");
  const raw = new Uint8Array(data.mon.length + constants.nameSize + constants.nameSize);
  raw.set(data.mon, 0);
  raw.set(data.ot, data.mon.length);
  raw.set(data.nickname, data.mon.length + constants.nameSize);
  const rawBase64 = bytesToBase64(raw);
  const displaySummary = pokemon.display_summary || normalizePokemonDisplay(pokemon);
  const summary = {
    species_id: pokemon.species_id,
    species_name: pokemon.species_name,
    level: pokemon.level,
    nickname: pokemon.nickname || pokemon.species_name,
    display_summary: displaySummary,
    unown_form: pokemon.unown_form || null,
    is_shiny: Boolean(pokemon.is_shiny),
    nature: null,
    ability: null
  };
  const canonical = gbcCanonicalPayload(save, generation, game, pokemon, location, data.mon, formatName);
  canonical.experience = generation === 1
    ? ((data.mon[0x0e] << 16) | (data.mon[0x0f] << 8) | data.mon[0x10])
    : ((data.mon[0x08] << 16) | (data.mon[0x09] << 8) | data.mon[0x0a]);
  return {
    payload_version: 2,
    generation,
    game,
    source_generation: generation,
    source_game: game,
    target_generation: generation,
    species_id: pokemon.species_id,
    species_name: pokemon.species_name,
    level: pokemon.level,
    nickname: pokemon.nickname || pokemon.species_name,
    ot_name: pokemon.ot_name,
    trainer_id: pokemon.trainer_id,
    raw_data_base64: rawBase64,
    display_summary: displaySummary,
    summary,
    raw: { format: formatName, data_base64: rawBase64 },
    canonical,
    compatibility_report: {
      compatible: true,
      mode: "same_generation",
      source_generation: generation,
      target_generation: generation,
      blocking_reasons: [],
      warnings: [],
      data_loss: [],
      suggested_actions: []
    },
    metadata: { format: formatName, source: "web-local-save", location, gender: pokemon.gender || null, unown_form: pokemon.unown_form || null }
  };
}

function applyGbcPayload(save, constants, location, payload, generation) {
  const evolution = getAppliedTradeEvolution(payload, generation);
  if (payload.generation !== generation || evolution) {
    applyCanonicalToGbc(save, constants, location, payload, generation);
    if (!evolution || !evolution.consumedItem) {
      applyReceivedItemTransferForSave(save, location, payload);
    }
    refreshLoadedSaveCollections(save);
    return;
  }
  const raw = base64ToBytes(payload.raw_data_base64 || (payload.raw && payload.raw.data_base64));
  const targetKind = parseLocation(location).kind;
  const rawFormat = String(payload.raw?.format || payload.metadata?.format || "");
  const sourceKind = rawFormat.includes("-box-") ? "box" : rawFormat.includes("-party-") ? "party" : null;
  const expectedMonSize = targetKind === "party" ? constants.monSize : constants.boxMonSize;
  if (sourceKind && sourceKind === targetKind && raw.length === expectedMonSize + constants.nameSize + constants.nameSize) {
    writeGbcLocationData(
      save,
      constants,
      location,
      generation,
      raw.slice(0, expectedMonSize),
      raw.slice(expectedMonSize, expectedMonSize + constants.nameSize),
      raw.slice(expectedMonSize + constants.nameSize)
    );
  } else {
    applyCanonicalToGbc(save, constants, location, payload, generation);
  }
  refreshLoadedSaveCollections(save);
}

function compatibleMovesForGeneration(canonical, generation) {
  const maxMove = generation === 1 ? 165 : generation === 2 ? 251 : 354;
  const moves = (canonical.moves || [])
    .map((move) => Number(move.move_id || move))
    .filter((moveId) => moveId > 0 && moveId <= maxMove)
    .slice(0, 4);
  return moves.length ? moves : [1];
}

function getAppliedTradeEvolution(payload, targetGeneration) {
  if (!window.POKECABLE_TRADE_EVOLUTION_ENABLED) return null;
  const canonical = canonicalFromPayload(payload);
  if (!canonical) return null;

  const rules = window.POKECABLE_TRADE_RULES;
  if (!rules) return null;

  const nationalId = Number(payloadNationalDexId(payload));
  if (!nationalId) return null;

  // Simple evolution
  const simpleTarget = rules.simpleTradeEvolutionByNational?.[nationalId];
  if (simpleTarget) {
    return { targetNationalId: simpleTarget, consumedItem: null };
  }

  // Item evolution
  if (targetGeneration >= 2) {
    const heldItemName = cleanName(canonical.held_item?.name || itemName(canonical.held_item?.item_id, canonical.source_generation));
    if (heldItemName) {
      const itemRule = (rules.itemTradeEvolutionRules || []).find(r => (
        targetGeneration >= r.minGeneration &&
        r.national === nationalId &&
        sameName(heldItemName, r.item)
      ));
      if (itemRule) {
        return { targetNationalId: itemRule.target, consumedItem: itemRule.item };
      }
    }
  }

  return null;
}

function applyCanonicalToGbc(save, constants, location, payload, generation) {
  const canonical = canonicalFromPayload(payload);
  if (!canonical) throw new Error("Payload cross-generation sem canonical.");

  const evolution = getAppliedTradeEvolution(payload, generation);
  const nationalId = evolution ? evolution.targetNationalId : Number(canonical.species.national_dex_id);

  const speciesId = nationalToNative(generation, nationalId);
  if (!speciesId) throw new Error(`${canonical.species.name} National Dex #${nationalId} nao existe na Gen ${generation}.`);

  const targetKind = parseLocation(location).kind;
  const mon = new Uint8Array(targetKind === "party" ? constants.monSize : constants.boxMonSize);
  const level = Math.max(1, Math.min(100, Number(canonical.level || 1)));
  const moves = compatibleMovesForGeneration(canonical, generation);

  mon[0] = speciesId;
  // ... rest of the function continues correctly as it uses speciesId and nationalId for later logic (like Pokedex)
  if (generation === 1) {
    mon[0x03] = level;
    moves.forEach((moveId, offset) => { mon[0x08 + offset] = moveId; });
    mon[0x0c] = (canonical.trainer_id >> 8) & 0xff;
    mon[0x0d] = canonical.trainer_id & 0xff;
    const experience = Math.max(0, Math.min(0xffffff, Number(canonical.experience || 0)));
    mon[0x0e] = (experience >> 16) & 0xff;
    mon[0x0f] = (experience >> 8) & 0xff;
    mon[0x10] = experience & 0xff;
    if (targetKind === "party") mon[0x21] = level;
  } else {
    mon[0x01] = 0;
    moves.forEach((moveId, offset) => { mon[0x02 + offset] = moveId; });
    mon[0x06] = (canonical.trainer_id >> 8) & 0xff;
    mon[0x07] = canonical.trainer_id & 0xff;
    const experience = Math.max(0, Math.min(0xffffff, Number(canonical.experience || 0)));
    mon[0x08] = (experience >> 16) & 0xff;
    mon[0x09] = (experience >> 8) & 0xff;
    mon[0x0a] = experience & 0xff;
    mon[0x1f] = level;
  }

  writeGbcLocationData(
    save,
    constants,
    location,
    generation,
    mon,
    encodeGbcText(canonical.ot_name || "TRAINER", constants.nameSize),
    encodeGbcText(canonical.nickname || canonical.species.name, constants.nameSize)
  );
}

function gen3SectorChecksum(data, offset) {
  let checksum = 0;
  for (let cursor = 0; cursor < gen3.sectorDataSize; cursor += 4) {
    checksum = (checksum + readLe32(data, offset + cursor)) >>> 0;
  }
  return ((checksum >>> 16) + checksum) & 0xffff;
}

function gen3BoxChecksum(secure) {
  let checksum = 0;
  for (let offset = 0; offset < gen3.secureSize; offset += 2) {
    checksum = (checksum + readLe16(secure, offset)) & 0xffff;
  }
  return checksum;
}

function decryptGen3Secure(raw) {
  const key = (readLe32(raw, 0) ^ readLe32(raw, 4)) >>> 0;
  const secure = new Uint8Array(gen3.secureSize);
  for (let offset = 0; offset < gen3.secureSize; offset += 4) {
    writeLe32(secure, offset, (readLe32(raw, gen3.secureOffset + offset) ^ key) >>> 0);
  }
  return secure;
}

function encryptGen3Secure(secure, personality, trainerId) {
  const key = (personality ^ trainerId) >>> 0;
  const encrypted = new Uint8Array(gen3.secureSize);
  for (let offset = 0; offset < gen3.secureSize; offset += 4) {
    writeLe32(encrypted, offset, (readLe32(secure, offset) ^ key) >>> 0);
  }
  return encrypted;
}

function parseGen3Pokemon(raw) {
  if (raw.length !== gen3.monSize) throw new Error("Struct Pokemon Gen 3 invalido.");
  const personality = readLe32(raw, 0);
  const trainerId = readLe32(raw, 4);
  const checksum = readLe16(raw, 0x1c);
  const secure = decryptGen3Secure(raw);
  if (gen3BoxChecksum(secure) !== checksum) throw new Error("Checksum interno do Pokemon Gen 3 invalido.");
  const growthIndex = gen3.substructOrders[personality % 24][0];
  const attacksIndex = gen3.substructOrders[personality % 24][1];
  const growth = growthIndex * 12;
  const attacks = attacksIndex * 12;
  const speciesId = readLe16(secure, growth);
  const moves = [];
  for (let offset = 0; offset < 4; offset += 1) {
    const moveId = readLe16(secure, attacks + offset * 2);
    if (moveId) moves.push(moveId);
  }
  const isEgg = speciesId === 412 || Boolean(raw[0x13] & 0x04);
  return {
    species_id: speciesId,
    species_name: speciesNameFor(3, speciesId),
    level: raw[0x54],
    nickname: decodeGen3Text(raw.slice(0x08, 0x12)),
    ot_name: decodeGen3Text(raw.slice(0x14, 0x1b)),
    trainer_id: trainerId,
    is_shiny: isEgg ? false : isShinyGen3(personality, trainerId),
    nature: isEgg ? null : natureNames[personality % 25],
    ability_index: isEgg ? null : (personality & 1),
    held_item_id: readLe16(secure, growth + 2) || null,
    moves,
    is_egg: isEgg
  };
}

function gen3PcBuffer(save) {
  const chunks = [];
  for (let sectionId = 5; sectionId <= 12; sectionId += 1) {
    const offset = save.slot.sectionOffsets[sectionId];
    chunks.push(save.bytes.slice(offset, offset + gen3.sectorDataSize));
  }
  const section13 = save.slot.sectionOffsets[13];
  chunks.push(save.bytes.slice(section13, section13 + 2000));
  const totalSize = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const buffer = new Uint8Array(totalSize);
  let cursor = 0;
  for (const chunk of chunks) {
    buffer.set(chunk, cursor);
    cursor += chunk.length;
  }
  return buffer;
}

function writeGen3PcBuffer(save, buffer) {
  let cursor = 0;
  for (let sectionId = 5; sectionId <= 12; sectionId += 1) {
    const offset = save.slot.sectionOffsets[sectionId];
    const chunk = buffer.slice(cursor, cursor + gen3.sectorDataSize);
    save.bytes.set(chunk, offset);
    writeLe16(save.bytes, offset + 0xff6, gen3SectorChecksum(save.bytes, offset));
    cursor += gen3.sectorDataSize;
  }
  const offset13 = save.slot.sectionOffsets[13];
  const tail = buffer.slice(cursor, cursor + 2000);
  save.bytes.set(tail, offset13);
  writeLe16(save.bytes, offset13 + 0xff6, gen3SectorChecksum(save.bytes, offset13));
}

function parseGen3BoxPokemon(raw, location) {
  if (raw.length !== gen3.boxMonSize) throw new Error("Struct Box Pokemon Gen 3 invalido.");
  const checksum = readLe16(raw, 0x1c);
  const secure = decryptGen3Secure(raw);
  if (gen3BoxChecksum(secure) !== checksum) throw new Error("Checksum interno do Box Pokemon Gen 3 invalido.");
  const personality = readLe32(raw, 0);
  const trainerId = readLe32(raw, 4);
  const growthIndex = gen3.substructOrders[personality % 24][0];
  const growth = growthIndex * 12;
  const speciesId = readLe16(secure, growth);
  const attacksIndex = gen3.substructOrders[personality % 24][1];
  const attacks = attacksIndex * 12;
  const experience = readLe32(secure, growth + 4);
  const isEgg = speciesId === 412 || Boolean(raw[0x13] & 0x04);
  const nationalDexId = isEgg ? null : nativeToNational(3, speciesId);
  const speciesName = isEgg ? "Egg" : speciesNameFor(3, speciesId);
  return {
    location,
    generation: 3,
    species_id: speciesId,
    species_name: speciesName,
    national_dex_id: nationalDexId,
    gender: isEgg || !nationalDexId ? null : genderFromGen3Personality(nationalDexId, readLe32(raw, 0)),
    unown_form: isEgg || nationalDexId !== 201 ? null : unownFormFromGen3Species(speciesId, personality),
    level: isEgg || !nationalDexId ? 1 : levelFromSpeciesExperience(nationalDexId, experience),
    nickname: decodeGen3Text(raw.slice(0x08, 0x12)) || speciesName,
    ot_name: decodeGen3Text(raw.slice(0x14, 0x1b)),
    trainer_id: trainerId,
    is_shiny: isEgg ? false : isShinyGen3(personality, trainerId),
    nature: isEgg ? null : natureNames[personality % 25],
    ability_index: isEgg ? null : (personality & 1),
    held_item_id: readLe16(secure, growth + 2) || null,
    held_item_name: itemName(readLe16(secure, growth + 2) || null, 3),
    moves: Array.from({ length: 4 }, (_, index) => readLe16(secure, attacks + index * 2)).filter(Boolean),
    is_egg: isEgg,
    experience
  };
}

function readGen3LocationRaw(save, location) {
  const parsed = parseLocation(location);
  if (parsed.kind === "party") {
    const section1 = save.slot.sectionOffsets[1];
    const start = section1 + save.layout.partyOffset + parsed.index * gen3.monSize;
    return { kind: "party", raw: save.bytes.slice(start, start + gen3.monSize) };
  }
  const buffer = gen3PcBuffer(save);
  const start = gen3.pcBufferBoxesOffset + (parsed.boxIndex * gen3.boxCapacity + parsed.slotIndex) * gen3.boxMonSize;
  return { kind: "box", raw: buffer.slice(start, start + gen3.boxMonSize) };
}

function writeGen3LocationRaw(save, location, raw) {
  const parsed = parseLocation(location);
  if (parsed.kind === "party") {
    const section1 = save.slot.sectionOffsets[1];
    const start = section1 + save.layout.partyOffset + parsed.index * gen3.monSize;
    save.bytes.set(raw, start);
    writeLe16(save.bytes, section1 + 0xff6, gen3SectorChecksum(save.bytes, section1));
    return;
  }
  const buffer = gen3PcBuffer(save);
  const start = gen3.pcBufferBoxesOffset + (parsed.boxIndex * gen3.boxCapacity + parsed.slotIndex) * gen3.boxMonSize;
  buffer.set(raw, start);
  writeGen3PcBuffer(save, buffer);
}

function emptyGbcName(size) {
  const bytes = new Uint8Array(size);
  bytes.fill(0x50);
  return bytes;
}

function gbcBoxOffset(save, constants, boxIndex) {
  return boxIndex === save.boxes?.current_box ? constants.currentBoxDataOffset : constants.storedBoxOffsets[boxIndex];
}

function readGbcContainerEntries(save, constants, generation, container) {
  if (container.kind === "party") {
    const count = save.bytes[constants.partyOffset];
    const entries = [];
    for (let index = 0; index < count; index += 1) {
      const data = readGbcLocationData(save, constants, `party:${index}`);
      entries.push({
        kind: "party",
        speciesEntry: save.bytes[constants.partyOffset + 1 + index],
        mon: data.mon,
        ot: data.ot,
        nickname: data.nickname,
        level: generation === 1 ? data.mon[0x21] : data.mon[0x1f]
      });
    }
    return { kind: "counted", capacity: constants.partyCapacity, entries };
  }
  const offset = gbcBoxOffset(save, constants, container.boxIndex);
  const count = save.bytes[offset];
  const entries = [];
  for (let slotIndex = 0; slotIndex < count; slotIndex += 1) {
    const data = readGbcLocationData(save, constants, `box:${container.boxIndex}:${slotIndex}`);
    entries.push({
      kind: "box",
      speciesEntry: save.bytes[offset + 1 + slotIndex],
      mon: data.mon,
      ot: data.ot,
      nickname: data.nickname,
      level: generation === 1 ? data.mon[0x03] : data.mon[0x1f]
    });
  }
  return { kind: "counted", capacity: constants.boxCapacity, entries };
}

function gbcEntryForTarget(entry, constants, generation, targetKind) {
  const monSize = targetKind === "party" ? constants.monSize : constants.boxMonSize;
  const mon = new Uint8Array(monSize);
  if (targetKind === "party") {
    mon.set(entry.mon.slice(0, Math.min(entry.mon.length, constants.boxMonSize)), 0);
    if (entry.mon.length >= monSize) mon.set(entry.mon.slice(0, monSize), 0);
    if (generation === 1) mon[0x21] = Number(entry.level || mon[0x03] || 1);
    else mon[0x1f] = Number(entry.level || 1);
  } else {
    mon.set(entry.mon.slice(0, Math.min(entry.mon.length, constants.boxMonSize)), 0);
  }
  return {
    speciesEntry: entry.speciesEntry || mon[0],
    mon,
    ot: entry.ot?.slice(0, constants.nameSize) || emptyGbcName(constants.nameSize),
    nickname: entry.nickname?.slice(0, constants.nameSize) || emptyGbcName(constants.nameSize)
  };
}

function writeGbcContainerEntries(save, constants, generation, container, entries) {
  if (entries.length > (container.kind === "party" ? constants.partyCapacity : constants.boxCapacity)) {
    throw new Error("Container excedeu a capacidade suportada.");
  }
  if (container.kind === "party") {
    save.bytes[constants.partyOffset] = entries.length;
    const speciesStart = constants.partyOffset + 1;
    for (let index = 0; index < constants.partyCapacity; index += 1) {
      save.bytes[speciesStart + index] = index < entries.length ? (entries[index].speciesEntry || entries[index].mon[0]) : 0;
    }
    save.bytes[speciesStart + entries.length] = 0xff;
    for (let index = entries.length + 1; index <= constants.partyCapacity; index += 1) {
      save.bytes[speciesStart + index] = 0;
    }
    for (let index = 0; index < constants.partyCapacity; index += 1) {
      const monStart = constants.dataOffset + index * constants.monSize;
      const otStart = constants.otOffset + index * constants.nameSize;
      const nickStart = constants.nickOffset + index * constants.nameSize;
      const converted = index < entries.length
        ? gbcEntryForTarget(entries[index], constants, generation, "party")
        : { mon: new Uint8Array(constants.monSize), ot: emptyGbcName(constants.nameSize), nickname: emptyGbcName(constants.nameSize) };
      save.bytes.set(converted.mon, monStart);
      save.bytes.set(converted.ot, otStart);
      save.bytes.set(converted.nickname, nickStart);
    }
    writeGbcChecksums(save, constants, generation);
    return;
  }
  const offset = gbcBoxOffset(save, constants, container.boxIndex);
  save.bytes[offset] = entries.length;
  const speciesStart = offset + 1;
  for (let index = 0; index < constants.boxCapacity; index += 1) {
    save.bytes[speciesStart + index] = index < entries.length ? (entries[index].speciesEntry || entries[index].mon[0]) : 0;
  }
  save.bytes[speciesStart + entries.length] = 0xff;
  for (let index = entries.length + 1; index <= constants.boxCapacity; index += 1) {
    save.bytes[speciesStart + index] = 0;
  }
  for (let index = 0; index < constants.boxCapacity; index += 1) {
    const monStart = offset + 0x16 + index * constants.boxMonSize;
    const otStart = offset + constants.boxOtOffset + index * constants.nameSize;
    const nickStart = offset + constants.boxNickOffset + index * constants.nameSize;
    const converted = index < entries.length
      ? gbcEntryForTarget(entries[index], constants, generation, "box")
      : { mon: new Uint8Array(constants.boxMonSize), ot: emptyGbcName(constants.nameSize), nickname: emptyGbcName(constants.nameSize) };
    save.bytes.set(converted.mon, monStart);
    save.bytes.set(converted.ot, otStart);
    save.bytes.set(converted.nickname, nickStart);
  }
  writeGbcChecksums(save, constants, generation);
}

function readGen3PartyEntries(save) {
  const section1 = save.slot.sectionOffsets[1];
  const count = save.bytes[section1 + save.layout.partyCountOffset];
  const entries = [];
  for (let index = 0; index < count; index += 1) {
    const start = section1 + save.layout.partyOffset + index * gen3.monSize;
    const raw = save.bytes.slice(start, start + gen3.monSize);
    const details = parseGen3Pokemon(raw);
    entries.push({ kind: "party", raw, level: details.level });
  }
  return { kind: "counted", capacity: gen3.partyCapacity, entries };
}

function gen3PartyRawFromEntry(entry) {
  if (entry.kind === "party" && entry.raw.length === gen3.monSize) return entry.raw;
  const raw = new Uint8Array(gen3.monSize);
  raw.set(entry.raw.slice(0, Math.min(entry.raw.length, gen3.boxMonSize)), 0);
  raw[84] = Number(entry.level || 1);
  return raw;
}

function gen3BoxRawFromEntry(entry) {
  if (entry.kind === "box" && entry.raw.length === gen3.boxMonSize) return entry.raw;
  const raw = new Uint8Array(gen3.boxMonSize);
  raw.set(entry.raw.slice(0, Math.min(entry.raw.length, gen3.boxMonSize)), 0);
  return raw;
}

function writeGen3PartyEntries(save, entries) {
  if (entries.length > gen3.partyCapacity) throw new Error("Party excedeu a capacidade suportada.");
  const section1 = save.slot.sectionOffsets[1];
  save.bytes[section1 + save.layout.partyCountOffset] = entries.length;
  for (let index = 0; index < gen3.partyCapacity; index += 1) {
    const start = section1 + save.layout.partyOffset + index * gen3.monSize;
    const raw = index < entries.length ? gen3PartyRawFromEntry(entries[index]) : new Uint8Array(gen3.monSize);
    save.bytes.set(raw, start);
  }
  writeLe16(save.bytes, section1 + 0xff6, gen3SectorChecksum(save.bytes, section1));
}

function readGen3BoxEntries(save, boxIndex) {
  const buffer = gen3PcBuffer(save);
  const entries = [];
  for (let slotIndex = 0; slotIndex < gen3.boxCapacity; slotIndex += 1) {
    const start = gen3.pcBufferBoxesOffset + (boxIndex * gen3.boxCapacity + slotIndex) * gen3.boxMonSize;
    const raw = buffer.slice(start, start + gen3.boxMonSize);
    if (!raw.some(Boolean)) {
      entries.push(null);
      continue;
    }
    const details = parseGen3BoxPokemon(raw, `box:${boxIndex}:${slotIndex}`);
    entries.push({ kind: "box", raw, level: details.level });
  }
  return { kind: "fixed", capacity: gen3.boxCapacity, entries };
}

function writeGen3BoxEntries(save, boxIndex, entries) {
  if (entries.length !== gen3.boxCapacity) throw new Error("Box Gen 3 com tamanho inválido.");
  const buffer = gen3PcBuffer(save);
  for (let slotIndex = 0; slotIndex < gen3.boxCapacity; slotIndex += 1) {
    const start = gen3.pcBufferBoxesOffset + (boxIndex * gen3.boxCapacity + slotIndex) * gen3.boxMonSize;
    const entry = entries[slotIndex];
    const raw = entry ? gen3BoxRawFromEntry(entry) : new Uint8Array(gen3.boxMonSize);
    buffer.set(raw, start);
  }
  writeGen3PcBuffer(save, buffer);
}

function containerKeyForLocation(location) {
  const parsed = parseLocation(location);
  return parsed.kind === "party" ? "party" : `box:${parsed.boxIndex}`;
}

function readContainerState(save, location) {
  const parsed = parseLocation(location);
  if (save.generation === 1) return readGbcContainerEntries(save, gen1, 1, parsed.kind === "party" ? { kind: "party" } : { kind: "box", boxIndex: parsed.boxIndex });
  if (save.generation === 2) return readGbcContainerEntries(save, save.layout, 2, parsed.kind === "party" ? { kind: "party" } : { kind: "box", boxIndex: parsed.boxIndex });
  if (save.generation === 3) {
    return parsed.kind === "party" ? readGen3PartyEntries(save) : readGen3BoxEntries(save, parsed.boxIndex);
  }
  throw new Error("Geração não suportada para containers.");
}

function writeContainerState(save, location, state) {
  const parsed = parseLocation(location);
  if (save.generation === 1) {
    writeGbcContainerEntries(save, gen1, 1, parsed.kind === "party" ? { kind: "party" } : { kind: "box", boxIndex: parsed.boxIndex }, state.entries);
    return;
  }
  if (save.generation === 2) {
    writeGbcContainerEntries(save, save.layout, 2, parsed.kind === "party" ? { kind: "party" } : { kind: "box", boxIndex: parsed.boxIndex }, state.entries);
    return;
  }
  if (save.generation === 3) {
    if (parsed.kind === "party") writeGen3PartyEntries(save, state.entries);
    else writeGen3BoxEntries(save, parsed.boxIndex, state.entries);
    return;
  }
  throw new Error("Geração não suportada para escrita de containers.");
}

function movePokemonToEmptyLocation(save, sourceLocation, targetLocation) {
  const source = parseLocation(sourceLocation);
  const target = parseLocation(targetLocation);
  const sourceState = readContainerState(save, sourceLocation);
  const sourceKey = containerKeyForLocation(sourceLocation);
  const targetKey = containerKeyForLocation(targetLocation);
  const sourceIndex = source.kind === "party" ? source.index : source.slotIndex;
  const targetIndex = target.kind === "party" ? target.index : target.slotIndex;

  if (sourceState.kind === "counted") {
    if (sourceIndex < 0 || sourceIndex >= sourceState.entries.length) throw new Error("Origem inválida para movimentação.");
  } else if (!sourceState.entries[sourceIndex]) {
    throw new Error("Origem vazia para movimentação.");
  }

  if (sourceKey === targetKey) {
    if (sourceState.kind === "counted" && targetIndex !== sourceState.entries.length) {
      throw new Error("Em containers contíguos, só o próximo slot vazio pode ser usado.");
    }
    const nextState = saveMovementModule.moveWithinContainer(sourceState, sourceIndex, targetIndex);
    writeContainerState(save, sourceLocation, nextState);
    return;
  }

  const targetState = readContainerState(save, targetLocation);
  if (targetState.kind === "counted" && (targetIndex !== targetState.entries.length || targetIndex >= targetState.capacity)) {
    throw new Error("O destino vazio precisa ser o próximo slot disponível.");
  }
  const nextStates = saveMovementModule.moveAcrossContainers(sourceState, targetState, sourceIndex, targetIndex);
  writeContainerState(save, sourceLocation, nextStates.source);
  writeContainerState(save, targetLocation, nextStates.target);
}

function parseGen3Boxes(save) {
  const buffer = gen3PcBuffer(save);
  const currentBox = readLe32(buffer, 0);
  const boxNames = [];
  for (let boxIndex = 0; boxIndex < gen3.boxCount; boxIndex += 1) {
    const nameOffset = gen3.pcBufferNamesOffset + boxIndex * gen3.boxNameSize;
    const label = decodeGen3Text(buffer.slice(nameOffset, nameOffset + gen3.boxNameSize));
    boxNames.push(label || `Box ${boxIndex + 1}`);
  }
  const boxes = [];
  for (let boxIndex = 0; boxIndex < gen3.boxCount; boxIndex += 1) {
    for (let slotIndex = 0; slotIndex < gen3.boxCapacity; slotIndex += 1) {
      const start = gen3.pcBufferBoxesOffset + (boxIndex * gen3.boxCapacity + slotIndex) * gen3.boxMonSize;
      const raw = buffer.slice(start, start + gen3.boxMonSize);
      if (!raw.some(Boolean)) continue;
      const pokemon = parseGen3BoxPokemon(raw, `box:${boxIndex}:${slotIndex}`);
      if (!(pokemon.species_id > 0)) continue;
      pokemon.game = save.game;
      pokemon.source_generation = 3;
      pokemon.source_game = save.game;
      pokemon.box_index = boxIndex;
      pokemon.slot_index = slotIndex;
      pokemon.box_name = boxNames[boxIndex];
      pokemon.display_summary = normalizePokemonDisplay(pokemon);
      boxes.push(pokemon);
    }
  }
  return { current_box: currentBox, box_names: boxNames, pokemon: boxes };
}

function deterministicPersonality(canonical) {
  let value = 0x9e3779b9;
  const text = `${canonical.species.national_dex_id}:${canonical.nickname}:${canonical.trainer_id}`;
  for (let index = 0; index < text.length; index += 1) {
    value = ((value * 33) ^ text.charCodeAt(index)) >>> 0;
  }
  return value >>> 0;
}

function readGen3Slot(bytes, base) {
  const sectionOffsets = {};
  const counters = [];
  for (let physical = 0; physical < gen3.sectorsPerSlot; physical += 1) {
    const offset = base + physical * gen3.sectorSize;
    if (offset + gen3.sectorSize > bytes.length) continue;
    const sectionId = readLe16(bytes, offset + 0xff4);
    const signature = readLe32(bytes, offset + 0xff8);
    const counter = readLe32(bytes, offset + 0xffc);
    if (signature !== gen3.signature || sectionId >= gen3.sectorsPerSlot) continue;
    if (sectionOffsets[sectionId] === undefined) sectionOffsets[sectionId] = offset;
    counters.push(counter);
  }
  if (!Object.keys(sectionOffsets).length || sectionOffsets[1] === undefined) return null;
  return { base, counter: Math.max(...counters), sectionOffsets };
}

function gen3LayoutScore(bytes, slot, layout) {
  const section1 = slot.sectionOffsets[1];
  if (readLe16(bytes, section1 + 0xff6) !== gen3SectorChecksum(bytes, section1)) return 0;
  const count = bytes[section1 + layout.partyCountOffset];
  if (count < 1 || count > gen3.partyCapacity) return 0;
  let score = 10;
  for (let index = 0; index < count; index += 1) {
    const start = section1 + layout.partyOffset + index * gen3.monSize;
    try {
      const details = parseGen3Pokemon(bytes.slice(start, start + gen3.monSize));
      if (details.species_id >= 1 && details.species_id <= 412) score += 1;
    } catch (_error) {
      // Another layout can still match.
    }
  }
  return score > 10 ? score : 0;
}

function detectGen3(bytes) {
  if (bytes.length < gen3.sectorSize * gen3.sectorsPerSlot) return null;
  const bases = [0];
  if (bytes.length >= gen3.sectorSize * gen3.sectorsPerSlot * 2) {
    bases.push(gen3.sectorSize * gen3.sectorsPerSlot);
  }
  const candidates = [];
  bases.forEach((base) => {
    const slot = readGen3Slot(bytes, base);
    if (!slot) return;
    gen3.layouts.forEach((layout) => {
      const score = gen3LayoutScore(bytes, slot, layout);
      if (score > 0) candidates.push({ score, slot, layout });
    });
  });
  candidates.sort((a, b) => (b.slot.counter - a.slot.counter) || (b.score - a.score));
  return candidates[0] || null;
}

function parseGen3Party(save) {
  const section1 = save.slot.sectionOffsets[1];
  const count = save.bytes[section1 + save.layout.partyCountOffset];
  const party = [];
  for (let index = 0; index < count; index += 1) {
    const start = section1 + save.layout.partyOffset + index * gen3.monSize;
    const raw = save.bytes.slice(start, start + gen3.monSize);
    const details = parseGen3Pokemon(raw);
    const speciesName = details.is_egg ? "Egg" : details.species_name;
    const nationalId = details.is_egg ? null : nativeToNational(3, details.species_id);
    const pokemon = {
      location: `party:${index}`,
      generation: 3,
      game: save.game,
      source_generation: 3,
      source_game: save.game,
      species_id: details.species_id,
      species_name: speciesName,
      national_dex_id: nationalId,
      gender: details.is_egg || !nationalId ? null : genderFromGen3Personality(nationalId, readLe32(raw, 0)),
      unown_form: details.is_egg || nationalId !== 201 ? null : unownFormFromGen3Species(details.species_id, readLe32(raw, 0)),
      level: details.level,
      nickname: details.nickname || speciesName,
      ot_name: details.ot_name,
      trainer_id: details.trainer_id,
      held_item_id: details.held_item_id,
      held_item_name: itemName(details.held_item_id, 3),
      moves: details.moves,
      is_egg: details.is_egg
    };
    pokemon.display_summary = normalizePokemonDisplay(pokemon);
    party.push(pokemon);
  }
  return party;
}

function parseGen3PlayerName(save) {
  const section0 = save.slot.sectionOffsets[0];
  if (section0 === undefined) return "Player";
  return decodeGen3Text(save.bytes.slice(section0 + gen3.playerNameOffset, section0 + gen3.playerNameOffset + 7)) || "Player";
}

function exportGen3Payload(save, location) {
  const pokemon = pokemonByLocation(save, location);
  if (!pokemon || pokemon.is_egg) throw new Error("Ovos ainda nao sao suportados para troca real.");
  const data = readGen3LocationRaw(save, location);
  const raw = data.raw;
  const rawBase64 = bytesToBase64(raw);
  const displaySummary = pokemon.display_summary || normalizePokemonDisplay(pokemon);
  const summary = {
    species_id: pokemon.species_id,
    species_name: pokemon.species_name,
    level: pokemon.level,
    nickname: pokemon.nickname || pokemon.species_name,
    display_summary: displaySummary,
    unown_form: pokemon.unown_form || null,
    is_shiny: Boolean(pokemon.is_shiny),
    nature: pokemon.nature || null,
    ability: pokemon.ability || (Number.isFinite(pokemon.ability_index) ? `Index ${pokemon.ability_index}` : null)
  };
  const canonicalSpecies = canonicalSpeciesFor(3, pokemon.species_id, pokemon.species_name);
  const rawFormat = data.kind === "party" ? "gen3-party-v1" : "gen3-box-v1";
  const rawForExperience = data.kind === "party" ? data.raw : (() => {
    const party = new Uint8Array(gen3.monSize);
    party.set(data.raw.slice(0, gen3.boxMonSize), 0);
    return party;
  })();
  const secure = decryptGen3Secure(rawForExperience);
  const growth = gen3.substructOrders[readLe32(rawForExperience, 0) % 24][0] * 12;
  return {
    payload_version: 2,
    generation: 3,
    game: save.game,
    source_generation: 3,
    source_game: save.game,
    target_generation: 3,
    species_id: pokemon.species_id,
    species_name: pokemon.species_name,
    level: pokemon.level,
    nickname: pokemon.nickname || pokemon.species_name,
    ot_name: pokemon.ot_name,
    trainer_id: pokemon.trainer_id,
    raw_data_base64: rawBase64,
    display_summary: displaySummary,
    summary,
    canonical: {
      source_generation: 3,
      source_game: save.game,
      species: canonicalSpecies,
      species_national_id: canonicalSpecies.national_dex_id,
      species_name: pokemon.species_name,
      nickname: pokemon.nickname || pokemon.species_name,
      level: pokemon.level,
      experience: readLe32(secure, growth + 4),
      ot_name: pokemon.ot_name,
      trainer_id: pokemon.trainer_id,
      moves: (pokemon.moves || []).map((moveId) => ({ move_id: moveId, source_generation: 3 })),
      held_item: pokemon.held_item_id ? { item_id: pokemon.held_item_id, name: pokemon.held_item_name || itemName(pokemon.held_item_id, 3), source_generation: 3 } : null,
      nature: pokemon.nature || null,
      ability: pokemon.ability || (Number.isFinite(pokemon.ability_index) ? `Index ${pokemon.ability_index}` : null),
      metadata: { gender: pokemon.gender || null, unown_form: pokemon.unown_form || null, is_shiny: Boolean(pokemon.is_shiny) }
    },
    raw: { format: rawFormat, data_base64: rawBase64 },
    compatibility_report: {
      compatible: true,
      mode: "same_generation",
      source_generation: 3,
      target_generation: 3,
      blocking_reasons: [],
      warnings: [],
      data_loss: [],
      suggested_actions: []
    },
    metadata: { format: rawFormat, source: "web-local-save", location, layout: save.layout.name, gender: pokemon.gender || null, unown_form: pokemon.unown_form || null }
  };
}

function applyGen3Payload(save, location, payload) {
  const evolution = getAppliedTradeEvolution(payload, 3);
  if (payload.generation !== 3 || evolution) {
    applyCanonicalToGen3(save, location, payload);
    if (!evolution || !evolution.consumedItem) {
      applyReceivedItemTransferForSave(save, location, payload);
    }
    refreshLoadedSaveCollections(save);
    return;
  }
  const raw = base64ToBytes(payload.raw_data_base64 || (payload.raw && payload.raw.data_base64));
  const targetKind = parseLocation(location).kind;
  const rawFormat = String(payload.raw?.format || payload.metadata?.format || "");
  const sourceKind = rawFormat.includes("-box-") ? "box" : rawFormat.includes("-party-") ? "party" : null;
  if (sourceKind === targetKind && ((targetKind === "party" && raw.length === gen3.monSize) || (targetKind === "box" && raw.length === gen3.boxMonSize))) {
    if (targetKind === "party") parseGen3Pokemon(raw);
    else parseGen3BoxPokemon(raw, location);
    writeGen3LocationRaw(save, location, raw);
  } else {
    applyCanonicalToGen3(save, location, payload);
  }
  refreshLoadedSaveCollections(save);
}

function applyCanonicalToGen3(save, location, payload) {
  const canonical = canonicalFromPayload(payload);
  if (!canonical) throw new Error("Payload cross-generation sem canonical.");

  const evolution = getAppliedTradeEvolution(payload, 3);
  const nationalId = evolution ? evolution.targetNationalId : Number(canonical.species.national_dex_id);

  const speciesId = nationalToNative(3, nationalId);
  if (!speciesId) throw new Error(`${canonical.species.name} National Dex #${nationalId} nao existe na Gen 3.`);
  const personality = deterministicPersonality(canonical);
  const trainerId = Number(canonical.trainer_id || 0) >>> 0;
  const secure = new Uint8Array(gen3.secureSize);
  const order = gen3.substructOrders[personality % 24];
  const growth = order[0] * 12;
  const attacks = order[1] * 12;
  const level = Math.max(1, Math.min(100, Number(canonical.level || 1)));
  const moves = compatibleMovesForGeneration(canonical, 3);

  writeLe16(secure, growth, speciesId);
  writeLe32(secure, growth + 4, Number(canonical.experience || 0) >>> 0);
  moves.forEach((moveId, offset) => {
    writeLe16(secure, attacks + offset * 2, moveId);
    secure[attacks + 8 + offset] = 35;
  });

  const raw = new Uint8Array(gen3.monSize);
  writeLe32(raw, 0, personality);
  writeLe32(raw, 4, trainerId);
  raw.set(encodeGen3Text(canonical.nickname || canonical.species.name, 10), 8);
  raw[18] = 2;
  raw.set(encodeGen3Text(canonical.ot_name || "TRAINER", 7), 20);
  writeLe16(raw, 28, gen3BoxChecksum(secure));
  raw.set(encryptGen3Secure(secure, personality, trainerId), gen3.secureOffset);
  raw[84] = level;
  parseGen3Pokemon(raw);
  const targetKind = parseLocation(location).kind;
  writeGen3LocationRaw(save, location, targetKind === "party" ? raw : raw.slice(0, gen3.boxMonSize));
}

function loadSave(bytes, name) {
  if (validateGen2Save(bytes.slice(0, 0x8000), gen2)) {
    const save = { bytes, name, generation: 2, game: "pokemon_crystal", label: "Gen 2 Crystal", layout: gen2 };
    save.player_name = parseGen2PlayerName(save);
    save.party = parseGen2Party(save);
    save.inventory = parseGen2Inventory(save);
    save.boxes = parseGen2Boxes(save);
    save.exportPayload = (location) => exportGbcPayload(save, save.layout, location, 2, save.game, "gen2-crystal-party-v1");
    save.applyPayload = (location, payload) => applyGbcPayload(save, save.layout, location, payload, 2);
    return save;
  }
  if (validateGen2Save(bytes.slice(0, 0x8000), gen2GoldSilver)) {
    const game = name.toLowerCase().includes("silver") ? "pokemon_silver" : "pokemon_gold";
    const save = { bytes, name, generation: 2, game, label: game === "pokemon_silver" ? "Gen 2 Silver" : "Gen 2 Gold", layout: gen2GoldSilver };
    save.player_name = parseGen2PlayerName(save);
    save.party = parseGen2Party(save);
    save.inventory = parseGen2Inventory(save);
    save.boxes = parseGen2Boxes(save);
    save.exportPayload = (location) => exportGbcPayload(save, save.layout, location, 2, save.game, "gen2-gold-silver-party-v1");
    save.applyPayload = (location, payload) => applyGbcPayload(save, save.layout, location, payload, 2);
    return save;
  }
  if (validateGen1Save(bytes)) {
    const lowerName = name.toLowerCase();
    const game = lowerName.includes("yellow") ? "pokemon_yellow" : lowerName.includes("blue") ? "pokemon_blue" : "pokemon_red";
    const save = { bytes, name, generation: 1, game, label: "Gen 1 Red/Blue/Yellow" };
    save.player_name = parseGen1PlayerName(save);
    save.party = parseGen1Party(save);
    save.inventory = parseGen1Inventory(save);
    save.boxes = parseGen1Boxes(save);
    save.exportPayload = (location) => exportGbcPayload(save, gen1, location, 1, save.game, "gen1-party-v1");
    save.applyPayload = (location, payload) => applyGbcPayload(save, gen1, location, payload, 1);
    return save;
  }
  const detectedGen3 = detectGen3(bytes);
  if (detectedGen3) {
    const lowerName = name.toLowerCase();
    let game = detectedGen3.layout.game;
    if (detectedGen3.layout.name === "frlg") {
      game = lowerName.includes("leaf") ? "pokemon_leafgreen" : "pokemon_firered";
    } else if (lowerName.includes("ruby")) {
      game = "pokemon_ruby";
    } else if (lowerName.includes("sapphire")) {
      game = "pokemon_sapphire";
    }
    const save = {
      bytes,
      name,
      generation: 3,
      game,
      label: detectedGen3.layout.name === "frlg" ? "Gen 3 FireRed/LeafGreen" : "Gen 3 Ruby/Sapphire/Emerald",
      slot: detectedGen3.slot,
      layout: detectedGen3.layout
    };
    save.player_name = parseGen3PlayerName(save);
    save.party = parseGen3Party(save);
    save.inventory = parseGen3Inventory(save);
    save.boxes = parseGen3Boxes(save);
    save.exportPayload = (location) => exportGen3Payload(save, location);
    save.applyPayload = (location, payload) => applyGen3Payload(save, location, payload);
    return save;
  }
  throw new Error("Save nao suportado. Carregue um .sav/.srm de Gen 1, Crystal Gen 2 ou Gen 3.");
}

function updatePokemonOptions() {
  pokemonChoiceEl.innerHTML = "";
  clearTradePreviews();
  if (!loadedSave) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Carregue um save";
    pokemonChoiceEl.append(option);
    battleTeamCountEl.textContent = "0 Pokémon";
    battleTeamPreviewEl.textContent = "";
    setupPartyPreviewEl.textContent = "";
    tradePartyPreviewEl.textContent = "";
    setupBagPreviewEl.className = "inventory-preview-body inventory-preview-empty";
    setupBagPreviewEl.textContent = "Carregue um save para visualizar os pockets da mochila.";
    setupPcPreviewEl.className = "inventory-preview-body inventory-preview-empty";
    setupPcPreviewEl.textContent = "Carregue um save para visualizar os itens guardados no PC.";
    setupPokemonPcPreviewEl.className = "inventory-preview-body inventory-preview-empty";
    setupPokemonPcPreviewEl.textContent = "Boxes/PC Pokémon ainda não foram carregados para este save.";
    if (battleSaveStatusEl) battleSaveStatusEl.textContent = "Nenhum save carregado.";
    tradeSelectedSummaryEl.textContent = "Nenhum Pokémon selecionado.";
    if (setupSelectedSummaryEl) setupSelectedSummaryEl.textContent = "Nenhum Pokémon selecionado.";
    if (setupStatusEl) setupStatusEl.textContent = "Carregue um save para liberar troca e batalha.";
    saveManagementStatusEl.textContent = "Selecione um Pokémon para começar.";
    selectedInventoryItem = null;
    pendingMoveSourceLocation = null;
    setBattleStatus("Carregue um save para montar o time.");
    setStatus("Carregue um save para começar.");
    refreshSessionUi();
    return;
  }
  [...loadedSave.party, ...(loadedSave.boxes?.pokemon || [])].forEach((pokemon) => {
    if (pokemon.species_name === "Egg") return;
    const option = document.createElement("option");
    option.value = pokemon.location;
    option.textContent = `${locationLabel(pokemon.location, loadedSave.boxes)} · ${pokemon.display_summary || normalizePokemonDisplay(pokemon)}`;
    pokemonChoiceEl.append(option);
  });
  const enabled = pokemonChoiceEl.options.length > 0;
  if (enabled) {
    const hasCurrentSelection = Array.from(pokemonChoiceEl.options).some((option) => option.value === selectedLocation);
    if (!hasCurrentSelection) selectedLocation = pokemonChoiceEl.options[0].value;
    pokemonChoiceEl.value = selectedLocation;
  } else {
    selectedLocation = "";
  }
  if (pendingMoveSourceLocation && !pokemonByLocation(loadedSave, pendingMoveSourceLocation)) pendingMoveSourceLocation = null;
  if (selectedInventoryItem) {
    selectedInventoryItem = (loadedSave.inventory || []).find(
      (entry) => Number(entry.item_id) === Number(selectedInventoryItem.item_id) && entry.pocket_name === selectedInventoryItem.pocket_name && entry.storage === selectedInventoryItem.storage
    ) || null;
  }
  if (battleSaveStatusEl) battleSaveStatusEl.textContent = `${loadedSave.label}: ${(loadedSave.party || []).length} Pokémon na party.`;
  if (setupStatusEl) {
    setupStatusEl.textContent = enabled
      ? `${loadedSave.label} carregado. Abra ou sincronize a sessão e depois escolha troca ou batalha.`
      : "Este save não possui Pokémon válidos na party nem no PC para troca.";
  }
  const selected = pokemonByLocation(loadedSave, selectedLocation);
  renderOfferCard(localOfferEl, localOfferDetailsEl, selected || null, "", { emptyMessage: "Escolha um Pokémon da party ou do PC." });
  updateBattleTeamPreview();
  updateSetupPartyPreview();
  updateTradePartyPreview();
  updateInventoryPreview();
  updatePokemonPcPreview();
  updateSelectionUi();
  refreshSessionUi();
}

function updateBattleTeamPreview() {
  battleTeamPreviewEl.textContent = "";
  if (!loadedSave) return;
  const team = loadedSave.party.filter((pokemon) => !pokemon.is_egg).slice(0, 6);
  battleTeamCountEl.textContent = `${team.length} Pokémon`;
  battleFormatEl.textContent = `Gen ${loadedSave.generation} local`;
  setBattleStatus(team.length ? "Time pronto para batalha." : "Nenhum Pokémon válido na party.");
  for (const pokemon of team) {
    const item = document.createElement("div");
    item.className = "team-preview-item";
    const name = document.createElement("div");
    name.className = "team-preview-name";
    name.innerHTML = renderPokemonSummaryHtml(pokemon);
    const meta = document.createElement("span");
    meta.textContent = `${pokemon.moves?.length || 0} golpes exportados`;
    item.append(name, meta);
    battleTeamPreviewEl.append(item);
  }
}

function updateSelectionUi() {
  saveManagementController?.updateSelectionUi();
}

function updateManagementButtons() {
  saveManagementController?.updateManagementButtons();
}

function handlePokemonSelectionClick(location, tab = null) {
  saveManagementController?.handlePokemonSelectionClick(location, tab);
}

function startMovePokemon() {
  saveManagementController?.startMovePokemon();
}

function cancelMovePokemon() {
  saveManagementController?.cancelMovePokemon();
}

function selectInventoryItem(itemId, pocketName, storage) {
  saveManagementController?.selectInventoryItem(itemId, pocketName, storage);
}

function removeHeldItemFromSelectedPokemon() {
  saveManagementController?.removeHeldItemFromSelectedPokemon();
}

function applySelectedItemToPokemon() {
  saveManagementController?.applySelectedItemToPokemon();
}

function updateSetupPartyPreview() {
  saveManagementController?.updateSetupPartyPreview();
}

function updateTradePartyPreview() {
  saveManagementController?.updateTradePartyPreview();
}

function updateInventoryPreview() {
  inventoryUiController?.updateInventoryPreview();
}

function updatePokemonPcPreview() {
  inventoryUiController?.updatePokemonPcPreview();
}

function setSelectedTradePokemon(location) {
  saveManagementController?.setSelectedTradePokemon(location);
}

function selectedPayload() {
  if (!loadedSave) throw new Error("Escolha um save local.");
  if (!selectedLocation) throw new Error("Escolha um Pokémon da party ou do PC.");
  return loadedSave.exportPayload(selectedLocation);
}

function swapPokemonLocations(save, locationA, locationB) {
  if (!save) throw new Error("Nenhum save carregado.");
  if (!locationA || !locationB || locationA === locationB) return;
  const payloadA = save.exportPayload(locationA);
  const payloadB = save.exportPayload(locationB);
  save.applyPayload(locationA, payloadB);
  save.applyPayload(locationB, payloadA);
}

function relocatePokemonWithinSave(save, sourceLocation, targetLocation) {
  if (!save) throw new Error("Nenhum save carregado.");
  if (!sourceLocation || !targetLocation || sourceLocation === targetLocation) return;
  if (pokemonByLocation(save, targetLocation)) {
    swapPokemonLocations(save, sourceLocation, targetLocation);
  } else {
    movePokemonToEmptyLocation(save, sourceLocation, targetLocation);
  }
  refreshLoadedSaveCollections(save);
}

function downloadBlob(name, bytes, label) {
  const blob = new Blob([bytes], { type: "application/octet-stream" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  link.textContent = label;
  downloadArea.append(link);
}

function connect() {
  return wsClient?.connect();
}

function send(payload) {
  return wsClient?.send(payload);
}

function resetSessionState() {
  sessionState.action = null;
  sessionState.pending = false;
  sessionState.joined = false;
  sessionState.tradeJoined = false;
  sessionState.battleJoined = false;
  tradeState.hasJoinedRoom = false;
  tradeState.roomReady = false;
  tradeFlowController?.resetTradeRoundUi();
  battleState.hasJoinedBattleRoom = false;
  battleState.roomReady = false;
  battleState.readyToConfirm = false;
  battleState.currentBattleId = null;
  battleState.currentBattleRequest = null;
  battleFlowController?.resetBattleUiForContextChange();
  refreshSessionUi();
}

async function openPendingSession() {
  if (!sessionState.pending || sessionState.joined || !loadedSave) return;
  try {
    sessionState.joined = false;
    sessionState.tradeJoined = false;
    sessionState.battleJoined = false;
    tradeFlowController?.resetTradeRoundUi();
    battleFlowController?.resetBattleUiForContextChange();
    
    setSessionStatus("Conectando ao servidor...");
    await connect();
    
    setSessionStatus("Entrando na sala...");
    log(`Tentando ${sessionState.action === "create" ? "criar" : "entrar na"} sala: ${roomNameEl.value}`);
    tradeFlowController?.joinTradeRoom(sessionState.action);
    battleFlowController?.joinBattleRoom(sessionState.action);
    refreshSessionUi();
  } catch (error) {
    sessionState.pending = false;
    setSessionStatus("Falha na conexão", error.message);
    log(`Erro de conexão: ${error.message}`);
    refreshSessionUi();
    throw error;
  }
}

async function startSession(action) {
  if (sessionState.joined || sessionState.pending) {
    setSessionStatus("Já existe uma sessão aberta.", "Saia da sala atual antes de criar ou entrar em outra.");
    return;
  }
  if (!roomCredentialsReady()) {
    setSessionStatus("Informe nome da sala e senha.");
    return;
  }
  sessionState.action = action;
  sessionState.pending = true;
  sessionState.joined = false;
  sessionState.tradeJoined = false;
  sessionState.battleJoined = false;
  tradeFlowController?.resetTradeRoundUi();
  battleFlowController?.resetBattleUiForContextChange();
  if (!loadedSave) {
    setSessionStatus("Sessão preparada. Carregue um save para concluir a entrada na sala.");
    refreshSessionUi();
    return;
  }
  await openPendingSession();
  refreshSessionUi();
}

async function syncSessionWithLoadedSave() {
  if (!loadedSave) return;
  if (sessionState.pending && !sessionState.joined) {
    await openPendingSession();
  }
}

function leaveSession() {
  log("Saindo da sessão e encerrando conexão...");
  wsClient?.close();
  resetSessionState();
  clearLoadedSave();
  updatePokemonOptions();
  setStatus("Sessão encerrada.");
  setBattleStatus("Sessão encerrada.");
  setSessionStatus("Sessão encerrada.", "Conexão encerrada.");
}

function handleMessage(message) {
  if (message.type === "heartbeat") return;

  // Filtra mensagens para os controladores específicos
  const handledByTrade = message.type !== "connected" && tradeFlowController?.handleTradeMessage(message);
  const handledByBattle = message.type !== "connected" && battleFlowController?.handleBattleMessage(message);

  if (handledByTrade) {
    if (message.type === "room_created" || message.type === "room_joined" || message.type === "room_ready") {
      sessionState.tradeJoined = true;
      sessionState.pending = false;
      sessionState.joined = true;
      refreshSessionUi();
    }
    if (message.type === "trade_cancelled" && message.reason !== "peer_disconnected") {
      sessionState.tradeJoined = false;
      refreshSessionUi();
    }
  }

  if (handledByBattle) {
    if (message.type === "battle_room_created" || message.type === "battle_room_joined" || message.type === "battle_room_ready") {
      sessionState.battleJoined = true;
      sessionState.pending = false;
      sessionState.joined = true;
      refreshSessionUi();
    }
    if (message.type === "battle_finished" || message.type === "battle_finished_received") {
      // Batalha acabou, mas a sala de batalha ainda existe até o peer desconectar ou contexto mudar
    }
  }

  switch (message.type) {
    case "connected":
      log("Conectado ao servidor. Pronto para entrar na sala.");
      refreshSessionUi();
      break;

    case "player_context_updated":
      sessionState.pending = false;
      sessionState.joined = true;
      sessionState.tradeJoined = Boolean(message.trade_room);
      sessionState.battleJoined = Boolean(message.battle_room);
      setSessionStatus("Sessão sincronizada.", "Troca e batalha disponíveis.");
      log("Contexto do jogador atualizado.");
      refreshSessionUi();
      break;

    case "generation_mismatch":
    case "game_mismatch":
    case "error":
      // Recuperação automática se a sala já existir ao tentar criar
      if (message.code === "room_exists" && sessionState.action === "create") {
        log("A sala já existe. Tentando entrar nela automaticamente...");
        sessionState.action = "join";
        void openPendingSession();
        return;
      }

      // Recuperação automática se a sala não existir ao tentar entrar
      if (message.code === "room_not_found" && sessionState.action === "join") {
        log("A sala não existe. Tentando criá-la automaticamente...");
        sessionState.action = "create";
        void openPendingSession();
        return;
      }
      
      // Erros que permitem nova tentativa imediata sem fechar socket
      const isAuthError = message.code === "invalid_password" || message.code === "room_not_found" || message.code === "room_exists";
      if (isAuthError) {
        sessionState.pending = false;
        // Mantemos o sessionState.action para o usuário ver o que tentou
        log(`Erro na sala: ${message.message}`);
      } else {
        sessionState.pending = false;
      }

      setStatus(message.message || "Erro no servidor.");
      battleFlowController?.handleBattleServerError(message);
      setSessionStatus(message.message || "Erro na sessão.");
      log(`Erro (${message.code}): ${message.message}`);
      refreshSessionUi();
      break;
      
    default:
      if (!handledByTrade && !handledByBattle) {
        log(`Evento: ${message.type}`);
      }
  }
}

accessSessionButton.addEventListener("click", () => {
  void startSession("join").catch((error) => setSessionStatus(error.message || String(error)));
});
openTradeTabButton?.addEventListener("click", () => {
  activateTab("trade");
});
openBattleTabButton?.addEventListener("click", () => {
  activateTab("battle");
});
backToModeFromTradeButton?.addEventListener("click", () => {
  activateTab("setup");
});
backToModeFromBattleButton?.addEventListener("click", () => {
  activateTab("setup");
});
roomNameEl.addEventListener("input", () => {
  refreshSessionUi();
});
roomPasswordEl.addEventListener("input", () => {
  refreshSessionUi();
});
leaveSessionButton.addEventListener("click", () => {
  leaveSession();
});
tabButtons.forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});
sendTradeOfferButton.addEventListener("click", () => {
  try {
    tradeFlowController?.sendOffer();
  } catch (error) {
    setStatus(error.message || String(error));
  }
});
confirmButton.addEventListener("click", () => {
  confirmButton.disabled = true;
  send({ type: "confirm_trade" });
});
sendBattleTeamButton.addEventListener("click", () => {
  try {
    battleFlowController?.sendBattleTeam();
  } catch (error) {
    setBattleStatus(error.message || String(error));
  }
});
confirmBattleButton.addEventListener("click", () => {
  battleFlowController?.handleBattleConfirm();
});
forfeitBattleButton.addEventListener("click", () => {
  battleFlowController?.handleBattleForfeit();
});
battleActionsEl.addEventListener("click", (event) => {
  battleFlowController?.handleBattleActionClick(event);
});
cancelButton.addEventListener("click", () => {
  send({ type: "cancel_trade_round", reason: "user_cancelled" });
});
startMovePokemonButton.addEventListener("click", () => {
  try {
    startMovePokemon();
  } catch (error) {
    saveManagementStatusEl.textContent = error.message || String(error);
  }
});
cancelMovePokemonButton.addEventListener("click", () => {
  cancelMovePokemon();
});
removeHeldItemButton.addEventListener("click", () => {
  try {
    removeHeldItemFromSelectedPokemon();
  } catch (error) {
    saveManagementStatusEl.textContent = error.message || String(error);
  }
});
applyHeldItemButton.addEventListener("click", () => {
  try {
    applySelectedItemToPokemon();
  } catch (error) {
    saveManagementStatusEl.textContent = error.message || String(error);
  }
});
setupPokemonPcPreviewEl.addEventListener("click", (event) => {
  if (inventoryUiController?.handlePokemonPcAction(event, "setup")) return;
  const button = event.target.closest("[data-pokemon-location]");
  if (!button) return;
  handlePokemonSelectionClick(button.getAttribute("data-pokemon-location"), "setup");
});
tradeBoxPreviewEl.addEventListener("click", (event) => {
  if (inventoryUiController?.handlePokemonPcAction(event, "trade")) return;
  const button = event.target.closest("[data-pokemon-location]");
  if (!button) return;
  handlePokemonSelectionClick(button.getAttribute("data-pokemon-location"), "trade");
});
setupTogglePokemonPcButton.addEventListener("click", () => {
  inventoryUiController?.togglePokemonPcVisibility("setup");
});
tradeTogglePokemonPcButton.addEventListener("click", () => {
  inventoryUiController?.togglePokemonPcVisibility("trade");
});
closePokemonDetailDrawerButton.addEventListener("click", () => {
  inventoryUiController?.closePokemonDetailDrawer();
});
pokemonDetailDrawerBackdropEl.addEventListener("click", () => {
  inventoryUiController?.closePokemonDetailDrawer();
});
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    inventoryUiController?.closePokemonDetailDrawer();
  }
});
setupBagPreviewEl.addEventListener("click", (event) => {
  const button = event.target.closest("[data-item-id]");
  if (!button) return;
  selectInventoryItem(button.getAttribute("data-item-id"), button.getAttribute("data-pocket-name"), button.getAttribute("data-storage"));
});
setupPcPreviewEl.addEventListener("click", (event) => {
  const button = event.target.closest("[data-item-id]");
  if (!button) return;
  selectInventoryItem(button.getAttribute("data-item-id"), button.getAttribute("data-pocket-name"), button.getAttribute("data-storage"));
});
window.addEventListener("beforeunload", (event) => {
  if (!sessionState.joined) return;
  event.preventDefault();
  event.returnValue = "";
});
document.querySelector("#clearLog").addEventListener("click", () => {
  eventLogEl.textContent = "";
});
pokemonChoiceEl.addEventListener("change", () => {
  if (!loadedSave) return;
  setSelectedTradePokemon(pokemonChoiceEl.value);
});
saveFileEl.addEventListener("change", async () => {
  const file = saveFileEl.files?.[0];
  if (!file) return;
  if (sessionState.saveLocked || loadedSave) {
    saveFileEl.value = "";
    setSessionStatus("O save local já foi carregado e ficou travado por segurança.", "Saia da sessão para liberar outro save.");
    log("Tentativa bloqueada de carregar um segundo save na mesma sessão.");
    return;
  }
  try {
    loadedSave = loadSave(new Uint8Array(await file.arrayBuffer()), file.name);
    loadedSave.signature = {
      size: loadedSave.bytes.length,
      sha256: await sha256Hex(loadedSave.bytes)
    };
    sessionState.saveLocked = true;
    saveFileEl.disabled = true;
    saveSummaryEl.innerHTML = `<span>${loadedSaveHeadline(loadedSave)}</span><strong>${loadedSave.party.length} Pokémon na party</strong>`;
    
    // Transição automática: esconde o carregamento e mostra a sala
    setupSaveStageEl.classList.add("setup-stage-hidden");
    setupRoomStageEl.classList.remove("setup-stage-hidden");
    
    setStatus(`Save carregado: ${loadedSave.label}.`);
    log(`Save carregado: ${file.name} (${loadedSave.label}).`);
  } catch (error) {
    loadedSave = null;
    sessionState.saveLocked = false;
    saveFileEl.disabled = false;
    saveSummaryEl.innerHTML = "<span>Nenhum save carregado</span><strong>Arquivo nao suportado ou checksum invalido.</strong>";
    setStatus(error.message);
    log(`Erro ao carregar save: ${error.message}`);
  }
  updatePokemonOptions();
  if (loadedSave) {
    await syncSessionWithLoadedSave();
  }
});

updatePokemonOptions();
battleFlowController?.renderBattleActions(null);
activateTab("setup");
refreshSessionUi();
log(`Frontend pronto em ${wsUrl()}`);
