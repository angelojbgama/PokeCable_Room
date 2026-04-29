#!/usr/bin/env node
"use strict";

const readline = require("node:readline");
const crypto = require("node:crypto");

let showdown = null;
let showdownLoadError = null;

for (const moduleName of ["pokemon-showdown", "pokemon-showdown/dist/sim"]) {
  try {
    showdown = require(moduleName);
    break;
  } catch (error) {
    showdownLoadError = error;
  }
}

const battles = new Map();

const KNOWN_MOVES = new Map([
  [1, "Pound"],
  [5, "Mega Punch"],
  [15, "Cut"],
  [33, "Tackle"],
  [35, "Wrap"],
  [45, "Growl"],
  [55, "Water Gun"],
  [57, "Surf"],
  [84, "Thunder Shock"],
  [85, "Thunderbolt"],
  [86, "Thunder Wave"],
  [93, "Confusion"],
  [94, "Psychic"],
  [98, "Quick Attack"],
  [100, "Teleport"],
  [105, "Recover"],
  [113, "Light Screen"],
  [118, "Metronome"],
  [129, "Swift"],
  [135, "Soft-Boiled"],
  [146, "Dizzy Punch"],
  [164, "Substitute"],
  [183, "Mach Punch"],
  [192, "Zap Cannon"],
  [252, "Fake Out"],
]);

const rl = readline.createInterface({
  input: process.stdin,
  crlfDelay: Infinity,
});

rl.on("line", (line) => {
  if (!line.trim()) return;
  handleLine(line).catch((error) => {
    respond({ request_id: null, ok: false, error: String(error && error.message ? error.message : error) });
  });
});

async function handleLine(line) {
  let request;
  try {
    request = JSON.parse(line);
  } catch (error) {
    respond({ request_id: null, ok: false, error: "invalid_json" });
    return;
  }

  const requestId = request.request_id || null;
  try {
    switch (request.type) {
      case "create_battle":
        respond({ request_id: requestId, ok: true, ...(await createBattle(request)) });
        break;
      case "battle_action":
        respond({ request_id: requestId, ok: true, ...(await sendAction(request)) });
        break;
      case "get_logs":
        respond({ request_id: requestId, ok: true, ...(await getLogs(request)) });
        break;
      case "battle_forfeit":
        respond({ request_id: requestId, ok: true, ...(await forfeit(request)) });
        break;
      case "ping":
        respond({ request_id: requestId, ok: true, pong: true });
        break;
      default:
        respond({ request_id: requestId, ok: false, error: `unknown_request_type:${request.type}` });
    }
  } catch (error) {
    respond({ request_id: requestId, ok: false, error: String(error && error.message ? error.message : error) });
  }
}

function respond(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

async function createBattle(request) {
  const api = requireShowdownApi();
  const battleId = `showdown-${crypto.randomUUID ? crypto.randomUUID() : crypto.randomBytes(12).toString("hex")}`;
  const formatId = String(request.format_id || "gen3customgame");
  const battleStream = new api.BattleStreams.BattleStream();
  const streams = api.BattleStreams.getPlayerStreams(battleStream);
  const playerByClient = new Map([
    [String(request.player_a_id || "A"), "p1"],
    [String(request.player_b_id || "B"), "p2"],
  ]);
  const battle = {
    battleId,
    formatId,
    streams,
    playerByClient,
    logs: [],
    finished: false,
  };
  battles.set(battleId, battle);
  collectOutput(battle);

  const playerATeam = packTeam(api.Teams, request.player_a_team || [], formatId, api.Dex);
  const playerBTeam = packTeam(api.Teams, request.player_b_team || [], formatId, api.Dex);

  await streams.omniscient.write(`>start ${JSON.stringify({ formatid: formatId })}`);
  await streams.omniscient.write(`>player p1 ${JSON.stringify({ name: "PokeCable A", team: playerATeam })}`);
  await streams.omniscient.write(`>player p2 ${JSON.stringify({ name: "PokeCable B", team: playerBTeam })}`);
  await delay(80);

  return {
    battle_id: battleId,
    logs: battle.logs.slice(),
    finished: battle.finished,
  };
}

async function sendAction(request) {
  const battle = requireBattle(request.battle_id);
  if (battle.finished) {
    return { battle_id: battle.battleId, logs: [], finished: true };
  }
  const side = sideForClient(battle, request.client_id);
  const action = normalizeAction(request.action);
  const start = battle.logs.length;
  await battle.streams.omniscient.write(`>${side} ${action}`);
  await delay(80);
  return {
    battle_id: battle.battleId,
    logs: battle.logs.slice(start),
    finished: battle.finished,
  };
}

async function getLogs(request) {
  const battle = requireBattle(request.battle_id);
  return {
    battle_id: battle.battleId,
    logs: battle.logs.slice(),
    finished: battle.finished,
  };
}

async function forfeit(request) {
  const battle = requireBattle(request.battle_id);
  const side = sideForClient(battle, request.client_id);
  const start = battle.logs.length;
  await battle.streams.omniscient.write(`>${side} forfeit`);
  await delay(80);
  return {
    battle_id: battle.battleId,
    logs: battle.logs.slice(start),
    finished: true,
  };
}

function requireShowdownApi() {
  if (!showdown) {
    const detail = showdownLoadError && showdownLoadError.message ? showdownLoadError.message : "pokemon-showdown not installed";
    throw new Error(`pokemon-showdown unavailable: ${detail}`);
  }
  const BattleStreams = showdown.BattleStreams || (
    showdown.BattleStream && showdown.getPlayerStreams
      ? { BattleStream: showdown.BattleStream, getPlayerStreams: showdown.getPlayerStreams }
      : null
  );
  if (!BattleStreams || !showdown.Teams) {
    throw new Error("pokemon-showdown API missing BattleStream/getPlayerStreams or Teams");
  }
  return { BattleStreams, Teams: showdown.Teams, Dex: showdown.Dex };
}

function requireBattle(battleId) {
  const battle = battles.get(String(battleId || ""));
  if (!battle) throw new Error("battle_not_found");
  return battle;
}

function sideForClient(battle, clientId) {
  const key = String(clientId || "");
  if (battle.playerByClient.has(key)) return battle.playerByClient.get(key);
  if (key === "A" || key === "p1") return "p1";
  if (key === "B" || key === "p2") return "p2";
  return "p1";
}

function normalizeAction(value) {
  const action = String(value || "").trim().replace(/^>[a-z0-9]+\s+/i, "");
  if (!action || action === "pass") return "move 1";
  if (/^(move|switch|team|default|undo|forfeit)\b/i.test(action)) return action;
  return "move 1";
}

function collectOutput(battle) {
  (async () => {
    try {
      for await (const chunk of battle.streams.omniscient) {
        for (const line of String(chunk).split(/\r?\n/)) {
          const clean = line.trim();
          if (!clean) continue;
          battle.logs.push(clean);
          if (clean.startsWith("|win|") || clean.startsWith("|tie|")) {
            battle.finished = true;
          }
        }
      }
    } catch (error) {
      battle.logs.push(`|error|${String(error && error.message ? error.message : error)}`);
      battle.finished = true;
    }
  })();
}

function packTeam(Teams, canonicalTeam, formatId, Dex = null) {
  const teamText = canonicalTeamToShowdownText(canonicalTeam, formatId, Dex);
  const imported = Teams.import(teamText);
  if (!imported || !imported.length) {
    throw new Error("pokemon-showdown rejected empty team");
  }
  return Teams.pack(imported);
}

function canonicalTeamToShowdownText(team, formatId, Dex = null) {
  const generation = generationFromFormat(formatId);
  return (Array.isArray(team) ? team : [])
    .slice(0, 6)
    .map((pokemon) => canonicalToShowdownSetText(pokemon || {}, generation, Dex))
    .filter(Boolean)
    .join("\n\n");
}

function canonicalToShowdownSetText(pokemon, generation, Dex = null) {
  const species = pokemon.species || {};
  const speciesName = resolveSpeciesName(pokemon, Dex);
  const nickname = cleanName(pokemon.nickname || "");
  const item = pokemon.held_item && generation >= 2 ? cleanName(pokemon.held_item.name || "") : "";
  const gender = cleanGender((pokemon.metadata && pokemon.metadata.gender) || pokemon.gender);
  const level = clampInt(pokemon.level, 1, 100, 50);
  const headerName = nickname && normalizeComparable(nickname) !== normalizeComparable(speciesName)
    ? `${nickname} (${speciesName})`
    : speciesName;
  let header = headerName;
  if (gender) header += ` (${gender})`;
  if (item) header += ` @ ${item}`;

  const lines = [header, `Level: ${level}`];
  if (generation >= 3 && pokemon.ability) lines.push(`Ability: ${cleanName(pokemon.ability)}`);
  if (generation >= 3 && pokemon.nature) lines.push(`${cleanName(pokemon.nature)} Nature`);
  const moves = canonicalMoves(pokemon.moves || []);
  for (const move of moves) lines.push(`- ${move}`);
  return lines.join("\n");
}

function resolveSpeciesName(pokemon, Dex = null) {
  const species = pokemon.species || {};
  const nationalDexId = Number(species.national_dex_id || pokemon.species_national_id || 0);
  const rawName = cleanName(species.name || pokemon.species_name || "");
  if (rawName && !isPlaceholderSpeciesName(rawName)) return rawName;
  const dexName = speciesNameFromDex(Dex, nationalDexId);
  if (dexName) return dexName;
  if (rawName) return rawName;
  return "Pokemon";
}

const speciesNameCache = new Map();

function speciesNameFromDex(Dex, nationalDexId) {
  if (!Dex || !nationalDexId) return "";
  if (speciesNameCache.has(nationalDexId)) return speciesNameCache.get(nationalDexId);
  try {
    const species = Dex.species.all().find((candidate) => candidate.num === nationalDexId && !candidate.forme);
    const name = species ? species.name : "";
    speciesNameCache.set(nationalDexId, name);
    return name;
  } catch (_error) {
    return "";
  }
}

function isPlaceholderSpeciesName(value) {
  return /^species\s*#?\s*\d+$/i.test(String(value || "").trim());
}

function canonicalMoves(moves) {
  const result = [];
  for (const move of Array.isArray(moves) ? moves : []) {
    const moveId = Number(move && move.move_id);
    const name = cleanMoveName((move && move.name) || KNOWN_MOVES.get(moveId) || "");
    if (!name || name === "None") continue;
    if (!result.includes(name)) result.push(name);
    if (result.length >= 4) break;
  }
  if (!result.length) result.push("Tackle");
  return result;
}

function cleanMoveName(value) {
  const text = cleanName(value);
  if (!text || /^Move #?\d+$/i.test(text)) return "";
  return text;
}

function cleanName(value) {
  return String(value || "").replace(/[^\p{L}\p{N}\-'. ]/gu, "").trim();
}

function cleanGender(value) {
  const text = String(value || "").trim().toUpperCase();
  if (["M", "MALE", "♂"].includes(text)) return "M";
  if (["F", "FEMALE", "♀"].includes(text)) return "F";
  return "";
}

function normalizeComparable(value) {
  return String(value || "").replace(/[^a-z0-9]/gi, "").toLowerCase();
}

function clampInt(value, min, max, fallback) {
  const number = Number.parseInt(value, 10);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function generationFromFormat(formatId) {
  const match = String(formatId || "").match(/^gen([1-9])/i);
  return match ? Number(match[1]) : 3;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
