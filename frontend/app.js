const statusEl = document.querySelector("#connectionStatus");
const tradeStatusEl = document.querySelector("#tradeStatus");
const localOfferEl = document.querySelector("#localOffer");
const peerOfferEl = document.querySelector("#peerOffer");
const eventLogEl = document.querySelector("#eventLog");
const pokemonChoiceEl = document.querySelector("#pokemonChoice");
const saveFileEl = document.querySelector("#saveFile");
const saveSummaryEl = document.querySelector("#saveSummary");
const createButton = document.querySelector("#createRoom");
const joinButton = document.querySelector("#joinRoom");
const confirmButton = document.querySelector("#confirmTrade");
const cancelButton = document.querySelector("#cancelTrade");
const downloadArea = document.querySelector("#downloadArea");
const createBattleButton = document.querySelector("#createBattleRoom");
const joinBattleButton = document.querySelector("#joinBattleRoom");
const confirmBattleButton = document.querySelector("#confirmBattle");
const forfeitBattleButton = document.querySelector("#forfeitBattle");
const battleLogEl = document.querySelector("#battleLog");
const battleStatusEl = document.querySelector("#battleStatus");
const battleFormatEl = document.querySelector("#battleFormat");
const battleTeamCountEl = document.querySelector("#battleTeamCount");
const battleTeamPreviewEl = document.querySelector("#battleTeamPreview");
const battleActionButtons = Array.from(document.querySelectorAll("[data-battle-action]"));
const tabButtons = Array.from(document.querySelectorAll("[data-tab]"));
const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
const openTradeTabButton = document.querySelector("#openTradeTab");
const openBattleTabButton = document.querySelector("#openBattleTab");
const setupStatusEl = document.querySelector("#setupStatus");
const setupPartyPreviewEl = document.querySelector("#setupPartyPreview");
const tradeSaveStatusEl = document.querySelector("#tradeSaveStatus");

const kantoSpeciesNames = [
  "",
  "Bulbasaur", "Ivysaur", "Venusaur", "Charmander", "Charmeleon", "Charizard",
  "Squirtle", "Wartortle", "Blastoise", "Caterpie", "Metapod", "Butterfree",
  "Weedle", "Kakuna", "Beedrill", "Pidgey", "Pidgeotto", "Pidgeot",
  "Rattata", "Raticate", "Spearow", "Fearow", "Ekans", "Arbok",
  "Pikachu", "Raichu", "Sandshrew", "Sandslash", "Nidoran-F", "Nidorina",
  "Nidoqueen", "Nidoran-M", "Nidorino", "Nidoking", "Clefairy", "Clefable",
  "Vulpix", "Ninetales", "Jigglypuff", "Wigglytuff", "Zubat", "Golbat",
  "Oddish", "Gloom", "Vileplume", "Paras", "Parasect", "Venonat",
  "Venomoth", "Diglett", "Dugtrio", "Meowth", "Persian", "Psyduck",
  "Golduck", "Mankey", "Primeape", "Growlithe", "Arcanine", "Poliwag",
  "Poliwhirl", "Poliwrath", "Abra", "Kadabra", "Alakazam", "Machop",
  "Machoke", "Machamp", "Bellsprout", "Weepinbell", "Victreebel",
  "Tentacool", "Tentacruel", "Geodude", "Graveler", "Golem", "Ponyta",
  "Rapidash", "Slowpoke", "Slowbro", "Magnemite", "Magneton",
  "Farfetch'd", "Doduo", "Dodrio", "Seel", "Dewgong", "Grimer", "Muk",
  "Shellder", "Cloyster", "Gastly", "Haunter", "Gengar", "Onix",
  "Drowzee", "Hypno", "Krabby", "Kingler", "Voltorb", "Electrode",
  "Exeggcute", "Exeggutor", "Cubone", "Marowak", "Hitmonlee",
  "Hitmonchan", "Lickitung", "Koffing", "Weezing", "Rhyhorn", "Rhydon",
  "Chansey", "Tangela", "Kangaskhan", "Horsea", "Seadra", "Goldeen",
  "Seaking", "Staryu", "Starmie", "Mr. Mime", "Scyther", "Jynx",
  "Electabuzz", "Magmar", "Pinsir", "Tauros", "Magikarp", "Gyarados",
  "Lapras", "Ditto", "Eevee", "Vaporeon", "Jolteon", "Flareon",
  "Porygon", "Omanyte", "Omastar", "Kabuto", "Kabutops", "Aerodactyl",
  "Snorlax", "Articuno", "Zapdos", "Moltres", "Dratini", "Dragonair",
  "Dragonite", "Mewtwo", "Mew"
];

const speciesNames = Object.fromEntries(
  kantoSpeciesNames.map((name, index) => [index, name]).filter(([index, name]) => index && name)
);
Object.assign(speciesNames, {
  152: "Chikorita",
  153: "Bayleef",
  154: "Meganium",
  155: "Cyndaquil",
  156: "Quilava",
  175: "Togepi",
  201: "Unown",
  208: "Steelix",
  212: "Scizor",
  230: "Kingdra",
  251: "Celebi",
  252: "Treecko",
  253: "Grovyle",
  254: "Sceptile",
  255: "Torchic",
  256: "Combusken",
  257: "Blaziken",
  258: "Mudkip",
  259: "Marshtomp",
  260: "Swampert",
  358: "Chimecho",
  366: "Clamperl",
  367: "Huntail",
  368: "Gorebyss",
  412: "Egg"
});

const gen1InternalNames = {
  14: "Gengar",
  21: "Mew",
  28: "Blastoise",
  34: "Onix",
  38: "Kadabra",
  39: "Graveler",
  41: "Machoke",
  49: "Golem",
  84: "Pikachu",
  126: "Machamp",
  147: "Haunter",
  149: "Alakazam"
};

const gen1InternalToNational = {
  1: 112, 2: 115, 3: 32, 4: 35, 5: 21, 6: 100, 7: 34, 8: 80, 9: 2, 10: 103,
  11: 108, 12: 102, 13: 88, 14: 94, 15: 29, 16: 31, 17: 104, 18: 111, 19: 131,
  20: 59, 21: 151, 22: 130, 23: 90, 24: 72, 25: 92, 26: 123, 27: 120, 28: 9,
  29: 127, 30: 114, 33: 58, 34: 95, 35: 22, 36: 16, 37: 79, 38: 64, 39: 75,
  40: 113, 41: 67, 42: 122, 43: 106, 44: 107, 45: 24, 46: 47, 47: 54, 48: 96,
  49: 76, 51: 126, 53: 125, 54: 82, 55: 109, 57: 56, 58: 86, 59: 50, 60: 128,
  64: 83, 65: 48, 66: 149, 70: 84, 71: 60, 72: 124, 73: 146, 74: 144, 75: 145,
  76: 132, 77: 52, 78: 98, 82: 37, 83: 38, 84: 25, 85: 26, 88: 147, 89: 148,
  90: 140, 91: 141, 92: 116, 93: 117, 96: 27, 97: 28, 98: 138, 99: 139,
  100: 39, 101: 40, 102: 133, 103: 136, 104: 135, 105: 134, 106: 66, 107: 41,
  108: 23, 109: 46, 110: 61, 111: 62, 112: 13, 113: 14, 114: 15, 116: 85,
  117: 57, 118: 51, 119: 49, 120: 87, 123: 10, 124: 11, 125: 12, 126: 68,
  128: 55, 129: 97, 130: 42, 131: 150, 132: 143, 133: 129, 136: 89, 138: 99,
  139: 91, 141: 101, 142: 36, 143: 110, 144: 53, 145: 105, 147: 93, 148: 63,
  149: 65, 150: 17, 151: 18, 152: 121, 153: 1, 154: 3, 155: 73, 157: 118,
  158: 119, 163: 77, 164: 78, 165: 19, 166: 20, 167: 33, 168: 30, 169: 74,
  170: 137, 171: 142, 173: 81, 176: 4, 177: 7, 178: 5, 179: 8, 180: 6,
  185: 43, 186: 44, 187: 45, 188: 69, 189: 70, 190: 71
};
const nationalToGen1Internal = Object.fromEntries(
  Object.entries(gen1InternalToNational).map(([internal, national]) => [national, Number(internal)])
);

const gen3NativeToNational = {
  277: 252, 278: 253, 279: 254,
  280: 255, 281: 256, 282: 257,
  283: 258, 284: 259, 285: 260,
  373: 366, 374: 367, 375: 368,
  411: 358,
  412: 0
};
for (let unownId = 252; unownId <= 276; unownId += 1) gen3NativeToNational[unownId] = 201;
const nationalToGen3Native = Object.fromEntries(
  Object.entries(gen3NativeToNational).map(([internal, national]) => [national, Number(internal)])
);

const itemNames = {
  2: {
    0x52: "King's Rock",
    0x8f: "Metal Coat",
    0x97: "Dragon Scale",
    0xac: "Up-Grade"
  },
  3: {
    187: "King's Rock",
    192: "Deep Sea Tooth",
    193: "Deep Sea Scale",
    199: "Metal Coat",
    201: "Dragon Scale",
    218: "Up-Grade"
  }
};

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
  return itemNames[generation]?.[Number(itemId)] || null;
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

let socket = null;
let heartbeatTimer = null;
let currentAction = null;
let localPayload = null;
let peerPayload = null;
let hasJoinedRoom = false;
let hasJoinedBattleRoom = false;
let currentBattleId = null;
let loadedSave = null;
let selectedLocation = "party:0";

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

function setBattleActionsEnabled(enabled) {
  for (const button of battleActionButtons) button.disabled = !enabled;
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

function battleFormatLabel(room) {
  const formatId = room?.format_id || "automatico";
  if (formatId === "gen1customgame") return "Gen 1 Custom Game";
  if (formatId === "gen2customgame") return "Gen 2 Custom Game";
  if (formatId === "gen3customgame") return "Gen 3 Custom Game";
  return formatId;
}

function updateBattleRoomDisplay(room) {
  if (!room) return;
  battleFormatEl.textContent = battleFormatLabel(room);
  const players = room.players || {};
  const teamSizes = Object.values(players).map((player) => `${player.team_size || 0}`);
  if (teamSizes.length) battleTeamCountEl.textContent = teamSizes.join(" x ");
}

function wsUrl() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

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
    trade_mode: "same_generation",
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
    trade_mode: "same_generation",
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
  if (!loadedSave || !loadedSave.party.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Carregue um save";
    pokemonChoiceEl.append(option);
    createButton.disabled = true;
    joinButton.disabled = true;
    createBattleButton.disabled = true;
    joinBattleButton.disabled = true;
    openTradeTabButton.disabled = true;
    openBattleTabButton.disabled = true;
    battleTeamCountEl.textContent = "0 Pokémon";
    battleTeamPreviewEl.textContent = "";
    setupPartyPreviewEl.textContent = "";
    tradeSaveStatusEl.textContent = "Nenhum save carregado.";
    setupStatusEl.textContent = "Carregue um save para liberar troca e batalha.";
    setBattleStatus("Carregue um save para montar o time.");
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
  createButton.disabled = !enabled;
  joinButton.disabled = !enabled;
  createBattleButton.disabled = !enabled;
  joinBattleButton.disabled = !enabled;
  openTradeTabButton.disabled = !enabled;
  openBattleTabButton.disabled = !enabled;
  tradeSaveStatusEl.textContent = `${loadedSave.label}: ${loadedSave.party.length} Pokémon na party.`;
  setupStatusEl.textContent = enabled
    ? `${loadedSave.label} carregado. Você pode ir para troca ou batalha.`
    : "A party não possui Pokémon válido para troca ou batalha.";
  const selected = loadedSave.party.find((pokemon) => pokemon.location === pokemonChoiceEl.value);
  localOfferEl.textContent = selected ? selected.display_summary || normalizePokemonDisplay(selected) : "-";
  updateBattleTeamPreview();
  updateSetupPartyPreview();
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
    const name = document.createElement("strong");
    name.textContent = pokemon.display_summary || normalizePokemonDisplay(pokemon);
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
    const name = document.createElement("strong");
    name.textContent = pokemon.display_summary || normalizePokemonDisplay(pokemon);
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
  return new Promise((resolve, reject) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      resolve();
      return;
    }
    socket = new WebSocket(wsUrl());
    socket.addEventListener("open", () => {
      statusEl.textContent = "Conectando";
      statusEl.classList.remove("online");
    });
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      handleMessage(message);
      if (message.type === "connected") {
        statusEl.textContent = "Online";
        statusEl.classList.add("online");
        resolve();
      }
    });
    socket.addEventListener("close", () => {
      statusEl.textContent = "Desconectado";
      statusEl.classList.remove("online");
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      heartbeatTimer = null;
      confirmButton.disabled = true;
      cancelButton.disabled = true;
      confirmBattleButton.disabled = true;
      forfeitBattleButton.disabled = true;
      setBattleActionsEnabled(false);
      if (hasJoinedRoom) setStatus("Conexao encerrada.");
      if (hasJoinedBattleRoom) setBattleStatus("Conexao de batalha encerrada.");
    });
    socket.addEventListener("error", () => reject(new Error("Falha ao conectar no WebSocket.")));
  });
}

function send(payload) {
  if (!socket || socket.readyState !== WebSocket.OPEN) throw new Error("WebSocket nao conectado.");
  socket.send(JSON.stringify(payload));
}

function handleMessage(message) {
  switch (message.type) {
    case "connected":
      log("Conectado ao servidor.");
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      heartbeatTimer = window.setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "heartbeat" }));
        }
      }, 20000);
      break;
    case "room_created":
      hasJoinedRoom = true;
      setStatus("Sala criada. Aguardando segundo usuario.");
      log("Sala criada.");
      cancelButton.disabled = false;
      break;
    case "room_waiting":
      if (hasJoinedRoom) setStatus(message.message || "Aguardando outro usuario.");
      log("Aguardando segundo usuario.");
      break;
    case "room_joined":
      hasJoinedRoom = true;
      setStatus("Entrou na sala. Enviando oferta.");
      log("Entrou na sala.");
      cancelButton.disabled = false;
      sendOffer();
      break;
    case "room_ready":
      log("Sala pronta com dois usuarios.");
      if (currentAction === "create") {
        setStatus("Segundo usuario entrou. Enviando oferta.");
        sendOffer();
      }
      break;
    case "offer_received":
      log("Servidor recebeu sua oferta.");
      break;
    case "peer_offer_received":
      peerPayload = message.offer;
      peerOfferEl.textContent = peerPayload.display_summary || (peerPayload.summary && peerPayload.summary.display_summary) || "-";
      setStatus("Oferta do outro usuario recebida. Validando compatibilidade.");
      confirmButton.disabled = true;
      log(`Outro usuario oferece: ${peerOfferEl.textContent}`);
      break;
    case "offers_ready":
      log("As duas ofertas estao prontas.");
      break;
    case "preflight_required":
      handlePreflightRequired(message);
      break;
    case "preflight_received":
      log("Preflight enviado ao servidor.");
      break;
    case "preflight_ready":
      setStatus("Compatibilidade validada nos dois lados. Confirme para concluir.");
      confirmButton.disabled = false;
      log("Preflight aprovado pelos dois usuarios.");
      break;
    case "trade_blocked":
      setStatus(message.message || "Troca bloqueada no preflight.");
      confirmButton.disabled = true;
      log(`Troca bloqueada: ${message.message || "preflight"}`);
      break;
    case "trade_confirmed":
      setStatus("Sua confirmacao foi enviada. Aguardando o outro usuario.");
      log("Confirmacao enviada.");
      break;
    case "peer_confirmed":
      log("O outro usuario confirmou.");
      break;
    case "trade_committed":
      setStatus(`Troca concluida. Recebido: ${message.received_payload.display_summary}`);
      peerOfferEl.textContent = message.received_payload.display_summary;
      try {
        downloadArea.textContent = "";
        const backup = new Uint8Array(loadedSave.bytes);
        loadedSave.applyPayload(selectedLocation, message.received_payload);
        downloadBlob(`${loadedSave.name}.bak`, backup, "Baixar backup original");
        downloadBlob(loadedSave.name, loadedSave.bytes, "Baixar save modificado");
        setStatus("Troca aplicada localmente. Baixe o save modificado antes de abrir o jogo.");
      } catch (error) {
        setStatus(error.message);
        log(`Erro ao aplicar save local: ${error.message}`);
      }
      confirmButton.disabled = true;
      cancelButton.disabled = true;
      log("Troca concluida.");
      break;
    case "generation_mismatch":
    case "game_mismatch":
    case "error":
      setStatus(message.message || "Erro no servidor.");
      if (currentAction && currentAction.startsWith("battle")) {
        setBattleStatus(message.message || "Erro no servidor.");
        setBattleActionsEnabled(false);
      }
      log(`Erro: ${message.message || message.code}`);
      break;
    case "battle_error":
      setBattleStatus(message.message || "Erro na batalha.");
      setBattleActionsEnabled(false);
      log(`Erro de batalha: ${message.message || message.code}`);
      break;
    case "trade_cancelled":
      if (message.reason === "peer_disconnected") {
        setStatus("Outro usuario desconectou. A sala continua aberta aguardando novo usuario.");
        peerOfferEl.textContent = "-";
        peerPayload = null;
        currentAction = "create";
      } else {
        setStatus(`Troca cancelada: ${message.reason}`);
      }
      confirmButton.disabled = true;
      cancelButton.disabled = !hasJoinedRoom;
      log(`Troca cancelada: ${message.reason}`);
      break;
    case "battle_room_created":
      hasJoinedBattleRoom = true;
      updateBattleRoomDisplay(message.room);
      setBattleStatus("Sala de batalha criada. Aguardando segundo usuário.");
      setStatus("Sala de batalha criada. Aguardando segundo usuario.");
      log("Sala de batalha criada.");
      forfeitBattleButton.disabled = false;
      break;
    case "battle_room_joined":
      hasJoinedBattleRoom = true;
      updateBattleRoomDisplay(message.room);
      setBattleStatus("Entrou na sala de batalha. Enviando time.");
      setStatus("Entrou na sala de batalha. Enviando time.");
      log("Entrou na sala de batalha.");
      forfeitBattleButton.disabled = false;
      sendBattleTeam();
      break;
    case "battle_room_ready":
      updateBattleRoomDisplay(message.room);
      log("Sala de batalha pronta.");
      if (currentAction === "battle_create") {
        setBattleStatus("Segundo usuário entrou. Enviando time.");
        setStatus("Segundo usuario entrou. Enviando time.");
        sendBattleTeam();
      }
      break;
    case "battle_team_received":
      updateBattleRoomDisplay(message.room);
      setBattleStatus(`Servidor recebeu seu time (${message.team_size || 0} Pokémon).`);
      log("Servidor recebeu seu time de batalha.");
      break;
    case "battle_ready":
      updateBattleRoomDisplay(message.room);
      setBattleStatus("Times prontos. Confirme para iniciar.");
      setStatus("Times prontos. Confirme para iniciar batalha.");
      confirmBattleButton.disabled = false;
      log("Batalha pronta.");
      break;
    case "battle_confirmed":
      setBattleStatus("Confirmação enviada. Aguardando o outro jogador.");
      setStatus("Confirmacao de batalha enviada.");
      log("Confirmacao de batalha enviada.");
      break;
    case "battle_started":
      currentBattleId = message.battle_id;
      updateBattleRoomDisplay(message.room);
      setBattleStatus("Batalha iniciada. Aguarde sua ação.");
      setStatus("Batalha iniciada.");
      confirmBattleButton.disabled = true;
      forfeitBattleButton.disabled = false;
      setBattleActionsEnabled(false);
      for (const line of message.logs || []) battleLog(line);
      log("Batalha iniciada.");
      break;
    case "battle_log":
      for (const line of message.logs || []) battleLog(line);
      break;
    case "battle_request_action":
      currentBattleId = message.battle_id || currentBattleId;
      setBattleStatus("Escolha uma ação de batalha.");
      setBattleActionsEnabled(true);
      battleLog("|request|escolha um golpe ou passe o turno");
      break;
    case "battle_finished":
      currentBattleId = null;
      hasJoinedBattleRoom = false;
      setBattleStatus("Batalha finalizada.");
      setStatus("Batalha finalizada.");
      for (const line of message.logs || []) battleLog(line);
      confirmBattleButton.disabled = true;
      forfeitBattleButton.disabled = true;
      setBattleActionsEnabled(false);
      log("Batalha finalizada.");
      break;
    case "heartbeat":
      break;
    default:
      log(`Evento: ${message.type}`);
  }
}

function sendOffer() {
  localPayload = selectedPayload();
  localOfferEl.textContent = localPayload.display_summary;
  send({ type: "offer_pokemon", payload: localPayload });
}

function battleTeam() {
  if (!loadedSave) throw new Error("Escolha um save local.");
  const team = loadedSave.party
    .filter((pokemon) => !pokemon.is_egg)
    .slice(0, 6)
    .map((pokemon) => {
      const payload = loadedSave.exportPayload(pokemon.location);
      const canonical = payload.canonical;
      if (canonical && canonical.original_data) {
        canonical.original_data = { ...canonical.original_data, raw_data_base64: null };
      }
      return canonical;
    });
  if (!team.length) throw new Error("A party nao possui Pokemon validos para batalha.");
  return team;
}

function sendBattleTeam() {
  const team = battleTeam();
  battleTeamCountEl.textContent = `${team.length} Pokémon enviados`;
  send({ type: "offer_battle_team", team });
}

function handlePreflightRequired(message) {
  const payload = message.received_payload;
  peerPayload = payload;
  peerOfferEl.textContent = payload.display_summary || (payload.summary && payload.summary.display_summary) || "-";
  const report = buildWebCompatibilityReport(payload, message);
  if (!loadedSave) {
    report.compatible = false;
    report.blocking_reasons.push("Nenhum save carregado.");
  } else if (!(payload.raw_data_base64 || (payload.raw && payload.raw.data_base64))) {
    if (payload.generation === loadedSave.generation) {
      report.compatible = false;
      report.blocking_reasons.push("Payload same-generation sem raw data.");
    }
  }
  send({
    type: "preflight_result",
    compatible: report.compatible,
    requires_user_confirmation: false,
    report,
    error: report.blocking_reasons.join("; ")
  });
  if (report.compatible) {
    setStatus("Preflight local aprovado. Aguardando o outro usuario.");
    log("Preflight local aprovado.");
  } else {
    setStatus(report.blocking_reasons.join(" "));
    confirmButton.disabled = true;
    log(`Preflight local bloqueado: ${report.blocking_reasons.join("; ")}`);
  }
}

function buildWebCompatibilityReport(payload, message) {
  const targetGeneration = loadedSave ? loadedSave.generation : message.target_generation;
  const report = {
    compatible: true,
    mode: message.derived_mode || "same_generation",
    source_generation: message.source_generation,
    target_generation: targetGeneration,
    blocking_reasons: [],
    warnings: [],
    data_loss: [],
    suggested_actions: [],
    transformations: [],
    removed_moves: [],
    removed_items: [],
    removed_fields: [],
    normalized_species: {},
    requires_user_confirmation: false
  };
  if (!loadedSave || payload.generation === targetGeneration) return report;
  const canonical = canonicalFromPayload(payload);
  if (!canonical) {
    report.compatible = false;
    report.blocking_reasons.push("Payload cross-generation sem canonical.");
    return report;
  }
  const nationalId = Number(canonical.species.national_dex_id);
  const targetSpeciesId = nationalToNative(targetGeneration, nationalId);
  report.normalized_species = {
    national_dex_id: nationalId,
    source_species_id: canonical.species.source_species_id,
    source_species_id_space: canonical.species.source_species_id_space,
    target_species_id: targetSpeciesId,
    target_species_id_space: targetGeneration === 1 ? "gen1_internal" : targetGeneration === 2 ? "national_dex" : "gen3_internal"
  };
  if (!speciesExistsInGeneration(nationalId, targetGeneration)) {
    report.compatible = false;
    report.blocking_reasons.push(`${canonical.species.name} National Dex #${nationalId} nao existe na Gen ${targetGeneration}.`);
    return report;
  }
  report.transformations.push(`Species National Dex #${nationalId} convertido para ID ${targetSpeciesId} na Gen ${targetGeneration}.`);
  const maxMove = targetGeneration === 1 ? 165 : targetGeneration === 2 ? 251 : 354;
  for (const move of canonical.moves || []) {
    const moveId = Number(move.move_id || move);
    if (moveId > maxMove) {
      report.removed_moves.push({ move_id: moveId, name: `Move #${moveId}` });
      if (!report.data_loss.includes("moves")) report.data_loss.push("moves");
    }
  }
  if (canonical.held_item && canonical.held_item.item_id && targetGeneration === 1) {
    report.removed_items.push({ item_id: canonical.held_item.item_id, name: `Item #${canonical.held_item.item_id}` });
    report.data_loss.push("held_item");
  }
  if (targetGeneration < 3) {
    if (canonical.ability) {
      report.removed_fields.push("ability");
      report.data_loss.push("ability");
    }
    if (canonical.nature) {
      report.removed_fields.push("nature");
      report.data_loss.push("nature");
    }
  }
  return report;
}

function supportedTradeModes(generation) {
  void generation;
  return ["same_generation", "time_capsule_gen1_gen2", "forward_transfer_to_gen3", "legacy_downconvert_experimental"];
}

function supportedProtocols() {
  return ["raw_same_generation", "canonical_cross_generation"];
}

async function startRoom(action) {
  const roomName = document.querySelector("#roomName").value.trim();
  const password = document.querySelector("#roomPassword").value;
  const payload = selectedPayload();
  if (!roomName || !password) {
    setStatus("Informe nome da sala e senha.");
    return;
  }
  currentAction = action;
  peerPayload = null;
  hasJoinedRoom = false;
  downloadArea.textContent = "";
  peerOfferEl.textContent = "-";
  localOfferEl.textContent = payload.display_summary;
  confirmButton.disabled = true;
  cancelButton.disabled = true;
  setStatus("Conectando...");
  await connect();
  send({
    type: action === "create" ? "create_room" : "join_room",
    room_name: roomName,
    password,
    generation: loadedSave.generation,
    game: loadedSave.game,
    supported_trade_modes: supportedTradeModes(loadedSave.generation),
    supported_protocols: supportedProtocols()
  });
}

async function startBattleRoom(action) {
  const roomName = document.querySelector("#roomName").value.trim();
  const password = document.querySelector("#roomPassword").value;
  if (!roomName || !password) {
    setStatus("Informe nome da sala e senha.");
    return;
  }
  if (!loadedSave || !loadedSave.party.length) {
    setStatus("Carregue um save com party antes da batalha.");
    return;
  }
  currentAction = action === "create" ? "battle_create" : "battle_join";
  hasJoinedBattleRoom = false;
  currentBattleId = null;
  battleLogEl.textContent = "";
  setBattleActionsEnabled(false);
  confirmBattleButton.disabled = true;
  forfeitBattleButton.disabled = true;
  setStatus("Conectando para batalha...");
  setBattleStatus("Conectando para batalha...");
  await connect();
  send({
    type: action === "create" ? "create_battle_room" : "join_battle_room",
    room_name: roomName,
    password,
    generation: loadedSave.generation,
    game: loadedSave.game
  });
}

createButton.addEventListener("click", () => startRoom("create").catch((error) => setStatus(error.message)));
joinButton.addEventListener("click", () => startRoom("join").catch((error) => setStatus(error.message)));
createBattleButton.addEventListener("click", () => startBattleRoom("create").catch((error) => setStatus(error.message)));
joinBattleButton.addEventListener("click", () => startBattleRoom("join").catch((error) => setStatus(error.message)));
tabButtons.forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});
openTradeTabButton.addEventListener("click", () => activateTab("trade"));
openBattleTabButton.addEventListener("click", () => activateTab("battle"));
confirmButton.addEventListener("click", () => {
  confirmButton.disabled = true;
  send({ type: "confirm_trade" });
});
confirmBattleButton.addEventListener("click", () => {
  confirmBattleButton.disabled = true;
  setBattleStatus("Confirmação enviada. Aguardando início da batalha.");
  send({ type: "confirm_battle" });
});
forfeitBattleButton.addEventListener("click", () => {
  setBattleActionsEnabled(false);
  setBattleStatus("Desistência enviada.");
  send({ type: "battle_forfeit" });
});
battleActionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const action = button.dataset.battleAction || "pass";
    setBattleActionsEnabled(false);
    setBattleStatus(`Ação enviada: ${action}.`);
    send({ type: "battle_action", battle_id: currentBattleId, action });
  });
});
cancelButton.addEventListener("click", () => {
  send({ type: "cancel_trade" });
  socket.close();
});
window.addEventListener("beforeunload", (event) => {
  if (!hasJoinedRoom) return;
  event.preventDefault();
  event.returnValue = "";
});
document.querySelector("#clearLog").addEventListener("click", () => {
  eventLogEl.textContent = "";
});
pokemonChoiceEl.addEventListener("change", () => {
  if (!loadedSave) return;
  const selected = loadedSave.party.find((pokemon) => pokemon.location === pokemonChoiceEl.value);
  localOfferEl.textContent = selected ? selected.display_summary || normalizePokemonDisplay(selected) : "-";
  updateSetupPartyPreview();
});
saveFileEl.addEventListener("change", async () => {
  const file = saveFileEl.files?.[0];
  if (!file) return;
  try {
    loadedSave = loadSave(new Uint8Array(await file.arrayBuffer()), file.name);
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
});

updatePokemonOptions();
activateTab("setup");
log(`Frontend pronto em ${wsUrl()}`);
