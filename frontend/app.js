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
const createSessionButton = document.querySelector("#createSession");
const joinSessionButton = document.querySelector("#joinSession");
const leaveSessionButton = document.querySelector("#leaveSession");
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
const battleFormatEl = document.querySelector("#battleFormat");
const battleTeamCountEl = document.querySelector("#battleTeamCount");
const battleTeamPreviewEl = document.querySelector("#battleTeamPreview");
const battleActionsEl = document.querySelector("#battleActions");
const tabButtons = Array.from(document.querySelectorAll("[data-tab]"));
const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
const openTradeTabButton = document.querySelector("#openTradeTab");
const openBattleTabButton = document.querySelector("#openBattleTab");
const setupStatusEl = document.querySelector("#setupStatus");
const setupPartyPreviewEl = document.querySelector("#setupPartyPreview");
const tradeSaveStatusEl = document.querySelector("#tradeSaveStatus");

const speciesData = window.POKECABLE_SPECIES_DATA;
if (!speciesData) {
  console.error("POKECABLE_SPECIES_DATA nao foi carregado. Verifique frontend/species-data.js.");
}
const speciesNames = speciesData?.speciesNames || Object.create(null);
const gen1InternalNames = speciesData?.gen1InternalNames || Object.create(null);
const gen1InternalToNational = speciesData?.gen1InternalToNational || Object.create(null);
const nationalToGen1Internal = speciesData?.nationalToGen1Internal || Object.create(null);
const gen3NativeToNational = speciesData?.gen3NativeToNational || Object.create(null);
const nationalToGen3Native = speciesData?.nationalToGen3Native || Object.create(null);
const tradeRules = window.POKECABLE_TRADE_RULES;
if (!tradeRules) {
  console.error("POKECABLE_TRADE_RULES nao foi carregado. Verifique frontend/trade-rules.js.");
}
const simpleTradeEvolutionByNational = tradeRules?.simpleTradeEvolutionByNational || Object.create(null);
const itemTradeEvolutionRules = tradeRules?.itemTradeEvolutionRules || [];
const tradePreviewModule = window.POKECABLE_TRADE_PREVIEW;
if (!tradePreviewModule) {
  console.error("POKECABLE_TRADE_PREVIEW nao foi carregado. Verifique frontend/trade-preview.js.");
}
const pokemonUiModule = window.POKECABLE_POKEMON_UI;
if (!pokemonUiModule) {
  console.error("POKECABLE_POKEMON_UI nao foi carregado. Verifique frontend/pokemon-ui.js.");
}
const webCompatibilityModule = window.POKECABLE_WEB_COMPATIBILITY;
if (!webCompatibilityModule) {
  console.error("POKECABLE_WEB_COMPATIBILITY nao foi carregado. Verifique frontend/web-compatibility.js.");
}
const tradeFlowModule = window.POKECABLE_TRADE_FLOW;
if (!tradeFlowModule) {
  console.error("POKECABLE_TRADE_FLOW nao foi carregado. Verifique frontend/trade-flow.js.");
}
const battleFlowModule = window.POKECABLE_BATTLE_FLOW;
if (!battleFlowModule) {
  console.error("POKECABLE_BATTLE_FLOW nao foi carregado. Verifique frontend/battle-flow.js.");
}
const wsClientModule = window.POKECABLE_WS_CLIENT;
if (!wsClientModule) {
  console.error("POKECABLE_WS_CLIENT nao foi carregado. Verifique frontend/websocket-client.js.");
}

const LOCAL_FALLBACK_SPRITE = "pokemon-fallback.svg";

const moveNames = window.POKECABLE_MOVE_NAMES;
if (!moveNames) {
  console.error("POKECABLE_MOVE_NAMES nao foi carregado. Verifique frontend/move-names.js.");
}
const abilityNames = window.POKECABLE_ABILITY_NAMES;
if (!abilityNames) {
  console.error("POKECABLE_ABILITY_NAMES nao foi carregado. Verifique frontend/ability-names.js.");
}
const itemNames = window.POKECABLE_ITEM_NAMES;
if (!itemNames) {
  console.error("POKECABLE_ITEM_NAMES nao foi carregado. Verifique frontend/item-names.js.");
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

function itemName(itemId, generation) {
  if (!itemId) return null;
  return (itemNames && itemNames[generation]?.[Number(itemId)]) || null;
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

function pokemonSpriteUrl(nationalDexId) {
  const dex = Number(nationalDexId || 0);
  if (!dex) return "";
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${dex}.png`;
}

function pokemonSpriteImgHtml(nationalDexId, altText, className = "pokemon-sprite") {
  const remoteSprite = pokemonSpriteUrl(nationalDexId);
  const sprite = remoteSprite || LOCAL_FALLBACK_SPRITE;
  const escapedAlt = escapeAttribute(altText || "Pokemon");
  const escapedSrc = escapeAttribute(sprite);
  const escapedFallback = escapeAttribute(LOCAL_FALLBACK_SPRITE);
  return `<img class="${className}" src="${escapedSrc}" alt="${escapedAlt}" loading="lazy" onerror="if(!this.dataset.fallbackApplied){this.dataset.fallbackApplied='1';this.src='${escapedFallback}';return;}this.style.display='none';" />`;
}

function sameName(left, right) {
  return cleanName(left).toLowerCase().replace(/[^a-z0-9]/g, "") === cleanName(right).toLowerCase().replace(/[^a-z0-9]/g, "");
}

function normalizePokemonDisplay({ national_dex_id, species_name, level, nickname, gender, held_item_name }) {
  let speciesName = cleanName(species_name);
  if ((!speciesName || isSpeciesPlaceholder(speciesName)) && national_dex_id && speciesNames[national_dex_id]) {
    speciesName = speciesNames[national_dex_id];
  }
  if (!speciesName) speciesName = national_dex_id ? `Species #${national_dex_id}` : "Pokemon";
  let text = `${national_dex_id ? `#${national_dex_id} ` : ""}${speciesName}${gender ? ` ${gender}` : ""} Lv. ${Number(level || 1)}`;
  text += held_item_name ? ` — Item: ${held_item_name}` : " — Sem item";
  const nick = cleanName(nickname);
  if (nick && !sameName(nick, speciesName)) text += ` "${nick}"`;
  return text;
}

function payloadNationalDexId(payload) {
  if (!payload) return null;
  if (payload.canonical && payload.canonical.species && payload.canonical.species.national_dex_id) {
    return Number(payload.canonical.species.national_dex_id);
  }
  if (payload.national_dex_id) return Number(payload.national_dex_id);
  return nativeToNational(Number(payload.generation || 0), Number(payload.species_id || 0)) || null;
}

function renderPokemonSummaryHtml(pokemonLike, textOverride = "", options = {}) {
  if (!pokemonLike) return "-";
  const variant = String(options.variant || "default");
  const payloadDexId = payloadNationalDexId(pokemonLike);
  const explicitDexId = Number(pokemonLike.national_dex_id || 0) || null;
  const nationalDexId = payloadDexId ?? explicitDexId;
  const text = textOverride || pokemonLike.display_summary || normalizePokemonDisplay(pokemonLike);
  const escapedText = escapeHtml(text);
  const summaryClass = variant === "trade" ? "pokemon-summary pokemon-summary-trade" : "pokemon-summary";
  const spriteClass = variant === "trade" ? "pokemon-sprite pokemon-sprite-trade" : "pokemon-sprite";
  return `
    <span class="${summaryClass}">
      ${pokemonSpriteImgHtml(nationalDexId, text, spriteClass)}
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
const sessionState = {
  action: null,
  joined: false,
  tradeJoined: false,
  battleJoined: false
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
  getLoadedSaveGeneration: () => loadedSave?.generation
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
  getLoadedSaveGeneration: () => loadedSave?.generation
});

const buildWebCompatibilityReport = webCompatibilityModule?.createCompatibilityBuilder({
  canonicalFromPayload,
  payloadNationalDexId,
  nationalToNative,
  speciesExistsInGeneration,
  itemName,
  moveName,
  getLoadedSaveGeneration: () => loadedSave?.generation
});

const tradeFlowController = tradeFlowModule?.createTradeFlowController({
  state: tradeState,
  getLoadedSave: () => loadedSave,
  getSelectedLocation: () => selectedLocation,
  getSelectedPokemon: () => loadedSave?.party.find((pokemon) => pokemon.location === pokemonChoiceEl.value) || null,
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
  partyOffset: 0x2f2c,
  dataOffset: 0x2f34,
  otOffset: 0x303c,
  nickOffset: 0x307e,
  checksumStart: 0x2598,
  checksumEnd: 0x3522,
  checksumOffset: 0x3523,
  partyCapacity: 6,
  monSize: 44,
  nameSize: 11
};

const gen2 = {
  partyOffset: 0x2865,
  primaryStart: 0x2009,
  primaryEnd: 0x2b82,
  primaryChecksum: 0x2d0d,
  secondaryStart: 0x1209,
  secondaryEnd: 0x1d82,
  secondaryChecksum: 0x1f0d,
  partyCapacity: 6,
  monSize: 48,
  nameSize: 11
};
gen2.headerSize = 1 + gen2.partyCapacity + 1;
gen2.dataOffset = gen2.partyOffset + gen2.headerSize;
gen2.otOffset = gen2.dataOffset + gen2.partyCapacity * gen2.monSize;
gen2.nickOffset = gen2.otOffset + gen2.partyCapacity * gen2.nameSize;

const gen2GoldSilver = {
  partyOffset: 0x288a,
  primaryStart: 0x2009,
  primaryEnd: 0x2d68,
  primaryChecksum: 0x2d69,
  partyCapacity: 6,
  monSize: 48,
  nameSize: 11
};
gen2GoldSilver.headerSize = 1 + gen2GoldSilver.partyCapacity + 1;
gen2GoldSilver.dataOffset = gen2GoldSilver.partyOffset + gen2GoldSilver.headerSize;
gen2GoldSilver.otOffset = gen2GoldSilver.dataOffset + gen2GoldSilver.partyCapacity * gen2GoldSilver.monSize;
gen2GoldSilver.nickOffset = gen2GoldSilver.otOffset + gen2GoldSilver.partyCapacity * gen2GoldSilver.nameSize;

const gen3 = {
  sectorDataSize: 3968,
  sectorSize: 4096,
  sectorsPerSlot: 14,
  signature: 0x08012025,
  monSize: 100,
  secureOffset: 32,
  secureSize: 48,
  partyCapacity: 6,
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
  const roomName = document.querySelector("#roomName").value.trim();
  const password = document.querySelector("#roomPassword").value;
  return Boolean(roomName && password);
}

function refreshSessionUi() {
  const hasSave = Boolean(loadedSave && loadedSave.party.length);
  const canJoinSession = hasSave && roomCredentialsReady() && !sessionState.joined;
  createSessionButton.disabled = !canJoinSession;
  joinSessionButton.disabled = !canJoinSession;
  leaveSessionButton.disabled = !sessionState.joined;
  openTradeTabButton.disabled = !hasSave;
  openBattleTabButton.disabled = !hasSave;
  tradeFlowController?.syncButtons();
  battleFlowController?.syncButtons();
  if (!loadedSave) {
    setSessionStatus("Defina sala e senha. Depois carregue um save para entrar.");
    return;
  }
  if (!sessionState.joined) {
    setSessionStatus(
      "Save carregado. Escolha criar ou entrar na sala.",
      `${loadedSave.label}. Você pode trocar de save antes de abrir a sessão.`
    );
    return;
  }
  const tradeLabel = sessionState.tradeJoined ? (tradeState.roomReady ? "troca pronta" : "troca aguardando") : "troca desconectada";
  const battleLabel = sessionState.battleJoined ? (battleState.roomReady ? "batalha pronta" : "batalha aguardando") : "batalha desconectada";
  setSessionStatus(
    "Sessão ativa na mesma sala para troca e batalha.",
    `${tradeLabel}; ${battleLabel}. Trocar o save ressincroniza seu lado sem derrubar a sessão.`
  );
}

function activateTab(tabName) {
  tabButtons.forEach((button) => {
    const active = button.dataset.tab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  });
  tabPanels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.tabPanel === tabName);
  });
}

function wsUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
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
      species_id: speciesId,
      species_name: speciesName,
      national_dex_id: nationalId,
      level: save.bytes[monStart + 0x21],
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
    const pokemon = {
      location: `party:${index}`,
      species_id: speciesId,
      species_name: speciesEntry === 0xfd ? "Egg" : speciesNameFor(2, speciesId),
      national_dex_id: speciesEntry === 0xfd ? null : speciesId,
      level: save.bytes[monStart + 0x1f],
      nickname: decodeGbcText(save.bytes.slice(nickStart, nickStart + constants.nameSize)),
      ot_name: decodeGbcText(save.bytes.slice(otStart, otStart + constants.nameSize)),
      trainer_id: (save.bytes[monStart + 0x06] << 8) | save.bytes[monStart + 0x07],
      held_item_id: heldItemId,
      held_item_name: itemName(heldItemId, 2),
      moves: Array.from(save.bytes.slice(monStart + 0x02, monStart + 0x06)).filter(Boolean),
      is_egg: speciesEntry === 0xfd
    };
    pokemon.display_summary = normalizePokemonDisplay(pokemon);
    party.push(pokemon);
  }
  return party;
}

function exportGbcPayload(save, constants, location, generation, game, format) {
  const index = Number(location.split(":")[1]);
  const pokemon = save.party[index];
  if (!pokemon || pokemon.is_egg) throw new Error("Ovos ainda nao sao suportados para troca real.");
  const monStart = constants.dataOffset + index * constants.monSize;
  const otStart = constants.otOffset + index * constants.nameSize;
  const nickStart = constants.nickOffset + index * constants.nameSize;
  const raw = new Uint8Array(constants.monSize + constants.nameSize + constants.nameSize);
  raw.set(save.bytes.slice(monStart, monStart + constants.monSize), 0);
  raw.set(save.bytes.slice(otStart, otStart + constants.nameSize), constants.monSize);
  raw.set(save.bytes.slice(nickStart, nickStart + constants.nameSize), constants.monSize + constants.nameSize);
  const rawBase64 = bytesToBase64(raw);
  const displaySummary = pokemon.display_summary || normalizePokemonDisplay(pokemon);
  const summary = {
    species_id: pokemon.species_id,
    species_name: pokemon.species_name,
    level: pokemon.level,
    nickname: pokemon.nickname || pokemon.species_name,
    display_summary: displaySummary
  };
  const canonicalSpecies = canonicalSpeciesFor(generation, pokemon.species_id, pokemon.species_name);
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
    raw: { format, data_base64: rawBase64 },
    canonical: {
      source_generation: generation,
      source_game: game,
      species: canonicalSpecies,
      species_national_id: canonicalSpecies.national_dex_id,
      species_name: pokemon.species_name,
      nickname: pokemon.nickname || pokemon.species_name,
      level: pokemon.level,
      ot_name: pokemon.ot_name,
      trainer_id: pokemon.trainer_id,
      moves: (pokemon.moves || []).map((moveId) => ({ move_id: moveId, source_generation: generation })),
      held_item: pokemon.held_item_id ? { item_id: pokemon.held_item_id, name: pokemon.held_item_name || itemName(pokemon.held_item_id, generation), source_generation: generation } : null
    },
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
    metadata: { format, source: "web-local-save", location }
  };
}

function applyGbcPayload(save, constants, location, payload, generation) {
  if (payload.generation !== generation) {
    applyCanonicalToGbc(save, constants, location, payload, generation);
    return;
  }
  const raw = base64ToBytes(payload.raw_data_base64 || (payload.raw && payload.raw.data_base64));
  if (raw.length !== constants.monSize + constants.nameSize + constants.nameSize) {
    throw new Error(`Payload Gen ${generation} invalido.`);
  }
  const index = Number(location.split(":")[1]);
  const monStart = constants.dataOffset + index * constants.monSize;
  const otStart = constants.otOffset + index * constants.nameSize;
  const nickStart = constants.nickOffset + index * constants.nameSize;
  save.bytes[constants.partyOffset + 1 + index] = raw[0];
  save.bytes.set(raw.slice(0, constants.monSize), monStart);
  save.bytes.set(raw.slice(constants.monSize, constants.monSize + constants.nameSize), otStart);
  save.bytes.set(raw.slice(constants.monSize + constants.nameSize), nickStart);
  if (generation === 1) {
    save.bytes[gen1.checksumOffset] = gen1Checksum(save.bytes);
  } else {
    if (constants.secondaryStart !== undefined) {
      save.bytes.set(save.bytes.slice(constants.primaryStart, constants.primaryEnd + 1), constants.secondaryStart);
      writeLe16(save.bytes, constants.secondaryChecksum, sumRange(save.bytes, constants.secondaryStart, constants.secondaryEnd));
    }
    writeLe16(save.bytes, constants.primaryChecksum, sumRange(save.bytes, constants.primaryStart, constants.primaryEnd));
  }
}

function compatibleMovesForGeneration(canonical, generation) {
  const maxMove = generation === 1 ? 165 : generation === 2 ? 251 : 354;
  const moves = (canonical.moves || [])
    .map((move) => Number(move.move_id || move))
    .filter((moveId) => moveId > 0 && moveId <= maxMove)
    .slice(0, 4);
  return moves.length ? moves : [1];
}

function applyCanonicalToGbc(save, constants, location, payload, generation) {
  const canonical = canonicalFromPayload(payload);
  if (!canonical) throw new Error("Payload cross-generation sem canonical.");
  const nationalId = Number(canonical.species.national_dex_id);
  const speciesId = nationalToNative(generation, nationalId);
  if (!speciesId) throw new Error(`${canonical.species.name} National Dex #${nationalId} nao existe na Gen ${generation}.`);
  const index = Number(location.split(":")[1]);
  const monStart = constants.dataOffset + index * constants.monSize;
  const otStart = constants.otOffset + index * constants.nameSize;
  const nickStart = constants.nickOffset + index * constants.nameSize;
  const mon = new Uint8Array(constants.monSize);
  const level = Math.max(1, Math.min(100, Number(canonical.level || 1)));
  const moves = compatibleMovesForGeneration(canonical, generation);

  mon[0] = speciesId;
  if (generation === 1) {
    mon[0x03] = level;
    moves.forEach((moveId, offset) => { mon[0x08 + offset] = moveId; });
    mon[0x0c] = (canonical.trainer_id >> 8) & 0xff;
    mon[0x0d] = canonical.trainer_id & 0xff;
    mon[0x21] = level;
  } else {
    mon[0x01] = 0;
    moves.forEach((moveId, offset) => { mon[0x02 + offset] = moveId; });
    mon[0x06] = (canonical.trainer_id >> 8) & 0xff;
    mon[0x07] = canonical.trainer_id & 0xff;
    mon[0x1f] = level;
  }

  save.bytes[constants.partyOffset + 1 + index] = speciesId;
  save.bytes.set(mon, monStart);
  save.bytes.set(encodeGbcText(canonical.ot_name || "TRAINER", constants.nameSize), otStart);
  save.bytes.set(encodeGbcText(canonical.nickname || canonical.species.name, constants.nameSize), nickStart);
  if (generation === 1) {
    save.bytes[gen1.checksumOffset] = gen1Checksum(save.bytes);
  } else {
    if (constants.secondaryStart !== undefined) {
      save.bytes.set(save.bytes.slice(constants.primaryStart, constants.primaryEnd + 1), constants.secondaryStart);
      writeLe16(save.bytes, constants.secondaryChecksum, sumRange(save.bytes, constants.secondaryStart, constants.secondaryEnd));
    }
    writeLe16(save.bytes, constants.primaryChecksum, sumRange(save.bytes, constants.primaryStart, constants.primaryEnd));
  }
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
  return {
    species_id: speciesId,
    species_name: speciesNameFor(3, speciesId),
    level: raw[0x54],
    nickname: decodeGen3Text(raw.slice(0x08, 0x12)),
    ot_name: decodeGen3Text(raw.slice(0x14, 0x1b)),
    trainer_id: trainerId,
    held_item_id: readLe16(secure, growth + 2) || null,
    moves,
    is_egg: speciesId === 412 || Boolean(raw[0x13] & 0x04)
  };
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
    const details = parseGen3Pokemon(save.bytes.slice(start, start + gen3.monSize));
    const speciesName = details.is_egg ? "Egg" : details.species_name;
    const nationalId = details.is_egg ? null : nativeToNational(3, details.species_id);
    const pokemon = {
      location: `party:${index}`,
      species_id: details.species_id,
      species_name: speciesName,
      national_dex_id: nationalId,
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

function exportGen3Payload(save, location) {
  const index = Number(location.split(":")[1]);
  const pokemon = save.party[index];
  if (!pokemon || pokemon.is_egg) throw new Error("Ovos ainda nao sao suportados para troca real.");
  const start = save.slot.sectionOffsets[1] + save.layout.partyOffset + index * gen3.monSize;
  const raw = save.bytes.slice(start, start + gen3.monSize);
  const rawBase64 = bytesToBase64(raw);
  const displaySummary = pokemon.display_summary || normalizePokemonDisplay(pokemon);
  const summary = {
    species_id: pokemon.species_id,
    species_name: pokemon.species_name,
    level: pokemon.level,
    nickname: pokemon.nickname || pokemon.species_name,
    display_summary: displaySummary
  };
  const canonicalSpecies = canonicalSpeciesFor(3, pokemon.species_id, pokemon.species_name);
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
      ot_name: pokemon.ot_name,
      trainer_id: pokemon.trainer_id,
      moves: (pokemon.moves || []).map((moveId) => ({ move_id: moveId, source_generation: 3 })),
      held_item: pokemon.held_item_id ? { item_id: pokemon.held_item_id, name: pokemon.held_item_name || itemName(pokemon.held_item_id, 3), source_generation: 3 } : null
    },
    raw: { format: "gen3-party-v1", data_base64: rawBase64 },
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
    metadata: { format: "gen3-party-v1", source: "web-local-save", location, layout: save.layout.name }
  };
}

function applyGen3Payload(save, location, payload) {
  if (payload.generation !== 3) {
    applyCanonicalToGen3(save, location, payload);
    return;
  }
  const raw = base64ToBytes(payload.raw_data_base64 || (payload.raw && payload.raw.data_base64));
  if (raw.length !== gen3.monSize) throw new Error("Payload Gen 3 invalido.");
  parseGen3Pokemon(raw);
  const index = Number(location.split(":")[1]);
  const section1 = save.slot.sectionOffsets[1];
  const start = section1 + save.layout.partyOffset + index * gen3.monSize;
  save.bytes.set(raw, start);
  writeLe16(save.bytes, section1 + 0xff6, gen3SectorChecksum(save.bytes, section1));
}

function applyCanonicalToGen3(save, location, payload) {
  const canonical = canonicalFromPayload(payload);
  if (!canonical) throw new Error("Payload cross-generation sem canonical.");
  const nationalId = Number(canonical.species.national_dex_id);
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
  writeLe32(secure, growth + 4, 0);
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

  const index = Number(location.split(":")[1]);
  const section1 = save.slot.sectionOffsets[1];
  const start = section1 + save.layout.partyOffset + index * gen3.monSize;
  save.bytes.set(raw, start);
  writeLe16(save.bytes, section1 + 0xff6, gen3SectorChecksum(save.bytes, section1));
}

function loadSave(bytes, name) {
  if (validateGen2Save(bytes.slice(0, 0x8000), gen2)) {
    const save = { bytes, name, generation: 2, game: "pokemon_crystal", label: "Gen 2 Crystal", layout: gen2 };
    save.party = parseGen2Party(save);
    save.exportPayload = (location) => exportGbcPayload(save, save.layout, location, 2, save.game, "gen2-crystal-party-v1");
    save.applyPayload = (location, payload) => applyGbcPayload(save, save.layout, location, payload, 2);
    return save;
  }
  if (validateGen2Save(bytes.slice(0, 0x8000), gen2GoldSilver)) {
    const game = name.toLowerCase().includes("silver") ? "pokemon_silver" : "pokemon_gold";
    const save = { bytes, name, generation: 2, game, label: game === "pokemon_silver" ? "Gen 2 Silver" : "Gen 2 Gold", layout: gen2GoldSilver };
    save.party = parseGen2Party(save);
    save.exportPayload = (location) => exportGbcPayload(save, save.layout, location, 2, save.game, "gen2-gold-silver-party-v1");
    save.applyPayload = (location, payload) => applyGbcPayload(save, save.layout, location, payload, 2);
    return save;
  }
  if (validateGen1Save(bytes)) {
    const lowerName = name.toLowerCase();
    const game = lowerName.includes("yellow") ? "pokemon_yellow" : lowerName.includes("blue") ? "pokemon_blue" : "pokemon_red";
    const save = { bytes, name, generation: 1, game, label: "Gen 1 Red/Blue/Yellow" };
    save.party = parseGen1Party(save);
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
    save.party = parseGen3Party(save);
    save.exportPayload = (location) => exportGen3Payload(save, location);
    save.applyPayload = (location, payload) => applyGen3Payload(save, location, payload);
    return save;
  }
  throw new Error("Save nao suportado. Carregue um .sav/.srm de Gen 1, Crystal Gen 2 ou Gen 3.");
}

function updatePokemonOptions() {
  pokemonChoiceEl.innerHTML = "";
  clearTradePreviews();
  if (!loadedSave || !loadedSave.party.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Carregue um save";
    pokemonChoiceEl.append(option);
    battleTeamCountEl.textContent = "0 Pokémon";
    battleTeamPreviewEl.textContent = "";
    setupPartyPreviewEl.textContent = "";
    tradeSaveStatusEl.textContent = "Nenhum save carregado.";
    setupStatusEl.textContent = "Carregue um save para liberar troca e batalha.";
    setBattleStatus("Carregue um save para montar o time.");
    setStatus("Carregue um save para começar.");
    refreshSessionUi();
    return;
  }
  loadedSave.party.forEach((pokemon) => {
    if (pokemon.species_name === "Egg") return;
    const option = document.createElement("option");
    option.value = pokemon.location;
    option.textContent = pokemon.display_summary || normalizePokemonDisplay(pokemon);
    pokemonChoiceEl.append(option);
  });
  const enabled = pokemonChoiceEl.options.length > 0;
  tradeSaveStatusEl.textContent = `${loadedSave.label}: ${loadedSave.party.length} Pokémon na party.`;
  setupStatusEl.textContent = enabled
    ? `${loadedSave.label} carregado. Abra ou sincronize a sessão e depois escolha troca ou batalha.`
    : "A party não possui Pokémon válido para troca ou batalha.";
  const selected = loadedSave.party.find((pokemon) => pokemon.location === pokemonChoiceEl.value);
  renderOfferCard(localOfferEl, localOfferDetailsEl, selected || null, "", { emptyMessage: "Escolha um Pokémon da party." });
  updateBattleTeamPreview();
  updateSetupPartyPreview();
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

function updateSetupPartyPreview() {
  setupPartyPreviewEl.textContent = "";
  if (!loadedSave) return;
  for (const pokemon of loadedSave.party.filter((item) => !item.is_egg).slice(0, 6)) {
    const item = document.createElement("div");
    item.className = "team-preview-item";
    const name = document.createElement("div");
    name.className = "team-preview-name";
    name.innerHTML = renderPokemonSummaryHtml(pokemon);
    const meta = document.createElement("span");
    meta.textContent = pokemon.location === pokemonChoiceEl.value ? "Selecionado para troca" : "Disponível";
    item.append(name, meta);
    setupPartyPreviewEl.append(item);
  }
}

function selectedPayload() {
  if (!loadedSave) throw new Error("Escolha um save local.");
  selectedLocation = pokemonChoiceEl.value;
  if (!selectedLocation) throw new Error("Escolha um Pokemon da party.");
  return loadedSave.exportPayload(selectedLocation);
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

async function startSession(action) {
  if (sessionState.joined) {
    setSessionStatus("Já existe uma sessão aberta.", "Saia da sala atual antes de criar ou entrar em outra.");
    return;
  }
  if (!loadedSave) {
    setSessionStatus("Carregue um save antes de abrir a sessão.");
    return;
  }
  if (!roomCredentialsReady()) {
    setSessionStatus("Informe nome da sala e senha.");
    return;
  }
  sessionState.action = action;
  sessionState.joined = false;
  sessionState.tradeJoined = false;
  sessionState.battleJoined = false;
  tradeFlowController?.resetTradeRoundUi();
  battleFlowController?.resetBattleUiForContextChange();
  setSessionStatus("Conectando a mesma sala para troca e batalha...");
  await connect();
  tradeFlowController?.joinTradeRoom(action);
  battleFlowController?.joinBattleRoom(action);
  refreshSessionUi();
}

async function syncSessionWithLoadedSave() {
  if (!sessionState.joined || !loadedSave) return;
  if (battleState.currentBattleId) {
    setSessionStatus("Finalize a batalha antes de trocar o save.");
    return;
  }
  if (tradeState.pendingTradePayload || tradeState.preparedTradeBackup) {
    setSessionStatus("Finalize a escrita da troca atual antes de trocar o save.");
    return;
  }
  if (tradeState.localPayload || tradeState.peerPayload) {
    send({ type: "cancel_trade_round", reason: "save_changed" });
  }
  send({
    type: "update_player_context",
    generation: loadedSave.generation,
    game: loadedSave.game,
    supported_trade_modes: supportedTradeModes(loadedSave.generation),
    supported_protocols: supportedProtocols()
  });
  tradeFlowController?.resetTradeRoundUi({ peerMessage: "Aguardando o Pokémon do outro jogador." });
  battleFlowController?.resetBattleUiForContextChange();
  setSessionStatus("Novo save carregado. Sincronizando a sessão sem sair da sala...");
  refreshSessionUi();
}

function leaveSession() {
  wsClient?.close();
  resetSessionState();
  setStatus("Sessão encerrada.");
  setBattleStatus("Sessão encerrada.");
  setSessionStatus("Sessão encerrada.", "Você pode carregar outro save ou entrar em outra sala.");
}

function handleMessage(message) {
  if (message.type !== "connected" && tradeFlowController?.handleTradeMessage(message)) {
    if (message.type === "room_created" || message.type === "room_joined") {
      sessionState.tradeJoined = true;
    }
    if (message.type === "room_ready") {
      sessionState.tradeJoined = true;
    }
    if (message.type === "trade_cancelled" && message.reason !== "peer_disconnected") {
      sessionState.tradeJoined = false;
    }
    sessionState.joined = sessionState.tradeJoined || sessionState.battleJoined;
    refreshSessionUi();
    return;
  }
  if (message.type !== "connected" && battleFlowController?.handleBattleMessage(message)) {
    if (message.type === "battle_room_created" || message.type === "battle_room_joined") {
      sessionState.battleJoined = true;
    }
    if (message.type === "battle_room_ready") {
      sessionState.battleJoined = true;
    }
    sessionState.joined = sessionState.tradeJoined || sessionState.battleJoined;
    refreshSessionUi();
    return;
  }
  switch (message.type) {
    case "connected":
      log("Conectado ao servidor.");
      refreshSessionUi();
      break;
    case "player_context_updated":
      sessionState.joined = true;
      sessionState.tradeJoined = Boolean(message.trade_room);
      sessionState.battleJoined = Boolean(message.battle_room);
      setSessionStatus("Save sincronizado com a mesma sala.", `${loadedSave?.label || "Save local"}. Troca e batalha continuam disponíveis.`);
      log("Contexto do jogador atualizado na sessão.");
      refreshSessionUi();
      break;
    case "generation_mismatch":
    case "game_mismatch":
    case "error":
      setStatus(message.message || "Erro no servidor.");
      battleFlowController?.handleBattleServerError(message);
      setSessionStatus(message.message || "Erro na sessão.");
      log(`Erro: ${message.message || message.code}`);
      break;
    case "heartbeat":
      break;
    default:
      log(`Evento: ${message.type}`);
  }
}

createSessionButton.addEventListener("click", () => {
  void startSession("create").catch((error) => setSessionStatus(error.message || String(error)));
});
joinSessionButton.addEventListener("click", () => {
  void startSession("join").catch((error) => setSessionStatus(error.message || String(error)));
});
leaveSessionButton.addEventListener("click", () => {
  leaveSession();
});
tabButtons.forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});
openTradeTabButton.addEventListener("click", () => activateTab("trade"));
openBattleTabButton.addEventListener("click", () => activateTab("battle"));
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
  const selected = loadedSave.party.find((pokemon) => pokemon.location === pokemonChoiceEl.value);
  renderOfferCard(localOfferEl, localOfferDetailsEl, selected || null, "", { emptyMessage: "Escolha um Pokémon da party." });
  updateSetupPartyPreview();
});
saveFileEl.addEventListener("change", async () => {
  const file = saveFileEl.files?.[0];
  if (!file) return;
  try {
    loadedSave = loadSave(new Uint8Array(await file.arrayBuffer()), file.name);
    loadedSave.signature = {
      size: loadedSave.bytes.length,
      sha256: await sha256Hex(loadedSave.bytes)
    };
    saveSummaryEl.innerHTML = `<span>${loadedSave.label}</span><strong>${loadedSave.party.length} Pokemon na party</strong>`;
    setStatus(`Save carregado: ${loadedSave.label}.`);
    log(`Save carregado: ${file.name} (${loadedSave.label}).`);
  } catch (error) {
    loadedSave = null;
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
