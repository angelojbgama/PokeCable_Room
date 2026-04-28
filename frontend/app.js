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

const speciesNames = {
  38: "Kadabra",
  41: "Machoke",
  64: "Kadabra",
  67: "Machoke",
  75: "Graveler",
  93: "Haunter",
  95: "Onix",
  156: "Quilava",
  175: "Togepi",
  201: "Unown",
  208: "Steelix",
  212: "Scizor",
  230: "Kingdra",
  251: "Celebi",
  277: "Treecko",
  280: "Torchic",
  283: "Mudkip",
  373: "Clamperl",
  374: "Huntail",
  375: "Gorebyss",
  412: "Egg"
};

const gen1InternalNames = {
  14: "Gengar",
  34: "Onix",
  38: "Kadabra",
  39: "Graveler",
  41: "Machoke",
  49: "Golem",
  126: "Machamp",
  147: "Haunter",
  149: "Alakazam"
};

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
let loadedSave = null;
let selectedLocation = "party:0";

function log(message) {
  const time = new Date().toLocaleTimeString();
  eventLogEl.textContent += `[${time}] ${message}\n`;
  eventLogEl.scrollTop = eventLogEl.scrollHeight;
}

function setStatus(message) {
  tradeStatusEl.textContent = message;
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
    const speciesName = gen1InternalNames[speciesId] || `Species #${speciesId}`;
    party.push({
      location: `party:${index}`,
      species_id: speciesId,
      species_name: speciesName,
      level: save.bytes[monStart + 0x21],
      nickname: decodeGbcText(save.bytes.slice(nickStart, nickStart + gen1.nameSize)) || speciesName,
      ot_name: decodeGbcText(save.bytes.slice(otStart, otStart + gen1.nameSize)),
      trainer_id: (save.bytes[monStart + 0x0c] << 8) | save.bytes[monStart + 0x0d]
    });
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
    party.push({
      location: `party:${index}`,
      species_id: speciesId,
      species_name: speciesEntry === 0xfd ? "Egg" : speciesNames[speciesId] || `Species #${speciesId}`,
      level: save.bytes[monStart + 0x1f],
      nickname: decodeGbcText(save.bytes.slice(nickStart, nickStart + constants.nameSize)),
      ot_name: decodeGbcText(save.bytes.slice(otStart, otStart + constants.nameSize)),
      trainer_id: (save.bytes[monStart + 0x06] << 8) | save.bytes[monStart + 0x07],
      is_egg: speciesEntry === 0xfd
    });
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
  const displaySummary = `${pokemon.species_name} Lv. ${pokemon.level}`;
  const summary = {
    species_id: pokemon.species_id,
    species_name: pokemon.species_name,
    level: pokemon.level,
    nickname: pokemon.nickname || pokemon.species_name,
    display_summary: displaySummary
  };
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
    canonical: generation === 1 ? null : {
      source_generation: generation,
      source_game: game,
      species_national_id: pokemon.species_id,
      species_name: pokemon.species_name,
      nickname: pokemon.nickname || pokemon.species_name,
      level: pokemon.level,
      ot_name: pokemon.ot_name,
      trainer_id: pokemon.trainer_id
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
    throw new Error(`Payload recebido e Gen ${payload.generation}; este save e Gen ${generation}. Cross-generation ainda esta protegido por feature guard.`);
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

function parseGen3Pokemon(raw) {
  if (raw.length !== gen3.monSize) throw new Error("Struct Pokemon Gen 3 invalido.");
  const personality = readLe32(raw, 0);
  const trainerId = readLe32(raw, 4);
  const checksum = readLe16(raw, 0x1c);
  const secure = decryptGen3Secure(raw);
  if (gen3BoxChecksum(secure) !== checksum) throw new Error("Checksum interno do Pokemon Gen 3 invalido.");
  const growthIndex = gen3.substructOrders[personality % 24][0];
  const speciesId = readLe16(secure, growthIndex * 12);
  return {
    species_id: speciesId,
    species_name: speciesNames[speciesId] || `Species #${speciesId}`,
    level: raw[0x54],
    nickname: decodeGen3Text(raw.slice(0x08, 0x12)),
    ot_name: decodeGen3Text(raw.slice(0x14, 0x1b)),
    trainer_id: trainerId,
    is_egg: speciesId === 412 || Boolean(raw[0x13] & 0x04)
  };
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
    party.push({
      location: `party:${index}`,
      species_id: details.species_id,
      species_name: speciesName,
      level: details.level,
      nickname: details.nickname || speciesName,
      ot_name: details.ot_name,
      trainer_id: details.trainer_id,
      is_egg: details.is_egg
    });
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
  const displaySummary = `${pokemon.species_name} Lv. ${pokemon.level}`;
  const summary = {
    species_id: pokemon.species_id,
    species_name: pokemon.species_name,
    level: pokemon.level,
    nickname: pokemon.nickname || pokemon.species_name,
    display_summary: displaySummary
  };
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
      species_national_id: pokemon.species_id,
      species_name: pokemon.species_name,
      nickname: pokemon.nickname || pokemon.species_name,
      level: pokemon.level,
      ot_name: pokemon.ot_name,
      trainer_id: pokemon.trainer_id
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
  if (payload.generation !== 3) throw new Error(`Payload recebido e Gen ${payload.generation}; este save e Gen 3. Cross-generation ainda esta protegido por feature guard.`);
  const raw = base64ToBytes(payload.raw_data_base64 || (payload.raw && payload.raw.data_base64));
  if (raw.length !== gen3.monSize) throw new Error("Payload Gen 3 invalido.");
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
    return;
  }
  loadedSave.party.forEach((pokemon) => {
    if (pokemon.species_name === "Egg") return;
    const option = document.createElement("option");
    option.value = pokemon.location;
    option.textContent = `${pokemon.species_name} Lv. ${pokemon.level} (${pokemon.nickname})`;
    pokemonChoiceEl.append(option);
  });
  const enabled = pokemonChoiceEl.options.length > 0;
  createButton.disabled = !enabled;
  joinButton.disabled = !enabled;
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
      if (hasJoinedRoom) setStatus("Conexao encerrada.");
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
      if (loadedSave && peerPayload.generation !== loadedSave.generation) {
        setStatus(`Payload recebido e Gen ${peerPayload.generation}; este save e Gen ${loadedSave.generation}. Cross-generation esta protegido por feature guard.`);
        confirmButton.disabled = true;
        log("Payload bloqueado por feature guard cross-generation.");
        break;
      }
      setStatus("Oferta do outro usuario recebida. Confirme para concluir.");
      confirmButton.disabled = false;
      log(`Outro usuario oferece: ${peerOfferEl.textContent}`);
      break;
    case "offers_ready":
      log("As duas ofertas estao prontas.");
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
      log(`Erro: ${message.message || message.code}`);
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

function supportedTradeModes(generation) {
  const modes = ["same_generation"];
  if (generation === 1 || generation === 2) modes.push("time_capsule_gen1_gen2");
  if (generation === 1 || generation === 2 || generation === 3) modes.push("forward_transfer_to_gen3");
  if (generation === 3) modes.push("legacy_downconvert_experimental");
  return modes;
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
    trade_mode: "same_generation",
    supported_trade_modes: supportedTradeModes(loadedSave.generation)
  });
}

createButton.addEventListener("click", () => startRoom("create").catch((error) => setStatus(error.message)));
joinButton.addEventListener("click", () => startRoom("join").catch((error) => setStatus(error.message)));
confirmButton.addEventListener("click", () => {
  confirmButton.disabled = true;
  send({ type: "confirm_trade" });
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
log(`Frontend pronto em ${wsUrl()}`);
